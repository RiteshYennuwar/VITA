from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from pinecone import Index
from config import EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION
from .utils import normalize_embeddings

# Initialize the embedding model
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

def create_embeddings(text_chunks: List[str]) -> List[List[float]]:
    embeddings = embedding_model.encode(text_chunks)
    normalized_embeddings = normalize_embeddings(embeddings)
    return [embedding.tolist() for embedding in normalized_embeddings]

def store_embeddings_in_pinecone(namespace: str,index: Index, text_chunks: List[str]) -> None:
    embeddings = create_embeddings(text_chunks)
    vectors = [
        {
            "id": str(i), 
            "values": embedding, 
            "metadata": {"text": chunk}
        } 
        for i, (embedding, chunk) in enumerate(zip(embeddings, text_chunks))
    ]
    index.upsert(vectors=vectors, namespace=namespace)

def get_embedding(text: str) -> List[float]:
    embedding = embedding_model.encode([text])[0]
    normalized_embedding = normalize_embeddings([embedding])[0]
    return normalized_embedding.tolist()

def batch_embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = create_embeddings(batch)
        all_embeddings.extend(batch_embeddings)
    return all_embeddings