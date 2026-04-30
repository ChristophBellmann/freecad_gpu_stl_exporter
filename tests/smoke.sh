#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

"${PYTHON_BIN}" -m py_compile \
  Init.py \
  InitGui.py \
  GpuStlExport/__init__.py \
  GpuStlExport/external_exporter.py \
  GpuStlExport/exporter/export_stl.py

"${PYTHON_BIN}" GpuStlExport/exporter/export_stl.py --help >/dev/null
bash -n scripts/install_local.sh scripts/setup_exporter.sh scripts/export_cli.sh GpuStlExport/exporter/setup_venv.sh

echo "smoke OK"
