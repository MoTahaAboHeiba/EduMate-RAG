#!/usr/bin/env python3
"""
RAG Evaluation Dataset Generator
=================================
Senior AI Engineer Implementation

Purpose:
    Automatically generate evaluation dataset from course PDFs.
    Creates QA pairs with ground truth answers for RAG evaluation.

Author: AI Engineering Team
Version: 1.0.0
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_loader import PDFLoader
from config import Config


class EvaluationDatasetBuilder:
    """Builds comprehensive evaluation datasets for RAG systems."""
    
    def __init__(self, config: Config):
        """Initialize dataset builder."""
        self.config = config
        self.pdf_loader = PDFLoader()
        self.evaluation_dir = Path(__file__).parent
        self.dataset_dir = self.evaluation_dir / "datasets"
        self.dataset_dir.mkdir(exist_ok=True)
        
    def extract_pdf_content(self) -> Dict[str, Any]:
        """Extract content from all course PDFs."""
        print("\n" + "="*70)
        print("STEP 1: Extracting PDF Content")
        print("="*70)
        
        pdf_files = list(Path(self.config.PDF_FOLDER_PATH).glob("*.pdf"))
        print(f"\nFound {len(pdf_files)} PDF files:")
        for pdf in pdf_files:
            print(f"  • {pdf.name}")
        
        pdf_contents = {}
        
        # Load all PDFs using PDFLoader
        print(f"\n Loading all PDFs...")
        try:
            all_docs = self.pdf_loader.load_all_pdfs()
            print(f"    Loaded {len(all_docs)} total chunks")
            
            # Group by source
            by_source = {}
            for doc in all_docs:
                source = doc['metadata']['source']
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(doc)
            
            # Store grouped by source
            for source, docs in by_source.items():
                pdf_contents[source] = {
                    "num_chunks": len(docs),
                    "chunks": docs,
                    "source": source
                }
                print(f"    Source '{source}': {len(docs)} chunks")
                
        except Exception as e:
            print(f"    Error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return pdf_contents
    
    def generate_qa_pairs(self, pdf_contents: Dict[str, Any]) -> List[Dict]:
        """Generate QA pairs from PDF content."""
        print("\n" + "="*70)
        print("STEP 2: Generating QA Pairs")
        print("="*70)
        
        qa_pairs = []
        concept_index = 1
        
        for source_name, source_data in pdf_contents.items():
            chunks = source_data["chunks"]
            source_type = self._get_pdf_type(source_name)
            
            print(f"\n  Processing {source_name} ({len(chunks)} chunks)")
            
            # Sample chunks for QA generation
            sample_interval = max(1, len(chunks) // 10)  # Sample ~10 chunks per PDF
            sample_chunks = chunks[::sample_interval]
            
            for chunk in sample_chunks:
                if concept_index > 100:  # Limit to ~100 pairs
                    break
                    
                # Extract sentences as potential questions
                chunk_content = chunk.get('content', '')
                sentences = chunk_content.split(".")
                
                for sentence in sentences[:2]:  # Take first 2 sentences
                    if len(sentence.strip()) > 20 and len(sentence.strip()) < 300:
                        qa_pair = {
                            "id": f"qa_{concept_index:03d}",
                            "question": sentence.strip() + "?",
                            "answer": chunk_content,
                            "source": source_name,
                            "source_type": source_type,
                            "difficulty": "medium",
                            "category": source_type,
                            "ground_truth_docs": [source_name]
                        }
                        qa_pairs.append(qa_pair)
                        concept_index += 1
                        
                        if concept_index > 100:
                            break
                
                if concept_index > 100:
                    break
        
        print(f"\n Generated {len(qa_pairs)} QA pairs")
        return qa_pairs
    
    def _get_pdf_type(self, pdf_name: str) -> str:
        """Determine PDF subject type."""
        pdf_lower = pdf_name.lower()
        if "architecture" in pdf_lower:
            return "Computer Architecture"
        elif "data structure" in pdf_lower or "algorithm" in pdf_lower:
            return "Data Structures & Algorithms"
        elif "operating" in pdf_lower or "os" in pdf_lower:
            return "Operating Systems"
        elif "oop" in pdf_lower or "object" in pdf_lower:
            return "Object-Oriented Programming"
        elif "ml" in pdf_lower or "machine learning" in pdf_lower:
            return "Machine Learning"
        else:
            return "General CS"
    
    def create_structured_dataset(self, qa_pairs: List[Dict]) -> Dict:
        """Create structured evaluation dataset."""
        print("\n" + "="*70)
        print("STEP 3: Creating Structured Dataset")
        print("="*70)
        
        dataset = {
            "metadata": {
                "name": "EduMate RAG Evaluation Dataset",
                "version": "1.0.0",
                "description": "Comprehensive evaluation dataset for RAG system",
                "created": str(Path(__file__).stat().st_mtime),
                "total_questions": len(qa_pairs),
                "source_pdfs": len(set(q["source"] for q in qa_pairs)),
            },
            "evaluation_config": {
                "retrieval_metrics": ["precision@3", "recall@5", "mrr"],
                "generation_metrics": ["faithfulness", "relevance", "completeness"],
                "performance_metrics": ["latency", "throughput"],
            },
            "qa_pairs": qa_pairs
        }
        
        print(f"\nDataset Structure:")
        print(f"  • Total QA Pairs: {len(qa_pairs)}")
        print(f"  • Source PDFs: {dataset['metadata']['source_pdfs']}")
        print(f"  • Categories: {len(set(q['category'] for q in qa_pairs))}")
        
        return dataset
    
    def save_dataset(self, dataset: Dict) -> str:
        """Save dataset to JSON file."""
        print("\n" + "="*70)
        print("STEP 4: Saving Dataset")
        print("="*70)
        
        dataset_path = self.dataset_dir / "rag_evaluation_dataset_v1.json"
        
        with open(dataset_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        file_size = dataset_path.stat().st_size / (1024 * 1024)  # MB
        print(f"\n Dataset saved to: {dataset_path}")
        print(f"   File size: {file_size:.2f} MB")
        
        return str(dataset_path)
    
    def generate_evaluation_report(self, dataset: Dict, dataset_path: str):
        """Generate dataset summary report."""
        print("\n" + "="*70)
        print("STEP 5: Generating Report")
        print("="*70)
        
        qa_pairs = dataset["qa_pairs"]
        
        # Group by category
        by_category = {}
        for qa in qa_pairs:
            cat = qa["category"]
            by_category[cat] = by_category.get(cat, 0) + 1
        
        # Group by difficulty
        by_difficulty = {}
        for qa in qa_pairs:
            diff = qa["difficulty"]
            by_difficulty[diff] = by_difficulty.get(diff, 0) + 1
        
        report = f"""

                    RAG EVALUATION DATASET REPORT                           


 DATASET OVERVIEW

  • Dataset Name:        EduMate RAG Evaluation Dataset v1
  • Total QA Pairs:      {len(qa_pairs)}
  • Source PDFs:         {dataset['metadata']['source_pdfs']}
  • File Path:           {dataset_path}

 BREAKDOWN BY CATEGORY

"""
        for category, count in sorted(by_category.items()):
            pct = (count / len(qa_pairs)) * 100
            report += f"  • {category:.<40} {count:>3} ({pct:>5.1f}%)\n"
        
        report += f"""
 BREAKDOWN BY DIFFICULTY

"""
        for difficulty, count in sorted(by_difficulty.items()):
            pct = (count / len(qa_pairs)) * 100
            report += f"  • {difficulty:.<40} {count:>3} ({pct:>5.1f}%)\n"
        
        report += f"""
 EVALUATION METRICS PLANNED

  Retrieval Metrics:
     Precision@3 (% of top-3 docs are relevant)
     Recall@5 (% of all relevant docs found in top-5)
     MRR (Mean Reciprocal Rank)
     NDCG@10 (Normalized Discounted Cumulative Gain)

  Generation Metrics:
     Faithfulness (% answers grounded in sources)
     Relevance (% answers address the question)
     Completeness (information coverage)
     Source Attribution Accuracy

  Performance Metrics:
     Query Latency (ms)
     Throughput (queries/sec)
     Memory Usage (MB)

 SAMPLE QA PAIRS (First 5)

"""
        for qa in qa_pairs[:5]:
            report += f"""
  [{qa['id']}] {qa['category']}
  Q: {qa['question'][:80]}...
  A: {qa['answer'][:100]}...
  Source: {qa['source']}
"""
        
        report += f"""
 DATASET READY FOR EVALUATION

  Next steps:
  1. Run RAG system against this dataset
  2. Calculate retrieval metrics
  3. Calculate generation metrics
  4. Generate evaluation report
  5. Identify improvement areas


                    Ready for Phase 2: Metrics Calculation                 

"""
        print(report)
        
        # Save report
        report_path = self.evaluation_dir / "DATASET_REPORT.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n Report saved to: {report_path}")


def main():
    """Main execution."""
    print("\n")
    print("")
    print("           RAG EVALUATION DATASET GENERATION - PHASE 1                      ")
    print("                   Senior AI Engineer Implementation                        ")
    print("")
    
    try:
        # Initialize
        config = Config()
        builder = EvaluationDatasetBuilder(config)
        
        # Pipeline
        pdf_contents = builder.extract_pdf_content()
        qa_pairs = builder.generate_qa_pairs(pdf_contents)
        dataset = builder.create_structured_dataset(qa_pairs)
        dataset_path = builder.save_dataset(dataset)
        builder.generate_evaluation_report(dataset, dataset_path)
        
        print("\n Phase 1 Complete: Evaluation dataset created successfully!")
        print("\n Next Phase: Create metrics calculation engine (Phase 2)")
        
    except Exception as e:
        print(f"\n Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
