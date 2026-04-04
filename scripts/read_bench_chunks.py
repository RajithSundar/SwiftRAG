import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
with open('benchmark_output.txt', 'r', encoding='utf-16') as f:
    content = f.read()
    # Print in chunks to avoid UI truncation
    chunk_size = 2000
    for i in range(0, len(content), chunk_size):
        print(f"--- CHUNK {i//chunk_size} ---")
        print(content[i:i+chunk_size])
