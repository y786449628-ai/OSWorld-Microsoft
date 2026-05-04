# Wuying Local Workflow

This directory contains a lightweight orchestration layer for running OSWorld-style tasks directly on a Wuying Windows desktop without VM snapshots.

## What it does

- reads a task list
- runs a desktop reset script before each task
- generates a single-task meta file for each run
- launches the real benchmark runner command
- archives results into a hidden host-side directory
- writes workflow summaries for later inspection

## Files

- `workflow.example.json`: workflow config template
- `reset_workspace.ps1`: first-pass desktop reset script

## Main entrypoint

Run:

```powershell
python .\scripts\python\run_wuying_workflow.py --config .\deploy\wuying\workflow.example.json
```

Before that, start the local desktop server in another terminal:

```powershell
python .\desktop_env\server\main.py
```

## Important note

The workflow now uses `run_windows.py --provider_name local` so the original benchmark execution loop stays intact while the underlying desktop target becomes the local Wuying machine.

If needed, you can override these environment variables:

- `OSWORLD_LOCAL_HOST`
- `OSWORLD_LOCAL_SERVER_PORT`
- `OSWORLD_LOCAL_RESET_COMMAND`
- `OSWORLD_LOCAL_CHROMIUM_PORT`
- `OSWORLD_LOCAL_VNC_PORT`
- `OSWORLD_LOCAL_VLC_PORT`

## Recommended result locations

- visible working results: `results_wuying_local`
- hidden archived results: `C:\ProgramData\OSWorld\results_hidden`
- workflow state and logs: `C:\ProgramData\OSWorld\runtime`
