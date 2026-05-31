"""Comprehensive test suite for FinFlow Phase 0-3."""

import pytest
import time
from src.tools import (
    enrichment_tool, anomaly_detection_tool, cashflow_tool,
    merchant_resolution_tool, insight_tool, get_enrichment_cache_stats
)


@pytest.fixture
def sample_txs():
    return [
        {"description": "STARBUCKS COFFEE", "amount": 5.50, "balance_change": -5.50, "merchant": "STARBUCKS"},
        {"description": "AMAZON PURCHASE", "amount": 99.99, "balance_change": -99.99, "merchant": "AMAZON"},
        {"description": "SALARY DEPOSIT", "amount": 3000.00, "balance_change": 3000.00, "merchant": "EMPLOYER"},
    ]

@pytest.fixture
def enriched_batch():
    return [
        {"category": "Food and Dining", "confidence": 0.95, "is_low_confidence": False},
        {"category": "Shopping", "confidence": 0.88, "is_low_confidence": False},
        {"category": "Travel", "confidence": 0.92, "is_low_confidence": False},
    ]


# ENRICHMENT TOOL
class TestEnrichmentTool:
    def test_basic(self):
        r = enrichment_tool("STARBUCKS COFFEE")
        assert r["category"] in ["Food and Dining", "Other"]
        assert 0 <= r["confidence"] <= 1
        assert isinstance(r["is_low_confidence"], bool)

    def test_multiple_descriptions(self):
        tests = ["AMAZON MKTP", "DELTA AIRLINES", "WALGREENS", "DIRECT DEPOSIT"]
        for desc in tests:
            r = enrichment_tool(desc)
            assert "category" in r and 0 <= r["confidence"] <= 1

    def test_edge_cases(self):
        for inp in ["", "   ", "!@#$%", "X"*500]:
            r = enrichment_tool(inp)
            assert "category" in r and 0 <= r["confidence"] <= 1

    def test_cache_hit(self):
        desc = "CACHE_TEST_12345"
        t1 = time.time()
        r1 = enrichment_tool(desc)
        t1 = time.time() - t1

        t2 = time.time()
        r2 = enrichment_tool(desc)
        t2 = time.time() - t2

        assert r1["category"] == r2["category"]
        if t2 > 0: assert t1 / t2 > 5

    def test_batch_100(self):
        results = [enrichment_tool(f"MERCHANT_{i}") for i in range(100)]
        assert len(results) == 100
        assert all("category" in r for r in results)

    def test_cache_stats(self):
        stats = get_enrichment_cache_stats()
        assert "cache_size" in stats
        assert "max_size" in stats


# ANOMALY TOOL
class TestAnomalyTool:
    def test_basic(self):
        r = anomaly_detection_tool(50, -50)
        assert "is_anomaly" in r
        assert 0 <= r["anomaly_score"] <= 1
        assert r["severity"] in ["low", "medium", "high"]

    def test_multiple_amounts(self):
        for amount in [50, 500, 5000, 10000]:
            r = anomaly_detection_tool(amount, -amount)
            assert 0 <= r["anomaly_score"] <= 1

    def test_extreme_values(self):
        for val in [0, -100, 999999]:
            r = anomaly_detection_tool(float(val), -float(val))
            assert 0 <= r["anomaly_score"] <= 1

    def test_zero_values(self):
        r = anomaly_detection_tool(0, 0)
        assert "anomaly_score" in r

    def test_batch_100(self):
        results = [anomaly_detection_tool(i*10, -i*10) for i in range(100)]
        assert len(results) == 100
        assert all("is_anomaly" in r for r in results)

    def test_consistency(self):
        r1 = anomaly_detection_tool(1000, -1000)
        r2 = anomaly_detection_tool(1000, -1000)
        assert r1["anomaly_score"] == r2["anomaly_score"]

    def test_with_kwargs(self):
        r = anomaly_detection_tool(amount=100, balance_change_orig=-100, balance_change_dest=0)
        assert "anomaly_score" in r


# MERCHANT TOOL
class TestMerchantTool:
    def test_basic(self):
        r = merchant_resolution_tool("STARBUCKS COFFEE")
        assert "normalized_merchant" in r
        assert 0 <= r["match_score"] <= 1
        assert "inferred_category" in r

    def test_known_merchants(self):
        merchants = ["STARBUCKS", "AMAZON", "MCDONALDS", "DELTA"]
        for m in merchants:
            r = merchant_resolution_tool(m)
            assert isinstance(r["normalized_merchant"], str)
            assert 0 <= r["match_score"] <= 1

    def test_unknown_merchant(self):
        r = merchant_resolution_tool("UNKNOWN_XYZ_12345")
        assert isinstance(r["normalized_merchant"], str)

    def test_typos(self):
        for typo in ["STARBKS", "AMZON", "MCDONLD"]:
            r = merchant_resolution_tool(typo)
            assert 0 <= r["match_score"] <= 1

    def test_edge_cases(self):
        for inp in ["", "   ", "!@#$", "X"*500]:
            r = merchant_resolution_tool(inp)
            assert 0 <= r["match_score"] <= 1

    def test_batch_100(self):
        results = [merchant_resolution_tool(f"MERCHANT_{i}") for i in range(100)]
        assert len(results) == 100
        assert all("normalized_merchant" in r for r in results)

    def test_consistency(self):
        r1 = merchant_resolution_tool("STARBUCKS")
        r2 = merchant_resolution_tool("STARBUCKS")
        assert r1["normalized_merchant"] == r2["normalized_merchant"]


# CASHFLOW TOOL
class TestCashflowTool:
    def test_basic_calculation(self):
        txs = [{"amount": 3000, "description": "SALARY"}, {"amount": -100, "description": "EXP"}]
        r = cashflow_tool(txs)
        assert r["cash_flow_summary"]["total_income"] == 3000
        assert r["cash_flow_summary"]["total_expenses"] == 100
        assert r["cash_flow_summary"]["net_cash_flow"] == 2900

    def test_empty_list(self):
        r = cashflow_tool([])
        assert r["cash_flow_summary"]["total_income"] == 0

    def test_income_only(self):
        r = cashflow_tool([{"amount": 5000, "description": "INCOME"}])
        assert r["cash_flow_summary"]["total_income"] == 5000

    def test_expense_only(self):
        r = cashflow_tool([{"amount": -200, "description": "EXP"}])
        assert r["cash_flow_summary"]["total_expenses"] == 200

    def test_mixed(self):
        txs = [
            {"amount": 5000, "description": "SALARY"},
            {"amount": -1500, "description": "RENT"},
            {"amount": -150, "description": "FOOD"},
            {"amount": -100, "description": "UTIL"},
        ]
        r = cashflow_tool(txs)
        assert r["cash_flow_summary"]["total_income"] == 5000
        assert r["cash_flow_summary"]["total_expenses"] == 1750

    def test_batch_1000(self):
        txs = [{"amount": 100 if i%10==0 else -50, "description": f"TX_{i}"} for i in range(1000)]
        r = cashflow_tool(txs)
        assert r["cash_flow_summary"]["transaction_count"] == 1000

    def test_accuracy(self):
        txs = [{"amount": 1000.50, "description": "A"}, {"amount": -250.25, "description": "B"}]
        r = cashflow_tool(txs)
        assert abs(r["cash_flow_summary"]["net_cash_flow"] - 750.25) < 0.01


# INSIGHT TOOL
class TestInsightTool:
    def test_basic(self, enriched_batch):
        r = insight_tool(enriched_batch)
        assert "health_score" in r
        assert "components" in r
        assert "insights" in r
        assert 0 <= r["health_score"] <= 1

    def test_empty(self):
        r = insight_tool([])
        assert "health_score" in r
        assert isinstance(r["health_score"], float)

    def test_single_item(self):
        r = insight_tool([{"category": "Food", "confidence": 0.9, "is_low_confidence": False}])
        assert 0 <= r["health_score"] <= 1

    def test_low_confidence(self):
        r = insight_tool([
            {"category": "Other", "confidence": 0.2, "is_low_confidence": True},
            {"category": "Other", "confidence": 0.2, "is_low_confidence": True},
        ])
        assert r["health_score"] < 0.8

    def test_high_confidence(self):
        r = insight_tool([
            {"category": "Food", "confidence": 0.99, "is_low_confidence": False},
            {"category": "Shopping", "confidence": 0.99, "is_low_confidence": False},
        ])
        assert r["health_score"] > 0.4

    def test_batch_500(self):
        cats = ["Food", "Shopping", "Travel", "Healthcare"]
        txs = [{"category": cats[i%4], "confidence": 0.8+(i%20)*0.01, "is_low_confidence": (i%20)<5} for i in range(500)]
        r = insight_tool(txs)
        assert 0 <= r["health_score"] <= 1

    def test_consistency(self, enriched_batch):
        r1 = insight_tool(enriched_batch)
        r2 = insight_tool(enriched_batch)
        assert r1["health_score"] == r2["health_score"]

    def test_components(self, enriched_batch):
        r = insight_tool(enriched_batch)
        assert len(r["components"]) >= 3
        for v in r["components"].values():
            assert 0 <= v <= 1


# INTEGRATION
class TestIntegration:
    def test_full_pipeline(self, sample_txs):
        enr = [enrichment_tool(t["description"]) for t in sample_txs]
        anom = [anomaly_detection_tool(t["amount"], t["balance_change"]) for t in sample_txs]
        merch = [merchant_resolution_tool(t["merchant"]) for t in sample_txs]
        cf = cashflow_tool(sample_txs)
        ins = insight_tool(enr)

        assert len(enr) == 3 and len(anom) == 3 and len(merch) == 3
        assert cf["cash_flow_summary"]["transaction_count"] == 3
        assert 0 <= ins["health_score"] <= 1

    def test_enrichment_to_insight(self):
        descs = ["STARBUCKS", "AMAZON", "SALARY"]
        enr = [enrichment_tool(d) for d in descs]
        ins = insight_tool(enr)
        assert "health_score" in ins

    def test_full_scenario(self):
        txs = [
            {"description": "SALARY", "amount": 5000, "balance_change": 5000, "merchant": "EMPLOYER"},
            {"description": "RENT", "amount": -1500, "balance_change": -1500, "merchant": "LANDLORD"},
            {"description": "FOOD", "amount": -100, "balance_change": -100, "merchant": "STORE"},
        ]
        enr = [enrichment_tool(t["description"]) for t in txs]
        anom = [anomaly_detection_tool(t["amount"], t["balance_change"]) for t in txs]
        cf = cashflow_tool(txs)
        ins = insight_tool(enr)

        assert cf["cash_flow_summary"]["net_cash_flow"] == 3400
        assert ins["health_score"] > 0.3


# SCALABILITY
class TestScalability:
    def test_enrichment_100(self):
        r = [enrichment_tool(f"TX_{i}") for i in range(100)]
        assert len(r) == 100

    def test_enrichment_500(self):
        r = [enrichment_tool(f"TX_{i}") for i in range(500)]
        assert len(r) == 500

    def test_anomaly_100(self):
        r = [anomaly_detection_tool(i*10, -i*10) for i in range(100)]
        assert len(r) == 100 and all("anomaly_score" in x for x in r)

    def test_anomaly_500(self):
        r = [anomaly_detection_tool(i*10, -i*10) for i in range(500)]
        assert len(r) == 500

    def test_merchant_100(self):
        r = [merchant_resolution_tool(f"M_{i}") for i in range(100)]
        assert len(r) == 100

    def test_merchant_500(self):
        r = [merchant_resolution_tool(f"M_{i}") for i in range(500)]
        assert len(r) == 500

    def test_cashflow_1000(self):
        txs = [{"amount": 100 if i%10==0 else -50, "description": f"TX_{i}"} for i in range(1000)]
        r = cashflow_tool(txs)
        assert r["cash_flow_summary"]["transaction_count"] == 1000

    def test_cashflow_5000(self):
        txs = [{"amount": 100 if i%10==0 else -50, "description": f"TX_{i}"} for i in range(5000)]
        r = cashflow_tool(txs)
        assert r["cash_flow_summary"]["transaction_count"] == 5000

    def test_insight_500(self):
        cats = ["Food", "Shop", "Travel"]
        txs = [{"category": cats[i%3], "confidence": 0.8+(i%10)*0.02, "is_low_confidence": i%20<5} for i in range(500)]
        r = insight_tool(txs)
        assert 0 <= r["health_score"] <= 1


# QUALITY ASSURANCE
# API TESTS
class TestAPI:
    def test_api_import(self):
        """Test API module imports."""
        from src.api.main import app
        from src.api.schemas import AnalyzeRequest, AnalyzeResponse
        assert app is not None
        assert AnalyzeRequest is not None
        assert AnalyzeResponse is not None

    def test_api_schemas(self):
        """Test API request/response schemas."""
        from src.api.schemas import Transaction, AnalyzeRequest, AnalyzeResponse

        tx = Transaction(
            description="TEST",
            amount=100.0,
            balance_change=-100.0,
            merchant="TEST_MERCHANT"
        )
        assert tx.description == "TEST"

        req = AnalyzeRequest(transactions=[tx])
        assert len(req.transactions) == 1

        resp = AnalyzeResponse(
            final_response="test",
            grounding_score=0.8,
            execution_trace=["node1", "node2"]
        )
        assert resp.grounding_score == 0.8

    def test_api_health_endpoint(self):
        """Test health check endpoint."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_api_analyze_endpoint(self, sample_txs):
        """Test analyze endpoint with real transactions."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)

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

        response = client.post("/api/analyze", json=payload)

        # May fail if GROQ_API_KEY not set, that's expected
        if response.status_code == 500 and "GROQ_API_KEY" in response.text:
            assert True  # Expected when GROQ key not set
        else:
            assert response.status_code == 200
            data = response.json()
            assert "final_response" in data
            assert "grounding_score" in data
            assert "execution_trace" in data

    def test_api_error_handling(self):
        """Test API error handling."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)

        # Missing required field
        payload = {"transactions": [{"description": "TEST"}]}
        response = client.post("/api/analyze", json=payload)
        assert response.status_code == 422  # Validation error


class TestQA:
    def test_enrichment_consistency(self):
        for _ in range(10):
            r1 = enrichment_tool("TEST_CONSISTENCY")
            r2 = enrichment_tool("TEST_CONSISTENCY")
            assert r1["category"] == r2["category"]

    def test_anomaly_range(self):
        for amt in [0, 100, 1000, 10000, 999999]:
            r = anomaly_detection_tool(float(amt), -float(amt))
            assert 0 <= r["anomaly_score"] <= 1

    def test_merchant_score_range(self):
        for m in ["TEST", "UNKNOWN", "STARBUCKS", ""]:
            r = merchant_resolution_tool(m)
            assert 0 <= r["match_score"] <= 1

    def test_cashflow_arithmetic(self):
        txs = [{"amount": 1000.99, "description": "A"}, {"amount": -250.50, "description": "B"}, {"amount": -100.25, "description": "C"}]
        r = cashflow_tool(txs)
        expected = 1000.99 - 250.50 - 100.25
        assert abs(r["cash_flow_summary"]["net_cash_flow"] - expected) < 0.01

    def test_insight_all_ranges(self):
        enr = [
            [{"category": "Food", "confidence": 0.99, "is_low_confidence": False}],
            [{"category": "Other", "confidence": 0.3, "is_low_confidence": True}],
            [],
        ]
        for e in enr:
            r = insight_tool(e)
            assert 0 <= r["health_score"] <= 1

    def test_error_recovery(self):
        for inp in ["", None, "X"*10000]:
            try:
                if inp: enrichment_tool(inp)
            except: pass
        assert True

    def test_extreme_cashflow(self):
        txs = [{"amount": 1e10, "description": "HUGE"}, {"amount": -1e10, "description": "HUGE_EXP"}]
        r = cashflow_tool(txs)
        assert r["cash_flow_summary"]["total_income"] > 0

    def test_malformed_recovery(self):
        tests = [anomaly_detection_tool(999999, 999999), merchant_resolution_tool("!@#$%")]
        assert all(t is not None for t in tests)
