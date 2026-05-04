import argparse
import json
import re
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


WORKSPACE = Path(r"C:\OSWorld")
SOURCE_ROOT = WORKSPACE / "Microsoft"
BUNDLE_ROOT = WORKSPACE / "evaluation_examples" / "rule_based_bundle"
TASK_PREFIX = "Microsoft"

SUPPORTED_EVALUATORS = {
    "xlsx": "compare_xlsx_files",
    "xls": "compare_xlsx_files",
    "docx": "compare_docx_files",
    "doc": "compare_docx_files",
    "pptx": "compare_pptx_files",
    "ppt": "compare_pptx_files",
    "pdf": "compare_pdfs",
    "png": "compare_images",
    "jpg": "compare_images",
    "jpeg": "compare_images",
    "mp4": "compare_videos",
    "zip": "compare_zip_files",
    "svg": "compare_text_file",
}

RUNNABLE_EVALUATOR_FUNCS = set(SUPPORTED_EVALUATORS.values()) | {"compare_directory_tree", "compare_artifact_with_llm_judge"}
OPAQUE_EXISTENCE_SUFFIXES = {"dwg", "fig", "prproj"}
LLM_JUDGE_SUFFIXES = {"png", "jpg", "jpeg", "pdf", "mp4"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def task_name_for_index(index: int) -> str:
    return f"{TASK_PREFIX}_{index:02d}"


def configure(dataset_root: Path | None = None, bundle_root: Path | None = None, task_prefix: str | None = None) -> None:
    global SOURCE_ROOT, BUNDLE_ROOT, TASK_PREFIX
    if dataset_root is not None:
        SOURCE_ROOT = dataset_root
    if bundle_root is not None:
        BUNDLE_ROOT = bundle_root
    if task_prefix:
        TASK_PREFIX = task_prefix


def snapshot_root(task_name: str) -> Path:
    return SOURCE_ROOT / task_name / "logs" / "MonitoringSnapshots"


def desktop_root(task_name: str, snapshot: str) -> Path:
    return snapshot_root(task_name) / snapshot / "Desktop"


def snapshot_names(task_name: str) -> list[str]:
    root = snapshot_root(task_name)
    if not root.exists():
        return []
    return sorted(path.name for path in root.iterdir() if path.is_dir())


def normalize_path(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def extract_quoted_filename(text: str, suffixes: tuple[str, ...]) -> str | None:
    for match in re.finditer(r"['\"]([^'\"]+)['\"]", text):
        value = match.group(1).strip()
        if value.lower().endswith(suffixes):
            return value
    match = re.search(r"([A-Za-z0-9][^'\"\n\r]*?\.(?:xlsx|xls|docx|doc|pptx|ppt|pdf|png|jpg|jpeg|mp4|zip|svg))", text, re.I)
    if match:
        return sanitize_unquoted_filename(match.group(1).strip())
    return None


def sanitize_unquoted_filename(value: str) -> str:
    lowered = value.lower()
    if lowered.startswith(("could you ", "please ", "open ", "import ", "export ", "save ")):
        return value.split()[-1].strip(".,;:!?")
    return value.strip(".,;:!?")


def extract_quoted_label(text: str) -> str | None:
    quoted = [match.group(1).strip() for match in re.finditer(r"['\"]([^'\"]+)['\"]", text)]
    for value in reversed(quoted):
        if "." not in value and value:
            return value
    return quoted[-1] if quoted else None


def quoted_values(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"['\"]([^'\"]+)['\"]", text)]


def office_summary(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix not in {".xlsx", ".xlsm"}:
        return {}
    try:
        return xlsx_summary(path)
    except Exception as exc:
        return {"parse_error": str(exc)}


def xlsx_summary(path: Path) -> dict[str, Any]:
    shared_strings = read_xlsx_shared_strings(path)
    sheet_names = read_xlsx_sheet_names(path)
    sheet_targets = read_xlsx_sheet_targets(path)
    worksheets: list[dict[str, Any]] = []
    total_nonempty = 0
    total_charts = 0
    with zipfile.ZipFile(path) as archive:
        for idx, target in enumerate(sheet_targets):
            sheet_path = f"xl/{target}".replace("xl//", "xl/")
            if sheet_path not in archive.namelist():
                continue
            xml = archive.read(sheet_path)
            root = ET.fromstring(xml)
            ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            nonempty = 0
            headers: list[str] = []
            for cell in root.findall(".//main:sheetData/main:row/main:c", ns):
                value = cell.find("main:v", ns)
                inline = cell.find("main:is/main:t", ns)
                if value is None and inline is None:
                    continue
                nonempty += 1
                ref = cell.attrib.get("r", "")
                if ref.startswith(tuple(chr(code) for code in range(ord("A"), ord("Z") + 1))) and ref.endswith("1"):
                    headers.append(read_cell_text(cell, shared_strings, ns))
            chart_count = len(root.findall(".//main:drawing", ns))
            total_nonempty += nonempty
            total_charts += chart_count
            worksheets.append(
                {
                    "name": sheet_names[idx] if idx < len(sheet_names) else f"Sheet{idx + 1}",
                    "nonempty_cells": nonempty,
                    "drawing_count": chart_count,
                    "headers": [header for header in headers if header],
                }
            )
    return {
        "sheet_names": sheet_names,
        "worksheet_count": len(sheet_names),
        "nonempty_cells": total_nonempty,
        "chart_count": total_charts,
        "worksheets": worksheets,
    }


def read_cell_text(cell: ET.Element, shared_strings: list[str], ns: dict[str, str]) -> str:
    inline = cell.find("main:is/main:t", ns)
    if inline is not None and inline.text:
        return inline.text
    value = cell.find("main:v", ns)
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(value.text)]
        except Exception:
            return value.text
    return value.text


def read_xlsx_shared_strings(path: Path) -> list[str]:
    strings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return strings
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    for si in root.findall("main:si", ns):
        pieces = [node.text or "" for node in si.findall(".//main:t", ns)]
        strings.append("".join(pieces))
    return strings


def read_xlsx_sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        if "xl/workbook.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/workbook.xml"))
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    return [sheet.attrib.get("name", "") for sheet in root.findall(".//main:sheets/main:sheet", ns)]


def read_xlsx_sheet_targets(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        if "xl/workbook.xml" not in archive.namelist() or "xl/_rels/workbook.xml.rels" not in archive.namelist():
            return []
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib.get("Id"): rel.attrib.get("Target", "")
        for rel in rels
        if rel.attrib.get("Type", "").endswith("/worksheet")
    }
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    targets = []
    for sheet in workbook.findall(".//main:sheets/main:sheet", ns):
        rel_id = sheet.attrib.get(f"{{{ns['rel']}}}id")
        target = rel_map.get(rel_id)
        if target:
            targets.append(target.lstrip("/"))
    return targets


def build_manifest(task_name: str, snapshot: str) -> dict[str, Any]:
    root = desktop_root(task_name, snapshot)
    files: dict[str, dict[str, Any]] = {}
    dirs: set[str] = set()
    if not root.exists():
        return {"snapshot": snapshot, "files": files, "dirs": []}
    for path in root.rglob("*"):
        rel = normalize_path(path, root)
        if path.is_dir():
            dirs.add(rel)
            continue
        entry = {
            "rel_path": rel,
            "name": path.name,
            "suffix": path.suffix.lower().lstrip("."),
            "size": path.stat().st_size,
        }
        summary = office_summary(path)
        if summary:
            entry["summary"] = summary
        files[rel] = entry
    return {"snapshot": snapshot, "files": files, "dirs": sorted(dirs)}


def find_files(manifest: dict[str, Any], suffixes: set[str], preferred_name: str | None = None) -> list[str]:
    candidates = []
    for rel, entry in manifest["files"].items():
        if entry["suffix"].lower() not in suffixes:
            continue
        if preferred_name and entry["name"].lower() != preferred_name.lower():
            continue
        candidates.append(rel)
    if not candidates and preferred_name:
        lowered = preferred_name.lower()
        for rel, entry in manifest["files"].items():
            if entry["suffix"].lower() in suffixes and lowered in entry["name"].lower():
                candidates.append(rel)
    return sorted(candidates)


def get_summary(manifest: dict[str, Any], rel_path: str | None) -> dict[str, Any]:
    if not rel_path:
        return {}
    return manifest["files"].get(rel_path, {}).get("summary", {})


def changed_file_count(before: dict[str, Any], after: dict[str, Any]) -> int:
    before_files = before["files"]
    after_files = after["files"]
    count = len(set(before_files) ^ set(after_files))
    for rel in set(before_files) & set(after_files):
        if before_files[rel].get("size") != after_files[rel].get("size"):
            count += 1
    return count


def choose_file_for_stage(stage: dict[str, Any]) -> tuple[set[str], str | None]:
    artifact = str(stage.get("expected_artifact") or "").lower().lstrip(".")
    artifact_parts = {part.strip().lstrip(".") for part in re.split(r"[|,/ ]+", artifact) if part.strip()}
    suffixes = {part for part in artifact_parts if part in SUPPORTED_EVALUATORS}
    if not suffixes and "excel" in stage.get("apps", []):
        suffixes = {"xlsx", "xls"}
    if not suffixes and "word" in stage.get("apps", []):
        suffixes = {"docx", "doc"}
    if not suffixes and "ppt" in stage.get("apps", []):
        suffixes = {"pptx", "ppt"}
    if not suffixes and artifact == "pdf":
        suffixes = {"pdf"}
    instruction_lower = stage.get("instruction", "").lower()
    image_tokens = {".png", ".jpg", ".jpeg", " png", " jpg", " jpeg", "image", "picture", "export", "save"}
    if not suffixes:
        token_suffixes: set[str] = set()
        for suffix in ("mp4", "zip", "svg", "pdf", "png", "jpg", "jpeg"):
            if f".{suffix}" in instruction_lower or re.search(rf"\b{suffix}\b", instruction_lower):
                token_suffixes.add(suffix)
        suffixes = {suffix for suffix in token_suffixes if suffix in SUPPORTED_EVALUATORS}
    if not suffixes and (
        artifact in {"psd", "image", "picture", "exported_image", "raster_image"}
        or any(token in instruction_lower for token in image_tokens)
    ):
        suffixes = {"png", "jpg", "jpeg"}
    if stage.get("task_kind") == "export_pdf" and "word" in stage.get("apps", []) and (
        "doc" in instruction_lower or "word document" in instruction_lower
    ):
        suffixes.update({"docx", "doc"})
    preferred = extract_quoted_filename(stage.get("instruction", ""), tuple(f".{s}" for s in suffixes)) if suffixes else None
    return suffixes, preferred


def choose_opaque_file_for_stage(stage: dict[str, Any]) -> tuple[set[str], str | None]:
    artifact = str(stage.get("expected_artifact") or "").lower().lstrip(".")
    artifact_parts = {part.strip().lstrip(".") for part in re.split(r"[|,/ ]+", artifact) if part.strip()}
    suffixes = {part for part in artifact_parts if part in OPAQUE_EXISTENCE_SUFFIXES}
    instruction = stage.get("instruction", "")
    instruction_lower = instruction.lower()
    if not suffixes:
        for suffix in OPAQUE_EXISTENCE_SUFFIXES:
            if f".{suffix}" in instruction_lower or re.search(rf"\b{suffix}\b", instruction_lower):
                suffixes.add(suffix)
    preferred = extract_quoted_filename(instruction, tuple(f".{s}" for s in suffixes)) if suffixes else None
    return suffixes, preferred


def locate_office_stage(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    kind = stage.get("task_kind")
    suffixes, preferred = choose_file_for_stage(stage)
    if not suffixes:
        return None, "No supported Office/PDF artifact suffix was inferred."

    instruction_lower = stage.get("instruction", "").lower()
    if kind == "excel_create_or_open_workbook" and "import" in instruction_lower:
        return locate_xlsx_content_growth(stage, manifests, start_index, suffixes, preferred, end_index)
    if kind in {"excel_create_or_open_workbook", "excel_create_or_save_workbook"}:
        return locate_file_appearance(stage, manifests, start_index, suffixes, preferred, end_index)
    if kind == "excel_rename_sheet":
        return locate_sheet_rename(stage, manifests, start_index, suffixes, preferred, end_index)
    if kind in {"excel_enter_data", "excel_calculate_formula", "excel_format_cells"}:
        return locate_xlsx_content_growth(stage, manifests, start_index, suffixes, preferred, end_index)
    if kind == "excel_create_chart":
        return locate_xlsx_chart_growth(stage, manifests, start_index, suffixes, preferred, end_index)
    if kind == "export_pdf":
        return locate_file_appearance(stage, manifests, start_index, suffixes, preferred, end_index)
    return locate_file_content_change(stage, manifests, start_index, suffixes, preferred, end_index)


def locate_file_artifact_stage(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    suffixes, preferred = choose_file_for_stage(stage)
    simple_file_suffixes = {"png", "jpg", "jpeg", "pdf", "mp4", "zip", "svg"}
    if not suffixes or not suffixes <= simple_file_suffixes:
        return None, "No supported simple file artifact suffix was inferred."

    text = f"{stage.get('stage_name', '')} {stage.get('instruction', '')} {stage.get('task_kind', '')}".lower()
    export_like = any(token in text for token in ("export", "save", "final", "png", "jpg", "jpeg", "image", "picture"))
    if export_like:
        localized, error = locate_file_appearance(stage, manifests, start_index, suffixes, preferred, end_index)
        if localized:
            return localized, ""
        if preferred:
            relaxed, relaxed_error = locate_file_appearance(stage, manifests, start_index, suffixes, None, end_index)
            if relaxed and relaxed.get("target_relative_path", "").split("/")[-1].lower() != preferred.lower():
                target = relaxed["target_relative_path"]
                before = next(item for item in manifests if item["snapshot"] == relaxed["input_snapshot"])
                after = next(item for item in manifests if item["snapshot"] == relaxed["gold_snapshot"])
                if not is_requested_output_filename(stage, preferred):
                    return relaxed, ""
                return make_llm_judge_localization(
                    stage,
                    before,
                    after,
                    target,
                    0.6,
                    f"Target artifact appeared with a different filename than requested; using LLM judge on visual previews. {relaxed_error or error}",
                    requested_result_path=preferred,
                ), ""
        changed, change_error = locate_file_content_change(stage, manifests, start_index, suffixes, preferred, end_index)
        return changed, change_error if changed is None else ""

    localized, error = locate_file_content_change(stage, manifests, start_index, suffixes, preferred, end_index)
    if localized:
        return localized, ""
    return locate_file_appearance(stage, manifests, start_index, suffixes, preferred, end_index)


def is_requested_output_filename(stage: dict[str, Any], filename: str) -> bool:
    text = stage.get("instruction", "").lower()
    filename_lower = filename.lower()
    filename_pos = text.find(filename_lower)
    if filename_pos < 0:
        return False
    before = text[max(0, filename_pos - 40) : filename_pos]
    context = text[max(0, filename_pos - 80) : filename_pos + len(filename_lower) + 20]
    if re.search(r"\b(open|import)\s+(?:the\s+image\s+)?['\"]?$", before):
        return False
    return bool(re.search(r"\b(save|export|output)(?:[^.?!]{0,60})\b(as|named)?[^.?!]{0,40}$", before)) or (
        " as " in before[-12:] or " named " in before[-20:] or "final" in context
    )


def make_file_presence_localization(
    stage: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    rel_path: str,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    rel_path = _norm_path(rel_path)
    if "/" in rel_path:
        root_relative_path, file_name = rel_path.rsplit("/", 1)
    else:
        root_relative_path, file_name = "", rel_path
    return make_directory_localization(
        stage,
        before,
        after,
        root_relative_path,
        [],
        [file_name],
        confidence,
        reason,
    )


def make_llm_judge_localization(
    stage: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    rel_path: str,
    confidence: float,
    reason: str,
    requested_result_path: str | None = None,
) -> dict[str, Any]:
    localized = deepcopy(stage)
    localized["input_snapshot"] = before["snapshot"]
    localized["gold_snapshot"] = after["snapshot"]
    localized["target_relative_path"] = rel_path
    if requested_result_path:
        localized["result_relative_path"] = requested_result_path
    localized["evaluator_candidate"] = "compare_artifact_with_llm_judge"
    localized["evaluation_hint"] = "llm_judge"
    localized["localization"] = {
        "status": "localized_llm_judge",
        "confidence": confidence,
        "reason": reason,
        "changed_file_count": changed_file_count(before, after),
    }
    return localized


def locate_opaque_file_presence_stage(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    suffixes, preferred = choose_opaque_file_for_stage(stage)
    if not suffixes:
        return None, "No opaque file suffix was inferred for presence-based evaluation."
    for idx in transition_indices(manifests, start_index, end_index):
        before = manifests[idx - 1]
        after = manifests[idx]
        before_files = set(find_files(before, suffixes, preferred))
        after_files = set(find_files(after, suffixes, preferred))
        if preferred and not after_files:
            before_files = set(find_files(before, suffixes, None))
            after_files = set(find_files(after, suffixes, None))
        appeared = sorted(after_files - before_files)
        if appeared:
            return make_file_presence_localization(
                stage,
                before,
                after,
                appeared[0],
                0.68,
                "Opaque target artifact appeared between snapshots; evaluating reliable file presence only.",
            ), ""
    return None, "Could not find opaque target artifact appearance."


def locate_directory_stage(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    kind = stage.get("task_kind")
    if kind == "filesystem_create_folder":
        return locate_create_folder(stage, manifests, start_index, end_index)
    if kind == "filesystem_create_subfolders":
        return locate_create_subfolders(stage, manifests, start_index, end_index)
    if kind == "filesystem_move_or_classify_files":
        return locate_classified_files(stage, manifests, start_index, end_index)
    return None, "No directory localization rule is available for this filesystem stage."


def make_directory_localization(
    stage: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    root_relative_path: str,
    expected_dirs: list[str],
    expected_files: list[str],
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    localized = deepcopy(stage)
    localized["input_snapshot"] = before["snapshot"]
    localized["gold_snapshot"] = after["snapshot"]
    localized["target_relative_path"] = root_relative_path
    localized["evaluator_candidate"] = "compare_directory_tree"
    localized["evaluation_hint"] = "rule_based"
    localized["directory_expectation"] = {
        "root_relative_path": root_relative_path,
        "dirs": sorted({_norm_path(path) for path in expected_dirs}),
        "files": sorted({_norm_path(path) for path in expected_files}),
        "allow_extra": True,
    }
    localized["localization"] = {
        "status": "localized",
        "confidence": confidence,
        "reason": reason,
        "changed_file_count": changed_file_count(before, after),
    }
    return localized


def _norm_path(path: str) -> str:
    return str(path).replace("\\", "/").strip("/")


def transition_indices(manifests: list[dict[str, Any]], start_index: int, end_index: int | None = None) -> range:
    start = max(1, start_index)
    end = min(len(manifests) - 1, end_index if end_index is not None else len(manifests) - 1)
    if end < start:
        return range(0)
    return range(start, end + 1)


def infer_directory_context(stage: dict[str, Any], manifests: list[dict[str, Any]]) -> tuple[str, str | None]:
    text = stage.get("instruction", "")
    values = quoted_values(text)
    container = next((value for value in values if "." not in value and "folder" not in value.lower()), None)
    if "Movie Box Office Data" in text:
        return "Movie Box Office Data", container
    if container:
        for manifest in manifests:
            matching_dirs = [path for path in manifest.get("dirs", []) if path.endswith(container)]
            if matching_dirs:
                return matching_dirs[0], None
    return "", container


def locate_create_folder(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    root_rel, folder_name = infer_directory_context(stage, manifests)
    if not folder_name:
        values = [value for value in quoted_values(stage.get("instruction", "")) if "." not in value]
        folder_name = values[0] if values else None
    if not folder_name:
        return None, "Could not infer the folder name to create."
    target_dir = _norm_path(f"{root_rel}/{folder_name}" if root_rel else folder_name)
    root = _norm_path(root_rel)
    expected_dir = _norm_path(folder_name if root else target_dir)
    for idx in transition_indices(manifests, start_index, end_index):
        before_dirs = set(manifests[idx - 1]["dirs"])
        after_dirs = set(manifests[idx]["dirs"])
        if target_dir not in before_dirs and target_dir in after_dirs:
            return make_directory_localization(
                stage,
                manifests[idx - 1],
                manifests[idx],
                root,
                [expected_dir],
                [],
                0.74,
                f"Directory '{target_dir}' appeared between snapshots.",
            ), ""
    return None, f"Could not find creation of directory '{target_dir}'."


def locate_create_subfolders(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    root_rel, _ = infer_directory_context(stage, manifests)
    values = [value for value in quoted_values(stage.get("instruction", "")) if "." not in value]
    subfolders = [value for value in values if value != root_rel and value.lower() != "records"]
    if len(subfolders) < 2:
        # Fall back to snapshots when the instruction gives only an example folder name.
        plus_minus = []
        for manifest in manifests:
            plus_minus = [
                path for path in manifest["dirs"]
                if "Records/" in path and ("+" in path or "-" in path)
            ]
            if len(plus_minus) >= 2:
                root_rel = root_rel or plus_minus[0].split("/Records/")[0]
                subfolders = [path.split("/Records/", 1)[1] for path in plus_minus]
                break
    root = _norm_path(root_rel if root_rel.lower().endswith("records") else f"{root_rel}/Records" if root_rel else "Records")
    target_dirs = [_norm_path(f"{root}/{name}") for name in subfolders]
    for idx in transition_indices(manifests, start_index, end_index):
        before_dirs = set(manifests[idx - 1]["dirs"])
        after_dirs = set(manifests[idx]["dirs"])
        if target_dirs and all(path in after_dirs for path in target_dirs) and not all(path in before_dirs for path in target_dirs):
            return make_directory_localization(
                stage,
                manifests[idx - 1],
                manifests[idx],
                root,
                subfolders,
                [],
                0.7,
                "Required subdirectories appeared under the Records folder.",
            ), ""
    return None, "Could not find creation of the required subfolders."


def locate_classified_files(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    root_rel, _ = infer_directory_context(stage, manifests)
    root = _norm_path(f"{root_rel}/Records" if root_rel else "Records")
    best: tuple[int, int, list[str]] | None = None
    for idx in transition_indices(manifests, start_index, end_index):
        files = [
            path.split(f"{root}/", 1)[1]
            for path in manifests[idx]["files"]
            if path.startswith(f"{root}/") and Path(path).suffix.lower() in {".jpg", ".jpeg", ".png"}
        ]
        score = len(files)
        if score and (best is None or score > best[0]):
            best = (score, idx, files)
    if best and best[0] >= 2:
        _, idx, files = best
        before_idx = max(start_index - 1, 0)
        return make_directory_localization(
            stage,
            manifests[before_idx],
            manifests[idx],
            root,
            [],
            files,
            0.68,
            f"Found {len(files)} classified image files under the Records folder.",
        ), ""
    return None, "Could not find classified files under the Records folder."


def make_localization(
    stage: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    rel_path: str,
    confidence: float,
    reason: str,
) -> dict[str, Any]:
    suffix = after["files"][rel_path]["suffix"]
    localized = deepcopy(stage)
    localized["input_snapshot"] = before["snapshot"]
    localized["gold_snapshot"] = after["snapshot"]
    localized["target_relative_path"] = rel_path
    localized["evaluator_candidate"] = SUPPORTED_EVALUATORS.get(suffix)
    localized["evaluation_hint"] = "rule_based" if localized["evaluator_candidate"] else stage.get("evaluation_hint", "llm_assisted")
    localized["localization"] = {
        "status": "localized",
        "confidence": confidence,
        "reason": reason,
        "changed_file_count": changed_file_count(before, after),
    }
    return localized


def make_pending_evaluator_localization(
    stage: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    rel_path: str | None,
    reason: str,
) -> dict[str, Any]:
    localized = deepcopy(stage)
    localized["input_snapshot"] = before["snapshot"]
    localized["gold_snapshot"] = after["snapshot"]
    if rel_path:
        localized["target_relative_path"] = rel_path
    localized["evaluator_candidate"] = None
    localized["evaluation_hint"] = "pending_evaluator"
    localized["localization"] = {
        "status": "pending_evaluator",
        "confidence": 0.55,
        "reason": reason,
        "changed_file_count": changed_file_count(before, after),
    }
    return localized


def locate_planned_pending_evaluator_stage(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    snapshot_index: dict[str, int],
    reason: str,
    min_input_snapshot: str | None = None,
) -> dict[str, Any] | None:
    input_snapshot = stage.get("planned_input_snapshot")
    gold_snapshot = stage.get("planned_gold_snapshot")
    if not input_snapshot or not gold_snapshot:
        return None
    if input_snapshot not in snapshot_index or gold_snapshot not in snapshot_index:
        return None
    input_idx = snapshot_index[input_snapshot]
    gold_idx = snapshot_index[gold_snapshot]
    if min_input_snapshot and min_input_snapshot in snapshot_index:
        input_idx = max(input_idx, snapshot_index[min_input_snapshot])
    if gold_idx <= input_idx:
        return None
    before = manifests[input_idx]
    after = manifests[gold_idx]
    suffixes, preferred = choose_file_for_stage(stage)
    before_files = set(find_files(before, suffixes, preferred)) if suffixes else set(before["files"])
    after_files = set(find_files(after, suffixes, preferred)) if suffixes else set(after["files"])
    if preferred and suffixes and not after_files:
        before_files = set(find_files(before, suffixes, None))
        after_files = set(find_files(after, suffixes, None))
    appeared = sorted(after_files - before_files)
    changed = sorted(
        rel
        for rel in (before_files & after_files)
        if before["files"].get(rel, {}).get("size") != after["files"].get(rel, {}).get("size")
    )
    target = appeared[0] if appeared else changed[0] if changed else None
    if not target:
        # A planned window may contain side effects such as monitoring/export archives
        # that are not the user-facing artifact. Do not turn those into pending tasks;
        # let the main flow merge the stage with an adjacent evaluable state instead.
        return None
    if target:
        suffix = after["files"].get(target, {}).get("suffix")
        if suffix in SUPPORTED_EVALUATORS:
            return make_localization(
                stage,
                before,
                after,
                target,
                0.62,
                f"{reason} Planned snapshots show an observable artifact change; using generic {SUPPORTED_EVALUATORS[suffix]} evaluator.",
            )
        if suffix in LLM_JUDGE_SUFFIXES:
            return make_llm_judge_localization(
                stage,
                before,
                after,
                target,
                0.58,
                f"{reason} Planned snapshots show a previewable artifact change; using LLM judge evaluator.",
            )
        if suffix in OPAQUE_EXISTENCE_SUFFIXES and target in appeared:
            return make_file_presence_localization(
                stage,
                before,
                after,
                target,
                0.62,
                f"{reason} Planned snapshots show an opaque artifact appeared; evaluating reliable file presence only.",
            )
    return make_pending_evaluator_localization(
        stage,
        before,
        after,
        target,
        f"{reason} Planned snapshots show an observable artifact change, but no reliable rule-based evaluator is available yet.",
    )


def locate_file_appearance(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    suffixes: set[str],
    preferred: str | None,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    for idx in transition_indices(manifests, start_index, end_index):
        before = manifests[idx - 1]
        after = manifests[idx]
        before_files = set(find_files(before, suffixes, preferred))
        after_files = set(find_files(after, suffixes, preferred))
        appeared = sorted(after_files - before_files)
        if appeared:
            return make_localization(stage, before, after, appeared[0], 0.82, "Target file appeared between snapshots."), ""
    return None, "Could not find target file appearance."


def locate_sheet_rename(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    suffixes: set[str],
    preferred: str | None,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    wanted_sheet = extract_quoted_label(stage.get("instruction", ""))
    for idx in transition_indices(manifests, start_index, end_index):
        before = manifests[idx - 1]
        after = manifests[idx]
        for rel in find_files(after, suffixes, preferred):
            if rel not in before["files"]:
                continue
            before_names = get_summary(before, rel).get("sheet_names", [])
            after_names = get_summary(after, rel).get("sheet_names", [])
            if before_names == after_names or not after_names:
                continue
            if wanted_sheet and wanted_sheet not in after_names:
                # Some collected traces contain minor wording typos; still accept a clear Sheet1 rename.
                if before_names != ["Sheet1"] and "Sheet1" not in before_names:
                    continue
            return make_localization(stage, before, after, rel, 0.78, "Workbook sheet names changed between snapshots."), ""
    return None, "Could not find a workbook sheet rename transition."


def locate_xlsx_content_growth(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    suffixes: set[str],
    preferred: str | None,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    matches: list[tuple[int, int, str, int, int]] = []
    stage_text = f"{stage.get('stage_name', '')} {stage.get('instruction', '')}".lower()
    prefer_early_header = any(token in stage_text for token in ("header", "column", "title row"))
    for idx in transition_indices(manifests, start_index, end_index):
        before = manifests[idx - 1]
        after = manifests[idx]
        for rel in find_files(after, suffixes, preferred):
            if rel not in before["files"]:
                continue
            before_nonempty = int(get_summary(before, rel).get("nonempty_cells") or 0)
            after_nonempty = int(get_summary(after, rel).get("nonempty_cells") or 0)
            before_charts = int(get_summary(before, rel).get("chart_count") or 0)
            after_charts = int(get_summary(after, rel).get("chart_count") or 0)
            if after_nonempty <= before_nonempty:
                continue
            # Prefer the largest content increase before chart-only work begins.
            if after_charts > before_charts:
                continue
            delta = after_nonempty - before_nonempty
            matches.append((delta, idx, rel, before_nonempty, after_nonempty))
    if matches:
        if prefer_early_header:
            best = sorted(matches, key=lambda item: (item[1], item[0]))[0]
        else:
            best = sorted(matches, key=lambda item: (-item[0], item[1]))[0]
        _, idx, rel, before_nonempty, after_nonempty = best
        return make_localization(
            stage,
            manifests[idx - 1],
            manifests[idx],
            rel,
            0.76,
            f"Workbook non-empty cells increased from {before_nonempty} to {after_nonempty}.",
        ), ""
    return None, "Could not find workbook content growth."


def locate_xlsx_chart_growth(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    suffixes: set[str],
    preferred: str | None,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    for idx in transition_indices(manifests, start_index, end_index):
        before = manifests[idx - 1]
        after = manifests[idx]
        for rel in find_files(after, suffixes, preferred):
            if rel not in before["files"]:
                continue
            before_charts = int(get_summary(before, rel).get("chart_count") or 0)
            after_charts = int(get_summary(after, rel).get("chart_count") or 0)
            if after_charts > before_charts:
                return make_localization(
                    stage,
                    before,
                    after,
                    rel,
                    0.84,
                    f"Workbook drawing/chart count increased from {before_charts} to {after_charts}.",
                ), ""
    return None, "Could not find workbook chart growth."


def locate_file_content_change(
    stage: dict[str, Any],
    manifests: list[dict[str, Any]],
    start_index: int,
    suffixes: set[str],
    preferred: str | None,
    end_index: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    for idx in transition_indices(manifests, start_index, end_index):
        before = manifests[idx - 1]
        after = manifests[idx]
        for rel in find_files(after, suffixes, preferred):
            if rel not in before["files"]:
                continue
            if after["files"][rel].get("size") != before["files"][rel].get("size"):
                return make_localization(stage, before, after, rel, 0.7, "Target file changed between snapshots."), ""
    return None, "Could not find target file content change."


def pending_stage(stage: dict[str, Any], reason: str, status: str = "pending_snapshot_localization") -> dict[str, Any]:
    pending = deepcopy(stage)
    pending["localization"] = {"status": status, "confidence": 0.0, "reason": reason}
    return pending


def merge_stage_into_previous(previous: dict[str, Any], current: dict[str, Any], reason: str) -> dict[str, Any]:
    merged = deepcopy(previous)
    merged_names = list(merged.get("merged_stage_names", [merged.get("stage_name")]))
    merged_names.append(current.get("stage_name"))
    merged["merged_stage_names"] = merged_names
    merged["merged_stage_indices"] = list(merged.get("merged_stage_indices", [merged.get("stage_index")]))
    merged["merged_stage_indices"].append(current.get("stage_index"))
    merged["stage_name"] = f"{merged.get('stage_name')}_and_{current.get('stage_name')}"
    merged["instruction"] = merge_instructions(merged.get("instruction", ""), current.get("instruction", ""))
    merged["trajectory_end"] = current.get("trajectory_end") or merged.get("trajectory_end")
    current_gold = current.get("gold_snapshot") or current.get("planned_gold_snapshot")
    merged_gold = merged.get("gold_snapshot") or merged.get("planned_gold_snapshot")
    if current_gold and (not merged_gold or str(current_gold) > str(merged_gold)):
        merged["gold_snapshot"] = current_gold
        merged["planned_gold_snapshot"] = current_gold
    if current.get("trajectory_evidence"):
        merged["trajectory_evidence"] = " | ".join(
            item for item in [merged.get("trajectory_evidence"), current.get("trajectory_evidence")] if item
        )
    if current.get("snapshot_evidence"):
        merged["snapshot_evidence"] = " | ".join(
            item for item in [merged.get("snapshot_evidence"), current.get("snapshot_evidence")] if item
        )
    merged.setdefault("localization", {})
    merged["localization"]["merged_with_following_stage"] = {
        "stage_index": current.get("stage_index"),
        "stage_name": current.get("stage_name"),
        "reason": reason,
    }
    return merged


def merge_stages_into_current(prefixes: list[dict[str, Any]], current: dict[str, Any], reason: str) -> dict[str, Any]:
    merged = deepcopy(current)
    prefix_names: list[Any] = []
    prefix_indices: list[Any] = []
    prefix_instruction = ""
    prefix_trajectory_evidence: list[str] = []
    prefix_snapshot_evidence: list[str] = []

    for prefix in prefixes:
        prefix_names.extend(prefix.get("merged_stage_names", [prefix.get("stage_name")]))
        prefix_indices.extend(prefix.get("merged_stage_indices", [prefix.get("stage_index")]))
        prefix_instruction = merge_instructions(prefix_instruction, prefix.get("instruction", ""))
        if prefix.get("trajectory_evidence"):
            prefix_trajectory_evidence.append(prefix["trajectory_evidence"])
        if prefix.get("snapshot_evidence"):
            prefix_snapshot_evidence.append(prefix["snapshot_evidence"])

    merged["merged_stage_names"] = prefix_names + list(merged.get("merged_stage_names", [merged.get("stage_name")]))
    merged["merged_stage_indices"] = prefix_indices + list(merged.get("merged_stage_indices", [merged.get("stage_index")]))
    merged["stage_name"] = "_and_".join(str(item) for item in merged["merged_stage_names"] if item)
    merged["instruction"] = merge_instructions(prefix_instruction, merged.get("instruction", ""))
    if prefixes:
        merged["trajectory_start"] = prefixes[0].get("trajectory_start") or merged.get("trajectory_start")
        prefix_input = prefixes[0].get("input_snapshot") or prefixes[0].get("planned_input_snapshot")
        if prefix_input:
            merged["input_snapshot"] = prefix_input
            merged["planned_input_snapshot"] = prefix_input
    evidence = prefix_trajectory_evidence + ([merged.get("trajectory_evidence")] if merged.get("trajectory_evidence") else [])
    if evidence:
        merged["trajectory_evidence"] = " | ".join(evidence)
    snapshot_evidence = prefix_snapshot_evidence + ([merged.get("snapshot_evidence")] if merged.get("snapshot_evidence") else [])
    if snapshot_evidence:
        merged["snapshot_evidence"] = " | ".join(snapshot_evidence)
    merged.setdefault("localization", {})
    merged["localization"]["merged_with_previous_stages"] = [
        {
            "stage_index": prefix.get("stage_index"),
            "stage_name": prefix.get("stage_name"),
            "reason": reason,
        }
        for prefix in prefixes
    ]
    return merged


def merge_instructions(first: str, second: str) -> str:
    first_clean = first.strip().rstrip("?")
    second_clean = second.strip()
    if second_clean.lower().startswith("could you "):
        second_clean = second_clean[10:]
    second_clean = second_clean.rstrip("?")
    if not first_clean:
        return second_clean
    if not second_clean:
        return first
    return f"{first_clean}, and then {second_clean}?"


def expand_localized_to_planned_bounds(localized: dict[str, Any], stage: dict[str, Any]) -> dict[str, Any]:
    expanded = deepcopy(localized)
    planned_input = stage.get("planned_input_snapshot")
    planned_gold = stage.get("planned_gold_snapshot")
    current_input = expanded.get("input_snapshot")
    current_gold = expanded.get("gold_snapshot")
    if planned_input and (not current_input or str(planned_input) < str(current_input)):
        expanded["input_snapshot"] = planned_input
        expanded["planned_input_snapshot"] = planned_input
        expanded.setdefault("localization", {})["expanded_to_planned_input_snapshot"] = planned_input
    if planned_gold and (not current_gold or str(planned_gold) > str(current_gold)):
        expanded["gold_snapshot"] = planned_gold
        expanded["planned_gold_snapshot"] = planned_gold
        expanded.setdefault("localization", {})["expanded_to_planned_gold_snapshot"] = planned_gold
    return expanded


def enforce_chain_input(localized: dict[str, Any], chain_input_snapshot: str | None) -> dict[str, Any]:
    if not chain_input_snapshot:
        return localized
    current_input = localized.get("input_snapshot")
    if current_input == chain_input_snapshot:
        return localized
    chained = deepcopy(localized)
    chained["input_snapshot"] = chain_input_snapshot
    chained.setdefault("localization", {})["chain_input_snapshot"] = chain_input_snapshot
    chained["localization"]["chain_input_replaced"] = current_input
    return chained


def should_merge_with_previous(stage: dict[str, Any], error: str) -> bool:
    text = f"{stage.get('stage_name', '')} {stage.get('instruction', '')} {error}".lower()
    if stage.get("planned_input_snapshot") and stage.get("planned_input_snapshot") == stage.get("planned_gold_snapshot"):
        return True
    merge_markers = [
        "save",
        "export",
        "final",
        "no change",
        "could not find target file appearance",
        "could not find workbook chart growth",
        "could not find target file content change",
    ]
    return any(marker in text for marker in merge_markers)


def trajectory_search_window(
    stage: dict[str, Any],
    trajectory_count: int,
    transition_count: int,
    radius: int = 1,
) -> tuple[int | None, int | None]:
    start = stage.get("trajectory_start")
    end = stage.get("trajectory_end")
    if not isinstance(start, int) or not isinstance(end, int) or trajectory_count <= 0 or transition_count <= 0:
        return None, None
    start = max(1, min(start, trajectory_count))
    end = max(start, min(end, trajectory_count))
    approx_start = int(((start - 1) / max(1, trajectory_count - 1)) * max(1, transition_count - 1)) + 1
    approx_end = int(((end - 1) / max(1, trajectory_count - 1)) * max(1, transition_count - 1)) + 1
    return max(1, approx_start - radius), min(transition_count, approx_end + radius)


def planned_snapshot_window(stage: dict[str, Any], snapshot_index: dict[str, int]) -> tuple[int | None, int | None]:
    input_snapshot = stage.get("planned_input_snapshot")
    gold_snapshot = stage.get("planned_gold_snapshot")
    if not input_snapshot or not gold_snapshot:
        return None, None
    if input_snapshot not in snapshot_index or gold_snapshot not in snapshot_index:
        return None, None
    input_idx = snapshot_index[input_snapshot]
    gold_idx = snapshot_index[gold_snapshot]
    if gold_idx <= input_idx:
        return None, None
    # transition idx compares manifests[idx - 1] -> manifests[idx].
    return input_idx + 1, gold_idx


def localize_source_map(source_map: dict[str, Any]) -> dict[str, Any]:
    task_name = source_map["source_name"]
    names = snapshot_names(task_name)
    manifests = [build_manifest(task_name, name) for name in names]
    snapshot_index = {manifest["snapshot"]: idx for idx, manifest in enumerate(manifests)}
    trajectory_count = len(source_map.get("trajectory_hints", []))
    transition_count = max(0, len(manifests) - 1)

    kept: list[dict[str, Any]] = []
    assisted: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    localized_by_stage: dict[int, dict[str, Any]] = {}
    unresolved_prefix: list[dict[str, Any]] = []

    for stage in source_map.get("candidate_atomic_tasks", []):
        if stage.get("evaluation_hint") == "unsupported":
            reason = "Stage was marked unsupported by decomposition and must be merged into the executable workflow."
            if kept:
                merged = merge_stage_into_previous(kept[-1], stage, reason)
                kept[-1] = merged
                localized_by_stage[int(stage["stage_index"])] = merged
                for merged_idx in merged.get("merged_stage_indices", []):
                    if isinstance(merged_idx, int):
                        localized_by_stage[merged_idx] = merged
            else:
                unresolved_prefix.append(stage)
            continue

        dep_indices = [int(item) for item in stage.get("depends_on", []) if str(item).isdigit()]
        dep_positions = [
            snapshot_index[localized_by_stage[dep]["gold_snapshot"]]
            for dep in dep_indices
            if dep in localized_by_stage and localized_by_stage[dep].get("gold_snapshot") in snapshot_index
        ]
        # A dependent stage should begin after all dependency gold snapshots.
        # The transition loop compares manifests[idx - 1] -> manifests[idx],
        # so starting at dep_position + 1 makes the dependency gold snapshot
        # the new input state.
        chain_positions = [
            snapshot_index[kept[-1]["gold_snapshot"]]
            for _ in [None]
            if kept and kept[-1].get("gold_snapshot") in snapshot_index
        ]
        dependency_start_index = (max(dep_positions + chain_positions) + 1) if (dep_positions or chain_positions) else 1
        chain_input_snapshot = manifests[dependency_start_index - 1]["snapshot"] if 0 < dependency_start_index <= len(manifests) else None
        start_index = dependency_start_index
        plan_start, plan_end = planned_snapshot_window(stage, snapshot_index)
        prior_start, prior_end = trajectory_search_window(stage, trajectory_count, transition_count)
        if plan_start is not None:
            start_index = max(start_index, plan_start)
            end_index = plan_end
            localization_prior = "planned_snapshot"
        else:
            if prior_start is not None:
                start_index = max(start_index, prior_start)
            end_index = prior_end
            localization_prior = "trajectory_window" if prior_start is not None else "dependency_order"

        artifact = str(stage.get("expected_artifact") or "").lower()
        apps = set(stage.get("apps", []))
        simple_suffixes, _ = choose_file_for_stage(stage)
        if simple_suffixes and simple_suffixes <= {"png", "jpg", "jpeg", "pdf", "mp4", "zip", "svg"}:
            localized, error = locate_file_artifact_stage(stage, manifests, start_index, end_index)
            used_fallback = False
            if not localized and prior_start is not None:
                localized, error = locate_file_artifact_stage(stage, manifests, dependency_start_index, None)
                used_fallback = localized is not None
            if localized and localized.get("evaluator_candidate"):
                localized = expand_localized_to_planned_bounds(localized, stage)
                localized = enforce_chain_input(localized, chain_input_snapshot)
                localized["localization"]["trajectory_window"] = {
                    "trajectory_start": stage.get("trajectory_start"),
                    "trajectory_end": stage.get("trajectory_end"),
                    "search_start_index": start_index,
                    "search_end_index": end_index,
                    "used_unbounded_fallback": used_fallback,
                    "prior_source": localization_prior,
                    "planned_input_snapshot": stage.get("planned_input_snapshot"),
                    "planned_gold_snapshot": stage.get("planned_gold_snapshot"),
                }
                if unresolved_prefix:
                    localized = merge_stages_into_current(
                        unresolved_prefix,
                        localized,
                        "Earlier stages had no standalone evaluator and were merged forward.",
                    )
                    localized = enforce_chain_input(localized, chain_input_snapshot)
                    unresolved_prefix = []
                kept.append(localized)
                localized_by_stage[int(stage["stage_index"])] = localized
                for merged_idx in localized.get("merged_stage_indices", []):
                    if isinstance(merged_idx, int):
                        localized_by_stage[merged_idx] = localized
                continue

        opaque_suffixes, _ = choose_opaque_file_for_stage(stage)
        if opaque_suffixes:
            localized, error = locate_opaque_file_presence_stage(stage, manifests, start_index, end_index)
            used_fallback = False
            if not localized and prior_start is not None:
                localized, error = locate_opaque_file_presence_stage(stage, manifests, dependency_start_index, None)
                used_fallback = localized is not None
            if localized and localized.get("evaluator_candidate"):
                localized = expand_localized_to_planned_bounds(localized, stage)
                localized = enforce_chain_input(localized, chain_input_snapshot)
                localized["localization"]["trajectory_window"] = {
                    "trajectory_start": stage.get("trajectory_start"),
                    "trajectory_end": stage.get("trajectory_end"),
                    "search_start_index": start_index,
                    "search_end_index": end_index,
                    "used_unbounded_fallback": used_fallback,
                    "prior_source": localization_prior,
                    "planned_input_snapshot": stage.get("planned_input_snapshot"),
                    "planned_gold_snapshot": stage.get("planned_gold_snapshot"),
                    "presence_only": True,
                }
                if unresolved_prefix:
                    localized = merge_stages_into_current(
                        unresolved_prefix,
                        localized,
                        "Earlier stages had no standalone evaluator and were merged forward.",
                    )
                    localized = enforce_chain_input(localized, chain_input_snapshot)
                    unresolved_prefix = []
                kept.append(localized)
                localized_by_stage[int(stage["stage_index"])] = localized
                for merged_idx in localized.get("merged_stage_indices", []):
                    if isinstance(merged_idx, int):
                        localized_by_stage[merged_idx] = localized
                continue

        if artifact in {"directory_state", "clipboard", "mixed"} or apps == {"os"}:
            localized, error = locate_directory_stage(stage, manifests, start_index, end_index)
            used_fallback = False
            if not localized and prior_start is not None:
                localized, error = locate_directory_stage(stage, manifests, dependency_start_index, None)
                used_fallback = localized is not None
            if localized and localized.get("evaluator_candidate"):
                localized = expand_localized_to_planned_bounds(localized, stage)
                localized = enforce_chain_input(localized, chain_input_snapshot)
                localized["localization"]["trajectory_window"] = {
                    "trajectory_start": stage.get("trajectory_start"),
                    "trajectory_end": stage.get("trajectory_end"),
                    "search_start_index": start_index,
                    "search_end_index": end_index,
                    "used_unbounded_fallback": used_fallback,
                    "prior_source": localization_prior,
                    "planned_input_snapshot": stage.get("planned_input_snapshot"),
                    "planned_gold_snapshot": stage.get("planned_gold_snapshot"),
                }
                if unresolved_prefix:
                    localized = merge_stages_into_current(unresolved_prefix, localized, "Earlier stages had no standalone evaluator and were merged forward.")
                    localized = enforce_chain_input(localized, chain_input_snapshot)
                    unresolved_prefix = []
                kept.append(localized)
                localized_by_stage[int(stage["stage_index"])] = localized
                for merged_idx in localized.get("merged_stage_indices", []):
                    if isinstance(merged_idx, int):
                        localized_by_stage[merged_idx] = localized
            else:
                reason = error or "No supported directory evaluator could be assigned."
                pending = locate_planned_pending_evaluator_stage(stage, manifests, snapshot_index, reason, chain_input_snapshot)
                if pending:
                    pending = enforce_chain_input(pending, chain_input_snapshot)
                    if unresolved_prefix:
                        pending = merge_stages_into_current(
                            unresolved_prefix,
                            pending,
                            "Earlier stages had no standalone evaluator and were merged into this pending evaluator stage.",
                        )
                        pending = enforce_chain_input(pending, chain_input_snapshot)
                        unresolved_prefix = []
                    if pending.get("evaluator_candidate"):
                        kept.append(pending)
                    else:
                        assisted.append(pending)
                    localized_by_stage[int(stage["stage_index"])] = pending
                    for merged_idx in pending.get("merged_stage_indices", []):
                        if isinstance(merged_idx, int):
                            localized_by_stage[merged_idx] = pending
                    continue
                if kept and should_merge_with_previous(stage, reason):
                    merged = merge_stage_into_previous(kept[-1], stage, reason)
                    kept[-1] = merged
                    localized_by_stage[int(stage["stage_index"])] = merged
                    for merged_idx in merged.get("merged_stage_indices", []):
                        if isinstance(merged_idx, int):
                            localized_by_stage[merged_idx] = merged
                else:
                    unresolved_prefix.append(stage)
            continue

        localized, error = locate_office_stage(stage, manifests, start_index, end_index)
        used_fallback = False
        if not localized and prior_start is not None:
            localized, error = locate_office_stage(stage, manifests, dependency_start_index, None)
            used_fallback = localized is not None
        if localized and localized.get("evaluator_candidate"):
            localized = expand_localized_to_planned_bounds(localized, stage)
            localized = enforce_chain_input(localized, chain_input_snapshot)
            localized["localization"]["trajectory_window"] = {
                "trajectory_start": stage.get("trajectory_start"),
                "trajectory_end": stage.get("trajectory_end"),
                "search_start_index": start_index,
                "search_end_index": end_index,
                "used_unbounded_fallback": used_fallback,
                "prior_source": localization_prior,
                "planned_input_snapshot": stage.get("planned_input_snapshot"),
                "planned_gold_snapshot": stage.get("planned_gold_snapshot"),
            }
            if unresolved_prefix:
                localized = merge_stages_into_current(unresolved_prefix, localized, "Earlier stages had no standalone evaluator and were merged forward.")
                localized = enforce_chain_input(localized, chain_input_snapshot)
                unresolved_prefix = []
            kept.append(localized)
            localized_by_stage[int(stage["stage_index"])] = localized
            for merged_idx in localized.get("merged_stage_indices", []):
                if isinstance(merged_idx, int):
                    localized_by_stage[merged_idx] = localized
        else:
            reason = error or "No supported evaluator could be assigned."
            pending = locate_planned_pending_evaluator_stage(stage, manifests, snapshot_index, reason, chain_input_snapshot)
            if pending:
                pending = enforce_chain_input(pending, chain_input_snapshot)
                if unresolved_prefix:
                    pending = merge_stages_into_current(
                        unresolved_prefix,
                        pending,
                        "Earlier stages had no standalone evaluator and were merged into this pending evaluator stage.",
                    )
                    pending = enforce_chain_input(pending, chain_input_snapshot)
                    unresolved_prefix = []
                if pending.get("evaluator_candidate"):
                    kept.append(pending)
                else:
                    assisted.append(pending)
                localized_by_stage[int(stage["stage_index"])] = pending
                for merged_idx in pending.get("merged_stage_indices", []):
                    if isinstance(merged_idx, int):
                        localized_by_stage[merged_idx] = pending
                continue
            if kept and should_merge_with_previous(stage, reason):
                merged = merge_stage_into_previous(kept[-1], stage, reason)
                kept[-1] = merged
                localized_by_stage[int(stage["stage_index"])] = merged
                for merged_idx in merged.get("merged_stage_indices", []):
                    if isinstance(merged_idx, int):
                        localized_by_stage[merged_idx] = merged
            else:
                unresolved_prefix.append(stage)

    if unresolved_prefix:
        reason = "Trailing stages had no standalone evaluator and were merged backward to preserve a complete workflow."
        if kept:
            merged = kept[-1]
            for stage in unresolved_prefix:
                merged = merge_stage_into_previous(merged, stage, reason)
            kept[-1] = merged
            for merged_idx in merged.get("merged_stage_indices", []):
                if isinstance(merged_idx, int):
                    localized_by_stage[merged_idx] = merged
        else:
            unsupported.extend(
                pending_stage(
                    stage,
                    "No stage in this task produced a reliable user-facing artifact in the snapshots; "
                    "the task is excluded from runnable benchmark examples until better ground truth is available.",
                    status="unsupported_no_observable_artifact",
                )
                for stage in unresolved_prefix
            )

    covered_stage_indices = {
        idx
        for item in kept
        for idx in item.get("merged_stage_indices", [])
        if isinstance(idx, int)
    }
    ready_ranges = [
        (item.get("input_snapshot"), item.get("gold_snapshot"))
        for item in kept
        if item.get("input_snapshot") and item.get("gold_snapshot")
    ]
    assisted = [
        item
        for item in assisted
        if item.get("stage_index") not in covered_stage_indices
        and not any(
            start <= item.get("input_snapshot", "") and item.get("gold_snapshot", "") <= end
            for start, end in ready_ranges
        )
    ]
    runnable_assisted: list[dict[str, Any]] = []
    for item in assisted:
        if item.get("evaluator_candidate") in RUNNABLE_EVALUATOR_FUNCS:
            runnable_assisted.append(item)
            continue
        blocked = deepcopy(item)
        blocked.setdefault("localization", {})
        blocked["localization"]["status"] = "unsupported_no_runnable_evaluator"
        blocked["localization"]["reason"] = (
            "The planned evaluator is not implemented as a runnable OSWorld metric; "
            "this stage is excluded until a reliable metric is added."
        )
        unsupported.append(blocked)
    assisted = runnable_assisted

    updated = deepcopy(source_map)
    updated["kept_atomic_tasks"] = kept
    updated["llm_assisted_atomic_tasks"] = assisted
    updated["unsupported_atomic_tasks"] = unsupported
    updated["stage_plan_status"] = "localized_ready" if len(kept) == len(source_map.get("candidate_atomic_tasks", [])) else "localized_partial"
    updated["localization_summary"] = {
        "candidate_count": len(source_map.get("candidate_atomic_tasks", [])),
        "kept_count": len(kept),
        "llm_assisted_count": len(assisted),
        "unsupported_count": len(unsupported),
        "snapshots_analyzed": len(manifests),
    }
    return updated


def refresh_index(source_maps_dir: Path, index_output: Path, start: int, end: int) -> None:
    index = {"sources": []}
    for idx in range(start, end + 1):
        task_name = task_name_for_index(idx)
        path = source_maps_dir / f"{task_name}.json"
        if not path.exists():
            continue
        record = load_json(path)
        index["sources"].append(
            {
                "source_name": task_name,
                "mapping_file": f"evaluation_examples/rule_based_bundle/source_maps/{task_name}.json",
                "stage_plan_source": record.get("stage_plan_source"),
                "stage_plan_status": record.get("stage_plan_status"),
                "candidate_count": len(record.get("candidate_atomic_tasks", [])),
                "kept_count": len(record.get("kept_atomic_tasks", [])),
                "llm_assisted_count": len(record.get("llm_assisted_atomic_tasks", [])),
                "unsupported_count": len(record.get("unsupported_atomic_tasks", [])),
                "unmapped_preview_count": len(record.get("unmapped_preview_atomic_tasks", [])),
                "llm_error": record.get("llm_error"),
            }
        )
    save_json(index_output, index)


def main() -> None:
    parser = argparse.ArgumentParser(description="Align LLM stage definitions to available MonitoringSnapshots.")
    parser.add_argument("--dataset-root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--bundle-root", type=Path, default=BUNDLE_ROOT)
    parser.add_argument("--task-prefix", type=str, default=TASK_PREFIX)
    parser.add_argument("--source-maps-dir", type=Path, default=BUNDLE_ROOT / "source_maps")
    parser.add_argument("--index-output", type=Path, default=BUNDLE_ROOT / "source_maps" / "index.json")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=2)
    args = parser.parse_args()
    configure(args.dataset_root, args.bundle_root, args.task_prefix)
    if args.source_maps_dir == Path(r"C:\OSWorld") / "evaluation_examples" / "rule_based_bundle" / "source_maps":
        args.source_maps_dir = BUNDLE_ROOT / "source_maps"
    if args.index_output == Path(r"C:\OSWorld") / "evaluation_examples" / "rule_based_bundle" / "source_maps" / "index.json":
        args.index_output = BUNDLE_ROOT / "source_maps" / "index.json"

    localized_count = 0
    for idx in range(args.start, args.end + 1):
        task_name = task_name_for_index(idx)
        path = args.source_maps_dir / f"{task_name}.json"
        if not path.exists():
            continue
        record = localize_source_map(load_json(path))
        save_json(path, record)
        localized_count += 1

    refresh_index(args.source_maps_dir, args.index_output, args.start, args.end)
    print(f"Localized {localized_count} source maps from {task_name_for_index(args.start)} to {task_name_for_index(args.end)}.")


if __name__ == "__main__":
    main()
