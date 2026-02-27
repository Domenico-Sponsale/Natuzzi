import requests
import re
import os

print(
    "Segui questo sito: https://www.oracle.com/java/technologies/downloads/\nCerca la versione per Windows\nCopia il link del download che si trova prima del login forzato da Oracle\nIncollalo in seguito"
)

BASE_URL = "https://javadl.oracle.com/webapps/download/GetFile/1.8.0_{0}-b{1}/{2}/windows-i586/{3}"
GIVEN_URL = input("URL preso dal link di Java: ")
POLISHED_URL = re.split("https", GIVEN_URL)
PARSED_URL = f"https{POLISHED_URL[-1]}"
ARGS_LIST = re.split("/", PARSED_URL)

VER_AND_BUILD = ARGS_LIST[-3]
ENCRYPTION_KEY = ARGS_LIST[-2]
NAME = ARGS_LIST[-1]
COMBINE_WITH_BASE = BASE_URL.format(
    re.split("(?<=u)(.*?)(?=-)", VER_AND_BUILD)[-2],
    re.split("b", VER_AND_BUILD)[-1],
    ENCRYPTION_KEY,
    NAME,
)
print(COMBINE_WITH_BASE)
path = os.path.expandvars(f"%USERPROFILE%/Downloads/{NAME}")
os.makedirs(os.path.dirname(path), exist_ok=True)
with requests.get(COMBINE_WITH_BASE, stream=True) as r:
    r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
