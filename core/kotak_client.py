"""
Thin wrapper around the official `neo-api-client` SDK for a single Kotak account.
If your installed SDK version's method names differ, check with:
    python -c "from neo_api_client import NeoAPI; help(NeoAPI)"
"""

from dataclasses import dataclass
from typing import Optional
import pyotp

try:
    from neo_api_client import NeoAPI
except ImportError:
    NeoAPI = None  # lets the dashboard still start before pip install


@dataclass
class AccountCredentials:
    label: str
    mobile_number: str
    password: str
    mpin: str
    totp_secret: Optional[str] = ""


class KotakAccountSession:
    def __init__(self, consumer_key: str, consumer_secret: str, env: str, creds: AccountCredentials):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.env = env
        self.creds = creds
        self.client: Optional["NeoAPI"] = None
        self.logged_in = False
        self.last_error = None

    def login(self) -> bool:
        if NeoAPI is None:
            self.last_error = "neo-api-client not installed. Run: pip install neo-api-client"
            return False
        try:
            self.client = NeoAPI(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                environment=self.env,
            )
            self.client.login(mobilenumber=self.creds.mobile_number, password=self.creds.password)

            if self.creds.totp_secret:
                otp_code = pyotp.TOTP(self.creds.totp_secret).now()
                self.client.session_2fa(OTP=otp_code)
            else:
                self.client.session_2fa(OTP=self.creds.mpin)

            self.logged_in = True
            return True
        except Exception as e:
            self.last_error = str(e)
            self.logged_in = False
            return False

    def place_order(self, exchange_segment: str, trading_symbol: str, transaction_type: str,
                     quantity: int, order_type: str, product: str, price: float = 0):
        if not self.logged_in or self.client is None:
            return {"success": False, "error": "Not logged in", "label": self.creds.label}
        try:
            resp = self.client.place_order(
                exchange_segment=exchange_segment,
                product=product,
                price=str(price) if order_type == "L" else "0",
                order_type=order_type,
                quantity=str(quantity),
                validity="DAY",
                trading_symbol=trading_symbol,
                transaction_type=transaction_type,
            )
            return {"success": True, "label": self.creds.label, "response": resp}
        except Exception as e:
            return {"success": False, "label": self.creds.label, "error": str(e)}
