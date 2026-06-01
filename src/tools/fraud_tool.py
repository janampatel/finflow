"""Supervised fraud classifier.

Complements the *unsupervised* anomaly tool (IsolationForest, novelty detection
on unlabeled streams). PaySim fraud is a labeled, supervised pattern that
unsupervised methods cannot separate, so when labels exist we use the right tool:
a RandomForest on the balance-error features that define the fraud signal.

The model is trained once with a held-out test split, evaluated honestly, and
cached to disk (`data/models/fraud_classifier.pkl`) so startup is fast on
subsequent boots. Held-out metrics are written to
`metrics/reports/fraud_evaluation.json` for the Phase 7 success gate (mirrors the
FinBERT Phase 2 → Phase 7 pattern, avoiding train/test leakage).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from loguru import logger

ROOT = Path(__file__).parent.parent.parent
MODEL_PATH = ROOT / "data" / "models" / "fraud_classifier.pkl"
PARQUET = ROOT / "data" / "processed" / "transactions" / "data.parquet"
EVAL_PATH = ROOT / "metrics" / "reports" / "fraud_evaluation.json"

FEATURES = [
    "amount",
    "balance_change_orig",
    "error_balance_orig",
    "error_balance_dest",
    "is_transfer",
    "is_cash_out",
]


def _engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Add the balance-error + transaction-type features that define PaySim fraud."""
    df = df.copy()
    df["balance_change_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]
    df["error_balance_orig"] = df["balance_change_orig"] + df["amount"]
    df["error_balance_dest"] = df["amount"] - df["balance_change_dest"]
    df["is_transfer"] = (df["type"] == "TRANSFER").astype(int)
    df["is_cash_out"] = (df["type"] == "CASH_OUT").astype(int)
    return df


class FraudClassifier:
    """RandomForest fraud probability model with cached weights + honest eval."""

    def __init__(self):
        self.model = None
        self._load_or_train()

    def _load_or_train(self):
        if MODEL_PATH.exists():
            try:
                self.model = joblib.load(MODEL_PATH)
                logger.info(f"Loaded fraud classifier from {MODEL_PATH}")
                return
            except Exception as e:
                logger.warning(f"Could not load fraud model ({e}); retraining")

        if not PARQUET.exists():
            logger.warning("Processed parquet not found — fraud classifier unavailable")
            return

        self._train_and_eval()

    def _train_and_eval(self):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            recall_score,
            precision_score,
            roc_auc_score,
            confusion_matrix,
        )

        logger.info("Training fraud classifier (one-time)…")
        df = pd.read_parquet(
            str(PARQUET),
            columns=[
                "type", "amount", "balance_change_orig",
                "oldbalanceDest", "newbalanceDest", "isFraud",
            ],
        )
        df = _engineer(df)

        # Stratified split so the test set is untouched by training (no leakage).
        train_df, test_df = train_test_split(
            df, test_size=0.2, stratify=df["isFraud"], random_state=42
        )

        # Balanced, downsampled training set for speed (all fraud + 200k legit).
        fraud_tr = train_df[train_df["isFraud"] == 1]
        legit_tr = train_df[train_df["isFraud"] == 0].sample(
            n=min(200_000, (train_df["isFraud"] == 0).sum()), random_state=42
        )
        train_bal = pd.concat([fraud_tr, legit_tr])

        X_train = train_bal[FEATURES].fillna(0.0).values
        y_train = train_bal["isFraud"].values

        self.model = RandomForestClassifier(
            n_estimators=80,
            max_depth=12,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_train, y_train)

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, MODEL_PATH)
        logger.info(f"Fraud classifier saved to {MODEL_PATH}")

        # Honest held-out evaluation: all test fraud + a representative legit sample.
        fraud_te = test_df[test_df["isFraud"] == 1]
        legit_te = test_df[test_df["isFraud"] == 0].sample(
            n=min(100_000, (test_df["isFraud"] == 0).sum()), random_state=7
        )
        test_eval = pd.concat([fraud_te, legit_te])

        X_test = test_eval[FEATURES].fillna(0.0).values
        y_test = test_eval["isFraud"].values
        proba = self.model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
        metrics = {
            "model": "RandomForest",
            "features": FEATURES,
            "recall": round(float(recall_score(y_test, pred)), 4),
            "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
            "false_positive_rate": round(float(fp / (fp + tn)) if (fp + tn) else 0.0, 4),
            "test_fraud": int(tp + fn),
            "test_legit": int(tn + fp),
            "feature_importance": {
                f: round(float(i), 4)
                for f, i in zip(FEATURES, self.model.feature_importances_)
            },
        }
        EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        EVAL_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        logger.info(
            f"Fraud eval — recall={metrics['recall']}, AUC={metrics['roc_auc']}, "
            f"precision={metrics['precision']} (saved to {EVAL_PATH})"
        )

    def __call__(
        self,
        amount: float,
        balance_change_orig: float = 0.0,
        balance_change_dest: float = 0.0,
        tx_type: str = "",
        **kwargs,
    ) -> dict:
        if self.model is None:
            return {
                "fraud_probability": 0.0,
                "is_fraud_predicted": False,
                "risk_level": "unknown",
                "method": "unavailable",
                "tool": "fraud_detection_tool",
            }

        error_orig = float(balance_change_orig) + float(amount)
        error_dest = float(amount) - float(balance_change_dest)
        features = np.array(
            [[
                float(amount),
                float(balance_change_orig),
                error_orig,
                error_dest,
                1.0 if tx_type == "TRANSFER" else 0.0,
                1.0 if tx_type == "CASH_OUT" else 0.0,
            ]],
            dtype=np.float64,
        )
        prob = float(self.model.predict_proba(features)[0][1])
        return {
            "fraud_probability": round(prob, 4),
            "is_fraud_predicted": prob >= 0.5,
            "risk_level": "high" if prob >= 0.7 else "medium" if prob >= 0.3 else "low",
            "method": "RandomForest",
            "tool": "fraud_detection_tool",
        }


# Lazy singleton — the classifier loads/trains on first call, not at import, so
# the API package imports without the dataset present (testable; fast cold start).
_fraud_instance: "FraudClassifier | None" = None


def _get_fraud_instance() -> "FraudClassifier":
    global _fraud_instance
    if _fraud_instance is None:
        _fraud_instance = FraudClassifier()
    return _fraud_instance


def fraud_detection_tool(
    amount: float,
    balance_change_orig: float = 0.0,
    balance_change_dest: float = 0.0,
    tx_type: str = "",
    **kwargs,
) -> dict:
    """Predict fraud probability for a transaction (supervised RandomForest).

    Args:
        amount: Transaction amount
        balance_change_orig: newbalanceOrig - oldbalanceOrg
        balance_change_dest: newbalanceDest - oldbalanceDest
        tx_type: Transaction type (TRANSFER / CASH_OUT / ...)

    Returns:
        dict: fraud_probability, is_fraud_predicted, risk_level, method, tool
    """
    return _get_fraud_instance()(amount, balance_change_orig, balance_change_dest, tx_type, **kwargs)
