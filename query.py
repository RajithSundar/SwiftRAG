import os
import chromadb
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

os.environ["GOOGLE_API_KEY"] = "AIzaSyCQd6TgI8xmFpNVNVOPjd2_i2v_G3Bvooo"

def get_answer(question):
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    client = chromadb.PersistentClient(path="./chroma_db")
    vectorstore = Chroma(
        client=client,
        collection_name="visa_policies",
        embedding_function=embedding_model
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a professional UK Visa Consultant. 
    Use ONLY the following context to answer the user's question about visa requirements.
    If the provided context does not contain the answer, politely respond with: 
    "I don't have enough specific information in the visa guidelines to answer that."
    
    Context:
    {context}
    
    Question: {question}
    
    Answer:
    """)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain.invoke(question)

if __name__ == "__main__":
    print("Welcome to the SwiftVisa Query Terminal!")
    print("Type 'exit' or 'quit' to stop.\n")
    
    while True:
        user_query = input("Ask a question about the visa (e.g., age, nationality, education level): ")
        if user_query.lower() in ['exit', 'quit']:
            break
            
        if not user_query.strip():
            print("Please enter a valid question or type 'exit' to quit.\n")
            continue
            
        print("\nSearching policies and generating answer...")
        try:
            answer = get_answer(user_query)
            print("-" * 50)
            print(f"Answer: {answer}")
            print("-" * 50 + "\n")
        except Exception as e:
            print(f"An error occurred: {e}\n")
