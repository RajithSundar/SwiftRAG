import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid

tid = "test_" + str(uuid.uuid4())[:8]
print("Running test consultation...\n")
res = query.run_visa_consultation("Hello, I am a 25 year old from India. I have $50,000 and want to study a Master's degree in the US.", tid)
print("\n--- RESULT ---")
print(f"Answer: {res.get('answer')}")
print(f"Relevance: {res.get('relevance')}")
print(f"Confidence (Probability): {res.get('confidence')}")
print(f"Info: {res.get('info')}")
