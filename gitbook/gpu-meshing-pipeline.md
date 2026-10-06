# GPU Meshing Pipeline

The current backend targets profile/revolve-style geometry.

It extracts and samples B-spline profile information, generates rotational mesh coordinates and writes the result as binary STL. The computational backend is implemented with PyTorch so compatible tensor operations can run on CPU, CUDA or ROCm.

## Quality presets

The repository defines three presets:

| Preset | Profile samples | Rotation segments |
| --- | ---: | ---: |
| draft | 96 | 512 |
| standard | 384 | 4096 |
| fine | 768 | 8192 |

Sample and segment counts can also be overridden manually.

Higher values increase mesh density and computational cost. They do not by themselves guarantee geometric correctness; validation against a trusted reference mesh remains necessary.
