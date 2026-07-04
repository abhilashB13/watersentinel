"""
Module: rag/query.py - Local Embedding Version
Uses sentence-transformers for query embeddings — matches ingest.py model.
Must use SAME model as ingest.py (all-MiniLM-L6-v2).
"""

import os
import chromadb
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
COLLECTION_NAME = "water_quality_knowledge"
TOP_K_RESULTS = 3

# Singleton model instance — load once, reuse across queries
_model = None
_collection = None


def get_model():
    """Load sentence-transformers model once and cache it."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Run: uv add sentence-transformers"
            )
    return _model


def get_collection() -> chromadb.Collection:
    """Get ChromaDB collection (singleton)."""
    global _collection
    if _collection is None:
        if not Path(CHROMA_DB_PATH).exists():
            raise RuntimeError(
                "ChromaDB not found. Run: uv run python rag/ingest.py"
            )
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def query_knowledge_base(
    symptoms: list[str],
    source_type: str,
    location_context: str = "",
    top_k: int = TOP_K_RESULTS,
) -> list[dict]:
    """
    Query RAG knowledge base for relevant water quality information.
    Used as a tool by WaterProfiler ADK agent.
    """
    symptom_text = ", ".join(symptoms) if symptoms else "water quality issue"
    query_text = (
        f"Water quality symptoms: {symptom_text}. "
        f"Water source: {source_type}. "
        f"Location: {location_context}. "
        f"Contaminants, BIS limits, health risks, treatment recommendations."
    )

    try:
        model = get_model()
        query_embedding = model.encode(query_text, convert_to_numpy=True).tolist()

        collection = get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        if results and results["documents"] and results["documents"][0]:
            for doc, metadata, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                formatted.append({
                    "content": doc,
                    "source": metadata["source"],
                    "citation": _get_citation(metadata["source"]),
                    "relevance_score": round(1 - distance, 3),
                })
        return formatted

    except Exception as e:
        print(f"RAG query error: {e}")
        return _get_fallback_results(symptoms)


def _get_citation(source: str) -> str:
    citation_map = {
        "bis_is10500_2012": "BIS IS 10500:2012 — Indian Standard: Drinking Water Specification",
        "who_guidelines_2022": "WHO Guidelines for Drinking-water Quality, 4th Edition (2022)",
        "cgwb_telangana_2023": "CGWB Groundwater Quality Report — Telangana (2023)",
        "cgwb_ap_2023": "CGWB Groundwater Quality Report — Andhra Pradesh (2023)",
        "symptom_contaminant_map": "WaterSentinel Symptom-Contaminant Reference Guide",
        "india_water_sources_guide": "WaterSentinel India Water Sources Guide",
        "treatment_recommendations": "WaterSentinel Water Treatment Recommendations Guide",
    }
    return citation_map.get(source, f"WaterSentinel Knowledge Base — {source}")


def _get_fallback_results(symptoms: list[str]) -> list[dict]:
    fallback_map = {
        "egg_smell": "Egg smell indicates H2S. BIS IS 10500:2012 limit: 0.05 mg/L. Safe for bathing, treat before drinking. Common in deep borewells >250ft.",
        "yellow_colour": "Yellow water indicates Iron (Fe). BIS limit: 0.3 mg/L. Safe for bathing, treat before drinking. Install iron removal filter — not UV.",
        "white_deposits": "White deposits indicate high TDS. BIS limit: 500 mg/L. Linked to kidney stones. RO system recommended. Boiling concentrates TDS.",
        "black_colour": "Black water indicates sewage contamination or manganese. STOP use immediately. Contact municipal authority as emergency.",
    }
    results = []
    for symptom in symptoms:
        if symptom in fallback_map:
            results.append({
                "content": fallback_map[symptom],
                "source": "fallback",
                "citation": "BIS IS 10500:2012 (Fallback)",
                "relevance_score": 0.70,
            })
    if not results:
        results.append({
            "content": "Get water tested at certified NABL lab. Boil water before drinking as precaution.",
            "source": "fallback",
            "citation": "WaterSentinel General Advisory",
            "relevance_score": 0.50,
        })
    return results


def test_query():
    print("\n" + "="*60)
    print("WaterSentinel RAG Query Test")
    print("="*60)
    results = query_knowledge_base(
        symptoms=["egg_smell", "yellow_colour"],
        source_type="borewell",
        location_context="Nallagandla, Hyderabad",
    )
    print(f"\n✅ Retrieved {len(results)} chunks:\n")
    for i, r in enumerate(results, 1):
        print(f"Result {i} (relevance: {r['relevance_score']}):")
        print(f"  Citation: {r['citation']}")
        print(f"  Preview: {r['content'][:150]}...")
        print()


if __name__ == "__main__":
    test_query()
