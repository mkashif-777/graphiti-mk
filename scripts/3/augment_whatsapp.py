import json
import random
import time
import uuid
from copy import deepcopy

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------
INPUT_FILE = "input.json"        # your original Airbyte-normalized json
OUTPUT_FILE = "augmented.json"   # final result
AUGMENT_COUNT = 2000             # how many synthetic records to generate

# Text variations for augmentation
TEXT_TEMPLATES = [
    "Got it, thanks!",
    "Thanks for the update.",
    "Alright, noted.",
    "Perfect, appreciate it.",
    "Hi, how are you doing?",
    "Hello, what's the status?",
    "Can you help me with this?",
    "Received. Will look into it.",
    "Sending the details shortly.",
    "Following up on my request.",
    "Any update so far?",
    "Let me check and get back to you.",
    "Thanks! That helps.",
]

def random_text():
    t = random.choice(TEXT_TEMPLATES)
    # small natural variations
    variations = [
        t,
        t.lower(),
        t + " 😊",
        t.replace("Hi", "Hey"),
        t.replace("thanks", "thank you"),
    ]
    return random.choice(variations)

def jitter_timestamp(ts):
    # ts is string epoch -> produce a slight random offset
    base = int(ts)
    return str(base + random.randint(10, 100000))

def random_message_id():
    return "wamid." + uuid.uuid4().hex.upper()

# ----------------------------------------------------------
# AUGMENTATION LOGIC
# ----------------------------------------------------------
def generate_augmented_records(original_records, count):
    augmented = []

    for _ in range(count):
        # pick one of the original items as base
        base = deepcopy(random.choice(original_records))

        # mutate message
        entry = base["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        msg = value["messages"][0]

        # update message body
        if msg.get("text"):
            msg["text"]["body"] = random_text()

        # update timestamp
        msg["timestamp"] = jitter_timestamp(msg["timestamp"])

        # update message id
        msg["id"] = random_message_id()

        # optionally modify names slightly
        contact = value["contacts"][0]
        name = contact["profile"]["name"]
        if random.random() < 0.25:
            contact["profile"]["name"] = name + random.choice(["", ".", "_", "1"])

        # push to final list
        augmented.append(base)

    return augmented

# ----------------------------------------------------------
# RUN SCRIPT
# ----------------------------------------------------------
if __name__ == "__main__":
    with open(INPUT_FILE, "r") as f:
        original = json.load(f)

    augmented_data = generate_augmented_records(original, AUGMENT_COUNT)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(augmented_data, f, indent=2)

    print(f"Generated {len(augmented_data)} augmented records -> {OUTPUT_FILE}")
