from concurrent.futures import ThreadPoolExecutor, as_completed
from core.kotak_client import KotakAccountSession, AccountCredentials
from core.logger_setup import get_logger

logger = get_logger()


def build_sessions(consumer_key, consumer_secret, env, account_dicts):
    sessions = []
    for a in account_dicts:
        creds = AccountCredentials(
            label=a["label"],
            mobile_number=a["mobile_number"],
            password=a["password"],
            mpin=a["mpin"],
            totp_secret=a.get("totp_secret", ""),
        )
        sessions.append(KotakAccountSession(consumer_key, consumer_secret, env, creds))
    return sessions


def login_all(sessions, max_workers=10):
    results = []

    def _login(s):
        ok = s.login()
        return {"label": s.creds.label, "success": ok, "error": s.last_error}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_login, s) for s in sessions]
        for f in as_completed(futures):
            r = f.result()
            results.append(r)
            logger.info(f"LOGIN {r['label']}: {'OK' if r['success'] else 'FAILED - ' + str(r['error'])}")
    return results


def place_order_all(sessions, order_params, max_workers=10):
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
                f"{order_params['quantity']} x {order_params['trading_symbol']} -> {status}"
            )

    skipped = [s.creds.label for s in sessions if not s.logged_in]
    for label in skipped:
        results.append({"success": False, "label": label, "error": "Skipped - not logged in"})

    return results
