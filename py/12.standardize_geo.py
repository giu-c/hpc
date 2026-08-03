import pandas as pd

# 1. Caricamento dei file CSV
df_hpc = pd.read_csv("hpc.csv")
df_geo = pd.read_csv("data/00.lookup/geo_cloud.csv")

# 2. Creazione del dizionario di mappatura per AWS (region -> state)
# Consideriamo sia maiuscolo che minuscolo per evitare discrepanze di casing
df_geo_aws = df_geo[df_geo["provider"].str.upper() == "AWS"]
mapping_aws = dict(zip(df_geo_aws["geo"], df_geo_aws["state"]))


# 3. Funzione per determinare lo 'state' in base al provider e alla region
def assign_state(row):
    provider = str(row["provider"]).upper()
    region = row["region"]

    # Regola speciale per OCI: imposta sempre "global"
    if provider == "OCI":
        return "global"
    # Per AWS (e altri eventuali provider), cerca il corrispettivo nel file geo_cloud
    else:
        return mapping_aws.get(region, None)


# 4. Applicazione della funzione per generare la serie dei dati "state"
states_series = df_hpc.apply(assign_state, axis=1)

# 5. Inserimento della colonna "state" subito dopo la colonna "region"
idx_region = df_hpc.columns.get_loc("region")
df_hpc.insert(idx_region + 1, "state", states_series)

# 6. Salvataggio del nuovo dataset
df_hpc.to_csv("hpc.csv", index=False)

print("Elaborazione completata! Il file 'hpc_states.csv' è stato salvato.")