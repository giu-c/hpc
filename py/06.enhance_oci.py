"""
Pulizia e arricchimento del dataset di pricing OCI Compute Shapes.

Operazioni eseguite:
1. Rimozione dei record relativi alle shape di generazione precedente / Always Free:
   E2 Micro, B1, E2, E3, X5, X7.

2. Aggiunta di una colonna "processor" con il nome del processore fisico associato
   a ciascuna shape, secondo la documentazione ufficiale Oracle Cloud Infrastructure:
   https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm

3. Aggiunta di una colonna "vCPU" con il rapporto OCPU:vCPU (equivalente al concetto
   di vCPU usato da AWS EC2), valorizzata solo sulle righe relative a OCPU (1 o 2)
   e lasciata nulla sulle righe relative alla RAM. Fonte: stessa pagina Oracle,
   sezione "OCPUs and vCPUs"

4. Aggiunta di una colonna "max_settable" (intero) con il valore massimo configurabile
   per quella riga: il massimo di OCPU sulle righe con metric a OCPU, il massimo di
   RAM in GB sulle righe con metric a RAM. Fonte: stessa pagina Oracle "Compute Shapes",
   tabella dettagliata delle VM Standard Shapes (colonne "Maximum OCPUs"/"Maximum
   Memory"), verificata il 20/07/2026

5. Moltiplicazione di "max_settable" per il valore di "vCPU" quando "metric"
   è pari a "1 OCPU".

"""

import re
import sys
from pathlib import Path

import pandas as pd

# Shape da rimuovere: generazioni precedenti o shape Always Free
SHAPES_TO_REMOVE_PREVIOUS_GEN = ["E2 Micro", "B1", "E2", "E3", "X5", "X7"]

# Fonte: blog ufficiali Oracle:
#  - "Introducing the Next Generation of OCI Compute Shapes"
#    (blogs.oracle.com/cloud-infrastructure/oci-acceleron-computeshapes)
#  - "Announcing OCI Compute A4 Acceleron Instances"
#    (blogs.oracle.com/cloud-infrastructure/announcing-oci-compute-a4-acceleron-instances)
#
SHAPES_TO_REMOVE_DOMINATED = []

SHAPES_TO_REMOVE = SHAPES_TO_REMOVE_PREVIOUS_GEN + SHAPES_TO_REMOVE_DOMINATED

# Mappatura shape -> processore fisico
# Fonte: Oracle Cloud Infrastructure, pagina ufficiale "Compute Shapes"
PROCESSOR_MAP = {
    "A1": "Ampere Altra Q80-30",
    "A2": "Ampere AmpereOne A160-30",
    "A4": "Ampere AmpereOne M A06-36M",
    "A4 Ax": "Ampere AmpereOne M 192-36M",
    "E4": "AMD EPYC 7J13",
    "E5": "AMD EPYC 9J14",
    "E6": "AMD EPYC 9J45",
    "E6 Ax": "AMD EPYC 9J45",
    "X12 Ax": "Intel Xeon 6987P-C",
    "X9": "Intel Xeon Platinum 8358",
}

# Mappatura shape -> rapporto OCPU:vCPU
# Fonte: Oracle Cloud Infrastructure, pagina ufficiale "Compute Shapes",
# sezione "OCPUs and vCPUs":
#   - Arm A1: 1 OCPU = 1 core = 1 vCPU (esecuzione single-thread)
#   - Arm A2 e A4 (incl. varianti Ax): 1 OCPU = 2 core = 2 vCPU
#   - x86 (AMD ed Intel): 1 OCPU = 2 vCPU (2 thread per core fisico)
VCPU_RATIO_MAP = {
    "A1": 1,
    "A2": 2,
    "A4": 2,
    "A4 Ax": 2,
    "E4": 2,
    "E5": 2,
    "E6": 2,
    "E6 Ax": 2,
    "X12 Ax": 2,
    "X9": 2,
}

# Mappatura shape -> numero massimo di OCPU configurabili (shape "*.Flex")
# Fonte: Oracle Cloud Infrastructure, pagina ufficiale "Compute Shapes",
# sezione "Virtual Machine (VM) Shapes" > "Standard Shapes" (colonna "OCPU",
# valore "... OCPU maximum"). Verificato il 20/07/2026.
MAX_OCPU_MAP = {
    "A1": 76,
    "A2": 78,
    "A4": 45,
    "A4 Ax": 45,
    "E4": 114,
    "E5": 126,
    "E6": 126,
    "E6 Ax": 94,
    "X12 Ax": 39,
    "X9": 56,
}

# Mappatura shape -> RAM massima configurabile, in GB (shape "*.Flex")
# Fonte: stessa pagina Oracle, stessa sezione (colonna "Memory (GB)",
# valore "... GB maximum"). Verificato il 20/07/2026.
MAX_RAM_GB_MAP = {
    "A1": 472,
    "A2": 946,
    "A4": 700,
    "A4 Ax": 720,
    "E4": 1760,
    "E5": 2098,
    "E6": 1454,
    "E6 Ax": 712,
    "X12 Ax": 360,
    "X9": 896,
}


def _natural_sort_key(shape_name: str) -> str:
    """Chiave per un ordinamento 'naturale' delle sigle (es. A1, A2, ... X9, X12 Ax):
    zero-padda i numeri interni alla stringa cosi' un confronto testuale ordina
    correttamente 9 prima di 12, invece di mettere '12' prima di '9' come farebbe
    un confronto puramente alfabetico carattere per carattere."""
    return re.sub(r"\d+", lambda m: m.group().zfill(6), shape_name)


def clean_and_enrich(input_path: Path, output_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"File non trovato: {input_path}")

    df = pd.read_csv(input_path)
    n_before = len(df)

    # 1. Rimozione dei record delle shape indicate
    df = df[~df["shape"].isin(SHAPES_TO_REMOVE)].reset_index(drop=True)
    n_after = len(df)
    print(f"Record rimossi: {n_before - n_after} (righe: {n_before} -> {n_after})")

    # 2. Aggiunta della colonna "processor"
    df["processor"] = df["shape"].map(PROCESSOR_MAP)

    # Controllo di sicurezza: shape rimaste senza processore mappato
    unmapped = sorted(df.loc[df["processor"].isna(), "shape"].unique().tolist())
    if unmapped:
        print(f"ATTENZIONE: shape senza processore mappato in PROCESSOR_MAP: {unmapped}")

    # 3. Aggiunta della colonna "vCPU"
    # Valorizzata (1 o 2) solo sulle righe la cui metrica riguarda le OCPU;
    # lasciata nulla (NA) sulle righe relative alla RAM.
    is_ocpu_row = df["metric"].str.contains("OCPU", case=False, na=False)
    df["vCPU"] = pd.Series(pd.NA, index=df.index, dtype="Int64")  # Int64 nullable: interi puliti + null
    df.loc[is_ocpu_row, "vCPU"] = df.loc[is_ocpu_row, "shape"].map(VCPU_RATIO_MAP)

    # Controllo di sicurezza: righe OCPU rimaste senza rapporto vCPU mappato
    unmapped_vcpu = sorted(
        df.loc[is_ocpu_row & df["vCPU"].isna(), "shape"].unique().tolist()
    )
    if unmapped_vcpu:
        print(f"ATTENZIONE: shape OCPU senza rapporto vCPU mappato in VCPU_RATIO_MAP: {unmapped_vcpu}")

    # 4. Aggiunta della colonna "max_settable"
    # Massimo di OCPU (righe con metric a OCPU) o massimo di RAM in GB (righe con
    # metric a RAM) configurabile per quella shape. Vedi mappe MAX_OCPU_MAP /
    # MAX_RAM_GB_MAP e le note nel docstring del modulo.
    is_ram_row = df["metric"].str.contains("GB", case=False, na=False)

    df["max_settable"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
    df.loc[is_ocpu_row, "max_settable"] = df.loc[is_ocpu_row, "shape"].map(MAX_OCPU_MAP)
    df.loc[is_ram_row, "max_settable"] = df.loc[is_ram_row, "shape"].map(MAX_RAM_GB_MAP)

    # Controlli di sicurezza
    unmapped_max_ocpu = sorted(
        df.loc[is_ocpu_row & df["max_settable"].isna(), "shape"].unique().tolist()
    )
    if unmapped_max_ocpu:
        print(f"ATTENZIONE: shape OCPU senza massimo mappato in MAX_OCPU_MAP: {unmapped_max_ocpu}")

    unmapped_max_ram = sorted(
        df.loc[is_ram_row & df["max_settable"].isna(), "shape"].unique().tolist()
    )
    if unmapped_max_ram:
        print(f"ATTENZIONE: shape RAM senza massimo mappato in MAX_RAM_GB_MAP: {unmapped_max_ram}")

    unrecognized_metric = sorted(
        df.loc[~is_ocpu_row & ~is_ram_row, "metric"].unique().tolist()
    )
    if unrecognized_metric:
        print(f"ATTENZIONE: valori di 'metric' non riconosciuti (ne' OCPU ne' RAM): {unrecognized_metric}")

    # Riordino colonne: processor, vCPU subito dopo shape; max_settable subito dopo metric
    ordered_cols = ["shape", "processor", "vCPU", "metric", "max_settable"] + [
        c for c in df.columns if c not in ("shape", "processor", "vCPU", "metric", "max_settable")
    ]
    df = df[ordered_cols]

    # 5a. Rimozione di "/h" dai valori di "metric" (l'unità temporale passa alla colonna prezzo)
    df["metric"] = df["metric"].str.replace("/h", "", regex=False).str.strip()

    # 5b. Moltiplica "max_settable" per "vCPU" quando la metrica è esattamente "1 OCPU"
    is_1_ocpu = df["metric"] == "1 OCPU"
    df.loc[is_1_ocpu, "max_settable"] = df.loc[is_1_ocpu, "max_settable"] * df.loc[is_1_ocpu, "vCPU"]

    # 5c. Rinomina "price($)" -> "price($/h)"
    df = df.rename(columns={"price($)": "price($/h)"})

    # 5d. Ordinamento per "shape" crescente (ordinamento naturale, stabile sulle righe
    # con la stessa shape, cosi' l'ordine OCPU/RAM e le fasce di prezzo di A1 restano coerenti)
    df = df.sort_values(
        by="shape", key=lambda col: col.map(_natural_sort_key), kind="stable"
    ).reset_index(drop=True)

    df.to_csv(output_path, index=False)
    print(f"File salvato in: {output_path}")
    return df


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data") / "02.cleaned" / "oci_compute_cleaned.csv"
    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data") / "03.enhanced" / "oci_compute.csv"
    )
    clean_and_enrich(input_path, output_path)


if __name__ == "__main__":
    main()