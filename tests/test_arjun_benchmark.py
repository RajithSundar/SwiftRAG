import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid
import json

def run_benchmark():
    tid = "arjun_bench_" + str(uuid.uuid4())[:8]
    print(f"--- STARTING ARJUN BENCHMARK (Thread: {tid}) ---\n")

    # Turn 1: Detailed Profile
    print("Turn 1: Providing detailed profile...")
    user_msg_1 = (
        "I'm Arjun Mehra, 25, from Mumbai. I have $45,000 in savings and a $40,000 "
        "pre-approved HDFC loan. I want to do MS in Computer Science at Stanford. "
        "I have 2 years of work experience at Infosys. I've already taken the GRE."
    )
    res1 = query.run_visa_consultation(user_msg_1, tid)
    
    print(f"Officer: {res1['answer']}")
    print(f"Factual Question Extracted: {res1['info'].get('factual_question', 'NONE')}")
    print(f"Sources: {res1['sources']}")
    
    # Check for math or lack of deflection
    answer1 = res1['answer'].lower()
    if any(word in answer1 for word in ["85,000", "85000", "total"]):
        print("SUCCESS: Agent performed financial math.")
    else:
        print("WARNING: Agent did not explicitly mention the $85,000 total.")
    
    if "website" in answer1 or "check" in answer1:
         print("FAILURE: Agent deflected to a website.")
    else:
         print("SUCCESS: Agent did not deflect.")

    print("\n" + "="*50 + "\n")

    # Turn 2: Specific Risk Question (Pre-approval vs Sanction)
    print("Turn 2: Asking about pre-approval vs sanction letter...")
    user_msg_2 = (
        "I haven't reached out to Stanford yet because I was under the impression that you could guide me "
        "on the I-20 process. To be honest, I'm a bit worried—my HDFC loan is just a pre-approval letter, "
        "not a final disbursement sanction. Will the Stanford DSO accept a pre-approval letter for the I-20?"
    )
    res2 = query.run_visa_consultation(user_msg_2, tid)
    
    print(f"Officer: {res2['answer']}")
    print(f"Factual Question Extracted: {res2['info'].get('factual_question', 'NONE')}")
    print(f"Sources: {res2['sources']}")

    answer2 = res2['answer'].lower()
    if "sanction" in answer2 or "pre-approval" in answer2:
        print("SUCCESS: Agent addressed the document risk.")
    else:
        print("FAILURE: Agent ignored the document risk.")

    if "website" in answer2:
        print("FAILURE: Agent deflected on Turn 2.")
    else:
        print("SUCCESS: Agent provided direct consultation.")

    print("\n--- BENCHMARK COMPLETE ---")

if __name__ == "__main__":
    run_benchmark()
