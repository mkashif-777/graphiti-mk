

from fastapi import FastAPI
from pydantic import BaseModel
import requests
from neo4j import GraphDatabase

app = FastAPI()

# ---- CONFIG ----
EMBEDDING_URL = "http://69.48.159.10:30001/v1/embeddings"
LLM_URL = "http://69.48.159.10:30000/v1/chat/completions"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "test1234")

driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

# ---- REQUEST SCHEMA ----
class QueryRequest(BaseModel):
    query: str

# ---- HELPERS ----
# def embed_query(text: str):
#     r = requests.post(
#         EMBEDDING_URL,
#         json={"input": text}
#     )
#     r.raise_for_status()
    # payload = r.json()

    # adapt once your embedding server is confirmed
    # return payload["embedding"]

    # resp = r.json()

    # embedding = resp["data"][0]["embedding"]
    # return embedding

def embed_query(text: str) -> list[float]:
    r = requests.post(
        "http://69.48.159.10:30001/v1/embeddings",
        headers={"Content-Type": "application/json"},
        json={
            "model": "Nexus-bge-m3-opensearch-embeddings",
            "input": text
        },
        timeout=30
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]

def retrieve_graph_context(embedding):
    cypher = """
    CALL db.index.vector.queryNodes(
      'message_embedding_index',
      5,
      $embedding
    )
    YIELD node, score
    MATCH (node:Message {source: $source})
    RETURN node.body AS main,
           collect(related.body) AS related
    """

    with driver.session() as session:
        result = session.run(cypher, embedding=embedding)
        return [r.data() for r in result]

def build_prompt(context, query):
    lines = []
    for row in context:
        lines.append(row["main"])
        lines.extend(row["related"])

    context_text = "\n".join(set(lines))

    return f"""
You are answering based on WhatsApp conversations.

Context:
{context_text}

Question:
{query}

Answer concisely and only using the context.
"""

def call_llm(prompt: str):
    r = requests.post(
        LLM_URL,
        json={
            "model": "llama-3.1-70b",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

# ---- API ENDPOINT ----
@app.post("/query")
def query_graph(req: QueryRequest):
    embedding = embed_query(req.query)
    context = retrieve_graph_context(embedding)
    prompt = build_prompt(context, req.query)
    answer = call_llm(prompt)

    return {
        "query": req.query,
        "answer": answer
    }
