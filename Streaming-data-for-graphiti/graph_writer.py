# graph_writer.py
from neo4j import GraphDatabase
from schemas import StreamEvent

class GraphWriter:

    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def write_event(self, tx, e: StreamEvent):
        tx.run("""
        MERGE (a:Actor {id: $actor_id})
        SET a.name = $actor_name
        """, actor_id=e.actor_id, actor_name=e.actor_name)

        tx.run("""
        MERGE (s:Stream {id: $stream_id, source: $source})
        """, stream_id=e.stream_id, source=e.source)

        tx.run("""
        MERGE (m:Message {id: $event_id})
        SET m.body = $content,
            m.timestamp = $timestamp,
            m.embedding = $embedding,
            m.source = $source
        WITH m
        MATCH (a:Actor {id: $actor_id})
        MERGE (a)-[:PRODUCED]->(m)
        WITH m
        MATCH (s:Stream {id: $stream_id})
        MERGE (s)-[:HAS_EVENT]->(m)
        """, {
            "event_id": e.event_id,
            "content": e.content,
            "timestamp": e.timestamp,
            "embedding": e.embedding,
            "actor_id": e.actor_id,
            "stream_id": e.stream_id,
            "source": e.source
        })

        if e.parent_event_id:
            tx.run("""
            MATCH (c:Message {id: $child})
            MATCH (p:Message {id: $parent})
            MERGE (c)-[:REPLIES_TO]->(p)
            """, child=e.event_id, parent=e.parent_event_id)

    def ingest(self, events):
        with self.driver.session() as session:
            for e in events:
                session.execute_write(self.write_event, e)
