#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "xcodegen is not installed."
  echo "Install it, then re-run:"
  echo "  brew install xcodegen"
  exit 1
fi

"${SCRIPT_DIR}/sync_model.sh"

cd "${IOS_DIR}"
xcodegen generate --spec project.yml
echo "Generated ${IOS_DIR}/SurfPal.xcodeproj"
