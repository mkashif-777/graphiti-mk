import json
import requests
from neo4j import GraphDatabase

def extract_events(payload):
    events = []
    for record in payload:
        for entry in record["entry"]:
            cid = entry["id"]
            for change in entry["changes"]:
                value = change["value"]

                contacts = {
                    c["wa_id"]: c["profile"]["name"]
                    for c in value.get("contacts", [])
                }

                for msg in value.get("messages", []):
                    events.append({
                        "conversation_id": cid,
                        "message_id": msg["id"],
                        "from": msg["from"],
                        "timestamp": int(msg["timestamp"]),
                        "text": msg["text"]["body"],
                        "parent_id": msg.get("parent_message_id"),
                        "contacts": contacts
                    })
    return events

def embed_texts(texts, batch_size=64):
    embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        r = requests.post(
            "http://69.48.159.10:30001/v1/embeddings",
            json={"input": batch}
        )

        r.raise_for_status()
        payload = r.json()

        # Handle common formats
        if "data" in payload:
            embeddings.extend([d["embedding"] for d in payload["data"]])

        elif "embeddings" in payload:
            embeddings.extend(payload["embeddings"])

        elif "embedding" in payload:
            embeddings.append(payload["embedding"])

        else:
            raise ValueError(f"Unknown embedding response format: {payload}")

    return embeddings


def write_batch(tx, event):
    for wa_id, name in event["contacts"].items():
        tx.run("""
        MERGE (u:User {wa_id: $wa_id})
        SET u.name = $name
        """, wa_id=wa_id, name=name)

    tx.run("""
    MERGE (c:Conversation {id: $cid})
    """, cid=event["conversation_id"])

    tx.run("""
    MERGE (m:Message {id: $id})
    SET m.body = $body,
        m.timestamp = $ts,
        m.embedding = $embedding
    WITH m
    MATCH (u:User {wa_id: $from})
    MERGE (u)-[:SENT]->(m)
    WITH m
    MATCH (c:Conversation {id: $cid})
    MERGE (c)-[:HAS_MESSAGE]->(m)
    """, {
        "id": event["message_id"],
        "body": event["text"],
        "ts": event["timestamp"],
        "embedding": event["embedding"],
        "from": event["from"],
        "cid": event["conversation_id"]
    })

    if event["parent_id"]:
        tx.run("""
        MATCH (child:Message {id: $child})
        MATCH (parent:Message {id: $parent})
        MERGE (child)-[:REPLY_TO]->(parent)
        """, child=event["message_id"], parent=event["parent_id"])


with open("whatsapp_messages.json") as f:
    raw_payload = json.load(f)

events = extract_events(raw_payload)

texts = [e["text"] for e in events]
vectors = embed_texts(texts)

for e, v in zip(events, vectors):
    e["embedding"] = v

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "test1234")
)

with driver.session() as session:
    for event in events:
        session.execute_write(write_batch, event)
