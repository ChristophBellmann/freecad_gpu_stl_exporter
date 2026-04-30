# FreeCAD GPU STL Exporter

Experimental FreeCAD workbench for exporting supported profile/revolve-style FreeCAD shapes to STL through a PyTorch CUDA/ROCm backend.

This repository does **not** replace FreeCAD's general OCCT mesher. It integrates the existing GPU STL exporter as an optional external backend so it can be tested from the FreeCAD GUI without adding PyTorch as a FreeCAD core dependency.

## Scope

Current backend:

- reads a temporary `.FCStd` copy,
- locates the selected object's `*.Shape.brp` member,
- samples B-spline profile curves,
- generates a rotational STL mesh on CPU, CUDA, or ROCm,
- writes binary STL,
- optionally imports the result back into the current FreeCAD document.

Supported today:

- profile/revolve-style shapes that match the exporter assumptions,
- CUDA via CUDA PyTorch,
- ROCm via ROCm PyTorch,
- custom ROCm path via `.rocm_path.local`, `ROCM_PATH`, or `FREECAD_ROCM_PATH`,
- CPU fallback.

Not supported as a general replacement yet:

- arbitrary BRep solids,
- getrimmte Flächen with complex boundaries,
- assemblies with many unrelated bodies as one automatic export,
- full OCCT `BRepMesh_IncrementalMesh` replacement.

## Install as FreeCAD workbench

```bash
cd /path/to/FreeCAD-GpuStlExport
./scripts/install_local.sh
```

This creates a symlink here:

```text
~/.local/share/FreeCAD/Mod/FreeCAD-GpuStlExport
```

Restart FreeCAD and select the workbench:

```text
GPU STL Export
```

Alternative custom target:

```bash
FREECAD_USER_MOD_DIR="$HOME/.FreeCAD/Mod" ./scripts/install_local.sh
```

## Setup exporter environment

From terminal:

```bash
./scripts/setup_exporter.sh cpu
./scripts/setup_exporter.sh cuda
./scripts/setup_exporter.sh rocm
./scripts/setup_exporter.sh rocm-custom /opt/rocm-custom
```

Or inside FreeCAD:

```text
GPU STL Export → Setup GPU exporter virtual environment
```

For custom wheels:

```bash
TORCH_WHEEL=/path/to/torch-*.whl ./scripts/setup_exporter.sh rocm-custom /opt/rocm-custom
TORCH_SPEC='torch==2.7.1+rocm6.2.4' ./scripts/setup_exporter.sh rocm
TORCH_INDEX_URL=https://download.pytorch.org/whl/rocm6.2.4 ./scripts/setup_exporter.sh rocm
```

## Use from FreeCAD GUI

1. Open a `.FCStd` model.
2. Select one object that has a valid `Shape`.
3. Switch to `GPU STL Export` workbench.
4. Click `Export selected Shape with GPU STL backend`.
5. Choose output path and quality preset.
6. Keep `Import resulting STL into current document` enabled if you want immediate visual inspection.

## Use from CLI

The original exporter is still available directly:

```bash
./scripts/export_cli.sh in/model.FCStd --shape Body --output out/model.stl --preset fine
./scripts/export_cli.sh in/model.FCStd --shape Body --output out/model.stl --preset draft --cpu
```

Quality presets:

| Preset | Profile samples | Rotation segments |
| --- | ---: | ---: |
| `draft` | 96 | 512 |
| `standard` | 384 | 4096 |
| `fine` | 768 | 8192 |

Manual override:

```bash
./scripts/export_cli.sh in/model.FCStd --shape Body --output out/model.stl --samples 768 --segments 8192
```

## Repository layout

```text
FreeCAD-GpuStlExport/
├── Init.py
├── InitGui.py
├── GpuStlExport/
│   ├── command.py
│   ├── external_exporter.py
│   └── exporter/
│       ├── export_stl.py
│       └── setup_venv.sh
├── resources/
│   └── gpu_stl_export.svg
├── scripts/
│   ├── export_cli.sh
│   ├── install_local.sh
│   └── setup_exporter.sh
├── docs/
│   └── upstream_integration_plan.md
└── tests/
    └── smoke.sh
```

## Smoke test

```bash
./tests/smoke.sh
```

This checks Python syntax, exporter help output, and shell script syntax. It does not require FreeCAD.

## Design decision

The workbench intentionally uses an external subprocess instead of importing PyTorch into FreeCAD's Python process. This avoids ABI/library conflicts between FreeCAD, OCCT, Qt, CUDA, ROCm, and PyTorch.

The generated STL should be visually compared against FreeCAD's normal STL export before relying on it for production parts.
