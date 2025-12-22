# ingest_whatsapp_bulk.py
import asyncio
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from datetime import datetime, timezone

# Example transform function (adapt to your WhatsApp JSON schema)
def make_episode_from_message(msg):
    # msg should contain: id, timestamp, sender, text, metadata...
    return {
        "name": f"whatsapp_msg_{msg['id']}",
        "episode_body": msg.get("text", ""),
        "source": EpisodeType.message,       # Graphiti enum for message episodes
        "source_description": "whatsapp_business_api",
        "reference_time": datetime.fromtimestamp(float(msg['timestamp']), tz=timezone.utc),
        # optional: include any metadata you want
        "metadata": {
            "sender": msg.get("from"),
            "message_id": msg.get("id")
        }
    }

async def main():
    g = Graphiti(
        neo4j_uri="bolt://neo4j:7687",
        neo4j_user="neo4j",
        neo4j_password="test1234",
        neo4j_database="graphiti",
        openai_base_url="http://69.48.159.10:30000/",
        openai_api_key="dummy_local_key",
        embedding_base_url="http://69.48.159.10:30001/",
    )

    # load your whatsapp JSON array from file
    import json
    with open("whatsapp_messages.json") as f:
        messages = json.load(f)

    bulk_episodes = [make_episode_from_message(m) for m in messages]

    # recommended: chunk bulk uploads to not overload the system
    chunk_size = 200
    for i in range(0, len(bulk_episodes), chunk_size):
        chunk = bulk_episodes[i:i+chunk_size]
        result = await g.add_episode_bulk(chunk)
        print(f"Uploaded chunk {i//chunk_size + 1}: {len(chunk)} episodes")

    await g.close()

if __name__ == "__main__":
    asyncio.run(main())
