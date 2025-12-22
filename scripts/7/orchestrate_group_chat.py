import json
import random
from datetime import datetime, timedelta
from uuid import uuid4

OUTPUT_FILE = "augmented.json"

GROUPS = [
    {
        "group_id": "whatsapp-group-llm-graph",
        "topic": "LLM-based knowledge graphs from chat data",
    },
    {
        "group_id": "whatsapp-group-agentic-ai",
        "topic": "Agentic AI and memory architectures",
    },
    {
        "group_id": "whatsapp-group-data-eng",
        "topic": "Streaming vs batch ingestion for messaging systems",
    },
]

USERS = [
    {"name": "Muhammad Kashif", "wa_id": "923046928830"},
    {"name": "Ali Raza", "wa_id": "923001112233"},
    {"name": "Sara Khan", "wa_id": "923334445566"},
    {"name": "Usman Tariq", "wa_id": "923217778899"},
    {"name": "Ayesha Malik", "wa_id": "923459991122"},
    {"name": "Hassan Ahmed", "wa_id": "923118887766"},
]

PHONE_NUMBER_ID = "934940683027684"
DISPLAY_PHONE = "15556566230"

MESSAGES_PER_GROUP = 120
MAX_THREAD_DEPTH = 15

MESSAGE_SEEDS = [
    "One architectural challenge is",
    "From a graph perspective",
    "A practical issue arises when",
    "This becomes interesting once",
    "In real deployments",
    "A counterargument would be",
]

CONTENT_FRAGMENTS = [
    "threads are not explicitly modeled",
    "message-level memory is required",
    "incremental sync misses context",
    "historical replay improves reasoning",
    "graphs outperform flat embeddings",
    "dense connectivity improves retrieval",
]

def new_message_id():
    return f"wamid.{uuid4().hex}"

def sentence():
    return f"{random.choice(MESSAGE_SEEDS)} {random.choice(CONTENT_FRAGMENTS)}."

def pick_user(exclude=None):
    pool = [u for u in USERS if u != exclude]
    return random.choice(pool)

all_groups_payload = []
base_time = datetime.utcnow() - timedelta(days=2)

for group in GROUPS:
    messages = []
    message_index = {}

    current_time = base_time

    for i in range(MESSAGES_PER_GROUP):
        sender = random.choice(USERS)
        message_id = new_message_id()

        reply_to = None
        if message_index and random.random() < 0.65:
            reply_to = random.choice(list(message_index.keys()))

        body = f"[{group['topic']}] {sentence()}"

        message = {
            "from": sender["wa_id"],
            "id": message_id,
            "timestamp": str(int(current_time.timestamp())),
            "type": "text",
            "text": {"body": body},
        }

        if reply_to:
            message["context"] = {
                "reply_to_message_id": reply_to
            }

        messages.append(message)
        message_index[message_id] = sender["wa_id"]

        current_time += timedelta(seconds=random.randint(20, 90))

    group_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": group["group_id"],
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": DISPLAY_PHONE,
                        "phone_number_id": PHONE_NUMBER_ID
                    },
                    "contacts": [
                        {
                            "profile": {"name": u["name"]},
                            "wa_id": u["wa_id"]
                        }
                        for u in USERS
                    ],
                    "messages": messages
                }
            }]
        }]
    }

    all_groups_payload.append(group_payload)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_groups_payload, f, indent=2)

print(f"Generated {len(GROUPS)} groups with threaded conversations → {OUTPUT_FILE}")
