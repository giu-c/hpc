import numpy as np
import pandas as pd

# 1. Caricamento del dataset
df = pd.read_csv("oci.csv")

# Rinomina la colonna all'inizio così tutto il resto del codice usa "family"
df = df.rename(columns={"shape": "family"})

# 2. Creazione della colonna 'monthly_price' condizionale
# Condizione: 'family' uguale ad 'A1' (rimuovendo eventuali spazi bianchi ai bordi)
is_a1 = df["family"].astype(str).str.strip() == "A1"

# Valore per le righe con family == "A1"
prezzo_a1d = (
    (df["daily_vCPU_price"] - df["discount_vCPU_price"]).clip(lower=0) + 
    (df["daily_ram_price"] - df["discount_ram_price"]).clip(lower=0)
).round(2)

# Valore per le righe con family == "A1"
prezzo_a1w = (
    (df["weekly_vCPU_price"] - df["discount_vCPU_price"]).clip(lower=0) + 
    (df["weekly_ram_price"] - df["discount_ram_price"]).clip(lower=0)
).round(2)

# Valore per le righe con family == "A1"
prezzo_a1m = (
    (df["monthly_vCPU_price"] - df["discount_vCPU_price"]).clip(lower=0) + 
    (df["monthly_ram_price"] - df["discount_ram_price"]).clip(lower=0)
).round(2)

# Valore per tutte le altre righe
prezzo_standard_d = (df["price($/h)"] * 24).round(2)
prezzo_standard_w = (df["price($/h)"] * 24 * 7).round(2)
prezzo_standard_m = (df["price($/h)"] * 730).round(2)


# Assegnazione con numpy.where
df["daily_price"] = np.where(is_a1, prezzo_a1d, prezzo_standard_d)
df["weekly_price"] = np.where(is_a1, prezzo_a1w, prezzo_standard_w)
df["monthly_price"] = np.where(is_a1, prezzo_a1m, prezzo_standard_m)

# 3. Eliminazione delle colonne non più necessarie
colonne_da_eliminare = [
    "monthly_vCPU_price",
    "monthly_ram_price",
    "discount_vCPU_price",
    "discount_ram_price",
    "weekly_vCPU_price",
    "weekly_ram_price",
    "daily_vCPU_price",
    "daily_ram_price"
]
df = df.drop(columns=colonne_da_eliminare)

# 4. Imposta a 0 il prezzo orario per A1 (effetto discount)
condizione_a1 = (
    (df["family"].str.contains("A1", case=False, na=False))
    & (df["vCPU"] <= 76)
    & (df["ram(GB)"] <= 472)
)
df.loc[condizione_a1, "price($/h)"] = 0

# 5. Salvataggio del nuovo dataset
df.to_csv("oci.csv", index=False)

print("Elaborazione completata con successo!")