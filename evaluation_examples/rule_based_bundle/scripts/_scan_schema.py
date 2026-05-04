"""Quick schema scan: snapshot values and VM user names across canonical and bundle."""
import json
import os
from collections import Counter

USER_PREFIX = "C:\\Users\\"


def scan(root_dir: str) -> tuple[Counter, Counter, int]:
    users: Counter = Counter()
    snaps: Counter = Counter()
    n = 0
    for root, _, files in os.walk(root_dir):
        for f in files:
            if not f.endswith(".json"):
                continue
            try:
                d = json.load(open(os.path.join(root, f), "r", encoding="utf-8"))
            except Exception:
                continue
            n += 1
            snaps[d.get("snapshot", "?")] += 1
            stk = [d]
            while stk:
                v = stk.pop()
                if isinstance(v, dict):
                    stk.extend(v.values())
                elif isinstance(v, list):
                    stk.extend(v)
                elif isinstance(v, str) and USER_PREFIX in v:
                    rest = v.split(USER_PREFIX, 1)[1]
                    name = rest.split("\\", 1)[0] if "\\" in rest else rest
                    users[name] += 1
    return snaps, users, n


def main() -> None:
    s1, u1, n1 = scan("evaluation_examples/examples_windows")
    s2, u2, n2 = scan("evaluation_examples/rule_based_bundle")
    print(f"canonical: {n1} files")
    print(f"  snapshots: {dict(s1)}")
    print(f"  users:     {dict(u1)}")
    print()
    print(f"bundle:    {n2} files")
    print(f"  snapshots: {dict(s2)}")
    print(f"  users:     {dict(u2)}")


if __name__ == "__main__":
    main()
