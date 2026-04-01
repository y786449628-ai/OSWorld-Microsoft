import json
import shutil
from pathlib import Path


WORKSPACE = Path(r"C:\OSWorld")
MICROSOFT_ROOT = WORKSPACE / "Microsoft"
RESOURCE_ROOT = WORKSPACE / "evaluation_examples" / "resources" / "windows_microsoft"
EXAMPLE_ROOTS = [
    WORKSPACE / "evaluation_examples" / "examples_windows" / "excel",
    WORKSPACE / "evaluation_examples" / "examples_windows" / "word",
    WORKSPACE / "evaluation_examples" / "examples_windows" / "ppt",
    WORKSPACE / "evaluation_examples" / "examples_windows" / "multi_app",
]


def to_repo_relative(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


def materialize_file(source: Path) -> Path:
    relative = source.relative_to(MICROSOFT_ROOT)
    destination = RESOURCE_ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination


def rewrite_example(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    rewritten = 0

    for cfg in data.get("config", []):
        if cfg.get("type") != "upload_file":
            continue
        for file_spec in cfg.get("parameters", {}).get("files", []):
            local_path = file_spec.get("local_path")
            if not local_path:
                continue

            source = Path(local_path)
            if not source.exists():
                continue

            if MICROSOFT_ROOT not in source.parents and source.parent != MICROSOFT_ROOT:
                continue

            destination = materialize_file(source)
            file_spec["local_path"] = to_repo_relative(destination)
            rewritten += 1

    if rewritten:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return rewritten


def main() -> None:
    total_examples = 0
    total_refs = 0
    for root in EXAMPLE_ROOTS:
        for example_path in root.glob("*.json"):
            changed = rewrite_example(example_path)
            if changed:
                total_examples += 1
                total_refs += changed
                print(f"Updated {example_path} ({changed} refs)")

    print(f"Done. Updated {total_examples} example files and {total_refs} local_path references.")
    print(f"Resource root: {RESOURCE_ROOT}")


if __name__ == "__main__":
    main()
