import asyncio
from datetime import datetime
from graphiti_core import Graphiti

async def process_whatsapp_history(whatsapp_records):
    # Update with your actual Neo4j/FalkorDB credentials
    graphiti = Graphiti("bolt://localhost:7687", "neo4j", "test1234")
    
    try:
        for record in whatsapp_records:
            msg_time = datetime.fromisoformat(record['timestamp'])
            
            # In the current Graphiti API, 'name' is often the content field 
            # and 'source' is the metadata origin.
            await graphiti.add_episode(
                name=record['message_text'], 
                reference_time=msg_time,
                source="WhatsApp"
            )
            print(f"Successfully indexed message from {msg_time}")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        # If 'name' fails, it might be 'body'. Let's avoid guessing 
        # and use the most direct structure.
    finally:
        await graphiti.close()

data = [
    {"timestamp": "2025-10-01T10:00:00", "sender": "Ali", "message_text": "I am starting a new job at Google today."},
    {"timestamp": "2025-12-25T15:30:00", "sender": "Ali", "message_text": "I just quit Google to start my own startup."}
]

if __name__ == "__main__":
    asyncio.run(process_whatsapp_history(data))