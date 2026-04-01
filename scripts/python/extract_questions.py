import argparse
import hashlib
import json
import re
from pathlib import Path


SECTION_STOP_HEADERS = (
    "Query:",
    "Subtasks:",
    "Answer:",
    "Options:",
    "Notes:",
)


def generate_id_from_filename(path: Path) -> str:
    digest = hashlib.sha1(path.stem.encode("utf-8")).hexdigest()
    return digest[:12]


def extract_question(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    pattern = re.compile(
        r"Question:\s*(.*?)(?=\n(?:"
        + "|".join(re.escape(header) for header in SECTION_STOP_HEADERS)
        + r")|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(normalized)
    if not match:
        return ""
    return match.group(1).strip()


def extract_from_directory(input_dir: Path) -> list[dict]:
    results = []
    for txt_path in sorted(input_dir.glob("*.txt")):
        raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
        results.append(
            {
                "file_name": txt_path.name,
                "id": generate_id_from_filename(txt_path),
                "question": extract_question(raw_text),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Question sections from txt files in the current directory only."
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing txt files")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output JSON file path",
    )
    args = parser.parse_args()

    if not args.input_dir.exists() or not args.input_dir.is_dir():
        raise SystemExit(
            f"Input directory does not exist or is not a directory: {args.input_dir}"
        )

    extracted = extract_from_directory(args.input_dir)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(extracted, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(extracted, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
