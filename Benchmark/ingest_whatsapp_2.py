import json
import requests
from neo4j import GraphDatabase
from typing import List

# -----------------------------
# CONFIG
# -----------------------------
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "test1234"

# EMBEDDING_URL = "http://69.48.159.10:30001/v1/embeddings"
EMBEDDING_URL = "http://localhost:30001/v1/embeddings"
EMBEDDING_MODEL = "Nexus-bge-m3-opensearch-embeddings"

INPUT_FILE = "whatsapp_synthetic_events.jsonl"

# -----------------------------
# EMBEDDING
# -----------------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    r = requests.post(
        EMBEDDING_URL,
        headers={"Content-Type": "application/json"},
        json={
            "model": EMBEDDING_MODEL,
            "input": texts
        },
        timeout=60
    )
    r.raise_for_status()
    vectors = [d["embedding"] for d in r.json()["data"]]
    # assert len(vectors[0]) == 768, "Embedding dimension mismatch"
    EMBED_DIM = len(vectors[0])
    print(f"Embedding dimension detected: {EMBED_DIM}")
    return vectors

# -----------------------------
# NEO4J WRITE
# -----------------------------
def write_batch(tx, batch):
    tx.run(
        """
        UNWIND $batch AS row

        MERGE (g:Group {id: row.group_id})

        MERGE (u:User {id: row.user_id})
        SET u.name = row.user_name

        MERGE (m:Message {id: row.message_id})
        SET m.body = row.body,
            m.timestamp = row.timestamp,
            m.embedding = row.embedding

        MERGE (u)-[:SENT]->(m)
        MERGE (m)-[:IN_GROUP]->(g)

        FOREACH (_ IN CASE WHEN row.parent_id IS NULL THEN [] ELSE [1] END |
            MERGE (p:Message {id: row.parent_id})
            MERGE (p)-[:REPLIED_TO]->(m)
        )
        """,
        batch=batch
    )

# -----------------------------
# MAIN INGESTION
# -----------------------------
def main():
    payload = []
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                payload.append(json.loads(line))

    records = []

    for obj in payload:
        for entry in obj.get("entry", []):
            group_id = entry["id"]

            for change in entry.get("changes", []):
                value = change["value"]

                contacts = {
                    c["wa_id"]: c["profile"]["name"]
                    for c in value.get("contacts", [])
                }

                for msg in value.get("messages", []):
                    # Handle Text
                    if msg["type"] == "text":
                        body = msg.get("text", {}).get("body")
                    
                    # Handle Images
                    elif msg["type"] == "image":
                        caption = msg.get("image", {}).get("caption", "")
                        body = f"[Image] {caption}".strip()
                    
                    # Handle Documents
                    elif msg["type"] == "document":
                        doc = msg.get("document", {})
                        filename = doc.get("filename", "unknown_file")
                        caption = doc.get("caption", "")
                        body = f"[Document: {filename}] {caption}".strip()

                    # Handle Reactions (skip for now as they are relationships, not content nodes usually)
                    # or other types
                    else:
                        continue

                    if not body:
                        continue

                    records.append({
                        "group_id": group_id,
                        "user_id": msg["from"],
                        "user_name": contacts.get(msg["from"], "Unknown"),
                        "message_id": msg["id"],
                        "parent_id": msg.get("context", {}).get("id") if "context" in msg else None, # Fix parent_id extraction
                        "timestamp": int(msg["timestamp"]),
                        "body": body
                    })

    # -----------------------------
    # EMBEDDING
    # -----------------------------
    texts = [r["body"] for r in records]
    embeddings = embed_texts(texts)

    for r, e in zip(records, embeddings):
        r["embedding"] = e

    # -----------------------------
    # WRITE TO NEO4J
    # -----------------------------
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    BATCH_SIZE = 100
    with driver.session() as session:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            session.execute_write(write_batch, batch)

    driver.close()
    print(f"Ingested {len(records)} messages successfully.")

# -----------------------------
if __name__ == "__main__":
    main()
