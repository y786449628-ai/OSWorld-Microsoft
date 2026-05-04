# OSWorld Cloud Deployment

This directory packages the existing OSWorld benchmark into a form that is easier to run on a Linux cloud server.

## Recommended target

Use an Ubuntu server with:

- Docker available
- `/dev/kvm` available for better VM performance
- at least 8 vCPU / 16 GB RAM for small parallel runs
- enough disk for VM snapshots and benchmark results

The deployment below uses the existing `docker` provider, which is the most direct way to run OSWorld on a cloud host.

## Files

- `install_host.sh`: installs server-side dependencies on Ubuntu
- `osworld.env.example`: benchmark runtime variables
- `run_benchmark.sh`: creates a Python venv and starts the benchmark
- `monitor.env.example`: monitor variables
- `start_monitor.sh`: starts the web monitor with Docker Compose

## Quick start

### 1. Prepare the host

```bash
sudo bash deploy/cloud/install_host.sh
```

### 2. Configure the benchmark

```bash
cp deploy/cloud/osworld.env.example deploy/cloud/osworld.env
```

At minimum, fill:

- `OPENAI_API_KEY`
- `MODEL_NAME`
- `TEST_ALL_META_PATH`
- `NUM_ENVS`
- `RESULT_DIR`

If your server is in mainland China or Hugging Face access is unstable, you can also set `HF_ENDPOINT`.

### 3. Start the benchmark

```bash
bash deploy/cloud/run_benchmark.sh
```

You can append any extra runner flags after the env file argument. Example:

```bash
bash deploy/cloud/run_benchmark.sh deploy/cloud/osworld.env --max_steps 20 --num_envs 4
```

## Monitor

### 1. Configure monitor paths

```bash
cp deploy/cloud/monitor.env.example deploy/cloud/monitor.env
```

The important value is `RESULTS_BASE_PATH`, which should point to the same result directory used by the benchmark.

### 2. Start the monitor

```bash
bash deploy/cloud/start_monitor.sh
```

Then open `http://<server-ip>:8080` unless you changed `FLASK_PORT`.

## Operational notes

- First run may take a long time because the Docker provider downloads the VM image automatically.
- If `/dev/kvm` is missing, OSWorld can still run, but it will be much slower.
- The benchmark scripts now create `logs/` automatically, so a fresh clone can start directly.
- Results are written under `RESULT_DIR`, and the web monitor reads from the same directory.

## Suggested first validation

Start with a small run before scaling out:

```bash
bash deploy/cloud/run_benchmark.sh deploy/cloud/osworld.env --domain libreoffice_calc --num_envs 1 --max_steps 5
```

After that succeeds, increase `NUM_ENVS` and switch back to your full task file.
