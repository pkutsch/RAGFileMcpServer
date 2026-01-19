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

# Tool Prefix Configuration
# This allows running multiple instances of the server (e.g. "finance_", "medical_")
# preserving global tool uniqueness for the MCP client.
try:
    tool_prefix = os.environ.get("TOOL_PREFIX", "")
except Exception:
    tool_prefix = ""

if tool_prefix:
    logger.info(f"Using tool prefix: '{tool_prefix}'")



def get_upload_dir() -> Path:
    """Get the upload directory path."""
    global _upload_dir
    if _upload_dir is None:
        _upload_dir = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
        _upload_dir.mkdir(parents=True, exist_ok=True)
    return _upload_dir


async def get_retriever(force_refresh: bool = False) -> Retriever:
    """Get or create the retriever instance.
    
    Args:
        force_refresh: Whether to force re-initialization of the retriever.
                      Useful when the underlying vector store might have changed
                      (e.g., updated by another process like Streamlit).
    """
    global _retriever, _config
    
    if _retriever is None or force_refresh:
        if force_refresh:
            logger.info("Refreshing RAG components...")
        else:
            logger.info("Initializing RAG components...")
        
        _config = RAGConfig()
        embedding = OllamaEmbedding(_config)
        store = ChromaVectorStore(persist_dir=_config.chroma_persist_dir)
        chunker = FixedSizeChunker(_config)
        
        _retriever = Retriever(embedding, store, chunker)
        
        logger.info(
            f"RAG components {'refreshed' if force_refresh else 'initialized'}: "
            f"embedding={_config.embedding_provider}, "
            f"store={_config.vector_store_type}"
        )
    
    return _retriever


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name=f"{tool_prefix}search_documents",
            description=(
                "[CATEGORY: document_search] "
                "Search the user's PRIVATE and INTERNAL CORPORATE knowledge base. "
                "This contains uploaded documents, internal company files, project notes, "
                "policies, procedures, and confidential information NOT available on the internet. "
                "IMPORTANT: Use this tool FIRST when the user asks about their personal files, "
                "internal projects, company-specific information, proprietary data, "
                "or any topic that might be documented in their private collection. "
                "This should be preferred over web search for internal/private queries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query text - be descriptive for better semantic matching",
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
            name=f"{tool_prefix}list_documents",
            description=(
                "[CATEGORY: document_search] "
                "List all documents in the user's private knowledge base. "
                "Use this to discover what internal/corporate documents are available for searching."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name=f"{tool_prefix}ingest_document",
            description=(
                "[CATEGORY: file_operations] "
                "Ingest a document into the RAG system."
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
            name=f"{tool_prefix}get_document_count",
            description="Get the total number of document chunks in the index.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name=f"{tool_prefix}rebuild_index",
            description=(
                "Completely rebuild the RAG index from the uploads directory. "
                "WARNING: This is a destructive operation that clears the existing index "
                "and re-ingests all files. Use this to fix synchronization issues."
            ),
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
    
    # Strip prefix for easier matching internally, or just match with prefix
    # Matching with prefix is safer to ensure we don't handle tools not meant for us if sharing names somehow
    
    try:
        if name == f"{tool_prefix}search_documents":
            result = await search_documents(
                query=arguments["query"],
                k=arguments.get("k", 5),
            )
        elif name == f"{tool_prefix}list_documents":
            result = await list_uploaded_documents()
        elif name == f"{tool_prefix}ingest_document":
            result = await ingest_document(filename=arguments["filename"])
        elif name == f"{tool_prefix}get_document_count":
            result = await get_document_count()
        elif name == f"{tool_prefix}rebuild_index":
            result = await rebuild_index()
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        if isinstance(result, str):
            return [TextContent(type="text", text=result)]
            
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
    # Force refresh to ensure we see the latest changes from other processes (e.g. Streamlit)
    retriever = await get_retriever(force_refresh=True)
    results = await retriever.search(query, k=k)
    
    # Format results as a single readable string for the LLM
    # This prevents "JSON Overload" and helps the model rely on the context
    formatted_results = []
    
    for i, r in enumerate(results):
        source_name = r.metadata.get("filename", "Unknown Source")
        formatted_results.append(
            f"--- Result {i+1} (Source: {source_name}, Relevance: {r.score:.2f}) ---\n"
            f"{r.text}\n"
        )
    
    if not formatted_results:
        return "No relevant documents found."
        
    return "\n".join(formatted_results)


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
    # We might want to refresh here too, but it's less critical as we are adding new data
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


async def rebuild_index() -> dict[str, Any]:
    """Completely rebuild the RAG index from uploaded files.
    
    Returns:
        Rebuild statistics.
    """
    logger.info("Starting index rebuild...")
    
    # Get retriever (force refresh)
    retriever = await get_retriever(force_refresh=True)
    
    # Clear existing index
    await retriever.store.clear()
    logger.info("Cleared existing index")
    
    upload_dir = get_upload_dir()
    files_processed = 0
    chunks_added = 0
    errors = []
    
    for file_path in upload_dir.iterdir():
        if not file_path.is_file():
            continue
            
        try:
            parser = get_parser_for_file(file_path.name)
            if not parser:
                logger.warning(f"Skipping {file_path.name}: No parser found")
                continue
                
            parsed = parser.parse(file_path)
            
            metadata = {
                "source": str(file_path),
                "filename": file_path.name,
                **parsed.metadata,
            }
            
            ids = await retriever.add_document(
                text=parsed.text,
                metadata=metadata,
            )
            
            files_processed += 1
            chunks_added += len(ids)
            logger.info(f"Re-ingested {file_path.name}: {len(ids)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to re-ingest {file_path.name}: {e}")
            errors.append(f"{file_path.name}: {str(e)}")
            
    logger.info(f"Index rebuild complete. Files: {files_processed}, Chunks: {chunks_added}")
    
    return {
        "status": "success",
        "files_processed": files_processed,
        "chunks_added": chunks_added,
        "errors": errors,
    }


async def get_document_count() -> dict[str, Any]:
    """Get the number of documents in the index.
    
    Returns:
        Document count.
    """
    # Force refresh to get accurate count including external updates
    retriever = await get_retriever(force_refresh=True)
    count = await retriever.count()
    
    return {
        "document_chunks": count,
    }


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri=f"rag://{tool_prefix}documents/list",
            name=f"{tool_prefix}Document List",
            description="List of all uploaded documents",
            mimeType="application/json",
        ),
        Resource(
            uri=f"rag://{tool_prefix}config/status",
            name=f"{tool_prefix}Configuration Status",
            description="Current RAG configuration and status",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    import json
    
    if uri == f"rag://{tool_prefix}documents/list":
        result = await list_uploaded_documents()
        return json.dumps(result, indent=2)
    
    elif uri == f"rag://{tool_prefix}config/status":
        global _config
        # Force refresh for status check
        retriever = await get_retriever(force_refresh=True)
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
