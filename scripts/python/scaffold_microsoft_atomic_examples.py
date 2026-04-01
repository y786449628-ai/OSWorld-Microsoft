import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import dashscope


SYSTEM_PROMPT = """You are helping convert a complex desktop task into OSWorld-style atomic tasks.

Your job:
1. Read one original task question.
2. Split it into a small list of atomic OSWorld-style task questions.
3. Each atomic task must have one primary goal, be independently understandable, and sound like an OSWorld instruction.

Requirements:
- Output only JSON.
- Return an object with one key: "atomic_tasks".
- "atomic_tasks" must be a list of strings.
- Each string must be a natural-language OSWorld-style question.
- Keep each atomic task concise and action-oriented.
- Do not include explanations.
- Do not include numbering.
- Do not include subtasks.
- Prefer 4 to 8 atomic tasks.
- Separate Excel-only, Word-only, PowerPoint-only, Outlook-only, and cross-app actions when reasonable.
- Exporting or saving into a final format like PDF/CSV should usually be its own atomic task.
- Do not invent names, worksheet names, file names, paths, numbers, or requirements that are not explicitly present in the original task.
- Prefer stage-level atomic tasks, not click-level, cell-level, or overly fine-grained procedural subtasks.
- Merge simple setup actions into a larger atomic task when they belong to the same evaluation target.
- Keep explicitly required application stages separate when they form different outcomes.
"""


def build_user_prompt(question: str) -> str:
    return f"""Original task question:
{question}

Please convert this into OSWorld-style atomic task questions.
Return JSON only in the form:
{{
  "atomic_tasks": [
    "Could you ...?",
    "Could you ...?"
  ]
}}
"""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_atomic_preview(
    item: dict[str, Any],
    preview_path: Path,
    model: str,
) -> dict[str, Any]:
    if preview_path.exists():
        return load_json(preview_path)

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit(
            f"Missing atomic preview for {item['file_name']} and DASHSCOPE_API_KEY is not set."
        )

    dashscope.api_key = api_key
    response = dashscope.Generation.call(
        model=model,
        temperature=0.2,
        top_p=0.8,
        result_format="message",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(item["question"])},
        ],
    )
    if response.status_code != 200:
        raise SystemExit(
            f"DashScope request failed for {item['file_name']}: status={response.status_code}, "
            f"code={getattr(response, 'code', None)}, message={getattr(response, 'message', None)}"
        )

    content = response["output"]["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    preview = {
        "source_file": item["file_name"],
        "source_id": item["id"],
        "source_question": item["question"],
        "atomic_tasks": parsed.get("atomic_tasks", []),
        "model": model,
    }
    save_json(preview_path, preview)
    return preview


def list_snapshot_dirs(ms_dir: Path) -> list[Path]:
    root = ms_dir / "logs" / "MonitoringSnapshots"
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name)


def list_desktop_files(snapshot_dir: Path) -> list[Path]:
    desktop = snapshot_dir / "Desktop"
    if not desktop.exists():
        return []
    return sorted([p for p in desktop.iterdir() if p.is_file()], key=lambda p: p.name.lower())


def snapshots_with_files(snapshot_dirs: list[Path]) -> list[list[Path]]:
    return [list_desktop_files(p) for p in snapshot_dirs]


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
    }


def detect_apps(text: str) -> list[str]:
    lowered = text.lower()
    apps: list[str] = []
    if "excel" in lowered or ".xlsx" in lowered or "worksheet" in lowered or "workbook" in lowered:
        apps.append("excel")
    if "word" in lowered or ".docx" in lowered or "document" in lowered:
        apps.append("word")
    if "powerpoint" in lowered or ".ppt" in lowered or "presentation" in lowered:
        apps.append("ppt")
    if "pdf" in lowered:
        apps.append("pdf")
    if any(token in lowered for token in ["folder", "desktop", "file", "move", "archive"]):
        apps.append("os")
    deduped: list[str] = []
    for app in apps:
        if app not in deduped:
            deduped.append(app)
    return deduped or ["os"]


def choose_domain(apps: list[str]) -> str:
    core = [app for app in apps if app in {"excel", "word", "ppt"}]
    if len(core) > 1:
        return "multi_app"
    if core:
        return core[0]
    return "multi_app"


def make_uuid_like(seed: str) -> str:
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:32]
    return f"{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def choose_primary_open_file(files: list[Path], domain: str) -> Path | None:
    wanted_ext = {
        "excel": {".xlsx", ".xls"},
        "word": {".docx", ".doc"},
        "ppt": {".pptx", ".ppt"},
        "multi_app": {".xlsx", ".docx", ".pptx", ".pdf"},
        "os": set(),
    }.get(domain, set())

    for path in files:
        if path.suffix.lower() in wanted_ext:
            return path
    for path in files:
        if relevant_file(path):
            return path
    return None


def pick_file_by_ext(files: list[Path], exts: set[str]) -> Path | None:
    for path in files:
        if path.suffix.lower() in exts:
            return path
    return None


def files_of_type(files: list[Path], exts: set[str]) -> list[Path]:
    return [p for p in files if p.suffix.lower() in exts]


def snapshot_contains_ext(files: list[Path], exts: set[str]) -> bool:
    return any(p.suffix.lower() in exts for p in files)


def first_snapshot_index_with_ext(snapshot_files: list[list[Path]], exts: set[str]) -> int | None:
    for idx, files in enumerate(snapshot_files):
        if snapshot_contains_ext(files, exts):
            return idx
    return None


def last_snapshot_index_with_ext(snapshot_files: list[list[Path]], exts: set[str]) -> int | None:
    for idx in range(len(snapshot_files) - 1, -1, -1):
        if snapshot_contains_ext(snapshot_files[idx], exts):
            return idx
    return None


def last_snapshot_index_before_ext(snapshot_files: list[list[Path]], exts: set[str]) -> int | None:
    first_idx = first_snapshot_index_with_ext(snapshot_files, exts)
    if first_idx is None:
        return None
    return max(first_idx - 1, 0)


def infer_stage_files(
    task_text: str,
    domain: str,
    snapshot_dirs: list[Path],
) -> tuple[list[Path], Path | None, Path | None, str | None]:
    snapshot_files = snapshots_with_files(snapshot_dirs)
    lowered = task_text.lower()

    doc_exts = {".docx", ".doc"}
    ppt_exts = {".pptx", ".ppt"}
    xlsx_exts = {".xlsx", ".xls"}
    pdf_exts = {".pdf"}

    first_files = snapshot_files[0] if snapshot_files else []
    last_files = snapshot_files[-1] if snapshot_files else []

    if domain == "word" or ("word" in lowered and "powerpoint" not in lowered):
        first_doc_idx = first_snapshot_index_with_ext(snapshot_files, doc_exts)
        last_doc_idx = last_snapshot_index_with_ext(snapshot_files, doc_exts)
        first_pdf_idx = first_snapshot_index_with_ext(snapshot_files, pdf_exts)

        if "save" in lowered and "pdf" in lowered:
            input_idx = (first_pdf_idx - 1) if first_pdf_idx and first_pdf_idx > 0 else last_doc_idx
            gold_idx = first_pdf_idx if first_pdf_idx is not None else len(snapshot_files) - 1
            input_files = snapshot_files[input_idx] if input_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[gold_idx], pdf_exts) if snapshot_files else None
            open_file = pick_file_by_ext(input_files, doc_exts)
            return input_files, open_file, gold_file, "compare_pdfs"

        if "create" in lowered and "document" in lowered:
            input_idx = last_snapshot_index_before_ext(snapshot_files, doc_exts)
            gold_idx = first_doc_idx
            input_files = snapshot_files[input_idx] if input_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[gold_idx], doc_exts) if gold_idx is not None else None
            return input_files, None, gold_file, "compare_docx_files"

        if any(token in lowered for token in ["paste", "insert", "copy"]):
            input_idx = first_doc_idx
            gold_idx = last_doc_idx
            input_files = snapshot_files[input_idx] if input_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[gold_idx], doc_exts) if gold_idx is not None else None
            open_file = pick_file_by_ext(input_files, doc_exts)
            return input_files, open_file, gold_file, "compare_docx_files"

    if domain == "ppt" or "powerpoint" in lowered or "presentation" in lowered:
        first_ppt_idx = first_snapshot_index_with_ext(snapshot_files, ppt_exts)
        last_ppt_idx = last_snapshot_index_with_ext(snapshot_files, ppt_exts)

        if "create" in lowered and any(token in lowered for token in ["slide", "presentation"]):
            input_idx = last_snapshot_index_before_ext(snapshot_files, ppt_exts)
            gold_idx = first_ppt_idx
            input_files = snapshot_files[input_idx] if input_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[gold_idx], ppt_exts) if gold_idx is not None else None
            return input_files, None, gold_file, "compare_pptx_files"

        if any(token in lowered for token in ["chart", "link", "adjust", "visualize"]):
            input_idx = first_ppt_idx
            gold_idx = last_ppt_idx
            input_files = snapshot_files[input_idx] if input_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[gold_idx], ppt_exts) if gold_idx is not None else None
            open_file = pick_file_by_ext(input_files, ppt_exts)
            return input_files, open_file, gold_file, "compare_pptx_files"

    if domain == "excel":
        pure_xlsx_snapshots: list[tuple[int, list[Path]]] = []
        for idx, files in enumerate(snapshot_files):
            if snapshot_contains_ext(files, xlsx_exts) and not snapshot_contains_ext(files, doc_exts | ppt_exts | pdf_exts):
                pure_xlsx_snapshots.append((idx, files))

        if pure_xlsx_snapshots:
            if "conditional formatting" in lowered or "data bars" in lowered:
                gold_idx = pure_xlsx_snapshots[min(3, len(pure_xlsx_snapshots) - 1)][0]
            elif "chart" in lowered:
                gold_idx = pure_xlsx_snapshots[-1][0]
            elif "calculate" in lowered:
                gold_idx = pure_xlsx_snapshots[min(2, len(pure_xlsx_snapshots) - 1)][0]
            else:
                gold_idx = pure_xlsx_snapshots[min(1, len(pure_xlsx_snapshots) - 1)][0]

            input_idx = max(gold_idx - 1, pure_xlsx_snapshots[0][0])
            input_files = snapshot_files[input_idx]
            gold_file = pick_file_by_ext(snapshot_files[gold_idx], xlsx_exts)
            open_file = pick_file_by_ext(input_files, xlsx_exts)
            return input_files, open_file, gold_file, "compare_xlsx_files"

    if domain == "multi_app":
        if "pdf" in lowered:
            first_pdf_idx = first_snapshot_index_with_ext(snapshot_files, pdf_exts)
            input_idx = (first_pdf_idx - 1) if first_pdf_idx and first_pdf_idx > 0 else len(snapshot_files) - 1
            input_files = snapshot_files[input_idx] if snapshot_files else []
            gold_file = pick_file_by_ext(last_files, pdf_exts)
            open_file = (
                pick_file_by_ext(input_files, doc_exts)
                or pick_file_by_ext(input_files, ppt_exts)
                or pick_file_by_ext(input_files, xlsx_exts)
            )
            return input_files, open_file, gold_file, "compare_pdfs"

        if "word" in lowered or "document" in lowered:
            first_doc_idx = first_snapshot_index_with_ext(snapshot_files, doc_exts)
            last_doc_idx = last_snapshot_index_with_ext(snapshot_files, doc_exts)
            input_files = snapshot_files[first_doc_idx] if first_doc_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[last_doc_idx], doc_exts) if last_doc_idx is not None else None
            open_file = pick_file_by_ext(input_files, doc_exts)
            return input_files, open_file, gold_file, "compare_docx_files"

        if "powerpoint" in lowered or "presentation" in lowered:
            first_ppt_idx = first_snapshot_index_with_ext(snapshot_files, ppt_exts)
            last_ppt_idx = last_snapshot_index_with_ext(snapshot_files, ppt_exts)
            input_files = snapshot_files[first_ppt_idx] if first_ppt_idx is not None else first_files
            gold_file = pick_file_by_ext(snapshot_files[last_ppt_idx], ppt_exts) if last_ppt_idx is not None else None
            open_file = pick_file_by_ext(input_files, ppt_exts)
            return input_files, open_file, gold_file, "compare_pptx_files"

    open_file = choose_primary_open_file(first_files, domain)
    gold_file, compare_func = choose_gold_file(task_text, last_files, domain)
    return first_files, open_file, gold_file, compare_func


def choose_gold_file(text: str, files: list[Path], domain: str) -> tuple[Path | None, str | None]:
    lowered = text.lower()
    if "pdf" in lowered:
        for path in files:
            if path.suffix.lower() == ".pdf":
                return path, "compare_pdfs"
    if domain == "word":
        for path in files:
            if path.suffix.lower() in {".docx", ".doc"}:
                return path, "compare_docx_files"
    if domain == "ppt":
        for path in files:
            if path.suffix.lower() in {".pptx", ".ppt"}:
                return path, "compare_pptx_files"
    if domain == "excel":
        for path in files:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                return path, "compare_xlsx_files"
    for path in files:
        if path.suffix.lower() == ".pdf":
            return path, "compare_pdfs"
    for path in files:
        if path.suffix.lower() in {".docx", ".doc"}:
            return path, "compare_docx_files"
    for path in files:
        if path.suffix.lower() in {".pptx", ".ppt"}:
            return path, "compare_pptx_files"
    for path in files:
        if path.suffix.lower() in {".xlsx", ".xls"}:
            return path, "compare_xlsx_files"
    return None, None


def vm_user_path(filename: str, for_gold: bool = False) -> str:
    base = r"C:\Users\78644\Documents" if for_gold else r"C:\Users\78644\Desktop"
    return str(Path(base) / filename)


def build_config(first_files: list[Path], open_file: Path | None, gold_file: Path | None) -> list[dict[str, Any]]:
    uploads: list[dict[str, str]] = []
    seen_names: set[str] = set()

    for path in first_files:
        if not relevant_file(path):
            continue
        if path.name in seen_names:
            continue
        seen_names.add(path.name)
        uploads.append({
            "local_path": str(path),
            "path": vm_user_path(path.name, for_gold=False),
        })

    if gold_file is not None:
        gold_name = f"{gold_file.stem}_gold{gold_file.suffix}"
        uploads.append({
            "local_path": str(gold_file),
            "path": vm_user_path(gold_name, for_gold=True),
        })

    config: list[dict[str, Any]] = []
    if uploads:
        config.append({
            "type": "upload_file",
            "parameters": {
                "files": uploads,
            },
        })

    if open_file is not None:
        config.append({
            "type": "open",
            "parameters": {
                "path": vm_user_path(open_file.name, for_gold=False),
            },
        })
    return config


def build_evaluator(task_text: str, domain: str, gold_file: Path | None, compare_func: str | None) -> dict[str, Any]:
    if gold_file is None or compare_func is None:
        return {
            "func": "check_file_exists",
            "result": {
                "type": "vm_file",
                "path": r"C:\Users\78644\Desktop\Record.lnk",
                "dest": "Record.lnk",
            },
        }

    gold_name = f"{gold_file.stem}_gold{gold_file.suffix}"
    result_name = gold_file.name

    result_vm_path = vm_user_path(result_name, for_gold=False)
    expected_vm_path = vm_user_path(gold_name, for_gold=True)

    if "pdf" in task_text.lower() and gold_file.suffix.lower() == ".pdf":
        result_vm_path = vm_user_path(result_name, for_gold=False)

    options: dict[str, Any] = {}
    if compare_func == "compare_xlsx_files":
        options = {
            "ignore_case": True,
            "check_sheet_order": True,
            "check_formats": False,
        }

    evaluator: dict[str, Any] = {
        "func": compare_func,
        "result": {
            "type": "vm_file",
            "path": result_vm_path,
            "dest": result_name,
        },
        "expected": {
            "type": "vm_file",
            "path": expected_vm_path,
            "dest": gold_name,
        },
    }
    if options:
        evaluator["options"] = options
    return evaluator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold OSWorld-style Windows examples for Microsoft tasks."
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path(r"C:\OSWorld\Microsoft\questions_clean.json"),
    )
    parser.add_argument(
        "--microsoft-dir",
        type=Path,
        default=Path(r"C:\OSWorld\Microsoft"),
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="1-based Microsoft task index to start from",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=10,
        help="1-based Microsoft task index to end at",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("TASK_SPLIT_MODEL", "qwen-max"),
    )
    parser.add_argument(
        "--examples-root",
        type=Path,
        default=Path(r"C:\OSWorld\evaluation_examples\examples_windows"),
    )
    parser.add_argument(
        "--meta-output",
        type=Path,
        default=Path(r"C:\OSWorld\evaluation_examples\test_microsoft_01_10_atomic_windows.json"),
    )
    args = parser.parse_args()

    questions = load_json(args.questions)
    grouped: dict[str, list[str]] = {
        "excel": [],
        "word": [],
        "ppt": [],
        "multi_app": [],
    }

    for idx in range(args.start, args.end + 1):
        item = questions[idx - 1]
        ms_name = f"Microsoft_{idx:02d}"
        ms_dir = args.microsoft_dir / ms_name
        preview_path = args.microsoft_dir / f"atomic_task_preview_{ms_name}.json"
        preview = ensure_atomic_preview(item, preview_path, args.model)

        snapshot_dirs = list_snapshot_dirs(ms_dir)

        for task_index, task_text in enumerate(preview.get("atomic_tasks", []), start=1):
            apps = detect_apps(task_text)
            domain = choose_domain(apps)
            input_files, open_file, gold_file, compare_func = infer_stage_files(
                task_text, domain, snapshot_dirs
            )

            example_id = make_uuid_like(f"{preview['source_id']}::{task_index}")
            config = build_config(input_files, open_file, gold_file)
            evaluator = build_evaluator(task_text, domain, gold_file, compare_func)

            example = {
                "id": example_id,
                "snapshot": domain if domain in {"excel", "word", "ppt"} else "excel",
                "instruction": task_text,
                "source": f"{ms_name} atomic task {task_index}",
                "config": config,
                "trajectory": f"trajectories/{example_id}",
                "related_apps": [app for app in apps if app != "pdf"],
                "evaluator": evaluator,
            }

            output_path = args.examples_root / domain / f"{example_id}.json"
            save_json(output_path, example)
            grouped.setdefault(domain, []).append(example_id)

    grouped = {k: v for k, v in grouped.items() if v}
    save_json(args.meta_output, grouped)
    print(f"Saved meta: {args.meta_output}")


if __name__ == "__main__":
    main()
