import socket
import struct

def hour(ntp):
    """Recupera l'ora da un server NTP."""
    if not ntp:
        raise ValueError("Il server NTP non è stato immesso, per favore riprovare aggiungendo l'argomento '-ntp <indirizzo>'")
    
    # Creazione dei dati per il protocollo NTP
    ntp_data = bytearray(48)
    ntp_data[0] = 0x1B  # Impostazione del primo byte

    # Porta UDP per NTP
    server_address = (ntp, 123)
    timeout = 5  # Timeout in secondi

    try:
        # Creazione della connessione UDP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
            udp_socket.settimeout(timeout)

            # Invio della richiesta al server NTP
            udp_socket.sendto(ntp_data, server_address)

            # Ricezione della risposta dal server
            ntp_data, _ = udp_socket.recvfrom(48)
    except Exception as e:
        print(f"Errore: {e}")
        return None

    # Estrazione del timestamp dalla risposta
    try:
        int_part = struct.unpack('!I', ntp_data[40:44])[0]
        unix_time = int_part - 2208988800  # Conversione in Unix Time
        return unix_time
    except Exception as e:
        print(f"Errore nell'estrazione del timestamp: {e}")
        return None
