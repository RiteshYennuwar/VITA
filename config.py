import os
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "be9c0ded-e23a-447e-a3d8-459804738105")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
PINECONE_INDEX_NAME = "vita-index"

COHERE_API_KEY = os.getenv("COHERE_API_KEY", "your_cohere_api_key_here")

EMBEDDING_MODEL_NAME = "all-mpnet-base-v2"
EMBEDDING_DIMENSION = 768

MAX_CHUNK_SIZE = 512

TOP_K_RESULTS = 5

MAX_TOKENS = 300
GENERATION_MODEL = "c4ai-aya-23-35b"