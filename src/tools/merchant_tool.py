"""Merchant resolution tool using fuzzy matching."""

from rapidfuzz import fuzz
from typing import List, Tuple
from loguru import logger


class MerchantTool:
    """Normalize and resolve merchant names."""

    def __init__(self):
        """Initialize merchant resolver."""
        # Common merchant mappings
        self.merchant_mappings = {
            "STARBUCKS": ["STARBUCKS COFFEE", "SBUX", "SQ*STARBUCKS"],
            "MCDONALDS": ["MCDONALDS", "MCDONALD'S", "MCDS"],
            "WALMART": ["WALMART", "WALMART SUPERCENTER", "WAL-MART"],
            "AMAZON": ["AMAZON", "AMZN", "AMAZON MKTP"],
            "UBER": ["UBER", "UBER EATS", "UBEREATS"],
            "DELTA": ["DELTA AIR", "DELTA AIRLINES"],
            "HOTEL": ["HILTON", "MARRIOTT", "HYATT", "HOLIDAY INN"],
        }
        logger.info("MerchantTool ready")

    def resolve_merchant(self, merchant_name: str, threshold: float = 0.7) -> Tuple[str, float]:
        """
        Resolve merchant name using fuzzy matching.

        Args:
            merchant_name: Raw merchant name from transaction
            threshold: Similarity threshold (0.0-1.0)

        Returns:
            (normalized_name, match_score)
        """
        if not merchant_name:
            return ("UNKNOWN", 0.0)

        merchant_name = merchant_name.strip().upper()
        best_match = merchant_name
        best_score = 0.0

        # Check against known mappings
        for canonical, aliases in self.merchant_mappings.items():
            # Check canonical
            score = fuzz.ratio(merchant_name, canonical) / 100.0
            if score > best_score:
                best_match = canonical
                best_score = score

            # Check aliases
            for alias in aliases:
                score = fuzz.ratio(merchant_name, alias) / 100.0
                if score > best_score:
                    best_match = canonical
                    best_score = score

        # Return best match if above threshold
        if best_score >= threshold:
            return (best_match, best_score)
        else:
            return (merchant_name, best_score)

    def normalize_category(self, merchant_name: str) -> str:
        """Infer merchant category from name."""
        name = merchant_name.upper()

        # Simple heuristic classification
        if any(x in name for x in ["COFFEE", "RESTAURANT", "BURGER", "PIZZA", "CAFE"]):
            return "Food and Dining"
        elif any(x in name for x in ["AMAZON", "WALMART", "TARGET", "STORE"]):
            return "Shopping"
        elif any(x in name for x in ["AIRLINE", "HOTEL", "UBER", "AIRBNB"]):
            return "Travel"
        elif any(x in name for x in ["HOSPITAL", "PHARMACY", "DOCTOR", "CLINIC"]):
            return "Healthcare"
        elif any(x in name for x in ["GAS", "ELECTRIC", "WATER", "INTERNET"]):
            return "Utilities"
        elif any(x in name for x in ["SALARY", "PAYROLL", "DEPOSIT"]):
            return "Income / Direct Deposit"
        elif any(x in name for x in ["TRANSFER", "WIRE", "ACH"]):
            return "Transfer"
        elif any(x in name for x in ["REFUND", "RETURN"]):
            return "Refund"
        elif any(x in name for x in ["MOVIE", "CONCERT", "GAME", "ENTERTAINMENT"]):
            return "Entertainment"
        elif any(x in name for x in ["INSURANCE", "PREMIUM"]):
            return "Insurance"
        elif any(x in name for x in ["STOCK", "INVESTMENT", "MUTUAL", "401"]):
            return "Investment"
        else:
            return "Other"

    def __call__(self, merchant_name: str, threshold: float = 0.8) -> dict:
        """Resolve and normalize merchant."""
        normalized, match_score = self.resolve_merchant(merchant_name, threshold)
        category = self.normalize_category(normalized)

        return {
            "raw_merchant": merchant_name,
            "normalized_merchant": normalized,
            "match_score": float(match_score),
            "inferred_category": category,
            "tool": "merchant_resolution_tool"
        }


# Singleton instance
_merchant_tool_instance = MerchantTool()


def merchant_resolution_tool(merchant_name: str, threshold: float = 0.8) -> dict:
    """
    Normalize and resolve merchant names using fuzzy matching.

    Args:
        merchant_name: Raw merchant name from transaction
        threshold: Similarity threshold for matching (0.0-1.0, default 0.8)

    Returns:
        dict with keys:
        - raw_merchant: Input merchant name
        - normalized_merchant: Resolved canonical merchant name
        - match_score: Confidence of match (0.0-1.0)
        - inferred_category: Heuristic spending category
        - tool: "merchant_resolution_tool"

    Example:
        >>> result = merchant_resolution_tool("STARBKS COFFE")
        >>> print(result['normalized_merchant'])
        'STARBUCKS'
        >>> print(result['match_score'])
        0.89
    """
    return _merchant_tool_instance(merchant_name, threshold)
