"""Generate 12k synthetic transaction descriptions for FinBERT fine-tuning."""

import csv
from pathlib import Path
from faker import Faker
import random
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

MERCHANTS = {
    "Food and Dining": [
        "STARBUCKS", "MCDONALD'S", "SUBWAY", "CHIPOTLE", "PANERA",
        "PIZZAHUT", "KFC", "DOMINOS", "TACO BELL", "BURGER KING",
        "WHOLE FOODS", "TRADER JOE'S", "SAFEWAY", "KROGER", "WALMART"
    ],
    "Shopping": [
        "AMAZON", "WALMART", "TARGET", "BESTBUY", "COSTCO",
        "ROSS", "TJMAXX", "H&M", "ZARA", "FOREVER 21",
        "GAP", "UNIQLO", "NIKE", "ADIDAS", "APPLE"
    ],
    "Travel": [
        "DELTA AIRLINES", "UNITED AIRLINES", "SOUTHWEST AIRLINES",
        "AMERICAN AIRLINES", "EXPEDIA", "BOOKING.COM",
        "AIRBNB", "UBER", "LYFT", "RENTAL CAR", "HILTON", "MARRIOTT"
    ],
    "Healthcare": [
        "WALGREENS", "CVS PHARMACY", "RITE AID",
        "DOCTOR CLINIC", "HOSPITAL", "DENTAL",
        "VISION CENTER", "PHARMACY", "URGENT CARE"
    ],
    "Utilities": [
        "ELECTRIC COMPANY", "WATER UTILITY", "GAS COMPANY",
        "INTERNET SERVICE", "PHONE COMPANY", "CABLE TV"
    ],
    "Income / Direct Deposit": [
        "DIRECT DEPOSIT PAYROLL", "EMPLOYER", "SALARY",
        "ACH CREDIT", "WAGE PAYMENT"
    ],
    "Transfer": [
        "ATM WITHDRAWAL", "TRANSFER OUT", "BANK TRANSFER",
        "P2P TRANSFER", "WIRE TRANSFER"
    ],
    "Refund": [
        "AMAZON REFUND", "STORE RETURN", "REFUND",
        "CREDIT ADJUSTMENT", "REVERSAL"
    ],
    "Entertainment": [
        "NETFLIX", "SPOTIFY", "DISNEY+", "HULU", "MOVIE THEATER",
        "CONCERT TICKETS", "GAMING", "PLAYSTATION", "XBOX", "STEAM"
    ],
    "Insurance": [
        "AUTO INSURANCE", "HOME INSURANCE", "HEALTH INSURANCE",
        "LIFE INSURANCE", "UMBRELLA INSURANCE"
    ],
    "Investment": [
        "STOCK BROKERAGE", "MUTUAL FUND", "ETF PURCHASE",
        "CRYPTO EXCHANGE", "401K CONTRIBUTION"
    ],
    "Other": [
        "MISCELLANEOUS", "UNKNOWN", "OTHER CHARGE", "ADJUSTMENT"
    ]
}


def generate_description(category: str, merchant_name: str) -> str:
    """Generate realistic-looking transaction description."""
    templates = [
        f"{merchant_name} {random.randint(1000, 9999)}",
        f"{merchant_name}",
        f"{merchant_name.upper()} #{random.randint(100, 999)}",
        f"SQ*{merchant_name} {random.randint(1000, 9999)}",
        f"*{merchant_name.upper()} {random.randint(100, 999)}",
        f"{merchant_name.upper()} STORE #{random.randint(10, 99)}",
    ]
    return random.choice(templates)


def generate_synthetic_data(output_file: str = "data/raw/transaction_labels.csv", num_per_category: int = 1000):
    """Generate 12k synthetic transaction descriptions (1k per category)."""
    logger.info(f"Generating {len(CATEGORIES) * num_per_category} synthetic transactions...")

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for category in CATEGORIES:
        merchants = MERCHANTS.get(category, ["MERCHANT"])
        for _ in range(num_per_category):
            merchant = random.choice(merchants)
            description = generate_description(category, merchant)
            rows.append({"description": description, "category": category})

    random.shuffle(rows)

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["description", "category"])
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Generated {len(rows)} samples at {output_file}")

    total = len(rows)
    train_split = int(total * 0.8)
    val_split = int(total * 0.1)

    train = rows[:train_split]
    val = rows[train_split:train_split + val_split]
    test = rows[train_split + val_split:]

    logger.info(f"Split: {len(train)} train ({len(train)/total*100:.1f}%), "
                f"{len(val)} val ({len(val)/total*100:.1f}%), "
                f"{len(test)} test ({len(test)/total*100:.1f}%)")

    return rows, train, val, test


if __name__ == "__main__":
    rows, train, val, test = generate_synthetic_data()
    print(f"Total: {len(rows)} | Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
