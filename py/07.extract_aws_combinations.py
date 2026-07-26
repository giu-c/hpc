import pandas as pd
from pathlib import Path

# 1. Carica il file CSV sorgente
df = pd.read_csv(Path("data/03.enhanced/aws_ec2.csv"))

# 2. Filtra per region = 'us-east-1'
filtered_df = df[df['region'] == 'us-east-1'].copy()

# Cast della colonna ram(GB) a intero
filtered_df['ram(GB)'] = filtered_df['ram(GB)'].astype(int)

# 3. Estrai le colonne ed elimina i duplicati passando i dati a un set di tuple
tuples_set = set(zip(filtered_df['vCPU'], filtered_df['ram(GB)']))

# 4. Ordina i dati per vCPU e poi per ram(GB)
sorted_data = sorted(tuples_set, key=lambda x: (x[0], x[1]))

# 5. Salva il risultato in un nuovo CSV
output_df = pd.DataFrame(sorted_data, columns=['vCPU', 'ram(GB)'])
output_df.to_csv(Path("data/00.lookup/shape_combinations.csv"), index=False)

print("File 'shape_combinations.csv' creato con successo!")