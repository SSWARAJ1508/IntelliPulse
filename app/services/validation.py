import hashlib
import io
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_ROWS = 100000
MAX_COLS = 50

# Canonical 19 model features
NUMERICAL_FEATURES = ["tenure", "MonthlyCharges", "TotalCharges", "SeniorCitizen"]
CATEGORICAL_FEATURES = [
    "gender", "Partner", "Dependents", "PhoneService", 
    "MultipleLines", "InternetService", "OnlineSecurity", 
    "OnlineBackup", "DeviceProtection", "TechSupport", 
    "StreamingTV", "StreamingMovies", "Contract", 
    "PaperlessBilling", "PaymentMethod"
]
ALL_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "Churn"
ID_COLUMN = "customerID"


def compute_schema_hash(df: pd.DataFrame, all_features: List[str], has_target: bool) -> str:
    """
    Generate a deterministic SHA-256 fingerprint representing the schema contract.
    Based on ordered column names, mapped canonical feature types, and target configuration.
    """
    schema_dict = {
        "features": []
    }
    for col in sorted(all_features):
        if col in df.columns:
            if col in NUMERICAL_FEATURES:
                col_type = "numeric"
            elif col in CATEGORICAL_FEATURES:
                col_type = "categorical"
            else:
                col_type = "unknown"
        else:
            col_type = "missing"
        schema_dict["features"].append({"name": col, "type": col_type})

    schema_dict["has_target"] = has_target
    schema_str = json.dumps(schema_dict, sort_keys=True)
    return hashlib.sha256(schema_str.encode("utf-8")).hexdigest()[:16]


def validate_file(file_obj, max_size_bytes: int = MAX_FILE_SIZE_BYTES,
                  max_rows: int = MAX_ROWS, max_cols: int = MAX_COLS) -> Tuple[bool, str, Optional[pd.DataFrame]]:
    """
    Validates physical CSV file constraints: readability, emptiness, size, shape.
    Supports file paths, BytesIO, or uploaded file buffers.
    """
    try:
        # Determine size if possible
        if hasattr(file_obj, "size"):
            size = file_obj.size
        elif hasattr(file_obj, "getvalue"):
            size = len(file_obj.getvalue())
        elif isinstance(file_obj, (str, bytes)):
            import os
            size = os.path.getsize(file_obj) if isinstance(file_obj, str) else len(file_obj)
        else:
            size = None

        if size is not None:
            if size == 0:
                return False, "File is empty (0 bytes).", None
            if size > max_size_bytes:
                return False, f"File size ({size / (1024*1024):.1f}MB) exceeds maximum allowed ({max_size_bytes / (1024*1024):.0f}MB).", None

        # Reset stream position if applicable
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        df = pd.read_csv(file_obj)

        if df.empty or len(df) == 0:
            return False, "CSV contains no data rows.", None

        if len(df) > max_rows:
            return False, f"Row count ({len(df)}) exceeds maximum limit of {max_rows}.", None

        if df.shape[1] > max_cols:
            return False, f"Column count ({df.shape[1]}) exceeds maximum limit of {max_cols}.", None

        return True, "File validation passed.", df

    except Exception as e:
        return False, f"Unable to read CSV file: {str(e)}", None


def validate_schema(df: pd.DataFrame, baseline_profile: Dict[str, Any],
                    all_features: List[str] = ALL_FEATURES,
                    num_features: List[str] = NUMERICAL_FEATURES,
                    cat_features: List[str] = CATEGORICAL_FEATURES) -> Dict[str, Any]:
    """
    Compare uploaded schema against the existing baseline/model data contract.
    Returns structured results dictionary.
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    cleaned_df = df.copy()

    # Detect Target & Identifier
    has_target = TARGET_COLUMN in cleaned_df.columns
    has_id = ID_COLUMN in cleaned_df.columns

    # Check Required Features
    expected_features = set(all_features)
    actual_columns = set(cleaned_df.columns)
    
    missing_features = list(expected_features - actual_columns)
    unexpected_columns = list(actual_columns - expected_features - {TARGET_COLUMN, ID_COLUMN})

    if missing_features:
        errors.append(f"Missing required feature columns: {', '.join(sorted(missing_features))}")

    if unexpected_columns:
        warnings.append(f"Unexpected extra columns (ignored for modeling): {', '.join(sorted(unexpected_columns))}")

    # Clean and check data types
    if "TotalCharges" in cleaned_df.columns:
        # Handle string whitespace in TotalCharges
        if not pd.api.types.is_numeric_dtype(cleaned_df["TotalCharges"]):
            try:
                cleaned_df["TotalCharges"] = pd.to_numeric(cleaned_df["TotalCharges"], errors="coerce").fillna(0.0)
            except Exception:
                errors.append("Column 'TotalCharges' could not be coerced to numeric.")

    for feat in num_features:
        if feat in cleaned_df.columns:
            if not pd.api.types.is_numeric_dtype(cleaned_df[feat]):
                errors.append(f"Numerical feature '{feat}' has invalid non-numeric dtype: {cleaned_df[feat].dtype}")

    # Validate categorical categories against baseline profile
    cat_profile = baseline_profile.get("categorical_profile", {})
    for feat in cat_features:
        if feat in cleaned_df.columns and feat in cat_profile:
            valid_cats = set(cat_profile[feat].get("frequencies", {}).keys())
            actual_cats = set(cleaned_df[feat].dropna().unique())
            invalid_cats = actual_cats - valid_cats
            if invalid_cats:
                errors.append(f"Feature '{feat}' contains unrecognized categories: {sorted(list(invalid_cats))}")

    # Validate impossible numerical values
    if "tenure" in cleaned_df.columns and pd.api.types.is_numeric_dtype(cleaned_df["tenure"]):
        if (cleaned_df["tenure"] < 0).any():
            errors.append("Feature 'tenure' contains negative values.")
    if "MonthlyCharges" in cleaned_df.columns and pd.api.types.is_numeric_dtype(cleaned_df["MonthlyCharges"]):
        if (cleaned_df["MonthlyCharges"] < 0).any():
            errors.append("Feature 'MonthlyCharges' contains negative values.")
    if "SeniorCitizen" in cleaned_df.columns and pd.api.types.is_numeric_dtype(cleaned_df["SeniorCitizen"]):
        unique_vals = set(cleaned_df["SeniorCitizen"].dropna().unique())
        if not unique_vals.issubset({0, 1, 0.0, 1.0}):
            errors.append(f"Feature 'SeniorCitizen' has invalid values: {unique_vals - {0, 1, 0.0, 1.0}}")

    schema_hash = compute_schema_hash(cleaned_df, all_features, has_target)
    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "has_target": has_target,
        "has_id": has_id,
        "schema_hash": schema_hash,
        "missing_features": missing_features,
        "unexpected_columns": unexpected_columns,
        "cleaned_df": cleaned_df
    }


def compute_data_quality_summary(df: pd.DataFrame,
                                 all_features: List[str] = ALL_FEATURES,
                                 num_features: List[str] = NUMERICAL_FEATURES,
                                 cat_features: List[str] = CATEGORICAL_FEATURES,
                                 baseline_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generates batch data quality metrics:
    row count, column count, missing rows/cells, duplicate rows, null %,
    invalid categories, invalid numeric values.
    """
    total_rows = len(df)
    total_cols = df.shape[1]
    
    # Duplicate rows
    duplicate_rows = int(df.duplicated().sum())

    # Missing values
    missing_cells = int(df.isna().sum().sum())
    missing_rows = int(df.isna().any(axis=1).sum())
    null_pct_by_col = {col: round(float((df[col].isna().sum() / total_rows) * 100), 2) for col in df.columns}
    total_null_pct = round(float((missing_cells / (total_rows * total_cols)) * 100), 2) if (total_rows * total_cols) > 0 else 0.0

    # Categorical domain checks
    invalid_categories_count = 0
    invalid_cat_details: Dict[str, List[Any]] = {}
    if baseline_profile:
        cat_profile = baseline_profile.get("categorical_profile", {})
        for feat in cat_features:
            if feat in df.columns and feat in cat_profile:
                valid_cats = set(cat_profile[feat].get("frequencies", {}).keys())
                actual_cats = set(df[feat].dropna().unique())
                unexpected = actual_cats - valid_cats
                if unexpected:
                    invalid_categories_count += len(unexpected)
                    invalid_cat_details[feat] = list(unexpected)

    # Numerical range checks
    invalid_numerics_count = 0
    invalid_num_details: Dict[str, str] = {}
    if "tenure" in df.columns and pd.api.types.is_numeric_dtype(df["tenure"]):
        neg_count = int((df["tenure"] < 0).sum())
        if neg_count > 0:
            invalid_numerics_count += neg_count
            invalid_num_details["tenure"] = f"{neg_count} negative values"

    if "MonthlyCharges" in df.columns and pd.api.types.is_numeric_dtype(df["MonthlyCharges"]):
        neg_count = int((df["MonthlyCharges"] < 0).sum())
        if neg_count > 0:
            invalid_numerics_count += neg_count
            invalid_num_details["MonthlyCharges"] = f"{neg_count} negative values"

    return {
        "row_count": total_rows,
        "column_count": total_cols,
        "duplicate_rows": duplicate_rows,
        "missing_cells": missing_cells,
        "missing_rows": missing_rows,
        "total_null_percentage": total_null_pct,
        "null_percentages": null_pct_by_col,
        "invalid_categories_count": invalid_categories_count,
        "invalid_cat_details": invalid_cat_details,
        "invalid_numerics_count": invalid_numerics_count,
        "invalid_num_details": invalid_num_details
    }
