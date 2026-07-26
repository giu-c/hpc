import subprocess
import sys
from pathlib import Path

def run_pipeline():
    # Definisci la cartella contenente gli script
    cartella_py = Path("py")
    file_escluso = "00.sample.py"

    # Verifica che la cartella esista
    if not cartella_py.exists() or not cartella_py.is_dir():
        print(f"Errore: La cartella '{cartella_py}' non esiste.")
        return

    # Trova tutti i file .py, escludi 00.sample.py e ordinali in modo crescente
    scripts = sorted(
        [
            file for file in cartella_py.glob("*.py")
            if file.is_file() and file.name != file_escluso
        ]
    )

    if not scripts:
        print("Nessun file .py trovato da eseguire.")
        return

    print("Inizio esecuzione della pipeline...\n" + "-"*40)

    # Esegui ogni script in ordine
    for script in scripts:
        print(f"Esecuzione di: {script.name}...")
        
        try:
            # sys.executable assicura l'utilizzo del Python corrente (utile con il .venv)
            risultato = subprocess.run(
                [sys.executable, str(script)],
                check=True,          # Solleva un'eccezione se lo script fallisce
                text=True,           # Restituisce output come stringa
                capture_output=False # Mettilo a True se vuoi nascondere l'output a terminale
            )
            print(f"[{script.name}] Completato con successo.\n" + "-"*40)
            
        except subprocess.CalledProcessError as e:
            print(f"\nERRORE: L'esecuzione di {script.name} è fallita (Codice di uscita: {e.returncode}).")
            print("Interruzione della pipeline.")
            break # Ferma la pipeline in caso di errore

if __name__ == "__main__":
    run_pipeline()