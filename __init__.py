bl_info = {
    "name": "KeyHabit",
    "author": "Nhen3D, qodo",
    "version": (0, 0, 5),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > KeyHabit",
    "description": "Lock Normal tools, modifier overlay, viewport displays.",
    "category": "3D View",
}

import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty

class KEYHABIT_Preferences(AddonPreferences):
    bl_idname = "KeyHabit"
    show_modifier_overlay: BoolProperty(
        name="Show Modifier Overlay",
        description="Enable modifier information overlay in viewport",
        default=False,
    )
    def draw(self, context):
        layout = self.layout
        layout.label(text="KeyHabit Add-on Settings")
        layout.prop(self, "show_modifier_overlay")

from . import KHB_Normal, KHB_Panel, KHB_Display

def register():
    bpy.utils.register_class(KEYHABIT_Preferences)
    KHB_Normal.register()
    KHB_Panel.register()
    KHB_Display.register()

def unregister():
    KHB_Display.unregister()
    KHB_Panel.unregister()
    KHB_Normal.unregister()
    try:
        bpy.utils.unregister_class(KEYHABIT_Preferences)
    except RuntimeError:
        pass
