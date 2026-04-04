import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid

tid = "sim_ext_" + str(uuid.uuid4())[:8]

dialogue = [
    "Hi, I'm a 35-year-old software engineer from Brazil, looking to move to the UK with my wife.",
    "I have an official job offer from a fintech company in London with an £85,000 salary, and I'm targeting a Skilled Worker Visa.",
    "I have around £15,000 in personal savings in my bank account. My employer has already issued my Certificate of Sponsorship (CoS).",
    "I've also passed the IELTS UKVI with a C1 level, and I have a clean criminal record.",
]

print(f"Starting simulation {tid}...")

with open("simulate_ext_out.txt", "w", encoding="utf-8") as f:
    f.write(f"--- Extensive Simulation Thread {tid} ---\n")
    
    for i, user_msg in enumerate(dialogue):
        print(f"Executing turn {i+1}...")
        f.write(f"\nUser: {user_msg}\n")
        res = query.run_visa_consultation(user_msg, tid)
        f.write(f"Officer: {res['answer']}\n")
        if res.get('relevance', 0) > 0 or res.get('confidence', 0) > 0:
            f.write(f"Relevance: {res.get('relevance')}% | Confidence: {res.get('confidence')}%\n")
            
print("Simulation complete. Check simulate_ext_out.txt")
