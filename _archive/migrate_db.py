import chromadb
from chromadb.config import Settings
import config
from langchain_chroma import Chroma
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
import time

print("Loading local embeddings...")
embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR, settings=Settings(allow_reset=True, anonymized_telemetry=False))
local_vectorstore = Chroma(client=client, collection_name=config.COLLECTION_NAME, embedding_function=embedding_model)

local_data = client.get_collection(config.COLLECTION_NAME).get(include=["documents", "metadatas"])

print(f"Found {len(local_data['documents'])} documents in local ChromaDB.")

# Target Pinecone setup
pc = Pinecone(api_key="pcsk_2fGaSa_8hRhXskiTQ9tcPuWbD6mi3MP5Sd33UGo4fp5LWnW2vZBfD6S1tuyCAsp42fSkzb")

index_name = "visa-policies"

if index_name not in pc.list_indexes().names():
    print(f"Creating Pinecone index '{index_name}'...")
    pc.create_index(
        name=index_name,
        dimension=768, # Gemini embedding dimension
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
    time.sleep(5) # wait for index init

target_vectorstore = PineconeVectorStore(index_name=index_name, embedding=embedding_model, pinecone_api_key="pcsk_2fGaSa_8hRhXskiTQ9tcPuWbD6mi3MP5Sd33UGo4fp5LWnW2vZBfD6S1tuyCAsp42fSkzb")

print("Migrating chunks to Pinecone in batches...")

from langchain_core.documents import Document
docs = []
for text, meta in zip(local_data['documents'], local_data['metadatas']):
    if text:
        docs.append(Document(page_content=text, metadata=meta))

# Upload in batches
batch_size = 100
for i in range(0, len(docs), batch_size):
    batch = docs[i:i+batch_size]
    print(f"Uploading batch {i} to {i+len(batch)}...")
    target_vectorstore.add_documents(batch)

print("Migration fully complete!")
