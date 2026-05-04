import argparse
import json
import sys
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from desktop_env.evaluators.metrics.llm_judge import prepare_artifact_pair


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare result/gold artifacts as LLM-readable previews.")
    parser.add_argument("--result", type=Path, required=True, help="Path to the result artifact.")
    parser.add_argument("--gold", type=Path, required=True, help="Path to the gold artifact.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory to write previews and manifest.")
    parser.add_argument("--artifact-type", type=str, default="", help="Optional artifact type such as dwg, psd, mp4.")
    args = parser.parse_args()

    prepared = prepare_artifact_pair(
        str(args.result),
        str(args.gold),
        args.output_dir,
        artifact_type=args.artifact_type or args.result.suffix.lower().lstrip("."),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = args.output_dir / "manifest.json"
    manifest.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {manifest}")
    print(f"Result previews: {len(prepared['result'].get('previews', []))}")
    print(f"Gold previews: {len(prepared['expected'].get('previews', []))}")


if __name__ == "__main__":
    main()
