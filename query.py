import os
import json
import re
from typing import Annotated, TypedDict, List, Dict, Any, Union
from dotenv import load_dotenv
import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

import config
import prompts

load_dotenv()

class State(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    extracted_info: Dict[str, Any]
    retrieved_docs: List[Any]
    confidence_score: int
    faithfulness: int
    selected_country: str
    visa_type: str
    vetting_requested: bool

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

MISSING_VALUES = ["", "unknown", "not mentioned", "not provided", "none", "n/a", "null"]

def is_pillar_missing(value):
    """Checks if a PILLAR value is effectively missing or null."""
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_VALUES

def parse_llm_json(raw_text: str) -> dict:
    """Robustly extracts and parses JSON from LLM output string."""
    json_match = re.search(r'\{[\s\S]*\}', raw_text)
    if not json_match:
        return {"response_to_user": raw_text}
    try:
        data = json.loads(json_match.group())
        return data
    except json.JSONDecodeError:
        return {"response_to_user": raw_text}

def agent(state: State):
    """
    Refactored Agent: Acts as a professional human consultant.
    Prevents robotic transitions by using history-aware reactions.
    """
    current_country = state.get("selected_country", "Unknown")
    current_visa = state.get("visa_type", "Unknown")
    
    system_prompt = (
        "You are an expert Visa Consultant. Your goal is to guide the user through a natural "
        "consultation. \n\n"
        "### Rules for Human-like Dialogue ###\n"
        "1. **Never** refer to the user in the third person. Use 'You'.\n"
        "2. **Acknowledge and Validate**: Always react to the specific content of the user's last message. "
        "If they mention $100,000 in freelancing savings, compliment their initiative and explain "
        "how that strengthens their financial profile for the visa.\n"
        "3. **Conversational Bridging**: Instead of just asking for a missing piece of info, explain "
        "why it's the next logical step. (e.g., 'Since your finances are so strong, the next big hurdle "
        "is matching your CSE background with the right university. Have you shortlisted any yet?')\n"
        "4. **No Lists**: Keep the dialogue to 2-4 cohesive sentences. Do not provide 'requirements' "
        "lists here; that is for the final evaluation stage.\n"
        "\nReturn the analysis followed by the JSON state update. "
        "Format: [Analysis] {{ \"extracted_info\": {{ ... }}, \"vetting_requested\": false }}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | llm | StrOutputParser()
    raw_output = chain.invoke({"messages": state["messages"]})
    
    # Robustly extract JSON and Analysis
    json_match = re.search(r'\{[\s\S]*\}', raw_output)
    if json_match:
        try:
            # Use json.loads instead of eval for safety
            result = json.loads(json_match.group())
            response = raw_output[:json_match.start()].strip()
            # If the LLM put the analysis inside "response_to_user" instead of outside
            if not response and "response_to_user" in result:
                response = result["response_to_user"]
        except json.JSONDecodeError:
            result = {}
            response = raw_output
    else:
        result = {}
        response = raw_output

    extracted = result.get("extracted_info", {})
    vetting = result.get("vetting_requested", False)
    
    # Normalize state update
    extracted_country = extracted.get("target_country") or current_country
    extracted_visa = extracted.get("visa_category") or current_visa
    
    if is_pillar_missing(extracted_country): extracted_country = current_country
    if is_pillar_missing(extracted_visa): extracted_visa = current_visa

    return {
        "extracted_info": extracted,
        "selected_country": extracted_country,
        "visa_type": extracted_visa,
        "vetting_requested": vetting,
        "messages": [AIMessage(content=response)]
    }

def retrieve(state: State):
    """Retrieves relevant visa policy documents using vector search."""
    from chromadb.config import Settings
    client = chromadb.PersistentClient(
        path=config.CHROMA_PERSIST_DIR,
        settings=Settings(allow_reset=True, anonymized_telemetry=False)
    )
    vectorstore = Chroma(
        client=client,
        collection_name=config.COLLECTION_NAME,
        embedding_function=embedding_model
    )
    
    human_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    query = human_messages[-1].content if human_messages else state["messages"][-1].content
    
    docs_and_scores = vectorstore.similarity_search_with_relevance_scores(
        query,
        k=3,
        filter={"country": state.get("selected_country", "UK")}
    )
    
    docs = [d[0] for d in docs_and_scores]
    scores = [d[1] for d in docs_and_scores]
    
    # Weighted confidence scoring
    weights = [0.5, 0.3, 0.2]
    retrieval_score = 0.0
    if scores:
        w = weights[:len(scores)]
        if sum(w) > 0:
            retrieval_score = (sum(s * weight for s, weight in zip(scores, w)) / sum(w)) * 100
    
    return {"retrieved_docs": docs, "confidence_score": int(retrieval_score)}

def evaluate(state: State):
    """Generates advice and evaluates faithfulness against context."""
    context = "\n\n".join(doc.page_content for doc in state["retrieved_docs"])
    info = state.get("extracted_info", {})
    
    answer_prompt = ChatPromptTemplate.from_messages([
        ("system", prompts.ADVICE_SYSTEM_PROMPT.format(
            country=state.get("selected_country", "Unknown"),
            visa=state.get("visa_type", "Unknown"),
            age=info.get('age'),
            nationality=info.get('nationality'),
            financials=info.get('financials'),
            purpose=info.get('purpose'),
            context=context
        )),
        MessagesPlaceholder("messages")
    ])
    
    answer = (answer_prompt | llm | StrOutputParser()).invoke({"messages": state["messages"]})

    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", prompts.EVAL_SYSTEM_PROMPT.format(context=context, answer=answer))
    ])
    
    f_score_str = (eval_prompt | llm | StrOutputParser()).invoke({})
    try:
        f_score = int(re.search(r'\d', f_score_str).group())
    except:
        f_score = 3

    faithfulness_percent = (f_score / 5.0) * 100
    final_confidence = (state["confidence_score"] + faithfulness_percent) / 2

    return {
        "messages": [AIMessage(content=answer)],
        "faithfulness": f_score,
        "confidence_score": int(final_confidence)
    }

def router(state: State):
    """Branching logic for the graph based on information completeness."""
    if state.get("vetting_requested", False):
        return "end"
    
    info = state.get("extracted_info", {})
    required = ["age", "nationality", "financials", "purpose", "target_country", "visa_category"]
    missing = [p for p in required if is_pillar_missing(info.get(p))]
    
    if missing:
        return "end"
    return "retrieve"

# Graph Construction
workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("retrieve", retrieve)
workflow.add_node("evaluate", evaluate)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router, {"retrieve": "retrieve", "end": END})
workflow.add_edge("retrieve", "evaluate")
workflow.add_edge("evaluate", END)

# Checkpointer configuration: LangGraph API handles persistence automatically.
# We only use MemorySaver for local manual runs.
if os.getenv("LANGGRAPH_API_URL") or os.getenv("LANGGRAPH_API") or os.getenv("LANGGRAPH_DEV"):
    graph = workflow.compile()
else:
    _memory = MemorySaver()
    graph = workflow.compile(checkpointer=_memory)

def run_visa_consultation(user_input: str, thread_id: str, country: str = None, visa: str = None):
    """External API for running the consultation graph."""
    config_run = {"configurable": {"thread_id": thread_id}}
    existing = graph.get_state(config_run)
    
    if existing.values:
        state_input = {"messages": [HumanMessage(content=user_input)]}
    else:
        state_input = {
            "messages": [HumanMessage(content=user_input)],
            "selected_country": country or "Unknown",
            "visa_type": visa or "Unknown",
            "extracted_info": {},
            "retrieved_docs": [],
            "confidence_score": 0,
            "faithfulness": 0,
            "vetting_requested": False
        }

    for _ in graph.stream(state_input, config_run, stream_mode="updates"):
        pass

    last_state = graph.get_state(config_run).values
    return {
        "answer": last_state["messages"][-1].content,
        "confidence": last_state.get("confidence_score", 0),
        "info": last_state.get("extracted_info", {}),
        "sources": [doc.metadata.get("source_url") for doc in last_state.get("retrieved_docs", [])]
    }

if __name__ == "__main__":
    tid = "session_refactored_1"
    print("Senior Visa Consultant (Audit Version) active. State your background.")
    while True:
        u_in = input("You: ")
        if u_in.lower() in ["exit", "quit"]: break
        res = run_visa_consultation(u_in, tid)
        print(f"Officer: {res['answer']}")
        if res.get('confidence'):
            print(f"Confidence: {res['confidence']}%")
