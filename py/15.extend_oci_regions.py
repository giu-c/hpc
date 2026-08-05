import pandas as pd

# 1. Elenco delle 27 nazioni
countries = [
    "Switzerland",
    "Israel",
    "United Arab Emirates",
    "Japan",
    "Spain",
    "Mexico",
    "South Korea",
    "Italy",
    "Ireland",
    "Brazil",
    "Singapore",
    "Indonesia",
    "Canada",
    "Sweden",
    "France",
    "India",
    "Malaysia",
    "Germany",
    "United States",
    "South Africa",
    "United Kingdom",
    "Australia",
]

# 2. Caricamento del dataset
df = pd.read_csv("hpc.csv")

# 3. Separazione delle righe OCI dagli altri provider
oci_df = df[df["provider"] == "oci"].copy()
other_df = df[df["provider"] != "oci"].copy()

# 4. Replicazione delle righe OCI per ciascuna nazione dell'elenco
oci_expanded = (
    oci_df.assign(country=[countries] * len(oci_df))
    .explode("country")
    .reset_index(drop=True)
)

# 5. Unione delle righe replicate con quelle degli altri provider
df_final = pd.concat([other_df, oci_expanded], ignore_index=True)

# 6. Rimozione di tutte le righe dove country == 'global'
df_final = df_final[df_final["country"] != "global"].reset_index(drop=True)

# 7. Salvataggio del nuovo file CSV
df_final.to_csv("hpc.csv", index=False)

print("Operazione completata con successo!")
print(f"Totale righe nel dataset aggiornato: {len(df_final)}")