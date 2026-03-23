import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import chromadb
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

import config

load_dotenv()

def load_sites_config():
    """Loads scraping configuration from a JSON file."""
    with open(config.SITES_CONFIG_FILE, 'r') as f:
        return json.load(f)

def fetch_html(url):
    """Fetches HTML content using requests for static pages."""
    response = requests.get(url, headers={"User-Agent": config.DEFAULT_USER_AGENT})
    response.raise_for_status()
    return response.text

def fetch_html_dynamic(url):
    """Fetches HTML content using Playwright for JS-heavy pages."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=config.PLAYWRIGHT_TIMEOUT)
        time.sleep(config.DYNAMIC_WAIT_TIME)
        content = page.content()
        browser.close()
        return content

def extract_main_content(html, country, sites_config):
    """Extracts the primary content area based on site-specific selectors."""
    soup = BeautifulSoup(html, "html.parser")
    
    country_cfg = sites_config["countries"].get(country, sites_config["countries"]["DEFAULT"])
    selectors = country_cfg["selectors"]
    
    main_content = None
    for selector in selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break
            
    if not main_content:
        main_content = soup.body

    # Remove excluded tags
    for tag in sites_config["exclusions"]["tags"]:
        for element in main_content(tag):
            element.decompose()
        
    return str(main_content)

def clean_html_content(html_str, sites_config):
    """Performs link and button cleaning on the extracted HTML."""
    soup = BeautifulSoup(html_str, "html.parser")
    exclusion_phrases = sites_config["exclusions"]["phrases"]
    
    for a in soup.find_all("a"):
        text = a.get_text(strip=True).lower()
        if any(phrase in text for phrase in exclusion_phrases):
            a.decompose()
    
    for button in soup.find_all("button"):
        button.decompose()
        
    return str(soup)

def clean_markdown(markdown_text, sites_config):
    """Post-processing for markdown text to remove UI clutter and excess whitespace."""
    phrases_pattern = '|'.join(sites_config["exclusions"]["phrases"])
    cleaned = re.sub(rf'(?i)({phrases_pattern})', '', markdown_text)
    cleaned = re.sub(r'\[\s*\]\(.*?\)', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

def html_to_markdown(html):
    """Converts cleaned HTML to clean markdown format."""
    return md(html, heading_style="ATX", strip=['a'])

def chunk_text(text):
    """Splits markdown text into chunks for vector indexing."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)

def ingest_url(url, country, visa_category, sites_config):
    """Orchestrates the full ingestion pipeline for a single URL."""
    country_cfg = sites_config["countries"].get(country, sites_config["countries"]["DEFAULT"])
    
    # 1. Fetch
    html = fetch_html_dynamic(url) if country_cfg["use_dynamic"] else fetch_html(url)
    
    # 2. Extract & Clean
    main_html = extract_main_content(html, country, sites_config)
    cleaned_html = clean_html_content(main_html, sites_config)
    
    # 3. Convert & Polish
    markdown_content = html_to_markdown(cleaned_html)
    final_markdown = clean_markdown(markdown_content, sites_config)
    
    # 4. Chunk & Embed
    chunks = chunk_text(final_markdown)
    timestamp = str(time.time())
    
    metadatas = [{
        "source_url": url,
        "country": country,
        "visa_category": visa_category,
        "timestamp": timestamp
    } for _ in chunks]
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    
    vectorstore = Chroma.from_texts(
        texts=chunks,
        embedding=embeddings,
        metadatas=metadatas,
        client=client,
        collection_name=config.COLLECTION_NAME
    )
    return len(chunks)

if __name__ == "__main__":
    sites_cfg = load_sites_config()
    sources = [
        {"url": "https://www.gov.uk/student-visa", "country": "UK", "visa_category": "Student Visa"},
        {"url": "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html/visa", "country": "USA", "visa_category": "Visitor Visa"},
        # ... other sources ...
    ]

    total_chunks = 0
    for source in sources:
        try:
            print(f"Ingesting {source['country']} - {source['visa_category']} from {source['url']}...")
            num_chunks = ingest_url(source['url'], source['country'], source['visa_category'], sites_cfg)
            print(f"-> Successfully ingested {num_chunks} chunks.")
            total_chunks += num_chunks
        except Exception as e:
            print(f"-> Failed to ingest {source['url']}: {e}")

    print(f"\nIngestion entirely complete. {total_chunks} total chunks stored.")
