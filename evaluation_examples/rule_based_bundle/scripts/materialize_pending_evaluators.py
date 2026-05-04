"""Materialize pending tasks whose evaluator can be filled in mechanically.

Stage-1 (deterministic comparators):
    - directory_state  -> compare_directory_tree (presence-only)
    - jpeg              -> compare_images
    - pdf               -> compare_pdfs
    - xlsx, xlsx|pdf    -> compare_xlsx_files

Stage-2 (opaque binary artifacts):
    - ai      -> compare_artifact_with_llm_judge (renders via fitz PDF stream)
    - dwg     -> compare_directory_tree (presence-only fallback; no OSS renderer)
    - uasset  -> compare_directory_tree (presence-only fallback; per-asset render
                  needs UE editor)

Excluded (need task-author revision):
    - mixed, visual: no reliable user-facing artifact

For each materialized task:
    - The task JSON's `evaluator` block is replaced with the runnable evaluator.
    - The id is removed from `pending_evaluator_windows.json`.
    - The id is appended to `test_rule_based_windows.json` under the same category
      (idempotent: skipped if already present).

Default behavior is dry-run. Pass --apply to write changes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path, PureWindowsPath
from typing import Any

BUNDLE_ROOT = Path(r"C:\OSWorld\evaluation_examples\rule_based_bundle")
APPS = [
    "Adobe Illustrator",
    "CAD",
    "Figma",
    "Microsoft",
    "PS",
    "Premiere",
    "Unreal Engine",
]
DEFAULT_DESKTOP = PureWindowsPath(r"C:\Users\78644\Desktop")

STAGE1_ARTIFACTS = {"directory_state", "jpeg", "pdf", "xlsx", "xlsx|pdf"}
# Stage-2 binary artifacts: "ai" gets LLM judge with fitz preview, "dwg" and
# "uasset" fall back to presence-only because no open-source renderer is wired
# in. These can be upgraded later by adding converters.
STAGE2_LLM_JUDGE_ARTIFACTS = {"ai", "dwg"}
STAGE2_PRESENCE_ONLY_ARTIFACTS = {"uasset"}
SUPPORTED_ARTIFACTS = (
    STAGE1_ARTIFACTS | STAGE2_LLM_JUDGE_ARTIFACTS | STAGE2_PRESENCE_ONLY_ARTIFACTS
)

# Filenames that the Unreal Engine editor regenerates as part of normal startup
# / build cache. Snapshots can capture these as the only changed files when
# the planner failed to capture a real asset diff. Materializing a task whose
# only signal is one of these produces a free-pass evaluator, so we treat them
# as "no real artifact" and refuse to use them as working paths.
BOILERPLATE_BASENAMES = {
    "extra_urls.txt",
    "myproject.uproject",
    "ddckey-editor.txt",
    "autoscreenshot.png",
}


def _desktop_relative_from_local(local_path: str | None) -> str | None:
    """Recover the post-Desktop relative path from a snapshot's local_path."""
    if not local_path:
        return None
    parts = Path(local_path.replace("\\", "/")).parts
    lowered = [p.lower() for p in parts]
    if "desktop" not in lowered:
        return None
    idx = lowered.index("desktop")
    rel = parts[idx + 1 :]
    return "\\".join(rel) if rel else None


def _is_boilerplate(path: str | None) -> bool:
    if not path:
        return False
    return PureWindowsPath(path).name.lower() in BOILERPLATE_BASENAMES


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def extract_paths(task: dict) -> tuple[str | None, str | None]:
    """Return (working_path, gold_path) using config + target_relative_path fallback.

    The gold's `local_path` (post-Desktop portion) is the most reliable signal
    for where the working file should live in the VM. We use it as the highest
    priority signal. Boilerplate engine cache files (extra_urls.txt etc.) are
    rejected as working paths even when no better candidate exists, because
    they produce free-pass evaluators when the snapshot pair didn't capture a
    real artifact change.
    """
    cfg = task.get("config", []) or []
    uploads: list[dict] = []
    open_paths: list[str] = []
    for entry in cfg:
        if entry.get("type") == "upload_file":
            uploads.extend(entry.get("parameters", {}).get("files", []))
        elif entry.get("type") == "open":
            p = entry.get("parameters", {}).get("path")
            if p:
                open_paths.append(p)

    gold_uploads = [u for u in uploads if "_gold" in u.get("path", "").lower()]
    desktop_uploads = [
        u["path"]
        for u in uploads
        if "Desktop" in u.get("path", "") and "_gold" not in u["path"].lower()
    ]

    gold_entry = gold_uploads[0] if gold_uploads else None
    gold = gold_entry["path"] if gold_entry else None
    target = task.get("evaluator", {}).get("options", {}).get("target_relative_path")

    # Working filename hint: gold-name minus _gold, or target_relative_path's basename.
    expected_name: str | None = None
    if gold:
        gold_name = PureWindowsPath(gold).name
        stem, _, ext = gold_name.rpartition(".")
        if stem.lower().endswith("_gold"):
            expected_name = f"{stem[:-len('_gold')]}.{ext}"
    if expected_name is None and target:
        expected_name = PureWindowsPath(target).name

    def _matches_expected(candidate: str) -> bool:
        return expected_name is not None and PureWindowsPath(candidate).name.lower() == expected_name.lower()

    working: str | None = None

    # 1) Best signal: gold's snapshot local_path tells us the file's true VM
    #    location relative to Desktop.
    if gold_entry:
        rel = _desktop_relative_from_local(gold_entry.get("local_path"))
        if rel:
            working = str(DEFAULT_DESKTOP / PureWindowsPath(rel))

    # 2) An open step that explicitly references the expected working file.
    if working is None:
        for candidate in open_paths:
            if _matches_expected(candidate):
                working = candidate
                break

    # 3) A Desktop upload whose basename matches the expected working file.
    if working is None:
        for candidate in desktop_uploads:
            if _matches_expected(candidate):
                working = candidate
                break

    # 4) target_relative_path resolved against Desktop.
    if working is None and target:
        working = str(DEFAULT_DESKTOP / PureWindowsPath(target))

    # 5) Strip `_gold` suffix from gold basename, default to Desktop root.
    if working is None and expected_name:
        working = str(DEFAULT_DESKTOP / expected_name)

    # Boilerplate guard: refuse to materialize a task whose only working-path
    # candidate is an Unreal engine cache file. Such tasks pass for free.
    if _is_boilerplate(working):
        return None, gold

    return working, gold


def build_evaluator(artifact: str, working: str, gold: str, instruction: str = "") -> dict:
    work_p = PureWindowsPath(working)
    gold_p = PureWindowsPath(gold)

    if artifact in STAGE2_PRESENCE_ONLY_ARTIFACTS or artifact == "directory_state":
        parent = str(work_p.parent)
        return {
            "func": "compare_directory_tree",
            "result": {"type": "list_directory", "path": parent},
            "expected": {
                "type": "rule",
                "rules": {
                    "dirs": [],
                    "files": [work_p.name],
                    "allow_extra": True,
                },
            },
            "options": {"min_nontrivial_actions": 1},
        }

    if artifact == "jpeg":
        return {
            "func": "compare_images",
            "result": {"type": "vm_file", "path": working, "dest": work_p.name},
            "expected": {"type": "vm_file", "path": gold, "dest": gold_p.name},
        }

    if artifact == "pdf":
        return {
            "func": "compare_pdfs",
            "result": {"type": "vm_file", "path": working, "dest": work_p.name},
            "expected": {"type": "vm_file", "path": gold, "dest": gold_p.name},
        }

    if artifact in {"xlsx", "xlsx|pdf"}:
        return {
            "func": "compare_xlsx_files",
            "result": {"type": "vm_file", "path": working, "dest": work_p.name},
            "expected": {"type": "vm_file", "path": gold, "dest": gold_p.name},
            "options": {
                "ignore_case": True,
                "check_sheet_order": True,
                "check_formats": True,
                "min_nontrivial_actions": 1,
            },
        }

    if artifact in STAGE2_LLM_JUDGE_ARTIFACTS:
        return {
            "func": "compare_artifact_with_llm_judge",
            "result": {"type": "vm_file", "path": working, "dest": work_p.name},
            "expected": {"type": "vm_file", "path": gold, "dest": gold_p.name},
            "options": {
                "instruction": instruction,
                "artifact_type": artifact,
                "threshold": 0.75,
                "judge_model": "qwen-vl-max",
            },
        }

    raise ValueError(f"Unsupported artifact: {artifact}")


def process_app(app: str, apply: bool) -> Counter:
    counter: Counter = Counter()
    app_dir = BUNDLE_ROOT / app
    pending_path = app_dir / "pending_evaluator_windows.json"
    test_path = app_dir / "test_rule_based_windows.json"

    pending = load_json(pending_path)
    test_index = load_json(test_path)
    if not isinstance(test_index, dict):
        raise RuntimeError(f"Unexpected test_rule_based_windows.json shape in {app}")

    new_pending: dict[str, list[str]] = {}
    for category, ids in pending.items():
        kept: list[str] = []
        listed_in_test = set(test_index.get(category, []))
        for tid in ids:
            task_path = app_dir / "examples_windows" / category / f"{tid}.json"
            if not task_path.exists():
                counter[(app, "missing_file")] += 1
                kept.append(tid)
                continue

            task = load_json(task_path)
            opt = task.get("evaluator", {}).get("options", {})
            artifact = opt.get("expected_artifact")
            if artifact not in SUPPORTED_ARTIFACTS:
                counter[(app, f"skip_artifact:{artifact}")] += 1
                kept.append(tid)
                continue

            working, gold = extract_paths(task)
            presence_only = (
                artifact == "directory_state"
                or artifact in STAGE2_PRESENCE_ONLY_ARTIFACTS
            )
            need_gold = not presence_only
            if not working or (need_gold and not gold):
                counter[(app, f"skip_no_paths:{artifact}")] += 1
                kept.append(tid)
                continue

            evaluator = build_evaluator(
                artifact,
                working,
                gold or working,  # gold unused when presence_only
                instruction=task.get("instruction", ""),
            )
            if apply:
                task["evaluator"] = evaluator
                save_json(task_path, task)
                if tid not in listed_in_test:
                    test_index.setdefault(category, []).append(tid)
                    listed_in_test.add(tid)
            counter[(app, f"materialized:{artifact}")] += 1

        if kept:
            new_pending[category] = kept

    if apply:
        save_json(pending_path, new_pending)
        save_json(test_path, test_index)

    return counter


def _make_pending_evaluator(reason: str) -> dict:
    return {
        "func": "pending_evaluator",
        "result": {"type": "pending"},
        "expected": {"type": "pending"},
        "options": {
            "reason": reason,
            "expected_artifact": "boilerplate_only",
        },
    }


def fix_boilerplate_targets(app: str, apply: bool) -> Counter:
    """For ready tasks whose presence-only check targets a known UE boilerplate
    file, re-derive the working path with the latest extract_paths logic.

    - If a real working path is recoverable, rewrite the evaluator.
    - Otherwise, demote the task back to pending with a clear reason.
    """
    counter: Counter = Counter()
    app_dir = BUNDLE_ROOT / app
    test_path = app_dir / "test_rule_based_windows.json"
    pending_path = app_dir / "pending_evaluator_windows.json"
    test_index = load_json(test_path)
    pending_index = load_json(pending_path)
    if not isinstance(test_index, dict) or not isinstance(pending_index, dict):
        raise RuntimeError(f"Unexpected JSON shape in {app}")

    for category, ids in list(test_index.items()):
        kept_in_test: list[str] = []
        demoted: list[str] = []
        for tid in ids:
            task_path = app_dir / "examples_windows" / category / f"{tid}.json"
            if not task_path.exists():
                kept_in_test.append(tid)
                continue
            task = load_json(task_path)
            ev = task.get("evaluator", {})
            if ev.get("func") != "compare_directory_tree":
                kept_in_test.append(tid)
                continue
            files = ev.get("expected", {}).get("rules", {}).get("files") or []
            checks_boilerplate = any(f.lower() in BOILERPLATE_BASENAMES for f in files)
            if not checks_boilerplate:
                kept_in_test.append(tid)
                continue

            # Try to recover a real working path with current logic.
            working, gold = extract_paths(task)
            if working and not _is_boilerplate(working):
                # Rebuild the evaluator with the recovered path. Treat it as
                # directory_state presence-only (the evaluator family did not
                # change, just the path).
                new_ev = build_evaluator(
                    "directory_state", working, gold or working,
                    instruction=task.get("instruction", ""),
                )
                if apply:
                    task["evaluator"] = new_ev
                    save_json(task_path, task)
                counter[(app, "fixed_in_place")] += 1
                kept_in_test.append(tid)
            else:
                # No real artifact; demote.
                if apply:
                    task["evaluator"] = _make_pending_evaluator(
                        "Snapshot diff captured only Unreal engine cache files; "
                        "no real user-facing artifact to evaluate."
                    )
                    save_json(task_path, task)
                counter[(app, "demoted_to_pending")] += 1
                demoted.append(tid)

        if apply:
            test_index[category] = kept_in_test
            if demoted:
                pending_index.setdefault(category, []).extend(demoted)

    if apply:
        save_json(test_path, test_index)
        save_json(pending_path, pending_index)
    return counter


def remap_app(app: str, target_artifact: str, apply: bool) -> Counter:
    """Re-route already-materialized tasks whose working-file extension matches
    `target_artifact` to the current routing for that artifact (e.g. dwg moves
    from presence-only to LLM judge after a converter is added).

    A task is eligible if it's currently using compare_directory_tree presence-only
    and the file basename being checked has the expected extension.
    """
    counter: Counter = Counter()
    app_dir = BUNDLE_ROOT / app
    test_path = app_dir / "test_rule_based_windows.json"
    test_index = load_json(test_path)
    if not isinstance(test_index, dict):
        raise RuntimeError(f"Unexpected test_rule_based_windows.json shape in {app}")

    target_suffix = "." + target_artifact.lower()

    for category, ids in test_index.items():
        for tid in list(ids):
            task_path = app_dir / "examples_windows" / category / f"{tid}.json"
            if not task_path.exists():
                continue
            task = load_json(task_path)
            ev = task.get("evaluator", {})
            if ev.get("func") != "compare_directory_tree":
                continue
            files = ev.get("expected", {}).get("rules", {}).get("files") or []
            if not files:
                continue
            if not any(f.lower().endswith(target_suffix) for f in files):
                continue

            working, gold = extract_paths(task)
            if not working:
                counter[(app, "remap_skip_no_working")] += 1
                continue
            if not gold:
                counter[(app, "remap_skip_no_gold")] += 1
                continue

            new_ev = build_evaluator(
                target_artifact, working, gold, instruction=task.get("instruction", "")
            )
            if apply:
                task["evaluator"] = new_ev
                save_json(task_path, task)
            counter[(app, f"remap:{target_artifact}->{new_ev['func']}")] += 1

    return counter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--app",
        choices=APPS,
        action="append",
        help="Limit to specific apps (repeatable). Default: all apps.",
    )
    parser.add_argument(
        "--remap",
        choices=["dwg"],
        action="append",
        help=(
            "Re-route already-materialized tasks. e.g. --remap dwg moves CAD "
            "presence-only checks to LLM judge after a converter is added."
        ),
    )
    parser.add_argument(
        "--fix-boilerplate-targets",
        action="store_true",
        help=(
            "Repair ready tasks whose presence-only check targets a UE engine "
            "cache file (extra_urls.txt etc.). Recovers the real working path "
            "when possible; demotes the task back to pending otherwise."
        ),
    )
    args = parser.parse_args()

    apps = args.app or APPS
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== materialize_pending_evaluators [{mode}] ===")

    if args.fix_boilerplate_targets:
        print("\n--- Fix pass: boilerplate-target tasks ---")
        grand: Counter = Counter()
        for app in apps:
            c = fix_boilerplate_targets(app, args.apply)
            grand.update(c)
            if any(a == app for (a, _) in c.keys()):
                print(f"\n[{app}]")
                for (a, k), v in sorted(c.items()):
                    if a == app:
                        print(f"    {k}: {v}")
        print(f"\nFix totals: {dict(grand)}")
        if not args.apply:
            print("\n(dry-run) re-run with --apply to write changes.")
        return

    if args.remap:
        for art in args.remap:
            print(f"\n--- Remap pass: artifact={art} ---")
            grand: Counter = Counter()
            for app in apps:
                c = remap_app(app, art, args.apply)
                grand.update(c)
                if any(a == app for (a, _) in c.keys()):
                    print(f"\n[{app}]")
                    for (a, k), v in sorted(c.items()):
                        if a == app:
                            print(f"    {k}: {v}")
            print(f"\nRemap totals: {dict(grand)}")
        if not args.apply:
            print("\n(dry-run) re-run with --apply to write changes.")
        return

    grand = Counter()
    for app in apps:
        c = process_app(app, args.apply)
        grand.update(c)
        materialized = sum(v for (a, k), v in c.items() if a == app and k.startswith("materialized:"))
        skipped = sum(v for (a, k), v in c.items() if a == app and not k.startswith("materialized:"))
        print(f"\n[{app}]  materialized={materialized}  skipped={skipped}")
        for (a, k), v in sorted(c.items()):
            if a != app:
                continue
            print(f"    {k}: {v}")

    print("\n=== Totals ===")
    total_done = sum(v for (_, k), v in grand.items() if k.startswith("materialized:"))
    total_skipped = sum(v for (_, k), v in grand.items() if not k.startswith("materialized:"))
    print(f"  materialized total: {total_done}")
    print(f"  skipped total:      {total_skipped}")
    by_artifact: Counter = Counter()
    for (_, k), v in grand.items():
        if k.startswith("materialized:"):
            by_artifact[k.split(":", 1)[1]] += v
    for art, n in sorted(by_artifact.items()):
        print(f"    materialized {art}: {n}")
    if not args.apply:
        print("\n(dry-run) re-run with --apply to write changes.")


if __name__ == "__main__":
    main()
