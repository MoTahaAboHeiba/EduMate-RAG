"""
Verify ChromaDB has actual data from PDFs
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.vector_store import vector_store

print("=" * 60)
print("🔍 ChromaDB VERIFICATION REPORT")
print("=" * 60)

# Get collection info
info = vector_store.get_collection_info()
print(f"\n📊 Collection Info:")
print(f"   Name: {info['collection_name']}")
print(f"   Total Documents: {info['count']}")
print(f"   Metadata: {info['metadata']}")

if info['count'] == 0:
    print("\n❌ NO DATA IN CHROMADB!")
    print("   This means indexing didn't work.")
    sys.exit(1)

print(f"\n✅ {info['count']} documents found in ChromaDB")

# Get ALL data from collection
print("\n📄 Sample Data Verification:")
all_data = vector_store.collection.get()

print(f"   Total IDs: {len(all_data['ids'])}")
print(f"   Total Documents: {len(all_data['documents'])}")
print(f"   Total Metadata: {len(all_data['metadatas'])}")

# Show first 3 documents
print(f"\n📖 First 3 Documents:\n")
for idx in range(min(3, len(all_data['documents']))):
    print(f"   Document {idx + 1}:")
    print(f"      ID: {all_data['ids'][idx]}")
    print(f"      Length: {len(all_data['documents'][idx])} characters")
    print(f"      Preview: {all_data['documents'][idx][:80]}...")
    print(f"      Source: {all_data['metadatas'][idx].get('source', 'Unknown')}")
    print()

# Show sources summary
print("📚 Sources Summary:")
sources = {}
for metadata in all_data['metadatas']:
    source = metadata.get('source', 'Unknown')
    sources[source] = sources.get(source, 0) + 1

for source, count in sorted(sources.items()):
    print(f"   - {source}: {count} chunks")

# Test search functionality
print(f"\n🔍 Testing Search Functionality:")
test_query = "What is"
results = vector_store.search(test_query, num_results=2)

if results:
    print(f"   ✅ Search works! Found {len(results)} results for '{test_query}'")
    for idx, result in enumerate(results, 1):
        print(f"\n   Result {idx}:")
        print(f"      Source: {result['metadata']['source']}")
        print(f"      Distance: {result['distance']:.4f}")
        print(f"      Content: {result['content'][:100]}...")
else:
    print(f"   ❌ Search returned no results!")

print("\n" + "=" * 60)
print("✅ VERIFICATION COMPLETE")
print("=" * 60)
