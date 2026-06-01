"""Anomaly detection tool using Isolation Forest - FIXED VERSION."""

import numpy as np
from pathlib import Path
from loguru import logger
from pyod.models.iforest import IForest
import pandas as pd


class AnomalyTool:
    """Isolation Forest anomaly detector for transactions."""

    def __init__(self):
        """Initialize anomaly detector."""
        self.model = None
        self.trained_features = []
        self._train_model()

    def _train_model(self):
        """Train Isolation Forest on processed transaction features."""
        try:
            # Load processed data from Phase 1
            processed_path = Path(__file__).parent.parent.parent / "data" / "processed" / "transactions" / "data.parquet"

            if not processed_path.exists():
                logger.warning(f"Processed data not found - using heuristic mode only")
                self.model = None
                return

            # Load parquet file
            df = pd.read_parquet(str(processed_path))
            logger.info(f"Loaded {len(df):,} processed transactions")

            # Engineer the PaySim fraud signal: "error-balance" features capture
            # the balance inconsistency that defines fraud (money leaves origin but
            # the destination balance doesn't reflect it). These separate fraud far
            # better than raw amount, and are computable from existing columns:
            #   error_balance_orig = (newbalanceOrig - oldbalanceOrg) + amount
            #   error_balance_dest = amount - (newbalanceDest - oldbalanceDest)
            df["balance_change_dest"] = df["newbalanceDest"] - df["oldbalanceDest"]
            df["error_balance_orig"] = df["balance_change_orig"] + df["amount"]
            df["error_balance_dest"] = df["amount"] - df["balance_change_dest"]

            self.trained_features = [
                "amount",
                "balance_change_orig",
                "error_balance_orig",
                "error_balance_dest",
            ]

            X = df[self.trained_features].fillna(0.0).values

            # Train Isolation Forest
            logger.info(f"Training IsolationForest: {len(X)} samples × {len(self.trained_features)} features")
            logger.info(f"Features: {self.trained_features}")
            self.model = IForest(contamination=0.05, random_state=42)
            self.model.fit(X)
            logger.info(f"✓ AnomalyTool ready (using {len(self.trained_features)} features)")

        except Exception as e:
            logger.error(f"Failed to train anomaly model: {e}")
            self.model = None
            self.trained_features = []

    def _heuristic_detection(self, amount: float, balance_change: float) -> dict:
        """Fallback heuristic-based anomaly detection."""
        scores = []

        if amount > 10000:
            scores.append(0.7)
        elif amount > 5000:
            scores.append(0.4)

        if abs(balance_change) > 50000:
            scores.append(0.8)
        elif abs(balance_change) > 20000:
            scores.append(0.5)

        if amount > 0 and amount == int(amount) and str(int(amount)).endswith("00"):
            scores.append(0.2)

        anomaly_score = max(scores) if scores else 0.1
        severity = "high" if anomaly_score > 0.7 else "medium" if anomaly_score > 0.4 else "low"

        return {
            "is_anomaly": anomaly_score > 0.5,
            "anomaly_score": float(anomaly_score),
            "severity": severity
        }

    def __call__(self, amount: float, balance_change_orig: float = 0.0, **kwargs) -> dict:
        """Detect anomalies in transaction."""
        if self.model is None:
            result = self._heuristic_detection(amount, balance_change_orig)
        else:
            try:
                # Build the SAME engineered feature vector used in training.
                balance_change_dest = float(kwargs.get("balance_change_dest", 0.0))
                error_balance_orig = float(balance_change_orig) + float(amount)
                error_balance_dest = float(amount) - balance_change_dest

                feature_map = {
                    "amount": float(amount),
                    "balance_change_orig": float(balance_change_orig),
                    "error_balance_orig": error_balance_orig,
                    "error_balance_dest": error_balance_dest,
                }
                feature_values = [feature_map[f] for f in self.trained_features]
                features = np.array(feature_values, dtype=np.float64).reshape(1, -1)

                # Predict
                is_anomaly = self.model.predict(features)[0] == 1
                anomaly_score = self.model.decision_function(features)[0]

                # Normalize score to 0-1
                anomaly_score = 1.0 / (1.0 + np.exp(-float(anomaly_score)))

                severity = "high" if anomaly_score > 0.7 else "medium" if anomaly_score > 0.4 else "low"

                result = {
                    "is_anomaly": bool(is_anomaly),
                    "anomaly_score": float(anomaly_score),
                    "severity": severity
                }
            except Exception as e:
                logger.error(f"Model prediction failed: {e}, using heuristic")
                result = self._heuristic_detection(amount, balance_change_orig)

        # Add reason
        if result["is_anomaly"]:
            if result["severity"] == "high":
                reason = f"High anomaly score ({result['anomaly_score']:.2f}): Unusual transaction pattern"
            elif result["severity"] == "medium":
                reason = f"Medium anomaly score ({result['anomaly_score']:.2f}): Potential outlier"
            else:
                reason = f"Low anomaly score ({result['anomaly_score']:.2f}): Minor deviation"
        else:
            reason = "Normal transaction pattern"

        return {
            **result,
            "anomaly_reason": reason,
            "method": "IsolationForest" if self.model else "Heuristic",
            "tool": "anomaly_detection_tool"
        }


# Lazy singleton — IsolationForest trains/loads on first call, not at import, so
# the API package imports without the dataset present (testable; fast cold start).
_anomaly_tool_instance: "AnomalyTool | None" = None


def _get_anomaly_tool() -> "AnomalyTool":
    global _anomaly_tool_instance
    if _anomaly_tool_instance is None:
        _anomaly_tool_instance = AnomalyTool()
    return _anomaly_tool_instance


def anomaly_detection_tool(amount: float, balance_change_orig: float = 0.0, **kwargs) -> dict:
    """
    Detect anomalies in transaction using Isolation Forest.

    Args:
        amount: Transaction amount
        balance_change_orig: Balance change for originator
        **kwargs: Additional features

    Returns:
        dict with keys: is_anomaly, anomaly_score, severity, anomaly_reason, method, tool
    """
    return _get_anomaly_tool()(amount, balance_change_orig, **kwargs)
