#!/usr/bin/env bash

# Installs frontend dependencies in frontend/ (npm install or npm ci)
# Usage: ./安装前端依赖.sh [--ci] [--clean]

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$script_dir"
if [[ -f "${script_dir}/../frontend/package.json" ]]; then
  repo_root="$(cd "${script_dir}/.." && pwd)"
fi

pushd "$repo_root" >/dev/null
cleanup() {
  popd >/dev/null || true
}
trap cleanup EXIT

frontend_dir="frontend"

if [[ ! -d "$frontend_dir" ]]; then
  echo "[ERROR] frontend directory not found: ${PWD}/${frontend_dir}" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm not found. Install Node.js and ensure npm is on PATH." >&2
  exit 1
fi

use_ci=0
force_clean=0

show_help() {
  cat <<'EOF'
Usage: ./安装前端依赖.sh [--ci] [--clean]
  --ci     Use "npm ci" when package-lock.json exists
  --clean  Remove node_modules before installing
EOF
}

while (($#)); do
  case "$1" in
    --ci)
      use_ci=1
      ;;
    --clean)
      force_clean=1
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "[WARN] Unknown option: $1" >&2
      ;;
  esac
  shift
done

pushd "$frontend_dir" >/dev/null

if [[ "$force_clean" -eq 1 && -d "node_modules" ]]; then
  echo "Removing node_modules..."
  rm -rf node_modules
fi

err=0

if [[ "$use_ci" -eq 1 && -f "package-lock.json" ]]; then
  echo "Running npm ci in ${PWD} ..."
  if npm ci; then
    err=0
  else
    err=$?
  fi
else
  echo "Running npm install in ${PWD} ..."
  if npm install; then
    err=0
  else
    err=$?
  fi
fi

popd >/dev/null

if [[ "$err" -ne 0 ]]; then
  echo "[ERROR] npm exited with code $err" >&2
  exit "$err"
fi

echo "Dependencies installed successfully."
exit 0
