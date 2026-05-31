"""Hallucination detection using grounding score."""

import re
from loguru import logger


class HallucinationGuard:
    """Validates LLM output against tool results for grounding."""

    def __init__(self, grounding_threshold: float = 0.85):
        """Initialize guard with grounding threshold.

        Args:
            grounding_threshold: Min grounding score (0.0-1.0) to accept response
        """
        self.threshold = grounding_threshold

    def compute_grounding_score(
        self,
        response: str,
        enriched_results: list[dict],
        anomaly_results: list[dict],
        cashflow_results: dict,
        insights: dict
    ) -> float:
        """Compute grounding score between LLM response and tool outputs.

        Checks:
        1. Category mentions match enriched results
        2. Anomaly claims backed by scores
        3. Financial health score consistency
        4. No invented metrics

        Returns:
            Grounding score 0.0-1.0
        """
        checks_passed = 0
        checks_total = 0

        # Check 1: Category mentions
        if enriched_results:
            categories = [r.get("category") for r in enriched_results if r.get("category")]
            checks_total += 1
            mentioned_categories = sum(
                1 for cat in categories
                if cat and cat.lower() in response.lower()
            )
            if mentioned_categories > 0:
                checks_passed += 1
            logger.debug(f"Category check: {mentioned_categories}/{len(categories)} mentioned")

        # Check 2: Anomaly backing
        if anomaly_results:
            checks_total += 1
            anomalies = [r for r in anomaly_results if r.get("is_anomaly")]
            if anomalies:
                # Must mention anomaly if it exists
                if "anomaly" in response.lower() or "suspicious" in response.lower():
                    checks_passed += 1
                logger.debug(f"Anomaly check: {len(anomalies)} anomalies found")
            else:
                checks_passed += 1
                logger.debug("Anomaly check: no anomalies, response consistent")

        # Check 3: Financial health score
        if insights:
            checks_total += 1
            health_score = insights.get("overall_health_score", 0.0)
            # Extract any mentioned score
            score_match = re.search(r"(?:score|rating|health)[\s:]*(\d+\.?\d*)", response.lower())
            if score_match:
                mentioned_score = float(score_match.group(1))
                # Allow ±0.15 variance
                if abs(mentioned_score - (health_score * 100)) < 15:
                    checks_passed += 1
                logger.debug(f"Health score check: {mentioned_score:.0f} vs {health_score*100:.0f}")
            else:
                # If no score mentioned, check qualitative consistency
                if health_score > 0.7:
                    if "good" in response.lower() or "healthy" in response.lower():
                        checks_passed += 1
                elif health_score < 0.4:
                    if "poor" in response.lower() or "concerning" in response.lower():
                        checks_passed += 1
                else:
                    if "moderate" in response.lower() or "fair" in response.lower():
                        checks_passed += 1

        # Check 4: No invented metrics
        checks_total += 1
        invented_patterns = [
            r"\d+\.\d+%\s+(?:increase|decrease)",  # Invented % changes
            r"(?:exactly|precisely)\s+\$\d+,\d+",  # Over-specific amounts
        ]
        if not any(re.search(pat, response) for pat in invented_patterns):
            checks_passed += 1
            logger.debug("Invented metrics check: passed")
        else:
            logger.debug("Invented metrics check: failed - suspicious patterns found")

        # Compute grounding score
        score = checks_passed / checks_total if checks_total > 0 else 0.0
        logger.info(f"Grounding score: {score:.2f} ({checks_passed}/{checks_total} checks)")
        return score

    def validate(
        self,
        response: str,
        enriched_results: list[dict],
        anomaly_results: list[dict],
        cashflow_results: dict,
        insights: dict
    ) -> tuple[bool, float, str]:
        """Validate LLM response against tool results.

        Returns:
            (is_valid, grounding_score, reason)
        """
        score = self.compute_grounding_score(
            response, enriched_results, anomaly_results, cashflow_results, insights
        )

        if score >= self.threshold:
            return True, score, f"Response grounded (score: {score:.2f})"
        else:
            return False, score, (
                f"Response not sufficiently grounded (score: {score:.2f}, "
                f"threshold: {self.threshold}). May contain hallucinations."
            )
