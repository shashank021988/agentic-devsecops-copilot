from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from langchain_openai import OpenAIEmbeddings
import uuid, os

COLLECTION = "runbooks"
embeddings = OpenAIEmbeddings()
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))


def index_runbook(title: str, content: str):
    try:
        qdrant.get_collection(COLLECTION)
    except Exception:
        qdrant.create_collection(COLLECTION, vectors_config=VectorParams(size=1536, distance=Distance.COSINE))
    vector = embeddings.embed_query(content)
    qdrant.upsert(collection_name=COLLECTION, points=[
        PointStruct(id=str(uuid.uuid4()), vector=vector, payload={"title": title, "content": content})
    ])


def search_runbooks(query: str, top_k: int = 3) -> list:
    vector = embeddings.embed_query(query)
    results = qdrant.search(collection_name=COLLECTION, query_vector=vector, limit=top_k)
    return [{"title": r.payload["title"], "content": r.payload["content"], "score": r.score} for r in results]
