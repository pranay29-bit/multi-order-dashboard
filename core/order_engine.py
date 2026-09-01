from concurrent.futures import ThreadPoolExecutor, as_completed
from core.brokers import get_session_class
from core.logger_setup import get_logger

logger = get_logger()


def build_sessions(broker_app_credentials: dict, account_dicts: list):
    """
    broker_app_credentials: { "kotak": {...}, "zerodha": {...}, "groww": {...} }
    account_dicts: each has a "broker" field plus that broker's per-account fields.
    """
    sessions = []
    for a in account_dicts:
        broker = a.get("broker", "kotak")
        SessionClass = get_session_class(broker)
        app_creds = broker_app_credentials.get(broker, {})
        sessions.append(SessionClass(app_creds, a))
    return sessions


def login_all(sessions, max_workers=10):
    results = []

    def _login(s):
        ok = s.login()
        return {"label": s.label, "broker": s.broker_name, "success": ok, "error": s.last_error}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_login, s) for s in sessions]
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            logger.info(f"LOGIN [{r['broker']}] {r['label']}: {'OK' if r['success'] else 'FAILED - ' + str(r['error'])}")
    return results


def place_order_all(sessions, order_params, max_workers=10):
    """order_params: NORMALIZED dict — symbol, exchange, transaction_type, quantity, order_type, product, price."""
    results = []
    logged_in_sessions = [s for s in sessions if s.logged_in]

    def _place(s):
        return s.place_order(**order_params)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_place, s) for s in logged_in_sessions]
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            status = "SUCCESS" if r.get("success") else f"FAILED - {r.get('error')}"
            logger.info(
                f"ORDER {r.get('label')}: {order_params['transaction_type']} "
                f"{order_params['quantity']} x {order_params['symbol']} -> {status}"
            )

    skipped = [s.label for s in sessions if not s.logged_in]
    for label in skipped:
        results.append({"success": False, "label": label, "error": "Skipped - not logged in"})

    return results
