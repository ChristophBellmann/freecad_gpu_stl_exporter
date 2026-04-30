from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class ExportOptions:
    output_path: Path
    shape_name: Optional[str] = None
    preset: str = "fine"
    samples: Optional[int] = None
    segments: Optional[int] = None
    cpu: bool = False
    flip: bool = False
    open_profile: bool = False


@dataclass(frozen=True)
class ExportResult:
    output_path: Path
    command: list[str]
    stdout: str
    stderr: str
    returncode: int


def addon_root() -> Path:
    return Path(__file__).resolve().parents[1]


def exporter_dir() -> Path:
    return Path(__file__).resolve().parent / "exporter"


def exporter_script() -> Path:
    return exporter_dir() / "export_stl.py"


def setup_script() -> Path:
    return exporter_dir() / "setup_venv.sh"


def venv_python() -> Path:
    return exporter_dir() / ".venv" / "bin" / "python"


def choose_python() -> str:
    if venv_python().exists():
        return str(venv_python())
    system_python = shutil.which("python3") or shutil.which("python")
    if system_python:
        return system_python
    return sys.executable


def list_shape_members(fcstd_path: os.PathLike[str] | str) -> list[str]:
    with zipfile.ZipFile(fcstd_path) as zf:
        return sorted(name[:-10] for name in zf.namelist() if name.endswith(".Shape.brp"))


def resolve_shape_for_object(
    fcstd_path: os.PathLike[str] | str,
    object_name: Optional[str],
    object_label: Optional[str] = None,
) -> Optional[str]:
    """Return the best .Shape.brp member name for a FreeCAD object.

    If the temporary document contains exactly one shape, returning None lets the
    exporter auto-detect it. Otherwise we try object.Name and object.Label.
    """
    shapes = list_shape_members(fcstd_path)
    if not shapes:
        raise RuntimeError(f"No .Shape.brp entries found in {fcstd_path}")
    if len(shapes) == 1:
        return None

    candidates: list[str] = []
    for value in (object_name, object_label):
        if value and value not in candidates:
            candidates.append(value)

    for candidate in candidates:
        if candidate in shapes:
            return candidate

    joined = "\n  ".join(shapes)
    raise RuntimeError(
        "The exported FCStd contains multiple shape members and the selected "
        "object could not be mapped automatically. Available shapes:\n  "
        f"{joined}"
    )


def build_export_command(fcstd_path: Path, options: ExportOptions) -> list[str]:
    cmd = [
        choose_python(),
        str(exporter_script()),
        str(fcstd_path),
        "--output",
        str(options.output_path),
        "--preset",
        options.preset,
    ]
    if options.shape_name:
        cmd += ["--shape", options.shape_name]
    if options.samples is not None:
        cmd += ["--samples", str(options.samples)]
    if options.segments is not None:
        cmd += ["--segments", str(options.segments)]
    if options.cpu:
        cmd.append("--cpu")
    if options.flip:
        cmd.append("--flip")
    if options.open_profile:
        cmd.append("--open-profile")
    return cmd


def run_export(fcstd_path: os.PathLike[str] | str, options: ExportOptions) -> ExportResult:
    fcstd = Path(fcstd_path).resolve()
    out = Path(options.output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    normalized = ExportOptions(
        output_path=out,
        shape_name=options.shape_name,
        preset=options.preset,
        samples=options.samples,
        segments=options.segments,
        cpu=options.cpu,
        flip=options.flip,
        open_profile=options.open_profile,
    )
    cmd = build_export_command(fcstd, normalized)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    proc = subprocess.run(
        cmd,
        cwd=str(exporter_dir()),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return ExportResult(
        output_path=out,
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
    )


def setup_venv(mode: str, rocm_path: Optional[str] = None, extra_env: Optional[dict[str, str]] = None) -> ExportResult:
    cmd = [str(setup_script()), mode]
    if mode == "rocm-custom" and rocm_path:
        cmd.append(rocm_path)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    if extra_env:
        env.update(extra_env)

    proc = subprocess.run(
        cmd,
        cwd=str(exporter_dir()),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return ExportResult(
        output_path=venv_python(),
        command=cmd,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
    )


def command_as_text(cmd: Iterable[str]) -> str:
    return " ".join(shlex_quote(part) for part in cmd)


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)
