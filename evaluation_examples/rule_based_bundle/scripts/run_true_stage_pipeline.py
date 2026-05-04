import argparse
import subprocess
import sys
from pathlib import Path


BUNDLE_SCRIPTS = Path(r"C:\OSWorld\evaluation_examples\rule_based_bundle\scripts")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the true-stage benchmark pipeline end to end.")
    parser.add_argument("--dataset-root", type=Path, default=Path(r"C:\OSWorld\Microsoft"))
    parser.add_argument("--bundle-root", type=Path, default=Path(r"C:\OSWorld\evaluation_examples\rule_based_bundle"))
    parser.add_argument("--task-prefix", type=str, default="Microsoft")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=2)
    parser.add_argument("--model", type=str, default="qwen-max")
    parser.add_argument("--no-llm", action="store_true", help="Use existing preview fallback instead of LLM decomposition.")
    args = parser.parse_args()

    python = sys.executable
    report_script = BUNDLE_SCRIPTS / "build_snapshot_transition_reports.py"
    build_script = BUNDLE_SCRIPTS / "build_true_stage_plans.py"
    localize_script = BUNDLE_SCRIPTS / "localize_stage_plans.py"
    scaffold_script = BUNDLE_SCRIPTS / "scaffold_from_source_maps.py"
    common = [
        "--dataset-root",
        str(args.dataset_root),
        "--bundle-root",
        str(args.bundle_root),
        "--task-prefix",
        args.task_prefix,
    ]

    subprocess.check_call([python, str(report_script), *common, "--start", str(args.start), "--end", str(args.end)])
    build_cmd = [python, str(build_script), *common, "--start", str(args.start), "--end", str(args.end), "--model", args.model]
    if args.no_llm:
        build_cmd.append("--no-llm")
    subprocess.check_call(build_cmd)
    subprocess.check_call([python, str(localize_script), *common, "--start", str(args.start), "--end", str(args.end)])
    subprocess.check_call([python, str(scaffold_script), *common, "--start", str(args.start), "--end", str(args.end)])
    print(f"Completed true-stage pipeline for {args.task_prefix}_{args.start:02d} to {args.task_prefix}_{args.end:02d}.")


if __name__ == "__main__":
    main()
