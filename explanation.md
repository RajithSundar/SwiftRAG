# SwiftVisa: Code & Architecture Explanation

This document provides a plain-English, technical breakdown of how the SwiftVisa RAG (Retrieval-Augmented Generation) pipeline operates under the hood, detailing the technology stack, the specific functions in the code, and how data flows between them.

## 1. The Technology Stack

Before diving into the code, here is a brief overview of the libraries making the magic happen:

*   **`requests`**: A standard Python library used to make HTTP requests (like a web browser) to fetch the raw HTML code of government visa pages.
*   **`BeautifulSoup4` (bs4)**: An HTML parsing library. It takes the messy raw HTML downloaded by `requests` and allows the code to easily find, navigate, and remove specific elements (like `<header>`, `<footer>`, `<script>`, `<nav>`, or specific CSS classes/IDs).
*   **`markdownify`**: Converts the cleaned HTML structure into clean, readable Markdown syntax. LLMs (Large Language Models) understand Markdown exceptionally well compared to raw HTML tags.
*   **LangChain (`langchain_text_splitters`, `langchain_chroma`, `langchain_core`)**: The overarching framework bridging all the components together. 
    *   It provides the exact logic for breaking text into overlapping chunks.
    *   It handles the interface for talking to the Vector Database (Chroma).
    *   It defines the "Chain" that connects the database retrieval directly into the LLM prompt.
*   **`langchain_google_genai`**: LangChain's specific integration package for Google's Gemini models. It handles both the Embeddings (converting text to numbers) and the final Chat Generation.
*   **ChromaDB (`chromadb`)**: A local, open-source Vector Database. It stores the actual text chunks alongside their mathematical "embedding" vectors on your hard drive (in the `./chroma_db` folder), allowing for hyper-fast semantic similarity searches later.

---

## 2. Data Ingestion Phase (`crawler.py`)

This script is responsible for the "ETL" (Extract, Transform, Load) portion of the pipeline.

### Function: `fetch_url_content(url)`
*   **What it does:** Reaches out to the internet to download the webpage.
*   **How it works:** It uses `requests.get(url, headers=...)` to download the page. It specifically mimics a real web browser using a `User-Agent` header to prevent government firewalls from blocking the automated script. It returns the raw HTML string.

### Function: `clean_html_to_markdown(html_content)`
*   **What it does:** Removes internet "noise" and converts the page to readable text.
*   **How it works:** 
    1.  It loads the HTML into `BeautifulSoup(html_content, 'html.parser')`.
    2.  It uses `.decompose()` to permanently delete non-content elements like `<script>`, `<style>`, `<header>`, `<footer>`, and `<nav>`.
    3.  It finds and removes specific noisy CSS classes or IDs commonly found on government sites (e.g., elements containing the words "cookie", "banner", "sidebar", "share").
    4.  Finally, it passes the newly cleaned HTML tree to `markdownify.markdown()`, which strips the remaining HTML tags and returns a pristine Markdown string.

### Function: `chunk_text(markdown_text)`
*   **What it does:** Breaks the massive Markdown document into bite-sized pieces that the LLM can actually digest (LLMs have context window limits).
*   **How it works:** It uses LangChain's `RecursiveCharacterTextSplitter`.
    *   `chunk_size=800`: Each piece of text will be roughly 800 characters long.
    *   `chunk_overlap=80`: The last 80 characters of Chunk A are repeated at the beginning of Chunk B. This prevents sentences or concepts from being abruptly cut in half across chunk boundaries, preserving context.
    *   It returns a list of string chunks.

### Function: `ingest_url(url, country, category)`
*   **What it does:** The orchestrator function that strings the above steps together and saves the result to the database.
*   **How it works:**
    1.  Calls `fetch_url_content`.
    2.  Passes the result to `clean_html_to_markdown`.
    3.  Passes the clean text to `chunk_text`.
    4.  **Metadata Creation:** Creates a Python dictionary for every single chunk containing data like `{"source_url": url, "country": country, "visa_category": category, "timestamp": [current_time]}`. This allows the system to trace exactly where an answer came from later.
    5.  **Database Connection:** Initializes `GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")` and connects to `chromadb.PersistentClient(path="./chroma_db")`.
    6.  **Storage:** Calls `Chroma.from_texts()`. Under the hood, this function sends every chunk to Google's API to be converted into a mathematical vector (embedding), and then saves both the original text, the metadata, and the new vector into the local `visa_policies` collection inside ChromaDB.

---

## 3. Querying & Generation Phase (`query.py`)

This script handles the user interaction, semantic search, and AI reasoning.

### Database Initialization (Global Scope)
*   **What it does:** Wakes up the database and the embedding model without making any new internet requests for data.
*   **How it works:** 
    *   Re-initializes the exact same `GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")` used in the crawler. (If the embedding model isn't identical, the search math will fail).
    *   Connects to the existing `./chroma_db` folder using `Chroma(client=..., embedding_function=...)`.

### The Retrieval Setup
*   **What it does:** Configures how the database should search for answers.
*   **How it works:** Calls `vectorstore.as_retriever(search_kwargs={"k": 3})`. This tells Chroma: *When I give you a question, convert that question into a vector, compare it mathematically to all stored chunks, and return the `k=3` chunks that are the closest match.*

### The LLM Setup
*   **What it does:** Initializes the generative AI that will formulate the final sentence.
*   **How it works:** Initializes `ChatGoogleGenerativeAI(model="models/gemini-2.5-flash", temperature=0.3)`. The `temperature=0.3` setting is crucial; it forces the AI to be highly deterministic and factual, reducing "hallucinations" (invented facts), which is vital for legal/visa advice.

### The Prompt Template
*   **What it does:** Gives the AI its persona and strict rules.
*   **How it works:** `ChatPromptTemplate.from_template(...)` creates a blueprint. It instructs the AI: "You are a professional UK Visa Consultant. Use ONLY the following context...". It contains two empty placeholders: `{context}` and `{question}`.

### Function: `get_answer(question)`
*   **What it does:** The core RAG execution function.
*   **How it works:** It uses LangChain Expression Language (LCEL) to create a pipeline (the `chain` variable):
    1.  `{"context": retriever | format_docs, "question": RunnablePassthrough()}`
        *   Takes the user's string `question`.
        *   Passes it to the `retriever`. The retriever searches the database and returns 3 raw Document objects.
        *   Pipes those 3 documents into the internal `format_docs` helper function, which simply extracts the raw text from the objects and joins them together with double-newlines.
        *   Packages this giant block of text into the `{context}` variable, and keeps the original question as `{question}`.
    2.  `| prompt`: Injects the `{context}` and `{question}` into the Prompt Template discussed earlier.
    3.  `| llm`: Sends the fully populated prompt to `gemini-2.5-flash` over the internet.
    4.  `| StrOutputParser()`: Takes the complex AI response packet and extracts just the plain text string answer.
    5.  It simply calls `return chain.invoke(question)` to trigger this entire sequence.

### The Interactive Loop (`if __name__ == "__main__":`)
*   **What it does:** Provides the terminal UI for the user.
*   **How it works:** An infinite `while True:` loop uses Python's `input()` to pause and wait for the user to type a question. 
    *   If the user types 'exit' or 'quit', `break` exits the loop.
    *   If the user types an empty string, `continue` resets the loop and asks again.
    *   Otherwise, it passes the string to `get_answer(user_query)`, prints the result, and loops back to ask for the next question.
