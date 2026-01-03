import csv
import requests
import os
from datetime import datetime

API_URL = "http://localhost:8000/query"
LLM_URL = "http://69.48.159.10:30000/v1/chat/completions"
INPUT_FILE = "qa_dataset.csv"
OUTPUT_DIR = "results"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def evaluate_semantic_similarity(question, ground_truth, prediction):
    prompt = f"""
    You are an impartial judge evaluating the quality of an answer to a question.
    
    Question: {question}
    Ground Truth: {ground_truth}
    Prediction: {prediction}
    
    Is the Prediction semantically consistent with the Ground Truth? 
    It doesn't have to be identical, but it must convey the same information.
    If the prediction adds extra correct info, that's fine.
    If the prediction is "I don't know" but the ground truth has an answer, it is incorrect.
    
    Answer only YES or NO.
    """
    
    try:
        r = requests.post(
            LLM_URL,
            json={
                "model": "llama-3.1-70b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            },
            timeout=30
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip().upper()
        return "YES" in content
    except Exception as e:
        print(f"Error calling LLM judge: {e}")
        return False

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
        predicted_answer = pred.get("answer", "")
        ground_truth = item["ground_truth_answer"]
        
        if not predicted_answer:
            print(f"Warning: No answer returned for question {item['question_id']}. Response: {pred}")
            exact_match = False
            is_correct = False
        else:
            exact_match = predicted_answer.strip().lower() == ground_truth.strip().lower()
            
            # Semantic evaluation via LLM
            is_correct = evaluate_semantic_similarity(
                item["question"], 
                ground_truth, 
                predicted_answer
            )

        results.append({
            "question_id": item["question_id"],
            "category": item["category"],
            "question": item["question"],
            "ground_truth": item["ground_truth_answer"],
            "predicted_answer": pred.get("answer", ""),
            "predicted_sources": ";".join(pred.get("source_message_ids", [])),
            "exact_match": exact_match,
            "semantic_similarity": is_correct,  # Now Boolean
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
