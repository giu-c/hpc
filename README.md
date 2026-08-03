La versione Python richiesta è la 3.13  

Su VS Code, aprire il terminale nella cartella dove si vuole scaricare il progetto e digitare:
1. git clone https://github.com/giu-c/hpc.git
2. cd hpc
3. python -m pip install --upgrade pip
4. python -m pip install -r requirements.txt
      - ancora meglio sarebbe mollare "pip" e passare a "uv" ma vabbuò...
5. Per replicare l'intera pipeline ETL, eseguire il file "main.py"
      - assicurarsi di essere all'interno del percorso corretto .\hpc\

   
Successivamente, si consiglia di rimuovere i file RAW (+5GB)
