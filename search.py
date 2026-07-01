import sys
import json
import hashlib
import sqlite3
from pathlib import Path
from difflib import SequenceMatcher
import chromadb
from sentence_transformers import SentenceTransformer

sys.stdout.reconfigure(encoding='utf-8')

from config import (
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    TOP_K,
)

CACHE_SIMILARITY_THRESHOLD = 0.6

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DB = CACHE_DIR / "search_cache.db"

_model = None
_client = None
_collection = None


def init_cache():
    CACHE_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            cache_key TEXT PRIMARY KEY,
            result TEXT NOT NULL,
            collection_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS collection_metadata (
            id INTEGER PRIMARY KEY,
            version TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _client.get_collection(name=CHROMA_COLLECTION_NAME)
    return _collection


def get_collection_version():
    try:
        collection = get_collection()
        metadata = collection.metadata
        return metadata.get("created_at", "unknown")
    except Exception:
        return "unknown"


def get_cache_key(query, top_k):
    key = f"{query}:{top_k}"
    return hashlib.md5(key.encode()).hexdigest()


def get_cached_result(cache_key):
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.execute(
        "SELECT result FROM search_cache WHERE cache_key = ?", (cache_key,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def find_similar_cached_result(query, top_k):
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.execute("SELECT result FROM search_cache")
    rows = cursor.fetchall()
    conn.close()

    best_match = None
    best_score = 0

    for row in rows:
        cached_result = json.loads(row[0])
        cached_question = cached_result.get("question", "")
        score = SequenceMatcher(None, query.lower(), cached_question.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = cached_result

    if best_score >= CACHE_SIMILARITY_THRESHOLD:
        return best_match, best_score
    return None, 0


def store_cache(cache_key, result):
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute(
        "INSERT OR REPLACE INTO search_cache (cache_key, result) VALUES (?, ?)",
        (cache_key, json.dumps(result)),
    )
    conn.commit()
    conn.close()


def invalidate_cache():
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute("DELETE FROM search_cache")
    conn.commit()
    conn.close()


def search_chromadb(question, top_k=TOP_K):
    init_cache()
    cache_key = get_cache_key(question, top_k)

    cached = get_cached_result(cache_key)
    if cached:
        return cached

    similar, score = find_similar_cached_result(question, top_k)
    if similar:
        return similar

    model = get_model()
    collection = get_collection()

    question_embedding = model.encode(question).tolist()

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results and results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            chunk = {
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
            chunks.append(chunk)

    result = {"question": question, "chunks": chunks}

    store_cache(cache_key, result)

    return result


def format_response(result):
    if "error" in result:
        return f"Error: {result['error']}"

    if not result["chunks"]:
        return "I couldn't find this information in the indexed PDF documents."

    output_lines = []
    output_lines.append("## Answer\n")
    output_lines.append("Based on the retrieved documents:\n")

    for i, chunk in enumerate(result["chunks"], 1):
        meta = chunk["metadata"]
        similarity = 1 - chunk["distance"]

        output_lines.append(f"### Chunk {i} (Similarity: {similarity:.4f})\n")
        output_lines.append(f"**Content:**\n{chunk['document']}\n")
        output_lines.append(f"**Source:**")
        output_lines.append(f"- File: {meta.get('filename', 'N/A')}")
        output_lines.append(f"- Page: {meta.get('page', 'N/A')}")
        output_lines.append(f"- Section: {meta.get('section', 'N/A')}")
        output_lines.append(f"- Chunk ID: {meta.get('chunk_id', 'N/A')}")
        output_lines.append("")

    return "\n".join(output_lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py \"your question here\"")
        sys.exit(1)

    if sys.argv[1] == "--clear-cache":
        invalidate_cache()
        print("Cache cleared successfully")
        return

    question = " ".join(sys.argv[1:])
    result = search_chromadb(question)
    print(format_response(result))


if __name__ == "__main__":
    main()
