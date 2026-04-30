#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-cpu}"
VENV_DIR=".venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ROCM_PATH_FILE=".rocm_path.local"
CUSTOM_ROCM_PATH="${2:-${ROCM_PATH:-}}"
TORCH_WHEEL="${TORCH_WHEEL:-}"
TORCH_SPEC="${TORCH_SPEC:-}"

if [[ "${MODE}" != "cpu" && "${MODE}" != "cuda" && "${MODE}" != "rocm" && "${MODE}" != "rocm-custom" ]]; then
  echo "Usage: $0 [cpu|cuda|rocm|rocm-custom] [custom_rocm_path]"
  exit 1
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: Python not found: ${PYTHON_BIN}"
  exit 1
fi

if [[ -n "${TORCH_WHEEL}" && ! -f "${TORCH_WHEEL}" ]]; then
  echo "ERROR: TORCH_WHEEL not found: ${TORCH_WHEEL}"
  exit 1
fi

echo "Creating virtual environment in ${VENV_DIR} ..."
"${PYTHON_BIN}" -m venv --clear "${VENV_DIR}"
PY="${VENV_DIR}/bin/python"
PIP_CMD=("${PY}" -m pip)

echo "Upgrading pip/setuptools/wheel ..."
"${PIP_CMD[@]}" install --upgrade pip setuptools wheel

echo "Installing base dependency: numpy ..."
NUMPY_SPEC="${NUMPY_SPEC:-numpy<2}"
"${PIP_CMD[@]}" install "${NUMPY_SPEC}"

if [[ "${MODE}" == "cpu" ]]; then
  if [[ -n "${TORCH_WHEEL}" ]]; then
    echo "Installing custom torch wheel: ${TORCH_WHEEL}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_WHEEL}"
  elif [[ -n "${TORCH_SPEC}" ]]; then
    echo "Installing custom torch spec: ${TORCH_SPEC}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_SPEC}"
  else
    echo "Installing CPU PyTorch ..."
    "${PIP_CMD[@]}" install --index-url https://download.pytorch.org/whl/cpu torch
  fi
elif [[ "${MODE}" == "cuda" ]]; then
  if [[ -n "${TORCH_WHEEL}" ]]; then
    echo "Installing custom torch wheel: ${TORCH_WHEEL}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_WHEEL}"
  elif [[ -n "${TORCH_SPEC}" ]]; then
    echo "Installing custom torch spec: ${TORCH_SPEC}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_SPEC}"
  else
    TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu124}"
    echo "Installing CUDA PyTorch from: ${TORCH_INDEX_URL}"
    "${PIP_CMD[@]}" install --index-url "${TORCH_INDEX_URL}" torch
  fi
elif [[ "${MODE}" == "rocm" ]]; then
  if [[ -n "${TORCH_WHEEL}" ]]; then
    echo "Installing custom torch wheel: ${TORCH_WHEEL}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_WHEEL}"
  elif [[ -n "${TORCH_SPEC}" ]]; then
    echo "Installing custom torch spec: ${TORCH_SPEC}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_SPEC}"
  else
    TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/rocm6.2.4}"
    echo "Installing ROCm PyTorch from: ${TORCH_INDEX_URL}"
    "${PIP_CMD[@]}" install --index-url "${TORCH_INDEX_URL}" torch
  fi
elif [[ "${MODE}" == "rocm-custom" ]]; then
  if [[ -z "${CUSTOM_ROCM_PATH}" ]]; then
    echo "ERROR: rocm-custom mode requires a custom ROCm path."
    echo "Example: $0 rocm-custom /opt/rocm-custom"
    exit 1
  fi
  if [[ ! -d "${CUSTOM_ROCM_PATH}" ]]; then
    echo "ERROR: ROCm path does not exist: ${CUSTOM_ROCM_PATH}"
    exit 1
  fi
  if [[ -z "${TORCH_WHEEL}" ]]; then
    DEFAULT_WHEEL_DIR="${CUSTOM_ROCM_PATH}/wheels/pytorch_rocm711"
    if [[ -f "${DEFAULT_WHEEL_DIR}/torch-current.whl" ]]; then
      TORCH_WHEEL="${DEFAULT_WHEEL_DIR}/torch-current.whl"
    else
      TORCH_WHEEL="$(ls -1t "${DEFAULT_WHEEL_DIR}"/torch-*.whl 2>/dev/null | head -n 1 || true)"
    fi
  fi

  if [[ -n "${TORCH_WHEEL}" ]]; then
    echo "Installing custom torch wheel: ${TORCH_WHEEL}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_WHEEL}"
  elif [[ -n "${TORCH_SPEC}" ]]; then
    echo "Installing custom torch spec: ${TORCH_SPEC}"
    "${PIP_CMD[@]}" install --upgrade --force-reinstall "${TORCH_SPEC}"
  else
    TORCH_INDEX_URL="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/rocm6.2.4}"
    echo "Installing ROCm PyTorch from: ${TORCH_INDEX_URL}"
    "${PIP_CMD[@]}" install --index-url "${TORCH_INDEX_URL}" torch
  fi
fi

if [[ "${MODE}" == "rocm-custom" ]]; then
  printf "%s\n" "${CUSTOM_ROCM_PATH}" > "${ROCM_PATH_FILE}"
  echo "Saved custom ROCm path to ${ROCM_PATH_FILE}: ${CUSTOM_ROCM_PATH}"
elif [[ "${MODE}" == "rocm" ]]; then
  if [[ -n "${CUSTOM_ROCM_PATH}" ]]; then
    printf "%s\n" "${CUSTOM_ROCM_PATH}" > "${ROCM_PATH_FILE}"
    echo "Saved ROCm path override to ${ROCM_PATH_FILE}: ${CUSTOM_ROCM_PATH}"
  else
    rm -f "${ROCM_PATH_FILE}"
  fi
else
  rm -f "${ROCM_PATH_FILE}"
fi

echo
echo "Done. Quick check:"
echo "  ${PY} -c \"import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda, getattr(torch.version, 'hip', None))\""
