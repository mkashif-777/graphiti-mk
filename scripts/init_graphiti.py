# init_graphiti.py
import asyncio
from graphiti_core import Graphiti

async def main():
    client = Graphiti(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test1234",
        neo4j_database="neo4j",
        openai_base_url="http://69.48.159.10:30000/",
        openai_api_key="unused_local",
        embedding_base_url="http://69.48.159.10:30001/",
    )
    await client.build_indices_and_constraints(delete_existing=False)
    print("✅ Graphiti indices and constraints created.")
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
