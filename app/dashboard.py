import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import hmac
import pandas as pd
import streamlit as st
from config.settings import (
    load_app_config, save_app_config,
    load_accounts, add_account, delete_account,
)
from core.kotak_client import KotakAccountSession, AccountCredentials
from core.order_engine import build_sessions, login_all, place_order_all

st.set_page_config(page_title="Kotak Multi-Account Orders", layout="centered")

# =========================================================
# Optional access gate. Set APP_ACCESS_PASSWORD in Streamlit
# Community Cloud's "Secrets" panel (App settings > Secrets) to
# require a password before this page loads. If it's not set,
# the app runs open — fine for local use, NOT recommended once
# deployed with a public URL.
# =========================================================
configured_password = st.secrets.get("APP_ACCESS_PASSWORD", "") if hasattr(st, "secrets") else ""

if configured_password:
    if not st.session_state.get("authenticated"):
        st.title("Kotak Multi-Account Order Dashboard")
        entered = st.text_input("Access password", type="password")
        if st.button("Unlock"):
            if hmac.compare_digest(entered, configured_password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

st.title("Kotak Multi-Account Order Dashboard")

if "sessions" not in st.session_state:
    st.session_state.sessions = None
if "login_results" not in st.session_state:
    st.session_state.login_results = None

app_config = load_app_config()
CONSUMER_KEY = app_config["consumer_key"]
CONSUMER_SECRET = app_config["consumer_secret"]
KOTAK_ENV = app_config["env"]

tab_settings, tab_accounts, tab_order = st.tabs(["⚙️ Settings", "👤 Accounts", "🚀 Place order"])

# =========================================================
# TAB 0 — Settings: Kotak Neo API app credentials, entered here
# =========================================================
with tab_settings:
    st.subheader("Kotak Neo API app credentials")
    st.caption(
        "This is the one-time API app registration from the Kotak Neo developer portal "
        "(not a personal account login — that's added in the Accounts tab)."
    )
    with st.form("settings_form"):
        consumer_key = st.text_input("Consumer key", value=CONSUMER_KEY)
        consumer_secret = st.text_input("Consumer secret", value=CONSUMER_SECRET, type="password")
        env = st.selectbox("Environment", ["prod", "uat"], index=0 if KOTAK_ENV == "prod" else 1)
        if st.form_submit_button("Save"):
            save_app_config(consumer_key, consumer_secret, env)
            st.success("Saved. Reloading...")
            st.rerun()

    if not CONSUMER_KEY or not CONSUMER_SECRET:
        st.warning("Not set yet — logins will fail until you save a Consumer Key and Secret above.")
    else:
        st.info("Consumer key/secret are set.")

# =========================================================
# TAB 1 — Accounts: add, verify (test login), delete
# =========================================================
with tab_accounts:
    st.subheader("Add a Kotak account")
    with st.form("add_account_form", clear_on_submit=True):
        label = st.text_input("Account label", placeholder="e.g. Self, Spouse, Dad")
        mobile_number = st.text_input("Registered mobile number", placeholder="+9198XXXXXXXX")
        password = st.text_input("Login password", type="password")
        mpin = st.text_input("MPIN", type="password")
        totp_secret = st.text_input(
            "TOTP secret (optional)", type="password",
            help="Set this only if you've enabled TOTP-based 2FA on this account in Kotak Neo. "
                 "Lets login work without typing an SMS OTP each time.",
        )
        submitted = st.form_submit_button("Add account")

        if submitted:
            if not all([label, mobile_number, password, mpin]):
                st.error("Label, mobile number, password, and MPIN are required.")
            else:
                try:
                    add_account({
                        "label": label,
                        "mobile_number": mobile_number,
                        "password": password,
                        "mpin": mpin,
                        "totp_secret": totp_secret,
                    })
                    st.success(f"Added account '{label}'.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.divider()
    st.subheader("Your accounts")

    accounts = load_accounts()
    if not accounts:
        st.info("No accounts added yet. Add one above to get started.")
    else:
        for a in accounts:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 2])
                col1.markdown(f"**{a['label']}**")
                col1.caption(a["mobile_number"])

                if col2.button("Verify login", key=f"verify_{a['label']}"):
                    creds = AccountCredentials(
                        label=a["label"], mobile_number=a["mobile_number"],
                        password=a["password"], mpin=a["mpin"],
                        totp_secret=a.get("totp_secret", ""),
                    )
                    session = KotakAccountSession(CONSUMER_KEY, CONSUMER_SECRET, KOTAK_ENV, creds)
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
# TAB 2 — Place order across all accounts at once
# =========================================================
with tab_order:
    account_dicts = load_accounts()

    if not CONSUMER_KEY or not CONSUMER_SECRET:
        st.warning("Set your Consumer Key/Secret in the Settings tab first.")
        st.stop()

    if not account_dicts:
        st.info("Add at least one account in the Accounts tab first.")
        st.stop()

    st.subheader(f"Linked accounts: {len(account_dicts)}")
    st.table(pd.DataFrame([{"Label": a["label"], "Mobile": a["mobile_number"]} for a in account_dicts]))

    if st.button("🔐 Login to all accounts", type="primary"):
        with st.spinner("Logging in to all accounts..."):
            sessions = build_sessions(CONSUMER_KEY, CONSUMER_SECRET, KOTAK_ENV, account_dicts)
            results = login_all(sessions)
            st.session_state.sessions = sessions
            st.session_state.login_results = results

    if st.session_state.login_results:
        df = pd.DataFrame(st.session_state.login_results)
        df["status"] = df["success"].map(lambda x: "✅ Logged in" if x else "❌ Failed")
        st.dataframe(df[["label", "status", "error"]], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("Order details")

    col1, col2 = st.columns(2)
    with col1:
        trading_symbol = st.text_input("Trading symbol", placeholder="e.g. RELIANCE-EQ")
        exchange_segment = st.selectbox("Exchange segment", ["nse_cm", "bse_cm"])
        transaction_type = st.selectbox("Transaction type", ["BUY", "SELL"])
    with col2:
        quantity = st.number_input("Quantity per account", min_value=1, value=1, step=1)
        order_type = st.selectbox("Order type", ["MKT", "L"], format_func=lambda x: "Market" if x == "MKT" else "Limit")
        product = st.selectbox("Product", ["CNC", "MIS"], format_func=lambda x: "Delivery (CNC)" if x == "CNC" else "Intraday (MIS)")

    price = 0.0
    if order_type == "L":
        price = st.number_input("Limit price", min_value=0.0, value=0.0, step=0.05)

    if st.session_state.sessions:
        n_logged_in = sum(1 for s in st.session_state.sessions if s.logged_in)
        st.info(f"This order will be sent to **{n_logged_in} logged-in account(s)**, "
                f"{quantity} shares each ({transaction_type} {trading_symbol or '—'}).")

    confirm = st.checkbox("I've double-checked the symbol, quantity, and price above.")

    if st.button("🚀 Place order in all accounts", disabled=not confirm):
        if not st.session_state.sessions:
            st.error("Log in to accounts first.")
        elif not trading_symbol:
            st.error("Enter a trading symbol.")
        else:
            order_params = dict(
                exchange_segment=exchange_segment,
                trading_symbol=trading_symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product=product,
                price=price,
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
