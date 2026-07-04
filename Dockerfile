# Dockerfile for WaterSentinel — Google Cloud Run deployment
# Base: Python 3.12 slim (smallest image that works with all dependencies)
# Port: 8080 (Cloud Run standard — do not change)
# Build: uv for fast, reproducible dependency installation

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed by chromadb and Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy dependency files first (Docker layer caching — only reinstalls when deps change)
COPY pyproject.toml .
COPY .env.example .

# Install Python dependencies via uv
RUN uv sync --no-dev

# Copy application code
COPY agents/ ./agents/
COPY mcp_servers/ ./mcp_servers/
COPY rag/ ./rag/
COPY api/ ./api/
COPY scripts/ ./scripts/

# Create data directory (ChromaDB + SQLite will write here at runtime)
# Note: Cloud Run filesystem is ephemeral — data resets on restart
# For production: mount a persistent volume or use Cloud SQL + Cloud Storage
RUN mkdir -p ./data

# Security: run as non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Cloud Run requires port 8080
EXPOSE 8080

# Startup: ingest RAG docs then start FastAPI server
# Using shell form to allow chained commands
CMD python rag/ingest.py && \
    python scripts/seed_mock_data.py && \
    uvicorn api.main:app --host 0.0.0.0 --port 8080 --workers 1
