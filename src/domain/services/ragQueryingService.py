import os
import json
import logging
import faiss
import numpy as np
import re
import openai
from typing import List, Dict, Any, Optional
from pathlib import Path

# Configure OpenAI settings
openai.verify_ssl_certs = False
EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_SIMILARITY_THRESHOLD = 0.5

def load_rag_data():
    """Load RAG index and metadata."""
    try:
        index_path = Path("index.faiss")
        chunks_path = Path("chunks.json")
        
        if not index_path.exists() or not chunks_path.exists():
            logging.error("Missing RAG data files")
            return None, None
            
        # Load FAISS index
        index = faiss.read_index(str(index_path))
        
        # Load chunk metadata
        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunk_metadata = json.load(f)
            
        return index, chunk_metadata
    except Exception as e:
        logging.error(f"Error loading RAG data: {e}")
        return None, None

def get_embedding(text: str) -> np.ndarray:
    """Get embedding for text."""
    try:
        # Clean and normalize text for better embedding quality
        text = preprocess_text_for_embedding(text)
        
        response = openai.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return np.array(response.data[0].embedding, dtype="float32")
    except Exception as e:
        logging.error(f"Error getting embedding: {e}")
        raise

def preprocess_text_for_embedding(text: str) -> str:
    """Clean and normalize text for better embedding quality."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Convert to lowercase for consistency
    text = text.lower()
    
    # Remove special characters that don't add semantic value
    text = re.sub(r'[^\w\s.,?!;:()\[\]{}\'"@#$%^&*=+-]', '', text)
    
    return text

def preprocess_query(query: str) -> str:
    """Preprocess query to improve matching."""
    # Basic preprocessing
    query = query.lower().strip()
    
    # Expand common variations
    replacements = {
        "hours": ["schedule", "times", "open", "closing", "close", "opens", "closes"],
        "pool": ["swimming", "swim", "aquatic", "pools"],
        "today": ["now", "current", "currently"],
        "tomorrow": ["next day"],
        "weekend": ["saturday", "sunday", "weekends"],
        "morning": ["am", "a.m.", "early"],
        "evening": ["pm", "p.m.", "night", "late"]
    }
    
    expanded_terms = []
    words = query.split()
    
    for word in words:
        expanded_terms.append(word)
        
        # Add common variations
        for key, variations in replacements.items():
            if word in variations and key not in expanded_terms:
                expanded_terms.append(key)
    
    expanded_query = " ".join(expanded_terms)
    logging.debug(f"Original query: '{query}' → Expanded: '{expanded_query}'")
    return expanded_query

def rerank_results(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rerank results based on semantic relevance and position."""
    if not results:
        return []
        
    # Find consecutive chunks from the same source
    sources = {}
    for result in results:
        source = result.get('source', '')
        position = result.get('position', {})
        if source not in sources:
            sources[source] = []
        sources[source].append(result)
    
    # Boost score for chunks that have neighbors also returned
    for source, chunks in sources.items():
        if len(chunks) > 1:
            # Sort by position index
            chunks.sort(key=lambda x: x.get('position', {}).get('index', 0))
            
            # Identify consecutive chunks
            for i in range(len(chunks) - 1):
                curr_pos = chunks[i].get('position', {}).get('index', -1)
                next_pos = chunks[i+1].get('position', {}).get('index', -1)
                
                # If consecutive, boost both
                if next_pos - curr_pos == 1:
                    chunks[i]['similarity'] = min(1.0, chunks[i]['similarity'] * 1.05)
                    chunks[i+1]['similarity'] = min(1.0, chunks[i+1]['similarity'] * 1.05)
    
    # Flatten and sort by similarity
    reranked = [item for sublist in sources.values() for item in sublist]
    reranked.sort(key=lambda x: x['similarity'], reverse=True)
    
    return reranked

def combine_relevant_chunks(results: List[Dict[str, Any]], max_chunks: int = 3) -> List[Dict[str, Any]]:
    """Combine chunks from the same source that are close to each other."""
    if not results or len(results) <= 1:
        return results
        
    # Group by source
    by_source = {}
    for result in results:
        source = result.get('source', '')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(result)
    
    # Process each source
    combined_results = []
    for source, chunks in by_source.items():
        # Sort by position
        chunks.sort(key=lambda x: x.get('position', {}).get('index', 0))
        
        # Combine consecutive chunks
        i = 0
        while i < len(chunks):
            combined_chunk = {**chunks[i]}  # Copy the first chunk
            
            # Check if there are consecutive chunks
            j = i + 1
            while j < len(chunks):
                curr_pos = chunks[i].get('position', {}).get('index', -1)
                next_pos = chunks[j].get('position', {}).get('index', -1)
                
                # If consecutive or very close, combine
                if 0 <= next_pos - curr_pos <= 2:
                    # Merge text
                    combined_chunk['text'] = combined_chunk['text'] + "\n\n" + chunks[j]['text']
                    # Take the higher similarity score
                    combined_chunk['similarity'] = max(combined_chunk.get('similarity', 0), 
                                                  chunks[j].get('similarity', 0))
                    # Update combined chunk ID to show range
                    combined_chunk['chunk_id'] = f"{combined_chunk['chunk_id']}-{chunks[j]['chunk_id']}"
                    # Update position
                    combined_chunk['position'] = {
                        'index': min(combined_chunk['position']['index'], chunks[j]['position']['index']),
                        'total': combined_chunk['position']['total'],
                        'is_first': combined_chunk['position']['is_first'] or chunks[j]['position']['is_first'],
                        'is_last': combined_chunk['position']['is_last'] or chunks[j]['position']['is_last']
                    }
                    j += 1
                else:
                    break
            
            combined_results.append(combined_chunk)
            i = j
    
    # Sort by similarity score and return top max_chunks
    combined_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    return combined_results[:max_chunks]

def query_rag(query: str, k: int = 5, threshold: float = DEFAULT_SIMILARITY_THRESHOLD, 
             combine_chunks: bool = True) -> List[Dict]:
    """
    Query the RAG system to find relevant chunks.
    
    Args:
        query: The user's question
        k: Number of results to return
        threshold: Similarity threshold (0-1)
        combine_chunks: Whether to combine relevant consecutive chunks
        
    Returns:
        List of relevant chunks with metadata
    """
    try:
        # Preprocess the query
        processed_query = preprocess_query(query)
        
        # Load data
        index, chunk_metadata = load_rag_data()
        if not index or not chunk_metadata:
            logging.error("Failed to load RAG data")
            return []
        
        # Get query embedding
        query_embedding = get_embedding(processed_query)
        
        # Get more candidates than needed for reranking
        search_k = min(k * 3, len(chunk_metadata))
        distances, indices = index.search(query_embedding.reshape(1, -1), search_k)
        
        # Process results with threshold filtering
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(chunk_metadata):
                continue
                
            # Convert distance to similarity (0-1)
            similarity = 1 - (dist / 2)
            
            # Only consider results above threshold
            if similarity >= threshold:
                chunk = {**chunk_metadata[idx]}  # Copy to avoid modifying original
                chunk['similarity'] = float(similarity)
                results.append(chunk)
        
        # Rerank based on context
        reranked_results = rerank_results(query, results)
        
        # Optionally combine relevant chunks
        if combine_chunks and reranked_results:
            final_results = combine_relevant_chunks(reranked_results, k)
        else:
            # Just take top k
            final_results = reranked_results[:k]
        
        logging.info(f"Found {len(final_results)} relevant results for query: '{query}'")
        
        return final_results
        
    except Exception as e:
        logging.error(f"RAG query error: {e}", exc_info=True)
        return []

def debug_query(query: str):
    """Debug a specific RAG query with detailed logging"""
    try:
        logging.info(f"DEBUG QUERY: '{query}'")
        
        index, chunk_metadata = load_rag_data()
        if not index or not chunk_metadata:
            logging.error("Failed to load RAG data")
            return
            
        # Show both original and preprocessed query
        processed_query = preprocess_query(query)
        logging.info(f"Original query: '{query}'")
        logging.info(f"Processed query: '{processed_query}'")
        
        query_embedding = get_embedding(processed_query)
        
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
                
                # Format the match info
                match_marker = "PASS" if similarity >= threshold else "FAIL"
                match_num = i + 1
                
                logging.info(f"Match {match_num}:")
                logging.info(f"  Similarity: {similarity:.3f} [{match_marker}]")
                logging.info(f"  Source: {chunk.get('source', 'unknown')}")
                preview = chunk.get('text', '')[:150]
                logging.info(f"  Text: {preview}...")
                
    except Exception as e:
        logging.error(f"Debug query error: {e}", exc_info=True)

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
        
        # Organize chunks by source
        sources = {}
        for chunk in chunk_metadata:
            source = chunk.get("source", "unknown")
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
            
        # Add source distribution
        status["sources"] = sources
        
        # Add sample chunks
        if chunk_metadata:
            for chunk in chunk_metadata[:3]:  # Show first 3 chunks
                status["chunks"].append({
                    "source": chunk.get("source", "unknown"),
                    "preview": chunk.get("text", "")[:150],
                    "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD
                })
        
        # Log without emojis
        logging.info("RAG System Status:")
        logging.info(f"  Index size: {status['index_size']} vectors")
        logging.info(f"  Chunks count: {status['chunks_count']}")
        logging.info(f"  Sources: {len(sources)}")
        
        return status
        
    except Exception as e:
        logging.error(f"Error checking RAG status: {e}")
        return {
            "status": "error",
            "message": str(e)
        }