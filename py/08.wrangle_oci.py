import pandas as pd
from pathlib import Path

# 1. Carica il dataset originale
df = pd.read_csv(Path("data/03.enhanced/oci_compute.csv"))


# 2. SEZIONE CPU 

# Filtra '1 OCPU' & elimina la riga dove rangeMin = 0
df_cpu = df[(df["metric"] == "1 OCPU") & (df["rangeMin(h/month)"] != 0.0)].copy()

# Calcola il prezzo unitario per vCPU
df_cpu["vCPU($/h)"] = df_cpu["price($/h)"] / df_cpu["vCPU"]

# Rinomina la colonna rangeMin specifica per il CPU
df_cpu = df_cpu.rename(columns={
    "rangeMin(h/month)": "vCPU_rangeMin(h/month)",
    "max_settable": "max_vCPU"
    })


# 3. SEZIONE RAM 

# Filtra '1 GB(ram)' e rinomina le colonne per la RAM
df_ram = df[(df["metric"] == "1 GB(ram)") & (df["rangeMin(h/month)"] != 0.0)].copy()
# questo è esattamente quello che abbiamo fatto sopra per la CPU

# Per la RAM, il prezzo 'price($/h)' è già riferito a 1 GB
df_ram = df_ram.rename(columns={
    "price($/h)": "ram($/h)",
    "rangeMin(h/month)": "ram_rangeMin(h/month)",
    "max_settable": "max_ram"
})


# 4. MERGE: unisce i dati CPU e RAM accoppiandoli tramite 'shape'
# Manteniamo da df_ram solo le colonne necessarie
df_merged = pd.merge(
    df_cpu,
    df_ram[["shape", "ram($/h)", "max_ram", "ram_rangeMin(h/month)"]],
    on="shape",
    how="left"
)


# 5. SELEZIONE E RIORDINO: filtra solo le colonne richieste nel formato finale
colonne_finali = [
    "shape",
    "processor",
    "vCPU($/h)",
    "ram($/h)",
    "max_vCPU",
    "max_ram",
    "vCPU_rangeMin(h/month)",
    "ram_rangeMin(h/month)"
]

df_finale = df_merged[colonne_finali]


# 6. Salva il nuovo DataFrame nel file CSV
df_finale.to_csv(Path("data/04.wrangled/oci.csv"), index=False)

print("Wrangling completato con successo! File salvato in 'oci.csv'")