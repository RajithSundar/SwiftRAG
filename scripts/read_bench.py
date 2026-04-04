import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
with open('benchmark_output.txt', 'r', encoding='utf-16') as f:
    content = f.read()
    print(content)
