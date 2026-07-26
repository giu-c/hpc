import pandas as pd
from pathlib import Path

# 1. Caricamento dei dati
df_oci = pd.read_csv(Path('data/04.wrangled/oci.csv'))
df_shapes = pd.read_csv(Path('data/00.lookup/shape_combinations.csv'))

# 2. Prodotto Cartesiano (Cross Join)
df_extended = df_oci.merge(df_shapes, how='cross')

# 3. Calcolo del prezzo totale orario
df_extended['price($/h)'] = (
    (df_extended['vCPU'] * df_extended['vCPU($/h)']) + 
    (df_extended['ram(GB)'] * df_extended['ram($/h)'])
)

# 4. Filtro delle combinazioni impossibili (inclusa la regola vCPU minime per non-A1)
df_extended = df_extended[
    (df_extended['vCPU'] <= df_extended['max_vCPU']) & 
    (df_extended['ram(GB)'] <= df_extended['max_ram']) &
    ((df_extended['shape'] == 'A1') | (df_extended['vCPU'] >= 2))
]

# 5. Aggiungi le nuove colonne calcolate SOLO per shape == "A1"
mask_a1 = df_extended['shape'] == 'A1'


# Calcolo giornaliero con vCPU e ram(GB)
df_extended.loc[mask_a1, "daily_vCPU_price"] = (
    df_extended.loc[mask_a1, "vCPU($/h)"] * df_extended.loc[mask_a1, "vCPU"] * 24
).round(2)

df_extended.loc[mask_a1, "daily_ram_price"] = (
    df_extended.loc[mask_a1, "ram($/h)"] * df_extended.loc[mask_a1, "ram(GB)"] * 24
).round(2)


# Calcolo settimanale con vCPU e ram(GB)
df_extended.loc[mask_a1, "weekly_vCPU_price"] = (
    df_extended.loc[mask_a1, "vCPU($/h)"] * df_extended.loc[mask_a1, "vCPU"] * 168
).round(2)

df_extended.loc[mask_a1, "weekly_ram_price"] = (
    df_extended.loc[mask_a1, "ram($/h)"] * df_extended.loc[mask_a1, "ram(GB)"] * 168
).round(2)


# Calcolo mensile con vCPU e ram(GB)
df_extended.loc[mask_a1, "monthly_vCPU_price"] = (
    df_extended.loc[mask_a1, "vCPU($/h)"] * df_extended.loc[mask_a1, "vCPU"] * 730
).round(2)

df_extended.loc[mask_a1, "monthly_ram_price"] = (
    df_extended.loc[mask_a1, "ram($/h)"] * df_extended.loc[mask_a1, "ram(GB)"] * 730
).round(2)


# Calcolo discount
df_extended.loc[mask_a1, "discount_vCPU_price"] = (
    df_extended.loc[mask_a1, "vCPU($/h)"] * 3000
).round(2)

df_extended.loc[mask_a1, "discount_ram_price"] = (
    df_extended.loc[mask_a1, "ram($/h)"] * 18000
).round(2)

# 6. Rimozione di tutte le colonne intermedie/superflue
colonne_da_rimuovere = [
    'max_vCPU', 'max_ram', 'vCPU($/h)', 'ram($/h)', 
    'vCPU_rangeMin(h/month)', 'ram_rangeMin(h/month)'
]
df_extended = df_extended.drop(columns=colonne_da_rimuovere)

# 7. ARROTONDAMENTO: Limita i float a 5 cifre decimali
df_extended = df_extended.round(5)

# 8. Riordino delle colonne rimaste
colonne_ordinate = [
    'shape', 'processor', 'vCPU', 'ram(GB)', 'price($/h)', 
    'daily_vCPU_price', 'daily_ram_price',
    'weekly_vCPU_price', 'weekly_ram_price',
    'monthly_vCPU_price', 'monthly_ram_price',
    'discount_vCPU_price', 'discount_ram_price'
]
df_extended = df_extended[colonne_ordinate]

# 9. Salvataggio del nuovo DataFrame
df_extended.to_csv('oci.csv', index=False)

print("Operazione completata! Il file 'oci.csv' è stato generato in versione compatta e pulita.")