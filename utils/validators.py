# utils/validators.py
import pandas as pd
from datetime import datetime

REQUIRED_COLUMNS = [
    "supplier_name",
    "category",
    "annual_spend_usd",
    "country",
    "contact_name",
    "contact_email",
    "sole_source",
]

OPTIONAL_COLUMNS = [
    "current_payment_terms",
    "last_negotiation_date",
    "notes",
]

ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


def validate_csv(df: pd.DataFrame) -> dict:
    """
    Validate uploaded CSV. Returns dict with:
    - valid: bool
    - errors: list of blocking errors
    - warnings: list of non-blocking warnings
    - cleaned_df: cleaned dataframe (if valid)
    """
    errors = []
    warnings = []

    # Check column presence
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_required:
        errors.append(f"Missing required columns: {', '.join(missing_required)}")
        return {"valid": False, "errors": errors, "warnings": warnings, "cleaned_df": None}

    # Add missing optional columns as empty
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""
            warnings.append(f"Optional column '{col}' not found — added as empty.")

    # Row-level validation
    row_errors = []
    for i, row in df.iterrows():
        row_num = i + 2  # 1-indexed + header row

        # Required field checks
        for col in REQUIRED_COLUMNS:
            if pd.isna(row[col]) or str(row[col]).strip() == "":
                row_errors.append(f"Row {row_num} ({row.get('supplier_name', '?')}): Missing '{col}'")

        # Spend must be numeric and positive
        try:
            spend = float(row["annual_spend_usd"])
            if spend <= 0:
                row_errors.append(f"Row {row_num}: annual_spend_usd must be positive")
        except (ValueError, TypeError):
            row_errors.append(f"Row {row_num}: annual_spend_usd must be a number")

        # Sole source must be Y or N
        ss = str(row.get("sole_source", "")).strip().upper()
        if ss not in ["Y", "N", "YES", "NO"]:
            row_errors.append(f"Row {row_num}: sole_source must be Y or N")

        # Email basic check
        email = str(row.get("contact_email", "")).strip()
        if "@" not in email or "." not in email:
            warnings.append(f"Row {row_num}: contact_email '{email}' looks invalid")

        # Date format check (optional field)
        lnd = str(row.get("last_negotiation_date", "")).strip()
        if lnd and lnd not in ["", "nan", "None"]:
            try:
                pd.to_datetime(lnd)
            except Exception:
                warnings.append(f"Row {row_num}: last_negotiation_date '{lnd}' could not be parsed as a date")

    errors.extend(row_errors)

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings, "cleaned_df": None}

    # Clean data
    df["annual_spend_usd"] = pd.to_numeric(df["annual_spend_usd"], errors="coerce")
    df["sole_source"] = df["sole_source"].astype(str).str.strip().str.upper().map(
        {"Y": "Y", "YES": "Y", "N": "N", "NO": "N"}
    ).fillna("N")
    df["supplier_name"] = df["supplier_name"].astype(str).str.strip()
    df["country"] = df["country"].astype(str).str.strip()
    df["contact_email"] = df["contact_email"].astype(str).str.strip()

    # Minimum supplier check
    if len(df) < 3:
        errors.append(
            "Please add at least 3 suppliers to run segmentation. "
            "ABC classification requires a minimum supplier base to be meaningful."
        )
        return {"valid": False, "errors": errors, "warnings": warnings, "cleaned_df": None}

    return {"valid": True, "errors": [], "warnings": warnings, "cleaned_df": df}


def validate_manual_entry(entry: dict) -> dict:
    """Validate a single manually entered supplier record."""
    errors = []

    for col in REQUIRED_COLUMNS:
        val = entry.get(col, "")
        if not val or str(val).strip() == "":
            errors.append(f"'{col}' is required")

    try:
        spend = float(entry.get("annual_spend_usd", 0))
        if spend <= 0:
            errors.append("Annual spend must be a positive number")
    except (ValueError, TypeError):
        errors.append("Annual spend must be a number")

    ss = str(entry.get("sole_source", "")).strip().upper()
    if ss not in ["Y", "N"]:
        errors.append("Sole source must be Y or N")

    return {"valid": len(errors) == 0, "errors": errors}


def is_international(country: str) -> bool:
    """Flag non-US suppliers as international."""
    domestic = {"usa", "united states", "us", "u.s.", "u.s.a."}
    return str(country).strip().lower() not in domestic


def is_stale(last_negotiation_date: str, threshold_months: int = 12) -> bool:
    """Return True if last negotiation was more than threshold_months ago."""
    if not last_negotiation_date or str(last_negotiation_date).strip() in ["", "nan", "None"]:
        return True  # Never negotiated = stale
    try:
        last_date = pd.to_datetime(last_negotiation_date)
        months_ago = (datetime.now() - last_date.to_pydatetime()).days / 30
        return months_ago > threshold_months
    except Exception:
        return False
