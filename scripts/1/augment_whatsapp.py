import json
import random
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone

with open("/home/ahoy/muhammad_kashif/graphiti/scripts/augmented.ndjson") as f:
    SEED_EVENTS = json.load(f)


TEXT_VARIATIONS = [
    "This is a text message.",
    "Hi there, just getting started!",
    "Just got a message from you, there?",
    "Untill we meet again",
    "Hope you are doing great",
    "Hello, I need help with my order #A1234",
    "pls cancel my order asap",
    "Sorry, come again?",
    "plz send tracking number — thanks!",
    "Is there a warranty on this product? 🤔",
    "What's the point of all of this?"
]

IMAGE_CAPTIONS = [
    "Here is the receipt",
    "Product photo attached",
    "Screenshot of the error"
]

def jitter_timestamp(base_ts:int, seconds_range:int=600):
    return str(base_ts + random.randint(-seconds_range, seconds_range))

def random_wa_id(country_code='92'):
    # country_code as string, generate plausible number
    return country_code + ''.join(str(random.randint(0,9)) for _ in range(9))

def augment(seed_event, n_variants=5):
    out = []
    base = seed_event
    # derive a base timestamp from seed if present
    try:
        base_ts = int(seed_event['entry'][0]['changes'][0]['value']['messages'][0]['timestamp'])
    except Exception:
        base_ts = int(time.time())
    for i in range(n_variants):
        e = deepcopy(base)
        # mutate id
        entry = e['entry'][0]
        entry['id'] = str(int(entry['id']) + i + 1000) if entry.get('id') and entry['id'].isdigit() else entry.get('id', '') + f"-{i}"
        change = entry['changes'][0]
        value = change['value']
        # mutate contact name slightly
        contact = value.get('contacts', [{}])[0]
        name = contact.get('profile', {}).get('name', '')
        if name:
            variants = [name, name.split()[0] if ' ' in name else name, name.title(), name.upper(), name.lower()]
            contact['profile']['name'] = random.choice(variants)
        # mutate wa_id and display number
        contact['wa_id'] = random_wa_id(country_code=random.choice(['92','1','44','52','234']))
        value['metadata']['display_phone_number'] = random.choice(["16505551111","15556566230","447700900001","14085551234","15551230000"])
        value['metadata']['phone_number_id'] = value['metadata'].get('phone_number_id','PN') + f"-{random.randint(100,999)}"
        # messages
        msg = value.get('messages', [{}])[0]
        # randomly pick message type text or image
        if random.random() < 0.85:
            msg['type'] = 'text'
            msg['text'] = {'body': random.choice(TEXT_VARIATIONS)}
        else:
            msg['type'] = 'image'
            msg.pop('text', None)
            msg['image'] = {
                'mime_type': 'image/jpeg',
                'sha256': ''.join(random.choice('abcdef0123456789') for _ in range(32)),
                'caption': random.choice(IMAGE_CAPTIONS)
            }
        msg['from'] = contact['wa_id']
        base_ts = int(base_ts)
        msg['timestamp'] = jitter_timestamp(base_ts, seconds_range=86400)
        msg['id'] = (msg.get('id','') or 'msg') + f"-{random.randint(1000,9999)}"
        out.append(e)
    return out

def main(out_file='augmented_whatsapp_events1.json', variants_per_seed=6):
    all_events = []
    for seed in SEED_EVENTS:
        generated = augment(seed, n_variants=variants_per_seed)
        all_events.extend(generated)
    # optionally shuffle to intermix languages and IDs
    random.shuffle(all_events)
    with open(out_file, 'w', encoding='utf-8') as fh:
        json.dump(all_events, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {len(all_events)} augmented events to {out_file}")

if __name__ == "__main__":
    main()
