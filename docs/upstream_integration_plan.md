# Upstream Integration Plan

## Ziel

GPU-basierte STL-Erzeugung in FreeCAD testen, ohne den stabilen Standard-Mesher zu ersetzen.

## Aktueller Stand

Dieses Repo integriert den vorhandenen PyTorch-basierten Exporter als externes FreeCAD-Workbench-Backend.

Ablauf:

```text
FreeCAD selected object
→ document saveCopy() to temporary FCStd
→ resolve selected *.Shape.brp
→ external export_stl.py subprocess
→ binary STL
→ optional Mesh.insert() back into active document
```

## Warum Addon statt Core-Patch

Ein direkter Core-Patch wäre zu früh, weil der aktuelle GPU-Code ein Spezialfall ist:

- B-spline profile sampling,
- rotational mesh generation,
- no general trimmed-surface meshing,
- no general solid/assembly/topology handling.

FreeCADs normaler Pfad muss beliebige OCCT-BRep-Geometrie behandeln. Deshalb bleibt der Standardexport der Fallback.

## Entwicklungsstufen

### Stufe 1: Externes Addon

Status: umgesetzt.

Eigenschaften:

- keine FreeCAD-Core-Abhängigkeit auf PyTorch,
- lokale `.venv`,
- CPU/CUDA/ROCm Setup,
- GUI Command,
- CLI weiter verfügbar.

### Stufe 2: Optionales MeshPart-Backend

Mögliche spätere API:

```python
MeshPart.meshFromShape(
    Shape=shape,
    LinearDeflection=0.01,
    AngularDeflection=0.5,
    Backend="gpu-revolve",
)
```

Das Backend muss nur aktiv werden, wenn die Shape in den unterstützten Spezialfall fällt. Sonst Standardpfad.

### Stufe 3: C++/Python Bridge ohne FCStd-Zwischendatei

Mögliche Verbesserung:

```text
TopoShape
→ BREP string / profile extraction
→ GPU backend
→ Mesh::MeshObject
```

Damit fällt `doc.saveCopy()` weg. Das ist schneller und sauberer, aber stärker an FreeCAD/OCCT gekoppelt.

### Stufe 4: Genereller GPU-Mesher

Deutlich größeres Projekt:

- Flächenklassifikation,
- NURBS/B-spline sampling,
- Randkurven und Löcher,
- adaptive Tessellierung,
- Toleranzen,
- Normalenorientierung,
- Vergleich gegen OCCT-Referenzmeshes,
- robuste CPU-Fallbacks.

## Empfohlene nächste Tests

1. Addon installieren.
2. Exporter-venv mit `rocm` oder `rocm-custom` einrichten.
3. Ein bekanntes Revolutionsprofil exportieren.
4. STL wieder importieren.
5. Gegen FreeCAD-Standard-STL visuell und quantitativ vergleichen.
6. Erst danach weitere Shape-Typen ergänzen.

## Qualitätschecks

Für jeden Testkörper speichern:

```text
input FCStd
FreeCAD standard STL
GPU STL
preset
samples
segments
triangle count
runtime
visuelle Screenshots
bekannte Abweichungen
```

Sinnvolle spätere Prüfungen:

- Bounding box Vergleich,
- Triangle count Vergleich,
- Normalenorientierung,
- Volumenvergleich,
- Hausdorff-Abstand gegen Referenzmesh.
