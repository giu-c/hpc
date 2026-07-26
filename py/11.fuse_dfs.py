import pandas as pd

# Rifinitura dettagli
# 1. Carica il dataframe dal file originale
df = pd.read_csv('aws.csv')

# 2. Pulisci la colonna (rimuove 'Processor' e gli spazi)
df['processor'] = df['processor'].str.replace('Processor', '').str.strip()

# 3. Sovrascrive il file CSV originale
df.to_csv('aws.csv', index=False)

print("File 'aws.csv' aggiornato con successo!")


# Armonizzazione e fusione dataframe

# 1. Leggi i due dataframe
df_oci = pd.read_csv("oci.csv")
df_aws = pd.read_csv("aws.csv")

# 2. Aggiungi la colonna "region" a oci popolata con "global"
df_oci["region"] = "global"

# 3. Aggiungi la colonna "provider" ad entrambi
df_oci["provider"] = "oci"
df_aws["provider"] = "aws"

# 4. Unisci i due dataframe
df_merged = pd.concat([df_oci, df_aws], ignore_index=True)

# 5. Crea la logica per popolare la colonna "architecture"
def get_architecture(proc):
    proc_str = str(proc)
    if "Ampere" in proc_str or "AWS" in proc_str:
        return "ARM"
    elif "Intel" in proc_str:
        return "x86(Intel)"
    elif "AMD" in proc_str:
        return "x86(AMD)"
    else:
        return "WTF!"

# Applica la funzione per creare la nuova colonna
df_merged["architecture"] = df_merged["processor"].apply(get_architecture)

# 6. Riordina le colonne mettendo 'provider' per prima e 'architecture' prima di 'processor'
new_columns_order = [
    'provider', 
    'region', 
    'family', 
    'architecture', 
    'processor', 
    'vCPU', 
    'ram(GB)', 
    'price($/h)', 
    'daily_price', 
    'weekly_price', 
    'monthly_price'
]
df_final = df_merged[new_columns_order]

df_final['ram(GB)'] = df_final['ram(GB)'].astype(int)

# 7. Salva il nuovo dataframe come hpc.csv
df_final.to_csv("hpc.csv", index=False)
print("File hpc.csv salvato con successo!")