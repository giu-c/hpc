import re
import shutil
import pandas as pd

# --- percorsi -------------------------------------------------------------
HPC_CSV     = "hpc.csv"
LOOKUP_XLSX = "data/00.lookup/price_normalization.xlsx"
OUTPUT_CSV  = "hpc.csv"

PROC_COL = "processor"

# colonne dei prezzi da normalizzare -> cifre decimali di arrotondamento
PRICE_COLS = {
    "price($/h)":    5,
    "daily_price":   4,
    "weekly_price":  3,
    "monthly_price": 2,
}

PREFIX = "N-"

# Nomi non canonici presenti nel dataset -> nome ufficiale del lookup.
# "Intel Xeon 6987P-C" ometteva il "6" della generazione Xeon 6.
RENAME = {
    "Intel Xeon 6987P-C": "Intel Xeon 6 6987P-C",
}

# True = riscrive hpc.csv con i nomi corretti (crea prima hpc.csv.bak)
FIX_SOURCE = True


def canon(s):
    """Normalizza spazi e margini: 'Intel  Xeon 6 ' -> 'Intel Xeon 6'."""
    return s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


# --- tabella di lookup ----------------------------------------------------
lookup = pd.read_excel(LOOKUP_XLSX, sheet_name="Foglio1",
                       usecols=["processor", "perf_index", "SMT_factor"])
lookup = lookup.dropna(subset=["perf_index", "SMT_factor"])
lookup["normalizer"] = lookup["perf_index"] * lookup["SMT_factor"] / 100

norm_map = lookup.set_index(canon(lookup["processor"]))["normalizer"]

# --- dataset --------------------------------------------------------------
df = pd.read_csv(HPC_CSV)

# correzione dei nomi processore, direttamente nel dataset
before = df[PROC_COL].copy()
df[PROC_COL] = canon(df[PROC_COL]).replace(RENAME)
changed = (before != df[PROC_COL]).sum()
if changed:
    print(f"Nomi processore corretti su {changed} righe:")
    for old, new in sorted(set(zip(before[before != df[PROC_COL]],
                                   df[PROC_COL][before != df[PROC_COL]]))):
        print(f"  '{old}' -> '{new}'")

if FIX_SOURCE and changed:
    shutil.copy2(HPC_CSV, HPC_CSV + ".bak")
    df.to_csv(HPC_CSV, index=False)
    print(f"{HPC_CSV} riscritto (backup in {HPC_CSV}.bak)")

norm = df[PROC_COL].map(norm_map)

missing = sorted(df.loc[norm.isna(), PROC_COL].unique())
if missing:
    print(f"ATTENZIONE - {len(missing)} processori assenti dal lookup "
          f"({norm.isna().sum()} righe non normalizzate):")
    for m in missing:
        print(f"  - {m}")

# --- inserimento delle colonne --------------------------------------------
for col, decimals in PRICE_COLS.items():
    df.insert(df.columns.get_loc(col) + 1, PREFIX + col,
              (df[col] / norm).round(decimals))

df.to_csv(OUTPUT_CSV, index=False)
print(f"Salvato {OUTPUT_CSV}: {len(df)} righe, {len(df.columns)} colonne.")