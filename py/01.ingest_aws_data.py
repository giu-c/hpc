"""
Scarica il listino prezzi completo di AWS EC2 per tutte le 34 region
"standard" attualmente disponibili (partizione "aws": esclude AWS GovCloud
(US) e le region Cina, che richiedono account separati e hanno endpoint
di pricing dedicati).

Endpoint pubblico (Price List Bulk API) — nessuna chiave AWS richiesta:
https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/{REGION}/index.csv

ATTENZIONE: ogni file può pesare da poche decine a diverse centinaia di MB.
Scaricare tutte le 34 region può richiedere diversi GB di spazio su disco
e parecchio tempo.
"""

import time
from pathlib import Path
import requests

BASE_URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/{region}/index.csv"
OUTPUT_DIR = Path("data/01.raw/ec2_regions")

# Le 34 region AWS effettivamente disponibili (partizione "aws"),
# così come elencate nella documentazione ufficiale:
# https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html
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


def scarica_listino(url: str, destinazione: Path, chunk_size: int = 1024 * 1024) -> None:
    """Scarica un CSV in streaming, mostrando l'avanzamento."""
    with requests.get(url, stream=True, timeout=60) as risposta:
        risposta.raise_for_status()
        totale = int(risposta.headers.get("Content-Length", 0))
        scaricato = 0

        with open(destinazione, "wb") as f:
            for chunk in risposta.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    scaricato += len(chunk)
                    if totale:
                        percentuale = scaricato / totale * 100
                        print(f"\r  {scaricato/1e6:.1f} MB / {totale/1e6:.1f} MB "
                              f"({percentuale:.1f}%)", end="")
                    else:
                        print(f"\r  {scaricato/1e6:.1f} MB", end="")
        print()


def scarica_tutte_le_region(regioni: dict[str, str], cartella: Path) -> None:
    cartella.mkdir(parents=True, exist_ok=True)
    totale_regioni = len(regioni)

    riepilogo_ok = []
    riepilogo_errori = []

    for i, (codice, nome) in enumerate(regioni.items(), start=1):
        url = BASE_URL.format(region=codice)
        destinazione = cartella / f"raw_ec2_{codice}.csv"

        print(f"[{i}/{totale_regioni}] {codice} — {nome}")
        try:
            scarica_listino(url, destinazione)
            riepilogo_ok.append(codice)
        except requests.exceptions.RequestException as e:
            print(f"  ERRORE: {e}")
            riepilogo_errori.append(codice)

        # Piccola pausa per non martellare l'endpoint
        time.sleep(0.5)

    print("\n--- Riepilogo ---")
    print(f"Scaricate correttamente: {len(riepilogo_ok)}/{totale_regioni}")
    if riepilogo_errori:
        print(f"Fallite: {riepilogo_errori}")


if __name__ == "__main__":
    print(f"Scaricamento listini EC2 per {len(AWS_REGIONS)} region in corso...\n")
    scarica_tutte_le_region(AWS_REGIONS, OUTPUT_DIR)
    print(f"\nCompletato. File salvati in: {OUTPUT_DIR.resolve()}")