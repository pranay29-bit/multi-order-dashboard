"""
Groww's official API uses TOTP-based auth (api_key + totp_secret), which —
unlike Zerodha — supports a fully headless login, no daily browser step needed.

Note: Groww also requires a Trading API subscription and a static IP added on
their API dashboard before order placement will work (reads like holdings work
without it). If method/param names below don't match your installed SDK
version, check with: python -c "from growwapi import GrowwAPI; help(GrowwAPI)"
"""

import pyotp
from core.brokers.base import BrokerSession

try:
    from growwapi import GrowwAPI
except ImportError:
    GrowwAPI = None

_PRODUCT_MAP = {"DELIVERY": "CNC", "INTRADAY": "MIS"}
_ORDER_TYPE_MAP = {"MARKET": "MARKET", "LIMIT": "LIMIT"}


class GrowwSession(BrokerSession):
    broker_name = "groww"

    def login(self) -> bool:
        if GrowwAPI is None:
            self.last_error = "growwapi not installed."
            return False
        try:
            api_key = self.account_creds["api_key"]
            totp_secret = self.account_creds["totp_secret"]
            totp = pyotp.TOTP(totp_secret).now()
            access_token = GrowwAPI.get_access_token(api_key=api_key, totp=totp)
            self.client = GrowwAPI(access_token)
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
            resp = self.client.place_order(
                trading_symbol=symbol,
                exchange=exchange,
                segment=self.client.SEGMENT_CASH,
                product=_PRODUCT_MAP[product],
                order_type=_ORDER_TYPE_MAP[order_type],
                transaction_type=transaction_type,
                quantity=quantity,
                price=price if order_type == "LIMIT" else 0,
                validity="DAY",
            )
            return {"success": True, "label": self.label, "response": resp}
        except Exception as e:
            return {"success": False, "label": self.label, "error": str(e)}
