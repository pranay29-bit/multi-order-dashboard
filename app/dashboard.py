import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
from config.settings import CONSUMER_KEY, CONSUMER_SECRET, KOTAK_ENV, load_accounts
from core.order_engine import build_sessions, login_all, place_order_all

st.set_page_config(page_title="Kotak Multi-Account Orders", layout="centered")
st.title("Kotak Multi-Account Order Dashboard")
st.caption("Places one order across all your configured Kotak accounts, in parallel, on your click.")

if "sessions" not in st.session_state:
    st.session_state.sessions = None
if "login_results" not in st.session_state:
    st.session_state.login_results = None

# ---- Load accounts ----
try:
    account_dicts = load_accounts()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

st.subheader(f"Configured accounts: {len(account_dicts)}")
st.table(pd.DataFrame([{"Label": a["label"], "Mobile": a["mobile_number"]} for a in account_dicts]))

# ---- Login ----
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

# ---- Order form ----
st.subheader("Place order")

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
