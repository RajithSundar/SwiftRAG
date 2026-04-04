**Technical Project Report: SwiftVisa - AI-Powered Visa Eligibility
Screening Agent**

This report details the \"SwiftVisa\" project, an advanced application
of an LLM-powered Retrieval-Augmented Generation (RAG) system
orchestrated using LangGraph. The system is engineered to leverage
natural language reasoning and state-machine transitions for the
comprehensive evaluation of US and UK visa eligibility. It is designed
to provide consultative, policy-grounded guidance, delivering
transparent and explainable eligibility assessments.

**Introduction**

The SwiftVisa project addresses the limitations of conventional visa
screening tools by shifting from rigid filtering to a conversational,
state-based interaction. The system proactively identifies and tracks 6
Informational Pillars---Age, Nationality, Financials, Purpose, Target
Country, and Visa Category. This methodology facilitates a nuanced user
experience, simulating the diagnostic process of an experienced visa
officer through multi-turn dialogue.

**Objectives**

The core objectives of the SwiftVisa system development are:

- Grounding and Transparency: Provide advice strictly grounded in
  official government policy documents from USCIS and gov.uk.

- Non-Hallucinated Output: Mitigate LLM hallucinations via a robust RAG
  pipeline and self-audit evaluation within the graph.

- Explainable Reasoning: Link eligibility assessments explicitly to
  relevant policy text.

- History-Aware Conversation: Deliver natural reactions and logical
  bridging between information gathering steps.

**Requirements**

The technical stack was selected for performance, modularity, and
state-management capabilities:

- Core Language: Python

- Orchestration Framework: LangGraph (State-machine architecture)

- Inference Engine: Groq API (Utilizing the Llama-3.3-70b-versatile
  model)

- Vector Database: ChromaDB

- Embeddings Model: Google Generative AI Embeddings

- Observability Platform: LangSmith

**Methodology**

The system is built upon a dual-layer RAG architecture managed by a
LangGraph state machine:

**History-Aware Agent Node**

The agent node uses history-aware reactions to prevent robotic
transitions. It acknowledges specific user details before bridging to
missing information.

def agent(state: State):

\# System prompt enforces conversational rules (No lists, 3rd person,
etc.)

prompt = ChatPromptTemplate.from_messages(\[

(\"system\", system_prompt),

MessagesPlaceholder(variable_name=\"messages\"),

\])

raw_output = (prompt \| llm \| StrOutputParser()).invoke({\"messages\":
state\[\"messages\"\]})

\# Robustly extract JSON and conversational response

json_match = re.search(r\'\\{\\\[\\s\\S\]\*\\}\', raw_output)

result = json.loads(json_match.group()) if json_match else {}

response = raw_output\[:json_match.start()\].strip() if json_match else
raw_output

return {

\"extracted_info\": result.get(\"extracted_info\", {}),

\"messages\": \[AIMessage(content=response)\],

\"vetting_requested\": result.get(\"vetting_requested\", False)

}

**Document Retrieval Logic**

The retrieve node encapsulates the semantic search and confidence
calculation.

def retrieve(state: State):

\# Metadata filtering ensures cross-policy isolation

docs_and_scores = vectorstore.similarity_search_with_relevance_scores(

query, k=3, filter={\"country\": state.get(\"selected_country\",
\"UK\")}

)

\# Weighted confidence scoring based on distance ranks

weights = \[0.5, 0.3, 0.2\]

scores = \[d\[1\] for d in docs_and_scores\]

retrieval_score = (sum(s \* w for s, w in zip(scores, weights)) /
sum(weights)) \* 100

return {\"retrieved_docs\": \[d\[0\] for d in docs_and_scores\],
\"confidence_score\": int(retrieval_score)}

**LangGraph State Machine Layout**

The orchestration is defined as a single, declarative StateGraph,
separating extraction from advice generation.

\# Create the state machine

workflow = StateGraph(State)

workflow.add_node(\"agent\", agent)

workflow.add_node(\"retrieve\", retrieve)

workflow.add_node(\"evaluate\", evaluate)

\# Define transitions and routing

workflow.add_edge(START, \"agent\")

workflow.add_conditional_edges(\"agent\", router, {\"retrieve\":
\"retrieve\", \"end\": END})

workflow.add_edge(\"retrieve\", \"evaluate\")

workflow.add_edge(\"evaluate\", END)

\# Compile with conditional persistence check

graph = workflow.compile(checkpointer=\_memory if not
os.getenv(\"LANGGRAPH_API_URL\") else None)

**Low-Latency Inference Engine**

A critical architectural pillar is the migration to the Groq API. By
utilizing the Llama-3.3-70b model, the system achieves exceptionally
low-latency responses, a key factor for the \"human-like\"
conversational speed required for a consultative experience.

**Observability and Audit**

The pipeline is fully integrated with LangSmith. Every execution is
recorded as a trace, allowing for:

- Diagnosis of Retrieval Quality: Pinpointing failures in semantic
  search or metadata filtering.

- Model Performance Monitoring: Tracking latency, token usage, and
  faithfulness ratings.

**Results (Confidence Scoring)**

The system employs a hybrid calculation for user trust:

- Retrieval Score: A weighted average of similarity distances returned
  by ChromaDB.

- Faithfulness Rating: A self-audit rating (1-5) assessing the degree to
  which the LLM\'s final answer adheres to the retrieved context.

**Conclusion**

The SwiftVisa project successfully implements a sophisticated
LangGraph-based RAG system. By simulating a consultative officer and
transparently identifying requirement gaps, the system provides
grounded, reliable advice. Next phases focus on deployment hardening,
managed database migration, and frontend integration.
