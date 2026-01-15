#!/bin/bash
set -e

# Define environment directory
VENV_DIR=".venv"

echo "========================================"
echo "    RAG File MCP Server (Mac/Linux)"
echo "========================================"

# Auto-create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv $VENV_DIR
    echo "Virtual environment created."
fi

# Activate venv
echo "Activating virtual environment..."
source $VENV_DIR/bin/activate
export PYTHONPATH=$PYTHONPATH:.


# Install requirements - prefer local RAGMcpServerCore if available
echo "Checking dependencies..."
if [ -d "../RAGMcpServerCore" ]; then
    echo "Using local RAGMcpServerCore..."
    pip install -e "../RAGMcpServerCore[chroma,qdrant]" | grep -v 'Requirement already satisfied' || true
    pip install -e ".[dev]" --no-deps | grep -v 'Requirement already satisfied' || true
    pip install -e ".[dev]" | grep -v 'Requirement already satisfied' || true
else
    echo "Using Git RAGMcpServerCore..."
    pip install -e ".[dev]" | grep -v 'Requirement already satisfied' || true
fi

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    set -a
    source <(grep -v '^\s*#' .env | sed 's/#.*//' | grep -v '^\s*$')
    set +a
fi

# Default ports
STREAMLIT_PORT=${STREAMLIT_PORT:-8501}
MCP_SERVER_PORT=${MCP_SERVER_PORT:-8000}

# Create data directories
mkdir -p data/uploads data/chroma

echo ""
echo "Starting services..."
echo ""

# Start MCP server in background
echo "Starting MCP Server (STDIO mode)..."
python -m src.server &
MCP_PID=$!

sleep 2

# Start Streamlit UI
echo "Starting Streamlit UI on http://localhost:$STREAMLIT_PORT"
streamlit run src/streamlit_app.py \
    --server.port=$STREAMLIT_PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false &
UI_PID=$!

echo ""
echo "✅ Services running:"
echo "   - Streamlit UI: http://localhost:$STREAMLIT_PORT"
echo "   - MCP Server: Running in STDIO mode (PID: $MCP_PID)"
echo ""
echo "Press Ctrl+C to stop"

# Cleanup function
cleanup() {
    echo ""
    echo "Stopping services..."
    kill -TERM $MCP_PID $UI_PID 2>/dev/null
    sleep 1
    kill -9 $MCP_PID $UI_PID 2>/dev/null
    echo "Services stopped."
    exit 0
}

trap cleanup INT
wait
