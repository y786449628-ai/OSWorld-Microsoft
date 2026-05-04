import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    import dashscope  # type: ignore
except Exception:  # pragma: no cover
    dashscope = None

try:
    import localize_stage_plans as localizer
    from localize_stage_plans import build_manifest as build_snapshot_manifest
    from localize_stage_plans import changed_file_count as count_snapshot_file_changes
    from localize_stage_plans import snapshot_names as list_snapshot_names
except Exception:  # pragma: no cover
    localizer = None
    build_snapshot_manifest = None
    count_snapshot_file_changes = None
    list_snapshot_names = None


BUNDLE_ROOT = Path(r"C:\OSWorld\evaluation_examples\rule_based_bundle")
SOURCE_ROOT = Path(r"C:\OSWorld\Microsoft")
TASK_PREFIX = "Microsoft"
DEFAULT_SOURCE_ROOT = SOURCE_ROOT
DEFAULT_BUNDLE_ROOT = BUNDLE_ROOT


KNOWN_TASK_KINDS = {
    "filesystem_create_folder": {"apps": ["os"], "artifact": "directory_state", "evaluation": "rule_based"},
    "filesystem_create_subfolders": {"apps": ["os"], "artifact": "directory_state", "evaluation": "rule_based"},
    "filesystem_move_or_classify_files": {"apps": ["os"], "artifact": "directory_state", "evaluation": "rule_based"},
    "excel_create_or_open_workbook": {"apps": ["excel"], "artifact": "xlsx", "evaluation": "rule_based"},
    "excel_rename_sheet": {"apps": ["excel"], "artifact": "xlsx", "evaluation": "rule_based"},
    "excel_enter_data": {"apps": ["excel"], "artifact": "xlsx", "evaluation": "rule_based"},
    "excel_calculate_formula": {"apps": ["excel"], "artifact": "xlsx", "evaluation": "rule_based"},
    "excel_format_cells": {"apps": ["excel"], "artifact": "xlsx", "evaluation": "rule_based"},
    "excel_create_chart": {"apps": ["excel"], "artifact": "xlsx", "evaluation": "rule_based"},
    "word_create_document": {"apps": ["word"], "artifact": "docx", "evaluation": "rule_based"},
    "word_edit_text_or_title": {"apps": ["word"], "artifact": "docx", "evaluation": "rule_based"},
    "word_insert_table_or_image": {"apps": ["word"], "artifact": "docx", "evaluation": "rule_based"},
    "ppt_create_or_edit_slide": {"apps": ["ppt"], "artifact": "pptx", "evaluation": "rule_based"},
    "cross_app_transfer_visible_artifact": {"apps": ["excel", "word"], "artifact": "docx", "evaluation": "rule_based"},
    "export_pdf": {"apps": ["word"], "artifact": "pdf", "evaluation": "rule_based"},
    "clipboard_only": {"apps": ["os"], "artifact": "clipboard", "evaluation": "unsupported"},
    "visual_ocr_or_semantic_extraction": {"apps": ["os"], "artifact": "mixed", "evaluation": "llm_assisted"},
    "ambiguous_state_or_layout": {"apps": ["os"], "artifact": "mixed", "evaluation": "llm_assisted"},
}


DECOMPOSITION_PROMPT = """You are constructing atomic desktop benchmark tasks.
Plan benchmark-friendly stages from the raw Question, trajectory, and snapshot transitions.

Return strict JSON only:
{
  "benchmarkable_stages": [
    {
      "stage_name": "short_snake_case",
      "instruction": "Could you ...?",
      "task_kind": "one of known_task_kinds or a clear new snake_case kind",
      "apps": ["os" | "excel" | "word" | "ppt"],
      "expected_artifact": "directory_state|xlsx|docx|pptx|pdf|clipboard|mixed",
      "evaluation_hint": "rule_based|llm_assisted|unsupported",
      "depends_on": [1, 2],
      "trajectory_start": 1,
      "trajectory_end": 3,
      "trajectory_evidence": "brief evidence from trajectory actions",
      "planned_input_snapshot": "snapshot name from snapshot_transition_summaries",
      "planned_gold_snapshot": "snapshot name from snapshot_transition_summaries",
      "snapshot_evidence": "brief evidence from snapshot transition summaries",
      "benchmarkability": "benchmarkable|needs_review",
      "reason": "brief reason"
    }
  ]
}

Rules:
1. Do not decompose semantically first. Use snapshot transitions to decide what can become a benchmark stage.
2. A benchmarkable stage must have an observable input snapshot and gold snapshot from snapshot_transition_summaries.
3. Prefer stages with clean, distinct snapshot evidence.
4. If adjacent semantic steps do not have separate clean snapshot transitions, merge them into one coarser benchmark stage with a valid input/gold transition.
5. Do not skip semantic steps. Transient or non-evaluable steps must be merged into the nearest neighboring benchmark stage so the final stages form a complete executable workflow.
6. Each stage should be as atomic as the snapshots allow; it may contain multiple semantic steps only when they share one observable transition.
7. Avoid unsupported stages. If clipboard-only, visual extraction, or semantic classification is necessary for the workflow, merge it into the nearest artifact-producing stage and mark that coarser stage llm_assisted when needed.
8. Mark OCR, visual extraction, or semantic classification as llm_assisted unless the final artifact alone is enough.
9. Keep order faithful to the user task and trajectory hints.
10. Bind every stage to the smallest continuous trajectory action range that supports it.
11. planned_input_snapshot and planned_gold_snapshot must be different, and planned_gold_snapshot must be later.
12. If a final save/export creates no observable state change, merge it with the preceding content-producing stage.
13. Do not invent requirements absent from Question, trajectory, or snapshot transitions.
14. The union of all benchmarkable_stages must cover the full user-intended workflow from initial state to final artifact.
"""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def task_name_for_index(index: int) -> str:
    return f"{TASK_PREFIX}_{index:02d}"


def normalize_instruction(text: Any, fallback_idx: int) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if not cleaned:
        return f"Could you complete atomic stage {fallback_idx}?"
    if cleaned.lower().startswith("could you"):
        return cleaned if cleaned.endswith("?") else f"{cleaned}?"
    stem = cleaned[:-1] if cleaned.endswith("?") else cleaned.rstrip(".")
    return f"Could you {stem[0].lower() + stem[1:] if stem else stem}?"


def normalize_apps(value: Any, task_kind: str) -> list[str]:
    apps = [str(item).lower() for item in value] if isinstance(value, list) else []
    if not apps and task_kind in KNOWN_TASK_KINDS:
        apps = list(KNOWN_TASK_KINDS[task_kind]["apps"])
    allowed = {"os", "excel", "word", "ppt"}
    deduped: list[str] = []
    for app in apps:
        if app in allowed and app not in deduped:
            deduped.append(app)
    return deduped or ["os"]


def normalize_stage(raw_stage: dict[str, Any], idx: int) -> dict[str, Any]:
    task_kind = str(raw_stage.get("task_kind") or raw_stage.get("kind") or f"custom_stage_{idx}").strip()
    defaults = KNOWN_TASK_KINDS.get(task_kind, {})
    evaluation_hint = str(raw_stage.get("evaluation_hint") or defaults.get("evaluation") or "llm_assisted").strip()
    if evaluation_hint not in {"rule_based", "llm_assisted", "unsupported"}:
        evaluation_hint = "llm_assisted"
    depends_on = raw_stage.get("depends_on", [])
    if not isinstance(depends_on, list):
        depends_on = []

    return {
        "stage_index": idx,
        "stage_name": str(raw_stage.get("stage_name") or f"stage_{idx}").strip(),
        "instruction": normalize_instruction(raw_stage.get("instruction"), idx),
        "task_kind": task_kind,
        "apps": normalize_apps(raw_stage.get("apps"), task_kind),
        "expected_artifact": str(raw_stage.get("expected_artifact") or defaults.get("artifact") or "mixed").strip(),
        "evaluation_hint": evaluation_hint,
        "depends_on": [int(item) for item in depends_on if str(item).isdigit()],
        "trajectory_start": normalize_optional_int(raw_stage.get("trajectory_start")),
        "trajectory_end": normalize_optional_int(raw_stage.get("trajectory_end")),
        "trajectory_evidence": str(raw_stage.get("trajectory_evidence") or "").strip(),
        "planned_input_snapshot": normalize_optional_str(raw_stage.get("planned_input_snapshot")),
        "planned_gold_snapshot": normalize_optional_str(raw_stage.get("planned_gold_snapshot")),
        "snapshot_evidence": str(raw_stage.get("snapshot_evidence") or "").strip(),
        "benchmarkability": str(raw_stage.get("benchmarkability") or "benchmarkable").strip(),
        "reason": str(raw_stage.get("reason") or "").strip(),
        "input_snapshot": None,
        "gold_snapshot": None,
        "linked_preview_tasks": [],
    }


def normalize_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"null", "none"}:
        return None
    return cleaned


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def load_trajectory_hints(task_name: str) -> list[dict[str, Any]]:
    data_path = SOURCE_ROOT / task_name / "data.json"
    if not data_path.exists():
        return []
    try:
        payload = load_json(data_path)
    except Exception:
        return []
    hints: list[dict[str, Any]] = []
    for idx, action in enumerate(payload.get("actions", []), start=1):
        instruction = (action or {}).get("instruct", "")
        if instruction and instruction.strip():
            hints.append({"index": idx, "instruction": instruction.strip()})
    return hints


def load_snapshot_report(task_name: str) -> dict[str, Any] | None:
    report_path = BUNDLE_ROOT / "reports" / f"{task_name}_snapshot_report.json"
    if not report_path.exists():
        return None
    try:
        return load_json(report_path)
    except Exception:
        return None


def build_snapshot_transition_summaries(task_name: str, max_file_examples: int = 8) -> list[dict[str, Any]]:
    if build_snapshot_manifest is None or count_snapshot_file_changes is None or list_snapshot_names is None:
        return []
    names = list_snapshot_names(task_name)
    manifests = [build_snapshot_manifest(task_name, name) for name in names]
    summaries: list[dict[str, Any]] = []
    for idx in range(1, len(manifests)):
        before = manifests[idx - 1]
        after = manifests[idx]
        before_files = before.get("files", {})
        after_files = after.get("files", {})
        before_dirs = set(before.get("dirs", []))
        after_dirs = set(after.get("dirs", []))

        added_files = sorted(set(after_files) - set(before_files))
        removed_files = sorted(set(before_files) - set(after_files))
        changed_files = []
        for rel in sorted(set(before_files) & set(after_files)):
            if before_files[rel].get("size") == after_files[rel].get("size"):
                continue
            entry = {
                "path": rel,
                "suffix": after_files[rel].get("suffix"),
                "size": f"{before_files[rel].get('size')} -> {after_files[rel].get('size')}",
            }
            before_summary = before_files[rel].get("summary", {})
            after_summary = after_files[rel].get("summary", {})
            if before_summary or after_summary:
                entry["office_delta"] = summarize_office_delta(before_summary, after_summary)
            changed_files.append(entry)

        likely_actions = infer_likely_actions(added_files, removed_files, changed_files, before_dirs, after_dirs)
        summaries.append(
            {
                "transition_index": idx,
                "from": before["snapshot"],
                "to": after["snapshot"],
                "dirs_added": sorted(after_dirs - before_dirs)[:max_file_examples],
                "dirs_removed": sorted(before_dirs - after_dirs)[:max_file_examples],
                "files_added": added_files[:max_file_examples],
                "files_removed": removed_files[:max_file_examples],
                "files_changed": changed_files[:max_file_examples],
                "changed_file_count": count_snapshot_file_changes(before, after),
                "likely_actions": likely_actions,
            }
        )
    return summaries


def summarize_office_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {}
    for key in ("sheet_names", "worksheet_count", "nonempty_cells", "chart_count"):
        before_value = before.get(key)
        after_value = after.get(key)
        if before_value != after_value:
            delta[key] = {"from": before_value, "to": after_value}
    before_worksheets = before.get("worksheets", [])
    after_worksheets = after.get("worksheets", [])
    if before_worksheets or after_worksheets:
        delta["worksheets"] = {
            "from": before_worksheets[:3],
            "to": after_worksheets[:3],
        }
    return delta


def infer_likely_actions(
    added_files: list[str],
    removed_files: list[str],
    changed_files: list[dict[str, Any]],
    before_dirs: set[str],
    after_dirs: set[str],
) -> list[str]:
    actions: list[str] = []
    if after_dirs - before_dirs:
        actions.append("create_directory")
    if added_files:
        actions.append("file_created_or_saved_as")
    if removed_files:
        actions.append("file_removed_or_moved")
    if added_files and removed_files:
        actions.append("file_renamed_or_moved")
    for item in changed_files:
        delta = item.get("office_delta", {})
        if "sheet_names" in delta:
            actions.append("rename_sheet")
        if "nonempty_cells" in delta:
            actions.append("edit_spreadsheet_content")
        if "chart_count" in delta:
            actions.append("create_or_modify_chart")
        if item.get("suffix") in {"docx", "doc"}:
            actions.append("edit_word_document")
        if item.get("suffix") in {"pptx", "ppt"}:
            actions.append("edit_presentation")
    deduped: list[str] = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def decompose_with_llm(
    question: str,
    preview: dict[str, Any],
    trajectory_hints: list[dict[str, Any]],
    snapshot_transition_summaries: list[dict[str, Any]],
    model: str,
) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]], str | None]:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return None, [], "DASHSCOPE_API_KEY is not set."

    payload = {
        "question": question,
        "preview_atomic_tasks": preview.get("atomic_tasks", []),
        "trajectory_hints": trajectory_hints,
        "snapshot_transition_summaries": snapshot_transition_summaries,
        "known_task_kinds": sorted(KNOWN_TASK_KINDS.keys()),
    }

    if dashscope is not None:
        try:
            dashscope.api_key = api_key
            response = dashscope.Generation.call(
                model=model,
                temperature=0.0,
                top_p=0.8,
                result_format="message",
                messages=[
                    {"role": "system", "content": DECOMPOSITION_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            if response.status_code != 200:
                return None, [], f"DashScope status={response.status_code}, message={getattr(response, 'message', '')}"
            content = response["output"]["choices"][0]["message"]["content"]
            parsed = extract_json_object(content)
            stages = parsed.get("benchmarkable_stages") or parsed.get("candidate_stages", [])
            if not isinstance(stages, list) or not stages:
                return None, [], "DashScope response did not contain benchmarkable_stages."
            return [normalize_stage(stage, idx) for idx, stage in enumerate(stages, start=1)], [], None
        except Exception as exc:
            dashscope_error = f"DashScope SDK call failed: {exc}"
    else:
        dashscope_error = "dashscope package is unavailable."

    if OpenAI is None:
        return None, [], f"{dashscope_error}; openai package is unavailable."

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        response = client.chat.completions.create(
            model=model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": DECOMPOSITION_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        content = response.choices[0].message.content or ""
        parsed = extract_json_object(content)
        stages = parsed.get("benchmarkable_stages") or parsed.get("candidate_stages", [])
        if not isinstance(stages, list) or not stages:
            return None, [], f"{dashscope_error}; OpenAI-compatible response did not contain benchmarkable_stages."
        return [normalize_stage(stage, idx) for idx, stage in enumerate(stages, start=1)], [], None
    except Exception as exc:
        return None, [], f"{dashscope_error}; OpenAI-compatible call failed: {exc}"


def fallback_from_preview(preview: dict[str, Any]) -> list[dict[str, Any]]:
    stages = []
    for idx, instruction in enumerate(preview.get("atomic_tasks", []), start=1):
        stages.append(
            normalize_stage(
                {
                    "stage_name": f"preview_stage_{idx}",
                    "instruction": instruction,
                    "task_kind": "ambiguous_state_or_layout",
                    "evaluation_hint": "llm_assisted",
                    "reason": "Fallback from existing preview because LLM decomposition was unavailable.",
                },
                idx,
            )
        )
    return stages


def map_preview_tasks(preview: dict[str, Any], stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preview_tasks = []
    for idx, instruction in enumerate(preview.get("atomic_tasks", []), start=1):
        lowered = instruction.lower()
        mapped = [
            stage["stage_index"]
            for stage in stages
            if stage["instruction"].lower().replace("could you ", "").strip("?") in lowered
        ]
        preview_tasks.append({"task_index": idx, "instruction": instruction, "mapped_stage_indices": mapped})
    return preview_tasks


def snapshot_names(task_name: str) -> list[str]:
    snap_root = SOURCE_ROOT / task_name / "logs" / "MonitoringSnapshots"
    if not snap_root.exists():
        return []
    return sorted(p.name for p in snap_root.iterdir() if p.is_dir())


def build_stage_record(
    task_name: str,
    question_item: dict[str, Any],
    preview: dict[str, Any],
    model: str,
    use_llm: bool,
) -> dict[str, Any]:
    trajectory_hints = load_trajectory_hints(task_name)
    snapshot_report = load_snapshot_report(task_name)
    snapshot_transition_summaries = (
        snapshot_report.get("transitions", []) if snapshot_report else build_snapshot_transition_summaries(task_name)
    )
    if use_llm:
        stages, skipped_stages, llm_error = decompose_with_llm(
            question_item["question"],
            preview,
            trajectory_hints,
            snapshot_transition_summaries,
            model,
        )
    else:
        stages, skipped_stages, llm_error = None, [], "LLM decomposition disabled by --no-llm."
    source = "snapshot_aware_llm_planning" if stages else "preview_fallback"
    if not stages:
        stages = fallback_from_preview(preview)

    preview_atomic_tasks = map_preview_tasks(preview, stages)
    for stage in stages:
        stage["linked_preview_tasks"] = [
            item["task_index"] for item in preview_atomic_tasks if stage["stage_index"] in item["mapped_stage_indices"]
        ]

    return {
        "source_name": task_name,
        "source_file": question_item["file_name"],
        "source_id": question_item["id"],
        "source_question": question_item["question"],
        "preview_model": preview.get("model"),
        "preview_atomic_tasks": preview_atomic_tasks,
        "candidate_atomic_tasks": stages,
        "kept_atomic_tasks": [],
        "llm_assisted_atomic_tasks": stages,
        "unsupported_atomic_tasks": [stage for stage in stages if stage["evaluation_hint"] == "unsupported"],
        "unmapped_preview_atomic_tasks": [item for item in preview_atomic_tasks if not item["mapped_stage_indices"]],
        "snapshot_sequence": snapshot_names(task_name),
        "snapshot_transition_summaries": snapshot_transition_summaries,
        "snapshot_transition_report": snapshot_report,
        "trajectory_hints": trajectory_hints,
        "skipped_stages": skipped_stages,
        "stage_plan_source": source,
        "stage_plan_status": "snapshot_aware_plan_pending_validation",
        "llm_error": llm_error,
    }


def main() -> None:
    global SOURCE_ROOT, BUNDLE_ROOT, TASK_PREFIX
    parser = argparse.ArgumentParser(description="Build normalized atomic stage definitions for a snapshot-backed dataset.")
    parser.add_argument("--dataset-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--bundle-root", type=Path, default=BUNDLE_ROOT)
    parser.add_argument("--task-prefix", type=str, default=TASK_PREFIX)
    parser.add_argument("--questions", type=Path, default=SOURCE_ROOT / "questions_clean.json")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=BUNDLE_ROOT / "source_maps")
    parser.add_argument("--index-output", type=Path, default=BUNDLE_ROOT / "source_maps" / "index.json")
    parser.add_argument("--model", type=str, default=os.getenv("TASK_SPLIT_MODEL", "qwen-max"))
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM decomposition and use preview fallback.")
    args = parser.parse_args()
    SOURCE_ROOT = args.dataset_root
    BUNDLE_ROOT = args.bundle_root
    TASK_PREFIX = args.task_prefix
    if localizer is not None:
        localizer.configure(SOURCE_ROOT, BUNDLE_ROOT, TASK_PREFIX)
    if args.questions == DEFAULT_SOURCE_ROOT / "questions_clean.json":
        args.questions = SOURCE_ROOT / "questions_clean.json"
    if args.output_dir == DEFAULT_BUNDLE_ROOT / "source_maps":
        args.output_dir = BUNDLE_ROOT / "source_maps"
    if args.index_output == DEFAULT_BUNDLE_ROOT / "source_maps" / "index.json":
        args.index_output = BUNDLE_ROOT / "source_maps" / "index.json"

    questions = load_json(args.questions)
    index = {"sources": []}

    for idx in range(args.start, args.end + 1):
        task_name = task_name_for_index(idx)
        preview_path = SOURCE_ROOT / f"atomic_task_preview_{task_name}.json"
        if not preview_path.exists():
            continue
        record = build_stage_record(
            task_name=task_name,
            question_item=questions[idx - 1],
            preview=load_json(preview_path),
            model=args.model,
            use_llm=not args.no_llm,
        )
        save_json(args.output_dir / f"{task_name}.json", record)
        index["sources"].append(
            {
                "source_name": task_name,
                "mapping_file": f"evaluation_examples/rule_based_bundle/source_maps/{task_name}.json",
                "stage_plan_source": record["stage_plan_source"],
                "stage_plan_status": record["stage_plan_status"],
                "candidate_count": len(record["candidate_atomic_tasks"]),
                "kept_count": len(record["kept_atomic_tasks"]),
                "llm_assisted_count": len(record["llm_assisted_atomic_tasks"]),
                "unsupported_count": len(record["unsupported_atomic_tasks"]),
                "unmapped_preview_count": len(record["unmapped_preview_atomic_tasks"]),
                "llm_error": record["llm_error"],
            }
        )

    save_json(args.index_output, index)
    print(f"Saved {len(index['sources'])} source maps to {args.output_dir}")


if __name__ == "__main__":
    main()
