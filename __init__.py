bl_info = {
    "name": "KeyHabit",
    "author": "MinThuan",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > KeyHabit",
    "description": "Advanced tools for 3D modeling workflow",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, IntProperty

import importlib
import sys

def safe_import_module(name):
    try:
        if f'{__name__}.{name}' in sys.modules:
            module = sys.modules[f'{__name__}.{name}']
            importlib.reload(module)
        else:
            module = importlib.import_module(f'.{name}', package=__name__)
        return module
    except Exception as e:
        print(f"Cannot import module {name}: {e}")
        return None

def get_display_module():
    return safe_import_module('KHB_Display')

def get_panel_module():
    return safe_import_module('KHB_Panel')

def get_normal_module():
    return safe_import_module('KHB_Normal')

class KHB_AddonPreferences(AddonPreferences):
    bl_idname = __name__
    khb_enable_display_system: BoolProperty(
        name="Enable Display System",
        default=False,
        update=lambda self, ctx: self._khb_update_display_system(ctx)
    )
    khb_display_icon_size: IntProperty(
        name="Icon Size", default=16, min=8, max=64,
        update=lambda self, ctx: self._khb_update_display_settings()
    )
    def _khb_update_display_system(self, ctx):
        display = get_display_module()
        if display is None: return
        if self.khb_enable_display_system:
            display.khb_display_manager.enable()
        else:
            display.khb_display_manager.disable()
    def _khb_update_display_settings(self):
        display = get_display_module()
        if display is None: return
        if hasattr(display, 'KHB_ICON_SIZE_PX'):
            display.KHB_ICON_SIZE_PX = self.khb_display_icon_size
        display.khb_display_manager.force_redraw()
    def draw(self, ctx):
        layout = self.layout
        display = get_display_module()
        col = layout.column()
        col.prop(self, "khb_enable_display_system")
        col.prop(self, "khb_display_icon_size")
        if display is not None:
            col.operator("khb_prefs.reload_icons", text="Reload icons", icon='FILE_REFRESH')
            col.operator("khb_prefs.force_cleanup", text="Force Cleanup", icon='TRASH')

class KHB_PREFS_OT_reload_icons(bpy.types.Operator):
    bl_idname = "khb_prefs.reload_icons"
    bl_label = "Reload Icons"
    bl_options = {'REGISTER'}
    def execute(self, ctx):
        display = get_display_module()
        if display is None:
            self.report({'ERROR'}, "No display module")
            return {'CANCELLED'}
        display.khb_icon_manager.cleanup()
        display.khb_icon_manager.load_icons()
        display.khb_display_manager.force_redraw()
        self.report({'INFO'}, "Icons reloaded")
        return {'FINISHED'}

class KHB_PREFS_OT_force_cleanup(bpy.types.Operator):
    bl_idname = "khb_prefs.force_cleanup"
    bl_label = "Force Cleanup"
    bl_options = {'REGISTER'}
    def execute(self, ctx):
        display = get_display_module()
        if display is not None:
            display.khb_display_manager.disable()
            display.khb_icon_manager.cleanup()
        self.report({'INFO'}, "Force cleanup done")
        return {'FINISHED'}

khb_addon_classes = (
    KHB_AddonPreferences,
    KHB_PREFS_OT_reload_icons,
    KHB_PREFS_OT_force_cleanup,
)

def register():
    for cls in khb_addon_classes:
        bpy.utils.register_class(cls)
    for name in ['KHB_Normal', 'KHB_Panel', 'KHB_Display']:
        mod = safe_import_module(name)
        if mod and hasattr(mod, 'register'):
            mod.register()

def unregister():
    for name in ['KHB_Display', 'KHB_Panel', 'KHB_Normal']:
        mod = safe_import_module(name)
        if mod and hasattr(mod, 'unregister'):
            mod.unregister()
    for cls in reversed(khb_addon_classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
