"""FinBERT fine-tuning script. Run on Google Colab with GPU."""

import json
from pathlib import Path
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, EarlyStoppingCallback
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
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

HYPERPARAMS = {
    "model_name": "ProsusAI/finbert",
    "max_length": 64,
    "batch_size": 32,
    "learning_rate": 2e-5,
    "num_epochs": 5,
    "warmup_steps": 100,
    "weight_decay": 0.01,
    "save_path": "./data/models/finbert-transaction"
}


class TransactionDataset(Dataset):
    """Custom dataset for transaction descriptions."""

    def __init__(self, descriptions, labels, tokenizer, max_length=64):
        self.descriptions = descriptions
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.descriptions)

    def __getitem__(self, idx):
        text = self.descriptions[idx]
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(label, dtype=torch.long)
        }


def load_data(csv_path: str, test_size: float = 0.1, val_size: float = 0.1):
    """Load and split transaction data."""
    logger.info(f"Loading data from {csv_path}...")

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} transactions")

    # Create label mapping
    label2id = {label: i for i, label in enumerate(CATEGORIES)}
    df["label"] = df["category"].map(label2id)

    # Remove unmapped categories
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    logger.info(f"After filtering: {len(df)} transactions")

    # Split: 80% train, 10% val, 10% test
    train_val, test = train_test_split(
        df, test_size=test_size, random_state=42, stratify=df["label"]
    )
    train, val = train_test_split(
        train_val, test_size=val_size / (1 - test_size), random_state=42, stratify=train_val["label"]
    )

    logger.info(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    return (
        train["description"].values, train["label"].values,
        val["description"].values, val["label"].values,
        test["description"].values, test["label"].values
    )


def compute_metrics(eval_pred):
    """Compute metrics for evaluation."""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="weighted", zero_division=0
    )

    return {
        "accuracy": accuracy,
        "f1": f1,
        "precision": precision,
        "recall": recall
    }


def train_finbert(csv_path: str):
    """Fine-tune FinBERT on transaction data."""
    logger.info("Starting FinBERT fine-tuning...")

    # Load data
    train_desc, train_labels, val_desc, val_labels, test_desc, test_labels = load_data(csv_path)

    # Load model and tokenizer
    logger.info(f"Loading {HYPERPARAMS['model_name']}...")
    tokenizer = AutoTokenizer.from_pretrained(HYPERPARAMS["model_name"])
    model = AutoModelForSequenceClassification.from_pretrained(
        HYPERPARAMS["model_name"],
        num_labels=len(CATEGORIES),
        id2label={i: cat for i, cat in enumerate(CATEGORIES)},
        label2id={cat: i for i, cat in enumerate(CATEGORIES)}
    )

    # Create datasets
    train_dataset = TransactionDataset(train_desc, train_labels, tokenizer, HYPERPARAMS["max_length"])
    val_dataset = TransactionDataset(val_desc, val_labels, tokenizer, HYPERPARAMS["max_length"])
    test_dataset = TransactionDataset(test_desc, test_labels, tokenizer, HYPERPARAMS["max_length"])

    # Training arguments
    training_args = TrainingArguments(
        output_dir="./training_outputs",
        num_train_epochs=HYPERPARAMS["num_epochs"],
        per_device_train_batch_size=HYPERPARAMS["batch_size"],
        per_device_eval_batch_size=HYPERPARAMS["batch_size"],
        learning_rate=HYPERPARAMS["learning_rate"],
        weight_decay=HYPERPARAMS["weight_decay"],
        warmup_steps=HYPERPARAMS["warmup_steps"],
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=100,
        seed=42
    )

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )

    # Train
    logger.info("Training...")
    trainer.train()

    # Evaluate on test set
    logger.info("Evaluating on test set...")
    test_results = trainer.evaluate(test_dataset)

    logger.info(f"Test Results: {test_results}")

    # Save model
    save_path = Path(HYPERPARAMS["save_path"])
    save_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(save_path))
    tokenizer.save_pretrained(str(save_path))
    logger.info(f"Model saved to {save_path}")

    # Save metrics
    metrics = {
        "hyperparameters": HYPERPARAMS,
        "test_results": test_results,
        "num_categories": len(CATEGORIES),
        "categories": CATEGORIES,
        "training_samples": len(train_dataset),
        "validation_samples": len(val_dataset),
        "test_samples": len(test_dataset)
    }

    metrics_path = Path("metrics/reports/finbert_metrics.json")
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    logger.info(f"Metrics saved to {metrics_path}")

    return model, tokenizer, test_results


if __name__ == "__main__":
    csv_path = "data/raw/transaction_labels.csv"
    model, tokenizer, results = train_finbert(csv_path)
    print(f"\nFine-tuning complete!")
    print(f"Test Accuracy: {results.get('test_accuracy', 0):.4f}")
    print(f"Test F1: {results.get('test_f1', 0):.4f}")
