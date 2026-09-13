import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from app.services.monitoring_pipeline import run_monitoring
from app.config import PROJECT_ROOT
import os

# Create a small sample CSV from the raw dataset to test ingestion
import pandas as pd
raw_data_path = PROJECT_ROOT / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
if raw_data_path.exists():
    df = pd.read_csv(raw_data_path).head(100)
    test_csv = "test_upload.csv"
    df.to_csv(test_csv, index=False)
    
    success, msg = run_monitoring(test_csv)
    print(f"Success: {success}")
    print(f"Message: {msg}")
    
    if os.path.exists(test_csv):
        os.remove(test_csv)
else:
    print(f"Raw data not found at {raw_data_path}")
