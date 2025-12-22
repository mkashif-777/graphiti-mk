from neo4j import GraphDatabase
import json

uri = "bolt://69.48.159.10:7687"   # use bolt://neo4j-graphiti:7687 inside container network
driver = GraphDatabase.driver(uri, auth=("neo4j","test1234"))

def upsert(tx, acc_meta, contact, msg):
    tx.run("""
    MERGE (acc:WAAccount {phone_number_id: $phone_number_id})
    SET acc.display_phone_number = $display_phone_number
    MERGE (contact:Contact {wa_id: $wa_id})
    SET contact.name = $name
    MERGE (acc)-[:HAS_CONTACT]->(contact)
    MERGE (m:Message {message_id: $msg_id})
    SET m.timestamp = $timestamp, m.type = $type, m.body = $body
    MERGE (contact)-[:SENT]->(m)
    MERGE (m)-[:SOURCE_ACCOUNT]->(acc)
    """, phone_number_id=acc_meta["phone_number_id"],
         display_phone_number=acc_meta["display_phone_number"],
         wa_id=contact["wa_id"],
         name=contact["profile"].get("name"),
         msg_id=msg["id"],
         timestamp=int(msg["timestamp"]),
         type=msg.get("type"),
         body=(msg.get("text") or {}).get("body","")
    )

with open("/home/ahoy/muhammad_kashif/graphiti/scripts/9/augmented.json") as f:
    data = json.load(f)

with driver.session() as sess:
    for root in data:
        for entry in root.get("entry", []):
            for change in entry.get("changes", []):
                v = change.get("value", {})
                acc_meta = v.get("metadata", {})
                for c in v.get("contacts", []):
                    for msg in v.get("messages", []):
                        sess.execute_write(upsert, acc_meta, c, msg)
driver.close()
