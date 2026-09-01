import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT / "accounts.json"
APP_CONFIG_FILE = ROOT / "app_config.json"


def load_app_config() -> dict:
    """Per-broker app-level credentials, entered via the Settings tab."""
    if not APP_CONFIG_FILE.exists():
        return {}
    with open(APP_CONFIG_FILE) as f:
        return json.load(f)


def save_broker_app_config(broker: str, config: dict) -> None:
    all_config = load_app_config()
    all_config[broker] = config
    with open(APP_CONFIG_FILE, "w") as f:
        json.dump(all_config, f, indent=2)


def load_accounts() -> list:
    if not ACCOUNTS_FILE.exists():
        return []
    with open(ACCOUNTS_FILE) as f:
        data = json.load(f)
    return data.get("accounts", [])


def save_accounts(accounts: list) -> None:
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump({"accounts": accounts}, f, indent=2)


def add_account(account: dict) -> None:
    accounts = load_accounts()
    if any(a["label"] == account["label"] for a in accounts):
        raise ValueError(f"An account labeled '{account['label']}' already exists.")
    accounts.append(account)
    save_accounts(accounts)


def delete_account(label: str) -> None:
    accounts = [a for a in load_accounts() if a["label"] != label]
    save_accounts(accounts)
