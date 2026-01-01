import csv
import requests
import os
from datetime import datetime

API_URL = "http://localhost:8102/query"
INPUT_FILE = "qa_dataset.csv"
OUTPUT_DIR = "results"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

results = []

# ---- Load QA dataset (CSV) ----
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for item in reader:
        # Parse semicolon-separated strings back into lists
        user_ids = [u.strip() for u in item["user_ids"].split(";")] if item["user_ids"] else []
        message_ids = [m.strip() for m in item["message_ids"].split(";")] if item["message_ids"] else []

        # ---- Call Query API ----
        try:
            r = requests.post(
                API_URL,
                json={
                    "query": item["question"],
                    "answer_type": item["answer_type"],
                    "expected_group_id": item["group_id"],
                    "expected_user_ids": user_ids,
                    "expected_message_ids": message_ids
                },
                timeout=120
            )
            r.raise_for_status()
            pred = r.json()
        except Exception as e:
            print(f"Error querying question {item['question_id']}: {e}")
            continue

        # ---- Evaluation ----
        exact_match = pred["answer"].strip().lower() == item["ground_truth_answer"].strip().lower()

        results.append({
            "question_id": item["question_id"],
            "category": item["category"],
            "question": item["question"],
            "ground_truth": item["ground_truth_answer"],
            "predicted_answer": pred.get("answer", ""),
            "predicted_sources": ";".join(pred.get("source_message_ids", [])),
            "exact_match": exact_match,
            "semantic_similarity": None,  # Placeholder for LLM-based scorer
            "source_node_overlap": None   # Placeholder for set intersection logic
        })

# ---- Persist results to CSV only ----
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = f"{OUTPUT_DIR}/benchmark_results_{timestamp}.csv"

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"Benchmark complete. Results saved to: {csv_path}")
print(f"Total questions evaluated: {len(results)}")