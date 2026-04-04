import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import sys
import uuid
import time
from query import run_visa_consultation

def main():
    tid = "session_" + str(uuid.uuid4())[:8]
    
    inputs = [
        "Hi, I'm thinking about doing my master's in the US. I'm 23 and from India.",
        "I want to do my MS in Computer Science. I recently graduated with a B.Tech in CS.",
        "I have about $60,000 in my bank account.",
        "Yes, my family is back in Mumbai, we own a house there and my dad runs a business which I plan to join after I graduate.",
        "I have taken the GRE and got 320, and my TOEFL score is 110. I haven't applied to any universities yet though.",
        "Oh, by the way, I'm aiming for an F-1 student visa once I get accepted.",
        "I'm looking at Stanford, MIT, and maybe some state universities like UIUC or UT Austin. Do you think those are realistic?",
        "Thanks! Let's say I get into UT Austin. What will my visa interview be like? Do I need to show all my bank statements at once?",
        "Can I work on campus to help with expenses while I'm there?",
        "That makes sense. Assuming I finish my degree, I definitely want to return home to help scale my dad's logistics business. Could they question my intent to return?",
        "I understand. I think I have all the information I need right now to start my applications. Thank you for your help, we can end the consultation."
    ]
    
    with open("simulation_transcript.md", "w") as f:
        # Header or preamble if needed (none for now)
        pass
        
    for user_input in inputs:
        print(f"User: {user_input}")
        with open("simulation_transcript.md", "a", encoding="utf-8") as f:
            f.write(f"**User**: {user_input}\n\n")
            
        print("Waiting for AI response...")
        res = run_visa_consultation(user_input, tid)
        
        officer_response = res['answer']
        print(f"Officer: {officer_response}\n")
        
        relevance = res.get('relevance', 0)
        confidence = res.get('confidence', 0)
        
        with open("simulation_transcript.md", "a", encoding="utf-8") as f:
            f.write(f"**Officer**: {officer_response}\n\n")
            if relevance > 0 or confidence > 0:
                f.write(f"*Relevance: {relevance}% | Approval Probability (Confidence): {confidence}%*\n\n")
                
        time.sleep(2)  # Avoid rate limit

if __name__ == "__main__":
    main()
