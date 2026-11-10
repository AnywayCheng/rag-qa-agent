import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
FRESHNESS_TTL_HOURS = float(os.getenv("FRESHNESS_TTL_HOURS", "24"))

GENERATION_MODEL = "gemini-3.8-flash"
EMBEDDING_MODEL = "gemini-embedding-001"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHROMA_DB_PATH = str(PROJECT_ROOT / "chroma_db")
CHROMA_COLLECTION_NAME = "rag_qa"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETRIEVAL_TOP_K = 5
