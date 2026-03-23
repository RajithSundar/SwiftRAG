# 1. Project Overview & Architecture
* **Purpose:** SwiftVisa is an intelligent, Python-based Retrieval-Augmented Generation (RAG) system that ingests immigration policy data from official government websites (e.g., US State Dept., UK Gov), stores it in a semantic vector database, and serves as an interactive conversational "Senior Visa Consultant". It proactively tracks 4 informational pillars (Age, Nationality, Financials, Purpose) from user queries via multi-turn conversation before evaluating eligibility.
* **Architecture:** Multi-turn RAG state-machine architecture using LangGraph. The system decouples the offline Data Ingestion processing pipeline (ETL) from the online Query/Inference execution graph.

## 2. Tech Stack & Environment
* **Language:** Python (Configured for `3.12` in `langgraph.json`, though documentation (`workflow.md`) notes compatibility configurations up to 3.14+).
* **Core Libraries & Frameworks:** 
  * **Orchestration:** LangChain & LangGraph (`langchain-core==1.2.15`, `langgraph-cli[inmem]`).
  * **Data Ingestion & Scraping:** `requests`, `BeautifulSoup4` (`soupsieve==2.8.3`), `playwright==1.58.0` (for dynamic JS rendering), `markdownify==1.2.2`.
  * **Database:** ChromaDB (`chromadb==1.5.1`) - Configured as a local, persistent vector store.
  * **Embeddings:** Google Gemini (`models/gemini-embedding-001`) via `langchain-google-genai==4.2.1`.
  * **LLM / Inference:** Groq API (`llama-3.3-70b-versatile`) via `langchain-groq`. (Architectural shift effectively substituted `gemini-2.5-flash` with Groq).
  * **Observability:** LangSmith (`langsmith==0.7.6`).
* **Environment Configuration:** Project tracks dependencies sequentially inside `requirements.txt` with deployment facilitated through an active virtual environment (`venv/`).

## 3. Directory Structure & Module Mapping
* `d:\InfosysVirtual\`
  * `crawler.py`: The data ingestion module (handles web scraping, HTML cleaning, markdown conversion, semantic chunking, and embedding to Chroma).
  * `query.py`: The main RAG pipeline execution script and graph entry point. Defines LangGraph states, nodes, and routing for inference plus serves an interactive terminal REPL.
  * `langgraph_query.py`: A secondary/legacy RAG script mirroring `query.py` logic but with slight differences (e.g., relying purely on a generic `JsonOutputParser`).
  * `debug_db.py`: Utility ad-hoc script to inspect raw attributes of the ChromaDB internal collection.
  * `chroma_db/`: Persistent local directory hosting the vector embeddings.
  * `requirements.txt`: Master list of pip dependencies.
  * `langgraph.json`: Configuration mapping for LangGraph Studio execution, targeting `./query.py:graph` as the root entry point.
  * `.env`, `.gitignore`: Secrets configuration and source control ignores.
  * `venv/`, `__pycache__`, `.langgraph_api/`: Ignored standard environment modules and cached objects.
  * Documentation (`workflow.md`, `meeting_prep.md`, `implementation_details.md`, `migration_guide.md`, `explanation.md`, `langgraph_explained.md`): Highly dense internal documentation concerning AI behavior choices, LangSmith integration, and system migration phases.

## 4. Core Components & Data Flow
* **Entry Points:** 
  * **Offline Ingestion:** `crawler.py` (Run interactively via `python crawler.py`).
  * **Online Inference:** `query.py`, or launched visually via `langgraph dev`.
* **Critical Components (`query.py` LangGraph Logic):**
  * `State (TypedDict)`: Global dictionary traversing nodes holding `messages`, `extracted_info`, `retrieved_docs`, `confidence_score`, `faithfulness`, `selected_country`, `visa_type`.
  * `agent` node: Connects to Groq Llama 3 to analyze conversation history and extract missing pillars into a rigid JSON format.
  * `router` conditional edge: Inspects `State`. If any of the 4 pillars (Age, Nationality, Financials, Purpose) are missing, execution hits `END` and asks the user for the lacking info (forcing multi-turn conversation). If 4 pillars are fully populated, routes to `retrieve`.
  * `retrieve` node: Queries the local Chroma DB taking user input, pulls the `k=3` most relevant Markdown chunks filtered by country, and yields an initial retrieval base score via strict rank weighting [0.5, 0.3, 0.2].
  * `evaluate` node: Composes a personalized, grounded answer relying explicitly upon the previously retrieved contexts. Follows up with a self-evaluating chain analyzing its own answer against the context to deliver a 1-5 faithfulness rating, normalizing directly to the final `confidence_score`.
* **Data Flow Step-by-Step:**
  1. Administrative user configures URLs in `crawler.py`.
  2. Scripts fetch URLs (Playwright dynamically traces DOM for JS frameworks), scrubs generic buttons using BeautifulSoup, and converts syntax into MD format using Markdownify.
  3. Text splits into overlapping chunks via `RecursiveCharacterTextSplitter`, embeds against Google GenAI, and sinks to `chroma_db`.
  4. End-client starts `query.py`. Provides baseline parameters (Country, Visa).
  5. The client submits varying sentence fragments. The Graph iterates `query.py:agent` iteratively checking for 4 info pillars, firing checkpointer states continuously backward to the user.
  6. Upon fulfilling all data criteria, the retriever locates chunks, and Llama 3 outputs a grounded advice response appending computed faithfulness confidences.

## 5. API Contracts & Interfaces
* **Internal Application API:**
  * `run_visa_consultation(user_input: str, thread_id: str, country: str, visa: str)` in `query.py`: Interfaces with the compiled `_local_graph.stream`. Maintains thread persistence across calls relying on `MemorySaver`. Expects to return structured data `{"answer": str, "confidence": int, "info": dict, "sources": list}`.
* **External API Integration Boundaries:**
  * **Google Generative AI API**: Bound exclusively for Vectorization requests (`models/gemini-embedding-001`).
  * **Groq SDK API**: Bound strictly for LLM conversational and evaluation invocations (`llama-3.3-70b-versatile`).
  * **LangSmith Observability API**: Used seamlessly inside standard LangChain Expression chains tracking intermediate token logs.

## 6. Environment & Configuration
* **System Environment (`.env`):**
  * `GOOGLE_API_KEY`: Authentication for Gemini embeddings.
  * `GROQ_API_KEY`: Authentication for Llama 3 LLM operations.
  * `LANGCHAIN_TRACING_V2` (Set `true`), `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`: Enable telemetry logging to LangSmith cloud servers.
* **Configuration Specifications:** 
  * `langgraph.json`: Signals root targets via `{"graphs": {"root": "./query.py:graph"}, "env": ".env", "python_version": "3.12"}` allowing native execution inside LangGraph Studio without manual state configuration.
  * `chromadb.config.Settings`: Hardcoded in scripts with properties `allow_reset=True, anonymized_telemetry=False`.

## 7. Known Gaps & Ambiguities
* **Dual Identical Pipeline Scripts:** `query.py` and `langgraph_query.py` serve nearly identical roles inside the system. `query.py` implements regex extraction (`re.search(r'\{[\s\S]*\}', raw_output)`) for its JSON payload whereas `langgraph_query.py` trusts `JsonOutputParser()`. Because `langgraph.json` isolates `query.py:graph` as the official binding, `langgraph_query.py` appears to be unused legacy/backup logic and exists ambiguously.
* **External/Missing Implementations:** 
  * The codebase documentation (`workflow.md`) references purging `test_*.py` items. There are definitively zero automated tests, fixtures, or unit testing structures anywhere natively visible in the module mapping. 
  * `implementation_details.md` cites a direct, manual hack to standard libraries mapping into `venv/Lib/site-packages/chromadb/config.py` altering the `Config` Pydantic models to accept `extra = "ignore"`. This change is not programmatic and relies on obscure, undocumented manual client configuration beyond standard `pip install`.
* **Future Work ("TODOs" found inside documentation):**
  * Migration requests to translate the Terminal UI into Streamlit/Next.js are noted.
  * Notes citing intentions of migrating from local `ChromaDB` towards managed remote databases (Pinecone or Managed Chroma).
  * Cron job tasks remain un-started or un-tracked.
