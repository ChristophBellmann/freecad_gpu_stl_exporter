#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORTER_DIR="${REPO_DIR}/GpuStlExport/exporter"

cd "${EXPORTER_DIR}"
python3 export_stl.py "$@"
