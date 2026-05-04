#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/deploy/cloud/osworld.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Copy deploy/cloud/osworld.env.example to deploy/cloud/osworld.env and fill it first."
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
INSTALL_DEPS="${INSTALL_DEPS:-true}"

cd "$ROOT_DIR"
mkdir -p logs "${RESULT_DIR:-./results_cloud}"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip

if [[ "$INSTALL_DEPS" == "true" ]]; then
  pip install -r requirements.txt
fi

HEADLESS_FLAG=()
if [[ "${HEADLESS:-true}" == "true" ]]; then
  HEADLESS_FLAG+=(--headless)
fi

python scripts/python/run_multienv.py \
  --provider_name "${PROVIDER_NAME:-docker}" \
  --domain "${DOMAIN:-all}" \
  --test_all_meta_path "${TEST_ALL_META_PATH:-evaluation_examples/test_all.json}" \
  --observation_type "${OBSERVATION_TYPE:-screenshot}" \
  --action_space "${ACTION_SPACE:-pyautogui}" \
  --model "${MODEL_NAME:-gpt-4o}" \
  --result_dir "${RESULT_DIR:-./results_cloud}" \
  --max_steps "${MAX_STEPS:-15}" \
  --num_envs "${NUM_ENVS:-1}" \
  --sleep_after_execution "${SLEEP_AFTER_EXECUTION:-3}" \
  --screen_width "${SCREEN_WIDTH:-1920}" \
  --screen_height "${SCREEN_HEIGHT:-1080}" \
  "${HEADLESS_FLAG[@]}" \
  "${@:2}"
