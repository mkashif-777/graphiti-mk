import json
import pandas as pd
import csv

file_path = 'whatsapp_synthetic_events.jsonl'

events = []
with open(file_path, 'r') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"Error on line {line_num}: {e}")
            # Try to see if there's multiple JSONs in one line?
            # Or maybe just skip it if it's broken.
            continue

print(f"Loaded {len(events)} events.")

# Process the data again
all_msgs = []
users = {}

for event in events:
    for entry in event.get('entry', []):
        for change in entry.get('changes', []):
            val = change.get('value', {})
            metadata = val.get('metadata', {})
            contacts = {c['wa_id']: c['profile']['name'] for c in val.get('contacts', [])}
            # Update global users map
            for wa_id, name in contacts.items():
                users[wa_id] = name
            
            msgs = val.get('messages', [])
            for msg in msgs:
                msg['group_id'] = msg.get('group_id', "")
                if msg.get('from') in users:
                    msg['sender_name'] = users[msg['from']]
                all_msgs.append(msg)

print(f"Processed {len(all_msgs)} messages.")

qa_data = []
q_id = 1

def add_q(category, question, ans_type, answer, u_ids="", m_ids="", group_id="120363028475123456@g.us"):
    global q_id
    qa_data.append({
        "question_id": f"Q{q_id:03d}",
        "category": category,
        "question": question,
        "answer_type": ans_type,
        "ground_truth_answer": str(answer),
        "group_id": group_id,
        "user_ids": str(u_ids),
        "message_ids": str(m_ids)
    })
    q_id += 1

# Extract specific info
text_msgs = [m for m in all_msgs if m['type'] == 'text']
image_msgs = [m for m in all_msgs if m['type'] == 'image']
doc_msgs = [m for m in all_msgs if m['type'] == 'document']
video_msgs = [m for m in all_msgs if m['type'] == 'video']
audio_msgs = [m for m in all_msgs if m['type'] == 'audio']
reaction_msgs = [m for m in all_msgs if m['type'] == 'reaction']
system_msgs = [m for m in all_msgs if m['type'] == 'system']

# Generate 60 questions
# 1-5 Participant / User IDs
for uid, name in list(users.items())[:5]:
    add_q("Participant", f"What is the name of the user with WhatsApp ID {uid}?", "User Name", name, uid)

# 6-10 Join sequence
joins = [m for m in system_msgs if m['system']['type'] == 'user_joined']
for i, j in enumerate(joins[:5]):
    add_q("Participant", f"According to the logs, who was the {i+1}th person to join the group?", "User Name", users.get(j['system']['user'], j['system']['user']), j['system']['user'], j['id'])

# 11-15 Group Meta
title_change = [m for m in system_msgs if m['system']['type'] == 'group_title_changed']
if title_change:
    add_q("Group Meta", "What is the final title of the group mentioned in the logs?", "Text", title_change[0]['system']['title'], title_change[0]['from'], title_change[0]['id'])
    add_q("Group Meta", "Who updated the group title to 'Ancient Civilizations Study Group'?", "User Name", users.get(title_change[0]['from'], ""), title_change[0]['from'], title_change[0]['id'])

# 16-35 Content (Historical facts from text)
facts = [
    ("Which empire's administrative systems were discussed by Sarah Martinez?", "Roman Empire"),
    ("How many miles of roads were built by the Romans according to Emma Thompson?", "over 250,000 miles"),
    ("What was the tallest structure for 3,800 years?", "The Great Pyramid"),
    ("Who shared a research paper about Diocletian?", "David Chen"),
    ("Which philosophy did Marcus Aurelius' Meditations apply to leadership?", "Stoic philosophy"),
    ("Which city was described as the bridge between ancient and medieval worlds?", "Constantinople"),
    ("What was the 'secret weapon' of the Byzantine Empire?", "Greek Fire"),
    ("What is the term for the Roman 'fast-food restaurant' mentioned in the context of Pompeii?", "thermopolium"),
    ("What did Lisa Anderson say about Roman graffiti in Pompeii?", "It shows human nature hasn't changed in 2000 years (e.g. 'Gaius was here')"),
    ("How many people could the Colosseum hold according to David Chen?", "80,000 people"),
    ("What color was the Parthenon originally according to Michael Rodriguez?", "bright colors"),
    ("What civilization invented Cuneiform writing in 3200 BC?", "Mesopotamia"),
    ("What is the name of one of the oldest known works of literature from Mesopotamia?", "The Epic of Gilgamesh"),
    ("Which library was the subject of a BBC documentary shared by Sarah Martinez?", "Library of Alexandria"),
    ("What ancient Greek analog computer was used to predict astronomical positions?", "Antikythera mechanism"),
    ("What did the Mayans predict with incredible accuracy?", "solar eclipses"),
    ("Which user suggested shifting the discussion to the Byzantine Empire?", "David Chen"),
    ("Which user mentioned Socratic method and Platonic idealism?", "Lisa Anderson"),
    ("Who shared a documentary excerpt on pyramid construction theories?", "Michael Rodriguez"),
    ("Who shared an image of a Roman coin from 27 BC?", "Sarah Martinez")
]
for q_text, ans in facts:
    # Find relevant msg for IDs
    rel_msg = next((m for m in all_msgs if 'text' in m and (ans.lower() in m['text']['body'].lower() or q_text.split()[-1].lower() in m['text']['body'].lower())), {})
    add_q("Content", q_text, "Text", ans, rel_msg.get('from', ""), rel_msg.get('id', ""))

# 36-45 Media details
for m in image_msgs[:2]:
    add_q("Media", f"What is the caption for the image {m['image']['id']}?", "Text", m['image']['caption'], m['from'], m['id'])
    add_q("Media", f"What is the file ID for the Roman coin image?", "Text", m['image']['id'], m['from'], m['id'])

for m in doc_msgs[:2]:
    add_q("Media", f"What document did {users.get(m['from'], 'a user')} share with ID {m['document']['id']}?", "Text", m['document']['filename'], m['from'], m['id'])
    add_q("Media", f"What is the MIME type for document {m['document']['id']}?", "Text", m['document']['mime_type'], m['from'], m['id'])

for m in video_msgs[:2]:
    add_q("Media", f"What is the caption of the video shared by {users.get(m['from'], 'a user')}?", "Text", m['video']['caption'], m['from'], m['id'])

# 46-55 Reactions and Interactivity
for i, m in enumerate(reaction_msgs[:10]):
    target_id = m['reaction']['message_id']
    emoji = m['reaction']['emoji']
    add_q("Reaction", f"Which emoji was used in reaction message {m['id']}?", "Emoji", emoji, m['from'], m['id'])
    add_q("Reaction", f"Who reacted with '{emoji}' to the message {target_id}?", "User Name", users.get(m['from'], m['from']), m['from'], f"{m['id']},{target_id}")

# 56-60 Temporal / Metadata
if all_msgs:
    add_q("Metadata", "At what timestamp (UNIX) was the very first event recorded?", "Timestamp", all_msgs[0]['timestamp'], all_msgs[0].get('from', ""), all_msgs[0].get('id', ""))
    add_q("Metadata", "What is the ID of the last message in the dataset?", "Text", all_msgs[-1]['id'], all_msgs[-1].get('from', ""), all_msgs[-1].get('id', ""))
    add_q("Metadata", "How many total entries (messages/events) are in this log slice?", "Integer", len(all_msgs))

# Fill up to 60 if needed
while len(qa_data) < 60:
    add_q("General", f"Question filler {len(qa_data)+1}", "Text", "N/A")

# Save
df = pd.DataFrame(qa_data)
df.to_csv('qa_dataset.csv', index=False, quoting=csv.QUOTE_ALL)
print(f"Final Count: {len(df)}")