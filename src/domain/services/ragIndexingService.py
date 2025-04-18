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
import re
from bs4 import BeautifulSoup  # Add this import
from pathlib import Path
from src.domain.sql.ragSourceGateway import get_all_rag_sources
import time

openai.verify_ssl_certs = False  # Disable SSL verification for OpenAI API")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536  # For text-embedding-3-small

# Chunking configuration
CHUNK_MAX_TOKENS = 200       # Maximum tokens per chunk
CHUNK_OVERLAP = 50           # Number of tokens to overlap between chunks
CHUNK_OVERLAP_RATIO = 0.2    # Percentage of chunk size to overlap

def load_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def load_text_from_pdf_url(pdf_url):
    resp = requests.get(pdf_url)  # Disable SSL verification
    resp.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(resp.content)
        tmp_path = tmp_file.name
    text = load_text_from_pdf(tmp_path)
    os.remove(tmp_path)
    return text

def load_text_from_url(url):
    resp = requests.get(url)  # Disable SSL verification
    resp.raise_for_status()
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
        
    # Get text and clean it up
    text = soup.get_text(separator=' ', strip=True)
    
    # Remove excessive whitespace
    lines = (line.strip() for line in text.splitlines())
    text = ' '.join(chunk for chunk in lines if chunk)
    
    logging.info(f"Extracted {len(text)} characters of clean text from URL")
    return text

def split_into_semantic_units(text):
    """Split text into semantic units (paragraphs, sections, lists)"""
    # First split by double newlines (paragraphs)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    # Process each paragraph to handle lists, bullet points, etc.
    semantic_units = []
    for para in paragraphs:
        # If very long paragraph, try to split on sentence boundaries
        if len(para) > 1500:  # ~375 tokens
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_unit = ""
            
            for sentence in sentences:
                if len(current_unit) + len(sentence) < 1500:
                    current_unit += sentence + " "
                else:
                    semantic_units.append(current_unit.strip())
                    current_unit = sentence + " "
                    
            if current_unit.strip():
                semantic_units.append(current_unit.strip())
        else:
            semantic_units.append(para)
    
    # Remove any tiny units (likely noise)
    semantic_units = [unit for unit in semantic_units if len(unit) > 20]
    
    logging.info(f"Split text into {len(semantic_units)} semantic units")
    return semantic_units

def chunk_text(text, max_tokens=CHUNK_MAX_TOKENS, overlap=CHUNK_OVERLAP):
    """
    Improved semantic chunking with sliding window:
    1. Split by semantic units (paragraphs, lists)
    2. Keep semantic units together where possible
    3. Implement sliding window overlap between chunks
    """
    enc = tiktoken.get_encoding("cl100k_base")
    
    # Step 1: Split text into semantic units
    semantic_units = split_into_semantic_units(text)
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    overlap_text = ""
    overlap_tokens = 0
    
    for unit in semantic_units:
        unit_tokens = len(enc.encode(unit))
        
        # Case 1: Unit fits in current chunk
        if current_tokens + unit_tokens <= max_tokens:
            current_chunk += (unit + "\n\n")
            current_tokens += unit_tokens + 2  # +2 for newlines
            
        # Case 2: Unit doesn't fit, finish current chunk and start new one
        else:
            # Store the current chunk if not empty
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Calculate overlap from previous chunk
            if chunks and overlap > 0:
                # Get the last part of the previous chunk for overlap
                prev_tokens = enc.encode(current_chunk)
                overlap_size = min(overlap, len(prev_tokens))
                overlap_text = enc.decode(prev_tokens[-overlap_size:])
            
            # If the unit itself is too large for a single chunk
            if unit_tokens > max_tokens:
                # Split large unit into smaller chunks by tokens
                unit_enc = enc.encode(unit)
                for i in range(0, len(unit_enc), max_tokens - overlap):
                    chunk_tokens = unit_enc[i:i + max_tokens - overlap]
                    chunk_text = enc.decode(chunk_tokens).strip()
                    
                    # Add overlap from previous chunk
                    if i > 0 and overlap > 0:
                        overlap_chunk = enc.decode(unit_enc[i-overlap:i])
                        chunk_text = overlap_chunk + chunk_text
                    
                    chunks.append(chunk_text)
            else:
                # Start a new chunk with this unit
                current_chunk = overlap_text + unit + "\n\n"
                current_tokens = len(enc.encode(current_chunk))
    
    # Add the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Log for debugging
    logging.info(f"Generated {len(chunks)} chunks with semantic boundaries and {overlap} token overlap")
    for i, chunk in enumerate(chunks):
        logging.debug(f"Chunk {i+1}/{len(chunks)}: {chunk[:100]}...")
    
    return chunks

def embed_chunks(chunks, batch_size=8):  # Reduced from 32 to 8
    embeddings = []
    batch_count = (len(chunks) + batch_size - 1) // batch_size
    
    logging.info(f"Starting embedding of {len(chunks)} chunks in {batch_count} batches")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        logging.info(f"Processing batch {batch_num}/{batch_count} ({len(batch)} chunks)")
        
        # Ensure chunks aren't too large (max 8192 chars per item recommended)
        batch = [chunk[:8000] for chunk in batch]  
        
        last_exception = None
        for retry in range(5):  # Increased from 3 to 5 retries
            try:
                resp = openai.embeddings.create(
                    input=batch,
                    model=EMBEDDING_MODEL
                )
                for item in resp.data:
                    embeddings.append(item.embedding)
                
                logging.info(f"Batch {batch_num}/{batch_count} successfully embedded")
                break
                
            except openai.APIConnectionError as e:
                # Exponential backoff
                wait_time = (2 ** retry) + 1  # 3, 5, 9, 17, 33 seconds
                logging.warning(f"Connection error on batch {batch_num}/{batch_count}, retry {retry+1}/5, waiting {wait_time}s: {e}")
                last_exception = e
                time.sleep(wait_time)
        else:
            logging.error(f"Failed to embed batch {batch_num}/{batch_count} after 5 retries.")
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"Failed to embed batch {batch_num} after retries")
                
        # Longer delay between batches
        time.sleep(2)  # Increased from 1s to 2s
    
    logging.info(f"Successfully embedded {len(embeddings)} chunks")
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
        chunks = chunk_text(text, max_tokens=CHUNK_MAX_TOKENS, overlap=CHUNK_OVERLAP)
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

def rebuild_index_from_db(faiss_path="index.faiss", meta_path="chunks.json"):
    try:
        sources = get_all_rag_sources()
        logging.info(f"Found {len(sources)} sources to process")
        all_metadata = []
        all_embeddings = []
        chunk_id = 0
        success_count = 0

        # Process each source individually
        for source_idx, source in enumerate(sources):
            label = source.get("label") or source.get("path") or source.get("url")
            logging.info(f"Processing source {source_idx+1}/{len(sources)}: {label}")
            
            try:
                # Extract text from the appropriate source
                text = None
                if source["type"] == "pdf":
                    if "path" in source and source["path"]:
                        text = load_text_from_pdf(source["path"])
                    elif "url" in source and source["url"]:
                        text = load_text_from_pdf_url(source["url"])
                elif source["type"] == "url":
                    url = source.get("url")
                    if url and url.lower().endswith(".pdf"):
                        text = load_text_from_pdf_url(url)
                    elif url:
                        text = load_text_from_url(url)
                elif source["type"] == "text" and "path" in source and source["path"]:
                    with open(source["path"], "r", encoding="utf-8") as tf:
                        text = tf.read()
                
                if not text:
                    logging.warning(f"No text extracted for source: {label}")
                    continue
                
                # Use the improved semantic chunking with overlap
                chunks = chunk_text(text, max_tokens=CHUNK_MAX_TOKENS, overlap=CHUNK_OVERLAP)
                if not chunks:
                    logging.warning(f"No chunks generated for source: {label}")
                    continue
                
                logging.info(f"Processing source: {source.get('url') or source.get('path')}")
                logging.info(f"Chunks generated: {len(chunks)}")
                
                # Embed the chunks for this source
                logging.info(f"Embedding {len(chunks)} chunks for source: {label}")
                
                # Use very small batch size
                source_embeddings = embed_chunks(chunks, batch_size=4)
                
                # Store metadata and embeddings for this source
                source_metadata = []
                for i, chunk in enumerate(chunks):
                    # Enhanced metadata with position information
                    source_metadata.append({
                        "chunk_id": chunk_id,
                        "source": label,
                        "text": chunk,
                        "position": {
                            "index": i,
                            "total": len(chunks),
                            "is_first": i == 0,
                            "is_last": i == len(chunks) - 1
                        }
                    })
                    chunk_id += 1
                
                # Append to the full collections
                all_metadata.extend(source_metadata)
                all_embeddings.append(source_embeddings)
                
                # Save partial progress after each successful source
                partial_meta_path = f"{meta_path}.partial"
                with open(partial_meta_path, "w", encoding="utf-8") as f:
                    json.dump(all_metadata, f, ensure_ascii=False, indent=2)
                
                logging.info(f"Successfully processed source: {label}")
                success_count += 1
                
            except Exception as e:
                logging.error(f"Error processing source {label}: {e}")
                # Continue with next source instead of failing completely
        
        # If we processed at least one source successfully, build the index
        if all_embeddings:
            combined_embeddings = np.vstack(all_embeddings)
            
            # Build and save the FAISS index
            index = faiss.IndexFlatL2(EMBEDDING_DIM)
            index.add(combined_embeddings)
            faiss.write_index(index, faiss_path)  # Changed from faiss.write_index(faiss_path, index)
            
            # Save the final metadata
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(all_metadata, f, ensure_ascii=False, indent=2)
            
            logging.info(f"Final index size: {len(all_metadata)} chunks")
            logging.info(f"Index rebuilt with {len(all_metadata)} chunks from {success_count}/{len(sources)} sources.")
            return True, f"Indexed {len(all_metadata)} chunks from {success_count}/{len(sources)} sources."
        else:
            return False, "No sources could be processed successfully."
            
    except Exception as e:
        logging.error(f"Failed to rebuild index from DB: {e}")
        return False, str(e)

def verify_index():
    """Verify RAG index and return detailed status information"""
    try:
        index_path = Path("index.faiss")
        chunks_path = Path("chunks.json")
        
        status = {
            "status": "ok",
            "chunks_count": 0,
            "index_size": 0,
            "sources": {},
            "sample_chunks": []
        }

        # Check files exist
        if not index_path.exists() or not chunks_path.exists():
            return {
                "status": "error", 
                "message": "Missing index files",
                "index_exists": index_path.exists(),
                "chunks_exists": chunks_path.exists()
            }

        # Load and analyze chunks
        with open(chunks_path, 'r') as f:
            chunks = json.load(f)
            status["chunks_count"] = len(chunks)
            
            # Analyze sources distribution
            for chunk in chunks:
                source = chunk.get('source', 'unknown')
                status["sources"][source] = status["sources"].get(source, 0) + 1
            
            # Add sample chunks (first chunk from each source)
            seen_sources = set()
            for chunk in chunks:
                source = chunk.get('source', 'unknown')
                if source not in seen_sources:
                    seen_sources.add(source)
                    status["sample_chunks"].append({
                        "chunk_id": chunk.get('chunk_id', 0),
                        "source": source,
                        "text": chunk.get('text', '')[:150]  # Preview of text
                    })

        # Verify FAISS index
        index = faiss.read_index(str(index_path))
        status["index_size"] = index.ntotal
        
        # Verify index and chunks match
        if status["chunks_count"] != status["index_size"]:
            status["status"] = "warning"
            status["message"] = f"Mismatch between chunks ({status['chunks_count']}) and index size ({status['index_size']})"
            
        return status

    except Exception as e:
        logging.error(f"Index verification failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }

