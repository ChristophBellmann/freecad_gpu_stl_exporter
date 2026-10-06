# Installation & Usage

## Install the workbench

The repository includes a local installation script that links the workbench into a FreeCAD user module directory.

```sh
./scripts/install_local.sh
```

After restarting FreeCAD, select **GPU STL Export**.

## Prepare the exporter environment

```sh
./scripts/setup_exporter.sh cpu
./scripts/setup_exporter.sh cuda
./scripts/setup_exporter.sh rocm
```

A custom ROCm path can also be configured.

## GUI workflow

1. Open an FCStd model.
2. Select one object with a valid Shape.
3. Switch to the GPU STL Export workbench.
4. Start the GPU export command.
5. Select output path and quality.
6. Optionally import the resulting STL for visual inspection.

## CLI workflow

The underlying exporter can also be called independently through `scripts/export_cli.sh`, which is useful for automated testing and benchmarking.
