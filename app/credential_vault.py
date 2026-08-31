import hmac
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from core.credential_vault import CredentialVaultError, FirebaseCredentialVault


st.set_page_config(page_title="Credential Vault", layout="centered")
st.title("Credential vault")
st.warning("Use this page only on a private, access-controlled Streamlit deployment. Never host it on GitHub Pages.")

access_password = os.getenv("VAULT_ACCESS_PASSWORD")
if not access_password:
    st.error("VAULT_ACCESS_PASSWORD is not configured on the server.")
    st.stop()

if not st.session_state.get("vault_authenticated"):
    supplied_password = st.text_input("Vault password", type="password")
    if st.button("Unlock"):
        if hmac.compare_digest(supplied_password, access_password):
            st.session_state.vault_authenticated = True
            st.rerun()
        st.error("Incorrect vault password.")
    st.stop()

try:
    vault = FirebaseCredentialVault()
except CredentialVaultError as error:
    st.error(str(error))
    st.stop()

st.caption("Credentials are encrypted before they are written to Firestore.")

with st.form("application_credentials"):
    st.subheader("Kotak Neo application")
    consumer_key = st.text_input("Consumer key")
    consumer_secret = st.text_input("Consumer secret", type="password")
    environment = st.selectbox("Environment", ["prod", "uat"])
    save_application = st.form_submit_button("Save application credentials")
    if save_application:
        if not consumer_key or not consumer_secret:
            st.error("Consumer key and consumer secret are required.")
        else:
            vault.save_application(consumer_key, consumer_secret, environment)
            st.success("Application credentials saved.")

with st.form("account_credentials", clear_on_submit=True):
    st.subheader("Kotak account")
    label = st.text_input("Account label", placeholder="e.g. Family account 1")
    mobile_number = st.text_input("Registered mobile number")
    password = st.text_input("Login password", type="password")
    mpin = st.text_input("MPIN", type="password")
    totp_secret = st.text_input("TOTP secret (optional)", type="password")
    save_account = st.form_submit_button("Save account")
    if save_account:
        if not all([label, mobile_number, password, mpin]):
            st.error("Label, mobile number, password, and MPIN are required.")
        else:
            vault.save_account(
                {
                    "label": label,
                    "mobile_number": mobile_number,
                    "password": password,
                    "mpin": mpin,
                    "totp_secret": totp_secret,
                }
            )
            st.success("Account credentials saved.")
