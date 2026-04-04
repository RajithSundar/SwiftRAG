import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid

def test_sequential_hallucination_fix():
    """Verify that the agent doesn't skip to the interview step."""
    tid = "seq_test_" + str(uuid.uuid4())[:8]
    print(f"\n--- SEQUENTIAL CONSTRAINT TEST (Thread: {tid}) ---")
    
    # User provides 4 pillars + admission, but NO mention of I-20 or SEVIS
    msg = (
        "My name is Rahul, 23. I'm Indian. I've been admitted to ASU for MS in Software Engineering. "
        "My parents are sponsoring me fully with $50,000 in liquid savings. I have no US relatives "
        "and plan to return to India to work as a Senior Engineer at Infosys."
    )
    res = query.run_visa_consultation(msg, tid)
    answer = res['answer']
    print(f"Agent Reply: {answer}")
    
    # Assertions
    interview_mentioned = "interview" in answer.lower() or "schedule" in answer.lower()
    i20_mentioned = "i-20" in answer.lower() or "sevis" in answer.lower() or "admission office" in answer.lower()
    
    if interview_mentioned and not i20_mentioned:
        print("FAILURE: Agent jumped to interview without mentioning I-20/SEVIS.")
    elif i20_mentioned:
        print("SUCCESS: Agent correctly identified I-20/SEVIS as the next step.")
    else:
        print("NEUTRAL: Agent didn't mention I-20 or interview. Check manually.")

if __name__ == "__main__":
    test_sequential_hallucination_fix()
