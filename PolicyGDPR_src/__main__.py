import re
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from colorama import init, Fore

# Inizializza il supporto ai colori nel terminale
init(autoreset=True)

# Lista delle aziende per cui generare il build
companies = ["Natuzzi", "Nacon", "Natco"]

TEMPLATE_FILE = "natuzzi.py"  # File sorgente da usare come template base
paths: list[str] = []  # Percorsi degli eseguibili generati
lock = Lock()  # Lock per accesso thread-safe alla lista paths


def read_template():
    """Legge il contenuto del file template e lo restituisce come stringa"""
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_company(company: str):
    """Esegue la build per una singola azienda"""
    try:
        print(Fore.YELLOW + f"▶️ Compilo per {company}...\n")

        # 1. Genera file sorgente personalizzato
        customized_code = read_template().replace("__COMPANY__", company)

        if company.lower() == "natuzzi":
            customized_code = customized_code.replace(
                'btn_lang.config(text=texts["btn_lang"][lang], state=tk.DISABLED)',
                'btn_lang.config(text=texts["btn_lang"][lang])',
            )

        temp_file = f"natuzzi_{company.lower()}.py"

        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(customized_code)

        # Crea cartelle dist e work separate per sicurezza
        dist_path = f"./PolicyGDPR_{company}"
        work_path = f"./PolicyGDPR_{company}/build"

        os.makedirs(dist_path, exist_ok=True)
        os.makedirs(work_path, exist_ok=True)

        # 2. Compila con PyInstaller
        process = subprocess.Popen(
            [
                "venv/Scripts/pyinstaller.exe",
                "--onefile",
                "--noconsole",
                f"--distpath={dist_path}",
                f"--workpath={work_path}",
                "--icon=../assets/i.ico",
                f"--specpath=PolicyGDPR_{company}",
                "--hidden-import=numpy",
                "--hidden-import=pandas",
                "--name=PolicyGDPR",
                f"--add-data=./pdf/gdpr.pdf;.",
                f"--add-data=./pdf/gdpr_en.pdf;.",
                "--add-data=../assets/Logo no sigillo_BLACK.png;.",
                "--add-data=../assets/.env;.",
                "--add-data=../assets/i.ico;.",
                "--add-data=../assets/Cartel1.xlsx;.",
                temp_file,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # 3. Output realtime colorato
        while True:
            output = process.stdout.readline() # type: ignore
            if output == "" and process.poll() is not None:
                break

            if output:
                line = output.strip()
                prefix = f"[{company}] "

                if re.search(r"ERROR", line):
                    print(Fore.RED + prefix + line)
                elif re.search(r"WARNING", line):
                    print(Fore.YELLOW + prefix + line)
                else:
                    print(Fore.GREEN + prefix + line)

        if process.returncode == 0:
            print(Fore.GREEN + f"✅ Build completata per {company}")
        else:
            print(Fore.RED + f"❌ Errore nella build per {company}")

        exe_path = os.path.abspath(
            f"{dist_path}/PolicyGDPR.exe"
        )

        # Accesso protetto alla lista condivisa
        with lock:
            paths.append(exe_path)

        # Rimuove file temporaneo specifico
        if os.path.exists(temp_file):
            os.remove(temp_file)

    except Exception as e:
        print(Fore.RED + f"❌ Errore per {company}: {e}")


def generate_build():
    """Esegue le build in parallelo"""
    with ThreadPoolExecutor(max_workers=len(companies)) as executor:
        futures = [
            executor.submit(build_company, company)
            for company in companies
        ]

        for future in as_completed(futures):
            future.result()


def cleanup():
    """Rimuove eventuali cartelle temporanee generali"""
    try:
        if os.path.exists("__pycache__"):
            shutil.rmtree("__pycache__")
    except Exception as e:
        print(e)


def print_paths():
    """Stampa i percorsi degli eseguibili generati"""
    print(Fore.CYAN + "\n📦 Eseguibili generati:")

    for path in paths:
        company_name = path.split(os.sep)[-2]

        print(
            Fore.CYAN
            + f"{company_name}: "
            + f"\033]8;;file:///{path}\033\\{path}\033]8;;\033\\"
        )


if __name__ == "__main__":
    generate_build()   # Build parallela
    cleanup()          # Pulizia
    print_paths()      # Output finale
