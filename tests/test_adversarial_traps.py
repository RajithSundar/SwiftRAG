import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid
import json

def test_trap_1_anchor_relative():
    """Trap 1: Brother at Google in San Jose while applicant goes to SJSU."""
    tid = "trap1_" + str(uuid.uuid4())[:8]
    print(f"\n--- TRAP 1: ANCHOR RELATIVE (Thread: {tid}) ---")
    
    # Fully qualified profile to trigger evaluate
    msg = (
        "I'm Rohan, 23, Indian. I'm going to San Jose State University for MS-SE. "
        "I have $60k in a savings account from my parents. I chose SJSU because "
        "my older brother lives in San Jose—he's at Google on an H-1B. I'll live with him to save rent."
    )
    res = query.run_visa_consultation(msg, tid)
    print(f"Officer: {res['answer']}")
    
    ans = res['answer'].lower()
    if "risk" in ans and ("intent" in ans or "relative" in ans or "brother" in ans):
        print("SUCCESS: Agent flagged the Anchor Relative risk.")
    else:
        print("FAILURE: Agent missed the Immigrant Intent risk.")

def test_trap_2_unverifiable_hustle():
    """Trap 2: $80k from crypto/freelance."""
    tid = "trap2_" + str(uuid.uuid4())[:8]
    print(f"\n--- TRAP 2: UNVERIFIABLE HUSTLE (Thread: {tid}) ---")
    
    msg = (
        "I'm Sara, 24, from India. I'm doing an MS in Data Science at NYU. "
        "I'm self-funding. I have $80,000 in my account that I earned from "
        "freelance web development and some crypto trading over 3 years. I have my TOEFL and GRE done."
    )
    res = query.run_visa_consultation(msg, tid)
    print(f"Officer: {res['answer']}")
    
    ans = res['answer'].lower()
    if "itr" in ans or "source" in ans or "tax" in ans or "contract" in ans:
        print("SUCCESS: Agent asked for documentation/ITRs for the hustle money.")
    else:
        print("FAILURE: Agent accepted the unverified cash blindly.")

def test_trap_3_course_mismatch():
    """Trap 3: CS Engineer -> General Management."""
    tid = "trap3_" + str(uuid.uuid4())[:8]
    print(f"\n--- TRAP 3: COURSE MISMATCH (Thread: {tid}) ---")
    
    msg = (
        "I'm Amit, 26, from India. I have a B.Tech in CS and 4 years of experience "
        "as a Senior Software Engineer at TCS. I got into a mid-tier school for a "
        "Master's in General Engineering Management. I have $70k in a loan sanctioned."
    )
    res = query.run_visa_consultation(msg, tid)
    print(f"Officer: {res['answer']}")
    
    ans = res['answer'].lower()
    if "progression" in ans or "logic" in ans or "mismatch" in ans or "why" in ans:
        print("SUCCESS: Agent challenged the academic trajectory.")
    else:
        print("FAILURE: Agent didn't question the downward/weird pivot.")

def test_trap_4_prearranged_employment():
    """Trap 4: Startup CEO waiting for them."""
    tid = "trap4_" + str(uuid.uuid4())[:8]
    print(f"\n--- TRAP 4: PRE-ARRANGED EMPLOYMENT (Thread: {tid}) ---")
    
    msg = (
        "I'm Neha, 22, from India. I'm going to MS in AI at Northeastern. "
        "A startup in Silicon Valley actually offered me a job but couldn't get the H-1B. "
        "The CEO told me to come on an F-1 first and they'll hire me the day I graduate on OPT. "
        "My parents are sponsoring my $90k tuition."
    )
    res = query.run_visa_consultation(msg, tid)
    print(f"Officer: {res['answer']}")
    
    ans = res['answer'].lower()
    if "urgent" in ans or "do not mention" in ans or "rejection" in ans or "intent" in ans:
        print("SUCCESS: Agent gave the urgent 'Dual Intent' warning.")
    else:
        print("FAILURE: Agent missed the pre-arranged employment trap.")

if __name__ == "__main__":
    test_trap_1_anchor_relative()
    test_trap_2_unverifiable_hustle()
    test_trap_3_course_mismatch()
    test_trap_4_prearranged_employment()
