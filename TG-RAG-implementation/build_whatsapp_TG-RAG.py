import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from datetime import datetime

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
debug_mode = os.getenv("TG_RAG_DEBUG", "false").lower() == "true"
log_level = logging.DEBUG if debug_mode else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(levelname)s - %(message)s"
)

if debug_mode:
    print("Debug mode enabled")

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------
load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from tgrag import create_temporal_graphrag_from_config

# -----------------------------------------------------------------------------
# WhatsApp Loader
# -----------------------------------------------------------------------------
def load_whatsapp_messages(path: Path) -> List[Dict]:
    if not path.exists():
        raise FileNotFoundError(f"WhatsApp file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []

    for obj in data:
        for entry in obj.get("entry", []):
            group_id = entry.get("id", "unknown-group")

            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                contact_map = {
                    c["wa_id"]: c.get("profile", {}).get("name", c["wa_id"])
                    for c in contacts
                }

                for msg in messages:
                    text = msg.get("text", {}).get("body")
                    if not text:
                        continue

                    sender_id = msg.get("from")
                    sender_name = contact_map.get(sender_id, sender_id)

                    ts = int(msg.get("timestamp", 0))
                    timestamp = datetime.utcfromtimestamp(ts).isoformat() if ts else None

                    documents.append({
                        "title": f"WhatsApp | {group_id} | {sender_name}",
                        "doc": text,
                        "timestamp": timestamp,
                        "metadata": {
                            "group_id": group_id,
                            "message_id": msg.get("id"),
                            "sender_id": sender_id,
                            "sender_name": sender_name,
                            "parent_message_id": msg.get("parent_message_id"),
                            "child_message_ids": msg.get("child_message_ids", [])
                        }
                    })

    logging.info(f"Loaded {len(documents)} WhatsApp messages")
    return documents

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Build Temporal GraphRAG knowledge graph from WhatsApp corpus"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to GraphRAG config.yaml"
    )

    parser.add_argument(
        "--whatsapp_path",
        type=str,
        default="whatsapp_messages.json",
        help="Path to WhatsApp messages JSON file"
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Override working_dir from config"
    )

    args = parser.parse_args()

    override_config = {}
    if args.output_dir:
        override_config["working_dir"] = args.output_dir

    print("=" * 60)
    print("Initializing Temporal GraphRAG")
    print("=" * 60)

    graph_rag = create_temporal_graphrag_from_config(
        config_path=args.config,
        config_type="building",
        override_config=override_config if override_config else None
    )

    print("TemporalGraphRAG initialized")
    print(f"Working directory: {graph_rag.working_dir}")
    print(f"Chunk size: {graph_rag.chunk_token_size}")
    print(f"Chunk overlap: {graph_rag.chunk_overlap_token_size}")

    # -------------------------------------------------------------------------
    # Load WhatsApp corpus
    # -------------------------------------------------------------------------
    whatsapp_path = Path(args.whatsapp_path)
    documents = load_whatsapp_messages(whatsapp_path)

    if not documents:
        raise RuntimeError("No WhatsApp messages found")

    # -------------------------------------------------------------------------
    # Insert into GraphRAG
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("Building Temporal Knowledge Graph")
    print("=" * 60)
    print(f"Inserting {len(documents)} messages")

    graph_rag.insert(documents)

    print("Graph build completed successfully")

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    try:
        from tgrag.src.llm.client import get_client_manager
        import asyncio

        client_manager = get_client_manager()
        asyncio.run(client_manager.close_clients())
    except Exception:
        pass

    print("=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"Messages processed: {len(documents)}")
    print(f"Graph stored at: {Path(graph_rag.working_dir).absolute()}")
    print(f"Config used: {args.config}")
    print("=" * 60)

# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
