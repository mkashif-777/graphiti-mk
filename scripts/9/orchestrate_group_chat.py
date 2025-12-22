import json
import random
from uuid import uuid4
from datetime import datetime, timedelta

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

OUTPUT_FILE = "augmented.json"

NUM_GROUPS = 4
MESSAGES_PER_GROUP = 240

DISPLAY_PHONE = "15556566230"
PHONE_NUMBER_ID = "934940683027684"

USERS = [
    {"name": "Muhammad Kashif", "wa_id": "923046928830"},
    {"name": "Babar Azam", "wa_id": "923001112233"},
    {"name": "Virat Kohli", "wa_id": "923334445566"},
    {"name": "Steve Smith", "wa_id": "923217778899"},
    {"name": "Joe Root", "wa_id": "923459991122"},
    {"name": "Mitchell Starc", "wa_id": "923118887766"},
    {"name": "Kane Williamson", "wa_id": "923009998877"},
]

GROUP_TOPICS = [
    "Knowledge graph construction from WhatsApp chats",
    "Agentic AI memory and long-term reasoning",
    "Batch vs streaming ingestion in Airbyte",
    "Graph-based retrieval for LLM systems",
]

MESSAGE_FRAGMENTS = [
    "thread structure matters here",
    "parent-child relationships improve traversal",
    "reply-only models lose hierarchy",
    "explicit trees improve reasoning",
    "graph depth improves recall",
    "flat chats collapse context",
]

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def new_message_id():
    return f"wamid.{uuid4().hex}"

def sentence(topic):
    return f"[{topic}] {random.choice(MESSAGE_FRAGMENTS)}."

def pick_users():
    return random.sample(USERS, random.randint(4, 6))

# --------------------------------------------------
# MAIN ORCHESTRATION
# --------------------------------------------------

all_groups = []
base_time = datetime.utcnow() - timedelta(days=4)

for g in range(NUM_GROUPS):
    topic = GROUP_TOPICS[g]
    group_id = f"whatsapp-group-{g+1}"
    group_users = pick_users()

    messages = []
    message_map = {}        # id -> message
    parent_children = {}    # parent_id -> [child_ids]

    current_time = base_time + timedelta(hours=g * 6)

    for i in range(MESSAGES_PER_GROUP):
        sender = random.choice(group_users)
        msg_id = new_message_id()

        parent_id = None
        if message_map and random.random() < 0.75:
            parent_id = random.choice(list(message_map.keys()))

        message = {
            "from": sender["wa_id"],
            "id": msg_id,
            "timestamp": str(int(current_time.timestamp())),
            "type": "text",
            "text": {"body": sentence(topic)},
            "parent_message_id": parent_id,
            "child_message_ids": [],
        }

        if parent_id:
            message["context"] = {
                "reply_to_message_id": parent_id
            }
            parent_children.setdefault(parent_id, []).append(msg_id)

        messages.append(message)
        message_map[msg_id] = message

        current_time += timedelta(seconds=random.randint(20, 80))

    # Populate child_message_ids
    for parent_id, children in parent_children.items():
        message_map[parent_id]["child_message_ids"] = children

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
                                "phone_number_id": PHONE_NUMBER_ID,
                            },
                            "contacts": [
                                {
                                    "profile": {"name": u["name"]},
                                    "wa_id": u["wa_id"],
                                }
                                for u in group_users
                            ],
                            "messages": messages,
                        },
                    }
                ],
            }
        ],
    }

    all_groups.append(group_payload)

# --------------------------------------------------
# WRITE OUTPUT
# --------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_groups, f, indent=2)

print(
    f"Generated {NUM_GROUPS} groups with explicit parent-child message trees → {OUTPUT_FILE}"
)
