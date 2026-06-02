"""Assemble the isolated build context for the public DEMO image.

Produces deploy/demo_build/ containing:
  - src/                                   (copied from repo)
  - requirements-api.txt                   (copied from repo)
  - Dockerfile                             (copied from deploy/Dockerfile.demo)
  - data/processed/transactions/data.parquet   (~50k stratified sample)
  - data/models/                           (fine-tuned FinBERT + fraud .pkl)
  - .gcloudignore                          (so `gcloud run deploy --source` uploads everything here)

Why a sample? The full 6.3M-row parquet (290 MB) would balloon memory when DuckDB
loads it alongside torch + FinBERT. A stratified ~50k-row sample (ALL fraud rows +
random legit) keeps the schema, keeps the fraud page populated, and fits a 2 GB
Cloud Run instance comfortably.

Run:  python scripts/prepare_demo.py
Then: cd deploy/demo_build && gcloud run deploy ... --source .   (in your PERSONAL project)
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
REQ = ROOT / "requirements-api.txt"
DOCKERFILE_DEMO = ROOT / "deploy" / "Dockerfile.demo"
FULL_PARQUET = ROOT / "data" / "processed" / "transactions" / "data.parquet"
MODELS = ROOT / "data" / "models"

BUILD = ROOT / "deploy" / "demo_build"
SAMPLE_LEGIT = 45_000  # legit rows; ALL fraud rows are always included
SEED = 42


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    # --- preconditions -----------------------------------------------------
    for p in (SRC, REQ, DOCKERFILE_DEMO, FULL_PARQUET, MODELS):
        if not p.exists():
            fail(f"required path missing: {p}")

    finbert = MODELS / "finbert-transaction"
    fraud_pkl = MODELS / "fraud_classifier.pkl"
    if not finbert.exists():
        fail(f"fine-tuned FinBERT not found: {finbert}")
    if not fraud_pkl.exists():
        fail(f"fraud model not found: {fraud_pkl}")

    # --- clean + recreate the build context --------------------------------
    if BUILD.exists():
        print(f"removing existing {BUILD}")
        shutil.rmtree(BUILD)
    (BUILD / "data" / "processed" / "transactions").mkdir(parents=True)
    (BUILD / "data" / "models").mkdir(parents=True)

    # --- stratified sample -------------------------------------------------
    print(f"reading {FULL_PARQUET} ...")
    df = pd.read_parquet(FULL_PARQUET)
    print(f"  full rows: {len(df):,}")
    if "isFraud" not in df.columns:
        fail("expected column 'isFraud' not in parquet")

    fraud = df[df["isFraud"] == 1]
    legit = df[df["isFraud"] == 0]
    legit_n = min(SAMPLE_LEGIT, len(legit))
    sample = (
        pd.concat([fraud, legit.sample(n=legit_n, random_state=SEED)])
        .sample(frac=1.0, random_state=SEED)  # shuffle
        .reset_index(drop=True)
    )
    out_parquet = BUILD / "data" / "processed" / "transactions" / "data.parquet"
    sample.to_parquet(out_parquet, index=False)
    print(
        f"  sample written: {len(sample):,} rows "
        f"({len(fraud):,} fraud + {legit_n:,} legit) -> {out_parquet.name} "
        f"({out_parquet.stat().st_size / 1e6:.1f} MB)"
    )

    # --- copy code + deps + Dockerfile -------------------------------------
    print("copying src/ ...")
    shutil.copytree(SRC, BUILD / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(REQ, BUILD / "requirements-api.txt")
    shutil.copy2(DOCKERFILE_DEMO, BUILD / "Dockerfile")

    # --- copy models (the heavy bit) ---------------------------------------
    print(f"copying FinBERT model ({finbert.name}) ...")
    shutil.copytree(finbert, BUILD / "data" / "models" / "finbert-transaction")
    shutil.copy2(fraud_pkl, BUILD / "data" / "models" / "fraud_classifier.pkl")

    # --- .gcloudignore so the upload includes data/ + models ---------------
    (BUILD / ".gcloudignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")

    total_mb = sum(f.stat().st_size for f in BUILD.rglob("*") if f.is_file()) / 1e6
    print("\nDONE.")
    print(f"  context: {BUILD}  (~{total_mb:.0f} MB)")
    print("  next:")
    print("    cd deploy/demo_build")
    print('    gcloud run deploy finflow-demo --source . --region us-central1 \\')
    print("      --allow-unauthenticated --memory 2Gi --cpu 2 --timeout 600 --max-instances 2 \\")
    print('      --set-env-vars "GROQ_API_KEY=<your-key>,FRONTEND_ORIGINS=*"')


if __name__ == "__main__":
    main()
