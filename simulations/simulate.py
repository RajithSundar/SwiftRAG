import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid

tid = "sim_" + str(uuid.uuid4())[:8]

with open("simulate_out_clean.txt", "w", encoding="utf-8") as f:
    f.write(f"--- Simulating Conversation Thread {tid} ---\n")
    
    f.write("\nUser: I am a 19 year old Indian with a degree in CS\n")
    res1 = query.run_visa_consultation("I am a 19 year old Indian with a degree in CS", tid)
    f.write(f"Officer: {res1['answer']}\n")
    
    f.write("\nUser: Im looking at the US to pursue my masters in cs\n")
    res2 = query.run_visa_consultation("Im looking at the US to pursue my masters in cs", tid)
    f.write(f"Officer: {res2['answer']}\n")
    
    f.write("\nUser: I have about 500000usd saved from my freelancing works\n")
    res3 = query.run_visa_consultation("I have about 500000usd saved from my freelancing works", tid)
    f.write(f"Officer: {res3['answer']}\n")
    f.write(f"Relevance: {res3.get('relevance')}% | Confidence: {res3.get('confidence')}%\n")
    
    f.write("\nUser: I have already been accepted into purdue, have a 9 in ielts, and a complete sevis registration\n")
    res4 = query.run_visa_consultation("I have already been accepted into purdue, have a 9 in ielts, and a complete sevis registration", tid)
    f.write(f"Officer: {res4['answer']}\n")
    f.write(f"Relevance: {res4.get('relevance')}% | Confidence: {res4.get('confidence')}%\n")
