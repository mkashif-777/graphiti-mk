# ingest.py
import json
from adapters.whatsapp import WhatsAppAdapter
from embedding import embed_texts
from graph_writer import GraphWriter

adapter = WhatsAppAdapter()
# To switch sources
# adapter = SlackAdapter()
# adapter = TeamsAdapter()
# adapter = GmailAdapter()

with open("whatsapp_messages.json") as f:
    payload = json.load(f)

events = list(adapter.parse(payload))

embeddings = embed_texts([e.content for e in events])

for e, v in zip(events, embeddings):
    e.embedding = v

writer = GraphWriter(
    uri="bolt://localhost:7687",
    auth=("neo4j", "test1234")
)

writer.ingest(events)
