import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger():
    logger = logging.getLogger("kotak_multi_order")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler(LOG_DIR / "orders.log")
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(sh)
    return logger
