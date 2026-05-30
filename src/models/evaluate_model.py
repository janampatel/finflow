"""Evaluate fine-tuned FinBERT model on test set."""

import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, f1_score, precision_recall_fscore_support,
    confusion_matrix, classification_report
)
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from finbert_classifier import FinBERTClassifier, CATEGORIES


def evaluate_model(model_path: str, test_csv: str):
    """Evaluate model on test data."""
    logger.info(f"Loading model from {model_path}...")
    clf = FinBERTClassifier(model_path=model_path)

    logger.info(f"Loading test data from {test_csv}...")
    df = pd.read_csv(test_csv)

    # Map categories
    label2id = {label: i for i, label in enumerate(CATEGORIES)}
    df["label"] = df["category"].map(label2id)
    df = df.dropna(subset=["label"])

    descriptions = df["description"].values
    true_labels = df["label"].values
    true_categories = df["category"].values

    # Predict
    logger.info(f"Making predictions on {len(descriptions)} samples...")
    predictions = []
    confidences = []

    for desc in descriptions:
        result = clf.predict(desc)
        pred_label = label2id[result["category"]]
        predictions.append(pred_label)
        confidences.append(result["confidence"])

    predictions = np.array(predictions)
    confidences = np.array(confidences)

    # Compute metrics
    logger.info("Computing metrics...")

    accuracy = accuracy_score(true_labels, predictions)
    precision, recall, f1_macro, _ = precision_recall_fscore_support(
        true_labels, predictions, average="macro", zero_division=0
    )
    _, _, f1_weighted, _ = precision_recall_fscore_support(
        true_labels, predictions, average="weighted", zero_division=0
    )
    cm = confusion_matrix(true_labels, predictions, labels=range(len(CATEGORIES)))

    # Per-class metrics
    per_class = {}
    for i, category in enumerate(CATEGORIES):
        mask = true_labels == i
        if mask.sum() > 0:
            class_prec, class_rec, class_f1, _ = precision_recall_fscore_support(
                true_labels[mask], predictions[mask], average="binary", zero_division=0, pos_label=i
            )
            per_class[category] = {
                "f1": float(class_f1),
                "precision": float(class_prec),
                "recall": float(class_rec),
                "support": int(mask.sum())
            }

    # Confidence distribution
    high_conf = (confidences > 0.9).sum()
    med_conf = ((confidences > 0.7) & (confidences <= 0.9)).sum()
    low_conf = (confidences <= 0.7).sum()

    metrics = {
        "overall": {
            "accuracy": float(accuracy),
            "f1_macro": float(f1_macro),
            "f1_weighted": float(f1_weighted),
            "precision_macro": float(precision),
            "recall_macro": float(recall)
        },
        "per_class": per_class,
        "confidence_distribution": {
            "mean_confidence": float(confidences.mean()),
            "pct_above_0.9": float(high_conf / len(confidences) * 100),
            "pct_above_0.7": float((high_conf + med_conf) / len(confidences) * 100),
            "pct_below_0.5": float((confidences <= 0.5).sum() / len(confidences) * 100)
        },
        "low_confidence_rate": float(low_conf / len(confidences) * 100),
        "confusion_matrix": cm.tolist(),
        "test_samples": len(descriptions)
    }

    # Save metrics
    metrics_path = Path("metrics/reports/finbert_evaluation.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    logger.info(f"Metrics saved to {metrics_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("FINBERT EVALUATION RESULTS")
    print("=" * 70)
    print(f"\nOverall Performance:")
    print(f"  Accuracy:        {accuracy:.4f}")
    print(f"  F1 (Macro):      {f1_macro:.4f}")
    print(f"  F1 (Weighted):   {f1_weighted:.4f}")
    print(f"  Precision:       {precision:.4f}")
    print(f"  Recall:          {recall:.4f}")

    print(f"\nConfidence Distribution:")
    print(f"  Mean:            {confidences.mean():.4f}")
    print(f"  > 0.9:           {high_conf:,} ({high_conf/len(confidences)*100:.1f}%)")
    print(f"  > 0.7:           {high_conf + med_conf:,} ({(high_conf+med_conf)/len(confidences)*100:.1f}%)")
    print(f"  < 0.5:           {low_conf:,} ({low_conf/len(confidences)*100:.1f}%)")

    print(f"\nPer-Class Performance (Top 5):")
    top_f1 = sorted(per_class.items(), key=lambda x: x[1]["f1"], reverse=True)[:5]
    for cat, metrics_dict in top_f1:
        print(f"  {cat:25s}: F1={metrics_dict['f1']:.3f}, Recall={metrics_dict['recall']:.3f}")

    print("\n" + "=" * 70)

    return metrics


if __name__ == "__main__":
    # Get project root
    project_root = Path(__file__).parent.parent.parent

    model_path = project_root / "data" / "models" / "finbert-transaction"
    test_csv = project_root / "data" / "raw" / "transaction_labels.csv"

    evaluate_model(str(model_path), str(test_csv))
