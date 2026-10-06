# Supported Geometry & Limits

The project is experimental and intentionally does not present itself as a general STL exporter replacement.

## Current scope

The implemented backend targets profile/revolve-style shapes that satisfy the exporter's assumptions.

## Outside the current scope

The repository explicitly does not claim general support for:

- arbitrary BRep solids,
- complex trimmed surfaces,
- automatic meshing of assemblies containing unrelated bodies,
- complete replacement of OCCT `BRepMesh_IncrementalMesh`.

These boundaries are important. GPU acceleration is only useful if geometric correctness is preserved.

FreeCAD's standard mesher remains the reference and fallback for unsupported geometry.
