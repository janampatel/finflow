"""DuckDB client for efficient data querying from Parquet files."""

import duckdb
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger


class DuckDBClient:
    """DuckDB client for querying Phase 1 Parquet output efficiently."""

    def __init__(self, parquet_path: str = "data/processed/transactions/"):
        """Initialize DuckDB connection to Parquet files.

        Args:
            parquet_path: Path to processed Parquet directory from Phase 1
        """
        self.parquet_path = Path(parquet_path)
        self.conn = duckdb.connect(":memory:")
        self.transactions_table = None

        # Register Parquet files as tables
        if self.parquet_path.exists():
            self._register_parquet_tables()
            logger.info(f"DuckDB initialized with Parquet files from {parquet_path}")
        else:
            logger.warning(f"Parquet path not found: {parquet_path}")

    def _register_parquet_tables(self):
        """Register all Parquet files as DuckDB tables."""
        parquet_files = list(self.parquet_path.glob("**/*.parquet"))

        if not parquet_files:
            logger.warning(f"No Parquet files found in {self.parquet_path}")
            return

        for parquet_file in parquet_files:
            try:
                # Create table from parquet
                # Always use "transactions" as table name (main table from Phase 1)
                table_name = "transactions"
                self.conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM parquet_scan('{parquet_file}')"
                )
                logger.debug(f"Registered table: {table_name} from {parquet_file.name}")
                self.transactions_table = table_name
            except Exception as e:
                logger.error(f"Failed to register {parquet_file}: {e}")

    def get_transactions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tx_type: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """Fetch transactions with pagination and filtering.

        Args:
            user_id: Filter by user (optional)
            limit: Max rows to return
            offset: Pagination offset
            date_from: ISO date string (optional)
            date_to: ISO date string (optional)
            tx_type: Transaction type filter (optional)

        Returns:
            Tuple of (list of transaction dicts, total count)
        """
        try:
            # Build query
            where_clauses = []
            params = []

            if user_id:
                where_clauses.append("nameOrig = ?")
                params.append(user_id)

            if date_from:
                where_clauses.append("step >= ?")
                params.append(int(datetime.fromisoformat(date_from).timestamp()))

            if date_to:
                where_clauses.append("step <= ?")
                params.append(int(datetime.fromisoformat(date_to).timestamp()))

            if tx_type:
                where_clauses.append("type = ?")
                params.append(tx_type)

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM transactions WHERE {where_clause}"
            count_result = self.conn.execute(count_query, params).fetchall()
            total_count = count_result[0][0] if count_result else 0

            # Get paginated data
            data_query = f"""
                SELECT
                    step, type, amount, nameOrig, nameDest,
                    oldbalanceOrg, newbalanceOrig,
                    oldbalanceDest, newbalanceDest,
                    isFraud, isFlaggedFraud
                FROM transactions
                WHERE {where_clause}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            results = self.conn.execute(data_query, params).fetchall()

            # Convert to list of dicts
            columns = ["step", "type", "amount", "nameOrig", "nameDest",
                      "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                      "newbalanceDest", "isFraud", "isFlaggedFraud"]

            transactions = [dict(zip(columns, row)) for row in results]

            return transactions, total_count

        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return [], 0

    def get_transaction_by_id(self, tx_id: int) -> Optional[Dict]:
        """Fetch a single transaction by step/id.

        Args:
            tx_id: Transaction step/id

        Returns:
            Transaction dict or None
        """
        try:
            result = self.conn.execute(
                "SELECT * FROM transactions WHERE step = ?", [tx_id]
            ).fetchall()

            if result:
                columns = ["step", "type", "amount", "nameOrig", "nameDest",
                          "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                          "newbalanceDest", "isFraud", "isFlaggedFraud"]
                return dict(zip(columns, result[0]))

            return None
        except Exception as e:
            logger.error(f"Error fetching transaction {tx_id}: {e}")
            return None

    def get_user_transactions(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict]:
        """Fetch recent transactions for a specific user.

        Args:
            user_id: User identifier
            days: Look back period in days
            limit: Max transactions to return

        Returns:
            List of transaction dicts
        """
        try:
            # For PaySim data, use step-based filtering (1 step = ~30 minutes)
            steps_lookback = (days * 24 * 60) // 30

            query = """
                SELECT
                    step, type, amount, nameOrig, nameDest,
                    oldbalanceOrg, newbalanceOrig,
                    oldbalanceDest, newbalanceDest,
                    isFraud, isFlaggedFraud
                FROM transactions
                WHERE nameOrig = ? AND step >= (SELECT MAX(step) FROM transactions) - ?
                ORDER BY step DESC
                LIMIT ?
            """

            results = self.conn.execute(query, [user_id, steps_lookback, limit]).fetchall()
            columns = ["step", "type", "amount", "nameOrig", "nameDest",
                      "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                      "newbalanceDest", "isFraud", "isFlaggedFraud"]

            return [dict(zip(columns, row)) for row in results]

        except Exception as e:
            logger.error(f"Error fetching user transactions: {e}")
            return []

    def get_statistics(self) -> Dict:
        """Get overall statistics from transaction data.

        Returns:
            Dict with total count, fraud rate, avg amount, etc.
        """
        try:
            stats = self.conn.execute("""
                SELECT
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN isFraud = 1 THEN 1 ELSE 0 END) as fraud_count,
                    AVG(amount) as avg_amount,
                    MIN(amount) as min_amount,
                    MAX(amount) as max_amount,
                    COUNT(DISTINCT nameOrig) as unique_users
                FROM transactions
            """).fetchall()

            if stats and stats[0]:
                row = stats[0]
                total = row[0] or 0
                fraud = row[1] or 0
                return {
                    "total_transactions": int(total),
                    "fraud_transactions": int(fraud),
                    "fraud_rate_pct": (fraud / total * 100) if total > 0 else 0.0,
                    "avg_amount": float(row[2] or 0),
                    "min_amount": float(row[3] or 0),
                    "max_amount": float(row[4] or 0),
                    "unique_users": int(row[5] or 0)
                }

            return {
                "total_transactions": 0,
                "fraud_transactions": 0,
                "fraud_rate_pct": 0.0,
                "avg_amount": 0.0,
                "min_amount": 0.0,
                "max_amount": 0.0,
                "unique_users": 0
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def get_fraud_transactions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Fetch fraudulent transactions.

        Args:
            limit: Max rows
            offset: Pagination offset

        Returns:
            Tuple of (fraud transactions, total count)
        """
        try:
            count_result = self.conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE isFraud = 1"
            ).fetchall()
            total = count_result[0][0] if count_result else 0

            results = self.conn.execute("""
                SELECT
                    step, type, amount, nameOrig, nameDest,
                    oldbalanceOrg, newbalanceOrig,
                    oldbalanceDest, newbalanceDest,
                    isFraud, isFlaggedFraud
                FROM transactions
                WHERE isFraud = 1
                ORDER BY amount DESC
                LIMIT ? OFFSET ?
            """, [limit, offset]).fetchall()

            columns = ["step", "type", "amount", "nameOrig", "nameDest",
                      "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
                      "newbalanceDest", "isFraud", "isFlaggedFraud"]

            transactions = [dict(zip(columns, row)) for row in results]
            return transactions, total

        except Exception as e:
            logger.error(f"Error fetching fraud transactions: {e}")
            return [], 0

    def query_raw(self, sql: str, params: List = None) -> List[Dict]:
        """Execute raw SQL query (advanced usage).

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of result dicts
        """
        try:
            if params is None:
                params = []

            results = self.conn.execute(sql, params).fetchall()

            if not results:
                return []

            # Get column names from description
            desc = self.conn.description
            columns = [d[0] for d in desc] if desc else []

            return [dict(zip(columns, row)) for row in results]

        except Exception as e:
            logger.error(f"Error executing raw query: {e}")
            return []

    def close(self):
        """Close DuckDB connection."""
        self.conn.close()
        logger.info("DuckDB connection closed")
