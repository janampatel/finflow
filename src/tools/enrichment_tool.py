"""Transaction enrichment tool using fine-tuned FinBERT."""

from functools import lru_cache
from pathlib import Path
from loguru import logger

from ..models.finbert_classifier import FinBERTClassifier, CATEGORIES


class EnrichmentTool:
    """Singleton pattern for FinBERT classifier."""

    _instance = None
    _classifier = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._classifier is None:
            model_path = Path(__file__).parent.parent.parent / "data" / "models" / "finbert-transaction"
            logger.info(f"Initializing FinBERT classifier from {model_path}")
            self._classifier = FinBERTClassifier(model_path=str(model_path))

    @lru_cache(maxsize=1000)
    def _predict_cached(self, description: str):
        """Cache wrapper for FinBERT predictions."""
        return self._classifier.predict(description)

    def __call__(self, transaction_description: str) -> dict:
        """Enrich transaction with category and confidence."""
        result = self._predict_cached(transaction_description)
        return {
            "category": result["category"],
            "confidence": result["confidence"],
            "is_low_confidence": result["confidence"] < 0.7,
            "raw_description": transaction_description,
            "all_scores": result.get("all_scores", {}),
            "tool": "enrichment_tool"
        }

    def cache_info(self):
        """Get LRU cache statistics."""
        return self._predict_cached.cache_info()

    def cache_clear(self):
        """Clear LRU cache."""
        self._predict_cached.cache_clear()


# Lazy singleton — the FinBERT model loads on first call, not at import. This
# keeps `import src.api.main` cheap and side-effect-free (testable, fast cold
# start on Cloud Run); the model warms once on the first enrichment request.
_enrichment_tool_instance: "EnrichmentTool | None" = None


def _get_enrichment_tool() -> "EnrichmentTool":
    global _enrichment_tool_instance
    if _enrichment_tool_instance is None:
        _enrichment_tool_instance = EnrichmentTool()
    return _enrichment_tool_instance


def enrichment_tool(transaction_description: str) -> dict:
    """
    Enrich transaction with category and confidence score.

    Args:
        transaction_description: Raw transaction string (e.g., "STARBUCKS COFFEE 1234")

    Returns:
        dict with keys:
        - category: Spending category (one of 12 categories)
        - confidence: Model confidence (0.0-1.0)
        - is_low_confidence: True if confidence < 0.7
        - raw_description: Input description
        - all_scores: Per-category scores
        - tool: "enrichment_tool"

    Example:
        >>> result = enrichment_tool("STARBUCKS COFFEE 1234")
        >>> print(result['category'])
        'Food and Dining'
        >>> print(result['confidence'])
        0.95
    """
    return _get_enrichment_tool()(transaction_description)


def get_enrichment_cache_stats():
    """Get LRU cache hit/miss statistics."""
    info = _get_enrichment_tool().cache_info()
    return {
        "hits": info.hits,
        "misses": info.misses,
        "hit_rate": info.hits / (info.hits + info.misses) if (info.hits + info.misses) > 0 else 0.0,
        "cache_size": info.currsize,
        "max_size": info.maxsize
    }
