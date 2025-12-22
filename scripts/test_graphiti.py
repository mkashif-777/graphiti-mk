from graphiti_core import Graphiti
from graphiti.storage.neo4j import Neo4jStorage

storage = Neo4jStorage(
    uri="bolt://neo4j-graphiti:7687",
    user="neo4j",
    password="test1234",
)

g = Graphiti(storage=storage)

# import asyncio
# from graphiti_core import Graphiti

# async def main():
#     g = Graphiti()  # no neo4j_* arguments
#     await g.initialize()

#     print("Graphiti initialized successfully")

# if __name__ == "__main__":
#     asyncio.run(main())
