from pinecone import Pinecone, ServerlessSpec, Index
from config import PINECONE_API_KEY, PINECONE_ENVIRONMENT, PINECONE_INDEX_NAME, EMBEDDING_DIMENSION

def initialize_pinecone(api_key: str = PINECONE_API_KEY, environment: str = PINECONE_ENVIRONMENT) -> Index:
    pinecone = Pinecone(api_key=api_key, environment=environment)
    
    # Check if the index already exists, if not create it
    if PINECONE_INDEX_NAME not in pinecone.list_indexes().names():
        pinecone.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    
    return pinecone.Index(PINECONE_INDEX_NAME)

def delete_all_vectors(index: Index) -> None:
    index.delete(delete_all=True, namespace="document-namespace")

def get_index_stats(index: Index) -> dict:
    return index.describe_index_stats()

def update_vector(index: Index, id: str, values: list, metadata: dict = None) -> None:
    index.upsert(vectors=[{"id": id, "values": values, "metadata": metadata}], namespace="document-namespace")

def delete_vector(index: Index, id: str) -> None:
    index.delete(ids=[id], namespace="document-namespace")