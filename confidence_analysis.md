# Confidence Score Architecture: Why the New Method is Superior

Our RAG pipeline has transitioned from a naive **Weighted Vector Matching** system to a sophisticated **Two-Stage Semantic Evaluation** system. Here is why the new scoring method is vastly more reliable.

## 1. The "Vector Similarity" Trap (Old Way)
Previously, we used a fixed weighting `(0.5, 0.3, 0.2)` of the top three vector similarities.
- **The Issue**: Vector databases calculate "distance" between embeddings. A distance might be "close" mathematically but "wrong" semantically (e.g., retrieving a policy for "F-1 Student Visa" when the user asked about "M-1 Vocational Visa"). 
- **The Result**: If the top three results were all "somewhat close" but irrelevant, the old system would still report high confidence (e.g., 85%) because the vectors were near each other in hyperspace.

## 2. The "Reranking" Filter (New Way)
We now use **Two-Stage Retrieval**:
1. **Vector Search (Recall)**: Find 10 broad candidates.
2. **Gemini Reranker (Precision)**: A second LLM pass re-evaluates each document individually against the specific query.
- **Thresholding**: We apply a strict **0.7 relevance floor**. If a document doesn't explicitly answer the query, it is discarded. 
- **Superiority**: This ensures that "weak" matches don't dilute the final confidence score.

## 3. Pydantic vs. Regex (Reliability)
- **Old Way**: We used Regex `(\d)` to hunt for a single digit in a long LLM string. If the LLM replied "I give this a 4 out of 5," it worked; if it said "The score is five," the system failed or defaulted.
- **New Way**: We use **LangChain Pydantic Encoders**. The Gemini API is forced to return a structured JSON schema. 
- **Benefits**: This eliminates parsing errors and forces the model to justify its faithfulness rating across specific keys like `is_faithful` and `citations`.

## 4. Holistic Confidence Calculation
The final confidence score is no longer just "Do these documents look like the query?". It is an average of two distinct vectors:
1. **Retrieval Score (Reranked)**: How relevant is the source material?
2. **Faithfulness Score (Reviewed)**: How accurately does the final answer reflect that source material?

| Feature | Naive Vector (Old) | Reranked Pydantic (New) |
| :--- | :--- | :--- |
| **Logic** | Fixed Weights (0.5, 0.3, 0.2) | Semantic Reranking (Cross-Check) |
| **Noise Filtering** | None (Top 3 always pass) | Strict 0.7 Relevance Threshold |
| **Parsing** | Fragile Regex | Strict Pydantic JSON Schema |
| **Accuracy** | High False Positives | Human-in-the-loop Fidelity |

**Conclusion**: The new system is "pessimistic by default," meaning it will only grant a high confidence score if the retrieved document is genuinely authoritative for that specific question.
