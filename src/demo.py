"""
RAG Core Integration Demo

This script demonstrates how to use rag-core components in the RAGFileMcpServer.
Run with: python src/demo.py
"""

import asyncio
from rag_core import RAGConfig
from rag_core.embeddings import OllamaEmbedding
from rag_core.vectorstores import InMemoryVectorStore
from rag_core.chunking import FixedSizeChunker
from rag_core.retrieval import Retriever


async def main():
    # Load config (reads from environment variables or uses defaults)
    config = RAGConfig()
    print(f"📋 Config loaded:")
    print(f"   Embedding provider: {config.embedding_provider}")
    print(f"   Ollama URL: {config.ollama_base_url}")
    print(f"   Ollama model: {config.ollama_model}")
    print(f"   Vector store: {config.vector_store_type}")
    print()

    # Create components
    embedding = OllamaEmbedding(config)
    store = InMemoryVectorStore()
    chunker = FixedSizeChunker(config)
    retriever = Retriever(embedding, store, chunker)

    # Sample documents
    documents = [
        "Python is a high-level programming language known for its simplicity.",
        "Machine learning uses algorithms to learn patterns from data.",
        "RAG combines retrieval with generation for better AI responses.",
    ]

    print("📄 Adding sample documents...")
    for doc in documents:
        ids = await retriever.add_document(doc)
        print(f"   Added document (id: {ids[0][:8]}...)")

    print()
    print("🔍 Searching for 'programming language'...")
    results = await retriever.search("programming language", k=2)

    print(f"   Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"   {i}. (score: {result.score:.3f}) {result.text[:60]}...")

    print()
    print("✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
