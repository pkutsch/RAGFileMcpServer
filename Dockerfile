# =============================================================================
# RAG File MCP Server - Dockerfile
# =============================================================================
# Multi-stage build for optimized image size

# -----------------------------------------------------------------------------
# Build Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy rag-core module first (for caching)
COPY RAGMcpServerCore /app/RAGMcpServerCore

# Copy project files
COPY RAGFileMcpServer/pyproject.toml RAGFileMcpServer/requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -e /app/RAGMcpServerCore[chroma] && \
    pip install --no-cache-dir pypdf chardet streamlit python-dotenv mcp

# -----------------------------------------------------------------------------
# Runtime Stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/RAGMcpServerCore /app/RAGMcpServerCore

# Copy source code
COPY RAGFileMcpServer/src /app/src
COPY RAGFileMcpServer/.env.example /app/.env.example

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/chroma

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default ports (can be overridden)
ENV STREAMLIT_PORT=8501
ENV MCP_SERVER_PORT=8000

# Expose ports
EXPOSE ${STREAMLIT_PORT}
EXPOSE ${MCP_SERVER_PORT}

# Volume for persistent data
VOLUME ["/app/data"]

# Default command (override in docker-compose)
CMD ["streamlit", "run", "src/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
