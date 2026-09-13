from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MONITORING_DIR = PROJECT_ROOT / "artifacts" / "monitoring"
DB_PATH = MONITORING_DIR / "intellipulse_monitoring.db"

# Validation Constant (NOT the source of truth, used only to validate)
EXPECTED_THRESHOLD = 0.29

# Scenarios mapping
SCENARIOS = {
    "Stable": "stable", 
    "Moderate Shift": "mild_shift",
    "Strong Shift": "strong_shift",
    "Uploaded Batch": "User Upload",
    "Baseline": "baseline"
}
