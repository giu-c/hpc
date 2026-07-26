"""
Sostituisce le famiglie Intel generiche (es. "Intel Xeon Scalable (Granite Rapids)")
con il modello/SKU esatto realmente utilizzato da AWS EC2 per ciascuna famiglia di
istanza (family), lasciando invariate le righe AMD ed AWS Graviton (già precise).
 
Mappatura basata su fonti ufficiali AWS (aws.amazon.com/ec2/instance-types/*) e,
dove AWS non pubblica la SKU esatta, su identificazione hardware indipendente
(Phoronix, SpareCores) tramite lscpu sulle istanze reali.
Vedi commenti nel dizionario INTEL_EXACT_MODEL per il dettaglio famiglia per famiglia.
"""
 
import re
import sys
import pandas as pd
from pathlib import Path
 
# ----------------------------------------------------------------------------
# Mappatura family -> processore Intel esatto
# ----------------------------------------------------------------------------
# Ice Lake (3a gen. Xeon Scalable): stessa SKU per tutte le famiglie generiche
# (compute/general/memory optimized). Confermato da pagine ufficiali AWS
# ("Ice Lake 8375C") e dall'identificazione hardware completa "Xeon Platinum
# 8375C" via benchmark Phoronix/Geekbench su istanze m6i/c6i/r6i.
_ICE_LAKE = "Intel Xeon Platinum 8375C"
 
# Sapphire Rapids (4a gen.): stessa SKU 8488C su tutte le famiglie standard
# m7i/c7i/r7i (non r7iz, che usa invece la 6455B ad alta frequenza e non
# compare in questo dataset). Fonte: pagine ufficiali AWS per ciascuna
# famiglia e runs-on.com/AWS EC2 Pricing API.
_SAPPHIRE_RAPIDS = "Intel Xeon Platinum 8488C"
 
# Granite Rapids (Intel Xeon 6): AWS non pubblica la SKU esatta nelle pagine
# di marketing ("custom Intel Xeon 6 processors"). Identificata via lscpu su
# istanze reali (SpareCores, Phoronix):
#  - m8i, c8i, x8i condividono la stessa SKU 6975P-C (3.9 GHz all-core turbo)
#  - r8i usa invece una SKU diversa, 6985P-C, non elencata da Intel
#    (variante "enhanced" per il segmento memory-optimized di fascia alta)
_GRANITE_RAPIDS_STD = "Intel Xeon 6 6975P-C"
_GRANITE_RAPIDS_R8I = "Intel Xeon 6 6985P-C"
 
INTEL_EXACT_MODEL = {
    "c6i": _ICE_LAKE,
    "m6i": _ICE_LAKE,
    "r6i": _ICE_LAKE,
    "c7i": _SAPPHIRE_RAPIDS,
    "m7i": _SAPPHIRE_RAPIDS,
    "r7i": _SAPPHIRE_RAPIDS,
    "c8i": _GRANITE_RAPIDS_STD,
    "m8i": _GRANITE_RAPIDS_STD,
    "x8i": _GRANITE_RAPIDS_STD,
    "r8i": _GRANITE_RAPIDS_R8I,
}
 
# Pattern che identifica un valore "processor" ancora generico (nome di
# famiglia/generazione senza un modello/SKU preciso), usato solo per
# segnalare all'utente eventuali family non ancora mappate sopra.
_GENERIC_MARKERS = ("Scalable (", "Xeon Family")
 
def replace_generic_intel_families(df: pd.DataFrame) -> pd.DataFrame:
    """Ritorna una copia del DataFrame con i processori Intel generici
    sostituiti dal modello esatto, in base a INTEL_EXACT_MODEL."""
    df = df.copy()
    mask = df["family"].isin(INTEL_EXACT_MODEL)
    df.loc[mask, "processor"] = df.loc[mask, "family"].map(INTEL_EXACT_MODEL)
    return df

def add_price_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge le colonne daily_price, weekly_price e monthly_price 
    subito dopo la colonna price($/h), con arrotondamenti specifici."""
    df = df.copy()
    col_name = "price($/h)"
    
    if col_name in df.columns:
        # Recupera l'indice della colonna 'price($/h)' e calcola dove inserire la successiva
        base_idx = df.columns.get_loc(col_name) + 1
        
        # Inserisce le colonne sfruttando i moltiplicatori e arrotondandole (.round)
        df.insert(base_idx, "daily_price", (df[col_name] * 24).round(4))
        df.insert(base_idx + 1, "weekly_price", (df[col_name] * 168).round(3))
        df.insert(base_idx + 2, "monthly_price", (df[col_name] * 730).round(2))
    else:
        print(f"ATTENZIONE: Colonna '{col_name}' non trovata. Impossibile calcolare i prezzi derivati.")
        
    return df
 
def warn_unmapped_generic_rows(df: pd.DataFrame) -> None:
    """Segnala eventuali righe il cui processore resta scritto in forma
    generica dopo la sostituzione: capita se il file contiene family
    Intel non ancora presenti in INTEL_EXACT_MODEL (es. i7i, m8i-flex, ...)."""
    pattern = "|".join(re.escape(marker) for marker in _GENERIC_MARKERS)
    still_generic = df[df["processor"].str.contains(pattern, na=False)]
    
    if not still_generic.empty:
        codes = sorted(still_generic["family"].unique())
        print(
            "ATTENZIONE: trovate famiglie Intel generiche non mappate in "
            f"INTEL_EXACT_MODEL: {codes}. Aggiungi la SKU esatta al dizionario "
            "dopo averla verificata su fonti ufficiali/benchmark indipendenti."
        )
 
def main() -> None:
    input_path = sys.argv[1] if len(sys.argv) > 1 else Path("data") / "02.cleaned" / "aws_ec2_cleaned.csv" 
    output_path = sys.argv[2] if len(sys.argv) > 2 else "aws.csv"
 
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Errore: il file di input non è stato trovato al percorso {input_path}")
        return
        
    # Rinomina la colonna all'inizio così tutto il resto del codice usa "family"
    df = df.rename(columns={"shape": "family"})
 
    before = df[["family", "processor"]].drop_duplicates()
 
    # 1. Correggi i processori Intel
    df_fixed = replace_generic_intel_families(df)
    
    # 2. Aggiungi le colonne dei prezzi giornalieri, settimanali e mensili (arrotondate)
    df_fixed = add_price_columns(df_fixed)
 
    after = df_fixed[["family", "processor"]].drop_duplicates()
 
    changed = before.merge(
        after, on="family", suffixes=("_prima", "_dopo")
    ).query("processor_prima != processor_dopo")
 
    if not changed.empty:
        print("Famiglie aggiornate:")
        for _, row in changed.iterrows():
            print(f"  {row['family']:>6}: '{row['processor_prima']}' -> '{row['processor_dopo']}'")
    else:
        print("Nessuna famiglia generica trovata da sostituire.")
 
    warn_unmapped_generic_rows(df_fixed)
 
    # Assicura che la directory di destinazione esista
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    df_fixed.to_csv(output_path, index=False)
 
    print(f"\n{len(df_fixed)} righe scritte in: {output_path}")
 
if __name__ == "__main__":
    main()