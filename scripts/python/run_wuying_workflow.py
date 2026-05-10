from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrate OSWorld-style execution on a Wuying Windows desktop."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="deploy/wuying/workflow.example.json",
        help="Path to workflow config JSON.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="Optional cap on number of tasks to run.",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="0-based offset in the flattened task list.",
    )
    parser.add_argument(
        "--user-home",
        type=str,
        default=None,
        help="Windows user home directory used to rewrite task paths. Defaults to USERPROFILE.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_json_sig(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def flatten_tasks(meta: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    for domain, example_ids in meta.items():
        for example_id in example_ids:
            items.append((domain, example_id))
    return items


def substitute_placeholders(command: Iterable[str], mapping: Dict[str, str]) -> List[str]:
    result: List[str] = []
    for item in command:
        current = item
        for key, value in mapping.items():
            current = current.replace("{" + key + "}", value)
        result.append(current)
    return result


def substitute_object(obj: Any, mapping: Dict[str, str]) -> Any:
    if isinstance(obj, str):
        value = obj
        for key, replacement in mapping.items():
            value = value.replace("{" + key + "}", replacement)
        return value
    if isinstance(obj, list):
        return [substitute_object(item, mapping) for item in obj]
    if isinstance(obj, dict):
        return {key: substitute_object(value, mapping) for key, value in obj.items()}
    return obj


def run_command(command: List[str], cwd: Path, label: str) -> subprocess.CompletedProcess[str]:
    print(f"[workflow] {label}: {' '.join(shlex.quote(part) for part in command)}")
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def check_server(server_url: str, timeout: int = 10) -> None:
    checks = (
        ("/screenshot", "image"),
        ("/terminal", "json"),
    )
    last_error = None
    for endpoint, mode in checks:
        try:
            response = requests.get(f"{server_url}{endpoint}", timeout=timeout)
            if response.status_code != 200:
                last_error = (
                    f"{endpoint} returned {response.status_code}: {response.text[:200]}"
                )
                continue
            if mode == "image":
                content_type = response.headers.get("Content-Type", "")
                if "image" in content_type.lower() or response.content:
                    return
                last_error = f"{endpoint} returned unexpected content type: {content_type}"
            else:
                return
        except requests.RequestException as exc:
            last_error = f"{endpoint} request failed: {exc}"
    raise RuntimeError(f"desktop server health check failed: {last_error}")


def write_task_meta(meta_dir: Path, domain: str, example_id: str) -> Path:
    ensure_dir(meta_dir)
    single_meta_path = meta_dir / f"{domain}__{example_id}.json"
    with single_meta_path.open("w", encoding="utf-8") as f:
        json.dump({domain: [example_id]}, f, indent=2)
    return single_meta_path


def load_example_file(repo_root: Path, base_dir: str, windows_dir: str, domain: str, example_id: str) -> Dict[str, Any]:
    example_path = (repo_root / base_dir / windows_dir / domain / f"{example_id}.json").resolve()
    return load_json_sig(example_path)


def infer_close_window_names(example: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for step in example.get("config", []):
        if step.get("type") == "open":
            path = step.get("parameters", {}).get("path")
            if path:
                names.append(Path(path).name)
    for step in example.get("evaluator", {}).get("postconfig", []):
        if step.get("type") == "activate_window":
            window_name = step.get("parameters", {}).get("window_name")
            if window_name:
                names.append(window_name)
    deduped: List[str] = []
    seen = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            deduped.append(name)
    return deduped


def close_windows_via_server(server_url: str, window_names: List[str], timeout: int = 10) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    headers = {"Content-Type": "application/json"}
    for window_name in window_names:
        payload = json.dumps({"window_name": window_name, "strict": False, "by_class": False})
        try:
            response = requests.post(
                f"{server_url}/setup/close_window",
                headers=headers,
                data=payload,
                timeout=timeout,
            )
            results.append(
                {
                    "window_name": window_name,
                    "status_code": response.status_code,
                    "response_text": response.text[:500],
                }
            )
        except requests.RequestException as exc:
            results.append(
                {
                    "window_name": window_name,
                    "status_code": None,
                    "response_text": str(exc),
                }
            )
    return results


def archive_results(source_dir: Path, archive_dir: Path) -> None:
    if not source_dir.exists():
        return
    ensure_dir(archive_dir.parent)
    if archive_dir.exists():
        shutil.rmtree(archive_dir)
    shutil.copytree(source_dir, archive_dir)


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def append_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(content)


def set_phase(task_record: Dict[str, Any], phase: str, detail: str | None = None) -> None:
    task_record["phase"] = phase
    task_record["last_update_at"] = dt.datetime.now().isoformat()
    print(f"[workflow] phase={phase}" + (f" detail={detail}" if detail else ""))


def summarize_runner_output(stdout: str, stderr: str) -> Tuple[str, List[str]]:
    text = f"{stdout}\n{stderr}"
    findings: List[str] = []
    if "OPENAI_API_KEY" in text:
        findings.append("missing_openai_api_key")
    if "SETUP FAILED" in text:
        findings.append("setup_failed")
    if "Traceback" in text:
        findings.append("traceback_present")
    if "ModuleNotFoundError" in text:
        findings.append("module_not_found")
    if "Failed to start recording" in text or "Failed to stop recording" in text:
        findings.append("recording_not_supported")
    if "Currently not implemented for platform" in text:
        findings.append("platform_not_implemented")
    if "PyGetWindowException" in text:
        findings.append("window_activation_warning")
    if not findings:
        return "no_known_error_markers", findings
    return ",".join(findings), findings


def collect_result_feedback(local_result_dir: Path, archived_result_dir: Path) -> Dict[str, Any]:
    feedback: Dict[str, Any] = {}
    candidate_dirs = [local_result_dir, archived_result_dir]
    for base in candidate_dirs:
        feedback_key_prefix = "archived" if base == archived_result_dir else "local"
        feedback[f"{feedback_key_prefix}_exists"] = base.exists()
        if not base.exists():
            continue
        result_txt = base / "result.txt"
        traj_jsonl = base / "traj.jsonl"
        runtime_log = base / "runtime.log"
        feedback[f"{feedback_key_prefix}_result_txt"] = result_txt.exists()
        feedback[f"{feedback_key_prefix}_traj_jsonl"] = traj_jsonl.exists()
        feedback[f"{feedback_key_prefix}_runtime_log"] = runtime_log.exists()
        if result_txt.exists():
            try:
                feedback[f"{feedback_key_prefix}_result"] = result_txt.read_text(encoding="utf-8").strip()
            except OSError:
                feedback[f"{feedback_key_prefix}_result"] = "<unreadable>"
        if traj_jsonl.exists():
            try:
                lines = [line for line in traj_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
                feedback[f"{feedback_key_prefix}_traj_lines"] = len(lines)
            except OSError:
                feedback[f"{feedback_key_prefix}_traj_lines"] = -1
    return feedback


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    config_path = (repo_root / args.config).resolve() if not os.path.isabs(args.config) else Path(args.config)
    raw_config = load_json(config_path)
    user_home = args.user_home or os.environ.get("USERPROFILE")
    if not user_home:
        raise RuntimeError("Unable to determine user home directory. Pass --user-home explicitly.")
    user_home_path = Path(user_home).resolve()
    config_placeholder_map = {
        "repo_root": str(repo_root),
        "user_home": str(user_home_path),
        "user_desktop": str(user_home_path / "Desktop"),
        "user_documents": str(user_home_path / "Documents"),
    }
    config = substitute_object(raw_config, config_placeholder_map)

    server_url = config["server_url"].rstrip("/")
    tasks_meta_path = (repo_root / config["tasks_meta_path"]).resolve()
    runner_command_template: List[str] = config["runner_command_template"]
    reset_command: List[str] = config.get("reset_command", [])
    cleanup_command: List[str] = config.get("cleanup_command", [])
    close_command: List[str] = config.get("close_command", [])
    example_base_dir = config.get("example_base_dir", "evaluation_examples/rule_based_bundle/Microsoft")
    example_windows_dir = config.get("example_windows_dir", "examples_windows_osworld")
    work_result_root = ensure_dir((repo_root / config["work_result_root"]).resolve())
    hidden_result_root = ensure_dir(Path(config["hidden_result_root"]).resolve())
    runtime_root = ensure_dir(Path(config["runtime_root"]).resolve())
    logs_root = ensure_dir(runtime_root / "workflow_logs")
    per_task_meta_root = ensure_dir(runtime_root / "task_meta")
    runner_cwd = (repo_root / config.get("runner_cwd", ".")).resolve()
    reset_before_each_task = bool(config.get("reset_before_each_task", True))
    reset_after_each_task = bool(config.get("reset_after_each_task", True))
    cleanup_after_each_task = bool(config.get("cleanup_after_each_task", False))
    delay_after_reset_sec = int(config.get("delay_after_reset_sec", 5))
    delay_after_cleanup_sec = int(config.get("delay_after_cleanup_sec", 0))

    check_server(server_url, timeout=int(config.get("server_health_timeout_sec", 10)))

    meta = load_json(tasks_meta_path)
    tasks = flatten_tasks(meta)
    if args.start_from:
        tasks = tasks[args.start_from:]
    if args.max_tasks is not None:
        tasks = tasks[:args.max_tasks]

    if not tasks:
        print("[workflow] no tasks selected")
        return 0

    summary: List[Dict[str, Any]] = []
    workflow_started_at = dt.datetime.now().strftime("%Y%m%d@%H%M%S")

    for index, (domain, example_id) in enumerate(tasks, start=1):
        task_started = time.time()
        single_meta_path = write_task_meta(per_task_meta_root, domain, example_id)
        example = load_example_file(repo_root, example_base_dir, example_windows_dir, domain, example_id)
        close_window_names = infer_close_window_names(example)
        local_result_dir = work_result_root / domain / example_id
        archived_result_dir = hidden_result_root / workflow_started_at / domain / example_id
        task_log_path = logs_root / f"{index:04d}_{domain}__{example_id}.log"

        remove_tree(local_result_dir)

        placeholder_map = {
            "domain": domain,
            "example_id": example_id,
            "task_meta_path": str(single_meta_path),
            "result_dir": str(work_result_root),
            "server_url": server_url,
            "repo_root": str(repo_root),
            "python_executable": sys.executable,
            "user_home": str(user_home_path),
            "user_desktop": str(user_home_path / "Desktop"),
            "user_documents": str(user_home_path / "Documents"),
        }

        task_record: Dict[str, Any] = {
            "index": index,
            "domain": domain,
            "example_id": example_id,
            "task_meta_path": str(single_meta_path),
            "local_result_dir": str(local_result_dir),
            "archived_result_dir": str(archived_result_dir),
            "started_at": dt.datetime.now().isoformat(),
            "phase": "selected",
        }

        try:
            set_phase(task_record, "server_check_before")
            check_server(server_url, timeout=int(config.get("server_health_timeout_sec", 10)))
            task_record["server_check_before"] = "ok"

            if reset_before_each_task and reset_command:
                set_phase(task_record, "reset_before")
                reset_cmd = substitute_placeholders(reset_command, placeholder_map)
                reset_proc = run_command(reset_cmd, repo_root, f"reset before {domain}/{example_id}")
                write_text(task_log_path, f"[reset-before]\n{reset_proc.stdout}\n{reset_proc.stderr}\n")
                task_record["reset_before_returncode"] = reset_proc.returncode
                if reset_proc.returncode != 0:
                    raise RuntimeError(f"reset command failed with exit code {reset_proc.returncode}")
                time.sleep(delay_after_reset_sec)
                set_phase(task_record, "server_check_after_reset_before")
                check_server(server_url, timeout=int(config.get("server_health_timeout_sec", 10)))
                task_record["reset_before_status"] = "ok"

            set_phase(task_record, "runner_start")
            runner_cmd = substitute_placeholders(runner_command_template, placeholder_map)
            if runner_cmd and runner_cmd[0].lower() == "python":
                runner_cmd[0] = sys.executable
            runner_proc = run_command(runner_cmd, runner_cwd, f"run {domain}/{example_id}")
            print("[workflow] runner stdout begin")
            if runner_proc.stdout:
                print(runner_proc.stdout, end="" if runner_proc.stdout.endswith("\n") else "\n")
            print("[workflow] runner stdout end")
            print("[workflow] runner stderr begin")
            if runner_proc.stderr:
                print(runner_proc.stderr, end="" if runner_proc.stderr.endswith("\n") else "\n")
            print("[workflow] runner stderr end")
            write_text(
                task_log_path,
                (
                    f"[runner-command]\n{' '.join(shlex.quote(part) for part in runner_cmd)}\n\n"
                    f"[stdout]\n{runner_proc.stdout}\n\n"
                    f"[stderr]\n{runner_proc.stderr}\n"
                ),
            )
            task_record["runner_returncode"] = runner_proc.returncode
            task_record["runner_error_summary"], task_record["runner_error_markers"] = summarize_runner_output(
                runner_proc.stdout, runner_proc.stderr
            )
            task_record["duration_sec"] = round(time.time() - task_started, 2)

            if close_command:
                set_phase(task_record, "close_after_run")
                task_record["close_window_names"] = close_window_names
                close_window_results = close_windows_via_server(
                    server_url,
                    close_window_names,
                    timeout=int(config.get("server_health_timeout_sec", 10)),
                )
                task_record["close_window_results"] = close_window_results
                append_text(
                    task_log_path,
                    "[close-window-results]\n"
                    + json.dumps(close_window_results, indent=2, ensure_ascii=False)
                    + "\n",
                )
                close_cmd = substitute_placeholders(close_command, placeholder_map)
                close_proc = run_command(close_cmd, repo_root, f"close after {domain}/{example_id}")
                append_text(task_log_path, f"\n[close-after-run]\n{close_proc.stdout}\n{close_proc.stderr}\n")
                task_record["close_after_run_returncode"] = close_proc.returncode
                if close_proc.returncode != 0:
                    raise RuntimeError(f"close-after-run command failed with exit code {close_proc.returncode}")

            set_phase(task_record, "archive_results")
            archive_results(local_result_dir, archived_result_dir)
            task_record.update(collect_result_feedback(local_result_dir, archived_result_dir))

            if cleanup_after_each_task and cleanup_command:
                set_phase(task_record, "cleanup_after")
                cleanup_cmd = substitute_placeholders(cleanup_command, placeholder_map)
                cleanup_proc = run_command(cleanup_cmd, repo_root, f"cleanup after {domain}/{example_id}")
                append_text(task_log_path, f"\n[cleanup-after]\n{cleanup_proc.stdout}\n{cleanup_proc.stderr}\n")
                task_record["cleanup_returncode"] = cleanup_proc.returncode
                if cleanup_proc.returncode != 0:
                    raise RuntimeError(f"cleanup command failed with exit code {cleanup_proc.returncode}")
                if delay_after_cleanup_sec:
                    time.sleep(delay_after_cleanup_sec)

            if reset_after_each_task and reset_command:
                set_phase(task_record, "reset_after")
                reset_after_cmd = substitute_placeholders(reset_command, placeholder_map)
                reset_after_proc = run_command(reset_after_cmd, repo_root, f"reset after {domain}/{example_id}")
                append_text(task_log_path, f"\n[reset-after]\n{reset_after_proc.stdout}\n{reset_after_proc.stderr}\n")
                task_record["reset_after_returncode"] = reset_after_proc.returncode
                if reset_after_proc.returncode != 0:
                    raise RuntimeError(f"reset-after command failed with exit code {reset_after_proc.returncode}")
                time.sleep(delay_after_reset_sec)
                set_phase(task_record, "server_check_after_reset_after")
                check_server(server_url, timeout=int(config.get("server_health_timeout_sec", 10)))
                task_record["reset_after_status"] = "ok"

            set_phase(task_record, "finalize")
            if runner_proc.returncode != 0:
                task_record["status"] = "runner_failed"
                task_record["error_stage"] = "runner"
            elif "missing_openai_api_key" in task_record["runner_error_markers"]:
                task_record["status"] = "suspect_result"
                task_record["error_stage"] = "agent_call"
            elif not task_record.get("archived_result_txt"):
                task_record["status"] = "missing_result"
                task_record["error_stage"] = "result_collection"
            elif task_record.get("archived_result") == "1.0" and "traceback_present" in task_record["runner_error_markers"]:
                task_record["status"] = "suspect_result"
                task_record["error_stage"] = "runner_log_conflict"
            else:
                task_record["status"] = "success"
                task_record["error_stage"] = None

        except Exception as exc:
            task_record["status"] = "error"
            task_record["error"] = str(exc)
            task_record["error_stage"] = task_record.get("phase")
            task_record["duration_sec"] = round(time.time() - task_started, 2)
            print(f"[workflow] task failed: {domain}/{example_id}: {exc}")

        summary.append(task_record)
        write_text(
            runtime_root / "latest_summary.json",
            json.dumps(summary, indent=2, ensure_ascii=False),
        )

    final_summary_path = runtime_root / f"summary_{workflow_started_at}.json"
    write_text(final_summary_path, json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[workflow] finished. summary: {final_summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
