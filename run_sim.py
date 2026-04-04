import uuid
from query import run_visa_consultation

def run_simulation():
    thread_id = "sim_" + str(uuid.uuid4())[:8]
    
    print("\n" + "="*80)
    print("STARTING VISA CONSULTATION SIMULATION (EXPANDED CONVERSATIONAL INTELLIGENCE)")
    print("="*80 + "\n")
    
    inputs = [
        "Hi, I'm thinking about doing my master's in the US. I'm 23 and from India.",
        "I want to do my MS in Computer Science. I recently graduated with a B.Tech in CS.",
        "I have about $60,000 in my bank account.",
        "Yes, my family is back in Mumbai, we own a house there and my dad runs a business which I plan to join after I graduate.",
        "I have taken the GRE and got 320, and my TOEFL score is 110. I haven't applied to any universities yet though.",
        "Oh, by the way, I'm aiming for an F-1 student visa once I get accepted."
    ]
    
    for user_input in inputs:
        print(f"\nUser: {user_input}\n")
        
        res = run_visa_consultation(user_input, thread_id)
        
        print(f"\nOfficer: {res['answer']}")
        if res.get("relevance", 0) > 0 or res.get("confidence", 0) > 0:
            print(f"Relevance: {res.get('relevance', 0)}% | Approval Probability (Confidence): {res.get('confidence', 0)}%")
        if res.get("sources"):
            print("Sources:")
            for s in set(res["sources"]):
                print(f" - {s}")

if __name__ == "__main__":
    run_simulation()
