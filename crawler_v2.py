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
        # Safe limit for testing the ingestion flow
        max_requests_per_crawl=20,
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
        # Let's target USCIS volume-2 and UK visas
        await context.enqueue_links(
            globs=[
                "https://www.uscis.gov/policy-manual/volume-2-**",
                "https://www.gov.uk/**"
            ],
            strategy="same-hostname"
        )

        try:
            # High-Fidelity Extraction (preserves tables as HTML inner strings)
            elements = partition_html(text=html_content, strategy="hi_res")
            
            # Title-aware chunking
            chunks = chunk_by_title(elements)

            documents = []
            for chunk in chunks:
                # If it's a Table, use text_as_html to keep tabular structure intact
                if hasattr(chunk, 'category') and chunk.category == 'Table' and hasattr(chunk.metadata, 'text_as_html') and chunk.metadata.text_as_html:
                    content = chunk.metadata.text_as_html
                else:
                    content = chunk.text
                
                # Assemble metadata
                metadata = {
                    "source_url": url,
                    "timestamp": str(time.time()),
                }
                
                # If unstructured found a parent section/title, add it
                if hasattr(chunk.metadata, 'parent_id') and chunk.metadata.parent_id:
                    metadata["parent_id"] = chunk.metadata.parent_id
                    
                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)
            
            # Store chunks in Chroma
            if documents:
                vectorstore.add_documents(documents)
                context.log.info(f"Successfully processed and stored {len(documents)} chunks from {url}")
                
        except Exception as e:
            context.log.error(f"Failed to extract/store from {url}: {e}")

    # Start the automated discovery
    start_urls = [
        "https://www.uscis.gov/policy-manual",
        "https://www.gov.uk/search/services?parent=%2Fentering-staying-uk%2Fvisas-entry-clearance&topic=29480b00-dc4d-49a0-b48c-25dda8569325"
    ]
    
    print("Starting Crawlee ingestion pipeline...")
    await crawler.run(start_urls)
    print("Crawlee ingestion complete.")

if __name__ == '__main__':
    asyncio.run(main())
