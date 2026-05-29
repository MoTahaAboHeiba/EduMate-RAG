#!/usr/bin/env python3
"""
EduMate RAG Performance Testing Suite

Measures and compares performance across:
- ChromaDB (local)
- Qdrant (local)
- Qdrant Cloud

Metrics: Latency, Throughput, Memory, Storage
"""

import time
import json
import psutil
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import statistics

class PerformanceTest:
    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "environment": {
                "python_version": self._get_python_version(),
                "platform": self._get_platform(),
                "cpu_cores": psutil.cpu_count(),
                "total_ram_gb": round(psutil.virtual_memory().total / (1024**3), 1)
            },
            "chromadb": {},
            "qdrant_local": {},
            "qdrant_cloud": {}
        }
        self.metrics = {}

    def _get_python_version(self) -> str:
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _get_platform(self) -> str:
        import platform
        return platform.platform()

    def measure_indexing(self, db_type: str, num_vectors: int, duration_seconds: float):
        """Measure indexing performance"""
        return {
            "vectors_indexed": num_vectors,
            "duration_seconds": round(duration_seconds, 2),
            "throughput_vectors_per_sec": round(num_vectors / duration_seconds, 2),
            "memory_peak_mb": round(psutil.Process().memory_info().rss / (1024**2), 1)
        }

    def measure_query(self, db_type: str, queries: List[float], num_successful: int):
        """Measure query performance"""
        return {
            "total_queries": len(queries),
            "successful_queries": num_successful,
            "avg_latency_ms": round(statistics.mean(queries), 2),
            "median_latency_ms": round(statistics.median(queries), 2),
            "p95_latency_ms": round(sorted(queries)[int(len(queries)*0.95)], 2),
            "p99_latency_ms": round(sorted(queries)[int(len(queries)*0.99)], 2),
            "min_latency_ms": round(min(queries), 2),
            "max_latency_ms": round(max(queries), 2),
            "throughput_queries_per_sec": round(len(queries) / (sum(queries)/1000), 2)
        }

    def test_chromadb(self, vector_count: int = 5637):
        """Test ChromaDB performance"""
        print("\n" + "="*60)
        print("🧪 Testing ChromaDB Performance")
        print("="*60)
        
        try:
            import chromadb
            
            # Initialize
            client = chromadb.Client()
            collection = client.create_collection(name="test_perf")
            
            # Simulate indexing
            print("⏱️  Measuring indexing performance...")
            start = time.time()
            
            # Create test vectors
            for i in range(vector_count):
                collection.add(
                    ids=[f"doc_{i}"],
                    documents=[f"Sample document {i}"],
                    metadatas=[{"source": f"pdf_{i//100}"}]
                )
            
            index_duration = time.time() - start
            self.results["chromadb"]["indexing"] = self.measure_indexing(
                "chromadb", vector_count, index_duration
            )
            
            # Simulate queries
            print("⏱️  Measuring query performance...")
            queries = []
            for i in range(100):
                start = time.time()
                results = collection.query(
                    query_texts=[f"sample query {i}"],
                    n_results=5
                )
                latency = (time.time() - start) * 1000
                queries.append(latency)
            
            self.results["chromadb"]["query"] = self.measure_query(
                "chromadb", queries, len(queries)
            )
            self.results["chromadb"]["status"] = "✅ Success"
            
            print("✓ ChromaDB testing completed")
            
        except Exception as e:
            self.results["chromadb"]["status"] = f"❌ Error: {str(e)}"
            print(f"❌ ChromaDB test failed: {e}")

    def test_qdrant_local(self, vector_count: int = 5637):
        """Test Qdrant Local performance"""
        print("\n" + "="*60)
        print("🧪 Testing Qdrant Local Performance")
        print("="*60)
        
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            
            # Initialize local client
            client = QdrantClient(":memory:")
            
            # Create collection
            client.create_collection(
                collection_name="test_perf",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
            
            # Simulate indexing
            print("⏱️  Measuring indexing performance...")
            start = time.time()
            
            # Create test vectors (1536 dims like OpenAI embeddings)
            import numpy as np
            points = [
                PointStruct(
                    id=i,
                    vector=np.random.rand(1536).tolist(),
                    payload={"source": f"pdf_{i//100}"}
                )
                for i in range(vector_count)
            ]
            
            client.upsert(collection_name="test_perf", points=points)
            index_duration = time.time() - start
            
            self.results["qdrant_local"]["indexing"] = self.measure_indexing(
                "qdrant_local", vector_count, index_duration
            )
            
            # Simulate queries
            print("⏱️  Measuring query performance...")
            queries = []
            for i in range(100):
                start = time.time()
                results = client.search(
                    collection_name="test_perf",
                    query_vector=np.random.rand(1536).tolist(),
                    limit=5
                )
                latency = (time.time() - start) * 1000
                queries.append(latency)
            
            self.results["qdrant_local"]["query"] = self.measure_query(
                "qdrant_local", queries, len(queries)
            )
            self.results["qdrant_local"]["status"] = "✅ Success"
            
            print("✓ Qdrant Local testing completed")
            
        except Exception as e:
            self.results["qdrant_local"]["status"] = f"❌ Error: {str(e)}"
            print(f"❌ Qdrant Local test failed: {e}")

    def test_qdrant_cloud(self):
        """Test Qdrant Cloud performance (simulated)"""
        print("\n" + "="*60)
        print("🧪 Testing Qdrant Cloud Performance")
        print("="*60)
        
        # Check if Qdrant Cloud credentials exist
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url or not qdrant_key or "placeholder" in qdrant_url:
            print("⚠️  Qdrant Cloud credentials not configured")
            self.results["qdrant_cloud"]["status"] = "⚠️ Not configured (needs real credentials)"
            return
        
        try:
            from qdrant_client import QdrantClient
            import numpy as np
            
            # Initialize cloud client
            client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=30)
            
            # Query existing cloud collection
            print("⏱️  Measuring query performance...")
            queries = []
            
            for i in range(50):  # Fewer queries to cloud due to network latency
                start = time.time()
                results = client.search(
                    collection_name="course_materials",
                    query_vector=np.random.rand(1536).tolist(),
                    limit=5
                )
                latency = (time.time() - start) * 1000
                queries.append(latency)
            
            self.results["qdrant_cloud"]["query"] = self.measure_query(
                "qdrant_cloud", queries, len(queries)
            )
            self.results["qdrant_cloud"]["status"] = "✅ Success"
            
            print("✓ Qdrant Cloud testing completed")
            
        except Exception as e:
            self.results["qdrant_cloud"]["status"] = f"❌ Error: {str(e)}"
            print(f"⚠️ Qdrant Cloud test failed: {e}")

    def run_all_tests(self):
        """Run all performance tests"""
        print("\n" + "🚀 "*30)
        print("EduMate RAG - Performance Test Suite")
        print("🚀 "*30)
        
        self.test_chromadb()
        self.test_qdrant_local()
        self.test_qdrant_cloud()
        
        return self.results

    def save_results(self, filename: str = "PERFORMANCE_METRICS.json"):
        """Save results to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n✅ Results saved to {filename}")

    def print_summary(self):
        """Print human-readable summary"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        if "query" in self.results.get("chromadb", {}):
            chroma_latency = self.results["chromadb"]["query"]["avg_latency_ms"]
            chroma_throughput = self.results["chromadb"]["query"]["throughput_queries_per_sec"]
            print(f"\n🟢 ChromaDB:")
            print(f"   Avg Query Latency: {chroma_latency}ms")
            print(f"   Throughput: {chroma_throughput} queries/sec")
        
        if "query" in self.results.get("qdrant_local", {}):
            qdrant_latency = self.results["qdrant_local"]["query"]["avg_latency_ms"]
            qdrant_throughput = self.results["qdrant_local"]["query"]["throughput_queries_per_sec"]
            print(f"\n🟡 Qdrant Local:")
            print(f"   Avg Query Latency: {qdrant_latency}ms")
            print(f"   Throughput: {qdrant_throughput} queries/sec")
            
            if chroma_latency > 0:
                improvement = ((chroma_latency - qdrant_latency) / chroma_latency) * 100
                print(f"   ⚡ {improvement:.1f}% faster than ChromaDB")
        
        if "query" in self.results.get("qdrant_cloud", {}):
            cloud_latency = self.results["qdrant_cloud"]["query"]["avg_latency_ms"]
            print(f"\n🔵 Qdrant Cloud:")
            print(f"   Avg Query Latency: {cloud_latency}ms")
            print(f"   (Higher due to network latency)")

if __name__ == "__main__":
    tester = PerformanceTest()
    results = tester.run_all_tests()
    tester.print_summary()
    tester.save_results()
