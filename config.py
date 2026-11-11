"""Verdant Capital settings. Never commit a populated .env file."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

DATA_DIR = str((BASE_DIR / (os.getenv("VERDANT_DATA_DIR") or "data_cache")).resolve())
RAG_DIR = str((BASE_DIR / (os.getenv("VERDANT_RAG_DIR") or "rag_db")).resolve())
RAG_PDF_DIR = os.path.join(DATA_DIR, "pdfs")
FEEDBACK_DB = os.getenv("VERDANT_FEEDBACK_DB") or os.path.join(DATA_DIR, "feedback.db")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
CARBON_TICKER = "KRBN"  # ETF proxy, NOT carbon allowance spot prices
DEFAULT_CANDIDATES = ["NEE", "ENPH", "TSLA", "XOM", "ICLN"]
DEMO_CANDIDATES = ["SOLR", "WIND", "FOSS"]  # entirely fictional synthetic assets
MAX_DEBATE_ROUNDS = 1
