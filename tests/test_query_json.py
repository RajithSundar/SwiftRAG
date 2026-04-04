import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid
import json

tid = "test_" + str(uuid.uuid4())[:8]
res = query.run_visa_consultation("Hello, I am a 25 year old from India. I have $50,000 and want to study a Master's degree in the US.", tid)

with open("test_result.json", "w", encoding="utf-8") as f:
    json.dump(res, f, indent=4)
