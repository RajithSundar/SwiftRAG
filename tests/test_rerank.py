import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sentence_transformers import CrossEncoder
import torch
print("Loading model...")
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', device='cpu')
print("Model loaded.")
scores = model.predict([["Is it raining?", "It is raining."], ["Is it raining?", "The sun is out."]])
print("Scores:", scores)
