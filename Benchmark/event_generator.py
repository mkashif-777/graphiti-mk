import json
import random
from datetime import datetime, timedelta

# Constants
WABA_ID = "WABA_ID_789012"
PHONE_NUMBER_ID = "1234567890987654"
BUSINESS_ID = "9876543210123456"
GROUP_ID = "120363028475123456@g.us"

PARTICIPANTS = [
    {"name": "Sarah Martinez", "wa_id": "17025551001"},
    {"name": "David Chen", "wa_id": "17025551002"},
    {"name": "Emma Thompson", "wa_id": "17025551003"},
    {"name": "Michael Rodriguez", "wa_id": "17025551004"},
    {"name": "Lisa Anderson", "wa_id": "17025551005"}
]

TOPICS = ["Roman Empire", "Ancient Egypt", "Greeks", "Maya Civilization", "Mesopotamia"]

def create_event(msg_id, timestamp, sender, msg_type, content, context=None):
    event = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": WABA_ID,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "+1 (800) 555-0100",
                        "phone_number_id": PHONE_NUMBER_ID,
                        "business_account_id": BUSINESS_ID
                    },
                    "contacts": [{"profile": {"name": sender["name"]}, "wa_id": sender["wa_id"]}],
                    "messages": [{
                        "from": sender["wa_id"],
                        "id": f"wamid.event_{msg_id:03d}",
                        "timestamp": str(int(timestamp.timestamp())),
                        "type": msg_type,
                        **content,
                        "group_id": GROUP_ID
                    }],
                    "statuses": [],
                    "errors": []
                },
                "field": "messages"
            }]
        }]
    }
    if context:
        event["entry"][0]["changes"][0]["value"]["messages"][0]["context"] = context
    return event

events = []
current_time = datetime(2025, 1, 1, 10, 0, 0)
msg_ids = [] # To track IDs for replies and reactions

# Generate 60 events
for i in range(1, 81):
    sender = random.choice(PARTICIPANTS)
    current_time += timedelta(minutes=random.randint(1, 10))
    
    # Decide type
    rand_val = random.random()
    msg_type = "text"
    content = {}
    context = None
    
    if rand_val < 0.6: # Text (60%)
        msg_type = "text"
        body = f"Message {i}: Discussing {random.choice(TOPICS)}. Interaction detail {random.randint(1,100)}."
        # Occasionally make it a reply
        if msg_ids and random.random() < 0.3:
            parent_id, parent_sender_id = random.choice(msg_ids)
            context = {"from": parent_sender_id, "id": parent_id}
            body = f"Reply to {parent_id}: I agree/disagree. " + body
        content = {"text": {"body": body}}
        
    elif rand_val < 0.75: # Reaction (15%)
        if msg_ids:
            msg_type = "reaction"
            parent_id, _ = random.choice(msg_ids)
            content = {"reaction": {"message_id": parent_id, "emoji": random.choice(["👍", "❤️", "😂", "😮", "🙏", "🔥"])}}
        else: # Fallback to text
            msg_type = "text"
            content = {"text": {"body": "Starting the session."}}
            
    elif rand_val < 0.85: # Image (10%)
        msg_type = "image"
        content = {"image": {"caption": f"Check this artifact from {random.choice(TOPICS)}!", "id": f"media_id_{i}", "mime_type": "image/jpeg"}}
        
    elif rand_val < 0.92: # Document (7%)
        msg_type = "document"
        content = {"document": {"caption": "Research paper summary.", "filename": f"research_{i}.pdf", "id": f"doc_id_{i}", "mime_type": "application/pdf"}}
        
    else: # System (8%)
        msg_type = "system"
        sys_type = random.choice(["user_joined", "group_title_changed"])
        if sys_type == "group_title_changed":
            content = {"system": {"type": sys_type, "title": f"Study Group - {random.choice(TOPICS)}", "user": sender["wa_id"]}}
        else:
            new_user = random.choice(PARTICIPANTS)["wa_id"]
            content = {"system": {"type": sys_type, "user": new_user}}

    event = create_event(i, current_time, sender, msg_type, content, context)
    events.append(event)
    
    # Add to msg_ids if it's a message that can be replied to/reacted to (not system/reaction)
    if msg_type not in ["system", "reaction"]:
        msg_ids.append((f"wamid.event_{i:03d}", sender["wa_id"]))

# Write to JSONL
with open('whatsapp_synthetic_events_v2.jsonl', 'w') as f:
    for event in events:
        f.write(json.dumps(event) + '\n')

print(f"Generated 80 events and saved to whatsapp_synthetic_events_v2.jsonl")