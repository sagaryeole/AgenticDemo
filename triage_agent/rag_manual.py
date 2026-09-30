# rag_manual.py
from dotenv import load_dotenv
load_dotenv()  # loads .env from current directory

import os, glob, numpy as np
from vertexai.language_models import TextEmbeddingModel
import vertexai
from google.cloud import aiplatform
import re

SERVICES = ["payments-api", "orders-api", "auth-service", "notifications-service"]

# Fix: Use actual project ID or set up BigQuery Storage for Vertex AI
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise ValueError("Set GOOGLE_CLOUD_PROJECT environment variable")

# Fix: Initialize with proper project and check for billing
vertexai.init(project=PROJECT_ID, location="us-central1")

# Fix: Use BigQuery Storage for embeddings (avoids Vertex AI permission issues)
# This is a free alternative that doesn't require Vertex AI permissions
try:
    # Try Vertex AI first (if you have proper permissions)
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    HAS_VERTEX_AI = True
except Exception as e:
    print(f"Vertex AI not available: {e}")
    print("Falling back to local embedding model...")
    
    # Fallback: Use HuggingFace BGE model (free, no API key needed)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("BAAI/bge-m3")
    HAS_VERTEX_AI = False

def load_runbooks(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "runbooks", "*.md")):
    docs = []
    for f in glob.glob(path):
        with open(f) as fh:
            docs.append({"id": f, "text": fh.read()})
    return docs

def embed_texts(texts):
    if HAS_VERTEX_AI:
        embeddings = model.get_embeddings(texts)
        return np.array([e.values for e in embeddings])
    else:
        # Fallback: embed using local model
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def extract_service(query: str) -> str | None:
    q = query.lower()
    for s in SERVICES:
        if s in q:
            return s
    return None

def retrieve(query, docs, doc_embeddings, top_k=3, service_boost=0.15):
    q_emb = embed_texts([query])[0]
    mentioned_service = extract_service(query)

    scored = []
    for doc, d_emb in zip(docs, doc_embeddings):
        score = cosine_sim(q_emb, d_emb)
        if mentioned_service and mentioned_service in doc["id"]:
            score += service_boost
        scored.append((doc, score))

    ranked = sorted(scored, key=lambda x: x[1], reverse=True)
    return ranked[:top_k]

if __name__ == "__main__":
    docs = load_runbooks()
    doc_embeddings = embed_texts([d["text"] for d in docs])

    queries = [
        "payments API is timing out",
        "auth token expired",
        "orders-api returning 500s",
        "service is slow",
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        results = retrieve(q, docs, doc_embeddings, top_k=3)
        for doc, score in results:
            print(f"  {score:.3f}  {doc['id']}")