"""
Verify ChromaDB has actual data from PDFs
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vector_store import vector_store

print("="* 60)
print("ChromaDB VERIFICATION REPORT")
print("="* 60)

# Get collection info
info = vector_store.get_collection_info()
print(f"\nCollection Info:")
print(f"   Name: {info['collection_name']}")
print(f"   Total Documents: {info['count']}")
print(f"   Metadata: {info['metadata']}")

if info['count'] == 0:
    print("\nNO DATA IN CHROMADB!")
    print("   This means indexing didn't work.")
    sys.exit(1)

print(f"\n{info['count']} documents found in ChromaDB")

# Get ALL data from collection
print("\nSample Data Verification:")
all_data = vector_store.collection.get()

print(f"   Total IDs: {len(all_data['ids'])}")
print(f"   Total Documents: {len(all_data['documents'])}")
print(f"   Total Metadata: {len(all_data['metadatas'])}")

# Show first 3 documents
print(f"\nFirst 3 Documents:\n")
for idx in range(min(3, len(all_data['documents']))):
    print(f"   Document {idx + 1}:")
    print(f"      ID: {all_data['ids'][idx]}")
    print(f"      Length: {len(all_data['documents'][idx])} characters")
    print(f"      Preview: {all_data['documents'][idx][:80]}...")
    print(f"      Source: {all_data['metadatas'][idx].get('source', 'Unknown')}")
    print()

# Show sources summary
print("Sources Summary:")
sources = {}
for metadata in all_data['metadatas']:
    source = metadata.get('source', 'Unknown')
    if source not in sources:
        sources[source] = 0
    sources[source] += 1

for source, count in sorted(sources.items()):
    print(f"   {source}: {count} documents")

print(f"\n ChromaDB is healthy and ready!")
