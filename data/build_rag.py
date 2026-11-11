"""Issuer-isolated ChromaDB RAG with page-level provenance.

Add PDFs named TICKER__report.pdf to data_cache/pdfs/, e.g. NEE__2025_report.pdf.
User-uploaded disclosures are not independently authenticated.
Run: python -m data.build_rag
"""

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import config


def pdf_chunks(pdf_path, ticker, chunk_size=850, overlap=120):
    from pypdf import PdfReader

    pdf_path = Path(pdf_path)
    if not (0 <= overlap < chunk_size):
        raise ValueError("Invalid chunk overlap")
    reader = PdfReader(str(pdf_path))
    for page_index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        for start in range(0, len(text), chunk_size - overlap):
            chunk = text[start : start + chunk_size].strip()
            if len(chunk) < 65:
                continue
            digest = hashlib.sha256(
                f"{pdf_path.name}:{page_index}:{start}:{chunk}".encode()
            ).hexdigest()[:24]
            year_match = re.search(r"(?:19|20)\d{2}", pdf_path.stem)
            year = year_match.group(0) if year_match else "unknown"
            yield {
                "id": digest,
                "text": chunk,
                "ticker": ticker,
                "source": pdf_path.name,
                "page": page_index,
                "report_year": year,
                "mode": "uploaded_pdf",
                "citation": f"[{pdf_path.name} p.{page_index}]",
            }


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def _collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(config.RAG_DIR))
    return client.get_or_create_collection("issuer_esg_v2")


def main():
    pdf_dir = Path(config.RAG_PDF_DIR)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    collection = _collection()
    model = _embedding_model()
    indexed = 0
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        ticker = pdf.stem.split("__", 1)[0].upper().strip()
        if "__" not in pdf.stem or not ticker.isalnum():
            print(f"Skipping {pdf.name}: name must start with TICKER__")
            continue
        entries = list(pdf_chunks(pdf, ticker))
        if not entries:
            continue
        # Idempotent upsert, not add: rerunning ingestion does not fail on same ids.
        collection.upsert(
            ids=[e["id"] for e in entries],
            documents=[e["text"] for e in entries],
            embeddings=model.encode([e["text"] for e in entries]).tolist(),
            metadatas=[
                {k: e[k] for k in ("ticker", "source", "page", "report_year", "mode", "citation")}
                for e in entries
            ],
        )
        indexed += len(entries)
    print(f"Indexed/upserted {indexed} page-scoped chunks into {config.RAG_DIR}")
    return indexed


def query(ticker, query_text=None, k=5):
    """Fail closed: without a real index and issuer matches return no evidence."""
    ticker = str(ticker).upper().strip()
    if not ticker or not Path(config.RAG_DIR).exists():
        return []
    try:
        collection = _collection()
        count = collection.count()
        if not count:
            return []
        model = _embedding_model()
        q = (
            query_text
            or f"{ticker} emissions intensity targets baselines independent assurance capex"
        )
        result = collection.query(
            query_embeddings=model.encode([q]).tolist(),
            where={"ticker": ticker},
            n_results=min(k, count),
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return [
            dict(meta, text=doc)
            for doc, meta in zip(documents, metadatas, strict=False)
            if meta.get("ticker") == ticker
        ]
    except (ImportError, ValueError, RuntimeError, OSError) as error:
        print(f"[rag] retrieval unavailable: {type(error).__name__}")
        return []


if __name__ == "__main__":
    main()
