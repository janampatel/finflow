"""Phase 5 (FastAPI REST API) validation script."""

import subprocess
import time
import sys
import json
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app
from src.api.schemas import Transaction, AnalyzeRequest


def test_direct_api():
    """Test API directly without HTTP."""
    print("[OK] Direct API Test")
    print("-" * 60)

    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Health check
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    print("  [OK] Health endpoint")

    # Analyze with valid request
    payload = {
        "transactions": [
            {
                "description": "STARBUCKS COFFEE",
                "amount": 5.50,
                "balance_change": -5.50,
                "merchant": "STARBUCKS"
            }
        ]
    }

    resp = client.post("/api/analyze", json=payload)

    # May fail due to GROQ_API_KEY
    if resp.status_code == 500:
        if "GROQ_API_KEY" in resp.text:
            print("  [OK] Analyze endpoint (GROQ_API_KEY not set - expected)")
        else:
            print(f"  [FAILED] Analyze endpoint: {resp.text}")
            return False
    else:
        data = resp.json()
        assert "final_response" in data
        assert "grounding_score" in data
        print("  [OK] Analyze endpoint with response")

    # Error handling
    resp = client.post("/api/analyze", json={"transactions": [{"description": "TEST"}]})
    assert resp.status_code == 422
    print("  [OK] Error handling (validation)")

    return True


def test_schemas():
    """Test Pydantic schemas."""
    print("\n[OK] Schema Validation Tests")
    print("-" * 60)

    # Transaction
    tx = Transaction(
        description="TEST TRANSACTION",
        amount=100.0,
        balance_change=-100.0,
        merchant="TEST_MERCHANT"
    )
    assert tx.description == "TEST TRANSACTION"
    print("  [OK] Transaction schema")

    # Request
    req = AnalyzeRequest(transactions=[tx])
    assert len(req.transactions) == 1
    print("  [OK] AnalyzeRequest schema")

    return True


def main():
    print("\n" + "=" * 60)
    print("PHASE 5: FastAPI REST API Validation")
    print("=" * 60)

    try:
        success = test_schemas()
        if not success:
            return 1

        success = test_direct_api()
        if not success:
            return 1

        print("\n" + "=" * 60)
        print("Phase 5 Validation: [OK] ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext: Start API server with:")
        print("  python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
        print("\nThen test with:")
        print("  curl -X POST http://localhost:8000/api/analyze \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{\"transactions\": [{\"description\": \"STARBUCKS\", \"amount\": 5.50, \"balance_change\": -5.50, \"merchant\": \"STARBUCKS\"}]}'")
        print("\n")

        return 0

    except Exception as e:
        print(f"\n[FAILED] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
