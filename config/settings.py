import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT / "accounts.json"
APP_CONFIG_FILE = ROOT / "app_config.json"


def load_app_config() -> dict:
    """Consumer key/secret/env, entered via the Settings tab on the site itself."""
    if not APP_CONFIG_FILE.exists():
        return {"consumer_key": "", "consumer_secret": "", "env": "prod"}
    with open(APP_CONFIG_FILE) as f:
        return json.load(f)


def save_app_config(consumer_key: str, consumer_secret: str, env: str) -> None:
    with open(APP_CONFIG_FILE, "w") as f:
        json.dump({"consumer_key": consumer_key, "consumer_secret": consumer_secret, "env": env}, f, indent=2)


def load_accounts() -> list[dict]:
    if not ACCOUNTS_FILE.exists():
        return []
    with open(ACCOUNTS_FILE) as f:
        data = json.load(f)
    return data.get("accounts", [])


def save_accounts(accounts: list[dict]) -> None:
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump({"accounts": accounts}, f, indent=2)


def add_account(account: dict) -> None:
    accounts = load_accounts()
    if any(a["label"] == account["label"] for a in accounts):
        raise ValueError(f"An account labeled '{account['label']}' already exists.")
    accounts.append(account)
    save_accounts(accounts)


def update_account(label: str, updated: dict) -> None:
    accounts = load_accounts()
    for i, a in enumerate(accounts):
        if a["label"] == label:
            accounts[i] = updated
            save_accounts(accounts)
            return
    raise ValueError(f"No account labeled '{label}' found.")


def delete_account(label: str) -> None:
    accounts = [a for a in load_accounts() if a["label"] != label]
    save_accounts(accounts)
