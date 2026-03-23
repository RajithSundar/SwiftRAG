import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("visa_policies")

results = collection.get(where={"country": "USA"}, include=["documents", "metadatas"])

print(f"Total USA documents: {len(results['documents'])}")
for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    print(f"\n--- Document {i+1} ---")
    print(f"Category: {meta.get('visa_category', 'N/A')}")
    print(f"Content ({len(doc)} chars): {doc[:200]}...")
