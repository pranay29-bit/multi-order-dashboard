from abc import ABC, abstractmethod


class BrokerSession(ABC):
    broker_name = "base"

    def __init__(self, app_credentials: dict, account_creds: dict):
        self.app_credentials = app_credentials
        self.account_creds = account_creds
        self.label = account_creds.get("label", "unknown")
        self.client = None
        self.logged_in = False
        self.last_error = None

    @abstractmethod
    def login(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, symbol: str, exchange: str, transaction_type: str,
                     quantity: int, order_type: str, product: str, price: float = 0) -> dict:
        raise NotImplementedError
