#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-rocm}"
ROCM_PATH_ARG="${2:-}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORTER_DIR="${REPO_DIR}/GpuStlExport/exporter"

cd "${EXPORTER_DIR}"
if [[ -n "${ROCM_PATH_ARG}" ]]; then
  ./setup_venv.sh "${MODE}" "${ROCM_PATH_ARG}"
else
  ./setup_venv.sh "${MODE}"
fi
