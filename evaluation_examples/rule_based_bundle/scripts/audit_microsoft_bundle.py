import csv
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


WORKSPACE = Path(r"C:\OSWorld")
BUNDLE_ROOT = WORKSPACE / "evaluation_examples" / "rule_based_bundle" / "Microsoft"
SOURCE_MAP_ROOT = BUNDLE_ROOT / "source_maps"
EXAMPLES_ROOT = BUNDLE_ROOT / "examples_windows"
EXAMPLES_OSWORLD_ROOT = BUNDLE_ROOT / "examples_windows_osworld"
DATASET_ROOT = WORKSPACE / "Microsoft"
REPORT_JSON = BUNDLE_ROOT / "microsoft_task_cleaning_report.json"
REPORT_CSV = BUNDLE_ROOT / "microsoft_task_cleaning_report.csv"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def expected_evaluator(expected_artifact: str | None) -> str | None:
    mapping = {
        "directory_state": "compare_directory_tree",
        "docx": "compare_docx_files",
        "doc": "compare_docx_files",
        "xlsx": "compare_xlsx_files",
        "xls": "compare_xlsx_files",
        "pptx": "compare_pptx_files",
        "ppt": "compare_pptx_files",
        "pdf": "compare_pdfs",
        "png": "compare_images",
        "jpg": "compare_images",
        "jpeg": "compare_images",
        "svg": "compare_text_file",
        "mp4": "compare_videos",
        "zip": "compare_zip_files",
    }
    return mapping.get((expected_artifact or "").lower())


def normalize_relative(path: Path, base: Path) -> str:
    rel = path.relative_to(base).as_posix()
    return "" if rel == "." else rel


def snapshot_desktop_root(source_map_name: str, snapshot_name: str) -> Path:
    return DATASET_ROOT / source_map_name / "logs" / "MonitoringSnapshots" / snapshot_name / "Desktop"


def snapshot_tree(root: Path) -> dict[str, set[str]]:
    dirs: set[str] = set()
    files: set[str] = set()
    if not root.exists():
        return {"dirs": dirs, "files": files}
    for path in root.rglob("*"):
        rel = normalize_relative(path, root)
        if path.is_dir():
            dirs.add(rel)
        else:
            files.add(rel)
    return {"dirs": dirs, "files": files}


def snapshot_diff(source_map_name: str, input_snapshot: str | None, gold_snapshot: str | None) -> dict[str, list[str]]:
    if not input_snapshot or not gold_snapshot:
        return {"dirs_added": [], "dirs_removed": [], "files_added": [], "files_removed": []}
    before = snapshot_tree(snapshot_desktop_root(source_map_name, input_snapshot))
    after = snapshot_tree(snapshot_desktop_root(source_map_name, gold_snapshot))
    return {
        "dirs_added": sorted(after["dirs"] - before["dirs"]),
        "dirs_removed": sorted(before["dirs"] - after["dirs"]),
        "files_added": sorted(after["files"] - before["files"]),
        "files_removed": sorted(before["files"] - after["files"]),
    }


def extract_first_quoted(text: str) -> str | None:
    match = re.search(r"['\"]([^'\"]+)['\"]", text)
    return match.group(1).strip() if match else None


def replace_first_quoted(text: str, new_value: str) -> str:
    return re.sub(r"(['\"])([^'\"]+)(['\"])", lambda m: f"{m.group(1)}{new_value}{m.group(3)}", text, count=1)


def artifact_alignment(expected_artifact: str | None, func: str | None) -> bool:
    expected = expected_evaluator(expected_artifact)
    if expected_artifact == "directory_state":
        return func == "compare_directory_tree"
    if expected is None:
        return True
    return expected == func


def build_directory_evaluator(folder_name: str) -> dict[str, Any]:
    return {
        "func": "compare_directory_tree",
        "result": {
            "type": "list_directory",
            "path": r"C:\Users\78644\Desktop",
        },
        "expected": {
            "type": "rule",
            "rules": {
                "dirs": [folder_name],
                "files": [],
                "allow_extra": True,
            },
        },
        "options": {
            "min_nontrivial_actions": 1,
        },
    }


def classify_task(
    source_map_name: str,
    kept_task: dict[str, Any],
    candidate_by_stage: dict[int, dict[str, Any]],
    example: dict[str, Any],
) -> dict[str, Any]:
    example_func = example.get("evaluator", {}).get("func")
    expected_artifact = kept_task.get("expected_artifact")
    merged_indices = kept_task.get("merged_stage_indices") or [kept_task.get("stage_index")]
    merged_candidates = [candidate_by_stage[idx] for idx in merged_indices if idx in candidate_by_stage]
    merged_artifacts = sorted({str(item.get("expected_artifact")) for item in merged_candidates if item.get("expected_artifact")})
    primary_artifact = str(expected_artifact)
    other_artifact_candidates = [item for item in merged_candidates if str(item.get("expected_artifact")) != primary_artifact]
    diff = snapshot_diff(source_map_name, kept_task.get("input_snapshot"), kept_task.get("gold_snapshot"))
    notes: list[str] = []
    status = "qualified"
    snapshot_support = "full"
    recommended_fix = ""

    if not artifact_alignment(expected_artifact, example_func):
        status = "unqualified"
        notes.append(
            f"Evaluator mismatch: expected {expected_evaluator(expected_artifact)} for artifact {expected_artifact}, got {example_func}."
        )

    localization_reason = ((kept_task.get("localization") or {}).get("reason") or "").strip()
    if localization_reason:
        notes.append(localization_reason)

    created_dir_conflict = False
    actual_created_dirs = diff["dirs_added"]
    if expected_artifact == "directory_state" and re.search(r"create a new folder named", example.get("instruction", ""), re.I):
        intended_name = extract_first_quoted(example.get("instruction", "")) or extract_first_quoted(kept_task.get("instruction", ""))
        if len(actual_created_dirs) == 1:
            actual_name = Path(actual_created_dirs[0]).parts[0]
            if intended_name and intended_name != actual_name:
                created_dir_conflict = True
                status = "unqualified"
                notes.append(
                    f"Snapshot mismatch: instruction asks for folder '{intended_name}', but the input/gold snapshots add '{actual_name}'."
                )

    if status != "unqualified" and other_artifact_candidates:
        status = "partial"
        notes.append(
            "Merged stage spans multiple artifact types: "
            + ", ".join(sorted({str(item.get('expected_artifact')) for item in other_artifact_candidates}))
            + "."
        )
        supports = []
        for item in other_artifact_candidates:
            bench = item.get("benchmarkability")
            evidence = (item.get("snapshot_evidence") or "").lower()
            observed = "no observable" not in evidence
            supports.append(observed and bench == "benchmarkable")
        snapshot_support = "partial" if any(supports) else "missing"
        if snapshot_support == "missing":
            notes.append("Original snapshots do not provide separate observable transitions for the extra artifact targets.")
            recommended_fix = "Keep as partial or rewrite the instruction to the retained artifact only."
        else:
            notes.append("Original snapshots include observable transitions for at least one extra artifact stage.")
            recommended_fix = "Split the merged task into separate examples using the intermediate snapshots."

    if status == "qualified":
        snapshot_support = "full"
    elif status == "unqualified":
        snapshot_support = "conflict"

    if status == "unqualified" and expected_artifact == "directory_state":
        folder_name = ""
        if len(actual_created_dirs) == 1:
            folder_name = Path(actual_created_dirs[0]).parts[0]
        if folder_name:
            recommended_fix = f"Switch to compare_directory_tree on Desktop with dirs=[{folder_name!r}] and align the instruction to the snapshot."
        else:
            recommended_fix = "Switch to compare_directory_tree and rebuild from the original snapshots."
    elif status == "unqualified" and not recommended_fix:
        recommended_fix = "Realign the evaluator/result artifact with the kept stage in source_maps."

    return {
        "status": status,
        "snapshot_support": snapshot_support,
        "notes": notes,
        "recommended_fix": recommended_fix,
        "merged_artifacts": merged_artifacts,
        "snapshot_diff": diff,
        "created_dir_conflict": created_dir_conflict,
    }


def apply_directory_fix(
    source_map_name: str,
    source_map_path: Path,
    kept_task: dict[str, Any],
    example_path: Path,
) -> dict[str, Any] | None:
    if kept_task.get("expected_artifact") != "directory_state":
        return None
    if kept_task.get("evaluator_candidate") == "compare_directory_tree":
        return None

    diff = snapshot_diff(source_map_name, kept_task.get("input_snapshot"), kept_task.get("gold_snapshot"))
    if len(diff["dirs_added"]) != 1:
        return None

    folder_name = Path(diff["dirs_added"][0]).parts[0]
    source_map = load_json(source_map_path)
    example = load_json(example_path)

    actual_instruction = replace_first_quoted(example["instruction"], folder_name) if extract_first_quoted(example.get("instruction", "")) else example["instruction"]

    for task in source_map.get("kept_atomic_tasks", []):
        if task.get("generated_examples"):
            for generated in task["generated_examples"]:
                if generated.get("example_json") == example_path.relative_to(WORKSPACE).as_posix():
                    task["instruction"] = actual_instruction
                    task["evaluator_candidate"] = "compare_directory_tree"
                    task["directory_expectation"] = {
                        "root_relative_path": "",
                        "dirs": [folder_name],
                        "files": [],
                        "allow_extra": True,
                    }
                    task["result_relative_path"] = ""
                    task["target_relative_path"] = folder_name
                    task["localization"] = {
                        **(task.get("localization") or {}),
                        "status": "localized_fixed",
                        "confidence": 0.95,
                        "reason": f"Corrected to a directory-state evaluator using the observed snapshot transition for '{folder_name}'.",
                    }
                    break

    save_json(source_map_path, source_map)

    example["instruction"] = actual_instruction
    example["config"] = []
    example["related_apps"] = []
    example["evaluator"] = build_directory_evaluator(folder_name)
    save_json(example_path, example)

    osworld_copy = EXAMPLES_OSWORLD_ROOT / example_path.relative_to(EXAMPLES_ROOT)
    if osworld_copy.exists():
        save_json(osworld_copy, example)

    return {
        "folder_name": folder_name,
        "instruction": actual_instruction,
        "example_path": example_path.relative_to(WORKSPACE).as_posix(),
    }


def audit(apply_fixes: bool = False) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []

    for source_map_path in sorted(SOURCE_MAP_ROOT.glob("Microsoft_*.json")):
        source_map_name = source_map_path.stem
        source_map = load_json(source_map_path)
        candidate_by_stage = {int(task["stage_index"]): task for task in source_map.get("candidate_atomic_tasks", [])}

        if apply_fixes:
            for kept_task in source_map.get("kept_atomic_tasks", []):
                for generated in kept_task.get("generated_examples", []):
                    example_path = WORKSPACE / generated["example_json"]
                    fixed = apply_directory_fix(source_map_name, source_map_path, kept_task, example_path)
                    if fixed:
                        fixes.append({"source_map": source_map_name, **fixed})

        source_map = load_json(source_map_path)
        candidate_by_stage = {int(task["stage_index"]): task for task in source_map.get("candidate_atomic_tasks", [])}

        for kept_task in source_map.get("kept_atomic_tasks", []):
            for generated in kept_task.get("generated_examples", []):
                example_path = WORKSPACE / generated["example_json"]
                example = load_json(example_path)
                classification = classify_task(source_map_name, kept_task, candidate_by_stage, example)
                row = {
                    "source_map": source_map_name,
                    "example_id": generated["example_id"],
                    "domain": generated["domain"],
                    "stage_index": kept_task.get("stage_index"),
                    "instruction": example.get("instruction", ""),
                    "current_evaluator": example.get("evaluator", {}).get("func"),
                    "expected_artifact": kept_task.get("expected_artifact"),
                    "status": classification["status"],
                    "snapshot_support": classification["snapshot_support"],
                    "input_snapshot": kept_task.get("input_snapshot"),
                    "gold_snapshot": kept_task.get("gold_snapshot"),
                    "merged_stage_indices": kept_task.get("merged_stage_indices") or [kept_task.get("stage_index")],
                    "merged_artifacts": classification["merged_artifacts"],
                    "example_json": generated["example_json"],
                    "notes": " | ".join(classification["notes"]),
                    "recommended_fix": classification["recommended_fix"],
                }
                rows.append(row)

    rows.sort(key=lambda item: (item["status"], item["source_map"], item["stage_index"], item["example_id"]))
    counts = {
        "qualified": sum(1 for row in rows if row["status"] == "qualified"),
        "partial": sum(1 for row in rows if row["status"] == "partial"),
        "unqualified": sum(1 for row in rows if row["status"] == "unqualified"),
    }

    report = {
        "summary": {
            "total_examples": len(rows),
            **counts,
            "applied_fixes": len(fixes),
        },
        "applied_fixes": fixes,
        "rows": rows,
    }
    save_json(REPORT_JSON, report)

    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_map",
                "example_id",
                "domain",
                "stage_index",
                "instruction",
                "current_evaluator",
                "expected_artifact",
                "status",
                "snapshot_support",
                "input_snapshot",
                "gold_snapshot",
                "merged_stage_indices",
                "merged_artifacts",
                "example_json",
                "notes",
                "recommended_fix",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **row,
                    "merged_stage_indices": json.dumps(row["merged_stage_indices"], ensure_ascii=False),
                    "merged_artifacts": json.dumps(row["merged_artifacts"], ensure_ascii=False),
                }
            )

    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Audit and optionally fix the Microsoft rule-based bundle.")
    parser.add_argument("--apply-fixes", action="store_true", help="Apply safe evaluator fixes before emitting the report.")
    args = parser.parse_args()

    report = audit(apply_fixes=args.apply_fixes)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if report["applied_fixes"]:
        print("Applied fixes:")
        for item in report["applied_fixes"]:
            print(json.dumps(item, ensure_ascii=False))
    print(f"JSON report: {REPORT_JSON}")
    print(f"CSV report: {REPORT_CSV}")


if __name__ == "__main__":
    main()
