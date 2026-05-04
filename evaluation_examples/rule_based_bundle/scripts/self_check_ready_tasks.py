"""Offline self-check for materialized ready tasks.

Per sampled task, verifies:
  1. evaluator.func resolves to a registered metric in desktop_env.evaluators.metrics.
  2. evaluator.result / evaluator.expected have well-formed type/path fields.
  3. Each upload_file's `local_path` exists on disk (gold files at minimum).
  4. For compare_artifact_with_llm_judge with artifact_type=ai/pdf, the gold
     file actually opens via fitz and renders a non-empty preview.
  5. For compare_images/compare_xlsx_files/compare_pdfs, the gold file opens
     via Pillow / openpyxl / fitz respectively.

The check is offline only: it does not start a VM, so vm_file `path` fields
(Windows paths inside the VM) are validated for shape only.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = ROOT / "evaluation_examples" / "rule_based_bundle"
sys.path.insert(0, str(ROOT))

import desktop_env.evaluators.metrics as metrics  # noqa: E402

APPS = [
    "Adobe Illustrator",
    "CAD",
    "Figma",
    "Microsoft",
    "PS",
    "Premiere",
    "Unreal Engine",
]

ALLOWED_RESULT_TYPES = {
    "vm_file",
    "list_directory",
    "rule",
    "vm_screenshot",
    "vm_command_line",
    "cloud_file",
}


def issue(issues: list, task_id: str, msg: str) -> None:
    issues.append((task_id, msg))


def check_evaluator_shape(task: dict, issues: list) -> None:
    tid = task.get("id", "?")
    ev = task.get("evaluator", {})
    func = ev.get("func")
    if not func:
        issue(issues, tid, "evaluator.func missing")
        return
    if not hasattr(metrics, func):
        issue(issues, tid, f"evaluator.func='{func}' is not registered in metrics")
        return
    for slot in ("result", "expected"):
        block = ev.get(slot)
        if not isinstance(block, dict):
            issue(issues, tid, f"evaluator.{slot} missing or not an object")
            continue
        t = block.get("type")
        if t not in ALLOWED_RESULT_TYPES:
            issue(issues, tid, f"evaluator.{slot}.type='{t}' is unexpected")
        if t == "vm_file":
            if not block.get("path"):
                issue(issues, tid, f"evaluator.{slot}.path missing for vm_file")
            if not block.get("dest"):
                issue(issues, tid, f"evaluator.{slot}.dest missing for vm_file")
        if t == "list_directory" and not block.get("path"):
            issue(issues, tid, f"evaluator.{slot}.path missing for list_directory")
        if t == "rule":
            rules = block.get("rules")
            if not isinstance(rules, dict):
                issue(issues, tid, f"evaluator.{slot}.rules missing for rule")


def check_upload_files_exist(task: dict, issues: list) -> None:
    tid = task.get("id", "?")
    for entry in task.get("config", []) or []:
        if entry.get("type") != "upload_file":
            continue
        for f in entry.get("parameters", {}).get("files", []):
            local = f.get("local_path")
            if not local:
                issue(issues, tid, "upload_file entry missing local_path")
                continue
            full = (ROOT / local).resolve() if not Path(local).is_absolute() else Path(local)
            if not full.exists():
                issue(issues, tid, f"local_path missing on disk: {local}")


def check_gold_renderable(task: dict, issues: list) -> None:
    """Verify that the gold artifact can actually be opened by the inferred reader."""
    tid = task.get("id", "?")
    ev = task.get("evaluator", {})
    func = ev.get("func")

    # Find gold local_path matching expected.path basename if possible.
    expected = ev.get("expected", {}) or {}
    if expected.get("type") != "vm_file":
        return
    expected_path = expected.get("path", "")
    expected_name = Path(expected_path.replace("\\", "/")).name.lower()
    gold_local: Path | None = None
    for entry in task.get("config", []) or []:
        if entry.get("type") != "upload_file":
            continue
        for f in entry.get("parameters", {}).get("files", []):
            vm_p = f.get("path", "")
            if Path(vm_p.replace("\\", "/")).name.lower() == expected_name:
                local = f.get("local_path")
                if local:
                    gold_local = (
                        Path(local) if Path(local).is_absolute() else (ROOT / local).resolve()
                    )
                break
        if gold_local:
            break

    if gold_local is None or not gold_local.exists():
        return  # Already reported by upload-files check.

    suffix = gold_local.suffix.lower()
    try:
        if func == "compare_artifact_with_llm_judge":
            artifact_type = (ev.get("options") or {}).get("artifact_type", "").lower()
            if artifact_type in {"ai", "pdf"}:
                import fitz

                doc = fitz.open(gold_local)
                pages = doc.page_count
                doc.close()
                if pages < 1:
                    issue(issues, tid, f"fitz opened {gold_local.name} but reports 0 pages")
        elif func == "compare_images":
            from PIL import Image

            with Image.open(gold_local) as img:
                img.verify()
        elif func == "compare_pdfs":
            import fitz

            doc = fitz.open(gold_local)
            pages = doc.page_count
            doc.close()
            if pages < 1:
                issue(issues, tid, f"fitz opened {gold_local.name} but 0 pages")
        elif func == "compare_xlsx_files":
            from openpyxl import load_workbook

            wb = load_workbook(gold_local, read_only=True, data_only=True)
            wb.close()
        elif func == "compare_docx_files":
            from docx import Document

            Document(str(gold_local))
        elif func == "compare_pptx_files":
            from pptx import Presentation

            Presentation(str(gold_local))
    except Exception as exc:
        issue(issues, tid, f"gold {gold_local.name} unreadable by {func}: {type(exc).__name__}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-app", type=int, default=8, help="Sample size per app")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--all", action="store_true", help="Check every ready task instead of sampling")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    grand_issues: list = []
    func_seen: Counter = Counter()
    sampled_per_app: dict[str, int] = {}

    for app in APPS:
        test_path = BUNDLE_ROOT / app / "test_rule_based_windows.json"
        test_index = json.loads(test_path.read_text(encoding="utf-8"))
        all_pairs: list[tuple[str, str]] = []
        for cat, ids in test_index.items():
            for tid in ids:
                all_pairs.append((cat, tid))
        if not all_pairs:
            sampled_per_app[app] = 0
            continue
        if args.all:
            sample = all_pairs
        else:
            sample = rng.sample(all_pairs, min(args.per_app, len(all_pairs)))
        sampled_per_app[app] = len(sample)
        app_issues: list = []
        for cat, tid in sample:
            task_path = BUNDLE_ROOT / app / "examples_windows" / cat / f"{tid}.json"
            if not task_path.exists():
                app_issues.append((tid, "task json missing on disk"))
                continue
            task = json.loads(task_path.read_text(encoding="utf-8"))
            func_seen[(app, task.get("evaluator", {}).get("func"))] += 1
            check_evaluator_shape(task, app_issues)
            check_upload_files_exist(task, app_issues)
            check_gold_renderable(task, app_issues)
        if app_issues:
            print(f"\n[{app}]  {len(app_issues)} issues across {len(sample)} samples")
            for tid, msg in app_issues[:30]:
                print(f"  {tid}: {msg}")
            if len(app_issues) > 30:
                print(f"  ... and {len(app_issues)-30} more")
        else:
            print(f"\n[{app}]  OK ({len(sample)} samples checked)")
        grand_issues.extend((app, tid, m) for tid, m in app_issues)

    print("\n=== Summary ===")
    print(f"  total samples:  {sum(sampled_per_app.values())}")
    print(f"  total issues:   {len(grand_issues)}")
    print("\n  evaluator funcs covered by sample:")
    for (app, fn), n in sorted(func_seen.items()):
        print(f"    {app:<22} {fn:<38} {n}")

    if grand_issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
