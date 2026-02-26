# SwiftVisa: RAG Pipeline Workflow

This document outlines the architecture, setup, and execution workflow for the **SwiftVisa** immigration policy RAG (Retrieval-Augmented Generation) pipeline.

## 1. Project Overview
SwiftVisa is a Python-based intelligent query system designed to ingest immigration policy data from official government websites, store it in a local vector database, and provide accurate, context-aware answers to user queries using Google's Gemini LLMs.

---

## 2. Technology Stack
*   **Language:** Python 3.14+
*   **Vector Database:** ChromaDB (Local Persistent)
*   **Embeddings Model:** Google Gemini (`models/gemini-embedding-001`)
*   **LLM Generator:** Google Gemini (`models/gemini-2.5-flash`)
*   **Framework:** LangChain
*   **Web Scraping & Processing:** `requests`, `BeautifulSoup4`, `markdownify`

---

## 3. Environment & Configuration

### Prerequisites
1.  Python Virtual Environment installed and activated (`.\venv\Scripts\Activate.ps1`).
2.  Google Gemini API Key generated from Google AI Studio.

### Required Dependencies
```bash
pip install chromadb langchain langchain-google-genai langchain-chroma langchain-text-splitters requests beautifulsoup4 markdownify pydantic pydantic-settings
```

### Python 3.14 Compatibility Patch
Due to Python 3.14 deprecating earlier Pydantic configurations used by ChromaDB, raw `chromadb` installations require patching their `config.py` file to replace v1 imports (`validator`, `BaseSettings`) with Pydantic v2 compliant counterparts (`field_validator` via `pydantic_settings`). 

---

## 4. Pipeline Execution Workflow

The system is separated into two distinct stages: **Ingestion** and **Retrieval/Generation**.

### Phase 1: Data Ingestion (`crawler.py`)
This script handles the extraction, cleaning, chunking, embedding, and storage of policy documents.

1.  **Extraction:** Uses the `requests` library to fetch raw HTML from target government visa policy URLs.
2.  **Cleaning (Noise Reduction):** 
    *   Uses `BeautifulSoup` to strip out irrelevant web elements (nav bars, footers, scripts, sidebars, inline CSS).
    *   Converts the cleaned HTML tree into clean Markdown format using `markdownify` for superior LLM comprehension.
3.  **Smart Chunking:**
    *   Passes the Markdown text through LangChain's `RecursiveCharacterTextSplitter`.
    *   Parameters are optimized for semantic context: `chunk_size = 800`, `chunk_overlap = 80`.
4.  **Embedding & Storage:**
    *   Uses `models/gemini-embedding-001` to convert text chunks into vector embeddings.
    *   Stores the embeddings alongside relevant metadata (URL source, country, visa category, ingestion timestamp) into a persistent local `Chroma` vector store located in the `./chroma_db` directory.

**Execution:**
```powershell
.\venv\Scripts\python.exe crawler.py
```

---

### Phase 2: Querying & Generation (`query.py`)
This script manages the interactive terminal where users can ask questions about the ingested visa policies.

1.  **Database Connection:** Connects to the local `./chroma_db` database and initializes the same `models/gemini-embedding-001` model used during ingestion.
2.  **User Input Handling:** Provides an interactive loop taking user queries (e.g., "age 20, indian, degree"). Captures and handles empty inputs gracefully to prevent embedding errors.
3.  **Context Retrieval (RAG):**
    *   Converts the user's query into a vector.
    *   Performs a similarity search against the ChromaDB, returning the top `k=3` most relevant policy chunks.
4.  **Answer Generation:**
    *   Injects the retrieved chunks into a specific `ChatPromptTemplate` instructing the LLM to act as a professional UK Visa Consultant.
    *   Passes the prompt and context to the `gemini-2.5-flash` model.
    *   The model evaluates the context and either provides a direct answer or politely declines if the necessary information isn't present in the retrieved chunks.

**Execution:**
```powershell
.\venv\Scripts\python.exe query.py
```
