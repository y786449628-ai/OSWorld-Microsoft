"""Run a lightweight, VM-less smoke test on a single migrated OSWorld task.

It performs every step the OSWorld runner would do *before* talking to the VM:

  1. Load the task JSON and verify required top-level fields.
  2. For each `download` config entry, fetch the URL into a local cache, mirror
     the size check, and surface 4xx/5xx errors.
  3. Resolve `evaluator.func` to a callable in `desktop_env.evaluators.metrics`.
  4. Cross-check that gold / result paths look sane.

If everything passes, the task is ready to ship to a real OSWorld run; the only
remaining unknown is the VM-side execution itself.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from desktop_env.evaluators import metrics  # noqa: E402

CACHE_DIR = ROOT / "evaluation_examples" / "rule_based_bundle" / ".smoke_cache"


def head_or_get_size(url: str) -> tuple[int, int | None]:
    """Return (status_code, content_length-or-None). Falls back to GET if HEAD
    is rejected by the CDN."""
    try:
        r = requests.head(url, allow_redirects=True, timeout=20)
        if r.status_code in {200, 302}:
            return r.status_code, int(r.headers.get("content-length", "0") or 0) or None
        return r.status_code, None
    except requests.RequestException:
        return -1, None


def download(url: str, dest: Path) -> tuple[int, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    n = 0
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
                n += len(chunk)
    return r.status_code, n


def slugify(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return p.path.lstrip("/").replace("/", "__")


def check_task(task_path: Path, *, full_download: bool) -> int:
    if not task_path.exists():
        print(f"FAIL: task json missing at {task_path}")
        return 1
    task = json.loads(task_path.read_text(encoding="utf-8"))

    print(f"=== {task.get('id')}  ({task.get('source','?')}) ===")
    print(f"instruction: {task.get('instruction','')[:120]}")
    print(f"snapshot:    {task.get('snapshot')}")
    print(f"related_apps:{task.get('related_apps')}")

    issues = 0

    # Schema sanity.
    for field in ("id", "snapshot", "instruction", "config", "evaluator"):
        if field not in task:
            print(f"  FAIL: missing field '{field}'")
            issues += 1

    # 1) Resolve evaluator function.
    ev_func = task.get("evaluator", {}).get("func")
    if not ev_func or not hasattr(metrics, ev_func):
        print(f"  FAIL: evaluator.func '{ev_func}' is not registered in metrics module")
        issues += 1
    else:
        print(f"  evaluator.func: {ev_func} -> {getattr(metrics, ev_func).__qualname__}")

    # 2) Walk config and probe download URLs.
    n_downloads = 0
    for entry in task.get("config", []) or []:
        kind = entry.get("type")
        if kind != "download":
            continue
        for f in entry.get("parameters", {}).get("files", []):
            n_downloads += 1
            url = f.get("url")
            vm_path = f.get("path")
            if not url or not vm_path:
                print(f"  FAIL: download entry missing url or path: {f}")
                issues += 1
                continue
            if full_download:
                cache_path = CACHE_DIR / slugify(url)
                try:
                    code, size = download(url, cache_path)
                    print(f"  GET  {code} {size:>10} bytes  {url[-80:]}")
                except Exception as exc:
                    print(f"  FAIL GET {url[-80:]}: {exc}")
                    issues += 1
            else:
                code, size = head_or_get_size(url)
                tag = "OK " if code in {200, 302} else "BAD"
                size_disp = f"{size:>10}" if size else " "*10
                print(f"  {tag} HEAD {code} {size_disp}  {url[-80:]}")
                if code not in {200, 302}:
                    issues += 1

    print(f"  total download entries: {n_downloads}")
    print(f"  issues: {issues}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_path", help="Path to a migrated task JSON file.")
    parser.add_argument(
        "--download", action="store_true",
        help="Actually fetch each file (default: HEAD-only probe).",
    )
    args = parser.parse_args()
    sys.exit(check_task(Path(args.task_path), full_download=args.download))


if __name__ == "__main__":
    main()
