import win32security

# Percorso della cartella
cartella = r"\\san\MultiUSer$"

# Ottenere le informazioni di sicurezza
security_info = win32security.GetFileSecurity(cartella, win32security.DACL_SECURITY_INFORMATION)
dacl = security_info.GetSecurityDescriptorDacl()

# Iterare sugli ACE (Access Control Entries)
print(dacl.GetAceCount())
for i in range(dacl.GetAceCount()):
    print(win32security.LookupAccountSid(None, dacl.GetAce(i)[2]))
#     ace = dacl.GetAce(i)
#     sid = ace[2]
#     # user, domain, _ = win32security.LookupAccountSid(None, sid)
#     print(rf"Utente autorizzato: {domain}\{user}")