from __future__ import annotations

import os
import tempfile
from pathlib import Path

import FreeCAD
import FreeCADGui

from GpuStlExport.external_exporter import (
    ExportOptions,
    command_as_text,
    resolve_shape_for_object,
    run_export,
    setup_venv,
)

try:
    from PySide import QtCore, QtGui
    QtWidgets = QtGui
except Exception:  # pragma: no cover - FreeCAD version dependent
    from PySide2 import QtCore, QtWidgets


PRESETS = ["draft", "standard", "fine"]
MODES = ["cpu", "cuda", "rocm", "rocm-custom"]


def log(message: str) -> None:
    FreeCAD.Console.PrintMessage(f"[GPU STL Export] {message}\n")


def warn(message: str) -> None:
    FreeCAD.Console.PrintWarning(f"[GPU STL Export] {message}\n")


def error(message: str) -> None:
    FreeCAD.Console.PrintError(f"[GPU STL Export] {message}\n")


def active_doc():
    doc = FreeCAD.ActiveDocument
    if doc is None:
        raise RuntimeError("No active FreeCAD document.")
    return doc


def selected_shape_object():
    selection = FreeCADGui.Selection.getSelectionEx()
    if not selection:
        raise RuntimeError("Select one object with a Shape first.")

    for item in selection:
        obj = item.Object
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            return obj

    raise RuntimeError("The selection does not contain an object with a valid Shape.")


def default_output_for_object(obj) -> str:
    doc = obj.Document
    label = getattr(obj, "Label", None) or getattr(obj, "Name", "selection")
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in label).strip("._")
    filename = f"{safe or 'selection'}_gpu.stl"
    if getattr(doc, "FileName", ""):
        return str(Path(doc.FileName).with_name(filename))
    return str(Path.home() / filename)


class ExportDialog(QtWidgets.QDialog):
    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPU STL Export")
        self.setMinimumWidth(540)
        self._build_ui(obj)

    def _build_ui(self, obj):
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        self.output_edit = QtWidgets.QLineEdit(default_output_for_object(obj))
        browse = QtWidgets.QPushButton("Browse…")
        browse.clicked.connect(self._browse_output)
        output_row = QtWidgets.QHBoxLayout()
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(browse)
        form.addRow("Output STL", output_row)

        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItems(PRESETS)
        self.preset_combo.setCurrentText("fine")
        form.addRow("Preset", self.preset_combo)

        self.samples_spin = QtWidgets.QSpinBox()
        self.samples_spin.setRange(0, 1000000)
        self.samples_spin.setValue(0)
        self.samples_spin.setSpecialValueText("preset")
        form.addRow("Profile samples", self.samples_spin)

        self.segments_spin = QtWidgets.QSpinBox()
        self.segments_spin.setRange(0, 1000000)
        self.segments_spin.setValue(0)
        self.segments_spin.setSpecialValueText("preset")
        form.addRow("Rotation segments", self.segments_spin)

        self.cpu_check = QtWidgets.QCheckBox("Use CPU fallback instead of CUDA/ROCm")
        form.addRow("Backend", self.cpu_check)

        self.import_check = QtWidgets.QCheckBox("Import resulting STL into current document")
        self.import_check.setChecked(True)
        form.addRow("After export", self.import_check)

        self.flip_check = QtWidgets.QCheckBox("Reverse triangle orientation")
        form.addRow("Orientation", self.flip_check)

        self.open_profile_check = QtWidgets.QCheckBox("Do not auto-close profile loops")
        form.addRow("Profile", self.open_profile_check)

        note = QtWidgets.QLabel(
            "This backend currently targets profile/revolve-style FCStd shapes. "
            "Unsupported geometry falls back by cancelling here and using FreeCAD's normal STL export."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export STL",
            self.output_edit.text(),
            "STL files (*.stl);;All files (*)",
        )
        if path:
            self.output_edit.setText(path)

    def options(self) -> tuple[ExportOptions, bool]:
        samples = self.samples_spin.value() or None
        segments = self.segments_spin.value() or None
        return (
            ExportOptions(
                output_path=Path(self.output_edit.text()).expanduser(),
                preset=self.preset_combo.currentText(),
                samples=samples,
                segments=segments,
                cpu=self.cpu_check.isChecked(),
                flip=self.flip_check.isChecked(),
                open_profile=self.open_profile_check.isChecked(),
            ),
            self.import_check.isChecked(),
        )


class GpuStlExportCommand:
    def GetResources(self):
        icon = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "resources",
            "gpu_stl_export.svg",
        )
        return {
            "Pixmap": icon,
            "MenuText": "Export selected Shape with GPU STL backend",
            "ToolTip": "Export the selected FreeCAD object to STL with the experimental PyTorch CUDA/ROCm backend.",
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        try:
            doc = active_doc()
            obj = selected_shape_object()
            doc.recompute()

            dialog = ExportDialog(obj, FreeCADGui.getMainWindow())
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            base_options, import_result = dialog.options()

            with tempfile.TemporaryDirectory(prefix="freecad_gpu_stl_") as tmp:
                tmp_fcstd = Path(tmp) / "selection.FCStd"
                doc.saveCopy(str(tmp_fcstd))
                shape_name = resolve_shape_for_object(
                    tmp_fcstd,
                    object_name=getattr(obj, "Name", None),
                    object_label=getattr(obj, "Label", None),
                )
                options = ExportOptions(
                    output_path=base_options.output_path,
                    shape_name=shape_name,
                    preset=base_options.preset,
                    samples=base_options.samples,
                    segments=base_options.segments,
                    cpu=base_options.cpu,
                    flip=base_options.flip,
                    open_profile=base_options.open_profile,
                )
                result = run_export(tmp_fcstd, options)

            log("command: " + command_as_text(result.command))
            if result.stdout:
                log(result.stdout.rstrip())
            if result.stderr:
                warn(result.stderr.rstrip())

            if result.returncode != 0:
                raise RuntimeError(f"Exporter failed with exit code {result.returncode}.")
            if not result.output_path.exists():
                raise RuntimeError(f"Exporter reported success but no STL was written: {result.output_path}")

            log(f"written: {result.output_path}")

            if import_result:
                import Mesh

                Mesh.insert(str(result.output_path), doc.Name)
                doc.recompute()
                log("imported STL into current document")

        except Exception as exc:
            error(str(exc))
            QtWidgets.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                "GPU STL Export failed",
                str(exc),
            )


class GpuStlExportSetupCommand:
    def GetResources(self):
        icon = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "resources",
            "gpu_stl_export.svg",
        )
        return {
            "Pixmap": icon,
            "MenuText": "Setup GPU exporter virtual environment",
            "ToolTip": "Create the local .venv for CPU, CUDA, ROCm, or custom ROCm PyTorch.",
        }

    def IsActive(self):
        return True

    def Activated(self):
        try:
            mode, ok = QtWidgets.QInputDialog.getItem(
                FreeCADGui.getMainWindow(),
                "Setup GPU STL Exporter",
                "Backend",
                MODES,
                0,
                False,
            )
            if not ok:
                return

            rocm_path = None
            if mode == "rocm-custom":
                rocm_path = QtWidgets.QFileDialog.getExistingDirectory(
                    FreeCADGui.getMainWindow(),
                    "Select custom ROCm directory",
                    "/opt",
                )
                if not rocm_path:
                    return

            result = setup_venv(mode, rocm_path=rocm_path)
            log("command: " + command_as_text(result.command))
            if result.stdout:
                log(result.stdout.rstrip())
            if result.stderr:
                warn(result.stderr.rstrip())
            if result.returncode != 0:
                raise RuntimeError(f"setup_venv.sh failed with exit code {result.returncode}.")

            QtWidgets.QMessageBox.information(
                FreeCADGui.getMainWindow(),
                "GPU STL Exporter",
                "Virtual environment setup completed.",
            )
        except Exception as exc:
            error(str(exc))
            QtWidgets.QMessageBox.critical(
                FreeCADGui.getMainWindow(),
                "GPU STL Export setup failed",
                str(exc),
            )
