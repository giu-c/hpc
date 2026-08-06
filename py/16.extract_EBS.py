import os
import glob
import pandas as pd
import numpy as np

# 1. Percorsi input e output
INPUT_DIR = os.path.join("data", "01.raw", "ec2_regions")
OUTPUT_DIR = os.path.join("data", "00.lookup")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 2. Mappatura completa Nome Regione AWS -> Codice Regione
AWS_LOCATION_MAP = {
    "US East (N. Virginia)": "us-east-1",
    "US East (Ohio)": "us-east-2",
    "US West (N. California)": "us-west-1",
    "US West (Oregon)": "us-west-2",
    "Africa (Cape Town)": "af-south-1",
    "Asia Pacific (Hong Kong)": "ap-east-1",
    "Asia Pacific (Hyderabad)": "ap-south-2",
    "Asia Pacific (Jakarta)": "ap-southeast-3",
    "Asia Pacific (Melbourne)": "ap-southeast-4",
    "Asia Pacific (Mumbai)": "ap-south-1",
    "Asia Pacific (Osaka)": "ap-northeast-3",
    "Asia Pacific (Seoul)": "ap-northeast-2",
    "Asia Pacific (Singapore)": "ap-southeast-1",
    "Asia Pacific (Sydney)": "ap-southeast-2",
    "Asia Pacific (Tokyo)": "ap-northeast-1",
    "Canada (Central)": "ca-central-1",
    "Canada West (Calgary)": "ca-west-1",
    "Europe (Frankfurt)": "eu-central-1",
    "Europe (Ireland)": "eu-west-1",
    "Europe (London)": "eu-west-2",
    "Europe (Milan)": "eu-south-1",
    "Europe (Paris)": "eu-west-3",
    "Europe (Spain)": "eu-south-2",
    "Europe (Stockholm)": "eu-north-1",
    "Europe (Zurich)": "eu-central-2",
    "Israel (Tel Aviv)": "il-central-1",
    "Middle East (Bahrain)": "me-south-1",
    "Middle East (UAE)": "me-central-1",
    "South America (São Paulo)": "sa-east-1"
}

def get_col(df, possible_names):
    """Trova il nome effettivo della colonna nel dataframe."""
    norm_map = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for name in possible_names:
        clean = name.lower().replace(" ", "").replace("_", "")
        if clean in norm_map:
            return norm_map[clean]
    return None

print(f"Lettura file in corso da: {INPUT_DIR}...")
csv_files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))

records_list = []

for file_path in csv_files:
    try:
        # Salta le 5 righe di intestazione AWS
        df = pd.read_csv(file_path, skiprows=5, low_memory=False)
        
        # Identificazione flessibile delle colonne
        col_vol_api     = get_col(df, ['Volume API Name', 'volumeApiName', 'Volume Type'])
        col_usage_type  = get_col(df, ['usageType', 'UsageType'])
        col_price_desc  = get_col(df, ['PriceDescription', 'priceDescription'])
        col_location    = get_col(df, ['Location', 'location'])
        col_price       = get_col(df, ['PricePerUnit', 'pricePerUnit'])
        col_unit        = get_col(df, ['Unit', 'unit'])
        col_currency    = get_col(df, ['Currency', 'currency'])
        col_eff_date    = get_col(df, ['EffectiveDate', 'effectiveDate'])
        col_sku         = get_col(df, ['SKU', 'sku'])
        col_rate_code   = get_col(df, ['RateCode', 'rateCode'])
        col_term_type   = get_col(df, ['TermType', 'termType'])

        # Filtro GP3: Cerca 'gp3' in usageType, Volume API Name o PriceDescription SENZA filtrare per Product Family
        is_gp3 = pd.Series(False, index=df.index)
        if col_usage_type:
            is_gp3 = is_gp3 | (df[col_usage_type].astype(str).str.contains('gp3', case=False, na=False))
        if col_vol_api:
            is_gp3 = is_gp3 | (df[col_vol_api].astype(str).str.lower() == 'gp3')
        if col_price_desc:
            is_gp3 = is_gp3 | (df[col_price_desc].astype(str).str.contains('gp3', case=False, na=False))

        df_gp3 = df[is_gp3].copy()

        if df_gp3.empty:
            continue

        # Filtro per le sole opzioni OnDemand / senza contratto
        if col_term_type:
            df_gp3 = df_gp3[df_gp3[col_term_type].isin(['OnDemand', np.nan]) | df_gp3[col_term_type].isna()]

        # Estrazione e pulizia dati
        clean_df = pd.DataFrame()
        clean_df['location']       = df_gp3[col_location] if col_location else "Unknown"
        clean_df['usage_type']     = df_gp3[col_usage_type] if col_usage_type else ""
        clean_df['price_description'] = df_gp3[col_price_desc] if col_price_desc else ""
        clean_df['price_usd']      = pd.to_numeric(df_gp3[col_price], errors='coerce') if col_price else np.nan
        clean_df['unit']           = df_gp3[col_unit] if col_unit else ""
        clean_df['currency']       = df_gp3[col_currency] if col_currency else "USD"
        clean_df['effective_date'] = pd.to_datetime(df_gp3[col_eff_date], errors='coerce').dt.strftime('%Y-%m-%d') if col_eff_date else ""
        clean_df['sku']            = df_gp3[col_sku] if col_sku else ""
        clean_df['rate_code']      = df_gp3[col_rate_code] if col_rate_code else ""

        # Rimuove righe con prezzo vuoto o righe di sconto Tiered secondarie (mantiene i prezzi base)
        clean_df = clean_df.dropna(subset=['price_usd'])
        
        records_list.append(clean_df)
        print(f"  Estratti {len(clean_df)} record gp3 da {os.path.basename(file_path)}")

    except Exception as e:
        print(f"  Errore nel file {file_path}: {e}")

if records_list:
    df_all = pd.concat(records_list, ignore_index=True)

    # Mappatura codice regione (es. eu-central-1)
    df_all['region_code'] = df_all['location'].map(AWS_LOCATION_MAP).fillna('unknown')

    # Classificazione precisa delle 3 componenti gp3
    def classify_component(row):
        us = str(row['usage_type']).lower()
        u = str(row['unit']).lower()
        desc = str(row['price_description']).lower()
        
        if 'volumep-iops' in us or 'iops' in u or 'iops' in desc:
            return 'Provisioned IOPS'
        elif 'volumep-throughput' in us or 'mibps' in u or 'mb/s' in u or 'throughput' in desc:
            return 'Provisioned Throughput'
        elif 'volumeusage' in us or 'gb' in u or 'storage' in desc:
            return 'Storage Capacity'
        return 'Other'

    df_all['component'] = df_all.apply(classify_component, axis=1)

    # 1. Output Dettagliato (Long Format)
    df_long = df_all[[
        'region_code', 'location', 'component', 'price_usd', 'unit', 'currency', 'effective_date', 'usage_type', 'price_description', 'sku', 'rate_code'
    ]].rename(columns={'location': 'region_name'}).sort_values(by=['region_code', 'component'])


    # 2. Output Sintetico (Pivot: 1 riga per regione con le 3 colonne di costo)
    df_pivot = df_long.pivot_table(
        index=['region_code', 'region_name', 'currency'],
        columns='component',
        values='price_usd',
        aggfunc='min'  # Prende il prezzo OnDemand principale
    ).reset_index()

    df_pivot.columns.name = None
    df_pivot = df_pivot.rename(columns={
        'Storage Capacity': 'storage_usd_gb_mo',
        'Provisioned IOPS': 'iops_extra_usd_iops_mo',
        'Provisioned Throughput': 'throughput_extra_usd_mibps_mo'
    })

    out_pivot = os.path.join(OUTPUT_DIR, "ebs_gp3.csv")
    df_pivot.to_csv(out_pivot, index=False)
    print(f"[✓] Salvato file sintetico: {out_pivot}")