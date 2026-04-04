import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
import uuid
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from query import run_visa_consultation

def main():
    tid = "session_" + str(uuid.uuid4())[:8]
    
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.6)
    
    persona_prompt = """
    You are an Indian student (23 years old) who wants to pursue an MS in Computer Science in the US.
    Your background:
    - B.Tech in CS (recently graduated).
    - $60,000 in savings in your bank account.
    - GRE score: 320, TOEFL: 110.
    - You want to apply for an F-1 student visa.
    - You are interested in Stanford, MIT, UIUC, and UT Austin.
    - Your family lives in Mumbai, owns a house, and your dad runs a logistics business that you intend to join after your MS.
    
    Guidelines for the interaction:
    1. The user you are talking to is the Visa Consultation Officer.
    2. Answer their questions directly based on your background. If they ask about something not in your background, invent a plausible answer fitting your persona.
    3. Be conversational and natural. Do not reveal all your background info at once. Only provide what is asked or highly relevant to the current topic.
    4. If it feels like the consultation is naturally concluding or you have gotten all the info you need about the process, you can politely thank the officer and say you are ready to prepare your application. Wrap it up around 10-12 turns.
    5. KEEP YOUR RESPONSES RELATIVELY SHORT (1-3 sentences) like a real chat.
    """
    
    chat_history = [SystemMessage(content=persona_prompt)]
    
    with open("simulation_transcript.md", "w", encoding="utf-8") as f:
        f.write("# Automated Dynamic Visa Consultation Simulation\n\n")

    # Start the conversation
    initial_user_msg = "Hi, I'm thinking about doing my master's in the US. I'm 23 and from India."
    print(f"User: {initial_user_msg}")
    
    with open("simulation_transcript.md", "a", encoding="utf-8") as f:
        f.write(f"**User**: {initial_user_msg}\n\n")
        
    chat_history.append(HumanMessage(content=f"You started with: {initial_user_msg}"))
    
    current_user_msg = initial_user_msg
    
    for turn in range(12):
        print("Waiting for Officer...")
        res = run_visa_consultation(current_user_msg, tid)
        officer_response = res['answer']
        relevance = res.get('relevance', 0)
        confidence = res.get('confidence', 0)
        
        print(f"\nOfficer: {officer_response}")
        if relevance > 0 or confidence > 0:
            print(f"Relevance: {relevance}% | Confidence: {confidence}%")
            
        with open("simulation_transcript.md", "a", encoding="utf-8") as f:
            f.write(f"**Officer**: {officer_response}\n\n")
            if relevance > 0 or confidence > 0:
                f.write(f"*Relevance: {relevance}% | Approval Probability (Confidence): {confidence}%*\n\n")
        
        if "good luck" in officer_response.lower() or "pleasure to assist" in officer_response.lower() or "reach out" in officer_response.lower():
            print("Conversation has naturally ended.")
            break
            
        # Get next user message
        chat_history.append(HumanMessage(content=f"Officer: {officer_response}\nBased on this, what do you reply? Remember to be conversational and concise."))
        
        ai_reply = llm.invoke(chat_history)
        current_user_msg = ai_reply.content.strip()
        chat_history.append(SystemMessage(content=f"You replied: {current_user_msg}"))
        
        print(f"\nUser: {current_user_msg}")
        with open("simulation_transcript.md", "a", encoding="utf-8") as f:
            f.write(f"**User**: {current_user_msg}\n\n")
            
        time.sleep(2) # rate limit prevention

if __name__ == "__main__":
    main()
    print("\nSimulation complete!")
