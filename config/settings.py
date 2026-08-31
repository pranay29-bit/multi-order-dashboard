import json
import os
from pathlib import Path

from dotenv import load_dotenv

from core.credential_vault import FirebaseCredentialVault

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ACCOUNTS_FILE = ROOT / "accounts.json"


def using_firebase_vault() -> bool:
    return os.getenv("KOTAK_CREDENTIAL_STORE", "local").lower() == "firebase"


def load_runtime_settings() -> tuple[str, str, str]:
    if not using_firebase_vault():
        return (
            os.getenv("KOTAK_CONSUMER_KEY", ""),
            os.getenv("KOTAK_CONSUMER_SECRET", ""),
            os.getenv("KOTAK_ENV", "prod"),
        )
    application, _ = FirebaseCredentialVault().load_configuration()
    return application["consumer_key"], application["consumer_secret"], application["environment"]


def load_accounts():
    if using_firebase_vault():
        _, accounts = FirebaseCredentialVault().load_configuration()
        return accounts
    if not ACCOUNTS_FILE.exists():
        raise FileNotFoundError(
            "accounts.json not found. Copy accounts.example.json to accounts.json "
            "and fill in your real per-account credentials."
        )
    with open(ACCOUNTS_FILE) as f:
        data = json.load(f)
    return data.get("accounts", [])
