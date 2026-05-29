#!/usr/bin/env python3
"""
Organize EduMate documentation by consolidating scattered MD files.
Creates archive directory and moves old process documentation.
"""

import os
import shutil
from pathlib import Path

# Base directory
base_dir = Path(__file__).parent
docs_dir = base_dir / 'docs'
archive_dir = docs_dir / 'archive'

# Create archive directory if it doesn't exist
archive_dir.mkdir(parents=True, exist_ok=True)
print(f"✓ Archive directory: {archive_dir}")

# Files to archive (process/execution documentation)
archive_files = [
    'REORGANIZATION_REPORT.md',
    'EXECUTION_SUMMARY.md',
    'IMPLEMENTATION_COMPLETE.md',
    'EVALUATION_FRAMEWORK_COMPLETION_REPORT.md',
    'EVALUATION_RESULTS.md',
    'YOUR_PHASE5_ACTION_PLAN.md',
    'README_DOCUMENTATION.md',
    'QUICK_REFERENCE_EVALUATION.txt',
    'EXECUTION_OUTPUT.txt',
    'EXECUTION_SUMMARY.txt',
    'FINAL_REPORT.txt',
    'VISUAL_SUMMARY.txt',
    'PHASE_3_4_GUIDE.txt',
    'ARCHITECTURE_DIAGRAM.txt'
]

# Files to keep in root and move to docs
keep_to_move = {
    'TECHNICAL_GUIDE.md': docs_dir / 'TECHNICAL_GUIDE.md',
    'OPTIMIZATION_GUIDE.md': docs_dir / 'OPTIMIZATION_GUIDE.md',
    'PHASE5_OPTIMIZATION_SUMMARY.md': docs_dir / 'PHASE5_OPTIMIZATION_SUMMARY.md',
    'afterQDRANT.md': docs_dir / 'QDRANT_MIGRATION.md',
}

# Archive old files
print("\n📦 Archiving process documentation:")
for filename in archive_files:
    source = base_dir / filename
    if source.exists():
        dest = archive_dir / filename
        shutil.move(str(source), str(dest))
        print(f"  ✓ {filename} → archive/")
    else:
        print(f"  ⊘ {filename} (not found)")

# Move valuable docs to docs/
print("\n📂 Moving active documentation to docs/:")
for filename, dest_path in keep_to_move.items():
    source = base_dir / filename
    if source.exists():
        shutil.move(str(source), str(dest_path))
        print(f"  ✓ {filename} → {dest_path.name}")
    else:
        print(f"  ⊘ {filename} (not found)")

# Handle duplicate PHASE5_EVALUATION_REPORT.md
phase5_root = base_dir / 'PHASE5_EVALUATION_REPORT.md'
phase5_docs = docs_dir / 'PHASE5_EVALUATION_REPORT.md'
if phase5_root.exists() and phase5_docs.exists():
    print("\n📋 Duplicate detected:")
    print(f"  Archiving: {phase5_root}")
    shutil.move(str(phase5_root), str(archive_dir / 'PHASE5_EVALUATION_REPORT.md'))

print("\n" + "="*60)
print("✅ Documentation organization complete!")
print("="*60)

# Summary
print("\n📊 Final structure:")
print(f"  Root directory: Cleaned up")
print(f"  docs/: Active user documentation")
print(f"  docs/archive/: Process documentation (for reference)")

# List what's in docs now
print("\n📚 Active documentation in docs/:")
for item in sorted(docs_dir.glob('*.md')):
    if item.name != 'archive':
        print(f"  - {item.name}")

print("\n🎯 README.md has been updated with documentation links")
print("\n💡 Next step: Run 'git pull' to sync the project structure changes from GitHub")
