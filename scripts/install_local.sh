#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOD_DIR="${FREECAD_USER_MOD_DIR:-${HOME}/.local/share/FreeCAD/Mod}"
TARGET="${MOD_DIR}/FreeCAD-GpuStlExport"

mkdir -p "${MOD_DIR}"

if [[ -e "${TARGET}" && ! -L "${TARGET}" ]]; then
  echo "ERROR: target exists and is not a symlink: ${TARGET}"
  exit 1
fi

ln -sfn "${REPO_DIR}" "${TARGET}"
echo "Installed symlink: ${TARGET} -> ${REPO_DIR}"
echo "Restart FreeCAD and choose the 'GPU STL Export' workbench."
