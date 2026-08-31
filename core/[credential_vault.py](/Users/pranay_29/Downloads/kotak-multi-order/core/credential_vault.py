"""Encrypted, server-side storage for Kotak credentials in Cloud Firestore."""

import json
import os
from typing import Any

import firebase_admin
from cryptography.fernet import Fernet, InvalidToken
from firebase_admin import credentials, firestore


class CredentialVaultError(RuntimeError):
    """Raised when the vault cannot safely read or write credentials."""


class FirebaseCredentialVault:
    """Stores encrypted payloads; the encryption key never reaches Firestore."""

    def __init__(self) -> None:
        service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        encryption_key = os.getenv("CREDENTIAL_VAULT_KEY")
        if not service_account or not encryption_key:
            raise CredentialVaultError(
                "Set FIREBASE_SERVICE_ACCOUNT_JSON and CREDENTIAL_VAULT_KEY on the server."
            )

        try:
            app = firebase_admin.get_app()
        except ValueError:
            try:
                app = firebase_admin.initialize_app(
                    credentials.Certificate(json.loads(service_account))
                )
            except (TypeError, ValueError) as error:
                raise CredentialVaultError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid.") from error

        try:
            self._cipher = Fernet(encryption_key.encode())
        except (TypeError, ValueError) as error:
            raise CredentialVaultError("CREDENTIAL_VAULT_KEY is not a valid Fernet key.") from error
        self._db = firestore.client(app)

    def _encrypt(self, payload: dict[str, Any]) -> str:
        return self._cipher.encrypt(json.dumps(payload).encode()).decode()

    def _decrypt(self, encrypted_payload: str) -> dict[str, Any]:
        try:
            return json.loads(self._cipher.decrypt(encrypted_payload.encode()).decode())
        except (InvalidToken, TypeError, ValueError, json.JSONDecodeError) as error:
            raise CredentialVaultError("Stored credential data cannot be decrypted.") from error

    def save_application(self, consumer_key: str, consumer_secret: str, environment: str) -> None:
        self._db.collection("credential_vault").document("kotak_application").set(
            {
                "payload": self._encrypt(
                    {
                        "consumer_key": consumer_key,
                        "consumer_secret": consumer_secret,
                        "environment": environment,
                    }
                )
            }
        )

    def save_account(self, account: dict[str, str]) -> str:
        document = self._db.collection("credential_vault").document()
        document.set(
            {"payload": self._encrypt(account), "created_at": firestore.SERVER_TIMESTAMP}
        )
        return document.id

    def load_configuration(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        application = self._db.collection("credential_vault").document(
            "kotak_application"
        ).get()
        if not application.exists:
            raise CredentialVaultError("No Kotak application credentials have been saved yet.")

        app_payload = self._decrypt(application.to_dict()["payload"])
        accounts = []
        for document in self._db.collection("credential_vault").stream():
            if document.id != "kotak_application":
                accounts.append(self._decrypt(document.to_dict()["payload"]))
        return app_payload, accounts
