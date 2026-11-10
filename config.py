"""Central config for Verdant Capital."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM provider chain: "auto" | "gemini" | "openrouter" | "mock" ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")   # free tier, fast, great JSON

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "OPENROUTER_FALLBACK_MODELS",
        "openrouter/free,"
        "nvidia/nemotron-3.5-lightning:free,"
        "qwen/qwen3.8-27b:free",
    ).split(",") if m.strip()
]
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

DATA_DIR = "data_cache"
RAG_DIR = "rag_db"
RAG_PDF_DIR = os.path.join(DATA_DIR, "pdfs")
FEEDBACK_DB = os.path.join(DATA_DIR, "feedback.db")

CARBON_TICKER = "KRBN"
DEFAULT_CANDIDATES = ["TSLA", "NEE", "XOM", "ENPH", "ICLN", "VEST"]

DISAGREEMENT_THRESHOLD = 0.15
MAX_DEBATE_ROUNDS = 2
