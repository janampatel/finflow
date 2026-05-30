"""FinBERT classifier wrapper for inference and fine-tuning."""

from pathlib import Path
from functools import lru_cache
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from loguru import logger

CATEGORIES = [
    "Food and Dining",
    "Shopping",
    "Travel",
    "Healthcare",
    "Utilities",
    "Income / Direct Deposit",
    "Transfer",
    "Refund",
    "Entertainment",
    "Insurance",
    "Investment",
    "Other"
]


class FinBERTClassifier:
    """FinBERT wrapper for transaction classification."""

    def __init__(self, model_path: str = "./data/models/finbert-transaction", device: str = None):
        """Initialize classifier with fine-tuned or base model."""
        self.model_path = Path(model_path)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.id2label = {i: label for i, label in enumerate(CATEGORIES)}
        self.label2id = {label: i for i, label in enumerate(CATEGORIES)}

        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load tokenizer and model."""
        if self.model_path.exists():
            logger.info(f"Loading fine-tuned model from {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_path))
        else:
            logger.info("Loading base FinBERT model")
            model_id = "ProsusAI/finbert"
            self.tokenizer = AutoTokenizer.from_pretrained(model_id)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_id,
                num_labels=len(CATEGORIES),
                id2label=self.id2label,
                label2id=self.label2id
            )

        self.model.to(self.device)
        self.model.eval()

    @lru_cache(maxsize=1000)
    def predict(self, description: str) -> dict:
        """Predict category for transaction description."""
        inputs = self.tokenizer(
            description,
            return_tensors="pt",
            max_length=64,
            truncation=True,
            padding="max_length"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits[0]
        probs = torch.softmax(logits, dim=-1)
        confidence, pred_id = torch.max(probs, dim=0)

        category = self.id2label[pred_id.item()]
        confidence_score = confidence.item()

        return {
            "category": category,
            "confidence": float(confidence_score),
            "is_low_confidence": confidence_score < 0.7,
            "raw_description": description,
            "all_scores": {
                self.id2label[i]: float(probs[i].item())
                for i in range(len(CATEGORIES))
            }
        }

    def save_model(self, output_path: str):
        """Save fine-tuned model."""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(str(output_path))
        self.tokenizer.save_pretrained(str(output_path))
        logger.info(f"Model saved to {output_path}")

    def push_to_hub(self, repo_id: str):
        """Push model to HuggingFace Hub."""
        self.model.push_to_hub(repo_id)
        self.tokenizer.push_to_hub(repo_id)
        logger.info(f"Model pushed to {repo_id}")


if __name__ == "__main__":
    clf = FinBERTClassifier()

    test_cases = [
        "STARBUCKS COFFEE 1234",
        "DELTA AIRLINES TICKET",
        "AMAZON PURCHASE",
        "WALGREENS PHARMACY",
        "DIRECT DEPOSIT PAYROLL"
    ]

    for desc in test_cases:
        result = clf.predict(desc)
        print(f"{desc:30s} → {result['category']:25s} (conf: {result['confidence']:.3f})")
