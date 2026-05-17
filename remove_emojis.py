#!/usr/bin/env python3
"""
Remove all emojis from project files
"""
import re
import os
from pathlib import Path

# Emoji pattern
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Symbols & pictographs
    "\U0001F680-\U0001F6FF"  # Transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # Flags (iOS)
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"  # Dingbats
    "\u3030"
    "]+",
    flags=re.UNICODE
)

root = Path("d:\\College \\Final Project\\edumate\\EduMate-RAG")
files_modified = 0

for file_path in root.rglob("*"):
    if file_path.is_file():
        # Skip binary files
        if file_path.suffix in ['.pyc', '.pyo', '.db', '.json']:
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if any(ord(char) > 127 and emoji_pattern.search(char) for char in content):
                new_content = emoji_pattern.sub('', content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                files_modified += 1
                print(f" {file_path.relative_to(root)}")
        except Exception as e:
            print(f" {file_path}: {e}")

print(f"\nTotal files cleaned: {files_modified}")
