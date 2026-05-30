"""Download real transaction data from Kaggle for fine-tuning."""

import os
import subprocess
from pathlib import Path
import pandas as pd
from loguru import logger

KAGGLE_DATASET = "sudheerkadam/online-transactions-dataset"
DOWNLOAD_PATH = "data/raw"


def download_from_kaggle():
    """Download dataset using Kaggle API."""
    Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading {KAGGLE_DATASET}...")

    try:
        subprocess.run([
            "kaggle", "datasets", "download",
            "-d", KAGGLE_DATASET,
            "-p", DOWNLOAD_PATH,
            "--unzip"
        ], check=True)

        logger.info(f"Downloaded to {DOWNLOAD_PATH}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Kaggle download failed: {e}")
        logger.error("Make sure kaggle.json is at ~/.kaggle/kaggle.json")
        return False
    except FileNotFoundError:
        logger.error("Kaggle CLI not installed. Run: pip install kaggle")
        return False


def process_transaction_data(csv_path: str, output_path: str = "data/raw/transaction_labels.csv"):
    """Extract descriptions and categories from Kaggle dataset."""
    logger.info(f"Processing {csv_path}...")

    df = pd.read_csv(csv_path)

    # Map Kaggle categories to our 12 categories
    category_mapping = {
        "Food & Drink": "Food and Dining",
        "Food and Drink": "Food and Dining",
        "Restaurants": "Food and Dining",
        "Shopping": "Shopping",
        "Groceries": "Food and Dining",
        "Electronics": "Shopping",
        "Clothing": "Shopping",
        "Home": "Shopping",
        "Travel": "Travel",
        "Transportation": "Travel",
        "Utilities": "Utilities",
        "Personal Care": "Healthcare",
        "Health & Fitness": "Healthcare",
        "Entertainment": "Entertainment",
        "Movies": "Entertainment",
        "Insurance": "Insurance",
        "Investment": "Investment",
        "Transfer": "Transfer",
        "Other": "Other",
    }

    # Extract relevant columns (adjust based on actual dataset structure)
    if "Merchant" in df.columns and "Category" in df.columns:
        df_subset = df[["Merchant", "Category"]].copy()
        df_subset.columns = ["description", "category"]
    elif "Description" in df.columns and "Category" in df.columns:
        df_subset = df[["Description", "Category"]].copy()
        df_subset.columns = ["description", "category"]
    else:
        logger.error(f"Dataset columns not recognized: {df.columns.tolist()}")
        return False

    # Map categories
    df_subset["category"] = df_subset["category"].map(category_mapping)

    # Remove unmapped categories
    df_subset = df_subset.dropna(subset=["category"])

    # Remove duplicates
    df_subset = df_subset.drop_duplicates(subset=["description"])

    # Shuffle
    df_subset = df_subset.sample(frac=1).reset_index(drop=True)

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df_subset.to_csv(output_path, index=False)

    logger.info(f"Processed {len(df_subset)} unique transactions")
    logger.info(f"Category distribution:\n{df_subset['category'].value_counts()}")
    logger.info(f"Saved to {output_path}")

    return True


if __name__ == "__main__":
    # Step 1: Download from Kaggle
    success = download_from_kaggle()

    if not success:
        logger.warning("Kaggle download failed. Manual download required.")
        logger.warning(f"Download from: https://www.kaggle.com/datasets/{KAGGLE_DATASET}")
        logger.warning(f"Extract to: {DOWNLOAD_PATH}/")

    # Step 2: Process the data
    # Adjust the CSV file path based on what Kaggle provides
    csv_files = list(Path(DOWNLOAD_PATH).glob("*.csv"))

    if csv_files:
        process_transaction_data(str(csv_files[0]))
    else:
        logger.error(f"No CSV files found in {DOWNLOAD_PATH}")
