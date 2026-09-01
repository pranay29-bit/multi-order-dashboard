from core.brokers.base import BrokerSession

try:
    from kiteconnect import KiteConnect
except ImportError:
    KiteConnect = None

_ORDER_TYPE_MAP = {"MARKET": "MARKET", "LIMIT": "LIMIT"}
_PRODUCT_MAP = {"DELIVERY": "CNC", "INTRADAY": "MIS"}


class ZerodhaSession(BrokerSession):
    broker_name = "zerodha"

    def login(self) -> bool:
        """
        Zerodha requires a fresh access_token generated once a day via their
        browser login redirect — no silent/TOTP-only login for third-party apps.
        This checks that today's access_token (saved on the account) still works.
        """
        if KiteConnect is None:
            self.last_error = "kiteconnect not installed."
            return False
        try:
            api_key = self.account_creds["api_key"]
            access_token = self.account_creds.get("access_token")
            if not access_token:
                self.last_error = "No access_token saved for today. Generate one first (see Accounts tab)."
                return False
            self.client = KiteConnect(api_key=api_key)
            self.client.set_access_token(access_token)
            self.client.profile()  # cheap call to confirm the token actually works
            self.logged_in = True
            return True
        except Exception as e:
            self.last_error = str(e)
            self.logged_in = False
            return False

    def place_order(self, symbol, exchange, transaction_type, quantity, order_type, product, price=0):
        if not self.logged_in or self.client is None:
            return {"success": False, "label": self.label, "error": "Not logged in"}
        try:
            order_id = self.client.place_order(
                variety=self.client.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=_PRODUCT_MAP[product],
                order_type=_ORDER_TYPE_MAP[order_type],
                price=price if order_type == "LIMIT" else None,
                validity=self.client.VALIDITY_DAY,
            )
            return {"success": True, "label": self.label, "response": {"order_id": order_id}}
        except Exception as e:
            return {"success": False, "label": self.label, "error": str(e)}
