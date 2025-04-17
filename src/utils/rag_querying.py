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

def query_rag(query: str, k: int = 3, threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Query the RAG system with a natural language question
    
    Args:
        query: The natural language query
        k: Number of results to return
        threshold: Similarity threshold (0-1) for filtering results
        
    Returns:
        List of relevant chunks with metadata and similarity scores
    """
    try:
        # Load index and metadata
        index, chunk_metadata = load_rag_data()
        if not index or not chunk_metadata:
            raise ValueError("Failed to load RAG data")
            
        # Get query embedding
        query_embedding = get_embedding(query)
        query_embedding = query_embedding.reshape(1, -1)
        
        # Search index
        distances, indices = index.search(query_embedding, k)
        
        # Process results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0 or idx >= len(chunk_metadata):
                continue
                
            # Convert distance to similarity score (0-1)
            similarity = 1 - (dist / 2)  # Assuming L2 distance
            
            if similarity < threshold:
                continue
                
            result = {
                **chunk_metadata[idx],
                "similarity": float(similarity)
            }
            results.append(result)
            
        return results
        
    except Exception as e:
        logging.error(f"Error querying RAG: {e}")
        return []