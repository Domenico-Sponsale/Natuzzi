import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
import re
import logging

logging.basicConfig(
    filename="gestione_orari.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class GestioneOrari:
    def __init__(self, window: tk.Tk):
        logging.info("Inizializzazione UI")
        self.window = window
        self.window.title("Gestore Orari Plant")
        
        self.entry_plant = tk.StringVar()
        self.directory_specifica = ""
        self.file_json = ""

        self.plants = {
            "Laterza": r"\\san\MultiUser$\Gestione Monitor UI\Laterza",
            "Ginosa": r"\\san\MultiUser$\Gestione Monitor UI\Ginosa",
            "Lamartella": r"\\san\MultiUser$\Gestione Monitor UI\Lamartella",
            "Iesce1": r"\\san\MultiUser$\Gestione Monitor UI\Iesce1",
            "Iesce2": r"\\san\MultiUser$\Gestione Monitor UI\Iesce2",
            "LaGraviscella": r"\\san\MultiUser$\Gestione Monitor UI\LaGraviscella",
        }

        self.giorni_settimana = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        self.entries = {}

        self.setup_ui()

    @staticmethod
    def valida_orario(orario):
        return re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", orario) is not None

    def setup_ui(self):
        logging.info("Configurazione UI")
        frame_top = tk.Frame(self.window)
        frame_top.pack(pady=10)

        tk.Label(frame_top, text="Seleziona Plant:").pack(side=tk.LEFT)
        plant_menu = ttk.Combobox(frame_top, textvariable=self.entry_plant, values=list(self.plants.keys()))
        plant_menu.pack(side=tk.LEFT, padx=10)
        plant_menu.bind("<<ComboboxSelected>>", self.update_directory)

        self.tab_control = ttk.Notebook(self.window)
        self.tabs = {}

        for giorno in self.giorni_settimana:
            tab = ttk.Frame(self.tab_control)
            self.tab_control.add(tab, text=giorno)
            self.tabs[giorno] = tab
            self.create_day_tab(tab, giorno)

        self.tab_control.pack(expand=1, fill="both")
        
        tk.Button(self.window, text="Salva Orari", command=self.salva_orari).pack(pady=20)

    def create_day_tab(self, tab, giorno):
        frame = tk.Frame(tab)
        frame.pack(pady=10)
        
        self.entries[giorno] = {}
        for label in ["Chiusura", "Standby", "Riavvio"]:
            row = tk.Frame(frame)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"Ora di {label}:").pack(side=tk.LEFT, padx=5)
            entry = tk.Entry(row)
            entry.pack(side=tk.RIGHT, padx=5)
            self.entries[giorno][label.lower()] = entry

    def update_directory(self, event=None):
        selected_plant = self.entry_plant.get()
        logging.info(f"Plant selezionato: {selected_plant}")
        self.directory_specifica = self.plants.get(selected_plant, "")
        self.file_json = os.path.join(self.directory_specifica, "orari.json")
        self.carica_orari()

    def carica_orari(self):
        logging.info(f"Caricamento orari da {self.file_json}")
        if not os.path.exists(self.directory_specifica):
            os.makedirs(self.directory_specifica, exist_ok=True)
        
        if os.path.exists(self.file_json):
            try:
                with open(self.file_json, "r") as file:
                    orari = json.load(file)
                    for giorno in self.giorni_settimana:
                        for key in ["chiusura", "standby", "riavvio"]:
                            self.entries[giorno][key].delete(0, tk.END)
                            self.entries[giorno][key].insert(0, orari.get(giorno, {}).get(key, ""))
            except Exception as e:
                logging.error(f"Errore nel caricamento JSON: {e}")
                messagebox.showerror("Errore", f"Errore nel caricamento del file JSON: {e}")
        else:
            logging.warning("File JSON non trovato, creazione predefinita")
            default_orari = {giorno: {"chiusura": "18:00", "standby": "12:00", "riavvio": "03:00"} for giorno in self.giorni_settimana}
            with open(self.file_json, "w") as file:
                json.dump(default_orari, file, indent=4)
            self.carica_orari()

    def salva_orari(self):
        logging.info("Salvataggio orari")
        orari = {}
        for giorno in self.giorni_settimana:
            orari[giorno] = {}
            for key in ["chiusura", "standby", "riavvio"]:
                valore = self.entries[giorno][key].get()
                if not self.valida_orario(valore):
                    logging.error(f"Formato orario non valido per {giorno} - {key.capitalize()}")
                    messagebox.showerror("Errore", f"Formato orario non valido per {giorno} - {key.capitalize()}.")
                    return
                orari[giorno][key] = valore
        
        try:
            with open(self.file_json, "w") as file:
                json.dump(orari, file, indent=4)
            logging.info("Orari salvati correttamente")
            messagebox.showinfo("Conferma", "Orari salvati correttamente!")
        except Exception as e:
            logging.error(f"Errore nel salvataggio JSON: {e}")
            messagebox.showerror("Errore", f"Errore nel salvataggio del file JSON: {e}")

if __name__ == "__main__":
    logging.info("Avvio applicazione")
    window = tk.Tk()
    app = GestioneOrari(window)
    window.iconbitmap("C:/Users/dsponsale/OneDrive - Natuzzi SpA/Immagini/N.ico")
    window.resizable(False, False)
    window.mainloop()
    logging.info("Applicazione terminata")
