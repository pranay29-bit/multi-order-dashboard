import pyotp
from core.brokers.base import BrokerSession

try:
    from neo_api_client import NeoAPI
except Exception:
    NeoAPI = None

_ORDER_TYPE_MAP = {"MARKET": "MKT", "LIMIT": "L"}
_PRODUCT_MAP = {"DELIVERY": "CNC", "INTRADAY": "MIS"}
_EXCHANGE_SEGMENT_MAP = {"NSE": "nse_cm", "BSE": "bse_cm"}


class KotakSession(BrokerSession):
    broker_name = "kotak"

    def login(self) -> bool:
        if NeoAPI is None:
            self.last_error = "neo-api-client not installed."
            return False
        try:
            self.client = NeoAPI(
                consumer_key=self.app_credentials["consumer_key"],
                consumer_secret=self.app_credentials["consumer_secret"],
                environment=self.app_credentials.get("env", "prod"),
            )
            self.client.login(
                mobilenumber=self.account_creds["mobile_number"],
                password=self.account_creds["password"],
            )
            totp_secret = self.account_creds.get("totp_secret", "")
            if totp_secret:
                self.client.session_2fa(OTP=pyotp.TOTP(totp_secret).now())
            else:
                self.client.session_2fa(OTP=self.account_creds["mpin"])
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
            kotak_order_type = _ORDER_TYPE_MAP[order_type]
            resp = self.client.place_order(
                exchange_segment=_EXCHANGE_SEGMENT_MAP[exchange],
                product=_PRODUCT_MAP[product],
                price=str(price) if kotak_order_type == "L" else "0",
                order_type=kotak_order_type,
                quantity=str(quantity),
                validity="DAY",
                trading_symbol=f"{symbol}-EQ",
                transaction_type=transaction_type,
            )
            return {"success": True, "label": self.label, "response": resp}
        except Exception as e:
            return {"success": False, "label": self.label, "error": str(e)}
