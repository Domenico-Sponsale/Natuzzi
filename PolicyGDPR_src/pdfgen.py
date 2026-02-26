import locale
import os
import socket
import fitz  # type: ignore
import getpass
import pandas as pd
import datetime

PDF_FILES = {"it": "gdpr.pdf", "en": "gdpr_en.pdf"}


def get_From_excel(excel_path: str, sheet_name: str):
    lista_utenze_xlsx = list()

    df = pd.read_excel(excel_path, sheet_name)

    for _, row in df.iterrows():
        try:
            username = str(row["USERID_OK"]).lower().strip()
            name = str(row["Cognome_Nome"]).upper().strip()
            today = str(row["DATA PDF"]).split(" ", 1)[0].replace("-", "/")
            pc_name = str(row["Nomi pc corrispondenti"]).strip()

            # AGGIUNGI correttamente una entry al dizionario
            lista_utenze_xlsx.append({
                "user": username,
                "date": today,
                "PC": pc_name,
                "fullname": name
            })

        except Exception as e:
            print("Errore riga:", e)

    return lista_utenze_xlsx

entries = get_From_excel(
    "assets/DevicesWithInventory_257b657a-49b6-4433-a74f-433da19faaec.xlsx",
    "Foglio1",
)

def make_pdf_attachment(current_lang="it"):
    for entry in entries:
        output_path = f"./users/PolicyGDPR_{entry['user'].replace(' ', '_')}.pdf"
        if entry["PC"] == "SNTVSV530":
            output_path = f"./users/no_pc/PolicyGDPR_{entry['user'].replace(' ', '_')}.pdf"
        # CORRETTO: usa apici singoli dentro l’f-string
        pdf_path = "./BUILDS/natuzzi/gdpr.pdf"

        # Apri PDF
        doc = fitz.open(pdf_path)
        last_page = doc[-1]

        # Coordinate pagina
        page_width, page_height = last_page.rect.width, last_page.rect.height
        x_pos = page_width - 200
        y_pos = page_height - 150

        # Se 'fullname' non esiste, usa user
        fullname = entry.get("fullname", entry["user"]).replace("(GUEST)", "")

        # CORRETTO anche qui: apici singoli nel dizionario
        text = f"{entry['date']}\n{fullname}"

        # Inserimento testo
        last_page.insert_text(
            (x_pos, y_pos),
            text,
            fontsize=10,
            fontname="helv",
            color=(0, 0, 0),
            lineheight=2,
        )

        # Salvataggio
        doc.save(output_path)
        doc.close()
        
def create_log():
    """
    Crea un file di log nella directory di rete specificata.

    - Imposta la localizzazione temporanea per la formattazione della data.
    - Genera un nome file basato sul nome utente e la data corrente nel formato `dd-MMM-YYYY`.
    - Scrive nel file la data e ora correnti, il nome host della macchina, il dominio utente e il nome utente.
    - Il file viene salvato nel percorso definito da `LOG_FILE_PATH`.

    Nota:
    Richiede permessi di scrittura nella directory di rete e accesso alle variabili ambiente utente.
    """

    locale.setlocale(locale.LC_TIME, "")
    for entry in entries:
        filename = f"{entry["user"]}_{entry["date"]}.txt".replace("/", "-")
        filepath = os.path.join("./logs", filename) 
        with open(filepath, "w", encoding="utf-8") as f: 
            f.write( f"{entry["date"]};" f"{entry["PC"]};" f"HQ;" f"{entry["user"]}" )


make_pdf_attachment()
# create_log()
# os.listdir(".")