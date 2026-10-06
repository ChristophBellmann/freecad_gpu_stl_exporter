# FreeCAD Integration

The project is packaged as a FreeCAD workbench named **GPU STL Export**.

From the GUI, a user can select an object with a valid Shape, invoke the GPU export command, choose an output location and quality preset, and optionally import the generated STL back into the active document for inspection.

## Why an add-on

The current GPU code handles a specialized geometry class. FreeCAD's standard meshing path must support substantially broader OCCT BRep geometry.

Keeping the implementation as an add-on therefore provides:

- isolation from FreeCAD core,
- an explicit fallback boundary,
- easier experimentation with PyTorch versions and GPU stacks,
- a path for validation before proposing deeper integration.

A possible future stage would expose the specialized backend through a MeshPart-style API only when a shape matches the supported case.
