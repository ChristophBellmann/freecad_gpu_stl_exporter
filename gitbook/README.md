# FreeCAD GPU STL Exporter

Experimental FreeCAD workbench for GPU-assisted STL generation on supported profile/revolve-style geometry.

The project explores how selected meshing workloads can be moved to a PyTorch backend using CPU, NVIDIA CUDA or AMD ROCm while keeping FreeCAD's standard OCCT mesher intact as the general-purpose path.

## Why this project exists

FreeCAD must handle arbitrary BRep geometry, so replacing its standard mesher with a specialized GPU implementation would be premature. This project therefore uses an external workbench backend: supported geometry can be exported through the experimental GPU path without adding PyTorch as a FreeCAD core dependency.

The current implementation is deliberately narrow. It is an engineering experiment in GPU-assisted tessellation and FreeCAD integration, not a claim to be a universal replacement for OCCT meshing.

Continue with [Architecture](architecture.md), [GPU Meshing Pipeline](gpu-meshing-pipeline.md), [FreeCAD Integration](freecad-integration.md), [Installation & Usage](installation-and-usage.md), [Supported Geometry & Limits](supported-geometry-and-limits.md), and [Validation & Roadmap](validation-and-roadmap.md).

---

**Renewable Energy Design**  
Engineering · CAD · GPU Computing · Automation
