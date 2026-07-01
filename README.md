# PDF Knowledge Base Agent

A local, privacy-first PDF Q&A system powered by ChromaDB and sentence-transformers. Index your PDF documents and ask questions against them with full source citations.

## Architecture

```
[PDF Files] → [Text Extraction] → [Chunking] → [Embedding] → [ChromaDB]

[User Question] → [Embed] → [ChromaDB Search] → [Top 5 Chunks] → [Answer + Citations]
```

## Project Structure

```
├── .env                        # Configuration variables (create from .env.example)
├── .env.example                # Example configuration template
├── config.py                   # Centralized settings loader
├── ingest.py                   # PDF indexing pipeline
├── search.py                   # ChromaDB search script
├── requirements.txt            # Python dependencies
├── pdfs/                       # Place PDF files here
├── db/                         # ChromaDB persist directory
└── .opencode/
    └── agents/
        └── web-Api.md          # Sub-agent definition
```

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to customize settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Sentence-transformers model for embeddings (Japanese-optimized) |
| `CHROMA_PERSIST_DIR` | `./db` | ChromaDB storage directory |
| `CHROMA_COLLECTION_NAME` | `pdf_knowledge_base` | ChromaDB collection name |
| `PDF_FOLDER` | `./pdfs` | Directory containing PDF files |
| `CHUNK_SIZE` | `500` | Character size per chunk |
| `CHUNK_OVERLAP` | `100` | Character overlap between chunks |
| `TOP_K` | `5` | Number of results to retrieve |

## Usage

### Step 1: Add PDFs

Place your PDF files in the `pdfs/` directory.

### Step 2: Run Ingestion

```bash
python ingest.py
```

This will:
- Scan all PDFs in the `pdfs/` folder
- Extract text page by page
- Split into chunks with overlap
- Generate embeddings using sentence-transformers
- Store everything in ChromaDB

### Step 3: Search

**Direct CLI search:**
```bash
python search.py "your question here"
```

**Via web-Api sub-agent:**

Invoke `@web-Api` in opencode and ask your question. The sub-agent will search ChromaDB and return results with source citations.

## Output Format

Search results include:

- **Content** — The relevant text chunk
- **File** — Source PDF filename
- **Page** — Page number in the PDF
- **Section** — Section heading (first line of chunk)
- **Chunk ID** — Unique identifier (`filename_page{N}_chunk{N}`)
- **Similarity** — Relevance score (0-1)

## Components

### `config.py`

Loads configuration from `.env` and provides centralized access to all settings.

### `ingest.py`

PDF indexing pipeline:
1. Scans `pdfs/` for PDF files
2. Extracts text using PyMuPDF
3. Splits into chunks with configurable size and overlap
4. Generates embeddings with sentence-transformers
5. Stores in ChromaDB with metadata

### `search.py`

CLI search tool:
1. Takes a question as input
2. Generates embedding for the question
3. Queries ChromaDB for top-K similar chunks
4. Returns formatted results with source citations

### `web-Api.md`

Opencode sub-agent that:
- Accepts user questions
- Runs `search.py` via bash
- Returns formatted results to the caller

## Dependencies

| Package | Purpose |
|---------|---------|
| `chromadb` | Vector database for similarity search |
| `sentence-transformers` | Text embedding generation |
| `pdfplumber` | PDF text extraction |
| `python-dotenv` | Environment variable loading |

## Re-indexing

To re-index all PDFs (e.g., after adding new documents):

```bash
python ingest.py
```

This deletes the existing collection and rebuilds it from scratch.

## Limitations

- Sentence-aware chunking for Japanese text (splits on 。and newlines)
- No OCR for scanned PDFs
- No conversation memory
- Multilingual embedding model (intfloat/multilingual-e5-large) optimized for Japanese

## License

MIT
# web-api
