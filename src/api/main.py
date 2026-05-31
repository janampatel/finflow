"""FastAPI REST API for FinFlow agent."""

import os
from fastapi import FastAPI, HTTPException
from loguru import logger

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse
from src.agents import create_agent_executor


# Initialize FastAPI app
app = FastAPI(
    title="FinFlow API",
    description="Financial transaction intelligence pipeline",
    version="1.0.0"
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


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
