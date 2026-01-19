#!/usr/bin/env python
"""Quick test script to verify RAG search functionality."""

import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def test_search():
    """Test the search functionality."""
    from src.server import (
        get_retriever,
        search_documents,
        list_uploaded_documents,
        get_document_count,
        ingest_document,
    )
    
    print("=" * 60)
    print("RAG File MCP Server - Search Test")
    print("=" * 60)
    
    # 1. List uploaded documents
    print("\n📁 Step 1: Checking uploaded documents...")
    docs = await list_uploaded_documents()
    print(f"   Upload dir: {docs['upload_dir']}")
    print(f"   Files found: {docs['count']}")
    for f in docs['files']:
        print(f"   - {f['name']} ({f['size_bytes']} bytes)")
    
    # 2. Check document count in index
    print("\n📊 Step 2: Checking indexed document count...")
    count = await get_document_count()
    print(f"   Indexed chunks: {count['document_chunks']}")
    
    # 3. If nothing indexed but files exist, ingest them
    if count['document_chunks'] == 0 and docs['count'] > 0:
        print("\n⚠️  No documents indexed! Ingesting first file...")
        first_file = docs['files'][0]['name']
        result = await ingest_document(first_file)
        print(f"   Ingested: {first_file}")
        print(f"   Chunks added: {result.get('chunks_added', 'error')}")
        
        # Recheck count
        count = await get_document_count()
        print(f"   New indexed chunks: {count['document_chunks']}")
    
    # 4. Perform a test search
    print("\n🔍 Step 3: Testing search...")
    test_queries = [
        "Yukiko",
        "Japan",
        "mother",
        "Dr. Mumblebee",  # In case Zorblax file was added
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = await search_documents(query, k=3)
        if results['count'] > 0:
            print(f"   ✅ Found {results['count']} results:")
            for i, r in enumerate(results['results'][:2]):
                score = f"{r['score']:.3f}" if isinstance(r['score'], float) else r['score']
                text_preview = r['text'][:80].replace('\n', ' ') + "..." if len(r['text']) > 80 else r['text']
                print(f"      [{i+1}] Score: {score} | {text_preview}")
        else:
            print(f"   ❌ No results found")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_search())
