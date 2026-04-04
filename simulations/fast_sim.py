import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uuid
from query import run_visa_consultation

def main():
    tid = "session_" + str(uuid.uuid4())[:8]
    
    with open("simulation_transcript.md", "w", encoding="utf-8") as f:
        f.write("# Automated Visa Consultation Simulation\n\n")

    user_msg = "Hi, I'm thinking about doing my master's in the US. I'm 23 and from India."
    
    # State tracking rules based on what Officer asks
    answered = {
        "field": False,
        "test": False,
        "finance": False,
        "university": False,
        "return": False,
        "interview": False,
        "work": False
    }

    for turn in range(12):
        print(f"User: {user_msg}")
        with open("simulation_transcript.md", "a", encoding="utf-8") as f:
            f.write(f"**User**: {user_msg}\n\n")
            
        res = run_visa_consultation(user_msg, tid)
        officer = res['answer']
        
        print(f"Officer: {officer}\n")
        with open("simulation_transcript.md", "a", encoding="utf-8") as f:
            f.write(f"**Officer**: {officer}\n\n")
            if res.get('relevance', 0) > 0 or res.get('confidence', 0) > 0:
                f.write(f"*Relevance: {res.get('relevance', 0)}% | Approval Probability (Confidence): {res.get('confidence', 0)}%*\n\n")

        off_lower = officer.lower()
        
        if "pleasure" in off_lower or "good luck" in off_lower or "wrap up" in off_lower:
            break
            
        # Determine next user action
        if ("field" in off_lower or "study" in off_lower) and not answered["field"]:
            user_msg = "I want to do an MS in Computer Science. I recently graduated with a B.Tech in CS."
            answered["field"] = True
        elif ("test" in off_lower or "gre" in off_lower or "toefl" in off_lower or "ielts" in off_lower) and not answered["test"]:
            user_msg = "I got 320 on the GRE and 110 on my TOEFL."
            answered["test"] = True
        elif ("funds" in off_lower or "financ" in off_lower or "sav" in off_lower or "support" in off_lower or "sponsor" in off_lower) and not answered["finance"]:
            user_msg = "I have $60,000 saved up in my bank account for tuition and living expenses."
            answered["finance"] = True
        elif ("university" in off_lower or "institutions" in off_lower or "school" in off_lower or "apply" in off_lower) and not answered["university"]:
            user_msg = "I'm looking at Stanford, MIT, and UT Austin. I'm aiming for an F-1 student visa."
            answered["university"] = True
        elif ("return" in off_lower or "home country" in off_lower or "after graduation" in off_lower or "ties" in off_lower or "plans after" in off_lower) and not answered["return"]:
            user_msg = "My family owns a home in Mumbai, and my dad runs a logistics business there which I plan to join and expand after my MS."
            answered["return"] = True
        elif ("process" in off_lower or "interview" in off_lower or "step" in off_lower) and not answered["interview"]:
            user_msg = "I haven't scheduled my visa interview yet. What should I expect during the interview, and do I need all bank statements at once?"
            answered["interview"] = True
        elif not answered["work"]:
            user_msg = "That makes sense. Can I also work on campus to help with expenses?"
            answered["work"] = True
        else:
            user_msg = "I think I have all the information I need right now. Thank you for your help, we can end the consultation."

if __name__ == "__main__":
    main()
