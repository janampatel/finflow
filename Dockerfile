# syntax=docker/dockerfile:1
#
# FinFlow serving image — multi-stage build.
#   Stage 1 (builder): compile/install all deps into an isolated virtualenv.
#   Stage 2 (runtime):  copy only the venv + app code into a slim, non-root image.
#
# Design choices worth calling out:
#   • CPU-only torch (skip ~2 GB of CUDA) — Cloud Run runs on CPU.
#   • No build toolchain in the final image (smaller, smaller attack surface).
#   • Runs as an unprivileged user.
#   • Binds to Cloud Run's injected $PORT (default 8080).
#   • data/ and models/ are NOT baked in (see .dockerignore). For a live deploy,
#     mount or bake a sample Parquet + model artifacts — see deploy/README.md.

############################
# Stage 1 — builder
############################
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential covers any source builds (statsmodels/scipy fall back to it).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv so the runtime stage copies a clean, self-contained tree.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements-api.txt .
RUN pip install --upgrade pip && \
    # CPU-only torch first, from PyTorch's CPU index (no CUDA bloat).
    pip install --index-url https://download.pytorch.org/whl/cpu torch==2.2.1 && \
    # Everything else from PyPI.
    pip install -r requirements-api.txt

############################
# Stage 2 — runtime
############################
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Copy the prebuilt virtualenv — no compiler in the final image.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Application code only. data/ + models/ excluded via .dockerignore.
COPY src/ ./src/

# Defense-in-depth: drop root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Cloud Run injects $PORT. Single uvicorn worker keeps model singletons in one
# process (no duplicate FinBERT/RandomForest loads); scale horizontally with
# replicas, not in-process workers.
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]
