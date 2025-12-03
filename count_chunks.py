"""
Count chunks in ChromaDB
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.vector_store import vector_store

# Get count
count = vector_store.collection.count()

print(f"📊 Total Chunks in ChromaDB: {count}")

if count == 0:
    print("❌ EMPTY - PDFs were not indexed correctly!")
    sys.exit(1)
elif count < 100:
    print("⚠️  WARNING - Very few chunks. Check your PDFs.")
    sys.exit(1)
else:
    print(f"✅ GOOD - {count} chunks ready for queries!")
    
    # Calculate rough storage
    avg_chunk_size = 1000  # characters
    total_size = (count * avg_chunk_size) / (1024 * 1024)
    print(f"   Approximate content size: {total_size:.1f} MB")
