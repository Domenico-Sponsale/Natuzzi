import base64
import datetime
import getpass
import locale
import os
import socket
import subprocess
import sys
import tkinter as tk
from tkinter import Canvas, Scrollbar
from typing import Any

import fitz  # type: ignore
import keyboard
import pandas as pd
import requests
import win32net
from dotenv import load_dotenv
from PIL import Image, ImageTk, UnidentifiedImageError
import winreg
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# --- Utils ---

def resource_path(relative_path: str):
    """Prende il path dei files incorporati nell'eseguibile"""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath("./assets_debug")
    return os.path.join(base_path, relative_path)


load_dotenv(dotenv_path=resource_path(".env"))

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
FILE_TO_DELETE = sys.executable
LOG_FILE_PATH = r"\\san\main\PolicyGDPR"
SERVICE_EMAIL = os.getenv("SERVICE_EMAIL")

PDF_FILES = {"it": "gdpr.pdf", "en": "gdpr_en.pdf"}

company = "__COMPANY__"

texts = {
    "top_right_text": {
        "it": f"{company} S.p.A. - Autorizzati al trattamento dati (Reg. UE 2016/679)",
        "en": f"{company} S.p.A. - Authorized to process data (EU Reg. 2016/679)",
    },
    "bottom_left_label": {
        "it": "*Leggere l'intera informativa per proseguire",
        "en": "*Read the entire notice to continue",
    },
    "bottom_right_button": {"it": "Per presa visione", "en": "For viewing"},
    "window_title": {
        "it": "Invia Email con Microsoft - Utente di servizio",
        "en": "Send Email with Microsoft - Service User",
    },
    "btn_back": {"it": "Indietro", "en": "Back"},
    "btn_forward": {"it": "Avanti", "en": "Next"},
    "btn_lang": {"it": "EN", "en": "IT"},
}


# --- Funzioni core ---


def create_log_attachment():
    locale.setlocale(locale.LC_TIME, "")
    timestamp = datetime.datetime.now().strftime("%d-%B-%Y")
    filename = f"{getpass.getuser()}_{timestamp}.txt"
    filepath = os.path.join(LOG_FILE_PATH, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(
            f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')};"
            f"{socket.gethostname()};{os.environ.get('USERDOMAIN')};{getpass.getuser()}"
        )


def get_application_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data: dict[str, Any] = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    response = requests.post(url, headers=headers, data=data, timeout=10)

    if response.status_code != 200:
        print("Errore nel recupero del token:")
        print(response.status_code)
        print(response.text)
        response.raise_for_status()

    token = response.json().get("access_token")
    return token


def name(username: str):

    n: str = str()

    # Ottieni il dominio
    domain = os.environ.get("USERDOMAIN")

    # Ottieni info utente da AD
    info = win32net.NetUserGetInfo(domain, username, 2)
    full_name: str = info["full_name"].strip()

    if "(" in full_name and ")" in full_name:
        # Rimuove l'ultima parola
        n = " ".join(full_name.split(" ")[:-1])
    else:
        n = full_name
    return n


def get_email():
    result = subprocess.run(["whoami", "/upn"], capture_output=True, text=True)
    email = result.stdout.strip()
    return email

def show_loading_screen():
    global loading_window
    loading_window = tk.Toplevel(root)
    loading_window.attributes("-fullscreen", True)
    loading_window.title("Attendere...")
    # loading_window.geometry("300x120")
    # loading_window.resizable(False, False)
    loading_window.grab_set()  # blocca interazione con la finestra principale
    loading_window.attributes("-topmost", True)

    
    center_frame = tk.Frame(loading_window)
    center_frame.pack(expand=True, fill="both")


    tk.Label(
        center_frame,
        text="Invio in corso...\nAttendere qualche secondo.",
        font=("Arial", 12),
        anchor="center",
        justify="center"
    ).pack(expand=True)

    # Impedisce la chiusura della finestra
    loading_window.protocol("WM_DELETE_WINDOW", lambda: None)
    
    loading_window.update_idletasks()
    loading_window.update()


def hide_loading_screen():
    global loading_window
    if loading_window:
        loading_window.destroy()
        loading_window = None

def send_mail_from_service(current_lang):
    show_loading_screen()
    
    root.update_idletasks()
    root.update()

    token = get_application_token()
    to_email = get_email()
    subject = "Invio Informativa GDPR"
    body = f"""Gentile {name(getpass.getuser())},

La informiamo che in allegato è disponibile la nostra Informativa ai sensi del Regolamento UE 2016/679.

Con la presente, confermiamo inoltre l’avvenuta presa visione da parte Sua della Policy sulla protezione dei dati personali.

La presente comunicazione è generata automaticamente, si prega di non rispondere a questa email.

Cordiali saluti,
Natuzzi

"""
    attachment_path = make_pdf_attachment(current_lang)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    message: dict[str, Any] = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        }
    }
    if attachment_path:
        with open(attachment_path, "rb") as f:
            attachment_content = base64.b64encode(f.read()).decode()
        message["message"]["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": os.path.basename(attachment_path),
                "contentBytes": attachment_content,
                "contentType": "text/plain",
            }
        ]
    send_url = f"https://graph.microsoft.com/v1.0/users/{SERVICE_EMAIL}/sendMail"
    try:
        resp = requests.post(send_url, headers=headers, json=message, timeout=10)
        create_log()
        make_reg_entry()
        resp.raise_for_status()
        hide_loading_screen()
        root.destroy()
        run_cleanup_and_exit()
    except Exception as e:
        print(e)


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
    timestamp = datetime.datetime.now().strftime("%d-%b-%Y")
    filename = f"{getpass.getuser()}_{timestamp}.txt"
    filepath = os.path.join(LOG_FILE_PATH, filename)  # type: ignore

    with open(filepath, "w", encoding="utf-8") as f:  # type: ignore
        f.write(
            f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')};"
            f"{socket.gethostname()};{os.environ.get('USERDOMAIN')};{getpass.getuser()}"
        )


def run_cleanup_and_exit():
    exe_path = FILE_TO_DELETE
    batch_path = exe_path + "_cleanup.bat"
    pdf_path = "./PolicyGDPR_*.pdf"
    batch_content = f"""@echo off
timeout /t 3 /nobreak >nul
del "{exe_path}"
timeout /t 3 /nobreak >nul
del /q /f "{pdf_path}"
del /q /f "%USERPROFILE%\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\PolicyGDPR*""
timeout /t 3 /nobreak >nul
rd /s /q "%localappdata%\\PolicyGDPR*"
timeout /t 3 /nobreak >nul
del "%~f0"
"""

    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)

    # Lancia il batch senza bloccare il Python script
    # pylint: disable=consider-using-with
    subprocess.Popen(
        batch_path, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # Chiudi il programma Python
    sys.exit()


def check_user_in_xlsx():

    lista_utenze_xlsx: dict[str, str] = {}
    username = str()
    today = str()
    df = pd.read_excel(resource_path("Cartel1.xlsx"))
    for _, row in df.iterrows():
        username = str(row["nome"])
        today = str(row["data"])
        today = today.split(" ", maxsplit=1)[0].replace("-", "/")
        lista_utenze_xlsx[username] = today
    return lista_utenze_xlsx


def make_pdf_attachment(current_lang):
    current_user = getpass.getuser()
    username = name(current_user)
    pdf_path = resource_path(PDF_FILES[current_lang.get()])
    output_path = f"./PolicyGDPR_{username.replace(" ","_")}.pdf"

    # Apri PDF
    doc = fitz.open(pdf_path)
    last_page = doc[-1]

    # Coordinate pagina in pt
    page_width, page_height = last_page.rect.width, last_page.rect.height

    # Posizione del rettangolo stimata (basata sull'immagine)
    # Regola questi valori se il testo non è centrato nel rettangolo
    x_pos = page_width - 200
    y_pos = page_height - 150

    # Testo da inserire
    # users = check_user_in_xlsx()
    users=list()
    if current_user in users:
        today = users[current_user]
    else:
        today = datetime.datetime.now().strftime("%d/%m/%Y")
    text = f"{today}\n{username}"

    # Inserimento del testo
    last_page.insert_text(
        (x_pos, y_pos),
        text.upper(),
        fontsize=10,
        fontname="helv",
        color=(0, 0, 0),
        lineheight=2,
    )

    # Salvataggio
    doc.save(output_path)
    doc.close()

    return output_path


def make_reg_entry():
    # 1. Definire i parametri necessari
    chiave_registro = r"Software\PolicyGDPR"
    valore_nome = "Visione"
    valore_dati = "1"
    valore_tipo = winreg.REG_SZ  # Tipo di valore (Stringa)

    try:
        # 2. Aprire o creare la chiave
        # `winreg.OpenKeyEx` o `winreg.CreateKeyEx` aprono la chiave
        # `winreg.KEY_WRITE` specifica l'accesso in scrittura
        chiave = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,  # Hive principale (es. HKEY_CURRENT_USER)
            chiave_registro,
            0,
            winreg.KEY_WRITE,
        )

        # 3. Impostare o modificare un valore
        # `winreg.SetValueEx` crea o aggiorna il valore specificato
        winreg.SetValueEx(chiave, valore_nome, 0, valore_tipo, valore_dati)

        # 4. Chiudere la chiave
        winreg.CloseKey(chiave)

        print("Valore del registro modificato con successo!")

    except Exception as e:
        print(f"Errore durante la modifica del registro: {e}", file=sys.stderr)


def check_reg_entry():
    chiave_registro = r"Software\PolicyGDPR"
    valore_nome = "Visione"

    try:
        # 1. Prova ad aprire la chiave in sola lettura
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, chiave_registro, 0, winreg.KEY_READ
        ) as chiave:
            try:
                # 2. Tenta di leggere il valore specificato
                valore, tipo = winreg.QueryValueEx(chiave, valore_nome)
                print(f"✅ Chiave trovata: {chiave_registro}\\{valore_nome} = {valore}")
                return True
            except FileNotFoundError:
                # La chiave esiste, ma il valore no
                print(f"⚠️ Chiave trovata, ma il valore '{valore_nome}' non esiste.")
                return False

    except FileNotFoundError:
        # La chiave non esiste affatto
        print(f"❌ La chiave '{chiave_registro}' non esiste.")
        return False


# --- GUI e logica applicazione ---


def main():
    """
    Avvia l'interfaccia principale del programma per la visualizzazione del PDF.

    - Esegue un server in un thread separato per eventuali operazioni in background.
    - Crea e configura la finestra principale (`root`) con interfaccia fullscreen.
    - Inizializza le variabili globali e i componenti GUI: pulsanti, etichette, canvas, scrollbar e contenitori.
    - Definisce funzioni interne per il caricamento del PDF, il rendering delle pagine, la gestione dello scroll,
      il cambio lingua e l’aggiornamento dinamico dell’interfaccia.
    - Gestisce la navigazione tra le pagine del PDF e abilita un controllo dell’interazione utente
      tramite lettura completa prima dell’abilitazione dell’azione finale.
    - Inizia caricando il PDF e visualizzando la prima pagina, poi avvia il ciclo principale dell'app Tkinter.
    """
    global root
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    current_lang = tk.StringVar(value="it")
    root.title(texts["window_title"][current_lang.get()])
    # root.geometry("1000x800")
    root.iconbitmap(resource_path("i.ico"))

    current_page = 0
    pdf_doc = None
    total_pages = 0
    read_pages = []

    konami_sequence = [
        "Up",
        "Up",
        "Down",
        "Down",
        "Left",
        "Right",
        "Left",
        "Right",
        "b",
        "a",
    ]
    konami_sequence = [k.lower() for k in konami_sequence]

    global input_index
    input_index = 0

    def on_resize(event):
        root.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def on_key(event: tk.Event):
        global input_index

        key = event.keysym.lower()

        expected_key = konami_sequence[input_index]

        if key == expected_key:
            input_index += 1
            if input_index == len(konami_sequence):
                cleanup()
                root.destroy()
        else:
            input_index = min(input_index, 0)

    def disable_close():
        pass

    def disable_alt_f4(_=None):
        return "break"

    root.protocol("WM_DELETE_WINDOW", disable_close)
    root.bind_all("<Alt-F4>", disable_alt_f4(_=None))
    root.bind_all("<Key>", on_key)
    root.bind("<Configure>", on_resize)

    # Blocca combinazioni di sistema
    keyboard.block_key("windows")
    keyboard.block_key("esc")
    keyboard.add_hotkey("alt+tab", lambda: None, suppress=True)
    keyboard.add_hotkey("ctrl+esc", lambda: None, suppress=True)
    keyboard.add_hotkey("ctrl+shift+esc", lambda: None, suppress=True)
    keyboard.add_hotkey("alt+f4", lambda: None, suppress=True)
    keyboard.add_hotkey("ctrl+alt+del", lambda: None, suppress=True)

    def cleanup():
        # Sblocca i tasti al termine
        keyboard.unhook_all_hotkeys()
        keyboard.unblock_key("windows")
        keyboard.unblock_key("esc")

    def load_pdf():
        """
        Carica il file PDF corrispondente alla lingua selezionata.

        - Apre il PDF dal percorso definito in `PDF_FILES` in base alla lingua corrente.
        - Imposta il numero totale di pagine.
        - Inizializza lo stato di lettura di ogni pagina come non letta.
        """

        nonlocal pdf_doc, total_pages, read_pages
        pdf_doc = fitz.open(resource_path(PDF_FILES[current_lang.get()]))
        total_pages = len(pdf_doc)
        read_pages[:] = [False] * total_pages

    def toggle_language():
        """
        Cambia la lingua dell'interfaccia tra italiano e inglese.

        - Inverte il valore di `current_lang` tra "it" e "en".
        - Ricarica il PDF, reimposta la visualizzazione alla prima pagina e aggiorna i testi visibili.
        """
        current_lang.set("en" if current_lang.get() == "it" else "it")
        load_pdf()
        render_page(0)
        canvas.yview_moveto(0)
        update_texts()

    top_frame = tk.Frame(root)
    top_frame.pack(fill=tk.X, padx=20, pady=10)

    try:
        logo_img = Image.open(resource_path("Logo no sigillo_BLACK.png")).resize(
            (300, 60)
        )
        logo_photo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(top_frame, image=logo_photo)
        logo_label.image = logo_photo  # evita che venga garbage-collected
        logo_label.pack(side=tk.LEFT)
    except (FileNotFoundError, OSError, UnidentifiedImageError) as e:
        print(f"[LOGO] Impossibile caricare il logo: {e}")

    label_top_right = tk.Label(top_frame, font=("Arial", 14))
    label_top_right.pack(side=tk.RIGHT)

    btn_lang = tk.Button(
        root, text=texts["btn_lang"][current_lang.get()], command=toggle_language
    )
    btn_lang.pack(anchor="ne", padx=20)

    center_frame = tk.Frame(root)
    center_frame.pack(fill=tk.BOTH, expand=True, padx=20)

    canvas = Canvas(center_frame)
    scroll_y = Scrollbar(center_frame, orient="vertical", command=canvas.yview)
    scroll_y.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.configure(yscrollcommand=scroll_y.set)

    pdf_container = tk.Frame(canvas)
    pdf_container.bind(
        "<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox("all"))
    )
    canvas_frame_id = canvas.create_window((0, 0), window=pdf_container, anchor="n")

    image_label = tk.Label(pdf_container)
    image_label.pack(anchor="center")

    def render_page(index: int):
        """
        Carica e visualizza una pagina del PDF come immagine centrata nell'interfaccia grafica.

        - Imposta la pagina corrente su quella indicata da `index`.
        - Converte la pagina del PDF in un'immagine ad alta risoluzione.
        - Rimuove eventuali widget precedenti dal contenitore e mostra la nuova immagine.
        - Aggiorna la configurazione del canvas per adattare lo scroll e la dimensione della pagina.
        - Richiama `update_buttons()` per aggiornare lo stato dell'interfaccia.
        """
        nonlocal current_page
        current_page = index
        page = pdf_doc.load_page(index)  # type: ignore
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))  # type: ignore
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)  # type: ignore
        photo = ImageTk.PhotoImage(img)
        for widget in pdf_container.winfo_children():
            widget.destroy()
        img_label = tk.Label(pdf_container, image=photo, bg="white")
        img_label.image = photo  # type: ignore
        img_label.pack(pady=20)
        canvas.itemconfig(canvas_frame_id, width=canvas.winfo_width())
        canvas.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        update_buttons()

    def update_buttons():
        """
        Aggiorna lo stato e il testo dei bottoni e delle etichette dell'interfaccia grafica.

        Questa funzione viene utilizzata per abilitare/disabilitare i bottoni di navigazione
        e per aggiornare le etichette e i testi visibili in base alla lingua corrente
        e allo stato di lettura delle pagine.

        Comportamento:
            - Abilita il bottone "Indietro" (`btn_back`) se non si è alla prima pagina.
            - Abilita il bottone "Avanti" (`btn_forward`) solo se la pagina corrente è stata letta e non è l'ultima.
            - Abilita il bottone "Per presa visione" (`btn_view`) solo se tutte le pagine sono state lette.
            - Aggiorna il testo delle etichette e dei bottoni in base alla lingua selezionata (`current_lang`).
            - Aggiorna il titolo della finestra principale.

        Dipendenze:
            - Variabili globali: `current_lang`, `current_page`, `total_pages`, `read_pages`, `texts`
            - Oggetti GUI esterni: `btn_back`, `btn_forward`, `btn_view`, `btn_lang`,
            `label_top_right`, `label_bottom`, `root`

        Nota:
            Assicura che l'interfaccia sia coerente con lo stato della lettura e la lingua corrente.
        """
        lang = current_lang.get()
        btn_back.config(state=tk.NORMAL if current_page > 0 else tk.DISABLED)
        btn_forward.config(
            state=(
                tk.NORMAL
                if current_page < total_pages - 1 and read_pages[current_page]
                else tk.DISABLED
            )
        )
        btn_view.config(state=tk.NORMAL if all(read_pages) else tk.DISABLED)
        label_top_right.config(text=texts["top_right_text"][lang])
        label_bottom.config(text=texts["bottom_left_label"][lang])
        btn_back.config(text=texts["btn_back"][lang])
        btn_forward.config(text=texts["btn_forward"][lang])
        btn_view.config(text=texts["bottom_right_button"][lang])
        root.title(texts["window_title"][lang])  # type: ignore
        btn_lang.config(text=texts["btn_lang"][lang], state=tk.DISABLED)

    def on_scroll(*args: str):  # type: ignore
        """
        Gestisce lo scroll verticale del canvas e aggiorna lo stato della pagina.

        Questa funzione viene invocata durante eventi di scorrimento, ad esempio tramite scrollbar
        o altre interazioni programmatiche. Si occupa di aggiornare la posizione dello scroll del canvas
        e di registrare se l'utente ha raggiunto la fine della pagina visibile.

        Parametri:
            *args: Argomenti variabili passati dall'evento di scorrimento.
                Tipicamente includono un'azione come 'moveto' o 'scroll' e un valore associato.

        Comportamento:
            - Se l'argomento indica un movimento (es. "moveto" o "scroll"), applica lo scroll.
            - Ignora eventuali errori che possono verificarsi durante l'applicazione dello scroll.
            - Dopo l'aggiornamento grafico (`update_idletasks`), controlla la posizione corrente dello scroll:
                - Se lo scroll è vicino al fondo (>= 99%) e la pagina corrente non è ancora segnata come letta,
                segna la pagina come letta e aggiorna i pulsanti dell'interfaccia.
            - (Commentato) È possibile bloccare lo scroll oltre il fondo disattivando l'evento `<MouseWheel>`.

        Note:
            - Usa `canvas.yview()` per ottenere la posizione dello scroll come una tupla (start, end).
            - Richiede che `canvas`, `read_pages`, `current_page` e `update_buttons` siano definiti
              nel contesto esterno.
        """
        try:
            canvas.yview_moveto(args[0]) if args[0] in ("moveto", "scroll") else None  # type: ignore
        except Exception:
            pass
        canvas.update_idletasks()
        _, end = canvas.yview()  # type: ignore
        if end >= 0.99 and 0 <= current_page < len(read_pages):
            if not read_pages[current_page]:
                read_pages[current_page] = True
                update_buttons()

    def _on_mousewheel(event: tk.Event):
        """
        Gestisce lo scroll verticale del canvas tramite la rotella del mouse.

        Questa funzione viene chiamata quando si verifica un evento di scorrimento (mouse wheel).
        Verifica se il contenitore PDF (`pdf_container`) è più alto del canvas visibile, e in tal caso
        permette lo scroll verticale del canvas.

        Parametri:
            event (tk.Event): L'evento di tipo mouse wheel generato da Tkinter,
                            contiene informazioni come la direzione e l'entità dello scroll.

        Comportamento:
            - Se l'altezza del contenuto (`pdf_container`) è maggiore dell'altezza del canvas visibile,
            lo scroll verticale viene applicato.
            - Lo scroll è calcolato in base al delta dell'evento del mouse (tipicamente multipli di 120 su Windows).
        """
        if canvas.winfo_height() < pdf_container.winfo_height():
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    canvas.configure(yscrollcommand=lambda *args: on_scroll(*args))

    label_bottom = tk.Label(root, font=("Arial", 12))
    label_bottom.pack(anchor="w", padx=20, pady=(5, 0))

    bottom_frame = tk.Frame(root)
    bottom_frame.pack(fill=tk.X, pady=10, padx=20)

    def go_back():
        if current_page > 0:
            render_page(current_page - 1)

    def go_forward():
        if current_page < total_pages - 1:
            next_page = current_page + 1
            if not read_pages[next_page]:
                canvas.yview_moveto(0)
            render_page(next_page)

    btn_back = tk.Button(bottom_frame, width=10, command=go_back)
    btn_back.pack(side=tk.LEFT, padx=(0, 10))

    btn_forward = tk.Button(bottom_frame, width=10, command=go_forward)
    btn_forward.pack(side=tk.LEFT)

    credit_text = "".join(
        [
            chr(98),chr(121),chr(58),chr(32),chr(68),
            chr(79),chr(77),chr(69),chr(78),chr(73),
            chr(67),chr(79),chr(32),chr(83),chr(80),
            chr(79),chr(78),chr(83),chr(65),chr(76),chr(69),
        ]
    )

    label_middle = tk.Label(
        bottom_frame,
        text=credit_text,
        font=("Arial", 6, "bold"),
        fg="#cecece",
    )
    label_middle.pack(anchor="center")

    btn_view = tk.Button(
        bottom_frame, width=15, command=lambda: send_mail_from_service(current_lang)
    )
    btn_view.pack(anchor="ne", padx=20)

    def update_texts():
        update_buttons()

    root.after(200, load_pdf)
    root.after(300, lambda: render_page(0))
    root.mainloop()


if __name__ == "__main__":
    try:
        if not check_reg_entry():
            main()
        else:
            run_cleanup_and_exit()
            sys.exit(0)
    except OSError as e:
        if e.winerror == 64:
            sys.exit(0)
