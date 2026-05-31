"""FastAPI REST API for FinFlow agent."""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from src.agents import create_agent_executor
from src.data import DuckDBClient


# Initialize FastAPI app
app = FastAPI(
    title="FinFlow API",
    description="Financial transaction intelligence pipeline",
    version="1.0.0"
)

# Initialize DuckDB client
db_client = DuckDBClient(parquet_path="data/processed/transactions/")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/api/transactions")
async def get_transactions(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tx_type: Optional[str] = None
):
    """Fetch transactions with pagination and filtering.

    Args:
        user_id: Filter by user ID
        limit: Max rows (default 50, max 1000)
        offset: Pagination offset
        date_from: ISO date string
        date_to: ISO date string
        tx_type: Transaction type filter
    """
    try:
        limit = min(limit, 1000)  # Cap limit for performance
        transactions, total_count = db_client.get_transactions(
            user_id=user_id,
            limit=limit,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
            tx_type=tx_type
        )

        return {
            "data": transactions,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "returned": len(transactions)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/statistics")
async def get_statistics():
    """Get transaction statistics (total count, fraud rate, etc.)."""
    try:
        stats = db_client.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fraud-transactions")
async def get_fraud_transactions(limit: int = 100, offset: int = 0):
    """Fetch fraudulent transactions."""
    try:
        limit = min(limit, 1000)
        transactions, total_count = db_client.get_fraud_transactions(
            limit=limit,
            offset=offset
        )

        return {
            "data": transactions,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "returned": len(transactions)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching fraud transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_transactions(request: AnalyzeRequest):
    """Analyze transactions using FinFlow agent.

    Args:
        request: Transaction batch to analyze

    Returns:
        Agent analysis results with grounding score
    """
    try:
        # Check environment
        if not os.getenv("GROQ_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="GROQ_API_KEY not set"
            )

        # Convert Pydantic models to dicts
        transactions = [t.model_dump() for t in request.transactions]

        logger.info(f"Analyzing {len(transactions)} transactions")

        # Create and execute agent
        graph, initial_state = create_agent_executor(transactions)
        final_state = graph.invoke(initial_state)

        # Construct response
        response = AnalyzeResponse(
            final_response=final_state.get("final_response", ""),
            grounding_score=float(final_state.get("grounding_score", 0.0)),
            execution_trace=final_state.get("execution_trace", []),
            enriched_results=final_state.get("enriched_results", []),
            anomaly_results=final_state.get("anomaly_results", []),
            merchant_results=final_state.get("merchant_results", []),
            cashflow_results=final_state.get("cashflow_results", {}),
            insights=final_state.get("insights", {})
        )

        logger.info(f"Analysis complete: grounding_score={response.grounding_score:.2f}")

        return response

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
