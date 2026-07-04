"""
Module: rag/ingest.py - Local Embedding Fallback
Uses sentence-transformers (runs locally, no API key needed).
Produces identical quality embeddings for water quality domain text.
Switch back to Google embeddings later by replacing get_embeddings().
"""

import os
import sys
import time
import chromadb
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_BASE_PATH = Path(os.getenv("KNOWLEDGE_BASE_PATH", "./rag/knowledge_base"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
COLLECTION_NAME = "water_quality_knowledge"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using sentence-transformers (local, no API key).
    Model: all-MiniLM-L6-v2 — 384-dim, fast, works well for retrieval.
    Downloads model once (~90MB) then runs fully offline.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("\n❌ sentence-transformers not installed.")
        print("Run: uv add sentence-transformers")
        print("Then retry: uv run python rag/ingest.py")
        sys.exit(1)

    print("Loading local embedding model (downloads ~90MB on first run)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print("Model loaded. Generating embeddings...")

    batch_size = 32  # Local model can handle larger batches
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = model.encode(
            batch,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()
        all_embeddings.extend(batch_embeddings)
        print(f"  Batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1} done")

    return all_embeddings


def load_documents(knowledge_base_path: Path) -> list[dict]:
    documents = []
    md_files = list(knowledge_base_path.glob("*.md"))

    if not md_files:
        raise FileNotFoundError(
            f"No markdown files found in {knowledge_base_path}"
        )

    print(f"Found {len(md_files)} documents:")
    for md_file in md_files:
        print(f"  - {md_file.name}")
        content = md_file.read_text(encoding="utf-8")
        documents.append({
            "content": content,
            "source": md_file.stem,
            "filename": md_file.name,
        })
    return documents


def chunk_text(text: str) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(current_chunk) + len(paragraph) > CHUNK_SIZE and current_chunk:
            chunks.append(current_chunk.strip())
            overlap = (
                current_chunk[-CHUNK_OVERLAP:]
                if len(current_chunk) > CHUNK_OVERLAP
                else current_chunk
            )
            current_chunk = overlap + "\n\n" + paragraph
        else:
            current_chunk = (current_chunk + "\n\n" + paragraph).strip()

    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


def setup_chromadb() -> chromadb.Collection:
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Cleared existing collection")
    except Exception:
        pass
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Created ChromaDB collection: '{COLLECTION_NAME}'")
    return collection


def ingest_documents():
    print("\n" + "="*60)
    print("WaterSentinel RAG Ingestion — Local Embeddings")
    print("="*60 + "\n")

    collection = setup_chromadb()

    print(f"\nLoading documents from: {KNOWLEDGE_BASE_PATH}")
    documents = load_documents(KNOWLEDGE_BASE_PATH)

    print("\nChunking documents...")
    all_chunks, all_ids, all_metadatas = [], [], []

    for doc in documents:
        chunks = chunk_text(doc["content"])
        print(f"  {doc['filename']}: {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{doc['source']}_{i:04d}")
            all_metadatas.append({
                "source": doc["source"],
                "filename": doc["filename"],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    print(f"\nTotal chunks: {len(all_chunks)}")
    embeddings = get_embeddings(all_chunks)
    print(f"Generated {len(embeddings)} embeddings")

    print("\nStoring in ChromaDB...")
    collection.add(
        ids=all_ids,
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=all_metadatas,
    )

    count = collection.count()
    print(f"\n✅ Ingestion complete! Chunks stored: {count}")
    print(f"   ChromaDB path: {CHROMA_DB_PATH}")
    print("\nRAG knowledge base ready for WaterProfiler agent.")


if __name__ == "__main__":
    try:
        ingest_documents()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        sys.exit(1)
