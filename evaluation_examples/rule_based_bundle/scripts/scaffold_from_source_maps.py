import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path, PureWindowsPath
from typing import Any


WORKSPACE = Path(r"C:\OSWorld")
SOURCE_ROOT = WORKSPACE / "Microsoft"
BUNDLE_ROOT = WORKSPACE / "evaluation_examples" / "rule_based_bundle"
RESOURCE_ROOT = WORKSPACE / "evaluation_examples" / "resources" / "windows_generated"
TASK_PREFIX = "Microsoft"
DEFAULT_SOURCE_ROOT = SOURCE_ROOT
DEFAULT_BUNDLE_ROOT = BUNDLE_ROOT
DEFAULT_RESOURCE_ROOT = RESOURCE_ROOT


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_uuid_like(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:32]
    return f"{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def task_name_for_index(index: int) -> str:
    return f"{TASK_PREFIX}_{index:02d}"


def vm_user_path(relative_path: str, for_gold: bool = False) -> str:
    # The collected Windows VM used by this benchmark has user 78644.
    base = PureWindowsPath(r"C:\Users\78644\Documents" if for_gold else r"C:\Users\78644\Desktop")
    return str(base / PureWindowsPath(relative_path))


def desktop_relative_path(path: Path) -> str:
    parts = list(path.parts)
    lowered = [part.lower() for part in parts]
    if "desktop" in lowered:
        idx = lowered.index("desktop")
        return Path(*parts[idx + 1 :]).as_posix()
    return path.name


def to_repo_relative(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


def materialize_resource(source: Path) -> Path:
    relative = source.relative_to(SOURCE_ROOT)
    destination = RESOURCE_ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination


def relevant_file(path: Path) -> bool:
    return path.suffix.lower() in {
        ".xlsx",
        ".xls",
        ".docx",
        ".doc",
        ".pptx",
        ".ppt",
        ".pdf",
        ".csv",
        ".txt",
        ".jpg",
        ".jpeg",
        ".png",
        ".psd",
        ".svg",
        ".mp4",
        ".wav",
        ".aac",
        ".prproj",
        ".dwg",
        ".fig",
        ".zip",
        ".uproject",
    }


def choose_domain(apps: list[str]) -> str:
    core = [app for app in apps if app in {"excel", "word", "ppt"}]
    if len(core) > 1:
        return "multi_app"
    if core:
        return core[0]
    return "multi_app"


def list_snapshot_files(task_name: str, snapshot_name: str) -> list[Path]:
    snapshot_dir = SOURCE_ROOT / task_name / "logs" / "MonitoringSnapshots" / snapshot_name / "Desktop"
    if not snapshot_dir.exists():
        return []
    return sorted([p for p in snapshot_dir.rglob("*") if p.is_file()], key=lambda p: str(p).lower())


def extract_open_file_names(text: str) -> list[str]:
    names: list[str] = []
    patterns = [
        r"\bopen(?:\s+the\s+(?:image|project|file|drawing))?\s+['\"]?([^'\"\n\r]+?\.(?:psd|png|jpg|jpeg|svg|mp4|prproj|dwg|fig))['\"]?",
        r"\bimport\s+['\"]?([^'\"\n\r]+?\.(?:psd|png|jpg|jpeg|svg|mp4|prproj|dwg|fig))['\"]?",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            names.append(Path(match.group(1).strip()).name.lower())
    return names


def pick_gold_file(stage: dict[str, Any], files: list[Path]) -> Path | None:
    compare_func = stage.get("evaluator_candidate")
    wanted_exts = {
        "compare_xlsx_files": {".xlsx", ".xls"},
        "compare_docx_files": {".docx", ".doc"},
        "compare_pptx_files": {".pptx", ".ppt"},
        "compare_pdfs": {".pdf"},
        "compare_images": {".png", ".jpg", ".jpeg"},
        "compare_videos": {".mp4"},
        "compare_artifact_with_llm_judge": {".png", ".jpg", ".jpeg", ".pdf", ".mp4"},
        "compare_zip_files": {".zip"},
        "compare_text_file": {".svg"},
    }.get(compare_func, set())
    target_relative_path = stage.get("target_relative_path")
    if target_relative_path:
        normalized_target = target_relative_path.replace("\\", "/").lower()
        for path in files:
            normalized_path = path.as_posix().lower()
            if normalized_path.endswith(f"/desktop/{normalized_target}") or path.name.lower() == Path(normalized_target).name:
                return path
    for path in files:
        if path.suffix.lower() in wanted_exts:
            return path
    for path in files:
        if relevant_file(path):
            return path
    return None


def pick_open_file(stage: dict[str, Any], files: list[Path]) -> Path | None:
    if stage.get("evaluator_candidate") == "compare_directory_tree" and str(stage.get("expected_artifact", "")).lower() == "directory_state":
        return None
    apps = stage.get("apps", [])
    compare_func = stage.get("evaluator_candidate")
    preferred = []
    if compare_func == "compare_docx_files":
        preferred = [".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"]
    elif compare_func == "compare_xlsx_files":
        preferred = [".xlsx", ".xls"]
    elif compare_func == "compare_pptx_files":
        preferred = [".pptx", ".ppt"]
    elif compare_func == "compare_pdfs":
        preferred = [".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"]
    elif compare_func == "compare_images":
        preferred = [".psd", ".dwg", ".fig", ".png", ".jpg", ".jpeg", ".svg"]
    elif compare_func == "compare_videos":
        preferred = [".prproj", ".mp4"]
    elif compare_func == "compare_artifact_with_llm_judge":
        preferred = [".psd", ".dwg", ".fig", ".prproj", ".png", ".jpg", ".jpeg", ".pdf", ".mp4"]
    elif compare_func == "compare_zip_files":
        preferred = [".dwg", ".zip"]
    elif compare_func == "compare_text_file":
        preferred = [".fig", ".svg"]
    elif compare_func == "compare_directory_tree":
        artifact = str(stage.get("expected_artifact") or "").lower()
        if artifact in {"fig", "dwg", "prproj", "uasset", "umap", "uproject"}:
            preferred = [".fig", ".dwg", ".prproj", ".uproject", ".uasset", ".umap"]
    elif "word" in apps:
        preferred = [".docx", ".doc"]
    elif "excel" in apps:
        preferred = [".xlsx", ".xls"]
    elif "ppt" in apps:
        preferred = [".pptx", ".ppt"]

    target_relative_path = stage.get("target_relative_path")
    target_name = Path(target_relative_path).name.lower() if target_relative_path else ""
    for name in extract_open_file_names(stage.get("instruction", "")):
        if name == target_name:
            continue
        for path in files:
            if path.name.lower() == name:
                return path

    if target_relative_path:
        normalized_name = target_name
        for path in files:
            if path.name.lower() == normalized_name:
                return path

    for suffix in preferred:
        for path in files:
            if path.suffix.lower() == suffix:
                return path
    for path in files:
        if relevant_file(path):
            return path
    return None


def is_scaffoldable_stage(stage: dict[str, Any], input_files: list[Path], open_file: Path | None) -> bool:
    if TASK_PREFIX.lower().startswith("unreal"):
        return False
    compare_func = stage.get("evaluator_candidate")
    if compare_func == "compare_videos":
        usable_sources = {".prproj", ".mp4"}
        return open_file is not None and open_file.suffix.lower() in usable_sources
    if compare_func == "compare_directory_tree":
        expected_files = stage.get("directory_expectation", {}).get("files", [])
        if any(str(path).lower().endswith((".uasset", ".umap")) for path in expected_files):
            # Unreal assets require a full project restore, not a single uploaded file.
            return False
    return True


def build_config(input_files: list[Path], open_file: Path | None, gold_file: Path | None) -> list[dict[str, Any]]:
    uploads: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for path in input_files:
        if not relevant_file(path) or path.name in seen_names:
            continue
        seen_names.add(path.name)
        local_source = materialize_resource(path)
        uploads.append(
            {
                "local_path": to_repo_relative(local_source),
                "path": vm_user_path(desktop_relative_path(path), for_gold=False),
            }
        )

    if gold_file is not None:
        gold_name = f"{gold_file.stem}_gold{gold_file.suffix}"
        local_source = materialize_resource(gold_file)
        uploads.append(
            {
                "local_path": to_repo_relative(local_source),
                "path": vm_user_path(gold_name, for_gold=True),
            }
        )

    config: list[dict[str, Any]] = []
    if uploads:
        config.append({"type": "upload_file", "parameters": {"files": uploads}})
    if open_file is not None:
        config.append({"type": "open", "parameters": {"path": vm_user_path(desktop_relative_path(open_file), for_gold=False)}})
    return config


def build_evaluator(stage: dict[str, Any], gold_file: Path | None) -> dict[str, Any]:
    if stage.get("evaluation_hint") == "pending_evaluator" or not stage.get("evaluator_candidate"):
        return {
            "func": "pending_evaluator",
            "result": {"type": "pending"},
            "expected": {"type": "pending"},
            "options": {
                "reason": stage.get("localization", {}).get("reason", "No reliable evaluator is available yet."),
                "input_snapshot": stage.get("input_snapshot") or stage.get("planned_input_snapshot"),
                "gold_snapshot": stage.get("gold_snapshot") or stage.get("planned_gold_snapshot"),
                "target_relative_path": stage.get("target_relative_path"),
                "expected_artifact": stage.get("expected_artifact"),
                "evaluator_candidate": stage.get("evaluator_candidate"),
            },
        }
    compare_func = stage["evaluator_candidate"]
    if compare_func == "compare_directory_tree":
        expectation = stage["directory_expectation"]
        root_relative_path = expectation["root_relative_path"]
        return {
            "func": "compare_directory_tree",
            "result": {
                "type": "list_directory",
                "path": vm_user_path(root_relative_path, for_gold=False),
            },
            "expected": {
                "type": "rule",
                "rules": {
                    "dirs": expectation.get("dirs", []),
                    "files": expectation.get("files", []),
                    "allow_extra": expectation.get("allow_extra", True),
                },
            },
            "options": {"min_nontrivial_actions": 1},
        }

    gold_name = f"{gold_file.stem}_gold{gold_file.suffix}"
    result_name = stage.get("result_relative_path") or stage.get("target_relative_path") or desktop_relative_path(gold_file)
    result_dest = Path(result_name).name
    options: dict[str, Any] = {}

    if compare_func == "compare_xlsx_files":
        options = {
            "ignore_case": True,
            "check_sheet_order": True,
            "check_formats": True,
            "min_nontrivial_actions": 1,
        }
    elif compare_func == "compare_text_file":
        options = {"ignore_blanks": True, "min_nontrivial_actions": 1}
    elif compare_func == "compare_artifact_with_llm_judge":
        options = {
            "instruction": stage.get("instruction", ""),
            "artifact_type": Path(result_name).suffix.lower().lstrip("."),
            "threshold": 0.75,
            "judge_model": "qwen-vl-max",
            "min_nontrivial_actions": 1,
        }

    evaluator: dict[str, Any] = {
        "func": compare_func,
        "result": {"type": "vm_file", "path": vm_user_path(result_name, for_gold=False), "dest": result_dest},
        "expected": {"type": "vm_file", "path": vm_user_path(gold_name, for_gold=True), "dest": gold_name},
    }
    if options:
        evaluator["options"] = options

    if compare_func in {"compare_xlsx_files", "compare_docx_files", "compare_pptx_files", "compare_pdfs"}:
        evaluator["postconfig"] = [
            {
                "type": "activate_window",
                "parameters": {"window_name": result_dest, "strict": False},
            },
            {"type": "sleep", "parameters": {"seconds": 0.5}},
            {
                "type": "execute",
                "parameters": {
                    "command": [
                        "python",
                        "-c",
                        "import pyautogui, time; pyautogui.hotkey('ctrl', 's'); time.sleep(0.5)",
                    ]
                },
            },
            {"type": "sleep", "parameters": {"seconds": 0.5}},
        ]
    return evaluator


def stage_to_example(
    source_map: dict[str, Any],
    stage: dict[str, Any],
    force_pending: bool = False,
    pending_reason: str | None = None,
) -> tuple[dict[str, Any], str]:
    task_name = source_map["source_name"]
    source_id = source_map["source_id"]
    domain = choose_domain(stage.get("apps", []))
    if force_pending:
        stage = dict(stage)
        stage["evaluation_hint"] = "pending_evaluator"
        if pending_reason:
            localization = dict(stage.get("localization", {}))
            localization.setdefault("status", "pending_evaluator")
            localization["reason"] = pending_reason
            stage["localization"] = localization

    input_snapshot = stage.get("input_snapshot") or stage.get("planned_input_snapshot")
    gold_snapshot = stage.get("gold_snapshot") or stage.get("planned_gold_snapshot")
    input_files = list_snapshot_files(task_name, input_snapshot) if input_snapshot else []
    gold_candidates = list_snapshot_files(task_name, gold_snapshot) if gold_snapshot else []
    if stage.get("evaluator_candidate") == "compare_directory_tree":
        gold_file = None
    else:
        gold_file = pick_gold_file(stage, gold_candidates)
        if gold_file is None and not force_pending:
            raise RuntimeError(f"Could not resolve gold file for {task_name} stage {stage['stage_index']}")
    open_file = pick_open_file(stage, input_files)
    if not force_pending and not is_scaffoldable_stage(stage, input_files, open_file):
        raise RuntimeError(f"Stage {task_name}#{stage['stage_index']} has no usable input file for {stage.get('evaluator_candidate')}.")
    example_id = make_uuid_like(f"{source_id}::stage::{stage['stage_index']}")

    example = {
        "id": example_id,
        "snapshot": domain if domain in {"excel", "word", "ppt"} else "excel",
        "instruction": stage["instruction"],
        "source": f"{task_name} true stage {stage['stage_index']}",
        "config": build_config(input_files, open_file, gold_file),
        "trajectory": f"trajectories/{example_id}",
        "related_apps": [app for app in stage.get("apps", []) if app not in {"pdf", "os"}],
        "evaluator": build_evaluator(stage, gold_file),
    }
    return example, domain


def refresh_generated_examples_in_map(source_map: dict[str, Any], examples_root: Path) -> dict[str, Any]:
    lookup = {}
    for path in examples_root.rglob("*.json"):
        data = load_json(path)
        if data.get("source", "").startswith(source_map["source_name"]):
            lookup.setdefault(data["instruction"], []).append(
                {
                    "example_id": data["id"],
                    "domain": path.parent.name,
                    "example_json": to_repo_relative(path),
                }
            )

    for key in ("kept_atomic_tasks", "llm_assisted_atomic_tasks", "unsupported_atomic_tasks"):
        for item in source_map.get(key, []):
            if "generated_examples" in item:
                item.pop("generated_examples")
            matched = lookup.get(item["instruction"], [])
            if matched:
                item["generated_examples"] = matched
    return source_map


def remove_existing_generated_examples(examples_root: Path, task_names: set[str]) -> None:
    if not examples_root.exists():
        return
    for path in examples_root.rglob("*.json"):
        try:
            data = load_json(path)
        except Exception:
            continue
        source = str(data.get("source", ""))
        if any(source.startswith(task_name) for task_name in task_names):
            os.chmod(path, 0o666)
            path.unlink()


def main() -> None:
    global SOURCE_ROOT, BUNDLE_ROOT, RESOURCE_ROOT, TASK_PREFIX
    parser = argparse.ArgumentParser(description="Scaffold runnable OSWorld examples from true-stage source maps.")
    parser.add_argument("--dataset-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--bundle-root", type=Path, default=BUNDLE_ROOT)
    parser.add_argument("--resource-root", type=Path, default=RESOURCE_ROOT)
    parser.add_argument("--task-prefix", type=str, default=TASK_PREFIX)
    parser.add_argument("--source-maps-dir", type=Path, default=BUNDLE_ROOT / "source_maps")
    parser.add_argument("--examples-root", type=Path, default=BUNDLE_ROOT / "examples_windows")
    parser.add_argument("--meta-output", type=Path, default=BUNDLE_ROOT / "test_rule_based_windows.json")
    parser.add_argument("--pending-output", type=Path, default=BUNDLE_ROOT / "pending_evaluator_windows.json")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=2)
    args = parser.parse_args()
    SOURCE_ROOT = args.dataset_root
    BUNDLE_ROOT = args.bundle_root
    RESOURCE_ROOT = args.resource_root
    TASK_PREFIX = args.task_prefix
    if args.source_maps_dir == DEFAULT_BUNDLE_ROOT / "source_maps":
        args.source_maps_dir = BUNDLE_ROOT / "source_maps"
    if args.examples_root == DEFAULT_BUNDLE_ROOT / "examples_windows":
        args.examples_root = BUNDLE_ROOT / "examples_windows"
    if args.meta_output == DEFAULT_BUNDLE_ROOT / "test_rule_based_windows.json":
        args.meta_output = BUNDLE_ROOT / "test_rule_based_windows.json"
    if args.pending_output == DEFAULT_BUNDLE_ROOT / "pending_evaluator_windows.json":
        args.pending_output = BUNDLE_ROOT / "pending_evaluator_windows.json"
    if args.resource_root == DEFAULT_RESOURCE_ROOT:
        RESOURCE_ROOT = WORKSPACE / "evaluation_examples" / "resources" / f"windows_{TASK_PREFIX.lower().replace(' ', '_')}"

    grouped: dict[str, set[str]] = {"excel": set(), "word": set(), "ppt": set(), "multi_app": set()}
    pending_grouped: dict[str, set[str]] = {"excel": set(), "word": set(), "ppt": set(), "multi_app": set()}
    task_names = {task_name_for_index(idx) for idx in range(args.start, args.end + 1)}
    remove_existing_generated_examples(args.examples_root, task_names)

    for idx in range(args.start, args.end + 1):
        task_name = task_name_for_index(idx)
        map_path = args.source_maps_dir / f"{task_name}.json"
        if not map_path.exists():
            continue
        source_map = load_json(map_path)
        seen_stage_indices: set[int] = set()

        for stage in source_map.get("kept_atomic_tasks", []):
            seen_stage_indices.add(stage.get("stage_index"))
            try:
                example, domain = stage_to_example(source_map, stage)
                out = args.examples_root / domain / f"{example['id']}.json"
                save_json(out, example)
                if example["evaluator"].get("func") == "pending_evaluator":
                    pending_grouped.setdefault(domain, set()).add(example["id"])
                else:
                    grouped.setdefault(domain, set()).add(example["id"])
            except RuntimeError as exc:
                try:
                    example, domain = stage_to_example(source_map, stage, force_pending=True, pending_reason=str(exc))
                except RuntimeError:
                    continue
                out = args.examples_root / domain / f"{example['id']}.json"
                save_json(out, example)
                pending_grouped.setdefault(domain, set()).add(example["id"])

        for key in ("llm_assisted_atomic_tasks", "unsupported_atomic_tasks"):
            for stage in source_map.get(key, []):
                stage_index = stage.get("stage_index")
                if stage_index in seen_stage_indices:
                    continue
                seen_stage_indices.add(stage_index)
                reason = stage.get("localization", {}).get("reason") or stage.get("reason") or f"Stage is recorded in {key} and awaits a runnable evaluator."
                try:
                    example, domain = stage_to_example(source_map, stage, force_pending=True, pending_reason=reason)
                except RuntimeError:
                    continue
                out = args.examples_root / domain / f"{example['id']}.json"
                save_json(out, example)
                pending_grouped.setdefault(domain, set()).add(example["id"])

        refreshed = refresh_generated_examples_in_map(source_map, args.examples_root)
        save_json(map_path, refreshed)

    meta = {domain: sorted(ids) for domain, ids in grouped.items() if ids}
    pending_meta = {domain: sorted(ids) for domain, ids in pending_grouped.items() if ids}
    save_json(args.meta_output, meta)
    save_json(args.pending_output, pending_meta)
    print(f"Saved examples to {args.examples_root}")
    print(f"Saved meta to {args.meta_output}")
    print(f"Saved pending evaluator meta to {args.pending_output}")


if __name__ == "__main__":
    main()
