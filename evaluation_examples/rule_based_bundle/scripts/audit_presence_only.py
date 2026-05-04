"""Audit presence-only compare_directory_tree tasks for evaluation soundness."""
from __future__ import annotations
import json
import os
from collections import Counter
from pathlib import Path, PureWindowsPath

ROOT = Path("evaluation_examples/rule_based_bundle")
APPS = ["Adobe Illustrator","CAD","Figma","Microsoft","PS","Premiere","Unreal Engine"]
BOILERPLATE = {"extra_urls.txt","MyProject.uproject","DDCKey-Editor.txt","AutoScreenshot.png"}


def normalize(p: str) -> str:
    return str(PureWindowsPath(p)).lower()


def main() -> None:
    stats: Counter = Counter()
    free_pass = []
    boiler = []
    for app in APPS:
        test = json.loads((ROOT / app / "test_rule_based_windows.json").read_text(encoding="utf-8"))
        for cat, ids in test.items():
            for tid in ids:
                tp = ROOT / app / "examples_windows" / cat / f"{tid}.json"
                if not tp.exists():
                    continue
                d = json.loads(tp.read_text(encoding="utf-8"))
                ev = d.get("evaluator", {})
                if ev.get("func") != "compare_directory_tree":
                    continue
                stats[(app, "total_presence_only")] += 1
                files = (ev.get("expected", {}).get("rules", {}).get("files") or [])
                checked_dir = ev.get("result", {}).get("path", "")
                checked_dir_n = normalize(checked_dir).rstrip("\\")
                uploads = []
                for c in d.get("config", []) or []:
                    if c.get("type") == "upload_file":
                        for f in c.get("parameters", {}).get("files", []):
                            uploads.append(normalize(f.get("path", "")))
                for fname in files:
                    full = checked_dir_n + "\\" + fname.lower()
                    if any(u == full for u in uploads):
                        stats[(app, "free_pass")] += 1
                        if len(free_pass) < 6:
                            free_pass.append((app, tid, fname, d.get("instruction","")[:80]))
                    if fname in BOILERPLATE:
                        stats[(app, "boilerplate_target")] += 1
                        if len(boiler) < 6:
                            boiler.append((app, tid, fname, d.get("instruction","")[:80]))
    print("Per-app presence-only audit:")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print("\n=== Free-pass examples (target file already in config upload) ===")
    for app, tid, fn, instr in free_pass:
        print(f"  [{app}] {tid}  checks={fn}")
        print(f"    {instr}")
    print("\n=== Boilerplate-target examples ===")
    for app, tid, fn, instr in boiler:
        print(f"  [{app}] {tid}  checks={fn}")
        print(f"    {instr}")


if __name__ == "__main__":
    main()
