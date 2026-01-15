"""RAG File MCP Server - MCP server providing RAG support for AI agents.

This server exposes tools for document ingestion, search, and management
using the rag-core module for embeddings and retrieval.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from rag_core import RAGConfig, Retriever
from rag_core.chunking import FixedSizeChunker
from rag_core.embeddings import OllamaEmbedding
from rag_core.vectorstores.chroma import ChromaVectorStore

from src.file_parser import get_parser_for_file
from src.logging import setup_logging, LogManager

# Load environment variables
load_dotenv()

# Setup logging
log_db_path = os.getenv("LOG_DB_PATH", "./data/logs.db")
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(db_path=log_db_path, level=log_level)

logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("rag-file-mcp-server")

# Global retriever instance (initialized on startup)
_retriever: Retriever | None = None
_config: RAGConfig | None = None
_upload_dir: Path | None = None


def get_upload_dir() -> Path:
    """Get the upload directory path."""
    global _upload_dir
    if _upload_dir is None:
        _upload_dir = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
        _upload_dir.mkdir(parents=True, exist_ok=True)
    return _upload_dir


async def get_retriever() -> Retriever:
    """Get or create the retriever instance."""
    global _retriever, _config
    
    if _retriever is None:
        logger.info("Initializing RAG components...")
        
        _config = RAGConfig()
        embedding = OllamaEmbedding(_config)
        store = ChromaVectorStore(persist_dir=_config.chroma_persist_dir)
        chunker = FixedSizeChunker(_config)
        
        _retriever = Retriever(embedding, store, chunker)
        
        logger.info(
            f"RAG components initialized: "
            f"embedding={_config.embedding_provider}, "
            f"store={_config.vector_store_type}"
        )
    
    return _retriever


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_documents",
            description=(
                "Search indexed documents using semantic similarity. "
                "Returns the most relevant document chunks matching the query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query text",
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_documents",
            description="List all indexed documents with their metadata.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="ingest_document",
            description=(
                "Ingest a document from the uploads directory into the RAG index. "
                "Supports PDF, TXT, MD, and RST files."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file in the uploads directory",
                    },
                },
                "required": ["filename"],
            },
        ),
        Tool(
            name="get_document_count",
            description="Get the total number of document chunks in the index.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    try:
        if name == "search_documents":
            result = await search_documents(
                query=arguments["query"],
                k=arguments.get("k", 5),
            )
        elif name == "list_documents":
            result = await list_uploaded_documents()
        elif name == "ingest_document":
            result = await ingest_document(filename=arguments["filename"])
        elif name == "get_document_count":
            result = await get_document_count()
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def search_documents(query: str, k: int = 5) -> dict[str, Any]:
    """Search for documents matching the query.
    
    Args:
        query: Search query text.
        k: Number of results to return.
    
    Returns:
        Search results with scores and metadata.
    """
    retriever = await get_retriever()
    results = await retriever.search(query, k=k)
    
    return {
        "query": query,
        "results": [
            {
                "text": r.text,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ],
        "count": len(results),
    }


async def list_uploaded_documents() -> dict[str, Any]:
    """List all uploaded documents.
    
    Returns:
        List of uploaded files with metadata.
    """
    upload_dir = get_upload_dir()
    
    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size_bytes": file_path.stat().st_size,
                "extension": file_path.suffix.lstrip("."),
            })
    
    return {
        "files": files,
        "count": len(files),
        "upload_dir": str(upload_dir),
    }


async def ingest_document(filename: str) -> dict[str, Any]:
    """Ingest a document into the RAG index.
    
    Args:
        filename: Name of the file in the uploads directory.
    
    Returns:
        Ingestion result.
    """
    upload_dir = get_upload_dir()
    file_path = upload_dir / filename
    
    if not file_path.exists():
        return {"error": f"File not found: {filename}"}
    
    # Get appropriate parser
    parser = get_parser_for_file(filename)
    if parser is None:
        return {"error": f"Unsupported file format: {filename}"}
    
    # Parse document
    logger.info(f"Parsing document: {filename}")
    parsed = parser.parse(file_path)
    
    # Add to retriever
    retriever = await get_retriever()
    
    metadata = {
        "source": str(file_path),
        "filename": filename,
        **parsed.metadata,
    }
    
    ids = await retriever.add_document(
        text=parsed.text,
        metadata=metadata,
    )
    
    logger.info(f"Ingested document: {filename}, chunks: {len(ids)}")
    
    return {
        "filename": filename,
        "chunks_added": len(ids),
        "text_length": len(parsed.text),
        "metadata": parsed.metadata,
    }


async def get_document_count() -> dict[str, Any]:
    """Get the number of documents in the index.
    
    Returns:
        Document count.
    """
    retriever = await get_retriever()
    count = await retriever.count()
    
    return {
        "document_chunks": count,
    }


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="rag://documents/list",
            name="Document List",
            description="List of all uploaded documents",
            mimeType="application/json",
        ),
        Resource(
            uri="rag://config/status",
            name="Configuration Status",
            description="Current RAG configuration and status",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    import json
    
    if uri == "rag://documents/list":
        result = await list_uploaded_documents()
        return json.dumps(result, indent=2)
    
    elif uri == "rag://config/status":
        global _config
        retriever = await get_retriever()
        count = await retriever.count()
        
        return json.dumps({
            "embedding_provider": _config.embedding_provider if _config else "unknown",
            "vector_store": _config.vector_store_type if _config else "unknown",
            "document_chunks": count,
            "upload_dir": str(get_upload_dir()),
        }, indent=2)
    
    raise ValueError(f"Unknown resource: {uri}")


async def main():
    """Run the MCP server."""
    logger.info("Starting RAG File MCP Server...")
    
    # Initialize retriever on startup
    await get_retriever()
    
    logger.info("RAG File MCP Server ready")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
