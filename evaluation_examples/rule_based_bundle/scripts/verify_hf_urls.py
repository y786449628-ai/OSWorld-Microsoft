"""Smoke-test that the HuggingFace URLs referenced by migrated tasks resolve.

Sends HEAD requests for a sample of distinct download URLs across each
migrated app folder. Counts 200 / 401 / 403 / 404 / other for a quick health
check after a HF upload.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
BUNDLE_ROOT = ROOT / "evaluation_examples" / "rule_based_bundle"


def collect_urls(app: str, source_dirname: str) -> list[str]:
    src = BUNDLE_ROOT / app / source_dirname
    urls: set[str] = set()
    if not src.exists():
        return []
    for tp in src.rglob("*.json"):
        d = json.loads(tp.read_text(encoding="utf-8"))
        for entry in d.get("config", []) or []:
            if entry.get("type") != "download":
                continue
            for f in entry.get("parameters", {}).get("files", []):
                u = f.get("url")
                if u:
                    urls.add(u)
    return sorted(urls)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, help="App folder name, e.g. Microsoft")
    parser.add_argument("--source-dirname", default="examples_windows_osworld")
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    urls = collect_urls(args.app, args.source_dirname)
    if not urls:
        print(f"No URLs found under {args.app}/{args.source_dirname}")
        return

    rng = random.Random(args.seed)
    sample = rng.sample(urls, min(args.sample, len(urls)))
    print(f"Probing {len(sample)} of {len(urls)} unique URLs ...\n")

    counts: Counter = Counter()
    failures: list[tuple[int, str]] = []
    for url in sample:
        try:
            r = requests.head(url, allow_redirects=True, timeout=20)
            counts[r.status_code] += 1
            if r.status_code != 200:
                failures.append((r.status_code, url))
        except Exception as exc:
            counts[("error", type(exc).__name__)] += 1
            failures.append((-1, f"{type(exc).__name__}: {url}"))

    print("Status counts:")
    for k, v in sorted(counts.items(), key=lambda kv: str(kv[0])):
        print(f"  {k}: {v}")
    if failures:
        print("\nFailures (first 10):")
        for code, u in failures[:10]:
            print(f"  [{code}] {u}")


if __name__ == "__main__":
    main()
