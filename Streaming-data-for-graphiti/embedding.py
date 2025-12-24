# embedding.py
import requests

EMBEDDING_URL = "http://69.48.159.10:30001/v1/embeddings"

def embed_texts(texts, batch_size=64):
    embeddings = []

    for i in range(0, len(texts), batch_size):
        r = requests.post(
            EMBEDDING_URL,
            json={"input": texts[i:i+batch_size]},
            timeout=30
        )
        r.raise_for_status()
        embeddings.extend([d["embedding"] for d in r.json()["data"]])

    return embeddings
