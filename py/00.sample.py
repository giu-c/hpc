import pandas as pd
from pathlib import Path

# ==============================================================================
# COSTANTI DI CONFIGURAZIONE
# ==============================================================================
DATASET = Path('hpc.csv')  # File CSV di input ⚠️IMPOSTARE NOME DEL FILE E PERCORSO CORRETTO⚠️
SKIPROWS = 0                          # Righe da saltare (0 se non ha metadati iniziali)
N_SAMPLES = 30                        # Numero di osservazioni da campionare
LIMIT_MAX = None                      # Limite riga file originale. Se None, usa l'intera lunghezza del dataset.
RANDOM_STATE = None                   # Seed per la riproducibilità (imposta a None per campioni sempre diversi)
OUTPUT_FILE = 'sample.csv'        # Nome del file CSV di output
# ==============================================================================

def data_sampling():
    print(f"\nCaricamento del dataset: '{DATASET}'...\n")
    try:
        # Carica il dataset escludendo le righe di metadati iniziali (skiprows)
        df = pd.read_csv(DATASET, skiprows=SKIPROWS)
        lunghezza_effettiva = len(df)
        print(f"\nDataset caricato correttamente. Righe di dati disponibili (dopo skiprows): {lunghezza_effettiva}\n")
        
        # Determina il limite massimo dell'intervallo per il campionamento
        if LIMIT_MAX is None:
            # Di default usa l'intera lunghezza del DataFrame caricato
            limite_destra = lunghezza_effettiva
            print(f"Nessun limite massimo specificato. Utilizzo l'intero dataset (fino all'indice {limite_destra}).\n")
        else:
            # Ricalcola l'indice del DataFrame basandoti sulla riga del file originale e sulle righe saltate
            limite_destra = LIMIT_MAX - SKIPROWS - 1
            
            # Controllo di sicurezza per evitare indici fuori intervallo o negativi
            if limite_destra > lunghezza_effettiva:
                print(f"Attenzione: Il limite specificato ({LIMIT_MAX}) supera le righe del file. Uso {lunghezza_effettiva}.\n")
                limite_destra = lunghezza_effettiva
            elif limite_destra <= 0:
                raise ValueError("Il limite massimo specificato è troppo piccolo rispetto alle righe saltate (skiprows).\n")
            
            print(f"Intervallo filtrato: estrazione attiva dall'indice 0 all'indice {limite_destra} (corrispondente alla riga {LIMIT_MAX} del file).\n")

        # Applica lo slicing sul sottoinsieme di dati desiderato
        df_subset = df.iloc[0:limite_destra]
        
        # Verifica se ci sono abbastanza righe per effettuare il campionamento richiesto
        if len(df_subset) < N_SAMPLES:
            raise ValueError(f"Impossibile campionare {N_SAMPLES} righe: l'intervallo filtrato contiene solo {len(df_subset)} righe.\n")
            
        # Campionamento casuale
        df_sample = df_subset.sample(n=N_SAMPLES, random_state=RANDOM_STATE)
        
        # Salvataggio su file
        df_sample.to_csv(OUTPUT_FILE, index=False)
        print(f"Campionamento completato con successo! Generato il file '{OUTPUT_FILE}' con {N_SAMPLES} record.\n")
        
    except FileNotFoundError:
        print(f"Errore: Il file '{DATASET}' non è stato trovato nella directory corrente.\n")
    except Exception as e:
        print(f"Si è verificato un errore durante l'esecuzione: {e}\n")

if __name__ == '__main__':
    data_sampling()