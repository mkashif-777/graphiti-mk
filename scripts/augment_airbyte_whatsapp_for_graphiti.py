"""
augment_airbyte_whatsapp_for_graphiti.py

Augment a normalized Airbyte WhatsApp record and produce a single JSON file (not NDJSON)
that contains temporal events, nodes, and relationships ready to be imported into Neo4j
or used with Graphiti.

Usage examples:

# Single record
python augment_airbyte_whatsapp_for_graphiti.py \
  --input-record '{"id":"wamid.HBgMNTU...","from":"447700900001","to":"1234","text":"Hello, I need help","received_at":"1698361200"}' \
  --n 200 --out augmented_graphiti.json --seed 42

# Multiple seed records from file
python augment_airbyte_whatsapp_for_graphiti.py \
  --input-file seeds.json --n 100 --out augmented_graphiti.json

Output schema (top-level JSON):
{
  "events": [ ... ],
  "nodes": [ ... ],
  "relationships": [ ... ]
}
"""

from __future__ import annotations
import argparse
import json
import random
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

try:
    from faker import Faker
    _HAS_FAKER = True
    fake = Faker()
except Exception:
    _HAS_FAKER = False
    fake = None

# ---------- Configurable constants ----------
TYPO_PROB = 0.10
EMOJI_PROB = 0.25
IMAGE_PROB = 0.06
MAX_JITTER_DAYS = 7  # jitter timestamps +/- this many days
EMOJI_POOL = ["👋","🙂","😕","🤔","🙏","👍","🚚","📦","🔔"]
IMAGE_CAPTIONS = ["Receipt attached","Product photo","Screenshot"]
ABBREVS = {"please":["pls","plz"], "you":["u"], "thanks":["thx","ty"]}

# ---------- Helpers ----------
def now_unix() -> int:
    return int(time.time())

def jitter_timestamp(base_ts: int, max_days: int = MAX_JITTER_DAYS) -> int:
    # jitter by up to max_days (in seconds) in either direction
    jitter = random.randint(-max_days*86400, max_days*86400)
    new_ts = max(0, int(base_ts) + jitter)
    return new_ts

def iso_ts(unix_ts: int) -> str:
    return datetime.fromtimestamp(int(unix_ts), tz=timezone.utc).isoformat()

def random_phone(country_code: str = "44") -> str:
    # produce synthetic phone number string of digits (no plus)
    digits = ''.join(str(random.randint(0,9)) for _ in range(9))
    return country_code + digits

def small_typo(word: str) -> str:
    if len(word) <= 2:
        return word
    if random.random() < 0.5:
        i = random.randrange(0, len(word)-1)
        arr = list(word)
        arr[i], arr[i+1] = arr[i+1], arr[i]
        return "".join(arr)
    else:
        i = random.randrange(0, len(word))
        return word[:i] + word[i+1:]

def apply_typos(text: str, prob=TYPO_PROB) -> str:
    tokens = re.split(r"(\W+)", text)
    out = []
    for t in tokens:
        if re.match(r"^\w+$", t) and random.random() < prob:
            out.append(small_typo(t))
        else:
            out.append(t)
    return "".join(out)

def maybe_add_emoji(text: str) -> str:
    if random.random() < EMOJI_PROB:
        return text + " " + random.choice(EMOJI_POOL)
    return text

def apply_abbrevs(text: str) -> str:
    for full, subs in ABBREVS.items():
        pattern = re.compile(r"\b" + re.escape(full) + r"\b", flags=re.IGNORECASE)
        def repl(m):
            return random.choice(subs) if random.random() < 0.5 else m.group(0)
        text = pattern.sub(repl, text)
    return text

# ---------- Graph element creators ----------
def person_node_id(phone: str) -> str:
    # canonical node id for person based on phone
    return f"person_{phone}"

def message_node_id(msg_id: str) -> str:
    return f"message_{msg_id}"

def conversation_node_id(conv_id: str) -> str:
    return f"conversation_{conv_id}"

# ---------- Augmentation core ----------
def augment_one(seed: Dict[str, Any], idx: int, base_conv_id: Optional[str]=None) -> Dict[str, Any]:
    """
    Create a single augmented event dict (normalized record) derived from seed.
    Returns a dict with keys: id, from, to, text, received_at (unix int), message_type, conversation_id, reply_to (optional)
    """
    s = deepcopy(seed)
    # ensure numeric timestamp
    base_ts = int(s.get("received_at") or now_unix())
    ts = jitter_timestamp(base_ts)
    # id variant
    mid = f"{s.get('id','msg')}-{idx:06d}"
    # pseudonymize phone numbers; preserve rough country code if known
    from_num = s.get("from","")
    to_num = s.get("to","")
    def make_syn(num):
        if num and num.isdigit() and len(num) >= 3:
            # keep first 1-3 digits as country code
            cc = num[:2] if len(num) >= 10 else "1"
        else:
            cc = random.choice(["1","44","92","52","234"])
        return random_phone(cc)
    from_syn = make_syn(from_num)
    to_syn = make_syn(to_num)
    # message type
    if random.random() < IMAGE_PROB:
        mtype = "image"
        text = random.choice(IMAGE_CAPTIONS)
    else:
        mtype = "text"
        # decide how to diversify text
        t = s.get("text","")
        r = random.random()
        if r < 0.18:
            # paraphrase short template
            t = f"Hi, I need help with order #{random.randint(1000,9999)}"
        elif r < 0.38:
            t = apply_abbrevs(t)
            t = apply_typos(t, prob=TYPO_PROB + 0.04)
        else:
            if random.random() < 0.4:
                t += " " + random.choice(["Thanks","Please advise","Order " + str(random.randint(1000,9999))])
            t = apply_typos(t, prob=TYPO_PROB)
            t = maybe_add_emoji(t)
    # maybe reply_to to create reply graph (20% chance)
    reply_to = None
    if random.random() < 0.20:
        # create synthetic reply pointer to earlier message (simple heuristic)
        reply_to = f"{s.get('id','msg')}-{max(0, idx - random.randint(1,3)):06d}"
    conv_id = base_conv_id or f"conv-{random.randint(100000,999999)}"
    event = {
        "id": mid,
        "from": from_syn,
        "to": to_syn,
        "text": text,
        "received_at": int(ts),                     # unix int
        "received_at_iso": iso_ts(ts),
        "message_type": mtype,
        "conversation_id": conv_id,
        "reply_to": reply_to,
        "meta": {
            "seed_id": s.get("id"),
            "orig_from": s.get("from"),
            "orig_to": s.get("to")
        }
    }
    return event

def build_graph_elements(events: List[Dict[str,Any]]) -> Dict[str, List[Dict[str,Any]]]:
    """
    From the events list generate de-duplicated node and relationship lists.
    Nodes include: Person, Message, Conversation
    Relationships include: (Message)-[SENT_BY]->(Person), (Message)-[TO]->(Person),
                       (Message)-[IN_CONVERSATION]->(Conversation), (Message)-[REPLY_TO]->(Message)
    Each relationship has properties: created_at (unix), created_at_iso
    """
    nodes = {}
    relationships = []

    for ev in events:
        # Person nodes
        p_from_id = person_node_id(ev["from"])
        if p_from_id not in nodes:
            nodes[p_from_id] = {"id": p_from_id, "label": "Person", "phone": ev["from"], "name": None}
        p_to_id = person_node_id(ev["to"])
        if p_to_id not in nodes:
            nodes[p_to_id] = {"id": p_to_id, "label": "Person", "phone": ev["to"], "name": None}
        # Conversation node
        conv_id = conversation_node_id(ev["conversation_id"])
        if conv_id not in nodes:
            nodes[conv_id] = {"id": conv_id, "label": "Conversation", "conversation_id": ev["conversation_id"]}
        # Message node
        msg_id = message_node_id(ev["id"])
        if msg_id not in nodes:
            nodes[msg_id] = {
                "id": msg_id,
                "label": "Message",
                "message_id": ev["id"],
                "text": ev.get("text"),
                "message_type": ev.get("message_type"),
                "received_at": ev.get("received_at"),
                "received_at_iso": ev.get("received_at_iso")
            }
        # Relationships
        # SENT_BY: message -> from person
        relationships.append({
            "from": msg_id,
            "to": p_from_id,
            "type": "SENT_BY",
            "properties": {"created_at": ev["received_at"], "created_at_iso": ev["received_at_iso"]}
        })
        # TO: message -> to person
        relationships.append({
            "from": msg_id,
            "to": p_to_id,
            "type": "TO",
            "properties": {"created_at": ev["received_at"], "created_at_iso": ev["received_at_iso"]}
        })
        # IN_CONVERSATION
        relationships.append({
            "from": msg_id,
            "to": conv_id,
            "type": "IN_CONVERSATION",
            "properties": {"created_at": ev["received_at"], "created_at_iso": ev["received_at_iso"]}
        })
        # REPLY_TO (if present) -> create relationship message->message
        if ev.get("reply_to"):
            target_msg_id = message_node_id(ev["reply_to"])
            # ensure a stub node for target if missing
            if target_msg_id not in nodes:
                # minimal stub - text unknown, will be inserted as stub
                nodes[target_msg_id] = {
                    "id": target_msg_id,
                    "label": "Message",
                    "message_id": ev["reply_to"],
                    "text": None,
                    "message_type": None,
                    "received_at": None,
                    "received_at_iso": None
                }
            relationships.append({
                "from": msg_id,
                "to": target_msg_id,
                "type": "REPLY_TO",
                "properties": {"created_at": ev["received_at"], "created_at_iso": ev["received_at_iso"]}
            })

    # convert nodes dict to list
    nodes_list = list(nodes.values())
    return {"nodes": nodes_list, "relationships": relationships}

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Augment Airbyte WhatsApp normalized records for Neo4j/Graphiti ingestion (single JSON output).")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-record", type=str, help="JSON string of a single normalized record")
    group.add_argument("--input-file", type=str, help="JSON file with array of seed records")
    p.add_argument("--n", type=int, default=100, help="Approximate number of augmented records to produce per seed")
    p.add_argument("--out", type=str, default="augmented_graphiti.json", help="Output JSON filename (single JSON document)")
    p.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    p.add_argument("--variants-per-seed", type=int, default=1, help="Repeat augmentation batches per seed")
    p.add_argument("--no-pseudonymize", dest="pseudonymize", action="store_false", help="Do not pseudonymize phone numbers")
    return p.parse_args()

def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    # Load seeds
    seeds = []
    if args.input_record:
        seeds = [json.loads(args.input_record)]
    else:
        with open(args.input_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                seeds = data
            else:
                seeds = [data]

    all_events: List[Dict[str,Any]] = []
    message_counter = 0
    for seed in seeds:
        # normalize seed structure
        # ensure fields id, from, to, text, received_at exist
        base = {
            "id": seed.get("id") or seed.get("message_id") or f"seed-{random.randint(1000,9999)}",
            "from": seed.get("from") or seed.get("sender") or seed.get("wa_id") or "000",
            "to": seed.get("to") or seed.get("recipient") or "000",
            "text": seed.get("text") or seed.get("body") or "hello",
            "received_at": seed.get("received_at") or seed.get("timestamp") or now_unix()
        }
        for batch in range(args.variants_per_seed):
            for i in range(args.n):
                event = augment_one(base, idx=message_counter)
                # optionally pseudonymize (we pseudonymize by default in augment_one via random_phone)
                if not args.pseudonymize:
                    # restore original phone-like values if the input was numeric-ish
                    event['from'] = base['from']
                    event['to'] = base['to']
                all_events.append(event)
                message_counter += 1

    # Build graph elements
    graph = build_graph_elements(all_events)
    output = {
        "generated_at": iso_ts(now_unix()),
        "events_count": len(all_events),
        "events": all_events,
        "nodes": graph["nodes"],
        "relationships": graph["relationships"]
    }

    # write single JSON file
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print(f"Wrote {len(all_events)} events, {len(graph['nodes'])} nodes, {len(graph['relationships'])} relationships to {args.out}")

if __name__ == "__main__":
    main()
