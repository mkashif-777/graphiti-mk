# group chat orchestrator to create a group chat of ~200 messages

import json
import random
import time
from datetime import datetime, timedelta
from uuid import uuid4

# ----------------------------
# Configuration
# ----------------------------

OUTPUT_FILE = "augmented.json"
TOTAL_MESSAGES = 220
TOPIC = "Designing knowledge graphs from WhatsApp conversations using LLMs"

PHONE_NUMBER_ID = "934940683027684"
DISPLAY_PHONE = "15556566230"
GROUP_ID = "whatsapp-group-llm-graph"

USERS = [
    {"name": "Muhammad Kashif", "wa_id": "923046928830"},
    {"name": "Ali Raza", "wa_id": "923001112233"},
    {"name": "Sara Khan", "wa_id": "923334445566"},
    {"name": "Usman Tariq", "wa_id": "923217778899"},
    {"name": "Ayesha Malik", "wa_id": "923459991122"},
    {"name": "Hassan Ahmed", "wa_id": "923118887766"},
]

MESSAGE_TEMPLATES = [
    "From a graph modeling perspective, {}",
    "One challenge I see is {}",
    "Building on the previous point, {}",
    "I agree, especially when considering {}",
    "This becomes more complex once {}",
    "A counterpoint would be {}",
    "In production systems, {}",
    "From my experience, {}",
]

CONTENT_FRAGMENTS = [
    "message-to-message relationships are preserved",
    "sender and receiver edges are explicitly modeled",
    "temporal ordering is maintained",
    "LLMs hallucinate less with structured context",
    "Graphiti benefits from dense connectivity",
    "incremental sync alone is insufficient",
    "historical replay improves reasoning",
    "group chats introduce multi-hop relationships",
    "mentions act as weak receiver signals",
]

# ----------------------------
# Helpers
# ----------------------------

def random_sentence():
    return random.choice(MESSAGE_TEMPLATES).format(
        random.choice(CONTENT_FRAGMENTS)
    )

def generate_message_id():
    return f"wamid.{uuid4().hex}"

def pick_mentions(sender_wa_id):
    candidates = [u for u in USERS if u["wa_id"] != sender_wa_id]
    return random.sample(candidates, k=random.randint(0, 2))

# ----------------------------
# Main orchestration
# ----------------------------

start_time = datetime.utcnow() - timedelta(days=1)
messages = []
previous_message_ids = []

for i in range(TOTAL_MESSAGES):
    sender = random.choice(USERS)
    mentions = pick_mentions(sender["wa_id"])

    text = random_sentence()

    if mentions:
        mention_text = " ".join(f"@{m['name']}" for m in mentions)
        text = f"{mention_text} {text}"

    message_id = generate_message_id()

    timestamp = int((start_time + timedelta(seconds=i * 30)).timestamp())

    message_payload = {
        "from": sender["wa_id"],
        "id": message_id,
        "timestamp": str(timestamp),
        "type": "text",
        "text": {
            "body": f"[{TOPIC}] {text}"
        },
    }

    messages.append(message_payload)
    previous_message_ids.append(message_id)

# ----------------------------
# Airbyte-normalized structure
# ----------------------------

airbyte_record = [{
    "object": "whatsapp_business_account",
    "entry": [{
        "id": GROUP_ID,
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
                        "profile": {"name": user["name"]},
                        "wa_id": user["wa_id"]
                    }
                    for user in USERS
                ],
                "messages": messages
            }
        }]
    }]
}]

# ----------------------------
# Write output
# ----------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(airbyte_record, f, indent=2)

print(f"Generated {TOTAL_MESSAGES} messages in {OUTPUT_FILE}")

