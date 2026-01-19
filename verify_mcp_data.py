#!/usr/bin/env python
"""Verification script for MCP data content."""

import asyncio
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def verify_mcp_data():
    """Verify that expected data is in the MCP index."""
    from src.server import (
        get_retriever,
        search_documents,
        get_document_count,
    )
    
    print("=" * 60)
    print("MCP Data Verification")
    print("=" * 60)
    
    # Check count
    count = await get_document_count()
    print(f"\n📊 Indexed chunks: {count['document_chunks']}")
    
    # Specific queries for the files user uploaded
    queries = [
        "Kenichi Takeuchi",  # From RagTest1.txt
        "Project Zorblax-7", # From TestRag3.txt
    ]
    
    all_found = True
    
    for query in queries:
        print(f"\n🔍 Searching for: '{query}'")
        results = await search_documents(query, k=1)
        
        if results['count'] > 0:
            top_result = results['results'][0]
            print(f"   ✅ Found match (Score: {top_result['score']:.3f})")
            print(f"      Text: {top_result['text'][:100]}...")
            print(f"      File: {top_result['metadata'].get('filename', 'Unknown')}")
        else:
            print(f"   ❌ No results found!")
            all_found = False
            
    print("\n" + "=" * 60)
    if all_found:
        print("✅ VERIFICATION SUCCESSFUL: All expected data found in index.")
    else:
        print("❌ VERIFICATION FAILED: Some data missing from index.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(verify_mcp_data())
