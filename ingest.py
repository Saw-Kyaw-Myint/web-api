import os
import sys
import pdfplumber
import chromadb
from sentence_transformers import SentenceTransformer
from config import (
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    PDF_FOLDER,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


def extract_text_from_pdf(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page": page_num, "text": text})
    return pages


def chunk_text(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - chunk_overlap
    return chunks


def get_section_name(chunk):
    lines = chunk.strip().split("\n")
    for line in lines:
        cleaned = line.strip()
        if cleaned and len(cleaned) < 100:
            return cleaned[:80]
    return "Unknown Section"


def ingest_pdfs():
    if not os.path.exists(PDF_FOLDER):
        print(f"PDF folder not found: {PDF_FOLDER}")
        return

    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"No PDF files found in {PDF_FOLDER}")
        return

    print(f"Found {len(pdf_files)} PDF file(s)")
    print(f"Loading embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
        print("Deleted existing collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    total_chunks = 0

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER, pdf_file)
        print(f"\nProcessing: {pdf_file}")

        pages = extract_text_from_pdf(pdf_path)
        print(f"  Extracted {len(pages)} pages")

        for page_info in pages:
            page_num = page_info["page"]
            text = page_info["text"]

            chunks = chunk_text(text)

            for idx, chunk in enumerate(chunks):
                chunk_id = f"{pdf_file}_page{page_num}_chunk{idx}"
                section = get_section_name(chunk)

                embedding = model.encode(chunk).tolist()

                collection.add(
                    ids=[chunk_id],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[
                        {
                            "filename": pdf_file,
                            "page": page_num,
                            "section": section,
                            "chunk_id": chunk_id,
                        }
                    ],
                )
                total_chunks += 1

        print(f"  Indexed {sum(1 for _ in collection.get()['ids'] if pdf_file in _)} chunks")

    print(f"\nIngestion complete! Total chunks indexed: {total_chunks}")
    print(f"Database saved to: {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    ingest_pdfs()
