"""PySpark pipeline adapted for Windows (uses pandas backend for file I/O)."""

import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from loguru import logger

VALID_TYPES = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}


def load_raw_csv(csv_path: str):
    """Load CSV using pandas."""
    logger.info(f"Loading CSV from {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def data_quality_checks(df):
    """Flag rows that fail quality checks. Returns (clean_df, failure_df)."""
    required_cols = ["step", "type", "amount", "nameOrig", "nameDest"]

    quality_checks = (
        df[required_cols].isnull().any(axis=1) |
        (df["amount"] <= 0) |
        (~df["type"].isin(VALID_TYPES)) |
        (~df["isFraud"].isin([0, 1]))
    )

    failures = df[quality_checks]
    clean = df[~quality_checks].copy()

    failure_count = len(failures)
    total_count = len(df)
    failure_rate = (failure_count / total_count * 100) if total_count > 0 else 0

    logger.info(f"Quality checks: {total_count:,} total, {failure_count:,} failures ({failure_rate:.3f}%)")

    return clean, failures


def feature_engineering(df):
    """Compute transaction-level and user-level features."""
    logger.info("Engineering features...")

    df["balance_change_orig"] = df["newbalanceOrig"] - df["oldbalanceOrg"]
    df["balance_change_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]
    df["is_round_amount"] = ((df["amount"] % 100) == 0).astype(int)
    df["amount_log"] = np.log1p(df["amount"])
    df["direction"] = df["type"].apply(lambda x: "credit" if x in ["CASH_IN", "PAYMENT"] else "debit")

    logger.info("Computing rolling user-level features...")

    rolling_cols = ["amount"]
    for col in rolling_cols:
        df[f"user_avg_{col}_30"] = df.groupby("nameOrig")[col].transform(
            lambda x: x.rolling(window=30, min_periods=1).mean()
        )
        df[f"user_stddev_{col}_30"] = df.groupby("nameOrig")[col].transform(
            lambda x: x.rolling(window=30, min_periods=1).std()
        )

    df["user_tx_count_30"] = df.groupby("nameOrig").cumcount() + 1
    df.loc[df["user_tx_count_30"] > 30, "user_tx_count_30"] = 30

    df["user_total_spend_30"] = df.groupby("nameOrig").apply(
        lambda g: g[g["direction"] == "debit"]["amount"].rolling(window=30, min_periods=1).sum()
    ).reset_index(level=0, drop=True)

    df["user_total_income_30"] = df.groupby("nameOrig").apply(
        lambda g: g[g["direction"] == "credit"]["amount"].rolling(window=30, min_periods=1).sum()
    ).reset_index(level=0, drop=True)

    df = df.fillna(0)

    logger.info("Feature engineering complete")
    return df


def run_pipeline(csv_path: str, output_dir: str = "data/processed", metrics_dir: str = "metrics/reports"):
    """Execute full Phase 1 pipeline."""
    start_time = datetime.now()

    try:
        raw_df = load_raw_csv(csv_path)
        clean_df, failure_df = data_quality_checks(raw_df)
        enriched_df = feature_engineering(clean_df)

        output_path = Path(output_dir) / "transactions"
        failures_path = Path(output_dir) / "quality_failures"

        output_path.mkdir(parents=True, exist_ok=True)
        failures_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing processed transactions to {output_path}")
        enriched_df.to_parquet(str(output_path / "data.parquet"), compression="snappy", index=False)

        logger.info(f"Writing quality failures to {failures_path}")
        failure_df.to_parquet(str(failures_path / "failures.parquet"), compression="snappy", index=False)

        total_rows = len(raw_df)
        clean_rows = len(clean_df)
        failure_rows = len(failure_df)
        elapsed = (datetime.now() - start_time).total_seconds()

        fraud_count = clean_df[clean_df["isFraud"] == 1].shape[0]
        fraud_rate = (fraud_count / clean_rows * 100) if clean_rows > 0 else 0

        type_dist = clean_df["type"].value_counts().to_dict()

        metrics = {
            "total_rows": int(total_rows),
            "quality_failure_rows": int(failure_rows),
            "quality_failure_rate_pct": float((failure_rows / total_rows * 100) if total_rows > 0 else 0),
            "null_rates": {
                "step": float((clean_df["step"].isnull().sum() / clean_rows * 100) if clean_rows > 0 else 0),
                "type": float((clean_df["type"].isnull().sum() / clean_rows * 100) if clean_rows > 0 else 0),
                "amount": float((clean_df["amount"].isnull().sum() / clean_rows * 100) if clean_rows > 0 else 0),
            },
            "processing_time_seconds": float(elapsed),
            "rows_per_second": float(total_rows / elapsed if elapsed > 0 else 0),
            "output_parquet_size_mb": 0,
            "partition_count": 1,
            "fraud_rate_pct": float(fraud_rate),
            "transaction_type_distribution": {str(k): int(v) for k, v in type_dist.items()}
        }

        metrics_path = Path(metrics_dir) / "phase1_metrics.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)

        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info(f"Phase 1 metrics saved to {metrics_path}")

        return enriched_df, metrics

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    csv_file = "data/raw/PS_20174392719_1491204439457_log.csv"
    df, metrics = run_pipeline(csv_file)
    print(f"\nPipeline complete. Processed {metrics['total_rows']:,} rows in {metrics['processing_time_seconds']:.1f}s")
    print(f"Quality failures: {metrics['quality_failure_rows']:,} ({metrics['quality_failure_rate_pct']:.2f}%)")
    print(f"Fraud rate: {metrics['fraud_rate_pct']:.2f}%")
