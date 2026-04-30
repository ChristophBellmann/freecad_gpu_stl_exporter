import os

import FreeCAD
import FreeCADGui


class GpuStlExportWorkbench(Workbench):
    MenuText = "GPU STL Export"
    ToolTip = "Experimental GPU STL export backend for supported FreeCAD shapes"
    Icon = os.path.join(os.path.dirname(__file__), "resources", "gpu_stl_export.svg")

    def Initialize(self):
        from GpuStlExport.command import GpuStlExportCommand
        from GpuStlExport.command import GpuStlExportSetupCommand

        FreeCADGui.addCommand("GpuStlExport_ExportSelection", GpuStlExportCommand())
        FreeCADGui.addCommand("GpuStlExport_SetupVenv", GpuStlExportSetupCommand())

        commands = [
            "GpuStlExport_ExportSelection",
            "GpuStlExport_SetupVenv",
        ]
        self.appendToolbar("GPU STL Export", commands)
        self.appendMenu("GPU STL Export", commands)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(GpuStlExportWorkbench())
