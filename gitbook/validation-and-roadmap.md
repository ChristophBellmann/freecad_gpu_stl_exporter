# Validation & Roadmap

The next engineering step is quantitative validation rather than simply adding more GPU code.

For each test body, useful comparison data includes:

- input FCStd,
- FreeCAD reference STL,
- GPU-generated STL,
- quality parameters,
- triangle count,
- runtime,
- visual comparison,
- known deviations.

Further checks should include bounding-box comparison, orientation, volume and geometric distance to a reference mesh.

## Development stages

The repository's integration plan describes a progression from the current external add-on toward a possible optional MeshPart backend, then a tighter C++/Python bridge, and only much later a general GPU mesher.

A general solution would require surface classification, NURBS/B-spline handling, trimmed boundaries and holes, adaptive tessellation, tolerance management, normal orientation and robust CPU fallbacks.

The current workbench should therefore be understood as a focused prototype and test platform for those questions.
