import argparse
import json
from pathlib import Path
from typing import Any

import localize_stage_plans as localizer


WORKSPACE = Path(r"C:\OSWorld")
BUNDLE_ROOT = WORKSPACE / "evaluation_examples" / "rule_based_bundle"
SOURCE_ROOT = WORKSPACE / "Microsoft"
TASK_PREFIX = "Microsoft"


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def task_name_for_index(index: int) -> str:
    return f"{TASK_PREFIX}_{index:02d}"


def office_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {}
    for key in ("sheet_names", "worksheet_count", "nonempty_cells", "chart_count"):
        if before.get(key) != after.get(key):
            delta[key] = {"from": before.get(key), "to": after.get(key)}
    before_ws = before.get("worksheets", [])
    after_ws = after.get("worksheets", [])
    if before_ws or after_ws:
        delta["headers"] = {
            "from": [header for ws in before_ws for header in ws.get("headers", [])][:20],
            "to": [header for ws in after_ws for header in ws.get("headers", [])][:20],
        }
    return delta


def transition_report(task_name: str) -> dict[str, Any]:
    names = localizer.snapshot_names(task_name)
    manifests = [localizer.build_manifest(task_name, name) for name in names]
    transitions = []
    for idx in range(1, len(manifests)):
        before = manifests[idx - 1]
        after = manifests[idx]
        before_files = before["files"]
        after_files = after["files"]
        before_dirs = set(before["dirs"])
        after_dirs = set(after["dirs"])
        files_added = sorted(set(after_files) - set(before_files))
        files_removed = sorted(set(before_files) - set(after_files))
        files_changed = []
        for rel in sorted(set(before_files) & set(after_files)):
            if before_files[rel].get("size") == after_files[rel].get("size"):
                continue
            item = {
                "path": rel,
                "suffix": after_files[rel].get("suffix"),
                "size": {"from": before_files[rel].get("size"), "to": after_files[rel].get("size")},
            }
            delta = office_delta(before_files[rel].get("summary", {}), after_files[rel].get("summary", {}))
            if delta:
                item["office_delta"] = delta
            files_changed.append(item)

        raw = {
            "files_added": files_added,
            "files_removed": files_removed,
            "files_changed": files_changed,
            "dirs_added": sorted(after_dirs - before_dirs),
            "dirs_removed": sorted(before_dirs - after_dirs),
            "changed_file_count": localizer.changed_file_count(before, after),
        }
        explanation = explain_transition(raw)
        transitions.append(
            {
                "transition_index": idx,
                "from": before["snapshot"],
                "to": after["snapshot"],
                "human_summary": explanation["human_summary"],
                "likely_stage": explanation["likely_stage"],
                "confidence": explanation["confidence"],
                "evidence": explanation["evidence"],
                "raw_changes": raw,
            }
        )
    return {"source_name": task_name, "snapshot_count": len(names), "transitions": transitions}


def explain_transition(raw: dict[str, Any]) -> dict[str, Any]:
    files_added = raw["files_added"]
    files_removed = raw["files_removed"]
    files_changed = raw["files_changed"]
    dirs_added = raw["dirs_added"]
    evidence: dict[str, Any] = {}

    if dirs_added:
        evidence["dirs_added"] = dirs_added[:10]
        return {
            "human_summary": f"New directories appeared: {', '.join(dirs_added[:5])}.",
            "likely_stage": "create or organize folders",
            "confidence": 0.82,
            "evidence": evidence,
        }

    if files_added and files_removed:
        evidence["files_added"] = files_added[:10]
        evidence["files_removed"] = files_removed[:10]
        return {
            "human_summary": "Files appeared and disappeared, suggesting a save-as, rename, or move operation.",
            "likely_stage": "save, rename, or move files",
            "confidence": 0.72,
            "evidence": evidence,
        }

    if files_added:
        evidence["files_added"] = files_added[:10]
        return {
            "human_summary": f"New files appeared: {', '.join(files_added[:5])}.",
            "likely_stage": "create or save file",
            "confidence": 0.78,
            "evidence": evidence,
        }

    office_items = [item for item in files_changed if item.get("office_delta")]
    if office_items:
        item = office_items[0]
        delta = item["office_delta"]
        evidence["file"] = item["path"]
        evidence["office_delta"] = delta
        summary_parts = []
        likely = []
        confidence = 0.75
        if "nonempty_cells" in delta:
            before = delta["nonempty_cells"]["from"]
            after = delta["nonempty_cells"]["to"]
            summary_parts.append(f"spreadsheet content changed from {before} to {after} non-empty cells")
            likely.append("enter or edit spreadsheet data")
            confidence = max(confidence, 0.86)
        if "sheet_names" in delta:
            summary_parts.append("worksheet names changed")
            likely.append("rename worksheet")
            confidence = max(confidence, 0.86)
        if "chart_count" in delta:
            before = delta["chart_count"]["from"]
            after = delta["chart_count"]["to"]
            summary_parts.append(f"chart/drawing count changed from {before} to {after}")
            likely.append("create or modify chart")
            confidence = max(confidence, 0.9)
        headers = delta.get("headers", {})
        added_headers = [h for h in headers.get("to", []) if h not in headers.get("from", [])]
        if added_headers:
            evidence["headers_added"] = added_headers[:12]
            summary_parts.append(f"new visible headers or values include: {', '.join(added_headers[:6])}")
        if not summary_parts:
            summary_parts.append("Office document content changed")
            likely.append("edit Office document")
        return {
            "human_summary": f"{item['path']} changed: " + "; ".join(summary_parts) + ".",
            "likely_stage": " + ".join(likely) if likely else "edit Office document",
            "confidence": confidence,
            "evidence": evidence,
        }

    if files_changed:
        evidence["files_changed"] = [{"path": item["path"], "size": item["size"]} for item in files_changed[:10]]
        return {
            "human_summary": "One or more files changed size, but no detailed Office feature delta was detected.",
            "likely_stage": "formatting, metadata, save, or subtle document edit",
            "confidence": 0.45,
            "evidence": evidence,
        }

    return {
        "human_summary": "No observable file or directory change was detected between these snapshots.",
        "likely_stage": "no observable benchmark state change",
        "confidence": 0.2,
        "evidence": {},
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [f"# {report['source_name']} Snapshot Transition Report", ""]
    for item in report["transitions"]:
        lines.append(f"## {item['transition_index']}. {item['from']} -> {item['to']}")
        lines.append(f"- Summary: {item['human_summary']}")
        lines.append(f"- Likely stage: {item['likely_stage']}")
        lines.append(f"- Confidence: {item['confidence']}")
        if item.get("evidence"):
            lines.append("- Evidence:")
            for key, value in item["evidence"].items():
                lines.append(f"  - {key}: `{json.dumps(value, ensure_ascii=False)}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    global SOURCE_ROOT, BUNDLE_ROOT, TASK_PREFIX
    parser = argparse.ArgumentParser(description="Build human-readable snapshot transition reports.")
    parser.add_argument("--dataset-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--bundle-root", type=Path, default=BUNDLE_ROOT)
    parser.add_argument("--task-prefix", type=str, default=TASK_PREFIX)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=BUNDLE_ROOT / "reports")
    args = parser.parse_args()
    SOURCE_ROOT = args.dataset_root
    BUNDLE_ROOT = args.bundle_root
    TASK_PREFIX = args.task_prefix
    localizer.configure(SOURCE_ROOT, BUNDLE_ROOT, TASK_PREFIX)
    if args.output_dir == Path(r"C:\OSWorld") / "evaluation_examples" / "rule_based_bundle" / "reports":
        args.output_dir = BUNDLE_ROOT / "reports"

    for idx in range(args.start, args.end + 1):
        task_name = task_name_for_index(idx)
        report = transition_report(task_name)
        save_json(args.output_dir / f"{task_name}_snapshot_report.json", report)
        write_markdown(report, args.output_dir / f"{task_name}_snapshot_report.md")
        print(f"Saved snapshot report for {task_name}: {len(report['transitions'])} transitions")


if __name__ == "__main__":
    main()
