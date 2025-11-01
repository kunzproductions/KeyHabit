"""
KHB_BakeSet - KeyHabit Bake Set Creator for Substance Painter
Creates and manages bake sets with automatic naming and collection organization
"""

import bpy
from bpy.types import Operator, Panel
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy_extras.io_utils import ExportHelper


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def ensure_collection(collection_name, parent_collection=None):
    """Đảm bảo collection tồn tại, tạo mới nếu chưa có"""
    if parent_collection:
        collection = parent_collection.children.get(collection_name)
    else:
        collection = bpy.data.collections.get(collection_name)
    
    if collection is None:
        collection = bpy.data.collections.new(collection_name)
        if parent_collection:
            parent_collection.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)
    
    return collection


def move_object_to_collection(obj, target_collection):
    """Di chuyển object sang collection mới"""
    for col in obj.users_collection:
        col.objects.unlink(obj)
    target_collection.objects.link(obj)


def get_next_number(base_name, existing_names):
    """Tìm số thứ tự tiếp theo"""
    number = 1
    while f"{base_name}_{number:03d}" in existing_names:
        number += 1
    return number


def get_next_bakeset_number():
    """Tìm số thứ tự tiếp theo cho BakeSet"""
    bakeset_collection = bpy.data.collections.get("KHB_BakeSet")
    if not bakeset_collection:
        return 1
    
    existing_numbers = []
    for col in bakeset_collection.children:
        if col.name.startswith("KHB_BakeSet_"):
            try:
                num_str = col.name.split("_")[2]
                existing_numbers.append(int(num_str))
            except (IndexError, ValueError):
                continue
    
    number = 1
    while number in existing_numbers:
        number += 1
    return number


def collect_objects_by_suffix(collection, suffix):
    """Thu thập objects theo suffix từ collection và sub-collections"""
    objects = []
    def _collect(col):
        for obj in col.objects:
            if obj.name.endswith(suffix):
                objects.append(obj)
        for child_col in col.children:
            _collect(child_col)
    _collect(collection)
    return objects


def apply_subsurf_modifiers(context, objects):
    """Apply Subdivision Surface modifiers"""
    for obj in objects:
        if obj.type == 'MESH':
            context.view_layer.objects.active = obj
            for mod in list(obj.modifiers):
                if mod.type == 'SUBSURF':
                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    except Exception as e:
                        print(f"[KHB] Warning: Could not apply modifier on '{obj.name}': {e}")


def apply_modifiers(obj):
    """Apply tất cả modifiers trừ Subdivision Surface (xóa)"""
    if obj.type != 'MESH':
        return
    
    for mod in list(obj.modifiers):
        if mod.type == 'SUBSURF':
            obj.modifiers.remove(mod)
        else:
            try:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except Exception:
                pass


def process_objects_modifiers(context, objects):
    """Apply/delete modifiers cho tất cả objects"""
    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    for obj in objects:
        if obj.type == 'MESH' and obj.modifiers:
            apply_modifiers(obj)


def join_objects(context, objects_to_join, new_name):
    """Join nhiều objects thành 1 object"""
    if not objects_to_join:
        return None
    
    if len(objects_to_join) == 1:
        objects_to_join[0].name = new_name
        return objects_to_join[0]
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects_to_join:
        obj.select_set(True)
    context.view_layer.objects.active = objects_to_join[0]
    bpy.ops.object.join()
    
    joined_obj = context.active_object
    joined_obj.name = new_name
    return joined_obj


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class KHB_OT_OptimalHighPolyObjects(Operator):
    """Rename selected objects as highpoly and move to BakeSet collection"""
    bl_idname = "khb.optimal_highpoly_objects"
    bl_label = "Optimal Highpoly Objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    base_name: StringProperty(default="KHB_pathHigh")
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects
    
    def execute(self, context):
        selected_objects = context.selected_objects.copy()
        if not selected_objects:
            return {'CANCELLED'}
        
        bakeset_collection = ensure_collection("KHB_BakeSet")
        bakeset_wip_collection = ensure_collection("KHB_BakeSet_Wip", bakeset_collection)
        existing_names = {obj.name for obj in bakeset_wip_collection.objects}
        
        for obj in selected_objects:
            number = get_next_number(self.base_name, existing_names)
            obj.name = f"{self.base_name}_{number:03d}"
            existing_names.add(obj.name)
            move_object_to_collection(obj, bakeset_wip_collection)
        
        self.report({'INFO'}, f"Processed {len(selected_objects)} object(s) as highpoly mesh")
        return {'FINISHED'}


class KHB_OT_CreateBakeSet(Operator):
    """Join selected highpoly and lowpoly objects into a bake set"""
    bl_idname = "khb.create_bakeset"
    bl_label = "Create Bake Set"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
        has_highpoly = any(obj.type == 'MESH' and obj.name.startswith("KHB_pathHigh_") for obj in context.selected_objects)
        has_lowpoly = any(obj.type == 'MESH' and not obj.name.startswith("KHB_pathHigh_") for obj in context.selected_objects)
        return has_highpoly and has_lowpoly
    
    def execute(self, context):
        selected_objects = context.selected_objects.copy()
        
        highpoly_objects = [obj for obj in selected_objects if obj.type == 'MESH' and obj.name.startswith("KHB_pathHigh_")]
        lowpoly_objects = [obj for obj in selected_objects if obj.type == 'MESH' and not obj.name.startswith("KHB_pathHigh_")]
        
        if not highpoly_objects or not lowpoly_objects:
            self.report({'WARNING'}, "Need both highpoly (KHB_pathHigh_xxx) and lowpoly objects")
            return {'CANCELLED'}
        
        bakeset_number = get_next_bakeset_number()
        bakeset_name = f"KHB_BakeSet_{bakeset_number:03d}"
        
        bakeset_parent = ensure_collection("KHB_BakeSet")
        bakeset_collection = ensure_collection(bakeset_name, bakeset_parent)
        
        # Apply/Delete modifiers
        process_objects_modifiers(context, highpoly_objects + lowpoly_objects)
        
        # Join objects
        high_obj = join_objects(context, highpoly_objects, f"{bakeset_name}_High")
        if high_obj:
            move_object_to_collection(high_obj, bakeset_collection)
        
        low_obj = join_objects(context, lowpoly_objects, f"{bakeset_name}_Low")
        if low_obj:
            move_object_to_collection(low_obj, bakeset_collection)
        
        self.report({'INFO'}, f"Created BakeSet '{bakeset_name}'")
        return {'FINISHED'}


class KHB_OT_ToggleHighpoly(Operator):
    """Toggle visibility of all highpoly objects"""
    bl_idname = "khb.toggle_highpoly"
    bl_label = "Toggle Highpoly"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bakeset_collection = bpy.data.collections.get("KHB_BakeSet")
        if not bakeset_collection:
            self.report({'WARNING'}, "KHB_BakeSet collection not found")
            return {'CANCELLED'}
        
        highpoly_objects = collect_objects_by_suffix(bakeset_collection, "_High")
        if not highpoly_objects:
            return {'FINISHED'}
        
        any_visible = any(not obj.hide_viewport for obj in highpoly_objects)
        for obj in highpoly_objects:
            obj.hide_viewport = any_visible
            obj.hide_render = any_visible
        
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class KHB_OT_ToggleLowpoly(Operator):
    """Toggle visibility of all lowpoly objects"""
    bl_idname = "khb.toggle_lowpoly"
    bl_label = "Toggle Lowpoly"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bakeset_collection = bpy.data.collections.get("KHB_BakeSet")
        if not bakeset_collection:
            self.report({'WARNING'}, "KHB_BakeSet collection not found")
            return {'CANCELLED'}
        
        lowpoly_objects = collect_objects_by_suffix(bakeset_collection, "_Low")
        if not lowpoly_objects:
            return {'FINISHED'}
        
        any_visible = any(not obj.hide_viewport for obj in lowpoly_objects)
        for obj in lowpoly_objects:
            obj.hide_viewport = any_visible
            obj.hide_render = any_visible
        
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class KHB_OT_ExportLowpoly(Operator, ExportHelper):
    """Export all lowpoly objects to FBX"""
    bl_idname = "khb.export_lowpoly"
    bl_label = "Export Lowpoly"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    
    apply_modifiers: BoolProperty(name="Apply Modifiers", default=True)
    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        items=(('OFF', "Normals Only", ""), ('FACE', "Face", ""), ('EDGE', "Edge", "")),
        default='FACE'
    )
    use_subsurf: BoolProperty(name="Export Subdivision Surface", default=False)
    use_mesh_edges: BoolProperty(name="Loose Edges", default=False)
    use_tspace: BoolProperty(name="Tangent Space", default=True)
    use_triangulate: BoolProperty(name="Triangulate Faces", default=False)
    use_vertex_colors: BoolProperty(name="Vertex Colors", default=True)
    global_scale: FloatProperty(name="Scale", min=0.001, max=1000.0, default=1.0)
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Geometry", icon='MESH_DATA')
        col = box.column(align=True)
        col.prop(self, "apply_modifiers")
        col.prop(self, "use_subsurf")
        col.prop(self, "use_mesh_edges")
        col.prop(self, "use_tspace")
        col.prop(self, "use_triangulate")
        col.prop(self, "use_vertex_colors")
        col.separator()
        col.prop(self, "mesh_smooth_type")
        col.prop(self, "global_scale")
    
    def execute(self, context):
        bakeset_collection = bpy.data.collections.get("KHB_BakeSet")
        if not bakeset_collection:
            self.report({'WARNING'}, "KHB_BakeSet collection not found")
            return {'CANCELLED'}
        
        lowpoly_objects = collect_objects_by_suffix(bakeset_collection, "_Low")
        if not lowpoly_objects:
            self.report({'WARNING'}, "No lowpoly objects found")
            return {'CANCELLED'}
        
        if not self.use_subsurf:
            apply_subsurf_modifiers(context, lowpoly_objects)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in lowpoly_objects:
            obj.select_set(True)
        
        try:
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
                apply_scale_options='FBX_SCALE_ALL',
                axis_forward='-Z',
                axis_up='Y',
                use_mesh_modifiers=self.apply_modifiers,
                use_mesh_modifiers_render=self.apply_modifiers,
                mesh_smooth_type=self.mesh_smooth_type,
                use_subsurf=self.use_subsurf,
                use_mesh_edges=self.use_mesh_edges,
                use_tspace=self.use_tspace,
                use_triangles=self.use_triangulate,
                colors_type='SRGB' if self.use_vertex_colors else 'NONE',
                global_scale=self.global_scale,
            )
            self.report({'INFO'}, f"Exported {len(lowpoly_objects)} lowpoly object(s)")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


class KHB_OT_ExportHighpoly(Operator, ExportHelper):
    """Export all highpoly objects to FBX"""
    bl_idname = "khb.export_highpoly"
    bl_label = "Export Highpoly"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    
    apply_modifiers: BoolProperty(name="Apply Modifiers", default=True)
    mesh_smooth_type: EnumProperty(
        name="Smoothing",
        items=(('OFF', "Normals Only", ""), ('FACE', "Face", ""), ('EDGE', "Edge", "")),
        default='FACE'
    )
    use_subsurf: BoolProperty(name="Export Subdivision Surface", default=False)
    use_mesh_edges: BoolProperty(name="Loose Edges", default=False)
    use_tspace: BoolProperty(name="Tangent Space", default=True)
    use_triangulate: BoolProperty(name="Triangulate Faces", default=False)
    use_vertex_colors: BoolProperty(name="Vertex Colors", default=True)
    global_scale: FloatProperty(name="Scale", min=0.001, max=1000.0, default=1.0)
    
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Geometry", icon='MESH_DATA')
        col = box.column(align=True)
        col.prop(self, "apply_modifiers")
        col.prop(self, "use_subsurf")
        col.prop(self, "use_mesh_edges")
        col.prop(self, "use_tspace")
        col.prop(self, "use_triangulate")
        col.prop(self, "use_vertex_colors")
        col.separator()
        col.prop(self, "mesh_smooth_type")
        col.prop(self, "global_scale")
    
    def execute(self, context):
        bakeset_collection = bpy.data.collections.get("KHB_BakeSet")
        if not bakeset_collection:
            self.report({'WARNING'}, "KHB_BakeSet collection not found")
            return {'CANCELLED'}
        
        highpoly_objects = collect_objects_by_suffix(bakeset_collection, "_High")
        if not highpoly_objects:
            self.report({'WARNING'}, "No highpoly objects found")
            return {'CANCELLED'}
        
        if not self.use_subsurf:
            apply_subsurf_modifiers(context, highpoly_objects)
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in highpoly_objects:
            obj.select_set(True)
        
        try:
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
                apply_scale_options='FBX_SCALE_ALL',
                axis_forward='-Z',
                axis_up='Y',
                use_mesh_modifiers=self.apply_modifiers,
                use_mesh_modifiers_render=self.apply_modifiers,
                mesh_smooth_type=self.mesh_smooth_type,
                use_subsurf=self.use_subsurf,
                use_mesh_edges=self.use_mesh_edges,
                use_tspace=self.use_tspace,
                use_triangles=self.use_triangulate,
                colors_type='SRGB' if self.use_vertex_colors else 'NONE',
                global_scale=self.global_scale,
            )
            self.report({'INFO'}, f"Exported {len(highpoly_objects)} highpoly object(s)")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# UI Panel
# -----------------------------------------------------------------------------

class KHB_PT_BakeSetPanel(Panel):
    """KeyHabit Bake Set Creator Panel"""
    bl_label = "KHB Bake Set"
    bl_idname = "KHB_PT_bakeset"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'KeyHabit'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Step 1: Prepare Highpoly
        box = layout.box()
        box.label(text="Step 1: Prepare Highpoly", icon='MESH_ICOSPHERE')
        selected_count = len(context.selected_objects)
        if selected_count > 0:
            box.label(text=f"Selected: {selected_count} object(s)", icon='INFO')
        row = box.row()
        row.scale_y = 1.5
        row.operator("khb.optimal_highpoly_objects", icon='MODIFIER')
        
        # Step 2: Create BakeSet
        box = layout.box()
        box.label(text="Step 2: Create BakeSet", icon='RENDERLAYERS')
        highpoly_count = sum(1 for obj in context.selected_objects if obj.type == 'MESH' and obj.name.startswith("KHB_pathHigh_"))
        lowpoly_count = sum(1 for obj in context.selected_objects if obj.type == 'MESH' and not obj.name.startswith("KHB_pathHigh_"))
        
        if selected_count > 0:
            col = box.column(align=True)
            if highpoly_count > 0:
                col.label(text=f"• Highpoly: {highpoly_count}", icon='MESH_CUBE')
            if lowpoly_count > 0:
                col.label(text=f"• Lowpoly: {lowpoly_count}", icon='MESH_PLANE')
        
        row = box.row()
        row.scale_y = 1.5
        row.operator("khb.create_bakeset", icon='ADD')
        
        # Visibility Control
        box = layout.box()
        bakeset_col = bpy.data.collections.get("KHB_BakeSet")
        high_visible = False
        low_visible = False
        
        if bakeset_col:
            high_objs = collect_objects_by_suffix(bakeset_col, "_High")
            low_objs = collect_objects_by_suffix(bakeset_col, "_Low")
            high_visible = any(not obj.hide_viewport for obj in high_objs)
            low_visible = any(not obj.hide_viewport for obj in low_objs)
        
        row = box.row(align=True)
        col = row.column(align=True)
        col.scale_y = 1.3
        col.operator("khb.toggle_highpoly", text="Highpoly", 
                     icon='HIDE_OFF' if high_visible else 'HIDE_ON', depress=high_visible)
        col = row.column(align=True)
        col.scale_y = 1.3
        col.operator("khb.toggle_lowpoly", text="Lowpoly",
                     icon='HIDE_OFF' if low_visible else 'HIDE_ON', depress=low_visible)
        
        # Export
        box = layout.box()
        high_count = low_count = 0
        if bakeset_col:
            high_count = len(collect_objects_by_suffix(bakeset_col, "_High"))
            low_count = len(collect_objects_by_suffix(bakeset_col, "_Low"))
        
        row = box.row(align=True)
        col = row.column(align=True)
        col.scale_y = 1.3
        col.enabled = low_count > 0
        col.operator("khb.export_lowpoly", text="Export Lowpoly", icon='EXPORT')
        col = row.column(align=True)
        col.scale_y = 1.3
        col.enabled = high_count > 0
        col.operator("khb.export_highpoly", text="Export Highpoly", icon='EXPORT')


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

classes = (
    KHB_OT_OptimalHighPolyObjects,
    KHB_OT_CreateBakeSet,
    KHB_OT_ToggleHighpoly,
    KHB_OT_ToggleLowpoly,
    KHB_OT_ExportLowpoly,
    KHB_OT_ExportHighpoly,
    KHB_PT_BakeSetPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

