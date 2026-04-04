import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import query
import uuid
from langchain_core.messages import HumanMessage

def test_state_merge():
    tid = "test_merge_" + str(uuid.uuid4())[:8]
    print(f"Starting verification test (Thread: {tid})...")
    
    # Turn 1: Provide Age and Country
    print("\n--- Turn 1: Providing Age and Country ---")
    res1 = query.run_visa_consultation("I am 25 years old and want to go to the US.", tid)
    print(f"Extracted info after Turn 1: {res1['info']}")
    
    # Turn 2: Provide Financials (should NOT erase age)
    print("\n--- Turn 2: Providing Financials ---")
    res2 = query.run_visa_consultation("I have $100,000 in savings.", tid)
    print(f"Extracted info after Turn 2: {res2['info']}")
    
    # Verification
    info = res2.get('info', {})
    if info.get('age') == '25' and '$100,000' in str(info.get('financials')):
        print("\n✅ SUCCESS: State merged correctly. Age preserved while adding financials.")
    else:
        print("\n❌ FAILURE: State merge failed or data lost.")
        print(f"Final Info: {info}")

if __name__ == "__main__":
    try:
        test_state_merge()
    except Exception as e:
        print(f"Test crashed: {e}")
