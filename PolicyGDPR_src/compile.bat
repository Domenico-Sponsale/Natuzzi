@echo off
setlocal

REM Controllo se Python è installato
where py -V >nul 2>nul
if %errorlevel% neq 0 (
    echo Python non e' installato. Installalo da https://www.python.org/downloads/ e riprova.
    pause
    exit /b
)

REM Controllo se la cartella del virtual environment esiste
if not exist venv (
    for /f "delims=" %%i in ('where python') do set py=%%i
    echo Creo l'ambiente virtuale...
    %py% -m venv .venv
    if %errorlevel% neq 0 (
        echo Errore nella creazione del virtual environment.
        pause
        exit /b
    )

    echo Installo le dipendenze...
    call venv\Scripts\activate
    if exist requirements.txt (
        pip install -r requirements.txt
    ) else (
        echo Nessun file requirements.txt trovato. Nessuna libreria installata.
    )
    py -m pip uninstall -y pathlib
)

REM Attivo l'ambiente virtuale
call venv\Scripts\activate

REM Avvio lo script principale Python
venv\Scripts\python.exe .

pause
