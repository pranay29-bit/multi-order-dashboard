import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CONSUMER_KEY = os.getenv("KOTAK_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("KOTAK_CONSUMER_SECRET", "")
KOTAK_ENV = os.getenv("KOTAK_ENV", "prod")

ACCOUNTS_FILE = ROOT / "accounts.json"


def load_accounts():
    if not ACCOUNTS_FILE.exists():
        raise FileNotFoundError(
            "accounts.json not found. Copy accounts.example.json to accounts.json "
            "and fill in your real per-account credentials."
        )
    with open(ACCOUNTS_FILE) as f:
        data = json.load(f)
    return data.get("accounts", [])
