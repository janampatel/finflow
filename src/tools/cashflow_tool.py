"""Cash flow analysis tool."""

from typing import List, Dict
from datetime import datetime, timedelta
import numpy as np
from loguru import logger


class CashFlowTool:
    """Analyze cash flow patterns and detect recurring transactions."""

    def __init__(self):
        """Initialize cash flow analyzer."""
        logger.info("CashFlowTool ready")

    def detect_recurring(self, transactions: List[Dict], threshold: float = 0.7) -> List[Dict]:
        """
        Detect recurring transactions.

        Args:
            transactions: List of transaction dicts with 'amount', 'date', 'description'
            threshold: Similarity threshold for grouping (0.0-1.0)

        Returns:
            List of recurring transaction groups
        """
        if not transactions:
            return []

        # Group by description and amount
        groups = {}
        for tx in transactions:
            key = (tx.get("description", ""), round(tx.get("amount", 0), 2))
            if key not in groups:
                groups[key] = []
            groups[key].append(tx)

        # Detect recurring patterns
        recurring = []
        for (desc, amount), txs in groups.items():
            if len(txs) < 2:
                continue

            # Check if transactions occur regularly
            dates = sorted([tx.get("date") for tx in txs if tx.get("date")])
            if len(dates) >= 2:
                # Calculate intervals
                intervals = []
                for i in range(1, len(dates)):
                    if isinstance(dates[i], str) and isinstance(dates[i-1], str):
                        try:
                            d1 = datetime.fromisoformat(dates[i-1])
                            d2 = datetime.fromisoformat(dates[i])
                            intervals.append((d2 - d1).days)
                        except:
                            pass

                if intervals:
                    avg_interval = np.mean(intervals)
                    std_interval = np.std(intervals)

                    # Check regularity (low std = high regularity)
                    if std_interval < avg_interval * 0.3:  # 30% tolerance
                        recurring.append({
                            "description": desc,
                            "amount": float(amount),
                            "frequency": "monthly" if 25 <= avg_interval <= 35 else "weekly" if 5 <= avg_interval <= 9 else "other",
                            "avg_interval_days": float(avg_interval),
                            "regularity_score": 1.0 - min(std_interval / avg_interval, 1.0),
                            "occurrence_count": len(txs)
                        })

        return sorted(recurring, key=lambda x: x["occurrence_count"], reverse=True)

    def calculate_summary(self, transactions: List[Dict]) -> dict:
        """
        Calculate cash flow summary.

        Args:
            transactions: List of transaction dicts

        Returns:
            Cash flow summary dict
        """
        if not transactions:
            return {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_cash_flow": 0.0,
                "transaction_count": 0,
                "avg_transaction": 0.0,
                "std_transaction": 0.0,
                "income_to_expense_ratio": None,
            }

        # Income/expense direction comes from the SIGNED balance change, not the
        # (always-positive) transaction amount. Fall back to amount sign only if
        # balance_change is absent.
        def _signed(tx):
            bc = tx.get("balance_change")
            return float(bc) if bc is not None else float(tx.get("amount", 0) or 0)

        magnitudes = [abs(float(tx.get("amount", 0) or 0)) for tx in transactions]
        signed = [_signed(tx) for tx in transactions]
        income = sum(a for a in signed if a > 0)
        expenses = abs(sum(a for a in signed if a < 0))
        net = income - expenses

        # Never emit a non-finite ratio (inf/NaN break JSON and downstream math).
        ratio = round(income / expenses, 4) if expenses > 0 else None

        return {
            "total_income": float(income),
            "total_expenses": float(expenses),
            "net_cash_flow": float(net),
            "transaction_count": len(transactions),
            "avg_transaction": float(np.mean(magnitudes)) if magnitudes else 0.0,
            "std_transaction": float(np.std(magnitudes)) if magnitudes else 0.0,
            "income_to_expense_ratio": ratio,
        }

    def __call__(self, transactions: List[Dict]) -> dict:
        """Analyze cash flow."""
        summary = self.calculate_summary(transactions)
        recurring = self.detect_recurring(transactions)

        return {
            "cash_flow_summary": summary,
            "recurring_transactions": recurring,
            "recurring_count": len(recurring),
            "total_transaction_count": len(transactions),
            "tool": "cashflow_tool"
        }


# Singleton instance
_cashflow_tool_instance = CashFlowTool()


def cashflow_tool(transactions: List[Dict]) -> dict:
    """
    Analyze cash flow patterns and detect recurring transactions.

    Args:
        transactions: List of transaction dicts with keys:
            - amount: float
            - description: str
            - date: str (ISO format, optional)

    Returns:
        dict with keys:
        - cash_flow_summary: Income, expenses, net flow
        - recurring_transactions: List of detected recurring patterns
        - recurring_count: Number of recurring patterns
        - total_transaction_count: Total transactions analyzed
        - tool: "cashflow_tool"

    Example:
        >>> txs = [
        ...     {"amount": -50, "description": "COFFEE", "date": "2024-01-01"},
        ...     {"amount": -50, "description": "COFFEE", "date": "2024-01-02"},
        ... ]
        >>> result = cashflow_tool(txs)
        >>> print(result['recurring_count'])
        1
    """
    return _cashflow_tool_instance(transactions)
