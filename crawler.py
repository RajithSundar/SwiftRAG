import os
import re
import time
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import chromadb

os.environ["GOOGLE_API_KEY"] = "AIzaSyCQd6TgI8xmFpNVNVOPjd2_i2v_G3Bvooo"

def fetch_html(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.text

def extract_main_content(html):
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["header", "footer", "aside", "nav", "style", "script", "noscript", "meta", "link", "svg"]):
        element.decompose()
    
    main_content = soup.find("main") or soup.find("article") or soup.find("div", id="content") or soup.body
    if not main_content:
        return ""
    return str(main_content)

def clean_html_content(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for a in soup.find_all("a"):
        text = a.get_text(strip=True).lower()
        if any(phrase in text for phrase in ["apply now", "share this page", "cookie policy", "accept cookies", "read more", "cookies"]):
            a.decompose()
    
    for button in soup.find_all("button"):
        button.decompose()
    return str(soup)

def clean_markdown(markdown_text):
    cleaned = re.sub(r'(?i)(apply now|share this page|cookie policy|accept cookies|read more|cookies)', '', markdown_text)
    cleaned = re.sub(r'\[\s*\]\(.*?\)', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def html_to_markdown(html):
    return md(html, heading_style="ATX", strip=['a'])

def chunk_text(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)

def ingest_url(url, country, visa_category, persist_directory="./chroma_db", collection_name="visa_policies"):
    html = fetch_html(url)
    main_html = extract_main_content(html)
    cleaned_html = clean_html_content(main_html)
    markdown_content = html_to_markdown(cleaned_html)
    final_markdown = clean_markdown(markdown_content)
    
    chunks = chunk_text(final_markdown)
    timestamp = str(time.time())
    
    metadatas = [{
        "source_url": url,
        "country": country,
        "visa_category": visa_category,
        "timestamp": timestamp
    } for _ in chunks]
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    client = chromadb.PersistentClient(path=persist_directory)
    
    vectorstore = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        metadatas=metadatas,
        client=client,
        collection_name=collection_name
    )
    return len(chunks)

if __name__ == "__main__":
    test_url = "https://www.gov.uk/student-visa"
    num_chunks = ingest_url(test_url, "UK", "Student Visa")
    print(f"Ingestion complete. {num_chunks} chunks stored.")
