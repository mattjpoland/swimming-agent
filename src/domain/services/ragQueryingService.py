import faiss
import json
import openai
import numpy as np
import logging
from typing import List, Dict, Any, Optional

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

def load_rag_data(faiss_path: str = "index.faiss", meta_path: str = "chunks.json"):
    """Load the FAISS index and metadata for querying"""
    try:
        # Load FAISS index
        index = faiss.read_index(faiss_path)
        
        # Load metadata
        with open(meta_path, 'r', encoding='utf-8') as f:
            chunk_metadata = json.load(f)
            
        return index, chunk_metadata
    except Exception as e:
        logging.error(f"Error loading RAG data: {e}")
        return None, None

def get_embedding(text: str) -> np.ndarray:
    """Get embedding for a single text string"""
    response = openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return np.array(response.data[0].embedding, dtype='float32')

def preprocess_query(query: str) -> str:
    """Preprocess query to improve matching"""
    query = query.lower()
    
    # Expand common variations and context
    replacements = {
        "hours": ["schedule", "times", "open", "closing", "close", "opens", "closes"],
        "pool": ["swimming", "swim", "aquatic", "pools"],
        "today": ["now", "current", "currently"],
        "tomorrow": ["next day"],
        "weekend": ["saturday", "sunday", "weekends"],
        "morning": ["am", "a.m.", "early"],
        "evening": ["pm", "p.m.", "night", "late"]
    }
    
    # Expand query with common variations
    expanded_terms = []
    words = query.split()
    
    for i, word in enumerate(words):
        expanded_terms.append(word)
        
        # Add common variations
        for key, variations in replacements.items():
            if word in variations:
                expanded_terms.append(key)
                
        # Handle time-related phrases
        if word in ["time", "when"]:
            expanded_terms.extend(["hours", "schedule"])
            
    return " ".join(expanded_terms)

def query_rag(query: str, k: int = 3, threshold: float = 0.5):
    """Query the RAG system with preprocessing"""
    try:
        # Enhance query preprocessing
        processed_query = preprocess_query(query)
        logging.info(f"Original query: '{query}'")
        logging.info(f"Processed query: '{processed_query}'")
        
        index, chunk_metadata = load_rag_data()
        if not index or not chunk_metadata:
            return []
        
        # Get query embedding
        query_embedding = get_embedding(processed_query)
        
        # Use k+2 to get more candidates then filter
        distances, indices = index.search(query_embedding.reshape(1, -1), k+2)
        
        # Process results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(chunk_metadata):
                continue
                
            similarity = 1 - (dist / 2)
            
            # Use 0.5 threshold - based on debug results
            if similarity >= 0.5:
                chunk = chunk_metadata[idx]
                results.append({
                    **chunk,
                    "similarity": float(similarity)
                })
        
        # Sort by similarity and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]
        
    except Exception as e:
        logging.error(f"RAG query error: {e}", exc_info=True)
        return []

def debug_rag_status():
    """Print detailed RAG system status for debugging"""
    try:
        index, chunk_metadata = load_rag_data()
        
        if not index or not chunk_metadata:
            logging.error("Failed to load RAG data")
            return {
                "status": "error",
                "message": "Failed to load RAG data"
            }
            
        status = {
            "status": "ok",
            "index_size": index.ntotal if index else 0,
            "chunks_count": len(chunk_metadata) if chunk_metadata else 0,
            "chunks": []
        }
        
        # Add sample chunks
        if chunk_metadata:
            for chunk in chunk_metadata[:3]:  # Show first 3 chunks
                status["chunks"].append({
                    "source": chunk.get("source", "unknown"),
                    "preview": chunk.get("text", "")[:150],
                    "similarity_threshold": 0.5  # Current threshold
                })
        
        # Log without emojis
        logging.info("RAG System Status:")
        logging.info(f"  Index size: {status['index_size']} vectors")
        logging.info(f"  Chunks count: {status['chunks_count']}")
        
        return status
        
    except Exception as e:
        logging.error(f"Error checking RAG status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

def debug_query(query: str):
    """Debug a specific RAG query with detailed logging"""
    try:
        logging.info(f"DEBUG QUERY: '{query}'")
        
        index, chunk_metadata = load_rag_data()
        if not index or not chunk_metadata:
            logging.error("Failed to load RAG data")
            return
            
        query_embedding = get_embedding(query)
        
        # Test different thresholds
        for threshold in [0.3, 0.5, 0.7]:
            logging.info(f"Testing threshold: {threshold}")
            
            distances, indices = index.search(query_embedding.reshape(1, -1), k=5)
            
            # Show all potential matches
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < 0 or idx >= len(chunk_metadata):
                    continue
                    
                similarity = 1 - (dist / 2)
                chunk = chunk_metadata[idx]
                
                # Format the match info without nested parentheses in f-strings
                match_marker = "PASS" if similarity >= threshold else "FAIL"
                match_num = i + 1
                
                logging.info(f"Match {match_num}:")
                logging.info(f"  Similarity: {similarity:.3f} [{match_marker}]")
                logging.info(f"  Source: {chunk.get('source', 'unknown')}")
                preview = chunk.get('text', '')[:150]
                logging.info(f"  Text: {preview}...")
                
    except Exception as e:
        logging.error(f"Debug query error: {e}", exc_info=True)