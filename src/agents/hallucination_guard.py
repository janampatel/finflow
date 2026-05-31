"""Hallucination detection using grounding score."""

import re
from loguru import logger


class HallucinationGuard:
    """Validates LLM output against tool results for grounding."""

    def __init__(self, grounding_threshold: float = 0.85, min_transaction_count: int = 10):
        """Initialize guard with grounding threshold.

        Args:
            grounding_threshold: Min grounding score (0.0-1.0) to accept response
            min_transaction_count: Min transactions for pattern claims (default 10)
        """
        self.threshold = grounding_threshold
        self.min_txn_count = min_transaction_count

    def compute_grounding_score(
        self,
        response: str,
        enriched_results: list[dict],
        anomaly_results: list[dict],
        cashflow_results: dict,
        insights: dict
    ) -> float:
        """Compute grounding score between LLM response and tool outputs.

        Checks (STRICT):
        1. Category mentions match enriched results
        2. Anomaly claims backed by scores
        3. Health score matches exactly (±5%)
        4. No invented metrics or comparative claims on insufficient data
        5. No claims about "diversity", "patterns", "habits" with <10 txns
        6. All numbers traceable to tool outputs

        Returns:
            Grounding score 0.0-1.0
        """
        checks_passed = 0
        checks_total = 0

        # Get transaction count from insights
        txn_count = 1  # Default: assume 1 transaction (insufficient)
        if insights:
            metrics = insights.get("metrics", {})
            txn_count = metrics.get("num_transactions", 1)

        logger.debug(f"Checking response for {txn_count} transactions")

        # Check 0: DATA SUFFICIENCY CHECK (most important)
        checks_total += 1
        insufficient_data_claims = [
            r"(?:low|high|limited|concentrated)\s+(?:diversity|variety|spending)",
            r"(?:spending|transaction|spending)\s+(?:patterns|habits|behavior)",
            r"(?:lack|absence)\s+of\s+(?:diversity|variety)",
            r"concentration\s+of\s+(?:spending|transactions)",
            r"(?:spending|transaction)\s+distribution",
        ]

        has_insufficient_claims = any(
            re.search(pat, response, re.IGNORECASE)
            for pat in insufficient_data_claims
        )

        if txn_count < self.min_txn_count:
            if has_insufficient_claims:
                logger.warning(
                    f"Pattern/diversity claims made with only {txn_count} transactions (min {self.min_txn_count})"
                )
                # Fail this check - don't pass it
                logger.debug("Data sufficiency check: FAILED - comparative claims on insufficient data")
            else:
                checks_passed += 1
                logger.debug(f"Data sufficiency check: OK - no pattern claims with {txn_count} txns")
        else:
            checks_passed += 1
            logger.debug(f"Data sufficiency check: OK - {txn_count} transactions is sufficient")

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

        # Check 3: Financial health score (STRICT: ±5% only)
        if insights:
            checks_total += 1
            health_score = insights.get("health_score", 0.0)
            score_match = re.search(r"(?:score|health)[\s:]*(\d+\.?\d*)", response.lower())

            if score_match:
                mentioned_score = float(score_match.group(1))
                # STRICT: Must match within ±5% (not ±15%)
                expected_score = health_score * 100 if health_score < 2 else health_score
                if abs(mentioned_score - expected_score) <= 5:
                    checks_passed += 1
                    logger.debug(f"Health score check: {mentioned_score:.1f} vs {expected_score:.1f} ✓")
                else:
                    logger.debug(f"Health score check: {mentioned_score:.1f} vs {expected_score:.1f} ✗ (out of range)")
            else:
                # No score mentioned but claims about health
                if any(word in response.lower() for word in ["health", "score", "wellness"]):
                    logger.debug("Health score mentioned but number not found - FAIL")
                else:
                    checks_passed += 1
                    logger.debug("Health score check: no health claims made")

        # Check 4: No invented metrics
        checks_total += 1
        invented_patterns = [
            (r"\d+\.\d+%\s+(?:increase|decrease|growth|change)", "invented % change"),
            (r"(?:exactly|precisely)\s+\$\d+\.\d+", "over-specific amount"),
            (r"(?:approximately|around)\s+\d+%", "invented percentage"),
            (r"\d+(?:\.\d+)?\s+(?:categories|items|transactions)\s+analyzed", "invented count"),
        ]

        has_invented = False
        for pattern, description in invented_patterns:
            if re.search(pattern, response):
                logger.debug(f"Invented metrics check: found {description}")
                has_invented = True

        if not has_invented:
            checks_passed += 1
            logger.debug("Invented metrics check: passed")

        # Check 5: Extract and verify all numeric claims
        checks_total += 1
        numeric_claims = re.findall(r"(\d+\.?\d*)\s*(?:%|transactions?|dollars?|\$)", response)
        tool_numbers = set()

        # Collect all numbers from tools
        if enriched_results:
            for r in enriched_results:
                conf = r.get("confidence", 0)
                if isinstance(conf, float):
                    tool_numbers.add(f"{conf*100:.1f}")

        if insights:
            health = insights.get("health_score", 0)
            if isinstance(health, float):
                tool_numbers.add(f"{health*100:.1f}")
                tool_numbers.add(f"{health:.2f}")

        if insights:
            metrics = insights.get("metrics", {})
            if metrics.get("anomaly_rate"):
                tool_numbers.add(str(metrics.get("anomaly_rate")))

        if numeric_claims:
            matched = sum(
                1 for claim in numeric_claims
                if any(
                    abs(float(claim) - float(tool_num)) < 2  # Within 2 points
                    for tool_num in tool_numbers
                    if tool_num.replace("%", "").replace("$", "").replace(".", "").isdigit()
                )
            )
            if matched > 0:
                checks_passed += 1
                logger.debug(f"Numeric verification: {matched}/{len(numeric_claims)} numbers traced")
            else:
                logger.debug(f"Numeric verification: {len(numeric_claims)} claims but none matched tools")
        else:
            checks_passed += 1

        # Compute grounding score
        score = checks_passed / checks_total if checks_total > 0 else 0.0
        logger.info(f"Grounding score: {score:.2f} ({checks_passed}/{checks_total} checks passed)")
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
                f"Response not sufficiently grounded (score: {score:.2f} < {self.threshold}). "
                f"May contain unverified claims or insufficient data for assertions."
            )
