# SwiftVisa Codebase Context (Updated 2026-03-30)

## 1. Project Overview & Architecture
* **Purpose:** SwiftVisa is an intelligent, Python-based Retrieval-Augmented Generation (RAG) system acting as a "Senior Visa Consultant". It ingests immigration policy data from official US (USCIS, State Dept) and UK (gov.uk) websites, stores it in a semantic vector database (ChromaDB), and conducts multi-turn consultations to evaluate visa eligibility.
* **Architecture:** State-machine architecture using **LangGraph**. It decouples the offline ingestion pipeline (ETL) from the online inference graph. The system proactively tracks **6 Core Pillars** and **4 Supplementary Fields** before providing grounded advice.

## 2. Tech Stack & Environment
* **Language:** Python 3.12.
* **Orchestration:** LangChain & LangGraph (`langchain-core`, `langgraph`).
* **Inference Engine:** **Groq API** (`llama-3.3-70b-versatile`) for LLM reasoning and evaluation.
* **Embeddings:** **Google Gemini** (`models/gemini-embedding-001`) for vectorization.
* **Vector Database:** **ChromaDB** (Local persistent storage).
* **Data Ingestion:** `playwright` (dynamic rendering), `BeautifulSoup4` (cleaning), `markdownify` (conversion).
* **Observability:** **LangSmith** for full trace telemetry.

## 3. Directory Structure & Module Mapping
* `query.py`: **Core Entry Point**. Defines the LangGraph state machine (agent → retrieve → evaluate), nodes, routing, and the terminal REPL.
* `crawler.py` & `crawler_v2.py`: Ingestion modules. V2 uses Crawlee/Unstructured for higher fidelity. Handles deduplication via MD5 hashing.
* `prompts.py`: Centralized store for system prompts (`INTERVIEW`, `ADVICE`, `FAITHFULNESS_EVAL`).
* `config.py`: Global constants for paths, chunking, and site selectors.
* `sites.json`: Configuration for target domains and CSS selectors for US/UK/Default sites.
* `chroma_db/`: Local persistent vector store.
* `langgraph.json`: LangGraph Studio configuration pointing to `query.py:graph`.

## 4. Core Components & Data Flow
* **State (`TypedDict`):** Tracks `messages`, `extracted_info` (10 pillars), `retrieved_docs`, `relevance_score` (technical quality), `confidence_score` (visa probability), `faithfulness` (1-5), `selected_country`, `visa_type`, and `factual_question`.
* **Agent Node:** 
    * Uses **State-to-Prose compression** to maintain context efficiency.
    * Implements a **robust brace-counting algorithm** for JSON extraction from LLM outputs.
    * Merges extracted info into state without overwriting valid data.
* **Retrieve Node:**
    * Performs broad semantic search (k=20).
    * Applies **Country-aware metadata filtering** (isolating USCIS vs. gov.uk docs).
    * Uses **Gemini-assisted Reranking** with a 0.7 relevance threshold.
* **Evaluate Node:**
    * Generates grounded advice based on retrieved policy context.
    * Conducts a **self-audit faithfulness evaluation** (relevance score vs. context).
    * Calculates **Visa Probability** (0-100%) based on profile strength.
* **Router Logic:**
    * **Core Pillar Check:** Requires all 6 core pillars (Age, Nationality, etc.).
    * **Supplementary Check:** Requires at least 3 of 4 supplementary fields (Education, English, etc.).
    * **Expert-First Trigger:** Immediately routes to retrieval if specific financial or academic data is detected, even if vetting wasn't requested.

## 5. Key Metrics & Scoring
* **Relevance Score:** Composite metric (40% Retrieval Similarity + 60% Faithfulness Rating).
* **Confidence Score:** Predictive 0-100% score representing the likelihood of visa approval.
* **Faithfulness:** 1-5 rating assessing if the LLM's answer is strictly grounded in the provided context.

## 6. Known Gaps & Stability
* **Audit Status:** Last comprehensive audit (2026-03-30) resolved critical bugs in unstructured exceptions handling, unprotected LangGraph state `existing.values` access, Chroma `from_texts` parameter mismatch, metadata `None` injection risks, and forced logical sequencing in prompts (Finances must precede I-20 queries). Useless test/log artifacts were permanently cleaned from the directory.
* **Testing:** Relies on robust local simulation scripts (`simulate.py`, `run_sim.py`) and various dynamic trap tests (`test_adversarial_traps.py`) alongside LangSmith observability.
* **Deployment:** Configured for local execution and LangGraph Studio; production deployment requires managed DB migration (e.g., Pinecone).
