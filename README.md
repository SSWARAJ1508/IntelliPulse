# IntelliPulse — Enterprise ML Observability & Root-Cause Analysis Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![XGBoost](https://img.shields.io/badge/model-XGBoost%20Tuned-orange.svg)](https://xgboost.readthedocs.io/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**IntelliPulse** is a production-grade Machine Learning Observability platform built for enterprise customer churn prediction. It couples real-time incoming batch validation, rigorous two-sample statistical drift detection (KS tests, Chi-Square tests, and Population Stability Index), frozen XGBoost model inference at a validated `0.29` threshold, and deterministic system health diagnostics with an agentic AI Copilot powered by Google Gemini and LangGraph.

---

## 🌟 Core Architecture & Capabilities

```mermaid
flowchart LR
    A[Incoming Customer Batch CSV] --> B[Schema & Type Validation]
    B --> C[Statistical Drift Engine\n(KS-Test, Chi-Sq, PSI, FDR)]
    B --> D[Frozen XGBoost Pipeline\n(Threshold: 0.29)]
    C --> E[Deterministic Health Engine\n(V9 Health Index)]
    D --> E
    E --> F[(SQLite Monitoring DB\nEvidence Store)]
    F --> G[Calm Enterprise Dashboard\n(Streamlit UI)]
    F --> H[Observability AI Copilot\n(LangGraph + Gemini 3.6)]
```

### 1. Rigorous Statistical Drift Engine (V7)
- **Numerical Drift:** Evaluates distributions using the Kolmogorov-Smirnov 2-sample test (`scipy.stats.ks_2samp`) and Population Stability Index (PSI) against frozen baseline profiles.
- **Categorical Drift:** Chi-Square goodness-of-fit tests (`scipy.stats.chisquare`).
- **FDR Correction:** Applies Benjamini-Hochberg False Discovery Rate control (`statsmodels.stats.multitest.multipletests`) across 19 feature hypotheses to eliminate false drift alarms.

### 2. Frozen XGBoost Model Pipeline
- **Optimized Threshold:** Locked to **`0.29`** (optimized for business recall and churn capture, balancing false positives).
- **Automated Validation:** Validates threshold alignment dynamically before inference.

### 3. Multi-Scenario Monitoring
- Pre-configured, ground-truth scenarios for audit verification:
  - **Baseline:** Ground-truth training reference distribution.
  - **Stable:** Clean production batch showing zero statistical drift.
  - **Moderate Shift:** Mild drift scenario with warning-level indicator shifts.
  - **Strong Shift:** Major demographic and contract feature drift triggering alert thresholds.
- **Live CSV Ingestion:** Drag-and-drop ingestion of arbitrary production batches with real-time schema validation.

### 4. Agentic AI Observability Copilot
- Multi-agent LangGraph workflow grounding all responses directly in SQLite database evidence (`artifacts/monitoring/intellipulse_monitoring.db`).
- Performs root-cause analysis, feature contribution queries, and diagnostic reporting.
- Operates in **Honest Optional Mode**: If no Gemini API key is configured, the dashboard functions deterministically without disruption.

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/SSWARAJ1508/IntelliPulse.git
cd IntelliPulse

python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables (Optional)
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (optional)
```

### 4. Launch the Application
```bash
streamlit run streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ☁️ Deployment on Streamlit Community Cloud

See [DEPLOYMENT.md](DEPLOYMENT.md) for full cloud configuration steps.

1. Fork or push this repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io/) and create a **New app**.
3. Set **Main file path** to `streamlit_app.py`.
4. In **Advanced Settings > Secrets**, configure:
   ```toml
   GEMINI_API_KEY = "your_actual_gemini_api_key_here"
   ```
5. Click **Deploy!**.

---

## 🧪 Automated Test Suite

Run the full verification matrix locally:
```bash
# 1. Pipeline & Ingestion Matrix (23 tests)
python3 tests/test_v12_pipeline.py

# 2. Dashboard & Visualization Matrix (19 tests)
python3 tests/test_v11_dashboard.py

# 3. Dynamic UI & Ground-Truth Verification (6 suites)
python3 tests/test_ui_and_functionality.py
```

---

## 📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
