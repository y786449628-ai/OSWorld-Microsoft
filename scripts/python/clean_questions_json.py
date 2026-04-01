import argparse
import json
import re
from pathlib import Path


STOP_PATTERNS = [
    r"\n\s*Query\s*[:：]",
    r"\n\s*Subtasks\s*[:：]",
    r"\n\s*Answer\s*[:：]",
    r"\n\s*Options\s*[:：]",
    r"\n\s*Notes\s*[:：]",
    r"\n\s*Query[^A-Za-z0-9\n]{0,10}",
    r"\n\s*Subtasks[^A-Za-z0-9\n]{0,10}",
]


def clean_question_text(text: str) -> str:
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cut_positions = []

    for pattern in STOP_PATTERNS:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            cut_positions.append(match.start())

    if cut_positions:
        normalized = normalized[: min(cut_positions)].strip()

    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean question fields in a questions.json file."
    )
    parser.add_argument("input_file", type=Path, help="Path to input questions.json")
    parser.add_argument("output_file", type=Path, help="Path to cleaned output JSON")
    args = parser.parse_args()

    data = json.loads(args.input_file.read_text(encoding="utf-8"))

    cleaned = []
    for item in data:
        new_item = dict(item)
        new_item["question"] = clean_question_text(item.get("question", ""))
        cleaned.append(new_item)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
