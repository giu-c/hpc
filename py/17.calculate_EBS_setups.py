import pandas as pd

# 1. Caricamento dei dati
df_oci = pd.read_csv('data/00.lookup/oci_volume_prices.csv')
df_ebs = pd.read_csv('data/00.lookup/ebs_gp3.csv')

rows = []

# 2. Iterazione su ogni regione AWS e configurazione workload
for _, ebs_row in df_ebs.iterrows():
    # Assegnazione identificativo regione
    region_id = ebs_row['region_code'] if ebs_row['region_code'] != 'unknown' else ebs_row['region_name']
    
    rate_storage = ebs_row['storage_usd_gb_mo']
    rate_iops = ebs_row['iops_extra_usd_iops_mo']
    rate_tp = ebs_row['throughput_extra_usd_mibps_mo']
    
    for _, oci_row in df_oci.iterrows():
        size = oci_row['size(GB)']
        vpu = oci_row['VPU']
        iops = oci_row['max_iops']
        tp = oci_row['max_throughput(MBps)']
        
        # Sconto franchigia AWS gp3 (3000 IOPS e 125 MBps gratuiti)
        paid_iops = max(0, iops - 3000)
        paid_tp = max(0, tp - 125)
        
        # Calcolo dei costi
        cost_storage = size * rate_storage
        cost_iops = paid_iops * rate_iops
        cost_tp = (paid_tp / 1024.0) * rate_tp  # Conversione MB/s eccedenti in GB/s fatturabili
        
        monthly_price = cost_storage + cost_iops + cost_tp
        hourly_price = monthly_price / 730
        daily_price = hourly_price * 24
        weekly_price = daily_price * 7
        
        rows.append({
            'region': region_id,
            'size(GB)': size,
            'VPU': vpu,
            'max_iops': iops,
            'max_throughput(MBps)': tp,
            'price($/h)': round(hourly_price, 4),
            'daily_price': round(daily_price, 2),
            'weekly_price': round(weekly_price, 2),
            'monthly_price(730h)': round(monthly_price, 2)
        })

# 3. Creazione del dataframe e salvataggio
df_final = pd.DataFrame(rows)
df_final.to_csv('data/00.lookup/ebs_gp3_prices.csv', index=False)