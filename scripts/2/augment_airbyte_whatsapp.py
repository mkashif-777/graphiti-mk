#!/usr/bin/env python3
"""
augment_airbyte_whatsapp.py

Take a normalized Airbyte record emitted from a WhatsApp connector and synthesize
many realistic variants for training / testing.

Usage:
  python augment_airbyte_whatsapp.py \
    --input-record '{"id":"wamid.HBgMOTIzMDQ2OTI4ODMwFQIAEhggQUM4RDNDM0ZENDAzODhDREZGOTc0QzBCRDlBMDFDMDEA-3696","from":"447700900001","to":"923331231234","text":"Hello, I need help","received_at":"1698361200"}' \
    --n 200 --out augmented.ndjson --ndjson

Or pass a JSON file with multiple seed records using --input-file seeds.json

Outputs NDJSON by default if --ndjson passed, otherwise JSON array.
"""

from __future__ import annotations
import argparse
import json
import random
import re
import time
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

try:
    from faker import Faker
    _HAS_FAKER = True
except Exception:
    _HAS_FAKER = False

# ---------- Helpers ----------

EMOJI = ["👋", "🙂", "😕", "🤔", "🙏", "👍", "🚚", "📦", "🔔"]
ABBREVS = {
    "please": ["pls", "plz", "plea se"],
    "you": ["u"],
    "thanks": ["thx", "ty", "thanks!"],
    "as soon as possible": ["ASAP", "asap"],
    "order": ["ord", "order"]
}
MULTILINGUAL_TEMPLATES = [
    "{greet}, I need help with my order #{order}",
    "Hi, can you please cancel my order {order}?",
    "Hola, ¿puedes ayudarme con mi factura?",
    "Bonjour, j'ai besoin d'aide avec ma commande {order}",
    "Hey — tracking number please.",
    "Is there a warranty on this product?"
]
TYPO_PROB = 0.12  # per-word typo probability
EMOJI_PROB = 0.25
CASE_VARIANTS = ["sentence", "lower", "upper", "title"]
IMAGE_CAPTIONS = ["Receipt attached", "Photo of product", "See screenshot"]

fake = Faker() if _HAS_FAKER else None

def unix_now() -> int:
    return int(time.time())

def jitter_timestamp(ts_unix: int, max_seconds: int = 86400) -> str:
    """
    Jitter an integer unix timestamp by up to +/- max_seconds (default 24h).
    Returns string to match your record style.
    """
    ts = int(ts_unix)
    jittered = ts + random.randint(-max_seconds, max_seconds)
    return str(max(0, jittered))

def random_phone(country_code: str = "44") -> str:
    """
    Very simple synthetic phone number generator: not guaranteed valid.
    If Faker available, uses it for more realistic numbers.
    """
    if _HAS_FAKER:
        # returns something like +44 7700 900001 -> strip non-digits
        p = re.sub(r"[^\d]", "", fake.phone_number())
        return (country_code + p[-9:]) if len(p) >= 9 else (country_code + ''.join(str(random.randint(0,9)) for _ in range(9)))
    else:
        return country_code + ''.join(str(random.randint(0,9)) for _ in range(9))

def small_typo(word: str) -> str:
    """
    Introduce a simple typo: swap adjacent chars or drop a char.
    """
    if len(word) <= 2:
        return word
    if random.random() < 0.5:
        i = random.randrange(0, len(word)-1)
        lst = list(word)
        lst[i], lst[i+1] = lst[i+1], lst[i]
        return "".join(lst)
    else:
        i = random.randrange(0, len(word))
        return word[:i] + word[i+1:]

def apply_typos(text: str, prob_per_word: float = TYPO_PROB) -> str:
    tokens = re.split(r"(\W+)", text)  # keep punctuation as separate tokens
    out = []
    for t in tokens:
        if re.match(r"^\w+$", t) and random.random() < prob_per_word:
            out.append(small_typo(t))
        else:
            out.append(t)
    return "".join(out)

def apply_abbrevs(text: str) -> str:
    for full, subs in ABBREVS.items():
        # use word-boundary replace
        pattern = re.compile(r"\b" + re.escape(full) + r"\b", flags=re.IGNORECASE)
        def repl(m):
            if random.random() < 0.5:
                return random.choice(subs)
            return m.group(0)
        text = pattern.sub(repl, text)
    return text

def case_variant(text: str) -> str:
    v = random.choice(CASE_VARIANTS)
    if v == "lower":
        return text.lower()
    if v == "upper":
        return text.upper()
    if v == "title":
        return text.title()
    return text  # sentence

def maybe_add_emoji(text: str) -> str:
    if random.random() < EMOJI_PROB:
        return text + " " + random.choice(EMOJI)
    return text

def paraphrase_template(seed_text: str) -> Optional[str]:
    # Choose a template that resembles the seed or fallback random multilingual
    if "help" in seed_text.lower():
        templates = [
            "Hi, I need help with my order {order}",
            "Hello, can you assist me with my order {order}?",
            "I need support regarding order {order}"
        ]
    elif "cancel" in seed_text.lower():
        templates = [
            "Please cancel order {order} ASAP",
            "Cancel my order {order}, please",
            "I want to cancel order {order}"
        ]
    else:
        templates = MULTILINGUAL_TEMPLATES
    t = random.choice(templates)
    order = random.choice(["A1234", "B9876", str(random.randint(1000,9999))])
    return t.format(order=order, greet=random.choice(["Hi","Hello","Hey"]))

# ---------- Augmentation pipeline ----------

def augment_record(seed: Dict[str, Any],
                   n: int = 100,
                   allow_images: bool = True,
                   replies: bool = True,
                   pseudonymize: bool = True,
                   seed_random: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Produce n augmented records derived from seed.
    - seed: normalized Airbyte record dict
    - n: number of augmented records to produce
    - allow_images: include a small fraction of image-type messages
    - replies: optionally synthesize reply messages as part of context (multi-turn)
    - pseudonymize: replace phone numbers with synthetic ones
    - seed_random: optional RNG seed for reproducibility
    Returns list of normalized records (same schema).
    """
    if seed_random is not None:
        random.seed(seed_random)

    results = []
    orig_ts = int(seed.get("received_at", str(unix_now())))
    base_text = seed.get("text", "")

    for i in range(n):
        r = deepcopy(seed)
        # id: append variant suffix to avoid collisions
        r["id"] = f"{seed.get('id','msg')}-{i:06d}"

        # phone numbers: optionally pseudonymize for privacy
        if pseudonymize:
            # try to preserve country code if present (leading digits)
            from_num = r.get("from", "")
            to_num = r.get("to", "")
            # simple heuristic: take first 1-3 digits as country code if length>8
            def make_syn(num):
                if not num or not num.isdigit():
                    return random_phone(random.choice(["1","44","92","52","234"]))
                if len(num) >= 10:
                    cc = num[:2]
                else:
                    cc = "1"
                return random_phone(cc)
            r["from"] = make_syn(from_num)
            r["to"] = make_syn(to_num)

        # timestamp jitter
        r["received_at"] = jitter_timestamp(orig_ts, max_seconds=7*86400)  # up to ±7 days

        # message type: mostly text, small chance image/sticker
        msg_type = "text"
        if allow_images and random.random() < 0.06:
            msg_type = "image"
            # create an image-like text field as caption
            caption = random.choice(IMAGE_CAPTIONS)
            r["text"] = caption
            # keep schema same (text field) but also add synthetic metadata
            r["_meta"] = {"type": "image", "image_sha256": "".join(random.choice("0123456789abcdef") for _ in range(32))}
        else:
            # produce diversified text
            variant_choice = random.random()
            if variant_choice < 0.18:
                # paraphrase template
                text = paraphrase_template(base_text) or base_text
            elif variant_choice < 0.40:
                # abbreviate + typos
                text = apply_abbrevs(base_text)
                text = apply_typos(text, prob_per_word=TYPO_PROB + 0.05)
            else:
                # small edits: punctuation, casing, emoji
                text = base_text
                if random.random() < 0.4:
                    # append contextual phrase or order id
                    text += " " + random.choice(["Thanks", "Please advise", "Order " + random.choice(["A1234","C4321"])])
                text = case_variant(text)
                text = apply_typos(text, prob_per_word=TYPO_PROB)
                text = maybe_add_emoji(text)
            r["text"] = text

        # optionally synthesize a reply (multi-turn). The reply becomes a new "record" linked via in-reply-to id.
        if replies and random.random() < 0.28:
            # create assistant reply as separate record (next in results)
            reply = {
                "id": f"{r['id']}-reply",
                "from": r["to"],     # swapped from/to
                "to": r["from"],
                "text": random.choice([
                    "Sure — can you share your order number?",
                    "We can help. Please share your order ID.",
                    "Done. Your order has been canceled.",
                    "Thanks — tracking number is TRK" + str(random.randint(100000,999999))
                ]),
                "received_at": str(int(r["received_at"]) + random.randint(5, 600))
            }
            # add both as conversation pair; optionally include a conversation_id meta
            r["_meta"] = r.get("_meta", {})
            r["_meta"]["conversation_id"] = f"conv-{random.randint(100000,999999)}"
            reply["_meta"] = {"conversation_id": r["_meta"]["conversation_id"], "in_reply_to": r["id"]}
            results.append(r)
            results.append(reply)
        else:
            results.append(r)

    return results

# ---------- CLI / main ----------

def parse_args():
    p = argparse.ArgumentParser(description="Augment a normalized Airbyte WhatsApp record")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-record", type=str, help="JSON string of a single normalized record")
    group.add_argument("--input-file", type=str, help="JSON file with array of seed records")
    p.add_argument("--n", type=int, default=100, help="Approximate number of augmented records to produce (per seed)")
    p.add_argument("--out", type=str, default="augmented.ndjson", help="Output filename")
    p.add_argument("--ndjson", action="store_true", help="Write newline-delimited JSON (one record per line)")
    p.add_argument("--no-replies", dest="replies", action="store_false", help="Do not synthesize reply messages")
    p.add_argument("--no-image", dest="allow_images", action="store_false", help="Do not generate image-type messages")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    p.add_argument("--variants-per-seed", type=int, default=1, help="Number of batches per seed to multiply outputs (advanced)")
    return p.parse_args()

def main():
    args = parse_args()
    seeds: List[Dict[str, Any]] = []
    if args.input_record:
        seeds = [json.loads(args.input_record)]
    else:
        with open(args.input_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                seeds = data
            else:
                seeds = [data]

    out_records: List[Dict[str, Any]] = []
    for seed_idx, seed in enumerate(seeds):
        n = args.n
        # you can scale by variants_per_seed if needed
        for _ in range(args.variants_per_seed):
            out_records.extend(augment_record(seed,
                                              n=n,
                                              allow_images=args.allow_images,
                                              replies=args.replies,
                                              pseudonymize=True,
                                              seed_random=(args.seed or None)))

    # write output
    if args.ndjson:
        with open(args.out, "w", encoding="utf-8") as fh:
            for rec in out_records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(out_records, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {len(out_records)} records to {args.out}")

if __name__ == "__main__":
    main()
