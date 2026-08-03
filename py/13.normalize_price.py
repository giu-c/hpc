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

# --- tabella di lookup ----------------------------------------------------
lookup = pd.read_excel(LOOKUP_XLSX, sheet_name="Foglio1",
                       usecols=["processor", "perf_index", "SMT_factor"])
lookup = lookup.dropna(subset=["perf_index", "SMT_factor"])
lookup["normalizer"] = lookup["perf_index"] * lookup["SMT_factor"] / 100

norm_map = lookup.set_index(lookup["processor"].str.strip())["normalizer"]

# --- dataset --------------------------------------------------------------
df = pd.read_csv(HPC_CSV)
norm = df[PROC_COL].str.strip().map(norm_map)

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