import numpy as np
from typing import List

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    return embedding / np.linalg.norm(embedding)

def normalize_embeddings(embeddings: List[np.ndarray]) -> List[np.ndarray]:
    return [normalize_embedding(emb) for emb in embeddings]

def format_query(query: str, context: str) -> str:
    return f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"

def truncate_text(text: str, max_length: int = 1000) -> str:
    return text[:max_length] + "..." if len(text) > max_length else text