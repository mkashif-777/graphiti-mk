import csv
import json

INPUT_CSV = "qa_dataset.csv"
INPUT_JSONL = "whatsapp_synthetic_events.jsonl"
OUTPUT_CSV = "qa_dataset_curated.csv"

def main():
    # Load JSONL content for checking existence
    print(f"Reading {INPUT_JSONL}...")
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        jsonl_content = f.read().lower()

    curated_rows = []
    removed_count = 0
    total_count = 0

    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            total_count += 1
            qid = row["question_id"]
            category = row["category"]
            answer = row["ground_truth_answer"].strip()
            
            # Logic: Keep if "Null" category OR Answer exists in JSONL
            keep = False
            
            if "null" in category.lower():
                keep = True
            elif answer.lower() in jsonl_content:
                keep = True
            
            if keep:
                curated_rows.append(row)
            else:
                removed_count += 1
                # print(f"Removed Q{qid}: Answer '{answer}' not found in logs.")

    print(f"Total Questions: {total_count}")
    print(f"Kept: {len(curated_rows)}")
    print(f"Removed: {removed_count}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(curated_rows)

    print(f"Saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
