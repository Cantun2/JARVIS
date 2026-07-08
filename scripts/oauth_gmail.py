"""OAuth Gmail one-shot — génère secrets/gmail_token.json (scope gmail.readonly).

Prérequis :
  1. Extra Python installé : `pip install -e ".[google]"` (déjà fait).
  2. Un client OAuth « Desktop » Google → fichier téléchargé et placé dans
     secrets/gmail_credentials.json (cf. docs/MANUAL_SETUP.md §2).

Usage (depuis la racine du repo, venv actif) :
  PYTHONUTF8=1 .venv/Scripts/python.exe scripts/oauth_gmail.py

Le script ouvre le navigateur, te fait autoriser l'accès **lecture seule** à Gmail,
puis écrit le jeton autorisé dans secrets/gmail_token.json. HERMES le consomme
via GMAIL_TOKEN_PATH. Aucune permission d'envoi n'est demandée.
"""

from __future__ import annotations

import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS = Path("secrets/gmail_credentials.json")
TOKEN = Path("secrets/gmail_token.json")


def main() -> int:
    if not CREDENTIALS.exists():
        print(f"✗ {CREDENTIALS} introuvable.")
        print("  Crée un client OAuth « Desktop » sur https://console.cloud.google.com/")
        print("  (API Gmail activée), télécharge le JSON et place-le à ce chemin.")
        print("  Détails : docs/MANUAL_SETUP.md §2.")
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
    # Ouvre le navigateur et écoute sur un port local pour le retour OAuth.
    creds = flow.run_local_server(port=0)

    TOKEN.parent.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    print(f"✓ Jeton écrit dans {TOKEN}")
    print("  HERMES peut désormais lire tes mails (lecture seule).")
    print("  Vérifie : PYTHONUTF8=1 .venv/Scripts/python.exe -m jarvis doctor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
