#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create zip file for peer review package"""
import zipfile
import os
import sys

def create_zip(source_dir, output_file):
    """Create zip file excluding large directories"""
    
    exclude_dirs = {'.git', '.venv', '__pycache__', '.pytest_cache', '.idea', '.egg-info', 'node_modules'}
    exclude_exts = {'.pyc', '.pyo', '.pyd', '.so'}
    
    total = 0
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zf.write(file_path, arcname)
                total += 1
    
    return os.path.getsize(output_file), total

if __name__ == '__main__':
    source = '.'
    output = '../ibkr-options-bot-peer-review-2026-01-09.zip'
    size, count = create_zip(source, output)
    print("✅ Zip file created successfully")
    print(f"📦 Name: ibkr-options-bot-peer-review-2026-01-09.zip")
    print(f"📊 Size: {size / 1024 / 1024:.2f} MB")
    print(f"📄 Files: {count} items")
    print(f"📍 Location: ../ibkr-options-bot-peer-review-2026-01-09.zip")
