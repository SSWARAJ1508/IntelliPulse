# IntelliPulse — Deployment & Operations Guide

This guide provides step-by-step instructions for deploying and running **IntelliPulse**, an enterprise Machine Learning Observability and Automated Root-Cause Analysis platform, on **Streamlit Community Cloud** and local environments.

---

## 1. System Requirements & Prerequisites

| Requirement | Specification |
|---|---|
| **Python Version** | Python 3.10, 3.11, or 3.12 (Recommended: `3.11.x`) |
| **Operating System** | Linux (Streamlit Cloud Debian), macOS, Windows 10/11 |
| **Model Runtime** | XGBoost (`xgboost>=2.0.0`), Scikit-learn (`scikit-learn>=1.3.0`) |
| **Storage** | ~20 MB repository footprint (XGBoost pipeline: 411 KB, SQLite DB: 580 KB) |
| **API Keys (Optional)** | Google Gemini API Key (`GEMINI_API_KEY`) for AI Observability Copilot |

---

## 2. Local Environment Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/SSWARAJ1508/IntelliPulse.git
cd IntelliPulse
```

### Step 2: Create and Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt / PowerShell)
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Production Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```
Open `.env` and add your Google Gemini API key:
```env
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```
> **Note:** IntelliPulse operates deterministically without Gemini. If `GEMINI_API_KEY` is omitted, all monitoring dashboards, statistical drift tests, frozen XGBoost inference, and SQLite evidence viewing remain 100% operational.

### Step 5: Run Application Locally
```bash
# Run using the root entry point:
streamlit run streamlit_app.py

# Or directly:
streamlit run app/main.py
```
The application will launch in your browser at `http://localhost:8501`.

---

## 3. Deploying to Streamlit Community Cloud

### Step 1: Push Repository to GitHub
Ensure your repository is pushed to your GitHub account:
```bash
git add .
git commit -m "Deploy: IntelliPulse Streamlit Community Cloud readiness"
git push origin main
```

### Step 2: Connect Streamlit Community Cloud
1. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
2. Click **New app**.
3. Select your repository: `your-username/IntelliPulse`.
4. Set **Branch**: `main`.
5. Set **Main file path**: `streamlit_app.py` (or `app/main.py`).
6. Expand **Advanced settings...**.

### Step 3: Configure Streamlit Cloud Secrets
In the **Secrets** text area within Advanced Settings, define your environment secrets using TOML syntax:
```toml
# Streamlit Secrets (Community Cloud)
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
```
Click **Save** and then click **Deploy!**.

---

## 4. Architectural Boundaries & Operational Contracts

### A. Contractual Decision Threshold (0.29)
The frozen XGBoost model (`artifacts/models/churn_xgboost_v4_tuned.joblib`) uses a strict, non-negotiable decision threshold of **`0.29`**.
- This threshold is mathematically validated in `app/config.py` and `app/data_access.py`.
- Any modification to this threshold will invalidate baseline comparisons and drift analytics.

### B. Two-Sample Statistical Drift Pipeline (V7)
- **Numerical Features (3):** `tenure`, `MonthlyCharges`, `TotalCharges` are evaluated against the frozen baseline dataset using the Kolmogorov-Smirnov two-sample test (`scipy.stats.ks_2samp`) and Population Stability Index (PSI).
- **Categorical Features (16):** Evaluated using Chi-Square goodness-of-fit tests (`scipy.stats.chisquare`).
- **Multiple Testing Correction:** Family-Wise Error Rate (FWER) controlled via Benjamini-Hochberg FDR (`statsmodels.stats.multitest.multipletests`).

### C. Gemini AI Copilot (Optional Tier)
- Gemini powers the AI Observability Copilot and LangGraph multi-agent root cause analysis (`agent/graph.py`).
- **Safe Fallback:** If the API key is not supplied, the AI Copilot reports `Configuration Required` and displays a helpful configuration guide. No errors or stack traces are displayed to end-users.

### D. Ephemeral SQLite Storage on Streamlit Cloud
- The platform uses a local SQLite database at `artifacts/monitoring/intellipulse_monitoring.db`.
- **Cloud Limitation:** Streamlit Community Cloud runs in ephemeral Docker containers. Uploaded customer batches and newly generated monitoring runs will persist across page refreshes during an active session, but will reset to the committed repository state when the cloud container restarts or rebuilds.
- **Permanent Preset Scenarios:** The four pre-packaged operational scenarios (`Baseline`, `Stable`, `Moderate Shift`, and `Strong Shift`) are fully pre-computed in committed artifacts and remain permanently accessible.

---

## 5. Verification & Smoke Testing

Run the automated test matrix to verify environment integrity:
```bash
# 1. Verify compilation
python3 -m compileall app agent streamlit_app.py

# 2. Run End-to-End Monitoring Pipeline Test Matrix (23 tests)
python3 tests/test_v12_pipeline.py

# 3. Run Dashboard & Data Access Integration Suite (19 tests)
python3 tests/test_v11_dashboard.py

# 4. Headless Streamlit Startup Smoke Test
streamlit run streamlit_app.py --server.headless true
```

---

## 6. Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'xgboost'` | Missing dependency in virtual environment | Run `pip install -r requirements.txt`. Ensure `xgboost>=2.0.0` is installed. |
| `FileNotFoundError: churn_xgboost_v4_tuned.joblib` | Model file ignored by `.gitignore` | Ensure `.gitignore` contains `!artifacts/models/churn_xgboost_v4_tuned.joblib` and the file is tracked in git. |
| `Gemini Copilot: Configuration Required` | `GEMINI_API_KEY` missing from `.env` or Streamlit Secrets | Define `GEMINI_API_KEY` in `.env` (locally) or in the Streamlit Cloud App Settings Secrets manager. |
| `503 / Streamlit Cloud Memory Limit Exceeded` | Attempting to load unneeded large models | Do not commit `churn_random_forest_v3.joblib` (56 MB). IntelliPulse runs exclusively on the 411 KB XGBoost pipeline. |
