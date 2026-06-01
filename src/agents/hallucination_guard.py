"""Hallucination detection via numeric grounding.

The grounding score is the fraction of numbers the LLM states in its narrative
that are traceable to an actual tool output (within tolerance). This directly
measures hallucination: a fabricated count/score/amount won't match any tool
value and lowers the score, while every true figure the model cites is verified.

A data-sufficiency gate additionally caps the score if the model makes
pattern/diversity claims on too few transactions to support them.
"""

import math
import re
from loguru import logger


class HallucinationGuard:
    """Validates LLM output against tool results via numeric grounding."""

    # Claims that require >= min_transaction_count to be legitimate.
    _PATTERN_CLAIMS = [
        r"(?:low|high|limited|concentrated)\s+(?:diversity|variety)",
        r"spending\s+(?:patterns|habits|behaviou?r)",
        r"(?:lack|absence)\s+of\s+(?:diversity|variety)",
        r"concentration\s+of\s+spending",
    ]

    def __init__(self, grounding_threshold: float = 0.85, min_transaction_count: int = 10):
        self.threshold = grounding_threshold
        self.min_txn_count = min_transaction_count

    @staticmethod
    def _add(valid: set, v) -> None:
        """Add a tool value (and its rounded / scaled variants) to the valid set."""
        try:
            v = float(v)
        except (TypeError, ValueError):
            return
        if not math.isfinite(v):  # guard against inf/NaN from tools
            return
        valid.add(round(v, 2))
        # Integer form is only meaningful for counts/amounts (>=2). Rounding a
        # 0-1 confidence/score to an int would inject spurious 0/1 into the set
        # and let fabricated small counts pass.
        if abs(v) >= 2:
            valid.add(float(round(v)))
        # A 0-1 score may be stated on a 0-100 scale (0.56 -> 56). Accept both.
        if 0 < v < 2:
            valid.add(float(round(v * 100)))

    def _valid_numbers(self, enriched, anomaly, cashflow, insights, fraud=None) -> set:
        """Collect every number that legitimately appears in the tool outputs."""
        valid: set = set()
        add = lambda v: self._add(valid, v)

        metrics = (insights or {}).get("metrics", {}) if insights else {}

        # Transaction count (a very common, legitimate figure)
        n_tx = metrics.get("num_transactions") or len(enriched or [])
        add(n_tx)

        # Category names count + per-transaction confidences
        cats = [r.get("category") for r in (enriched or []) if r.get("category")]
        add(len(set(cats)))
        for r in (enriched or []):
            add(r.get("confidence"))

        # Anomaly count + per-transaction scores
        add(sum(1 for a in (anomaly or []) if a.get("is_anomaly")))
        for a in (anomaly or []):
            add(a.get("anomaly_score"))

        # Fraud count + per-transaction probabilities
        add(sum(1 for f in (fraud or []) if f.get("is_fraud_predicted")))
        for f in (fraud or []):
            add(f.get("fraud_probability"))

        # Health score + components
        if insights:
            add(insights.get("health_score"))
            for v in (insights.get("components") or {}).values():
                add(v)
            for v in (metrics or {}).values():
                add(v)

        # Cash-flow summary figures
        summary = (cashflow or {}).get("cash_flow_summary", {}) if cashflow else {}
        for v in summary.values():
            add(v)

        return valid

    @staticmethod
    def _matches(x: float, valid: set) -> bool:
        """A number is grounded if it's near a tool value.

        Tolerance is tight (0.05 absolute) so a stated count/score must really
        correspond to a tool figure — e.g. "1" must not match a 0.9 confidence —
        while 1% relative absorbs rounding on large cash-flow amounts.
        """
        for v in valid:
            if abs(x - v) <= max(0.05, abs(v) * 0.01):
                return True
        return False

    def compute_grounding_score(
        self,
        response: str,
        enriched_results: list[dict],
        anomaly_results: list[dict],
        cashflow_results: dict,
        insights: dict,
        fraud_results: list[dict] | None = None,
    ) -> float:
        metrics = (insights or {}).get("metrics", {}) if insights else {}
        txn_count = metrics.get("num_transactions") or len(enriched_results or []) or 1
        logger.debug(f"Grounding check: {txn_count} transactions")

        valid = self._valid_numbers(
            enriched_results, anomaly_results, cashflow_results, insights, fraud_results
        )

        # Extract numeric tokens (strip thousands separators / currency)
        cleaned = response.replace(",", "")
        nums = [
            float(m)
            for m in re.findall(r"-?\d+(?:\.\d+)?", cleaned)
        ]

        if nums:
            matched = sum(1 for x in nums if self._matches(x, valid))
            score = matched / len(nums)
            logger.debug(f"Numeric grounding: {matched}/{len(nums)} numbers traceable")
        else:
            # No numbers stated → nothing to fabricate → grounded by construction.
            score = 1.0
            logger.debug("Numeric grounding: no numbers stated")

        # Data-sufficiency gate: pattern claims need enough transactions.
        if txn_count < self.min_txn_count and any(
            re.search(p, response, re.IGNORECASE) for p in self._PATTERN_CLAIMS
        ):
            logger.warning(
                f"Pattern claims with only {txn_count} txns (min {self.min_txn_count}) — capping score"
            )
            score = min(score, 0.5)

        score = round(score, 4)
        logger.info(f"Grounding score: {score:.2f}")
        return score

    def validate(
        self,
        response: str,
        enriched_results: list[dict],
        anomaly_results: list[dict],
        cashflow_results: dict,
        insights: dict,
        fraud_results: list[dict] | None = None,
    ) -> tuple[bool, float, str]:
        """Validate LLM response against tool results. Returns (is_valid, score, reason)."""
        score = self.compute_grounding_score(
            response, enriched_results, anomaly_results, cashflow_results, insights, fraud_results
        )
        if score >= self.threshold:
            return True, score, f"Response grounded (score: {score:.2f})"
        return False, score, (
            f"Response not sufficiently grounded (score: {score:.2f} < {self.threshold}). "
            f"Contains numbers not traceable to tool outputs."
        )
