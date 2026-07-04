"""
Module: rag/ingest.py
Purpose: Ingests all knowledge base markdown documents into ChromaDB
         vector store for RAG retrieval by WaterProfiler agent.
Component: RAG Knowledge Base — Document Ingestion Pipeline
Inputs: Markdown files in rag/knowledge_base/
Outputs: ChromaDB collection 'water_quality_knowledge' in data/chroma_db/
Key Design Decisions:
  - Chunk size 500 tokens with 50 token overlap: balances context window
    usage with retrieval precision. Smaller chunks = more precise retrieval.
  - Google text-embedding-004: free via Gemini API, high quality embeddings
    optimised for retrieval tasks.
  - Persistent ChromaDB: survives restarts, no need to re-ingest every run.
  - Source metadata stored with each chunk: enables citation in agent output.
Competition Concepts Demonstrated:
  - RAG (knowledge grounding for WaterProfiler agent)
"""

import os
import sys
import chromadb
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

KNOWLEDGE_BASE_PATH = Path(os.getenv("KNOWLEDGE_BASE_PATH", "./rag/knowledge_base"))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
COLLECTION_NAME = "water_quality_knowledge"
CHUNK_SIZE = 500        # characters per chunk (approximate token equivalent)
CHUNK_OVERLAP = 50      # overlap between chunks to preserve context
EMBEDDING_MODEL = "text-embedding-004"

# ── Google API Setup ───────────────────────────────────────────────────────────

def setup_google_api():
    """Configure Google Generative AI with API key from environment."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found in environment variables. "
            "Create a .env file with: GOOGLE_API_KEY=your_key_here"
        )
    genai.configure(api_key=api_key)
    print(f"Google API configured successfully")


# ── Document Loading ───────────────────────────────────────────────────────────

def load_documents(knowledge_base_path: Path) -> list[dict]:
    """
    Load all markdown files from the knowledge base directory.

    Args:
        knowledge_base_path: Path to directory containing .md files

    Returns:
        List of dicts with 'content', 'source', 'filename' keys
    """
    documents = []
    md_files = list(knowledge_base_path.glob("*.md"))

    if not md_files:
        raise FileNotFoundError(
            f"No markdown files found in {knowledge_base_path}. "
            "Ensure all 7 RAG documents are in rag/knowledge_base/"
        )

    print(f"Found {len(md_files)} documents to ingest:")
    for md_file in md_files:
        print(f"  - {md_file.name}")
        content = md_file.read_text(encoding="utf-8")
        documents.append({
            "content": content,
            "source": md_file.stem,       # filename without extension
            "filename": md_file.name,
        })

    return documents


# ── Text Chunking ──────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    Uses paragraph-aware chunking to avoid splitting mid-sentence.

    Args:
        text: Full document text
        chunk_size: Target chunk size in characters
        overlap: Overlap between consecutive chunks in characters

    Returns:
        List of text chunks
    """
    # Split on double newlines (paragraphs) first for cleaner chunks
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # If adding this paragraph exceeds chunk size, save current and start new
        if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap: carry forward end of current chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + paragraph
        else:
            current_chunk = (current_chunk + "\n\n" + paragraph).strip()

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


# ── Embedding Generation ───────────────────────────────────────────────────────

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings using Google text-embedding-004.
    Processes in batches to avoid API rate limits.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (each a list of floats)
    """
    embeddings = []
    batch_size = 10  # Google API limit per request

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch,
                task_type="RETRIEVAL_DOCUMENT",  # Optimised for document storage
            )
            embeddings.extend(result["embedding"])
            # Rate limit protection: small delay between batches
            if i + batch_size < len(texts):
                time.sleep(0.5)
        except Exception as e:
            print(f"Embedding error for batch {i//batch_size + 1}: {e}")
            raise

    return embeddings


# ── ChromaDB Setup ─────────────────────────────────────────────────────────────

def setup_chromadb(db_path: str) -> chromadb.Collection:
    """
    Initialise ChromaDB persistent client and create/get collection.

    Args:
        db_path: Path where ChromaDB data will be stored

    Returns:
        ChromaDB collection object
    """
    # Ensure data directory exists
    os.makedirs(db_path, exist_ok=True)

    # Persistent client saves to disk (survives restarts)
    client = chromadb.PersistentClient(path=db_path)

    # Delete existing collection if re-ingesting (clean slate)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}' for fresh ingest")
    except Exception:
        pass  # Collection didn't exist — that's fine

    # Create new collection (no embedding function — we provide our own embeddings)
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # Cosine similarity for text retrieval
    )
    print(f"Created ChromaDB collection: '{COLLECTION_NAME}'")
    return collection


# ── Main Ingestion Pipeline ────────────────────────────────────────────────────

def ingest_documents():
    """
    Main ingestion pipeline:
    1. Load markdown documents
    2. Chunk into smaller segments
    3. Generate embeddings via Google API
    4. Store in ChromaDB with metadata
    """
    print("\n" + "="*60)
    print("WaterSentinel RAG Ingestion Pipeline")
    print("="*60 + "\n")

    # Step 1: Setup
    setup_google_api()
    collection = setup_chromadb(CHROMA_DB_PATH)

    # Step 2: Load documents
    print(f"\nLoading documents from: {KNOWLEDGE_BASE_PATH}")
    documents = load_documents(KNOWLEDGE_BASE_PATH)

    # Step 3: Chunk documents
    print("\nChunking documents...")
    all_chunks = []
    all_ids = []
    all_metadatas = []

    for doc in documents:
        chunks = chunk_text(doc["content"])
        print(f"  {doc['filename']}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc['source']}_{i:04d}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadatas.append({
                "source": doc["source"],
                "filename": doc["filename"],
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

    print(f"\nTotal chunks to embed: {len(all_chunks)}")

    # Step 4: Generate embeddings
    print("\nGenerating embeddings via Google text-embedding-004...")
    print("(This may take 30-60 seconds for the full knowledge base)")
    embeddings = get_embeddings(all_chunks)
    print(f"Generated {len(embeddings)} embeddings")

    # Step 5: Store in ChromaDB
    print("\nStoring in ChromaDB...")
    collection.add(
        ids=all_ids,
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=all_metadatas,
    )

    # Verify
    count = collection.count()
    print(f"\n✅ Ingestion complete!")
    print(f"   Collection: '{COLLECTION_NAME}'")
    print(f"   Total chunks stored: {count}")
    print(f"   ChromaDB path: {CHROMA_DB_PATH}")
    print("\nRAG knowledge base is ready for WaterProfiler agent.")


if __name__ == "__main__":
    try:
        ingest_documents()
    except KeyboardInterrupt:
        print("\nIngestion cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        print("\nFallback: If Google embedding API fails, run with local embeddings:")
        print("  pip install sentence-transformers")
        print("  Then edit EMBEDDING_MODEL to use 'all-MiniLM-L6-v2'")
        sys.exit(1)
