# Architecture

The workbench keeps experimental GPU dependencies outside FreeCAD's core Python environment.

## Data flow

```text
Selected FreeCAD object
→ temporary FCStd copy
→ selected *.Shape.brp member
→ external PyTorch exporter
→ binary STL
→ optional import into the active document
```

This separation is intentional. The workbench is the integration layer; the meshing backend runs as an external process in its own virtual environment.

## Backend choices

The exporter can operate with:

- CPU,
- CUDA-enabled PyTorch on NVIDIA GPUs,
- ROCm-enabled PyTorch on AMD GPUs,
- a custom ROCm installation.

This architecture makes GPU experimentation possible without turning PyTorch into a mandatory FreeCAD dependency.
