import os
import time
import asyncio
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from unstructured.partition.html import partition_html
from unstructured.chunking.title import chunk_by_title
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
import chromadb
from dotenv import load_dotenv

import config

load_dotenv()

# Initialize Vectorstore
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
vectorstore = Chroma(
    embedding_function=embeddings,
    client=client,
    collection_name=config.COLLECTION_NAME
)

async def main():
    # Crawlee Playwright configuration
    crawler = PlaywrightCrawler(
        # High depth for comprehensive US and UK visa content ingestion
        max_requests_per_crawl=500,
        headless=True
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        url = context.request.url
        context.log.info(f"Processing {url}")

        # Wait for dynamic elements to settle
        try:
            await context.page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            context.log.warning(f"Network idle timeout for {url}, proceeding anyway. {e}")
        
        # Extract HTML
        html_content = await context.page.content()

        # Recursive Enqueueing: Crawlee automatically finds links and adds them
        # BUG FIX: Tighten gov.uk glob to visa-specific paths only
        await context.enqueue_links(
            globs=[
                "https://www.uscis.gov/policy-manual/volume-2-**",
                "https://travel.state.gov/content/travel/en/us-visas/**",
                "https://fam.state.gov/FAM/**",
                "https://studyinthestates.dhs.gov/**",
                "https://www.gov.uk/student-visa/**",
                "https://www.gov.uk/skilled-worker-visa/**",
                "https://www.gov.uk/standard-visitor/**",
                "https://www.gov.uk/entering-staying-uk/visas-entry-clearance/**",
                "https://www.gov.uk/guidance/immigration-rules/**",
                "https://www.gov.uk/government/collections/student-route-caseworker-guidance**",
                "https://www.gov.uk/government/publications/skilled-worker-visa-caseworker-guidance**"
            ],
            strategy="same-hostname"
        )

        try:
            # High-Fidelity Extraction (preserves tables as HTML inner strings)
            elements = partition_html(text=html_content, strategy="hi_res")
            
            # Smaller, focused chunks with overlap for better reranking precision
            chunks = chunk_by_title(elements, max_characters=500, overlap=50)

            documents = []
            for chunk in chunks:
                # If it's a Table, use text_as_html to keep tabular structure intact
                if hasattr(chunk, 'category') and chunk.category == 'Table' and hasattr(chunk.metadata, 'text_as_html') and chunk.metadata.text_as_html:
                    content = chunk.metadata.text_as_html
                else:
                    content = chunk.text
                
                # Assemble metadata
                # BUG FIX: Add country/visa_category for consistency with V1
                country = "USA" if any(domain in url for domain in ["uscis.gov", "state.gov", "dhs.gov"]) else "UK" if "gov.uk" in url else "DEFAULT"
                
                # Dynamically guess the visa category from the URL slug
                visa_category = "General"
                if "student-visa" in url or "part-f" in url:
                    visa_category = "Student Visa"
                elif "skilled-worker" in url or "part-h" in url:
                    visa_category = "Work Visa"
                elif "visitor" in url or "part-b" in url:
                    visa_category = "Visitor Visa"
                
                metadata = {
                    "source_url": url,
                    "country": country,
                    "visa_category": visa_category,
                    "timestamp": str(time.time()),
                }
                
                # If unstructured found a parent section/title, add it
                if hasattr(chunk.metadata, 'parent_id') and chunk.metadata.parent_id:
                    metadata["parent_id"] = chunk.metadata.parent_id
                    
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)
            
            # Store chunks in Chroma
            if documents:
                # BUG FIX: Deduplication via deterministic IDs
                import hashlib
                ids = [hashlib.md5(f"{doc.metadata['source_url']}{doc.page_content}".encode()).hexdigest() for doc in documents]
                vectorstore.add_documents(documents, ids=ids)
                context.log.info(f"Successfully processed and stored {len(documents)} chunks from {url}")
                
        except Exception as e:
            context.log.error(f"Failed to extract/store from {url}: {e}")

    # Start the automated discovery
    start_urls = [
        # US visa sources (USCIS)
        "https://www.uscis.gov/policy-manual",
        "https://www.uscis.gov/policy-manual/volume-2-part-b",  # Visitors
        "https://www.uscis.gov/policy-manual/volume-2-part-f",  # Students
        "https://www.uscis.gov/policy-manual/volume-2-part-h",  # Work visas
        
        # US visa sources (State Dept & ICE)
        "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
        "https://travel.state.gov/content/travel/en/us-visas/employment/temporary-worker-visas.html",
        "https://travel.state.gov/content/travel/en/us-visas/tourism-visit/visitor.html",
        "https://fam.state.gov/FAM/09FAM/09FAM040205.html",
        "https://studyinthestates.dhs.gov/students",

        # UK visa sources (Basic)
        "https://www.gov.uk/search/services?parent=%2Fentering-staying-uk%2Fvisas-entry-clearance&topic=29480b00-dc4d-49a0-b48c-25dda8569325",
        "https://www.gov.uk/standard-visitor",
        "https://www.gov.uk/student-visa",
        "https://www.gov.uk/skilled-worker-visa",

        # UK visa sources (Deep Lore/Caseworker)
        "https://www.gov.uk/guidance/immigration-rules/appendix-student",
        "https://www.gov.uk/guidance/immigration-rules/appendix-skilled-worker",
        "https://www.gov.uk/government/collections/student-route-caseworker-guidance",
        "https://www.gov.uk/government/publications/skilled-worker-visa-caseworker-guidance",
    ]
    
    print("Starting Crawlee ingestion pipeline...")
    await crawler.run(start_urls)
    print("Crawlee ingestion complete.")

if __name__ == '__main__':
    asyncio.run(main())
