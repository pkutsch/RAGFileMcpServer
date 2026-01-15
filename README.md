# RAG File MCP Server

A Model Context Protocol (MCP) server that provides Retrieval-Augmented Generation (RAG) capabilities for AI agents, with support for file-based data sources (PDF, TXT, Markdown) and a Streamlit web interface.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **🔌 MCP Server** - Exposes RAG tools and resources for AI agents via the Model Context Protocol
- **📄 File Parsing** - Support for PDF, TXT, Markdown, and RST files with international language detection
- **🔍 Semantic Search** - Vector-based document search using configurable embedding providers
- **🎨 Streamlit UI** - Modern web interface for file uploads, search testing, and log viewing
- **🐳 Docker Support** - Multi-stage Docker build with docker-compose orchestration
- **📊 SQLite Logging** - Built-in logging with database storage and retention policies

## Quick Start

### Prerequisites

- Python 3.12.7+
- [Ollama](https://ollama.ai/) (for local embeddings) or OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/pkutsch/RAGFileMcpServer.git
   cd RAGFileMcpServer
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the server** (creates virtual environment automatically)
   ```bash
   # macOS/Linux
   ./run.sh
   
   # Windows
   run.bat
   
   # Cross-platform (Python)
   python run.py
   ```

4. **Access the Streamlit UI**
   
   Open http://localhost:8501 in your browser.

## Configuration

Configuration is managed via environment variables. Copy `.env.example` to `.env` and customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_PORT` | `8501` | Streamlit web interface port |
| `MCP_SERVER_PORT` | `8000` | MCP server port (SSE mode) |
| `EMBEDDING_PROVIDER` | `ollama` | Embedding provider (`ollama` or `openai`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `VECTOR_STORE_TYPE` | `chroma` | Vector store (`chroma`, `qdrant`, `memory`) |
| `CHUNK_SIZE` | `500` | Text chunk size for splitting |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |

## MCP Tools

The server exposes the following tools for AI agents:

| Tool | Description |
|------|-------------|
| `search_documents` | Search for documents matching a query |
| `list_uploaded_documents` | List all uploaded documents |
| `ingest_document` | Ingest a document into the RAG index |
| `get_document_count` | Get the number of indexed documents |

## Project Structure

```
RAGFileMcpServer/
├── src/
│   ├── server.py           # MCP server implementation
│   ├── streamlit_app.py    # Streamlit web interface
│   ├── file_parser/        # File parsing modules
│   │   ├── base.py         # Base parser interface
│   │   ├── pdf_parser.py   # PDF file parser
│   │   └── text_parser.py  # Text/Markdown parser
│   └── logging/            # Logging infrastructure
│       ├── db_handler.py   # SQLite log handler
│       ├── log_manager.py  # Log management
│       └── models.py       # Data models
├── tests/                  # Test suite
├── data/                   # Data directory (uploads, chroma, logs)
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Docker orchestration
├── pyproject.toml          # Python project configuration
├── run.sh / run.bat / run.py  # Cross-platform run scripts
└── .env.example            # Environment configuration template
```

## Docker Deployment

### Using Docker Compose

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The compose file starts two services:
- **streamlit** - Web interface on port 8501
- **mcp-server** - MCP server (STDIO mode by default)

### Standalone Docker

```bash
# Build image (run from parent directory)
docker build -f RAGFileMcpServer/Dockerfile -t rag-file-mcp-server .

# Run container
docker run -p 8501:8501 -v ./data:/app/data rag-file-mcp-server
```

## Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

## Dependencies

This project depends on [rag-core](https://github.com/pkutsch/RAGMcpServerCore), a shared RAG module providing:
- Embedding providers (Ollama, OpenAI)
- Vector stores (ChromaDB, Qdrant, Memory)
- Text chunking strategies
- Retrieval logic

## License

MIT License - see [LICENSE](LICENSE) for details.
