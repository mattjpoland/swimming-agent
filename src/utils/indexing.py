import os
import json
import pickle
import logging
import requests
import faiss
import numpy as np
import openai
import tiktoken
from PyPDF2 import PdfReader
import tempfile
from src.sql.ragSourceGateway import get_all_rag_sources

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536  # For text-embedding-3-small

def load_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def load_text_from_pdf_url(pdf_url):
    resp = requests.get(pdf_url, verify=False)  # Disable SSL verification
    resp.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(resp.content)
        tmp_path = tmp_file.name
    text = load_text_from_pdf(tmp_path)
    os.remove(tmp_path)
    return text

def load_text_from_url(url):
    resp = requests.get(url, verify=False)  # Disable SSL verification
    resp.raise_for_status()
    return resp.text

def chunk_text(text, max_tokens=300):
    enc = tiktoken.get_encoding("cl100k_base")
    words = text.split()
    chunks = []
    chunk = []
    token_count = 0
    for word in words:
        tokens = len(enc.encode(word + " "))
        if token_count + tokens > max_tokens:
            chunks.append(" ".join(chunk))
            chunk = []
            token_count = 0
        chunk.append(word)
        token_count += tokens
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks

def embed_chunks(chunks):
    embeddings = []
    for chunk in chunks:
        resp = openai.embeddings.create(
            input=chunk,
            model=EMBEDDING_MODEL
        )
        embeddings.append(resp.data[0].embedding)
    return np.array(embeddings, dtype="float32")

def rebuild_index(source_type="pdf", source_path=None, source_url=None, faiss_path="index.faiss", meta_path="chunks.json"):
    try:
        # 1. Load text
        if source_type == "pdf" and source_path:
            text = load_text_from_pdf(source_path)
            source = source_path
        elif source_type == "url" and source_url:
            text = load_text_from_url(source_url)
            source = source_url
        else:
            raise ValueError("Invalid source_type or missing path/url.")

        # 2. Chunk text
        chunks = chunk_text(text)
        chunk_meta = []
        for i, chunk in enumerate(chunks):
            chunk_meta.append({
                "chunk_id": i,
                "source": source,
                "text": chunk
            })

        # 3. Embed chunks
        embeddings = embed_chunks(chunks)

        # 4. Build and save FAISS index
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        index.add(embeddings)
        faiss.write_index(index, faiss_path)

        # 5. Save metadata
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(chunk_meta, f, ensure_ascii=False, indent=2)

        # 6. Optionally hot-swap in-memory index (if needed)
        # You can implement a global or app context variable to hold the index if desired.

        logging.info("Index rebuilt successfully.")
        return True, f"Indexed {len(chunks)} chunks from {source}"
    except Exception as e:
        logging.error(f"Failed to rebuild index: {e}")
        return False, str(e)

def rebuild_index_from_config(
    config_path="rag_sources.json",
    faiss_path="index.faiss",
    meta_path="chunks.json"
):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            sources = json.load(f)

        all_chunks = []
        all_metadata = []
        chunk_id = 0

        for source in sources:
            label = source.get("label") or source.get("path") or source.get("url")
            if source["type"] == "pdf":
                text = load_text_from_pdf(source["path"])
            elif source["type"] == "url":
                text = load_text_from_url(source["url"])
            elif source["type"] == "text":
                with open(source["path"], "r", encoding="utf-8") as tf:
                    text = tf.read()
            else:
                logging.warning(f"Unknown source type: {source['type']}")
                continue

            chunks = chunk_text(text)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadata.append({
                    "chunk_id": chunk_id,
                    "source": label,
                    "text": chunk
                })
                chunk_id += 1

        if not all_chunks:
            raise ValueError("No chunks found from sources.")

        embeddings = embed_chunks(all_chunks)

        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        index.add(embeddings)
        faiss.write_index(index, faiss_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)

        logging.info(f"Index rebuilt successfully from {len(sources)} sources, {len(all_chunks)} chunks.")
        return True, f"Indexed {len(all_chunks)} chunks from {len(sources)} sources."
    except Exception as e:
        logging.error(f"Failed to rebuild index from config: {e}")
        return False, str(e)

def rebuild_index_from_db(
    faiss_path="index.faiss",
    meta_path="chunks.json"
):
    try:
        sources = get_all_rag_sources()
        all_chunks = []
        all_metadata = []
        chunk_id = 0

        for source in sources:
            label = source.get("label") or source.get("path") or source.get("url")
            text = None

            # Handle PDF (local or URL)
            if source["type"] == "pdf":
                if "path" in source and source["path"]:
                    text = load_text_from_pdf(source["path"])
                elif "url" in source and source["url"]:
                    text = load_text_from_pdf_url(source["url"])
                else:
                    logging.warning(f"No path or url for PDF source: {label}")
                    continue
            # Handle URL (web page or PDF)
            elif source["type"] == "url":
                url = source.get("url")
                if url and url.lower().endswith(".pdf"):
                    text = load_text_from_pdf_url(url)
                elif url:
                    text = load_text_from_url(url)
                else:
                    logging.warning(f"No url for URL source: {label}")
                    continue
            # Handle plain text file
            elif source["type"] == "text":
                if "path" in source and source["path"]:
                    with open(source["path"], "r", encoding="utf-8") as tf:
                        text = tf.read()
                else:
                    logging.warning(f"No path for text source: {label}")
                    continue
            else:
                logging.warning(f"Unknown source type: {source.get('type')}")
                continue

            if not text:
                logging.warning(f"No text extracted for source: {label}")
                continue

            chunks = chunk_text(text)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadata.append({
                    "chunk_id": chunk_id,
                    "source": label,
                    "text": chunk
                })
                chunk_id += 1

        if not all_chunks:
            raise ValueError("No chunks found from sources.")

        embeddings = embed_chunks(all_chunks)

        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        index.add(embeddings)
        faiss.write_index(index, faiss_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)

        logging.info(f"Index rebuilt successfully from {len(sources)} sources, {len(all_chunks)} chunks.")
        return True, f"Indexed {len(all_chunks)} chunks from {len(sources)} sources."
    except Exception as e:
        logging.error(f"Failed to rebuild index from DB: {e}")
        return False, str(e)

