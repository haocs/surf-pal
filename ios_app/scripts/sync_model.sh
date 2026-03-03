#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${IOS_DIR}/.." && pwd)"

MODEL_SRC="${REPO_ROOT}/models/yolov8n.mlpackage"
MODEL_DEST="${IOS_DIR}/Resources/yolov8n.mlpackage"

mkdir -p "${IOS_DIR}/Resources"

if [ ! -d "${MODEL_SRC}" ]; then
  echo "CoreML model not found at ${MODEL_SRC}"
  echo "Generate it from repo root with:"
  echo "  python3 models/export_coreml.py"
  exit 1
fi

if [ -L "${MODEL_DEST}" ] || [ -d "${MODEL_DEST}" ]; then
  rm -rf "${MODEL_DEST}"
fi

cp -R "${MODEL_SRC}" "${MODEL_DEST}"
echo "Copied model bundle to ${MODEL_DEST}"
