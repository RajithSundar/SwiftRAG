# SwiftVisa: Complete Pipeline & Data Flow Architecture

This document maps out the comprehensive end-to-end data flow and logical architecture of the SwiftVisa ecosystem. It covers how data is sourced, how user queries are processed, and the distinct functions mapping the LLM processing pipeline.

---

## 1. The Offline Pipeline: Data Ingestion (ETL)
Before the agent can answer queries, the domain knowledge must be seeded into the local environment.

**Modules:** `crawler.py`, `crawler_v2.py`

### **Process Flow:**
1. **Target Identification:** The crawler reads `sites.json` and internal arrays to target specific visa policy URLs for the US (state.gov, uscis.gov) and the UK (gov.uk).
2. **Extraction:**
   - **V1 (`crawler.py`):** Uses `playwright` for dynamic page rendering and `BeautifulSoup` to target specific HTML DOM components, removing headers/footers to isolate the main policy text. The HTML is converted to Markdown using `markdownify`.
   - **V2 (`crawler_v2.py`):** Utilizes `crawlee` alongside `unstructured` to scrape tables, nested tags, and advanced elements simultaneously, injecting them into LangChain document formats.
3. **Chunking & Hashing:** The document is split into smaller, semantically manageable chunks using `RecursiveCharacterTextSplitter` (e.g., `CHUNK_SIZE = 800`, `CHUNK_OVERLAP = 80`). An `MD5` hash is computed on `url+chunk` to create a deterministic ID, effectively preventing duplicate data upon reingestion (upserting).
4. **Vectorization & Storage:** Chunks and their descriptive metadata (`source_url`, `country`, `visa_category`) are passed to **Google Generative AI Embeddings** (`models/gemini-embedding-001`). The resulting numerical vectors are securely saved to the persistent local database **ChromaDB**.

---

## 2. The Online Pipeline: Graph State Machine
When a user begins a chat session, execution hands over to the LangGraph state machine inside `query.py`. This system behaves like a persistent "while-loop" with built-in memory checkpoints.

### **The Canonical `State` Object**
Data flows through the nodes using a shared `TypedDict` initialized per user thread (`thread_id`).
* `messages`: The conversational memory between the human and the AI.
* `extracted_info`: A dictionary aggregating the 10 data "Pillars" the agent discovers.
* `retrieved_docs`: The exact context chunks dragged from ChromaDB.
* `relevance_score` & `confidence_score`: Operational viability metrics.
* `faithfulness`: A 1-5 rating representing hallucination safety.
* `factual_question`: The isolated, pure intent of the user stripped of conversational fluff.

### **Execution Gateway: `run_visa_consultation()`**
This is the root API method called by all tests and scripts.
1. Accepts `user_input` and checks memory for an `existing.values` state using LangGraph.
2. If empty, correctly initializes a fresh skeleton state to prevent `NullPointer` exceptions.
3. Overwrites the immediate human message queue and invokes the graph execution.

---

## 3. Node-by-Node Pipeline Logic

The system is cyclical. A user speaks -> `agent` attempts extraction -> `router` dictates whether to dig for more info (`END`) or process final advice (`retrieve` -> `evaluate`). 

### **Node 1: `agent(state)` (Information Gathering)**
**Objective:** Maintain conversation, ask missing pillar questions smoothly, and extract JSON metadata in parallel.
* **LLM Call:** Feeds the system instructions (`prompts.py`) + chat history to `Groq (llama-3.3-70b-versatile)`.
* **String Parsing (`find_json_boundary`):** AI models often pollute JSON outputs with conversational text. The agent implements a meticulous *manual brace-counting algorithm* capturing dynamic `{"extracted_info": ...}` dictionaries amid markdown prose.
* **State Updates:** Discovered pillars are parsed. If a new pillar is valid (passes the `is_pillar_missing()` validation utility), it gets merged onto older pillars.

### **Intersection: `router(state)` (The Decision Engine)**
**Objective:** Decide if the session has enough profile strength to issue a formal visa verdict.
1. Checks the **6 Core Pillars** (`age`, `nationality`, `financials`, `purpose`, `target_country`, `visa_category`).
2. Checks the **4 Supplementary Pillars** (`education`, `employment`, `english_proficiency`, `ties_to_home_country`). Needs at least 3.
3. **Expert-First Bypass:** If the agent isolates hardcore data constraints (e.g., detecting keywords like `$` or `stanford`), it immediately short-circuits the pillars check and violently routes directly to `retrieve` to ensure it doesn't give flawed off-the-cuff financial advice.
4. **Outcome:** Routes to `retrieve` if ready, or `END` (kicking the conversation back to the human for more info).

### **Node 2: `retrieve(state)` (Database Search & Reranking)**
**Objective:** Extract truth based on the context.
* Uses the specific `factual_question` (or the last message) generated back at the `agent` node.
* **Metadata Toggling:** Applies country-aware routing filters based on the `target_country` variable. If the user wants to go to the US, `goverment.uk` domains are completely stripped from the query vector space to prevent cross-contamination.
* **Top-K Search:** Extracts `K=20` initial chunks.
* **Reranking:** Matches chunk relevance specifically against the query using zero-shot classification loops and a strict `0.7` inclusion threshold. Keeps the highest matching 3 chunks.

### **Node 3: `evaluate(state)` (Consultation & Auditing)**
**Objective:** Deliver the final grounded verdict.
* Injects the Top-3 verified documents into `ADVICE_SYSTEM_PROMPT`.
* Generates a "strict rule" response enforcing sequences (e.g., verifying finances before allowing I-20 application progression) and screening for Adversarial Profile Traps (Anchor Relatives, Pre-arranged employment violations, etc.).
* **Generates Output:** Extracts a `1-100% Probability Score`.
* **Self-Reflection Pipeline (`FAITHFULNESS_EVAL_PROMPT`):** Uses the LLM as an internal judge to grade its own just-generated response against the literal document chunks on a 1-5 scale. If the result hallucinates outside the bounds of the provided PDFs, the faithfulness score crashes, marking the generation as unstable.

### **Node 4: `END`**
Returns the modified dictionary to `run_visa_consultation()`, un-boxing the `answer`, `relevance`, `confidence`, and cleaned `sources` strings up to any connected UI or test integration script.

---

## 4. Current Directory Ecosystem
Following the v2.0 restructure, operations are strictly cordoned off:
1. **`/Root`** - The primary API endpoint instances (`query.py`, `run_sim.py`, `crawler.py`), global states (`config.py`), and system instructions (`prompts.py`).
2. **`/tests/`** - Execution endpoints (`test_*.py`) forcing the inference engine through adversarial loops and trapping validations to verify that the LLM doesn't collapse under edge-case profiles.
3. **`/simulations/`** - Chat harnesses (`simulate_chat_dynamic.py`) using persona injections enabling LLMs to talk to the Backend agent automatically, stress-testing multi-turn graph states.
4. **`/scripts/`** - Background operational tools for reading DB outputs, ingesting special rulesides, and handling non-inference workloads.