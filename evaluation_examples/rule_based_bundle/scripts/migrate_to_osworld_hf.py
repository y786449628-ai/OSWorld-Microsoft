"""Migrate rule_based_bundle tasks to OSWorld canonical format with HF-hosted resources.

For one app at a time, this script:
  1. Rewrites each `upload_file` config step into a `download` step that points
     at the HuggingFace dataset URL.
  2. Normalizes the VM user path (default: `78644` -> `User`).
  3. Sets `related_apps` based on the task's category folder when the field is
     empty.
  4. Validates that every referenced local resource file exists on disk so the
     subsequent HF upload won't ship broken URLs.

The script preserves the original task JSON layout and writes the migrated
files to a sibling directory `examples_windows_osworld/` for review before any
in-place replacement.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = ROOT / "evaluation_examples" / "rule_based_bundle"
RESOURCES_ROOT = ROOT / "evaluation_examples" / "resources"

HF_BASE_DEFAULT = "https://huggingface.co/datasets/Yang1741/572h6_veridesktop/resolve/main"

# Resource folder name on local disk -> path prefix to use on HF.
APP_RESOURCE_MAP = {
    "Adobe Illustrator": ("windows_adobe_illustrator", "adobe_illustrator"),
    "CAD": ("windows_cad", "cad"),
    "Figma": ("windows_figma", "figma"),
    "Microsoft": ("windows_microsoft", "microsoft"),
    "PS": ("windows_ps", "photoshop"),
    "Premiere": ("windows_premiere", "premiere"),
    "Unreal Engine": ("windows_unreal_engine", "unreal_engine"),
}

# Category folder -> default related_apps list for OSWorld scheduling hints.
RELATED_APPS_BY_CATEGORY = {
    "excel": ["excel"],
    "word": ["word"],
    "ppt": ["ppt"],
    "multi_app": [],  # leave empty; OSWorld treats no-hint as multi-app generic
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def normalize_vm_path(path: str, old_user: str, new_user: str) -> str:
    if not isinstance(path, str):
        return path
    target = f"\\Users\\{old_user}\\"
    replacement = f"\\Users\\{new_user}\\"
    return path.replace(target, replacement)


def rewrite_evaluator_paths(ev: dict, old_user: str, new_user: str) -> None:
    for slot in ("result", "expected"):
        block = ev.get(slot)
        if isinstance(block, dict):
            if "path" in block:
                block["path"] = normalize_vm_path(block["path"], old_user, new_user)
    if isinstance(ev.get("postconfig"), list):
        for entry in ev["postconfig"]:
            params = entry.get("parameters", {}) if isinstance(entry, dict) else {}
            for k in ("path", "command"):
                if k in params:
                    if isinstance(params[k], str):
                        params[k] = normalize_vm_path(params[k], old_user, new_user)
                    elif isinstance(params[k], list):
                        params[k] = [
                            normalize_vm_path(x, old_user, new_user) if isinstance(x, str) else x
                            for x in params[k]
                        ]


def local_to_hf_url(local_path: str, app_local_root: str, app_hf_prefix: str, hf_base: str) -> str | None:
    """Map a `evaluation_examples/resources/<windows_xxx>/...` local path to its
    HuggingFace download URL under the same app prefix."""
    norm = local_path.replace("\\", "/")
    # The known root for this app on local disk.
    needle = f"evaluation_examples/resources/{app_local_root}/"
    if needle not in norm:
        return None
    rest = norm.split(needle, 1)[1]
    return f"{hf_base.rstrip('/')}/{app_hf_prefix}/{rest}"


def migrate_task(
    task: dict,
    *,
    app: str,
    category: str,
    app_local_root: str,
    app_hf_prefix: str,
    hf_base: str,
    old_user: str,
    new_user: str,
    counter: Counter,
) -> dict:
    """Return a new task dict in OSWorld-canonical format."""
    new_task = json.loads(json.dumps(task, ensure_ascii=False))  # deep copy

    # related_apps fill-in.
    if not new_task.get("related_apps"):
        new_task["related_apps"] = list(RELATED_APPS_BY_CATEGORY.get(category, []))

    # snapshot: keep canonical category names for Microsoft (excel/word/ppt);
    # otherwise switch to the app's HF prefix as the snapshot tag.
    if app != "Microsoft":
        new_task["snapshot"] = app_hf_prefix

    # Rewrite config: upload_file -> download with HF URL.
    new_config = []
    for entry in new_task.get("config", []) or []:
        kind = entry.get("type")
        params = entry.get("parameters", {}) or {}
        if kind == "upload_file":
            files = params.get("files", []) or []
            new_files = []
            for f in files:
                local_path = f.get("local_path", "")
                vm_path = normalize_vm_path(f.get("path", ""), old_user, new_user)
                url = local_to_hf_url(local_path, app_local_root, app_hf_prefix, hf_base)
                if not url:
                    counter[("unmapped_local_path",)] += 1
                    # Leave as-is to surface for manual review.
                    new_files.append({"local_path": local_path, "path": vm_path})
                    continue
                new_files.append({"url": url, "path": vm_path})
                counter[("rewritten_files",)] += 1
            new_config.append({"type": "download", "parameters": {"files": new_files}})
        elif kind == "open":
            params = dict(params)
            if "path" in params:
                params["path"] = normalize_vm_path(params["path"], old_user, new_user)
            new_config.append({"type": "open", "parameters": params})
        else:
            new_config.append(entry)
    new_task["config"] = new_config

    # Rewrite evaluator paths to use the new VM user.
    if isinstance(new_task.get("evaluator"), dict):
        rewrite_evaluator_paths(new_task["evaluator"], old_user, new_user)

    counter[("tasks_migrated",)] += 1
    return new_task


def verify_local_resources(task: dict, app_local_root: str, counter: Counter) -> list[str]:
    """Scan the original task config for local_paths and confirm they exist."""
    missing: list[str] = []
    for entry in task.get("config", []) or []:
        if entry.get("type") != "upload_file":
            continue
        for f in entry.get("parameters", {}).get("files", []):
            lp = f.get("local_path")
            if not lp:
                continue
            full = (ROOT / lp).resolve() if not Path(lp).is_absolute() else Path(lp)
            if not full.exists():
                missing.append(lp)
                counter[("missing_local",)] += 1
    return missing


def migrate_app(
    app: str,
    *,
    hf_base: str,
    old_user: str,
    new_user: str,
    apply: bool,
    output_dirname: str,
) -> Counter:
    counter: Counter = Counter()
    if app not in APP_RESOURCE_MAP:
        raise ValueError(f"Unknown app: {app}")
    app_local_root, app_hf_prefix = APP_RESOURCE_MAP[app]

    src_dir = BUNDLE_ROOT / app / "examples_windows"
    out_dir = BUNDLE_ROOT / app / output_dirname
    if apply and out_dir.exists():
        shutil.rmtree(out_dir)

    for category_dir in sorted(src_dir.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        for task_path in sorted(category_dir.glob("*.json")):
            task = load_json(task_path)
            missing = verify_local_resources(task, app_local_root, counter)
            new_task = migrate_task(
                task,
                app=app,
                category=category,
                app_local_root=app_local_root,
                app_hf_prefix=app_hf_prefix,
                hf_base=hf_base,
                old_user=old_user,
                new_user=new_user,
                counter=counter,
            )
            if apply:
                out_path = out_dir / category / task_path.name
                save_json(out_path, new_task)
            if missing:
                counter[("tasks_with_missing_local",)] += 1
    return counter


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--app",
        choices=list(APP_RESOURCE_MAP.keys()),
        action="append",
        help="Limit to specific apps (repeatable). Default: Microsoft only for the pilot.",
    )
    parser.add_argument("--apply", action="store_true", help="Write migrated files to disk.")
    parser.add_argument(
        "--hf-base",
        default=HF_BASE_DEFAULT,
        help="HuggingFace dataset URL prefix (resolve/main). Default: %(default)s",
    )
    parser.add_argument("--old-user", default="78644")
    parser.add_argument("--new-user", default="User")
    parser.add_argument(
        "--output-dirname",
        default="examples_windows_osworld",
        help="Sibling directory name to write migrated tasks under each app.",
    )
    args = parser.parse_args()

    apps = args.app or ["Microsoft"]
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== migrate_to_osworld_hf [{mode}] ===")
    print(f"  HF base: {args.hf_base}")
    print(f"  user rename: {args.old_user} -> {args.new_user}")
    print(f"  apps: {apps}")

    grand: Counter = Counter()
    for app in apps:
        c = migrate_app(
            app,
            hf_base=args.hf_base,
            old_user=args.old_user,
            new_user=args.new_user,
            apply=args.apply,
            output_dirname=args.output_dirname,
        )
        print(f"\n[{app}]")
        for k, v in sorted(c.items()):
            print(f"    {k[0]}: {v}")
        grand.update(c)

    print("\n=== Totals ===")
    for k, v in sorted(grand.items()):
        print(f"  {k[0]}: {v}")
    if not args.apply:
        print("\n(dry-run) re-run with --apply to write migrated files.")


if __name__ == "__main__":
    main()
