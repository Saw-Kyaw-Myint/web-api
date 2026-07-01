import sys
import json
import chromadb
from sentence_transformers import SentenceTransformer
from config import (
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    TOP_K,
)


def search_chromadb(question, top_k=TOP_K):
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        return {"error": "Collection not found. Run ingest.py first."}

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

    return {"question": question, "chunks": chunks}


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

    question = " ".join(sys.argv[1:])
    result = search_chromadb(question)
    print(format_response(result))


if __name__ == "__main__":
    main()
