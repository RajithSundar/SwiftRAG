**Technical Project Report: SwiftVisa - AI-Powered Visa Eligibility
Screening Agent**

This report details the "SwiftVisa" project, an advanced application
of an LLM-powered Retrieval-Augmented Generation (RAG) system
orchestrated using LangGraph. The system is engineered to leverage
natural language reasoning and state-machine transitions for the
comprehensive evaluation of US and UK visa eligibility. It is designed
to provide consultative, policy-grounded guidance, delivering
transparent and explainable eligibility assessments.

**Introduction**

The SwiftVisa project addresses the limitations of conventional visa
screening tools by shifting from rigid filtering to a conversational,
state-based interaction. The system proactively identifies and tracks a 
structured set of **10 Informational Pillars**, categorized into **6 Core Pillars** 
(Age, Nationality, Financials, Purpose, Target Country, Visa Category) 
and **4 Supplementary Fields** (Education, Employment, English Proficiency, 
Ties to Home Country). This methodology facilitates a nuanced user
experience, simulating the diagnostic process of an experienced visa
officer through multi-turn dialogue.

**Objectives**

The core objectives of the SwiftVisa system development are:

- Grounding and Transparency: Provide advice strictly grounded in
  official government policy documents from USCIS and gov.uk.

- Non-Hallucinated Output: Mitigate LLM hallucinations via a robust RAG
  pipeline and self-audit evaluation within the graph.

- Explainable Reasoning: Link eligibility assessments explicitly to
  relevant policy text and provide a confidence-based probability of success.

- History-Aware Conversation: Deliver natural reactions and logical
  bridging between information gathering steps using **State-to-Prose compression**.

**Requirements**

The technical stack was selected for performance, modularity, and
state-management capabilities:

- Core Language: Python (3.12)

- Orchestration Framework: LangGraph (State-machine architecture)

- Inference Engine: **Groq API** (Utilizing the **Llama-3.3-70b-versatile** model)

- Vector Database: ChromaDB (Local persistent storage)

- Embeddings Model: **Google Generative AI Embeddings** (gemini-embedding-001)

- Observability Platform: LangSmith (Full trace telemetry)

**Methodology**

The system is built upon a dual-layer RAG architecture managed by a
LangGraph state machine, featuring advanced state merging and reranking logic.

**State-Aware Agent Node**

The agent node uses a compressed "prose profile" of the current state to maintain context without exceeding token limits. It employs a **robust brace-counting algorithm** for reliable JSON extraction and tracks a `completed_steps` list to prevent repetitive questions.

```python
def agent(state: State):
    # Compress 10-pillar state into prose for the LLM
    state_prose = _build_state_prose(info, current_country, current_visa)
    system_prompt = prompts.INTERVIEW_SYSTEM_PROMPT.format(state_prose=state_prose)

    # Robust JSON extraction via manual brace counting
    start, end = find_json_boundary(raw_output)
    if start is not None:
        result = json.loads(raw_output[start:end])
    
    # Merge extracted info and track completed steps
    clean_extracted = {k: v for k, v in extracted.items() if not is_pillar_missing(v)}
    new_info = {**info, **clean_extracted}
    merged_steps = list(set(state.get("completed_steps", []) + result.get("completed_steps", [])))
    
    return {
        "extracted_info": new_info,
        "completed_steps": merged_steps,
        "selected_country": extracted_country,
        "visa_type": extracted_visa,
        "messages": [AIMessage(content=response)]
    }
```

**Advanced Document Retrieval and Reranking**

The retrieval node implements country-aware metadata filtering and **Gemini-assisted reranking** to ensure high precision. It fetches 20 candidates and refines them to the top 3 most relevant policy chunks based on a 0.7 relevance threshold.

```python
def retrieve(state: State):
    # Broad retrieval from ChromaDB (k=20) with rate-limit retries
    docs_and_scores = vectorstore.similarity_search_with_relevance_scores(query, k=20)
    docs = [d[0] for d in docs_and_scores]
    
    # Country-aware filtering (USCIS vs gov.uk isolation)
    allowed_domains = country_domain_map.get(target_country, [])
    docs = [d for d in docs if any(dom in d.metadata.get("source_url") for dom in allowed_domains)]
    
    # Gemini-assisted Reranking with 0.7 threshold
    raw_rerank = (rerank_prompt | llm | StrOutputParser()).invoke({"query": query, "docs_text": docs_text})
    cross_scores = rerank_parser.parse(raw_rerank).scores
    filtered_docs = [(doc, s) for doc, s in zip(docs, cross_scores) if s >= 0.7]
    
    return {"retrieved_docs": [d[0] for d in filtered_docs[:3]], "relevance_score": int(avg_score * 100)}
```

**LangGraph State Machine Layout**

The orchestration is defined as a declarative StateGraph with **"Expert-First" routing logic**. It triggers retrieval early if specific high-value data (financials or university names) is detected in the *latest* message. It also features **Auto-Conclusion logic** that forces a final verdict once all 10 pillars are satisfied.

```python
workflow = StateGraph(State)
workflow.add_node("agent", agent)
workflow.add_node("retrieve", retrieve)
workflow.add_node("evaluate", evaluate)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", router, {"retrieve": "retrieve", "evaluate": "evaluate", "end": END})
workflow.add_edge("retrieve", "evaluate")
workflow.add_edge("evaluate", END)
```

**Low-Latency Inference Engine**

A critical architectural pillar is the migration to the Groq API. By
utilizing the Llama-3.3-70b model, the system achieves exceptionally
low-latency responses, a key factor for the "human-like"
conversational speed required for a consultative experience.

**Observability and Audit**

The pipeline is fully integrated with LangSmith. Every execution is
recorded as a trace, allowing for:

- Diagnosis of Retrieval Quality: Pinpointing failures in semantic
  search or metadata filtering.

- Model Performance Monitoring: Tracking latency, token usage, and
  faithfulness ratings.

- Stability Audit: The system underwent a comprehensive audit (2026-03-30) which resolved critical bugs in unstructured exceptions handling, state persistence, and metadata injection risks.

**Results (Relevance and Confidence)**

The system employs a dual-metric calculation to provide users with transparent and reliable feedback:

- **Relevance Score**: A composite metric representing the overall technical quality of the advice. It is calculated as a weighted average: **40% Retrieval Relevance** (similarity from ChromaDB) and **60% Faithfulness Rating** (LLM self-audit of answer adherence to context).

- **Confidence Score (Visa Probability)**: A predictive metric representing the estimated likelihood of the applicant receiving the visa. This is a dedicated 0-100% score generated by the evaluation node based on the user's profile and the retrieved policy requirements.

- **Faithfulness Rating**: A 1-5 rating assessing how strictly the generated answer follows the provided context, used as a sub-component for the Relevance Score.

**Output (Sample Consultation)**

The following transcript demonstrates a successful multi-turn consultation where the agent proactively gathers the 10 informational pillars and provides grounded advice.

**User**: Hi, I'm Vikram, 24, from Delhi. I just got admitted to NYU for their MS in Data Science program. I'm really happy because it's my dream school!

**Officer**: Congratulations on your admission to NYU, Vikram! That's a fantastic achievement. To help you with the next steps for your F-1 visa, could you tell me a bit about how you plan to fund your studies and if you've already looked into the I-20 process?

**User**: My parents are sponsoring me. We have $40,000 in a savings account and I've also secured a sanctioned education loan of $50,000 from SBI. Is that enough for NYU?

**Officer**: Having $90,000 in total funds is a strong start, as NYU typically requires around $80,000-$85,000 for the first year. Since you have a sanctioned loan from SBI, you're in a good position for the I-20 issuance. By the way, do you have any immediate family living in the US, or are you planning to return to India after your graduation?

**User**: I don't have any relatives in the US. My family is in Delhi and we own property here. I plan to return to India to work in an AI startup in Bangalore.

**Officer**: Based on your strong financial profile ($90k total), clear academic purpose at NYU, and established ties to India, your eligibility for an F-1 visa looks very positive. You should now focus on securing your official I-20 from NYU and paying the SEVIS I-901 fee before scheduling your interview.

**Metrics for this session**:
- **Relevance Score**: 92%
- **Confidence Score (Visa Probability)**: 88%
- **Faithfulness Rating**: 5/5

**Conclusion**

The SwiftVisa project successfully implements a sophisticated
LangGraph-based RAG system. By simulating a consultative officer and
transparently identifying requirement gaps across 10 informational pillars, the system provides
grounded, reliable advice. Next phases focus on deployment hardening,
managed database migration, and frontend integration.
