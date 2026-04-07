import re
with open('query.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = re.sub(r'def retrieve\(state: State\):.*?(?=\n    factual_question)', 'def retrieve(state: State):\n    from langchain_pinecone import PineconeVectorStore\n    vectorstore = PineconeVectorStore(index_name=\"visa-policies\", embedding=embedding_model, pinecone_api_key=\"pcsk_2fGaSa_8hRhXskiTQ9tcPuWbD6mi3MP5Sd33UGo4fp5LWnW2vZBfD6S1tuyCAsp42fSkzb\")\n', t, flags=re.DOTALL)

with open('query.py', 'w', encoding='utf-8') as f:
    f.write(t)
