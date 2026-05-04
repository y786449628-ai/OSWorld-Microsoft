from __future__ import annotations

import argparse
import json
import os
import re
import time
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


DEFAULT_BUNDLE_ROOT = Path(r"C:\OSWorld\evaluation_examples\rule_based_bundle\Microsoft")
DEFAULT_EXAMPLES_DIR = "examples_windows_osworld"
DEFAULT_SOURCE_MAPS_DIR = "source_maps"

SYSTEM_PROMPT = """You rewrite desktop benchmark task instructions.

The repository already has OSWorld-style example JSON files with fixed setup, input/gold snapshots, and evaluator. Your job is NOT to split or change files. Your job is to rewrite exactly one example instruction so it matches the actual benchmark example and is fair to evaluate.

Return strict JSON only:
{
  "instruction": "Could you ...?",
  "quality_flags": ["..."],
  "rationale": "short reason"
}

Rules:
1. Output one single OSWorld-style task question, not a list.
2. The instruction must match the fixed evaluator target. If evaluator checks an xlsx, focus on the Excel workbook. If evaluator checks docx, focus on the Word document. If evaluator checks pptx, focus on the PowerPoint presentation. If evaluator checks pdf, focus on the PDF export.
3. Do not mention unrelated downstream artifacts that are not evaluated by this example.
4. Do not invent filenames, sheet names, document titles, cell ranges, values, chart types, or formatting details unless provided by the current instruction, source stage, source question, or result/expected filenames.
5. Prefer concise, benchmark-friendly wording: one primary goal, action-oriented, independently understandable.
6. Avoid click-level instructions. Avoid overly broad multi-step project descriptions.
7. If the original instruction is already good, keep it mostly unchanged.
8. If the instruction is too broad because the input/gold snapshot spans multiple semantic operations, summarize the evaluated artifact-level goal instead of pretending it is a tiny step.
9. If the current instruction appears to be a pure save/finalization/no-op stage where input may already match gold, keep the best possible instruction but add quality flag "possible_noop_or_weak_stage".
10. If the current instruction mentions artifacts outside evaluator scope, rewrite to evaluator scope and add quality flag "evaluator_scope_mismatch".
11. If the task remains broad after rewriting because the snapshot interval is broad, add quality flag "coarse_stage".
12. Use natural English beginning with "Could you" and ending with "?".
13. Do not add "save as final result.xlsx" or any save/export clause unless the current example instruction or source stage explicitly asks for that exact save/export operation.
14. If the evaluator checks an intermediate Excel/Word/PPT file, prefer describing the content transformation being evaluated; do not mention unrelated final delivery artifacts.
15. Return exactly one sentence and exactly one question mark.
"""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_example_paths(examples_root: Path, domains: set[str] | None) -> list[Path]:
    paths = []
    for path in examples_root.rglob("*.json"):
        if domains and path.parent.name not in domains:
            continue
        paths.append(path)
    return sorted(paths)


def source_name_from_example(example: dict[str, Any]) -> str | None:
    source = str(example.get("source", ""))
    if " true stage " in source:
        return source.split(" true stage ", 1)[0]
    return None


def stage_index_from_example(example: dict[str, Any]) -> int | None:
    source = str(example.get("source", ""))
    match = re.search(r"true stage\s+(\d+)", source)
    return int(match.group(1)) if match else None


def find_source_stage(source_map: dict[str, Any], stage_index: int | None) -> dict[str, Any] | None:
    if stage_index is None:
        return None
    for key in ("kept_atomic_tasks", "llm_assisted_atomic_tasks", "unsupported_atomic_tasks", "candidate_atomic_tasks"):
        for item in source_map.get(key, []) or []:
            if item.get("stage_index") == stage_index:
                return item
    return None


def summarize_evaluator(example: dict[str, Any]) -> dict[str, Any]:
    evaluator = example.get("evaluator") or {}
    result = evaluator.get("result") if isinstance(evaluator, dict) else {}
    expected = evaluator.get("expected") if isinstance(evaluator, dict) else {}
    return {
        "func": evaluator.get("func") if isinstance(evaluator, dict) else None,
        "result_type": result.get("type") if isinstance(result, dict) else None,
        "result_path": result.get("path") if isinstance(result, dict) else None,
        "result_dest": result.get("dest") if isinstance(result, dict) else None,
        "expected_type": expected.get("type") if isinstance(expected, dict) else None,
        "expected_path": expected.get("path") if isinstance(expected, dict) else None,
        "expected_dest": expected.get("dest") if isinstance(expected, dict) else None,
    }


def summarize_setup(example: dict[str, Any]) -> dict[str, Any]:
    downloads = []
    opens = []
    for step in example.get("config", []) or []:
        step_type = step.get("type")
        params = step.get("parameters") or {}
        if step_type in {"download", "upload_file"}:
            for item in params.get("files", []) or []:
                downloads.append({
                    "path": item.get("path"),
                    "url_tail": str(item.get("url", "")).split("/resolve/main/")[-1] if item.get("url") else None,
                    "local_path": item.get("local_path"),
                })
        elif step_type == "open":
            opens.append(params.get("path"))
    return {"files": downloads, "open": opens}


def heuristic_problematic(example: dict[str, Any]) -> bool:
    instruction = str(example.get("instruction", ""))
    words = re.findall(r"\w+", instruction)
    lowered = instruction.lower()
    if len(words) > 35:
        return True
    if lowered.count("and then") >= 2:
        return True
    if lowered.count("could you") >= 2:
        return True
    if re.search(r"\b(save|finalize|final|export)\b", lowered) and len(words) < 18:
        return True
    evaluator = (example.get("evaluator") or {}).get("func", "")
    if evaluator == "compare_xlsx_files" and any(term in lowered for term in ["word", "powerpoint", "pdf", "presentation"]):
        return True
    if evaluator == "compare_docx_files" and any(term in lowered for term in ["excel", "powerpoint", "ppt", "pdf"]):
        return True
    if evaluator == "compare_pptx_files" and any(term in lowered for term in ["excel", "word", "pdf"]):
        return True
    return False


def normalize_instruction(text: str) -> str:
    cleaned = " ".join(str(text or "").strip().split())
    if not cleaned:
        return "Could you complete the benchmark task?"
    cleaned = re.sub(r"\?+\s+Could you\s+", ", and ", cleaned)
    if not cleaned.lower().startswith("could you"):
        cleaned = "Could you " + cleaned[0].lower() + cleaned[1:]
    cleaned = re.sub(r"\?+", "?", cleaned)
    cleaned = cleaned.rstrip(" .?")
    return cleaned + "?"


def build_prompt(example_path: Path, example: dict[str, Any], source_map: dict[str, Any] | None, stage: dict[str, Any] | None) -> str:
    source_question = source_map.get("source_question") if source_map else None
    payload = {
        "example_json": example_path.as_posix(),
        "domain": example_path.parent.name,
        "id": example.get("id"),
        "source": example.get("source"),
        "current_instruction": example.get("instruction"),
        "source_question": source_question,
        "stage_record": stage,
        "setup_summary": summarize_setup(example),
        "evaluator_summary": summarize_evaluator(example),
    }
    return "Rewrite this benchmark example instruction.\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def make_client(api_mode: str) -> Any:
    if api_mode == "dashscope":
        if dashscope is None:
            raise SystemExit("dashscope package is required for --api-mode dashscope.")
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            raise SystemExit("Set DASHSCOPE_API_KEY first.")
        dashscope.api_key = api_key
        return {"mode": "dashscope"}

    if OpenAI is None:
        raise SystemExit("openai package is required.")
    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set DASHSCOPE_API_KEY or OPENAI_API_KEY first.")
    base_url = os.environ.get("DASHSCOPE_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    return {"mode": "openai", "client": OpenAI(api_key=api_key, base_url=base_url)}


def rewrite_one(client: Any, model: str, prompt: str, retries: int = 3) -> dict[str, Any]:
    last_error = None
    for attempt in range(retries):
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            if client["mode"] == "dashscope":
                response = dashscope.Generation.call(
                    model=model,
                    temperature=0.1,
                    top_p=0.8,
                    result_format="message",
                    messages=messages,
                )
                if response.status_code != 200:
                    raise RuntimeError(
                        f"DashScope status={response.status_code}, "
                        f"code={getattr(response, 'code', None)}, "
                        f"message={getattr(response, 'message', None)}"
                    )
                content = response["output"]["choices"][0]["message"]["content"]
            else:
                response = client["client"].chat.completions.create(
                    model=model,
                    temperature=0.1,
                    top_p=0.8,
                    messages=messages,
                )
                content = response.choices[0].message.content or ""
            parsed = parse_json_object(content)
            instruction = normalize_instruction(parsed.get("instruction", ""))
            flags = parsed.get("quality_flags", [])
            if not isinstance(flags, list):
                flags = [str(flags)]
            return {
                "instruction": instruction,
                "quality_flags": [str(item) for item in flags],
                "rationale": str(parsed.get("rationale", "")).strip(),
            }
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"LLM rewrite failed: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rewrite OSWorld example instructions with an LLM while preserving config/evaluator.")
    parser.add_argument("--bundle-root", type=Path, default=DEFAULT_BUNDLE_ROOT)
    parser.add_argument("--examples-dir", type=str, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--source-maps-dir", type=str, default=DEFAULT_SOURCE_MAPS_DIR)
    parser.add_argument("--model", type=str, default=os.environ.get("INSTRUCTION_REWRITE_MODEL", "qwen-max"))
    parser.add_argument("--api-mode", choices=["dashscope", "openai"], default=os.environ.get("INSTRUCTION_REWRITE_API_MODE", "dashscope"))
    parser.add_argument("--domains", type=str, default="", help="Comma-separated domains, e.g. excel,word,ppt,multi_app")
    parser.add_argument("--ids", type=str, default="", help="Comma-separated example ids to process")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only-problematic", action="store_true", help="Only rewrite long/coarse/suspicious examples.")
    parser.add_argument("--apply", action="store_true", help="Overwrite example JSON instruction fields. Without this, write preview only.")
    parser.add_argument("--backup", action="store_true", default=True, help="Save .bak before modifying an example JSON.")
    parser.add_argument("--preview-output", type=Path, default=None)
    args = parser.parse_args()

    examples_root = args.bundle_root / args.examples_dir
    source_maps_root = args.bundle_root / args.source_maps_dir
    domains = {item.strip() for item in args.domains.split(",") if item.strip()} or None
    ids = {item.strip() for item in args.ids.split(",") if item.strip()} or None
    preview_output = args.preview_output or (args.bundle_root / "instruction_rewrite_preview.jsonl")

    paths = iter_example_paths(examples_root, domains)
    if ids:
        paths = [path for path in paths if path.stem in ids]

    selected: list[Path] = []
    for path in paths:
        example = load_json(path)
        if args.only_problematic and not heuristic_problematic(example):
            continue
        selected.append(path)
        if args.limit and len(selected) >= args.limit:
            break

    client = make_client(args.api_mode)
    preview_output.parent.mkdir(parents=True, exist_ok=True)
    processed = 0

    with preview_output.open("w", encoding="utf-8") as preview_file:
        for path in selected:
            example = load_json(path)
            source_name = source_name_from_example(example)
            source_map = None
            if source_name:
                source_map_path = source_maps_root / f"{source_name}.json"
                if source_map_path.exists():
                    source_map = load_json(source_map_path)
            stage = find_source_stage(source_map, stage_index_from_example(example)) if source_map else None
            prompt = build_prompt(path, example, source_map, stage)
            rewrite = rewrite_one(client, args.model, prompt)

            record = {
                "path": path.as_posix(),
                "id": example.get("id"),
                "source": example.get("source"),
                "domain": path.parent.name,
                "old_instruction": example.get("instruction"),
                "new_instruction": rewrite["instruction"],
                "quality_flags": rewrite["quality_flags"],
                "rationale": rewrite["rationale"],
                "changed": example.get("instruction") != rewrite["instruction"],
            }
            preview_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            preview_file.flush()

            if args.apply:
                if args.backup:
                    backup_path = path.with_suffix(path.suffix + ".bak")
                    if not backup_path.exists():
                        backup_path.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8")
                example.setdefault("instruction_rewrite", {})
                example["instruction_rewrite"] = {
                    "old_instruction": example.get("instruction"),
                    "model": args.model,
                    "quality_flags": rewrite["quality_flags"],
                    "rationale": rewrite["rationale"],
                }
                example["instruction"] = rewrite["instruction"]
                save_json(path, example)

            processed += 1
            print(f"[{processed}/{len(selected)}] {path.name}: {rewrite['instruction']}")

    print(f"Processed {processed} examples.")
    print(f"Preview written to {preview_output}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to update example JSON files.")


if __name__ == "__main__":
    main()
