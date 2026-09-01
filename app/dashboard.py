import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import hmac
import pandas as pd
import streamlit as st
from config.settings import (
    load_app_config, save_broker_app_config,
    load_accounts, add_account, delete_account,
)
from core.brokers import get_session_class, BROKER_DISPLAY_NAMES
from core.order_engine import build_sessions, login_all, place_order_all

st.set_page_config(page_title="Multi-Broker Multi-Account Orders", layout="centered")

configured_password = st.secrets.get("APP_ACCESS_PASSWORD", "") if hasattr(st, "secrets") else ""
if configured_password:
    if not st.session_state.get("authenticated"):
        st.title("Multi-Account Order Dashboard")
        entered = st.text_input("Access password", type="password")
        if st.button("Unlock"):
            if hmac.compare_digest(entered, configured_password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

st.title("Multi-Account Order Dashboard")

if "sessions" not in st.session_state:
    st.session_state.sessions = None
if "login_results" not in st.session_state:
    st.session_state.login_results = None

BROKERS = ["kotak", "zerodha", "groww"]

tab_settings, tab_accounts, tab_order = st.tabs(["⚙️ Settings", "👤 Accounts", "🚀 Place order"])

# =========================================================
# TAB 0 — Settings: pick a broker, then that broker's app-level credentials
# =========================================================
with tab_settings:
    st.subheader("Select broker")
    broker = st.selectbox(
        "Which broker's app credentials do you want to set up?",
        BROKERS, format_func=lambda b: BROKER_DISPLAY_NAMES[b],
    )

    st.divider()
    app_config = load_app_config()
    current = app_config.get(broker, {})

    if broker == "kotak":
        st.subheader("Kotak Neo API app credentials")
        st.caption("From the Kotak Neo developer portal — one-time, not a personal account login.")
        with st.form("kotak_settings_form"):
            consumer_key = st.text_input("Consumer key", value=current.get("consumer_key", ""))
            consumer_secret = st.text_input("Consumer secret", value=current.get("consumer_secret", ""), type="password")
            env = st.selectbox("Environment", ["prod", "uat"], index=0 if current.get("env", "prod") == "prod" else 1)
            if st.form_submit_button("Save"):
                save_broker_app_config("kotak", {
                    "consumer_key": consumer_key, "consumer_secret": consumer_secret, "env": env,
                })
                st.success("Saved.")
                st.rerun()

    elif broker == "zerodha":
        st.subheader("Zerodha Kite Connect app")
        st.caption(
            "Each Zerodha account needs its OWN Kite Connect app (api_key/api_secret) — "
            "these live per-account instead, in the Accounts tab. Nothing to save here."
        )

    elif broker == "groww":
        st.subheader("Groww API")
        st.caption(
            "Groww's api_key and totp_secret are per-account (from the Groww API dashboard, "
            "Trading APIs section) — added per account in the Accounts tab. Nothing to save here."
        )

# =========================================================
# TAB 1 — Accounts: pick broker, add account with that broker's fields, verify, delete
# =========================================================
with tab_accounts:
    st.subheader("Add an account")
    add_broker = st.selectbox(
        "Broker", BROKERS, format_func=lambda b: BROKER_DISPLAY_NAMES[b], key="add_broker_select",
    )

    with st.form("add_account_form", clear_on_submit=True):
        label = st.text_input("Account label", placeholder="e.g. Self, Spouse, Dad")

        account_fields = {"broker": add_broker, "label": label}

        if add_broker == "kotak":
            account_fields["mobile_number"] = st.text_input("Registered mobile number", placeholder="+9198XXXXXXXX")
            account_fields["password"] = st.text_input("Login password", type="password")
            account_fields["mpin"] = st.text_input("MPIN", type="password")
            account_fields["totp_secret"] = st.text_input(
                "TOTP secret (optional)", type="password",
                help="Set this only if TOTP-based 2FA is enabled on this account. Avoids manual SMS OTP.",
            )

        elif add_broker == "zerodha":
            account_fields["api_key"] = st.text_input("Kite Connect API key (this account's own app)")
            account_fields["api_secret"] = st.text_input("Kite Connect API secret", type="password")
            st.caption(
                "Zerodha requires a fresh access_token once per trading day via their browser login "
                "redirect — no headless login exists. After adding this account, you'll generate "
                "and paste in today's token below each morning before it can log in."
            )
            account_fields["access_token"] = ""

        elif add_broker == "groww":
            account_fields["api_key"] = st.text_input("Groww API key / TOTP token")
            account_fields["totp_secret"] = st.text_input("Groww TOTP secret", type="password")

        submitted = st.form_submit_button("Add account")

        if submitted:
            required = [v for k, v in account_fields.items() if k not in ("broker", "access_token")]
            if not label or not all(required):
                st.error("Fill in all fields for this broker.")
            else:
                try:
                    add_account(account_fields)
                    st.success(f"Added '{label}' ({BROKER_DISPLAY_NAMES[add_broker]}).")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.divider()
    st.subheader("Your accounts")

    accounts = load_accounts()
    if not accounts:
        st.info("No accounts added yet. Add one above to get started.")
    else:
        app_config = load_app_config()
        for a in accounts:
            broker_of_a = a.get("broker", "kotak")
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 2])
                col1.markdown(f"**{a['label']}**  \n`{BROKER_DISPLAY_NAMES[broker_of_a]}`")

                if broker_of_a == "zerodha":
                    new_token = col1.text_input(
                        "Today's access token", value=a.get("access_token", ""),
                        key=f"token_{a['label']}", type="password",
                    )
                    if new_token != a.get("access_token", ""):
                        a["access_token"] = new_token
                        accounts_all = load_accounts()
                        for acc in accounts_all:
                            if acc["label"] == a["label"]:
                                acc["access_token"] = new_token
                        from config.settings import save_accounts
                        save_accounts(accounts_all)

                if col2.button("Verify login", key=f"verify_{a['label']}"):
                    SessionClass = get_session_class(broker_of_a)
                    session = SessionClass(app_config.get(broker_of_a, {}), a)
                    with st.spinner(f"Verifying {a['label']}..."):
                        ok = session.login()
                    if ok:
                        st.success(f"✅ {a['label']}: login works.")
                    else:
                        st.error(f"❌ {a['label']}: {session.last_error}")

                if col3.button("Delete", key=f"delete_{a['label']}"):
                    delete_account(a["label"])
                    st.rerun()

# =========================================================
# TAB 2 — Place order across ALL accounts, all brokers, at once
# =========================================================
with tab_order:
    account_dicts = load_accounts()
    app_config = load_app_config()

    if not account_dicts:
        st.info("Add at least one account in the Accounts tab first.")
        st.stop()

    st.subheader(f"Linked accounts: {len(account_dicts)}")
    st.table(pd.DataFrame([
        {"Broker": BROKER_DISPLAY_NAMES[a.get("broker", "kotak")], "Label": a["label"]} for a in account_dicts
    ]))

    if st.button("🔐 Login to all accounts", type="primary"):
        with st.spinner("Logging in to all accounts..."):
            sessions = build_sessions(app_config, account_dicts)
            results = login_all(sessions)
            st.session_state.sessions = sessions
            st.session_state.login_results = results

    if st.session_state.login_results:
        df = pd.DataFrame(st.session_state.login_results)
        df["status"] = df["success"].map(lambda x: "✅ Logged in" if x else "❌ Failed")
        st.dataframe(df[["broker", "label", "status", "error"]], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Order details")

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("Symbol", placeholder="e.g. RELIANCE")
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        transaction_type = st.selectbox("Transaction type", ["BUY", "SELL"])
    with col2:
        quantity = st.number_input("Quantity per account", min_value=1, value=1, step=1)
        order_type = st.selectbox("Order type", ["MARKET", "LIMIT"])
        product = st.selectbox("Product", ["DELIVERY", "INTRADAY"])

    price = 0.0
    if order_type == "LIMIT":
        price = st.number_input("Limit price", min_value=0.0, value=0.0, step=0.05)

    if st.session_state.sessions:
        n_logged_in = sum(1 for s in st.session_state.sessions if s.logged_in)
        st.info(f"This order will be sent to **{n_logged_in} logged-in account(s)** across all brokers, "
                f"{quantity} shares each ({transaction_type} {symbol or '—'}).")

    confirm = st.checkbox("I've double-checked the symbol, quantity, and price above.")

    if st.button("🚀 Place order in all accounts", disabled=not confirm):
        if not st.session_state.sessions:
            st.error("Log in to accounts first.")
        elif not symbol:
            st.error("Enter a symbol.")
        else:
            order_params = dict(
                symbol=symbol.upper().strip(), exchange=exchange, transaction_type=transaction_type,
                quantity=quantity, order_type=order_type, product=product, price=price,
            )
            with st.spinner("Placing orders across accounts..."):
                results = place_order_all(st.session_state.sessions, order_params)

            st.subheader("Results")
            df = pd.DataFrame(results)
            df["status"] = df["success"].map(lambda x: "✅ Placed" if x else "❌ Failed")
            show_cols = [c for c in ["label", "status", "response", "error"] if c in df.columns]
            st.dataframe(df[show_cols], hide_index=True, use_container_width=True)

            n_success = sum(1 for r in results if r.get("success"))
            st.success(f"{n_success}/{len(results)} orders placed successfully.")

    st.divider()
    st.caption("Full audit log written to logs/orders.log")
