"""Central config for Verdant Capital."""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

DATA_DIR = "data_cache"
RAG_DIR = "rag_db"
RAG_PDF_DIR = os.path.join(DATA_DIR, "pdfs")
FEEDBACK_DB = os.path.join(DATA_DIR, "feedback.db")

# Carbon-credit market proxy (real, tradeable ETF tracking global carbon futures)
CARBON_TICKER = "KRBN"
DEFAULT_CANDIDATES = ["TSLA", "NEE", "XOM", "ENPH", "ICLN", "VEST"]

DISAGREEMENT_THRESHOLD = 0.15   # max allowed spread in agent confidences before a critique round
MAX_DEBATE_ROUNDS = 2
