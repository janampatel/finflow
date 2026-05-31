"""Find users with multiple transactions for testing Agent Trace page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DuckDBClient

def find_active_users():
    """Find users with 20+ transactions for Agent Trace testing."""
    print("\n🔍 Finding active users in database...\n")

    client = DuckDBClient(parquet_path="data/processed/transactions/")

    # Query to find top users by transaction count
    query = """
    SELECT nameOrig, COUNT(*) as txn_count
    FROM transactions
    GROUP BY nameOrig
    HAVING COUNT(*) >= 3
    ORDER BY COUNT(*) DESC
    LIMIT 20
    """

    results = client.query_raw(query)

    if not results:
        print("❌ No users with 3+ transactions found")
        return

    print(f"✅ Found {len(results)} users with 3+ transactions:\n")
    print(f"{'User ID':<20} {'Transactions':<15}")
    print("-" * 35)

    for row in results:
        user_id = row.get("nameOrig", "Unknown")
        txn_count = row.get("txn_count", 0)
        print(f"{user_id:<20} {txn_count:<15}")

    print("\n" + "=" * 35)
    print("\n💡 Use any of these User IDs in Agent Trace page:")
    print(f"   → Try: {results[0]['nameOrig']}")
    print("\n📝 Steps:")
    print("1. Go to Agent Trace page")
    print(f"2. User ID: {results[0]['nameOrig']}")
    print("3. Click 'Load User History'")
    print("4. Add a new transaction")
    print("5. Run Agent Pipeline")

    client.close()


if __name__ == "__main__":
    find_active_users()
