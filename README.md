# Kotak Multi-Account Order Dashboard

A local Streamlit dashboard that lets you place the **same order simultaneously across multiple Kotak Securities (Kotak Neo) trading accounts** with one click. Built on Kotak's official Neo Trade API.

> ⚠️ **Personal-use tool, not a black-box algo.** Every order is triggered by you clicking a button after reviewing the symbol, quantity, and price. Nothing fires automatically in the background. If you later turn this into a fully automated/unattended strategy, note that SEBI has separate rules for algorithmic trading (tagging, broker approval, etc.) — this scope here (manual multi-account fan-out) does not require that, but automated/unattended triggering would.

---

## 1. How Kotak Neo API access works (do this first)

You need **one Neo API app registration** (consumer key + secret) and, separately, **login credentials for each of your 7+ accounts**.

1. Go to the Kotak Neo Trade API developer portal: https://neo.kotaksecurities.com (look for "Trade API" / API Developer section) and sign up as a developer using any one of your Kotak accounts.
2. Create an "App" — this gives you a **Consumer Key** and **Consumer Secret**. This one app+secret pair can generally be reused to log in to your other Kotak accounts too (each login is per-account, the app registration is just the API client identity). Some setups require Kotak to whitelist multiple client IDs under one app — if you hit that limit, ask Kotak Neo API support to enable multi-client access for your app.
3. For each of your 7 accounts, note down:
   - Mobile number registered with that account
   - Login password
   - MPIN (used for the 2FA/session step)
   - (Optional but recommended) TOTP secret if you enable TOTP-based 2FA on the account — this avoids needing an SMS OTP every session and is what makes multi-account automation practical.
4. The official Python SDK is `neo-api-client` (`pip install neo-api-client`). Login flow per account is:
   - `login(mobile_number, password)` → triggers OTP unless TOTP is set up
   - `session_2fa(OTP_or_MPIN)` → completes login and returns a session token
5. Keep all of these secrets **out of git** — this repo is set up so credentials only ever live in a local `accounts.json` / `.env` file that's gitignored (see below).

If any of this differs from what you see in the actual portal (Kotak updates their API portal periodically), their official API docs are the source of truth: search "Kotak Neo Trade API documentation."

---

## 2. Project structure

```
kotak-multi-order/
├── app/
│   └── dashboard.py        # Streamlit UI
├── core/
│   ├── kotak_client.py     # Wraps neo-api-client login + order placement per account
│   ├── order_engine.py     # Fan-out: places one order across all accounts in parallel
│   └── logger_setup.py     # Order/audit logging
├── config/
│   └── settings.py         # Loads accounts.json + .env
├── accounts.example.json   # Template — copy to accounts.json and fill in
├── .env.example             # Template — copy to .env and fill in
├── requirements.txt
└── logs/                    # Order history / audit trail (gitignored)
```

---

## 3. Setup

```bash
git clone <your-new-repo-url>
cd kotak-multi-order
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
cp accounts.example.json accounts.json
# now edit accounts.json and .env with your real credentials
```

Run the dashboard:

```bash
streamlit run app/dashboard.py
```

## Firebase credential vault (optional)

The included credential form is a **server-side Streamlit page**, not a GitHub Pages feature. It encrypts each credential payload before writing it to Cloud Firestore; the encryption key remains in your deployment's secrets.

1. Create a Firebase project with Cloud Firestore enabled, then create a service account with only the Firestore permissions this app needs.
2. Configure these as private deployment environment variables: `FIREBASE_SERVICE_ACCOUNT_JSON`, `CREDENTIAL_VAULT_KEY`, and `VAULT_ACCESS_PASSWORD`. Generate the encryption key with the command shown in `.env.example`.
3. Set `KOTAK_CREDENTIAL_STORE=firebase` on the Streamlit server.
4. Run `streamlit run app/credential_vault.py` from that private deployment to save the application and account credentials. Then run the dashboard normally.

Do not put any of these values in GitHub Actions variables, repository files, GitHub Pages, or the browser's Firebase client configuration.

---

## 4. Using the dashboard

1. Click **"Login to all accounts"** — it authenticates each of the 7+ accounts and shows a status indicator (✅/❌) per account.
2. Enter the trading symbol, exchange, transaction type (BUY/SELL), quantity per account, order type (MARKET/LIMIT), and price if LIMIT.
3. Review the per-account quantity/value summary shown before submitting.
4. Click **"Place order in all accounts"**. Orders are fired in parallel (thread pool), and a results table shows success/failure + order ID per account.
5. All attempts are logged to `logs/orders.log` with timestamps for your own audit trail.

---

## 5. Security notes

- `accounts.json` and `.env` are in `.gitignore` — never commit real credentials.
- Consider using OS-level keyring or a secrets manager instead of plaintext JSON if you're comfortable — `config/settings.py` has a hook to swap the loader.
- This tool talks directly to Kotak's official API endpoints only.
