#!/usr/bin/env python3
"""
Clean up unnecessary files from EduMate RAG project

Removes:
- Old Railway configuration
- Old scripts and process files
- Old documentation (moves to archive)
- Temporary files
- Test artifacts

Keeps only:
- Essential code (src/, tests/)
- Production files (Dockerfile, requirements.txt)
- Essential documentation
- Git configuration
"""

import os
import shutil
from pathlib import Path

# Files/dirs to remove
REMOVE_FILES = [
    # Railway specific (if not using)
    '.railway.toml',
    'Procfile',
    'runtime.txt',
    
    # Duplicate Docker
    'Dockerfile.txt',
    
    # Old reorganization scripts
    'reorganize_now.py',
    'reorganize_structure.py',
    'execute_reorganization.py',
    'execute_reorganization_direct.py',
    'quick_execute_reorganize.py',
    'manual_reorganize.py',
    'run_reorganize.py',
    'run_reorganize_bat.bat',
    'run_dev.py',
    'run_tests.py',
    'run_script.cmd',
    'create_dirs.bat',
    'remove_emojis.py',
    'verify_optimizations.py',
    'count_chunks.py',
    
    # Old output/logs
    'phase3_output.txt',
    'phase4_output.txt',
    'EXECUTION_OUTPUT.txt',
    
    # Old text files
    'ARCHITECTURE_DIAGRAM.txt',
    'PHASE_3_4_GUIDE.txt',
    'VISUAL_SUMMARY.txt',
    'QUICK_REFERENCE_EVALUATION.txt',
    'FINAL_REPORT.txt',
    
    # Test artifacts
    '.coverage',
]

# Old markdown files to move to archive
ARCHIVE_FILES = [
    'REORGANIZATION_REPORT.md',
    'EXECUTION_SUMMARY.md',
    'EXECUTION_SUMMARY.txt',
    'IMPLEMENTATION_COMPLETE.md',
    'EVALUATION_FRAMEWORK_COMPLETION_REPORT.md',
    'EVALUATION_RESULTS.md',
    'PHASE5_EVALUATION_REPORT.md',
    'YOUR_PHASE5_ACTION_PLAN.md',
    'README_DOCUMENTATION.md',
    'DOCUMENTATION_ORGANIZATION_COMPLETE.md',
]

def cleanup():
    base_dir = Path(__file__).parent
    archive_dir = base_dir / 'docs' / 'archive'
    
    # Create archive directory
    archive_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Archive directory ready: {archive_dir}")
    
    # Remove files
    print("\n🗑️  Removing unnecessary files:")
    removed_count = 0
    for filename in REMOVE_FILES:
        filepath = base_dir / filename
        if filepath.exists():
            filepath.unlink()
            print(f"  ✓ Removed: {filename}")
            removed_count += 1
    
    print(f"\n✅ Removed {removed_count} files")
    
    # Archive old documentation
    print("\n📦 Archiving old documentation:")
    archived_count = 0
    for filename in ARCHIVE_FILES:
        source = base_dir / filename
        if source.exists():
            dest = archive_dir / filename
            # Check if already in archive
            if source.parent == archive_dir:
                print(f"  ⊘ Already archived: {filename}")
            else:
                shutil.move(str(source), str(dest))
                print(f"  ✓ Archived: {filename}")
                archived_count += 1
    
    print(f"\n✅ Archived {archived_count} files to docs/archive/")
    
    # Print summary
    print("\n" + "="*60)
    print("CLEANUP COMPLETE")
    print("="*60)
    print(f"Removed: {removed_count} files")
    print(f"Archived: {archived_count} files")
    print(f"\n📂 Project is now clean and production-ready!")
    print("\n✨ Root directory is now focused on:")
    print("   ✓ Source code (src/)")
    print("   ✓ Tests (tests/)")
    print("   ✓ Documentation (docs/)")
    print("   ✓ Configuration (.env.example, requirements.txt)")
    print("   ✓ Production (Dockerfile, README.md)")
    print("   ✓ Deployment guides (HUGGING_FACE_DEPLOYMENT.md, etc.)")

if __name__ == "__main__":
    cleanup()
