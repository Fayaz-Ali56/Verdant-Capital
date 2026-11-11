"""Build the RAG store from ESG PDFs in data_cache/pdfs/. Run: python -m data.build_rag"""
import os, glob
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import config

os.makedirs(config.RAG_PDF_DIR, exist_ok=True)

def load_chunks(pdf_path, chunk_size=900, overlap=150):
    text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 80]

def main():
    client = chromadb.PersistentClient(path=config.RAG_DIR)
    col = client.get_or_create_collection("esg_docs")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    n = 0
    for pdf in glob.glob(os.path.join(config.RAG_PDF_DIR, "*.pdf")):
        name = os.path.basename(pdf)
        for j, chunk in enumerate(load_chunks(pdf)):
            col.add(ids=[f"{name}-{j}"], documents=[chunk],
                    embeddings=[model.encode(chunk).tolist()],
                    metadatas=[{"source": name}])
            n += 1
    print(f"Indexed {n} chunks into {config.RAG_DIR}")

_MODEL = None

def _model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL

def query(q: str, k: int = 5):
    client = chromadb.PersistentClient(path=config.RAG_DIR)
    col = client.get_or_create_collection("esg_docs")
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=[_model().encode(q).tolist()], n_results=min(k, col.count()))
    return list(zip(res["documents"][0], [m["source"] for m in res["metadatas"][0]]))

if __name__ == "__main__":
    main()
