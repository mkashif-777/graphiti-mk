import json
import csv
import requests
from datetime import datetime

API_URL = "http://69.48.159.10:8102/query"

results = []

# ---- Load QA dataset (JSONL) ----
with open("qa_dataset.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue

        item = json.loads(line)

        # ---- Call Query API ----
        r = requests.post(
            API_URL,
            json={"query": item["question"]},
            timeout=30
        )
        r.raise_for_status()
        pred = r.json()

        # ---- Optional evaluation hooks (placeholders) ----
        exact_match = (
            pred["answer"].strip().lower()
            == item["ground_truth_answer"].strip().lower()
        )

        # Semantic similarity and graph grounding
        # You can replace these later with real scorers
        semantic_similarity = None
        source_node_overlap = None

        results.append({
            "question_id": item["question_id"],
            "question": item["question"],
            "ground_truth": item["ground_truth_answer"],
            "predicted_answer": pred["answer"],
            "predicted_sources": pred.get("source_message_ids", []),
            "exact_match": exact_match,
            "semantic_similarity": semantic_similarity,
            "source_node_overlap": source_node_overlap,
        })

# ---- Persist results ----
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Save JSON (authoritative artifact)
json_path = f"results/benchmark_results_{timestamp}.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Save CSV (human-friendly)
csv_path = f"results/benchmark_results_{timestamp}.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "question_id",
            "question",
            "ground_truth",
            "predicted_answer",
            "predicted_sources",
            "exact_match",
            "semantic_similarity",
            "source_node_overlap",
        ],
    )
    writer.writeheader()
    writer.writerows(results)

print(f"Saved JSON results to {json_path}")
print(f"Saved CSV results to {csv_path}")
print(f"Total questions evaluated: {len(results)}")
