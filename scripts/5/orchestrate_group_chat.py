# group chat orchestrator

import json
import time
import uuid
from copy import deepcopy

OUTPUT_FILE = "augmented.json"

# --------------------------------------------------
# GROUP + PARTICIPANTS
# --------------------------------------------------
BUSINESS_PHONE = {
    "display_phone_number": "15556566230",
    "phone_number_id": "934940683027684"
}

PARTICIPANTS = [
    {"name": "Muhammad Kashif", "wa_id": "923046928830"},
    {"name": "Ali Raza",        "wa_id": "923001112233"},
    {"name": "Sara Khan",       "wa_id": "923334445566"},
    {"name": "Ahmed Hassan",    "wa_id": "923221234567"}
]

GROUP_ID = "25700534409553170"

# --------------------------------------------------
# SINGLE TOPIC CONVERSATION
# --------------------------------------------------
CHAT_MESSAGES = [
    "I think using WhatsApp as an ingestion layer for AI agents makes a lot of sense.",
    "Agreed. Especially when messages are streamed into a knowledge graph.",
    "How are you planning to structure entities from chats?",
    "We are mapping users, messages, intents, and timestamps as nodes.",
    "That should help with conversational memory across sessions.",
    "Yes, and Graphiti helps maintain temporal edges.",
    "Are you doing real-time ingestion or batch?",
    "Both. Webhooks for real-time and Airbyte for backfills.",
    "Nice. That should make agent reasoning much more contextual.",
    "Exactly. The agent can traverse prior conversations easily."
]

# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def make_event(sender, message, timestamp):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": GROUP_ID,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": BUSINESS_PHONE,
                            "contacts": [
                                {
                                    "profile": {"name": sender["name"]},
                                    "wa_id": sender["wa_id"]
                                }
                            ],
                            "messages": [
                                {
                                    "from": sender["wa_id"],
                                    "id": "wamid." + uuid.uuid4().hex,
                                    "timestamp": str(timestamp),
                                    "type": "text",
                                    "text": {
                                        "body": message
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

# --------------------------------------------------
# ORCHESTRATION
# --------------------------------------------------
def orchestrate_chat():
    events = []
    base_ts = int(time.time()) - 3600  # start 1 hour ago

    for i, text in enumerate(CHAT_MESSAGES):
        sender = PARTICIPANTS[i % len(PARTICIPANTS)]
        event = make_event(
            sender=sender,
            message=text,
            timestamp=base_ts + (i * 45)
        )
        events.append(event)

    return events

# --------------------------------------------------
# WRITE OUTPUT
# --------------------------------------------------
if __name__ == "__main__":
    data = orchestrate_chat()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {len(data)} group chat messages in {OUTPUT_FILE}")
