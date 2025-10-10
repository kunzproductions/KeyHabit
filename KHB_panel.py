# KHB_Panel.py
import bpy
from bpy.types import Panel
from .KHB_Normal import (
    KEYHABIT_OT_weight_face_area,
    KEYHABIT_OT_weight_corner_angle,
    KEYHABIT_OT_weight_face_area_angle,
    KEYHABIT_OT_split_faces_and_weld,
    KEYHABIT_OT_restore_normals,
    KHB_OT_toggle_split_normals,
)

def get_overlay(context):
    return context.space_data.overlay

class KEYHABIT_PT_locknormal(Panel):
    bl_label = "Lock Normal"
    bl_idname = "KEYHABIT_PT_locknormal"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "KeyHabit"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        in_edit = bool(obj and obj.type == 'MESH' and obj.mode == 'EDIT')
        overlay = context.space_data.overlay

        # Weighted Normal Tools
        box = layout.box()
        box.label(text="Weighted Normal Tools", icon='MOD_NORMALEDIT')
        col = box.column(align=True)
        col.enabled = bool(obj and obj.type == 'MESH')
        col.operator(KEYHABIT_OT_weight_face_area.bl_idname, icon='NORMALS_FACE')
        col.operator(KEYHABIT_OT_weight_corner_angle.bl_idname, icon='NORMALS_VERTEX')
        col.operator(KEYHABIT_OT_weight_face_area_angle.bl_idname, icon='NODE_TEXTURE')

        # Split Normals Display
        box = layout.box()
        box.label(text="Split Normals Display", icon='MOD_NORMALEDIT')
        row = box.row()
        row.enabled = bool(obj and obj.type == 'MESH')
        row.operator('keyhabit.togglesplitnormals', text="Show Split Normals", icon='NORMALS_VERTEX')

        # -------- THÊM SLIDER ----------
        overlay = get_overlay(context)
        # Slider độ dài normals
        row = box.row()
        row.prop(overlay, "normals_length", text="Normals Length")

        # Split Sharp Face
        row = layout.row()
        row.enabled = bool(obj and obj.type == 'MESH')
        row.operator(KEYHABIT_OT_split_faces_and_weld.bl_idname, text="Split Sharp Face", icon='MODIFIER')

        # Data Transfer tools
        box = layout.box()
        box.label(text="Data Transfer", icon='MODIFIER')
        row = box.row(align=True)
        row.enabled = bool(obj and obj.type == 'MESH')
        row.operator("keyhabit.setup_data_transfer", text="Setup", icon='MODIFIER')
        box.label(text="Pick source with eyedropper", icon='EYEDROPPER')

        # Restore tools
        row = layout.row()
        row.enabled = bool(obj and obj.type == 'MESH')
        row.operator(KEYHABIT_OT_restore_normals.bl_idname, icon='RECOVER_LAST')

        if not in_edit:
            layout.label(text="Edit Mode required", icon='INFO')

classes = (KEYHABIT_PT_locknormal,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

__all__ = [
    'KEYHABIT_PT_locknormal',
    'register',
    'unregister',
]
