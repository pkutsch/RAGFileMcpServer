#!/usr/bin/env python3
"""
Cross-platform entry point for running the RAG File MCP Server.
Performs pre-flight checks before starting the application.
"""

import os
import sys
import subprocess
from pathlib import Path


def check_requirements():
    """Check if all required packages are installed."""
    try:
        import streamlit
        import pypdf
        import chardet
        import mcp
        from dotenv import load_dotenv
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements: pip install -e '.[dev]'")
        return False


def check_rag_core():
    """Check if rag-core module is available."""
    try:
        from rag_core import RAGConfig, Retriever
        return True
    except ImportError:
        print("❌ rag-core module not found")
        print("Please install: pip install -e ../RAGMcpServerCore[chroma]")
        return False


def check_ollama():
    """Check if Ollama server is accessible (optional)."""
    try:
        import httpx
        from dotenv import load_dotenv
        load_dotenv()
        
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = httpx.get(f"{ollama_url}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def create_directories():
    """Create necessary data directories."""
    dirs = [
        "data/uploads",
        "data/chroma",
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def main():
    """Run the application with checks."""
    print("🚀 RAG File MCP Server")
    print("=" * 50)
    
    # Check requirements
    print("\nChecking requirements...")
    if not check_requirements():
        sys.exit(1)
    print("✅ Core requirements satisfied")
    
    if not check_rag_core():
        sys.exit(1)
    print("✅ rag-core module available")
    
    # Check Ollama (optional)
    print("\nChecking Ollama server...")
    if check_ollama():
        print("✅ Ollama server accessible")
    else:
        print("⚠️  Ollama server not accessible (embeddings may fail)")
        print("   Start Ollama: ollama serve")
    
    # Create directories
    print("\nCreating data directories...")
    create_directories()
    print("✅ Directories ready")
    
    # Get port from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    streamlit_port = os.getenv("STREAMLIT_PORT", "8501")
    
    print("\n" + "=" * 50)
    print(f"Starting Streamlit UI on http://localhost:{streamlit_port}")
    print("=" * 50 + "\n")
    
    # Run Streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/streamlit_app.py",
        "--server.port", streamlit_port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ])


if __name__ == "__main__":
    main()
