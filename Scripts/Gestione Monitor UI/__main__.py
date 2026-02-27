import argparse
import os
import time
import datetime
import subprocess
import psutil
import json
import ctypes
import sys
import threading
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import ntplib  # Per la sincronizzazione NTP

FILE_JSON = "orari.json"
url = "http://itandon"

plants = {
    "Laterza": {
        "path": r"\\san\MultiUser$\Gestione Monitor UI\Laterza",
        "ip": "172.28.14.140",
    },
    "Ginosa": {
        "path": r"\\san\MultiUser$\Gestione Monitor UI\Ginosa",
        "ip": "172.28.14.52",  # da definire
    },
    "Lamartella": {
        "path": r"\\san\MultiUser$\Gestione Monitor UI\Lamartella",
        "ip": "172.28.40.139",
    },
    "Iesce1": {
        "path": r"\\san\MultiUser$\Gestione Monitor UI\Iesce1",
        "ip": "172.28.72.139",
    },
    "Iesce2": {
        "path": r"\\san\MultiUser$\Gestione Monitor UI\Iesce2",
        "ip": "172.28.17.139",
    },
    "LaGraviscella": {
        "path": r"\\san\MultiUser$\Gestione Monitor UI\LaGraviscella",
        "ip": "172.28.14.56",  # da definire
    },
}


def setup_logger(plant):
    log_filename = fr"\\san\MultiUser$\Gestione Monitor UI\{plant}\monitor_ui_{plant}.log"
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8"
    )


def leggi_orari(file_json):
    """Legge gli orari per il giorno corrente dal file JSON."""
    try:
        if os.path.exists(file_json):
            with open(file_json, "r") as file:
                orari = json.load(file)
                giorno_attuale = datetime.datetime.today().strftime(
                    "%A"
                )  # Nome del giorno in inglese
                giorni_traduzione = {
                    "Monday": "Lunedì",
                    "Tuesday": "Martedì",
                    "Wednesday": "Mercoledì",
                    "Thursday": "Giovedì",
                    "Friday": "Venerdì",
                    "Saturday": "Sabato",
                    "Sunday": "Domenica",
                }
                giorno_attuale = giorni_traduzione.get(giorno_attuale, giorno_attuale)

                if giorno_attuale in orari:
                    return (
                        orari[giorno_attuale]["chiusura"],
                        orari[giorno_attuale]["standby"],
                        orari[giorno_attuale]["riavvio"],
                    )
                else:
                    logging.warning(f"❌ Nessun orario specificato per {giorno_attuale}.")
                    return None, None, None
        else:
            logging.error("❌ Il file JSON non esiste.")
            return None, None, None
    except json.JSONDecodeError:
        logging.error("❌ Errore nella sintassi del file JSON.")
    except Exception as e:
        logging.error(f"❌ Errore durante la lettura del file JSON: {e}")
        return None, None, None


def avvia_chrome():
    """Avvia Chrome in modalità kiosk"""
    try:
        chrome_process = subprocess.Popen(
            [
                "c:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "--kiosk",
                url,
            ]
        )
        time.sleep(5)
        logging.info("✅ Chrome avviato con successo.")
        return chrome_process.pid
    except Exception as e:
        logging.error(f"❌ Errore nell'avvio di Chrome: {e}")


def chiudi_chrome(pid):
    """Chiudi il processo Chrome"""
    try:
        for process in psutil.process_iter():
            if process.pid == pid:
                process.terminate()
                logging.info("🛑 Chrome chiuso.")
                break
    except Exception as e:
        logging.error(f"❌ Errore nella chiusura di Chrome: {e}")


def standby():
    """Mette il sistema in standby."""
    try:
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
    except Exception as e:
        logging.error(f"❌ Errore nello standby: {e}")


def riavvia_sistema():
    """Riavvia il sistema."""
    try:
        os.system("shutdown /r /t 0")
    except Exception as e:
        logging.error(f"❌ Errore nel riavvio del sistema: {e}")


def sincronizza_orario(ntp, timeout=5):
    """Ottieni l'orario dal server NTP."""
    try:
        client = ntplib.NTPClient()
        response = client.request(host=ntp, timeout=timeout)
        return round(response.tx_time)  # Timestamp Unix
    except Exception as e:
        logging.error(f"⚠️ Errore NTP: {e}\nFallback all'orario della macchina")
        return time.time()  # Fallback all'orario locale


def watch_json(file_json, chrome_pid):
    """Monitoraggio del file JSON e riavvio in caso di modifica."""

    class RestartOnChange(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith("orari.json"):
                logging.info("🔄 Modifica rilevata, riavvio del processo...")
                chiudi_chrome(chrome_pid)
                os.execl(sys.executable, sys.executable, *sys.argv)

    observer = Observer()
    event_handler = RestartOnChange()
    observer.schedule(event_handler, path=os.path.dirname(file_json), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def parse_arguments():
    """Analizza gli argomenti da linea di comando"""
    parser = argparse.ArgumentParser(description="Script per la gestione degli orari.")
    parser.add_argument("-plant", required=True, help="Nome del plant")
    args = parser.parse_args()
    return args.plant


def main():
    try:
        plant = parse_arguments()
        setup_logger(plant)

        if plant not in plants:
            logging.error("❌ Plant non valido.")
            return

        directory = plants[plant]["path"]
        file_json = os.path.join(directory, "orari.json")
        logging.info(fr"📂 Monitoraggio file: {file_json}")

        ora_chiusura, ora_standby, ora_riavvio = leggi_orari(file_json)
        if ora_chiusura and ora_standby and ora_riavvio:
            chrome_pid = avvia_chrome()
            logging.info(f"✅ Chrome avviato con PID {chrome_pid}.")
            ntp_time = sincronizza_orario(plants[plant]["ip"])
            watcher_thread = threading.Thread(
                target=watch_json, args=(file_json, chrome_pid)
            )
            unix = ntp_time
            watcher_thread.daemon = True
            watcher_thread.start()

            while True:
                unix += 1
                ora_attuale = datetime.datetime.fromtimestamp(unix).strftime("%H:%M")
                print(ora_attuale)
                if ora_attuale == ora_chiusura:
                    chiudi_chrome(chrome_pid)
                if ora_attuale == ora_standby:
                    standby()
                if ora_attuale == ora_riavvio:
                    riavvia_sistema()
                time.sleep(1)
        else:
            logging.error("❌ Orari non validi.")
    except Exception as e:
        logging.error(f"❌ Errore nel main: {e}")


if __name__ == "__main__":
    main()
