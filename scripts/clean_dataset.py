import json
from pathlib import Path

def clean_dataset():
    project_root = Path(__file__).resolve().parent.parent
    dataset_path = project_root / "evaluation" / "datasets" / "rag_evaluation_dataset_v1.json"
    
    print(f"Reading dataset from: {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    old_qa_pairs = data["qa_pairs"]
    print(f"Original total questions: {len(old_qa_pairs)}")
    
    new_qa_pairs = []
    removed_count = 0
    modified_count = 0
    
    for qa in old_qa_pairs:
        # Standardize source and ground_truth_docs if they match "Data structure Book"
        modified = False
        source = qa.get("source", "")
        if source == "Data structure Book":
            qa["source"] = "Data structures and Algorithm Book"
            modified = True
            
        gt_docs = qa.get("ground_truth_docs", [])
        new_gt_docs = []
        for doc in gt_docs:
            if doc == "Data structure Book":
                new_gt_docs.append("Data structures and Algorithm Book")
                modified = True
            else:
                new_gt_docs.append(doc)
        qa["ground_truth_docs"] = new_gt_docs
        
        # Check if the query is for the missing Operating Systems PDF
        is_os = False
        if qa["source"] == "Operating Systems Lecture Notes":
            is_os = True
        for doc in qa["ground_truth_docs"]:
            if doc == "Operating Systems Lecture Notes":
                is_os = True
                
        if is_os:
            removed_count += 1
            print(f"Removing OS query [{qa.get('id')}]: {qa.get('question')[:60]}...")
            continue
            
        if modified:
            modified_count += 1
            
        new_qa_pairs.append(qa)
        
    print(f"\nRemoved {removed_count} Operating Systems queries.")
    print(f"Standardized {modified_count} Data structure Book references.")
    print(f"New total questions: {len(new_qa_pairs)}")
    
    # Assert counts
    assert len(new_qa_pairs) == len(old_qa_pairs) - removed_count, "Mismatch in question counts after filtering!"
    
    # Update metadata
    data["metadata"]["total_questions"] = len(new_qa_pairs)
    data["metadata"]["source_pdfs"] = 5  # OS is removed, leaving 5 PDFs
    data["qa_pairs"] = new_qa_pairs
    
    # Print new unique sources
    unique_sources = set(qa["source"] for qa in new_qa_pairs)
    unique_gt = set(doc for qa in new_qa_pairs for doc in qa["ground_truth_docs"])
    print(f"New unique sources: {unique_sources}")
    print(f"New unique ground truth docs: {unique_gt}")
    
    # Overwrite the original dataset file
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    print(f"Successfully wrote cleaned dataset to: {dataset_path}")

if __name__ == "__main__":
    clean_dataset()
