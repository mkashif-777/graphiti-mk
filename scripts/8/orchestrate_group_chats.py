import json
import random
from uuid import uuid4
from datetime import datetime, timedelta

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

OUTPUT_FILE = "augmented.json"

NUM_GROUPS = 4
MESSAGES_PER_GROUP = 220

DISPLAY_PHONE = "15556566230"
PHONE_NUMBER_ID = "934940683027684"

# Shared global user pool (overlap across groups)
USERS = [
    {"name": "Muhammad Kashif", "wa_id": "923046928830"},
    {"name": "Ali Raza", "wa_id": "923001112233"},
    {"name": "Sara Khan", "wa_id": "923334445566"},
    {"name": "Usman Tariq", "wa_id": "923217778899"},
    {"name": "Ayesha Malik", "wa_id": "923459991122"},
    {"name": "Hassan Ahmed", "wa_id": "923118887766"},
    {"name": "Bilal Hussain", "wa_id": "923009998877"},
]

GROUP_TOPICS = [
    "Building knowledge graphs from WhatsApp chat data",
    "Agentic AI memory and long-term context storage",
    "Batch vs streaming ingestion in Airbyte pipelines",
    "LLM-based reasoning over conversational graphs",
]

MESSAGE_OPENERS = [
    "One challenge is",
    "From an architectural perspective",
    "In production systems",
    "A key limitation appears when",
    "This becomes more complex once",
    "A practical observation is",
]

MESSAGE_CONTENT = [
    "message-level context is lost",
    "thread reconstruction becomes ambiguous",
    "incremental sync lacks historical grounding",
    "graph traversal improves recall",
    "dense edges help reasoning agents",
    "flat embeddings fail under long conversations",
]

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def new_message_id():
    return f"wamid.{uuid4().hex}"

def generate_sentence(topic):
    return f"[{topic}] {random.choice(MESSAGE_OPENERS)} {random.choice(MESSAGE_CONTENT)}."

def pick_users_for_group():
    # force overlap: 4–6 users per group
    return random.sample(USERS, random.randint(4, 6))

# --------------------------------------------------
# GROUP CHAT ORCHESTRATION
# --------------------------------------------------

all_groups = []
global_start_time = datetime.utcnow() - timedelta(days=3)

for group_index in range(NUM_GROUPS):
    topic = GROUP_TOPICS[group_index]
    group_id = f"whatsapp-group-{group_index + 1}"

    group_users = pick_users_for_group()
    messages = []
    message_ids = []

    timestamp = global_start_time + timedelta(hours=group_index * 4)

    for i in range(MESSAGES_PER_GROUP):
        sender = random.choice(group_users)
        msg_id = new_message_id()

        message = {
            "from": sender["wa_id"],
            "id": msg_id,
            "timestamp": str(int(timestamp.timestamp())),
            "type": "text",
            "text": {
                "body": generate_sentence(topic)
            }
        }

        # Threading logic (reply chains)
        if message_ids and random.random() < 0.7:
            message["context"] = {
                "reply_to_message_id": random.choice(message_ids[-20:])
            }

        messages.append(message)
        message_ids.append(msg_id)

        timestamp += timedelta(seconds=random.randint(25, 90))

    group_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": group_id,
                "changes": [
                    {
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
                                for u in group_users
                            ],
                            "messages": messages
                        }
                    }
                ]
            }
        ]
    }

    all_groups.append(group_payload)

# --------------------------------------------------
# WRITE OUTPUT
# --------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_groups, f, indent=2)

print(
    f"Generated {NUM_GROUPS} independent WhatsApp group chats "
    f"with overlapping users and deep threading → {OUTPUT_FILE}"
)
