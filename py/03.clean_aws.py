from pathlib import Path
import pandas as pd
import duckdb
import gc

# Configurazione percorsi
RAW_DIR = Path("data/01.raw/ec2_regions")
CLEANED_REGIONS_DIR = Path("data/02.cleaned/ec2_regions")
MASTER_DIR = Path("data/02.cleaned")

# Family_code "standard"
STANDARD_FAMILIES = [
    "c6a", "c6g", "c6i",
    "c7a", "c7g", "c7i",
    "c8a", "c8g", "c8i",
    "c9g",
    "m6a", "m6g", "m6i",
    "m7a", "m7g", "m7i",
    "m8a", "m8g", "m8i",
    "m9g", 
    "r6a", "r6g", "r6i",
    "r7a", "r7g", "r7i", 
    "r8a", "r8g", "r8i",
    "x8g", "x8i",
]

# Dizionario delle region
AWS_REGIONS = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "af-south-1": "Africa (Cape Town)",
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "ap-east-2": "Asia Pacific (Taipei)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-south-2": "Asia Pacific (Hyderabad)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-southeast-3": "Asia Pacific (Jakarta)",
    "ap-southeast-4": "Asia Pacific (Melbourne)",
    "ap-southeast-5": "Asia Pacific (Malaysia)",
    "ap-southeast-6": "Asia Pacific (New Zealand)",
    "ap-southeast-7": "Asia Pacific (Thailand)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ca-central-1": "Canada (Central)",
    "ca-west-1": "Canada West (Calgary)",
    "eu-central-1": "Europe (Frankfurt)",
    "eu-central-2": "Europe (Zurich)",
    "eu-west-1": "Europe (Ireland)",
    "eu-west-2": "Europe (London)",
    "eu-west-3": "Europe (Paris)",
    "eu-south-1": "Europe (Milan)",
    "eu-south-2": "Europe (Spain)",
    "eu-north-1": "Europe (Stockholm)",
    "il-central-1": "Israel (Tel Aviv)",
    "mx-central-1": "Mexico (Central)",
    "me-south-1": "Middle East (Bahrain)",
    "me-central-1": "Middle East (UAE)",
    "sa-east-1": "South America (São Paulo)",
}

def clean_aws_ec2_pricing(df, region, standard_families=STANDARD_FAMILIES):
    # Filtri a valore fisso
    mask = (
        (df['TermType'] == 'OnDemand') &
        (df['Unit'] == 'Hrs') &
        (df['CapacityStatus'] == 'Used') &
        (df['Operating System'] == 'Linux') &
        (df['License Model'] == 'No License required') &
        (df['Pre Installed S/W'].isna()) &
        (df['Tenancy'] == 'Shared') &
        (df['Region Code'] == region) &
        (df['MarketOption'] == 'OnDemand') &
        (df['Product Family'] == 'Compute Instance') &
        (df['Storage'] == 'EBS only')
    )

    clean = df.loc[mask].copy()
    if clean.empty:
        return pd.DataFrame()

    # shape (prefisso di Instance Type)
    clean['shape'] = clean['Instance Type'].str.split('.').str[0]
    clean = clean[clean['shape'].isin(standard_families)]

    if clean.empty:
        return pd.DataFrame()

    keep_cols = ['Region Code', 'shape', 'Physical Processor', 'vCPU', 'Memory', 'PricePerUnit']
    clean = clean[keep_cols].reset_index(drop=True)

    clean = clean.rename(columns={
        'Region Code': 'region',
        'Physical Processor': 'processor',
        'Memory': 'ram(GB)',
        'PricePerUnit': 'price($/h)',
    })

    # Cast tipizzati
    clean['vCPU'] = clean['vCPU'].astype(int)
    clean['ram(GB)'] = (
        clean['ram(GB)'].str.replace(' GiB', '', regex=False)
                        .str.replace(',', '', regex=False)
                        .astype(float)
                        .round(2)
    )
    clean['price($/h)'] = clean['price($/h)'].astype(float).round(8)

    # Diagnostica rapida
    for keys in (['region', 'shape', 'vCPU', 'ram(GB)'], ['region', 'processor', 'vCPU', 'ram(GB)']):
        dup = clean.groupby(keys)['price($/h)'].nunique()
        flagged = dup[dup > 1]
        if len(flagged):
            print(f"ATTENZIONE [{region}] - prezzi multipli per stesso {keys}:")
            print(flagged)

    return clean

def process_pipeline(input_dir: Path, cleaned_regions_dir: Path, master_dir: Path, regions: dict):
    # Crea le cartelle se non esistono
    cleaned_regions_dir.mkdir(parents=True, exist_ok=True)
    master_dir.mkdir(parents=True, exist_ok=True)

    # --- FASE 1: PULIZIA E SALVATAGGIO SINGOLO (RAM SAFE) ---
    print("=== FASE 1: Elaborazione e salvataggio dei file singoli ===")
    
    for region in regions.keys():
        file_path = input_dir / f"raw_ec2_{region}.csv"
        if not file_path.exists():
            file_path = input_dir / f"{region}.csv"
            
        if not file_path.exists():
            continue
            
        print(f"[+] Pulizia in corso: {region}...")
        
        try:
            df_raw = pd.read_csv(file_path, skiprows=5, low_memory=False)
            df_cleaned = clean_aws_ec2_pricing(df_raw, region=region)

            if not df_cleaned.empty:
                out_path = cleaned_regions_dir / f"ec2_{region}_cleaned.csv"
                df_cleaned.to_csv(out_path, index=False)
            
            # Forziamo la pulizia della memoria ad ogni iterazione
            del df_raw
            del df_cleaned
            gc.collect()
                
        except Exception as e:
            print(f"[ERR] Errore su {region}: {e}")

    # --- FASE 2: CONSOLIDAMENTO OUT-OF-CORE CON DUCKDB ---
    print("\n=== FASE 2: Consolidamento globale con DuckDB ===")
    
    csv_pattern = sorted(list(cleaned_regions_dir.glob("ec2_*_cleaned.csv")))
    
    if csv_pattern:
        master_csv_path = master_dir / "aws_ec2_cleaned.csv"
        
        # Stringa jolly per DuckDB
        duckdb_csv_path = str(cleaned_regions_dir / "ec2_*_cleaned.csv")
        
        # Connessione temporanea in-memory a DuckDB
        con = duckdb.connect(database=':memory:')
        
        # Costruzione della query SQL (usiamo le virgolette per le colonne con parentesi o caratteri speciali)
        query_consolidate = f"""
            SELECT * 
            FROM read_csv_auto('{duckdb_csv_path}')
            ORDER BY region, shape, processor, vCPU, "ram(GB)", "price($/h)"
        """
        
        try:
            print("[-->] Generazione file master CSV...")
            con.execute(f"COPY ({query_consolidate}) TO '{master_csv_path}' (FORMAT CSV, HEADER);")
            print(f"[OK] Salvato in: {master_csv_path.resolve()}")
            
        except Exception as e:
            print(f"[ERR] Errore durante l'esecuzione di DuckDB: {e}")
        finally:
            con.close()
    else:
        print("[!] Nessun file ripulito trovato. Impossibile generare i file master.")

if __name__ == "__main__":
    process_pipeline(RAW_DIR, CLEANED_REGIONS_DIR, MASTER_DIR, AWS_REGIONS)