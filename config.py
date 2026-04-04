import os

# Chromadb Configuration
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "visa_policies"

# Web Scraping Configuration
PLAYWRIGHT_TIMEOUT = 60000
DEFAULT_USER_AGENT = "Mozilla/5.0"
DYNAMIC_WAIT_TIME = 3

# Text Splitting Configuration
CHUNK_SIZE = 800
CHUNK_OVERLAP = 80

# External Files
SITES_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "sites.json")
