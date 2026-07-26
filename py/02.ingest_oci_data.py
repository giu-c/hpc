#!/usr/bin/env python3
"""
Scarica il listino prezzi Oracle Cloud (OCI) da:
  https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/

e lo appiattisce in un CSV tabellare, una riga per ogni combinazione:
SKU x valuta x fascia di prezzo.

Include due controlli automatici di coerenza:
  1) Conteggio righe attese (calcolato dal JSON) vs righe effettivamente scritte
  2) Confronto casuale di N SKU tra il JSON originale e il CSV generato

Uso:
    pip install requests
    python oracle_price_list_to_csv.py

Output:
    raw_oci.csv
"""

import csv
import random
import sys
import requests
from pathlib import Path

# Definisce il percorso completo
URL = "https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/"
OUTPUT_FILE = Path("data") / "01.raw" / "raw_oci.csv"
N_CAMPIONI_VERIFICA = 30  # quanti SKU controllare a random nel controllo #2

FIELDNAMES = [
    "partNumber",
    "displayName",
    "description",
    "metricName",
    "serviceCategory",
    "currencyCode",
    "model",
    "value",
    "rangeMin",
    "rangeMax",
]


def fetch_data(url: str) -> dict:
    print(f"Scaricamento dati da {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"Ultimo aggiornamento fonte: {data.get('lastUpdated')}")
    print(f"Numero di SKU (items) trovati: {len(data.get('items', []))}")
    return data


def flatten(data: dict):
    """Genera un dict per riga (SKU x valuta x fascia di prezzo)."""
    for item in data.get("items", []):
        base_row = {
            "partNumber": item.get("partNumber", ""),
            "displayName": item.get("displayName", ""),
            "description": item.get("description", ""),
            "metricName": item.get("metricName", ""),
            "serviceCategory": item.get("serviceCategory", ""),
        }
        for loc in item.get("currencyCodeLocalizations", []):
            currency = loc.get("currencyCode", "")
            for price in loc.get("prices", []):
                row = dict(base_row)
                row["currencyCode"] = currency
                row["model"] = price.get("model", "")
                row["value"] = price.get("value", "")
                row["rangeMin"] = price.get("rangeMin", "")
                row["rangeMax"] = price.get("rangeMax", "")
                yield row


def conta_righe_attese(data: dict) -> int:
    """Calcola quante righe DOVREBBERO uscire, contando direttamente nel JSON
    (senza passare dal generatore flatten), come controllo indipendente."""
    totale = 0
    for item in data.get("items", []):
        for loc in item.get("currencyCodeLocalizations", []):
            totale += len(loc.get("prices", []))
    return totale


def controllo_1_conteggio(data: dict, n_righe_scritte: int) -> bool:
    print("\n=== CONTROLLO 1: conteggio righe attese vs scritte ===")
    attese = conta_righe_attese(data)
    print(f"Righe attese (calcolate dal JSON):  {attese}")
    print(f"Righe scritte nel CSV:               {n_righe_scritte}")
    if attese == n_righe_scritte:
        print("OK: i conteggi coincidono.")
        return True
    else:
        print("ATTENZIONE: i conteggi NON coincidono, controllare lo script.")
        return False


def controllo_2_campione_random(data: dict, csv_path: str, n_campioni: int) -> bool:
    print(f"\n=== CONTROLLO 2: confronto random di {n_campioni} SKU (JSON vs CSV) ===")

    items = data.get("items", [])
    if not items:
        print("Nessun item da controllare.")
        return False

    campioni = random.sample(items, min(n_campioni, len(items)))

    # Carica il CSV in memoria indicizzato per (partNumber, currencyCode)
    csv_index = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["partNumber"], row["currencyCode"])
            csv_index.setdefault(key, []).append(row)

    tutto_ok = True
    for item in campioni:
        part_number = item.get("partNumber", "")
        locs = item.get("currencyCodeLocalizations", [])
        if not locs:
            continue
        loc = random.choice(locs)
        currency = loc.get("currencyCode", "")
        prices_json = loc.get("prices", [])

        righe_csv = csv_index.get((part_number, currency), [])

        print(f"\n  SKU: {part_number} | valuta: {currency}")
        print(f"    Prezzi nel JSON: {prices_json}")
        print(f"    Righe trovate nel CSV: {len(righe_csv)}")

        if len(righe_csv) != len(prices_json):
            print("    ATTENZIONE: numero di righe non corrisponde.")
            tutto_ok = False
            continue

        # confronta i valori (ordine potrebbe non coincidere, quindi confronto per insieme)
        valori_json = sorted(str(p.get("value", "")) for p in prices_json)
        valori_csv = sorted(r["value"] for r in righe_csv)

        if valori_json == valori_csv:
            print("    OK: valori coincidono.")
        else:
            print(f"    ATTENZIONE: valori diversi. JSON={valori_json} CSV={valori_csv}")
            tutto_ok = False

    print()
    if tutto_ok:
        print("Controllo 2 superato: tutti i campioni corrispondono.")
    else:
        print("Controllo 2: trovate discrepanze, vedi sopra.")
    return tutto_ok


def main():
    try:
        data = fetch_data(URL)
    except requests.RequestException as e:
        print(f"Errore durante lo scaricamento: {e}", file=sys.stderr)
        sys.exit(1)

    n_rows = 0
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in flatten(data):
            writer.writerow(row)
            n_rows += 1

    print(f"\nFatto. Scritte {n_rows} righe in '{OUTPUT_FILE}'.")

    ok1 = controllo_1_conteggio(data, n_rows)
    ok2 = controllo_2_campione_random(data, OUTPUT_FILE, N_CAMPIONI_VERIFICA)

    print("\n=== RIEPILOGO ===")
    print(f"Controllo 1 (conteggio):        {'OK' if ok1 else 'FALLITO'}")
    print(f"Controllo 2 (campione random):  {'OK' if ok2 else 'FALLITO'}")

    if not (ok1 and ok2):
        sys.exit(2)


if __name__ == "__main__":
    main()
