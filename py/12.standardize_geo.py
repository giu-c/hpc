import pandas as pd

# 1. Caricamento dei file CSV
df_hpc = pd.read_csv("hpc.csv")
df_geo = pd.read_csv("data/00.lookup/geo_cloud.csv")

# 2. Creazione del dizionario di mappatura per AWS (region -> country)
df_geo_aws = df_geo[df_geo["provider"].str.upper() == "AWS"]
mapping_aws_country = dict(zip(df_geo_aws["geo"], df_geo_aws["country"]))


# 3. Funzione per determinare il 'country'
def assign_country(row):
    provider = str(row["provider"]).upper()
    region = row["region"]

    if provider == "OCI":
        return "global"
    else:
        return mapping_aws_country.get(region, None)


# 4. Applicazione della funzione per generare la serie "country"
countries_series = df_hpc.apply(assign_country, axis=1)

# 5. Pulizia colonne geografiche precedenti (se esistenti) e inserimento di "country"
for col in ["country", "state"]:
    if col in df_hpc.columns:
        df_hpc.drop(columns=[col], inplace=True)

idx_region = df_hpc.columns.get_loc("region")
df_hpc.insert(idx_region + 1, "country", countries_series)

# 6. Salvataggio del nuovo dataset
df_hpc.to_csv("hpc.csv", index=False)

print("Elaborazione completata! Il file 'hpc.csv' ora contiene solo la colonna 'country'.")