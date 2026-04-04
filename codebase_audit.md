# Comprehensive Codebase Audit & Resolution Report

**Date:** March 30, 2026  
**Status:** **RESOLVED**  

This document logs the core issues discovered during the definitive codebase inspection of the backend and traces the resolutions successfully implemented. 

## 1. Safety and Stability (CRITICAL)

### **Null Pointer Access in Graph State**
*   **File:** query.py
*   **Issue:** The setup checking existing.values for resuming graph states was completely unprotected. Without a prior execution, LangGraph's API returns existing without valid inner data, sparking an immediate AttributeError: 'NoneType' object has no attribute 'values', effectively crashing any first-time simulation instantly.
*   **Resolution:** Tightened state condition check: if existing and existing.values and "extracted_info" in existing.values: ensuring graceful dictionary population and bypassing the crash risk loop.

### **Uncaught Exception Handling & Hard Crashes**
*   **Locations:** query.py (API fallback)
*   **Issue:** The environment relied solely on a logic loop targeting Error 429 (Rate Limits). Any other HTTP exception bypassed the fallback block and triggered a raw raise. Up the call chain, run_visa_consultation had no global safety net.
*   **Resolution:** Modified exception hooks inside query.py to default gracefully. Wrapped graph.invoke in an explicit try-except that intercepts system-breaking failures and cleanly returns standard UI apologies.

## 2. API Structure & Logical Consistency (HIGH)

### **Parameter Mislabeling**
*   **File:** crawler.py
*   **Issue:** The chromadb integration used the wrong from_texts constructor parameter, calling embedding instead of the expected embedding_function.
*   **Resolution:** Adjusted the argument mapping to strictly respect the module parameter scheme (embedding_function=embeddings).

### **Dataset Integrity Risks [None] injection**
*   **File:** query.py
*   **Issue:** Compiling final chunks inside metadata.get() for semantic URLs failed to filter out untruthful outputs, injecting bare None tokens into sources lists.
*   **Resolution:** Wrapped the extraction logic (if doc.metadata and doc.metadata.get("source_url")), returning strict string-typed target lists.

### **System Prompt Hallucinations (Agent Logic Jump)**
*   **File:** prompts.py
*   **Issue:** The agent requests I-20 evidence without confirming Finances causing sequence discontinuity.
*   **Resolution:** Hardcoded chronological logic directly into the principal prompt dictating that agents must ALWAYS ask about funding/finances BEFORE I-20s.

## 3. Redundancy Processing (LOW)

### **Duplicated Variable Reassignment**
*   **File:** query.py
*   **Issue:** Reassignment of info = state.get("extracted_info", {}) appeared back-to-back inside the evaluation routers.
*   **Resolution:** Deduplicated code loops prioritizing upstream variable cache utilization.

---
**Sign-off:** All components tested clean and syntactic integrity successfully compiled post-modification.
