import os
import json
from typing import Annotated, TypedDict, List, Dict, Any
from dotenv import load_dotenv
import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

import config
import prompts

load_dotenv()

class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    extracted_info: Dict[str, Any]
    retrieved_docs: List[Any]
    confidence_score: int
    relevance_score: int
    selected_country: str
    vetting_requested: bool
    end_session: bool
    factual_question: str

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

MISSING_VALUES = ["", "unknown", "not mentioned", "not provided", "none", "n/a", "null", "not specified"]

def is_pillar_missing(value):
    """Checks if a PILLAR value is effectively missing or null."""
    if value is None:
        return True
    return str(value).strip().lower() in MISSING_VALUES

def _build_state_prose(info: dict, country: str, visa: str) -> str:
    """Converts extracted_info dict into a compact prose summary for the LLM."""
    parts = []
    missing = []
    
    # Core
    if info.get("age") and not is_pillar_missing(info["age"]): parts.append(f"Age: {info['age']}")
    else: missing.append("Age")
    if info.get("nationality") and not is_pillar_missing(info["nationality"]): parts.append(f"Nationality: {info['nationality']}")
    else: missing.append("Nationality")
    if info.get("financials") and not is_pillar_missing(info["financials"]): parts.append(f"Financials: {info['financials']}")
    else: missing.append("Financials")
    if info.get("purpose") and not is_pillar_missing(info["purpose"]): parts.append(f"Purpose: {info['purpose']}")
    else: missing.append("Purpose")
    if country and country != "Unknown": parts.append(f"Target Country: {country}")
    else: missing.append("Target Country")
    if visa and visa != "Unknown": parts.append(f"Visa Category: {visa}")
    else: missing.append("Visa Category")
    
    # Supplementary
    if info.get("education") and not is_pillar_missing(info["education"]): parts.append(f"Education: {info['education']}")
    else: missing.append("Education")
    if info.get("employment") and not is_pillar_missing(info["employment"]): parts.append(f"Employment: {info['employment']}")
    else: missing.append("Employment")
    if info.get("english_proficiency") and not is_pillar_missing(info["english_proficiency"]): parts.append(f"English Proficiency: {info['english_proficiency']}")
    else: missing.append("English Proficiency")
    if info.get("ties_to_home_country") and not is_pillar_missing(info["ties_to_home_country"]): parts.append(f"Ties to Home Country: {info['ties_to_home_country']}")
    else: missing.append("Ties to Home Country")

    collected = ", ".join(parts) if parts else "No information collected yet."
    missing_str = ", ".join(missing) if missing else "None."
    return f"COLLECTED: {collected}\nSTILL MISSING: {missing_str}"

def agent(state: State):
    """
    Lightweight Agent: Uses State-to-Prose compression + last 2 messages.
    Only job is to be polite, react to user input, and fill extracted_info slots.
    """
    current_country = state.get("selected_country", "Unknown")
    info = state.get("extracted_info", {})
    current_visa = info.get("visa_category", "Unknown")
    
    # Build compact state summary instead of relying on full chat history
    state_prose = _build_state_prose(info, current_country, current_visa)
    
    system_prompt = prompts.INTERVIEW_SYSTEM_PROMPT.format(state_prose=state_prose)

    # Token optimization: send last 6 messages to preserve conversational continuity
    recent_messages = state["messages"][-6:]

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

    import time as _time
    chain = prompt | llm | StrOutputParser()
    
    raw_output = None
    for attempt in range(3):
        try:
            raw_output = chain.invoke({"messages": recent_messages})
            break
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = 30 * (attempt + 1)
                print(f"[WARN] Groq rate limit hit during agent generation. Retrying in {wait}s... (attempt {attempt + 1}/3)")
                _time.sleep(wait)
            else:
                print(f"[ERROR] API failed during agent generation: {e}")
                break
    
    if not raw_output or raw_output == "{}":
        raw_output = '{"extracted_info": {}, "response_to_user": "I am experiencing server issues. Could you please repeat that?"}'

    
    # Robustly extract JSON and Analysis
    # BUG FIX: Regex (greedy or non-greedy) fails on nested braces or multiple {} blocks.
    # Manual brace counting is more reliable.
    def find_json_boundary(text):
        start = text.find('{')
        if start == -1: return None, None
        count = 0
        for i in range(start, len(text)):
            if text[i] == '{': count += 1
            elif text[i] == '}': count -= 1
            if count == 0:
                return start, i + 1
        return None, None

    start, end = find_json_boundary(raw_output)
    if start is not None:
        try:
            json_str = raw_output[start:end]
            result = json.loads(json_str)
            # Text is everything BEFORE the first { or AFTER the last }
            response_before = raw_output[:start].strip()
            response_after = raw_output[end:].strip()
            response = response_before or response_after
            
            if not response and isinstance(result, dict):
                response = result.get("response_to_user", "")
        except json.JSONDecodeError:
            result = {}
            response = raw_output
    else:
        result = {}
        response = raw_output

    extracted = result.get("extracted_info", {})
    vetting = result.get("vetting_requested", False)
    end_session_requested = result.get("end_session_requested", False)
    factual_question = result.get("factual_question", "")
    
    if not response:
        response = "I've noted that information. Let me see what else we need to discuss."
    
    # Normalize state update
    # BUG FIX: Merge instead of overwrite, but skip unknown/missing values
    # so that a valid "age": "25" isn't overwritten by "age": "unknown"
    clean_extracted = {k: v for k, v in extracted.items() if not is_pillar_missing(v)}
    new_info = {**info, **clean_extracted}
    
    extracted_country = extracted.get("target_country") or current_country
    
    if is_pillar_missing(extracted_country): extracted_country = current_country

    return {
        "extracted_info": new_info,
        "selected_country": extracted_country,
        "vetting_requested": vetting,
        "end_session": end_session_requested,
        "factual_question": factual_question,
        "messages": [AIMessage(content=response)]
    }

def retrieve(state: State):
    """Retrieves relevant visa policy documents using vector search and Gemini-assisted reranking."""
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
    
    factual_question = state.get("factual_question")
    if factual_question:
        query = factual_question
    else:
        human_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        query = human_messages[-1].content if human_messages else state["messages"][-1].content
    
    # 0. Empty query guard (prevents embedding API 400 crash)
    if not query.strip():
        print("[DEBUG] Empty query detected, skipping retrieval.")
        return {"retrieved_docs": [], "relevance_score": 0}
    # 1. Broad retrieval with rate-limit retry
    import time as _time
    docs_and_scores = None
    for attempt in range(3):
        try:
            docs_and_scores = vectorstore.similarity_search_with_relevance_scores(
                query,
                k=20
            )
            break
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 30 * (attempt + 1)
                print(f"[WARN] Embedding rate limit hit. Retrying in {wait}s... (attempt {attempt + 1}/3)")
                _time.sleep(wait)
            else:
                raise
    
    if docs_and_scores is None:
        print("[ERROR] Embedding API unavailable after 3 retries.")
        return {"retrieved_docs": [], "relevance_score": 0}
    
    docs = [d[0] for d in docs_and_scores]
    
    # Country-aware filtering: prefer docs matching the user's target country
    target_country = (state.get("selected_country") or "").strip().lower()
    country_domain_map = {
        "us": ["uscis.gov", "state.gov"],
        "usa": ["uscis.gov", "state.gov"],
        "united states": ["uscis.gov", "state.gov"],
        "uk": ["gov.uk"],
        "united kingdom": ["gov.uk"],
        "britain": ["gov.uk"],
    }
    allowed_domains = country_domain_map.get(target_country, [])
    
    if allowed_domains:
        country_filtered = [d for d in docs if any(domain in (d.metadata.get("source_url") or "") for domain in allowed_domains)]
        if country_filtered:
            docs = country_filtered
            print(f"[DEBUG] Country filter applied for '{target_country}': {len(docs)} relevant chunks kept.")
    
    initial_urls = list(set([d.metadata.get("source_url") for d in docs]))
    print(f"\n[DEBUG] Candidates Found: {len(docs)} chunks from {len(initial_urls)} unique URLs")
    for url in initial_urls:
        if url: print(f" - Candidate: {url}")
    
    if not docs:
        return {"retrieved_docs": [], "relevance_score": 0}
        
    # 2. Gemini-assisted Reranking
    class RerankResult(BaseModel):
        scores: List[float] = Field(description="Scores between 0 and 1 for each document in order")
    
    rerank_parser = PydanticOutputParser(pydantic_object=RerankResult)
    rerank_prompt = ChatPromptTemplate.from_template(
        "You are a relevance evaluator. Rank these documents based on how specifically "
        "they answer the user's visa query: '{query}'\n\nDocs:\n{docs_text}\n\n"
        "Return ONLY the scores as valid JSON with NO python comments (no # signs) inside the JSON block.\n{format_instructions}"
    )
    
    docs_text = "\n".join([f"Doc {i}: {doc.page_content}" for i, doc in enumerate(docs)])
    try:
        raw_rerank = (rerank_prompt | llm | StrOutputParser()).invoke({
            "query": query, 
            "docs_text": docs_text,
            "format_instructions": rerank_parser.get_format_instructions()
        })
        rerank_output = rerank_parser.parse(raw_rerank)
        cross_scores = rerank_output.scores
    except Exception as e:
        print(f"[ERROR] Reranking failed: {e}")
        cross_scores = [0.5] * len(docs) # Conservative fallback — don't inflate confidence on parse failure
    
    # 3. Filter by threshold (0.7) and sort
    filtered_docs_with_scores = [(doc, float(score)) for doc, score in zip(docs, cross_scores) if score >= 0.7]
    filtered_docs_with_scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"[DEBUG] Reranking complete. {len(filtered_docs_with_scores)} / {len(docs)} chunks passed the 0.7 threshold.")
    
    # Fallback: if no docs pass 0.7, use top 3 regardless (some context > no context)
    if not filtered_docs_with_scores:
        all_with_scores = sorted(zip(docs, cross_scores), key=lambda x: x[1], reverse=True)
        filtered_docs_with_scores = [(d, float(s)) for d, s in all_with_scores[:3]]
        print(f"[DEBUG] Fallback: Using top {len(filtered_docs_with_scores)} docs below threshold.")
        
    final_docs = [d[0] for d in filtered_docs_with_scores[:3]]
    avg_score = sum(d[1] for d in filtered_docs_with_scores[:3]) / len(final_docs)
    retrieval_score = int(avg_score * 100)
    
    return {"retrieved_docs": final_docs, "relevance_score": retrieval_score}

def evaluate(state: State):
    """Generates advice and evaluates faithfulness against context.
    Uses State-to-Prose + last 3 messages instead of full history for token efficiency."""
    import time as _time
    context = "\n\n".join(doc.page_content for doc in state["retrieved_docs"])
    info = state.get("extracted_info", {})
    visa_cat = info.get("visa_category", "Unknown")
    
    # Token optimization: build prose profile from state dict instead of full history
    state_prose = _build_state_prose(info, state.get("selected_country", "Unknown"), visa_cat)
    
    # Only send the last 6 messages for conversational context
    recent_messages = state["messages"][-6:]
    
    # BUG FIX: Use .replace() instead of .format() to avoid KeyError when
    # policy documents (context) or user data contain curly braces like {embassy}
    advice_content = (prompts.ADVICE_SYSTEM_PROMPT
        .replace("{country}", state.get("selected_country", "Unknown"))
        .replace("{visa}", visa_cat)
        .replace("{age}", str(info.get('age', 'Unknown')))
        .replace("{nationality}", str(info.get('nationality', 'Unknown')))
        .replace("{financials}", str(info.get('financials', 'Unknown')))
        .replace("{purpose}", str(info.get('purpose', 'Unknown')))
        .replace("{education}", str(info.get('education', 'Not provided')))
        .replace("{employment}", str(info.get('employment', 'Not provided')))
        .replace("{english_proficiency}", str(info.get('english_proficiency', 'Not provided')))
        .replace("{ties_to_home_country}", str(info.get('ties_to_home_country', 'Not provided')))
        .replace("{context}", context)
    )
    
    is_ending = state.get("end_session", False)

    # --- NEW AUTO-CONCLUSION LOGIC ---
    # Automatically trigger the final verdict if the profile is complete enough
    core_required = ["age", "nationality", "financials", "purpose", "target_country", "visa_category"]
    core_missing = [p for p in core_required if is_pillar_missing(info.get(p))]
    
    supplementary = ["education", "employment", "english_proficiency", "ties_to_home_country"]
    supplementary_filled = sum(1 for p in supplementary if not is_pillar_missing(info.get(p)))

    # If all core pillars are met AND at least 4 supplementary pillars are met, force the conclusion!
    if not core_missing and supplementary_filled == 4:
        is_ending = True
    # ---------------------------------

    class Evaluation(BaseModel):
        relevance_score: float = Field(description="Score between 0 and 1 indicating confidence in the answer based on context")
        visa_probability: float = Field(description="Score between 0 and 1 indicating the estimated probability the applicant will receive the visa, based on their profile and the context")
        citations: List[str] = Field(description="List of specific policy sections or URLs used")

    answer = None
    if is_ending:
        human_instruction = (
            "The user profile is complete. Provide a structured final verdict containing:\n"
            "1. **Strengths:** What parts of their profile align well with policy?\n"
            "2. **Red Flags (If any):** Address Course Mismatches, Unverifiable Funds, etc.\n"
            "3. **Next Steps:** A strict chronological action plan.\n\n"
            "Do NOT ask any more questions. End the conversation gracefully and professionally."
        )
        answer_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=advice_content),
            MessagesPlaceholder(variable_name="messages"),
            ("human", human_instruction)
        ])

        # Rate-limit retry for advice generation
        for attempt in range(3):
            try:
                answer = (answer_prompt | llm | StrOutputParser()).invoke({"messages": recent_messages})
                break
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait = 30 * (attempt + 1)
                    print(f"[WARN] Groq rate limit hit during advice generation. Retrying in {wait}s... (attempt {attempt + 1}/3)")
                    _time.sleep(wait)
                else:
                    raise
    else:
        # DO NOT generate a new answer. Just evaluate the one the Agent already generated!
        ai_msgs = [m for m in state.get("messages", []) if isinstance(m, AIMessage)]
        answer = ai_msgs[-1].content if ai_msgs else ""
    
    if answer is None:
        answer = ""
    print(f"[DEBUG] Advisor raw output length: {len(answer)} chars")

    if not answer or not answer.strip():
        answer = "I've analyzed the policy manual for your situation. Based on your financial background and purpose of travel, I'm evaluating your eligibility for the relevant visa category."

    parser = PydanticOutputParser(pydantic_object=Evaluation)
    
    # BUG FIX: Pre-format the eval prompt with .replace() before wrapping in SystemMessage.
    # SystemMessage doesn't expand template variables, so {context}/{answer}/{format_instructions}
    # would be sent as literal text to the LLM without this.
    eval_content = (prompts.EVALUATION_PROMPT
        .replace("{format_instructions}", parser.get_format_instructions())
        .replace("{profile}", state_prose)
        .replace("{context}", context)
        .replace("{answer}", answer)
    )
    eval_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=eval_content)
    ])
    
    try:
        # Rate-limit retry for faithfulness evaluation
        raw_eval = None
        for attempt in range(3):
            try:
                raw_eval = (eval_prompt | llm | StrOutputParser()).invoke({})
                break
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait = 30 * (attempt + 1)
                    print(f"[WARN] Groq rate limit hit during evaluation. Retrying in {wait}s... (attempt {attempt + 1}/3)")
                    _time.sleep(wait)
                else:
                    raise
        
        if raw_eval is None:
            raise Exception("Evaluation API unavailable after 3 retries.")
        
        parsed_eval = parser.parse(raw_eval)
        llm_relevance_percent = parsed_eval.relevance_score * 100
        visa_probability_percent = parsed_eval.visa_probability * 100
    except Exception as e:
        llm_relevance_percent = 50.0
        visa_probability_percent = 0.0

    # Compose final relevance from retrieval score and LLM evaluation
    final_relevance_score = (state.get("relevance_score", 0) * 0.4) + (llm_relevance_percent * 0.6)

    if is_ending:
        metrics_text = f"\nMetrics for this session: - Relevance Score: {int(final_relevance_score)}% - Confidence Score (Visa Probability): {int(visa_probability_percent)}%"
        answer += metrics_text

    return {
        "messages": [AIMessage(content=answer)],
        "relevance_score": int(final_relevance_score),
        "confidence_score": int(visa_probability_percent),
        "end_session": is_ending  # <--- CRITICAL FIX: This passes the flag back to the UI!
    }

def router(state: State):
    """Branching logic: requires core 6 pillars + at least 2 supplementary fields."""
    if state.get("end_session") or state.get("vetting_requested"):
        return "evaluate"
        
    if state.get("factual_question"):
        return "retrieve"
    
    info = state.get("extracted_info", {})
    
    # Check Pillar Status First
    core_required = ["age", "nationality", "financials", "purpose", "target_country", "visa_category"]
    core_missing = [p for p in core_required if is_pillar_missing(info.get(p))]
    
    supplementary = ["education", "employment", "english_proficiency", "ties_to_home_country"]
    supplementary_filled = sum(1 for p in supplementary if not is_pillar_missing(info.get(p)))

    # --- THE FIX: Check only the LATEST message for expert triggers ---
    # We want to check what the user *just* said, not what they said 3 turns ago
    human_messages = [m for m in state.get("messages", []) if isinstance(m, HumanMessage)]
    last_user_msg = human_messages[-1].content.lower() if human_messages else ""
    
    mentioned_money = any(m in last_user_msg for m in ["$", "loan", "lakh", "₹", "bank", "savings", "pension"])
    mentioned_school = any(sch in last_user_msg for sch in ["university", "college", "school", "stanford", "harvard", "mit"])
    
    # If the profile is incomplete, but they just asked about money/schools right now, do a quick retrieval
    if (mentioned_money or mentioned_school) and (core_missing or supplementary_filled < 4):
        return "retrieve"
    # ----------------------------------------------------------------

    # If pillars are missing and no immediate triggers were fired, pause graph (wait for user)
    if core_missing or supplementary_filled < 4:
        return "end"
    
    # If we made it here, the profile is complete! 
    return "retrieve"

# Graph Construction
workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("retrieve", retrieve)
workflow.add_node("evaluate", evaluate)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router, {"retrieve": "retrieve", "evaluate": "evaluate", "end": END})
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
    
    if existing and existing.values and "extracted_info" in existing.values:
        state_input = {"messages": [HumanMessage(content=user_input)]}
    else:
        state_input = {
            "messages": [HumanMessage(content=user_input)],
            "selected_country": country or "Unknown",
            "extracted_info": {},
            "retrieved_docs": [],
            "relevance_score": 0,
            "confidence_score": 0,
            "vetting_requested": False,
            "end_session": False,
            "factual_question": ""
        }

    # Use invoke for deterministic state completion
    try:
        final_state = graph.invoke(state_input, config_run)
    except Exception as e:
        print(f"[ERROR] Graph execution failed: {e}")
        return {
            "answer": "I apologize, but I encountered an internal error. Please try again.",
            "relevance": 0,
            "confidence": 0,
            "info": state_input.get("extracted_info", {}),
            "sources": []
        }
    
    messages = final_state.get("messages", [])
    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    
    answer = ai_messages[-1].content if ai_messages else "I'm having trouble connecting to my knowledge base. Please try again."

    return {
        "answer": answer,
        "relevance": final_state.get("relevance_score", 0),
        "confidence": final_state.get("confidence_score", 0),
        "info": final_state.get("extracted_info", {}),
        "end_session": final_state.get("end_session", False),
        "sources": [doc.metadata.get("source_url") for doc in final_state.get("retrieved_docs", []) if doc.metadata and doc.metadata.get("source_url")]
    }

if __name__ == "__main__":
    import uuid
    tid = "session_" + str(uuid.uuid4())[:8]
    print(f"Senior Visa Consultant (Audit Version) active. State your background.")
    
    while True:
        u_in = input("You: ")
        if u_in.lower() in ["exit", "quit"]: break
        res = run_visa_consultation(u_in, tid)
        
        print(f"\nOfficer: {res['answer']}")
        if res.get("relevance", 0) > 0 or res.get("confidence", 0) > 0:
            print(f"Relevance: {res.get('relevance', 0)}% | Approval Probability (Confidence): {res.get('confidence', 0)}%")
        
        if res.get("sources"):
            print("Sources:")
            for s in res["sources"]:
                if s: print(f" - {s}")
        print()
