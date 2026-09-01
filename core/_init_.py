from core.brokers.kotak import KotakSession
from core.brokers.zerodha import ZerodhaSession
from core.brokers.groww import GrowwSession

BROKER_REGISTRY = {
    "kotak": KotakSession,
    "zerodha": ZerodhaSession,
    "groww": GrowwSession,
}

BROKER_DISPLAY_NAMES = {
    "kotak": "Kotak Securities",
    "zerodha": "Zerodha",
    "groww": "Groww",
}


def get_session_class(broker_name: str):
    broker_name = broker_name.lower()
    if broker_name not in BROKER_REGISTRY:
        raise ValueError(f"Unknown broker '{broker_name}'. Supported: {list(BROKER_REGISTRY.keys())}")
    return BROKER_REGISTRY[broker_name]
