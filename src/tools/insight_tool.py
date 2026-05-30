"""Financial insight generation tool."""

from typing import Dict, List
from loguru import logger


class InsightTool:
    """Generate financial insights from enriched transaction data."""

    def __init__(self):
        """Initialize insight generator."""
        logger.info("InsightTool ready")

    def calculate_health_score(self, enriched_transactions: List[Dict]) -> dict:
        """
        Calculate composite financial health score.

        Args:
            enriched_transactions: Transactions enriched with all tool outputs

        Returns:
            Health score metrics
        """
        if not enriched_transactions:
            return {
                "health_score": 0.5,
                "components": {
                    "confidence_score": 0.5,
                    "anomaly_score": 0.5,
                    "regularity_score": 0.5,
                    "category_diversity": 0.5
                }
            }

        # Extract metrics
        confidences = []
        anomalies = []
        categories = set()

        for tx in enriched_transactions:
            enrichment = tx.get("enrichment", {})
            anomaly = tx.get("anomaly", {})

            if enrichment:
                confidences.append(enrichment.get("confidence", 0.5))
                categories.add(enrichment.get("category", "Other"))

            if anomaly:
                anomalies.append(1.0 if anomaly.get("is_anomaly", False) else 0.0)

        # Calculate component scores
        confidence_score = sum(confidences) / len(confidences) if confidences else 0.5
        anomaly_rate = sum(anomalies) / len(anomalies) if anomalies else 0.0
        anomaly_score = 1.0 - min(anomaly_rate, 0.2) / 0.2  # Penalize high anomaly rate
        category_diversity = min(len(categories) / 12.0, 1.0)  # Score up to 12 categories

        # Regularity: prefer recurring transactions (stable pattern)
        regularity_score = 0.5 + (0.5 * min(len(enriched_transactions) / 100.0, 1.0))

        # Composite health score (weighted average)
        health_score = (
            confidence_score * 0.3 +  # Model confidence
            anomaly_score * 0.3 +     # Low anomaly rate
            category_diversity * 0.2 +  # Diverse spending
            regularity_score * 0.2     # Regular patterns
        )

        return {
            "health_score": float(health_score),
            "components": {
                "confidence_score": float(confidence_score),
                "anomaly_score": float(anomaly_score),
                "category_diversity": float(category_diversity),
                "regularity_score": float(regularity_score)
            },
            "metrics": {
                "avg_confidence": float(confidence_score),
                "anomaly_rate": float(anomaly_rate),
                "num_categories": len(categories),
                "num_transactions": len(enriched_transactions)
            }
        }

    def generate_insights(self, enriched_transactions: List[Dict]) -> List[str]:
        """Generate human-readable financial insights."""
        insights = []

        if not enriched_transactions:
            return ["No transaction data available."]

        # Extract metrics
        total_amount = sum(tx.get("amount", 0) for tx in enriched_transactions)
        categories = {}
        anomaly_count = 0
        low_confidence_count = 0

        for tx in enriched_transactions:
            enrichment = tx.get("enrichment", {})
            anomaly = tx.get("anomaly", {})

            category = enrichment.get("category", "Other")
            categories[category] = categories.get(category, 0) + 1

            if enrichment.get("is_low_confidence", False):
                low_confidence_count += 1

            if anomaly.get("is_anomaly", False):
                anomaly_count += 1

        # Generate insights
        # Insight 1: Spending pattern
        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else "Unknown"
        insights.append(f"Top spending category: {top_category} ({categories.get(top_category, 0)} transactions)")

        # Insight 2: Anomaly rate
        anomaly_rate = anomaly_count / len(enriched_transactions) if enriched_transactions else 0
        if anomaly_rate > 0.1:
            insights.append(f"⚠️  High anomaly rate ({anomaly_rate*100:.1f}%): Review unusual transactions")
        elif anomaly_rate > 0.05:
            insights.append(f"📊 Moderate anomaly rate ({anomaly_rate*100:.1f}%): Some unusual patterns detected")
        else:
            insights.append("✓ Low anomaly rate: Healthy transaction patterns")

        # Insight 3: Model confidence
        confidence_rate = (len(enriched_transactions) - low_confidence_count) / len(enriched_transactions)
        if confidence_rate < 0.8:
            insights.append(f"⚠️  Model confidence low ({confidence_rate*100:.1f}%): Some categories uncertain")
        else:
            insights.append(f"✓ High model confidence ({confidence_rate*100:.1f}%): Categories well-classified")

        # Insight 4: Category diversity
        num_categories = len(categories)
        if num_categories < 3:
            insights.append(f"📊 Low category diversity ({num_categories}/12): Concentrated spending")
        elif num_categories < 6:
            insights.append(f"📊 Moderate category diversity ({num_categories}/12): Typical pattern")
        else:
            insights.append(f"✓ High category diversity ({num_categories}/12): Well-distributed spending")

        # Insight 5: Total activity
        insights.append(f"Total transactions analyzed: {len(enriched_transactions)}")

        return insights

    def __call__(self, enriched_transactions: List[Dict]) -> dict:
        """Generate comprehensive financial insights."""
        health = self.calculate_health_score(enriched_transactions)
        insights = self.generate_insights(enriched_transactions)

        return {
            "health_score": health["health_score"],
            "components": health["components"],
            "metrics": health.get("metrics", {}),
            "insights": insights,
            "num_insights": len(insights),
            "tool": "insight_tool"
        }


# Singleton instance
_insight_tool_instance = InsightTool()


def insight_tool(enriched_transactions: List[Dict]) -> dict:
    """
    Generate financial insights from enriched transactions.

    Args:
        enriched_transactions: List of transactions enriched with:
            - enrichment: {category, confidence, is_low_confidence}
            - anomaly: {is_anomaly, anomaly_score, severity}

    Returns:
        dict with keys:
        - health_score: 0.0-1.0 composite financial health
        - components: Score breakdown
        - metrics: Quantitative metrics
        - insights: List of human-readable insights
        - num_insights: Number of insights generated
        - tool: "insight_tool"

    Example:
        >>> txs = [{"amount": 50, "enrichment": {...}, "anomaly": {...}}]
        >>> result = insight_tool(txs)
        >>> print(result['health_score'])
        0.75
        >>> print(result['insights'])
        [...]
    """
    return _insight_tool_instance(enriched_transactions)
