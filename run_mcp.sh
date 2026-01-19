#!/bin/bash
# MCP Server launcher for stdio transport
# This script sets up the environment and runs the server

# Set the project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Change to project directory
cd "$PROJECT_DIR"

# Set Python path for module imports
export PYTHONPATH="$PROJECT_DIR"

# Load environment from .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Override with absolute paths for safety
export UPLOAD_DIR="${UPLOAD_DIR:-$PROJECT_DIR/data/uploads}"
export CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-$PROJECT_DIR/data/chroma}"
export LOG_DB_PATH="${LOG_DB_PATH:-$PROJECT_DIR/data/logs.db}"

# Run the MCP server
exec "$PROJECT_DIR/.venv/bin/python" -m src.server
