
import json
from pathlib import Path


def build_dev_records(split, auto_records, manual_records):
    """Combine labels while trusting only explicit human confirmation."""
    output = []

    for index in split["development"]:
        auto = auto_records[index]
        manual = manual_records[index]

        assert str(auto["listing_id"]) == str(manual["listing_id"])

        verified = manual.get("human_verified") is True
        output.append({
            "source_index": index,
            "listing_id": auto["listing_id"],
            "text": auto["text"],
            "entities": manual["entities"] if verified else auto["entities"],
            "human_verified": verified,
        })

    return output


def main():
    data_dir = Path("data/labeled")

    with (data_dir / "week3_split.json").open(encoding="utf-8") as f:
        split = json.load(f)

    with (data_dir / "week3_auto_labels.jsonl").open(encoding="utf-8") as f:
        auto_records = [json.loads(line) for line in f]

    with (data_dir / "week3_annotations.jsonl").open(encoding="utf-8") as f:
        manual_records = [json.loads(line) for line in f]

    output = build_dev_records(split, auto_records, manual_records)
    output_path = data_dir / "week3_dev_annotations.jsonl"

    # Keep the original safety guard: this generated file may contain
    # human-reviewed work, so regeneration must be an explicit operator action.
    with output_path.open("x", encoding="utf-8") as f:
        for record in output:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("Development records:", len(output))
    print("Human verified:", sum(r["human_verified"] for r in output))
    print("Remaining to review:", sum(not r["human_verified"] for r in output))
    print("Saved:", output_path)


if __name__ == "__main__":
    main()
