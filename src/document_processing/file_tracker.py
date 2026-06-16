"""
File modification tracker for incremental PDF indexing.
Tracks PDF file modification times to detect changes.
"""
import json
from pathlib import Path
from typing import Dict, Tuple


class FileTracker:
    """Track file modification times for incremental processing."""
    
    def __init__(self, cache_dir: Path = None):
        """
        Initialize file tracker.
        
        Args:
            cache_dir: Directory to store file tracking metadata
        """
        if cache_dir is None:
            cache_dir = Path(".cache") / "file_tracking"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tracker_file = self.cache_dir / "file_metadata.json"
        self.file_metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Dict]:
        """Load file metadata from cache."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load file metadata: {e}")
                return {}
        return {}
    
    def _save_metadata(self):
        """Save file metadata to cache."""
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.file_metadata, f, indent=2)
        except Exception as e:
            print(f"Failed to save file metadata: {e}")
    
    def get_file_hash(self, file_path: Path) -> Tuple[float, int]:
        """
        Get file modification time and size.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (modification_time, file_size)
        """
        if not file_path.exists():
            return (0, 0)
        
        stat = file_path.stat()
        return (stat.st_mtime, stat.st_size)
    
    def is_changed(self, file_path: Path) -> bool:
        """
        Check if file has changed since last tracking.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is new or modified, False otherwise
        """
        file_key = str(file_path)
        current_hash = self.get_file_hash(file_path)
        
        if file_key not in self.file_metadata:
            return True
        
        stored_hash = self.file_metadata[file_key]
        return current_hash != stored_hash
    
    def mark_processed(self, file_path: Path):
        """
        Mark file as processed by storing its current hash.
        
        Args:
            file_path: Path to file
        """
        file_key = str(file_path)
        self.file_metadata[file_key] = list(self.get_file_hash(file_path))
        self._save_metadata()
    
    def get_changed_files(self, pdf_files: list) -> Tuple[list, list]:
        """
        Partition files into changed and unchanged.
        
        Args:
            pdf_files: List of PDF file paths
            
        Returns:
            Tuple of (changed_files, unchanged_files)
        """
        changed = []
        unchanged = []
        
        for pdf_file in pdf_files:
            if self.is_changed(pdf_file):
                changed.append(pdf_file)
            else:
                unchanged.append(pdf_file)
        
        return changed, unchanged
    
    def clear_tracking(self):
        """Clear all tracked file metadata."""
        self.file_metadata = {}
        self._save_metadata()


file_tracker = FileTracker()
