import pandas as pd
from pathlib import Path

cols = ["displayName", "metricName", "serviceCategory", "currencyCode", "model", "value", "rangeMin", "rangeMax"]

# 1. Carica il file

df = pd.read_csv(Path("data") / "01.raw" / "raw_oci.csv", usecols=cols)

# 2. Applica i filtri classici
condizione = (
    (df["serviceCategory"] == "Compute - Virtual Machine") & 
    (df["currencyCode"] == "USD") & 
    (~df["displayName"].str.contains("Dense|Optimized", na=False))
)

df_filtrato = df[condizione].copy()

# Rimuove le colonne non più necessarie subito dopo il filtraggio
colonne_da_rimuovere = ["serviceCategory", "currencyCode", "model"]
df_filtrato = df_filtrato.drop(columns=colonne_da_rimuovere)


# =========================================================================
# INTEGRATION: Pulizia prefissi e Split di displayName in 3 colonne
# =========================================================================
# Pulizia dei prefissi variabili e uniformazione
df_filtrato["displayName"] = df_filtrato["displayName"].str.replace(r"^(OCI|Oracle Cloud Infrastructure)\s*-\s*", "", regex=True)
df_filtrato["displayName"] = df_filtrato["displayName"].str.replace(r"^Compute\s*-\s*", "", regex=True)
df_filtrato["displayName"] = df_filtrato["displayName"].str.replace(r"Virtual Machine\s+", "", regex=True)
df_filtrato["displayName"] = df_filtrato["displayName"].str.replace("Dense IO", "Dense I/O")

# Split in massimo 3 colonne: Category, Shape, Metric
df_split = df_filtrato["displayName"].str.split(r"\s*-\s*", n=2, expand=True)

# Gestione di sicurezza: se alcune righe hanno meno di due '-' generiamo colonne vuote
for i in range(3):
    if i not in df_split.columns:
        df_split[i] = None

# Assegniamo i valori estratti alle nuove colonne dedicate
df_filtrato[["Category", "Shape", "Metric"]] = df_split[[0, 1, 2]]
# =========================================================================


# 3. Funzione per splittare e tenere l'elemento con il numero + quello prima
def filtra_elementi_con_numero(testo):
    if pd.isna(testo):
        return testo

    elementi = [elem.strip() for elem in str(testo).split("-")]
    indici_da_tenere = set()
    
    for i, elem in enumerate(elementi):
        if any(carattere.isdigit() for carattere in elem):
            indici_da_tenere.add(i)
            if i > 0:
                indici_da_tenere.add(i - 1)
                
    elementi_filtrati = [elementi[idx] for idx in sorted(indici_da_tenere)]
    return " - ".join(elementi_filtrati)

# Applica la funzione alla colonna originaria
df_filtrato["displayName"] = df_filtrato["displayName"].apply(filtra_elementi_con_numero)


# 4. Nelle prime due righe, split per spazio " " e tiene solo il primo elemento
if len(df_filtrato) > 0:
    primi_due_indici = df_filtrato.index[:2]
    df_filtrato.loc[primi_due_indici, "displayName"] = df_filtrato.loc[primi_due_indici, "displayName"].apply(
        lambda x: str(x).split(" ")[0] if pd.notna(x) else x
    )


# 5. Rimuove le ultime tre righe del dataset (se vuoi attivarlo, scommenta la riga sotto)
# df_filtrato = df_filtrato.iloc[:-3]


# =========================================================================
# 5.5 NUOVE TRASFORMAZIONI, RINOMINE E RIORDINAMENTO COLONNE
# =========================================================================

# A. Ridenominazione delle colonne principali
df_filtrato = df_filtrato.rename(columns={
    "metricName": "metric",
    "value": "price($)",
    "Shape": "shape"
})

# B. Trasformazione condizionale dei valori in 'metric'
cond_ocpu = df_filtrato["metric"].str.contains("OCPU", na=False)
cond_giga = df_filtrato["metric"].str.contains("Giga", na=False)
df_filtrato.loc[cond_ocpu, "metric"] = "1 OCPU/h"
df_filtrato.loc[cond_giga, "metric"] = "1 GB(ram)/h"

# C. Cast numerico a float per price, rangeMin e rangeMax
df_filtrato["price($)"] = pd.to_numeric(df_filtrato["price($)"], errors='coerce').astype(float).round(4)
df_filtrato["rangeMin(h/month)"] = pd.to_numeric(df_filtrato["rangeMin"], errors='coerce').astype(float)
df_filtrato["rangeMax(h/month)"] = pd.to_numeric(df_filtrato["rangeMax"], errors='coerce').astype(float)

# D. Pulizia dei valori nella colonna 'shape' (rimozione di "OCPU" e "Memory")
df_filtrato["shape"] = df_filtrato["shape"].str.replace(r"\b(OCPU|Memory)\b", "", regex=True)
df_filtrato["shape"] = df_filtrato["shape"].str.replace(r"\s+", " ", regex=True).str.strip() # Pulisce spazi doppi rimasti

# E. Rimozione definitiva delle colonne obsolete prima del riordinamento
colonne_finali_da_escludere = ["displayName", "Category", "Metric"]
df_filtrato = df_filtrato.drop(columns=colonne_finali_da_escludere, errors='ignore')

# F. Riordinamento: impostiamo 'shape' come prima colonna del dataset
ordine_colonne = ["shape", "metric", "price($)", "rangeMin(h/month)", "rangeMax(h/month)"]
df_filtrato = df_filtrato[ordine_colonne]
# =========================================================================

# 6. Salva il file (forzando il formato float a 4 cifre decimali nel testo del CSV)
df_filtrato.to_csv(Path("data") / "02.cleaned" / "oci_compute_cleaned.csv", index=False, float_format="%.4f")