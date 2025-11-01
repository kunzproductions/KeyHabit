import bpy
import bmesh
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty, IntProperty, FloatProperty
from typing import List, Set

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _addon_name() -> str:
    return __package__ or __name__

def get_prefs(context=None):
    context = context or bpy.context
    addon_key = _addon_name()
    try:
        return context.preferences.addons[addon_key].preferences
    except Exception:
        return None

def log(msg: str):
    prefs = get_prefs()
    if getattr(prefs, "debug_logging", False):
        print(f"[KeyHabit] {msg}")

def _ensure_vgroup(obj: bpy.types.Object, name: str) -> bpy.types.VertexGroup:
    vg = obj.vertex_groups.get(name)
    if vg is None:
        vg = obj.vertex_groups.new(name=name)
        log(f"Created vertex group: {name}")
    return vg

def _get_selected_vertices(context) -> List[int]:
    """Lấy tất cả vertices từ selection hiện tại (vertex/edge/face)"""
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    sel: Set[int] = set()
    sel_mode = context.tool_settings.mesh_select_mode
    
    if sel_mode[0]:  # vertex select
        sel.update(v.index for v in bm.verts if v.select)
    if sel_mode[1]:  # edge select
        sel.update(v.index for e in bm.edges if e.select for v in e.verts)
    if sel_mode[2]:  # face select
        sel.update(v.index for f in bm.faces if f.select for v in f.verts)
    
    return sorted(sel)

def _get_face_vertices(context) -> List[int]:
    """Lấy vertices từ selected faces"""
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    sel = set()
    for f in bm.faces:
        if f.select:
            sel.update(v.index for v in f.verts)
    
    return sorted(sel)

def _co_key(vec) -> tuple:
    """Round coordinates để tránh float equality issues"""
    try:
        return (round(vec.x, 6), round(vec.y, 6), round(vec.z, 6))
    except Exception:
        return (round(vec[0], 6), round(vec[1], 6), round(vec[2], 6))

def _safe_set_attr(obj, attr_name: str, value, fallback=None):
    """Safely set attribute với fallback"""
    try:
        setattr(obj, attr_name, value)
        return True
    except Exception as e:
        log(f"Failed to set {attr_name}: {e}")
        if fallback is not None:
            try:
                setattr(obj, attr_name, fallback)
                return True
            except Exception:
                pass
        return False

def _ensure_weighted_normal_modifier(obj: bpy.types.Object, mod_name: str, mode: str, vgroup_name: str):
    """Tạo hoặc cập nhật Weighted Normal modifier"""
    mod = obj.modifiers.get(mod_name)
    if mod is None:
        mod = obj.modifiers.new(name=mod_name, type='WEIGHTED_NORMAL')
        log(f"Created Weighted Normal modifier: {mod_name} mode={mode}")
    
    # Set properties với fallback
    _safe_set_attr(mod, "mode", mode)
    _safe_set_attr(mod, "weight", int(100))
    _safe_set_attr(mod, "keep_sharp", True)
    _safe_set_attr(mod, "show_viewport", True)
    _safe_set_attr(mod, "show_in_editmode", True)
    _safe_set_attr(mod, "show_on_cage", True)
    _safe_set_attr(mod, "vertex_group", vgroup_name)

def _move_vertices_between_groups(obj, vertex_indices: List[int], from_groups: List[str], to_group: str):
    """Di chuyển vertices giữa các groups"""
    moved = 0
    added_new = 0
    
    target_vg = _ensure_vgroup(obj, to_group)
    
    for vidx in vertex_indices:
        in_other = False
        in_target_before = False
        
        # Remove from other groups
        for group_name in from_groups:
            other_vg = obj.vertex_groups.get(group_name)
            if other_vg:
                try:
                    other_vg.weight(vidx)
                    other_vg.remove([vidx])
                    in_other = True
                except RuntimeError:
                    pass
        
        # Check if already in target
        try:
            target_vg.weight(vidx)
            in_target_before = True
        except RuntimeError:
            pass
        
        if in_other:
            moved += 1
        if not in_target_before and not in_other:
            added_new += 1
        
        target_vg.add([vidx], 1.0, 'REPLACE')
    
    return moved, added_new

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class KHB_OT_toggle_split_normals(Operator):
    bl_idname = "keyhabit.toggle_split_normals"
    bl_label = "Toggle Split Normals"
    bl_description = "Toggle display of split normals"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        overlay = context.space_data.overlay
        overlay.show_split_normals = not overlay.show_split_normals
        status = "ON" if overlay.show_split_normals else "OFF"
        self.report({'INFO'}, f"Split Normals Display: {status}")
        return {'FINISHED'}

class KEYHABIT_OT_weight_face_area(Operator):
    bl_idname = "keyhabit.weight_face_area"
    bl_label = "Weight Face Area"
    bl_description = "Assign selected vertices to KHB_FaceArea group and ensure a Weighted Normal modifier (Face Area) uses it"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'
    
    def execute(self, context):
        obj = context.active_object
        sel_indices = _get_selected_vertices(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No vertices from selection (vertex/edge/face) to process")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        moved, added_new = _move_vertices_between_groups(
            obj, sel_indices, ['KHB_CornerAngle'], 'KHB_FaceArea'
        )
        
        _ensure_weighted_normal_modifier(obj, 'KHB_FaceArea', 'FACE_AREA', 'KHB_FaceArea')
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Report message
        if moved > 0 and added_new > 0:
            msg = f"-{moved} vertex KHB_CornerAngle > KHB_FaceArea | +{added_new} vertex"
        elif moved > 0:
            msg = f"-{moved} vertex KHB_CornerAngle > KHB_FaceArea"
        elif added_new > 0:
            msg = f"+{added_new} vertex > KHB_FaceArea"
        else:
            msg = "vertex already exists in KHB_FaceArea"
        
        self.report({'WARNING'} if moved > 0 else {'INFO'}, msg)
        return {'FINISHED'}

class KEYHABIT_OT_weight_corner_angle(Operator):
    bl_idname = "keyhabit.weight_corner_angle"
    bl_label = "Weight Corner Angle"
    bl_description = "Assign selected vertices to KHB_CornerAngle group and ensure a Weighted Normal modifier (Corner Angle) uses it"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'
    
    def execute(self, context):
        obj = context.active_object
        sel_indices = _get_selected_vertices(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No vertices from selection (vertex/edge/face) to process")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        moved, added_new = _move_vertices_between_groups(
            obj, sel_indices, ['KHB_FaceArea'], 'KHB_CornerAngle'
        )
        
        _ensure_weighted_normal_modifier(obj, 'KHB_CornerAngle', 'CORNER_ANGLE', 'KHB_CornerAngle')
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Report message
        if moved > 0 and added_new > 0:
            msg = f"-{moved} vertex KHB_FaceArea > KHB_CornerAngle | +{added_new} vertex"
        elif moved > 0:
            msg = f"-{moved} vertex KHB_FaceArea > KHB_CornerAngle"
        elif added_new > 0:
            msg = f"+{added_new} vertex > KHB_CornerAngle"
        else:
            msg = "vertex already exists in KHB_CornerAngle"
        
        self.report({'WARNING'} if moved > 0 else {'INFO'}, msg)
        return {'FINISHED'}

class KEYHABIT_OT_weight_face_area_angle(Operator):
    bl_idname = "keyhabit.weight_face_area_angle"
    bl_label = "Weight Face Area + Angle"
    bl_description = "Assign selected vertices to KHB_FaceAreaAngle group and ensure Weighted Normal modifier (Face Area + Angle) uses it"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'
    
    def execute(self, context):
        obj = context.active_object
        sel_indices = _get_selected_vertices(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No vertices from selection (vertex/edge/face) to process")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        moved, added_new = _move_vertices_between_groups(
            obj, sel_indices, ['KHB_FaceArea', 'KHB_CornerAngle'], 'KHB_FaceAreaAngle'
        )
        
        _ensure_weighted_normal_modifier(obj, 'KHB_FaceAreaAngle', 'FACE_AREA_WITH_ANGLE', 'KHB_FaceAreaAngle')
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        msg = f"Removed from FaceArea/CornerAngle, added {added_new} new vertices to KHB_FaceAreaAngle"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

class KEYHABIT_OT_setup_data_transfer(Operator):
    bl_idname = "keyhabit.setup_data_transfer"
    bl_label = "Setup Data Transfer"
    bl_description = "Create KHB_Data_XX vertex group from selection and configure a Data Transfer modifier"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'
    
    def execute(self, context):
        obj = context.active_object
        sel_indices = _get_selected_vertices(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No selection to build Data Transfer group")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Find next available suffix
        suffix = 1
        while suffix < 100 and obj.vertex_groups.get(f"KHB_Data_{suffix:02d}") is not None:
            suffix += 1
        
        vg_name = f"KHB_Data_{suffix:02d}"
        mod_name = f"KHB_DataTransfer_{suffix:02d}"
        
        # Create vertex group
        vg = _ensure_vgroup(obj, vg_name)
        vg.add(sel_indices, 1.0, 'REPLACE')
        
        # Create or update Data Transfer modifier
        mod = obj.modifiers.get(mod_name)
        if mod is None:
            mod = obj.modifiers.new(name=mod_name, type='DATA_TRANSFER')
        
        # Configure modifier
        _safe_set_attr(mod, "use_loop_data", True)
        _safe_set_attr(mod, "data_types_loops", {'CUSTOM_NORMAL'})
        _safe_set_attr(mod, "loop_mapping", 'POLYINTERP_NEAREST')
        _safe_set_attr(mod, "vertex_group", vg_name)
        _safe_set_attr(mod, "show_viewport", True)
        _safe_set_attr(mod, "show_in_editmode", True)
        _safe_set_attr(mod, "show_on_cage", True)
        _safe_set_attr(mod, "object", None)
        
        # Activate modifier
        try:
            idx = list(obj.modifiers).index(mod)
            obj.modifiers.active_index = idx
            mod.show_expanded = True
        except Exception:
            pass
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        self.report({'INFO'}, f"Created: VG={vg_name}, MOD={mod_name}")
        return {'FINISHED'}

class KEYHABIT_OT_split_faces_and_weld(Operator):
    bl_idname = "keyhabit.split_faces_and_weld"
    bl_label = "Split Sharp Face"
    bl_description = "Split selected faces, remove their vertices from Data Transfer's vertex group(s), and ensure KBH_Weld after Data Transfer"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'
    
    def execute(self, context):
        obj = context.active_object
        face_sel_indices_before = _get_face_vertices(context)
        
        if not face_sel_indices_before:
            self.report({'WARNING'}, "No selected faces to split")
            return {'CANCELLED'}
        
        # Identify boundary vertices BEFORE split
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        
        boundary_keys = set()
        for v in bm.verts:
            if v.select and any((not f.select) for f in v.link_faces):
                boundary_keys.add(_co_key(v.co))
        
        # Split selected faces
        try:
            bpy.ops.mesh.split()
        except Exception as e:
            self.report({'ERROR'}, f"Split failed: {e}")
            return {'CANCELLED'}
        
        # Get boundary vertices after split
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        boundary_all_indices = [v.index for v in bm.verts if _co_key(v.co) in boundary_keys]
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Create boundary vertex group
        boundary_vg_name = 'KHB_WeldBoundarySharpFace'
        vg_boundary = _ensure_vgroup(obj, boundary_vg_name)
        if boundary_all_indices:
            vg_boundary.add(boundary_all_indices, 1.0, 'REPLACE')
        
        # Remove vertices from Data Transfer groups
        removed_vertices_total = 0
        affected_groups = 0
        idx_set = set(face_sel_indices_before)
        
        dt_mods = [m for m in obj.modifiers if m.type == 'DATA_TRANSFER']
        dt_vgroups = list(set(getattr(m, 'vertex_group', '') for m in dt_mods if getattr(m, 'vertex_group', '')))
        
        for name in dt_vgroups:
            vg = obj.vertex_groups.get(name)
            if not vg:
                continue
            
            removed_here = sum(1 for vidx in idx_set if _has_vertex_weight(vg, vidx))
            
            if removed_here > 0:
                affected_groups += 1
                try:
                    vg.remove(list(idx_set))
                except Exception:
                    for vidx in idx_set:
                        try:
                            vg.remove([vidx])
                        except Exception:
                            pass
                removed_vertices_total += removed_here
        
        # Ensure Weld modifier
        weld = obj.modifiers.get('KBH_Weld')
        if weld is None:
            weld = obj.modifiers.new(name='KBH_Weld', type='WELD')
            _safe_set_attr(weld, "merge_threshold", 0.0001)
            _safe_set_attr(weld, "show_viewport", True)
            _safe_set_attr(weld, "show_in_editmode", True)
            _safe_set_attr(weld, "show_on_cage", True)
        else:
            _safe_set_attr(weld, "show_viewport", True)
            _safe_set_attr(weld, "show_in_editmode", True)
            _safe_set_attr(weld, "show_on_cage", True)
        
        _safe_set_attr(weld, "vertex_group", boundary_vg_name)
        
        # Reorder weld after last Data Transfer
        try:
            dt_indices = [i for i, m in enumerate(obj.modifiers) if m.type == 'DATA_TRANSFER']
            if dt_indices:
                target_index = min(max(dt_indices) + 1, len(obj.modifiers) - 1)
                bpy.ops.object.modifier_move_to_index(modifier=weld.name, index=target_index)
        except Exception as e:
            log(f"Failed to reorder KBH_Weld: {e}")
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Report message
        msg_parts = ["Split faces"]
        if boundary_all_indices:
            msg_parts.append(f"boundary {len(boundary_all_indices)} -> {boundary_vg_name}")
        if affected_groups:
            msg_parts.append(f"removed {removed_vertices_total} vtx from {affected_groups} group(s)")
        msg_parts.append("Weld after DataTransfer" if dt_mods else "Weld added")
        
        self.report({'INFO'}, " | ".join(msg_parts))
        return {'FINISHED'}

def _has_vertex_weight(vg, vidx):
    """Check if vertex has weight in group"""
    try:
        vg.weight(vidx)
        return True
    except RuntimeError:
        return False

class KEYHABIT_OT_restore_normals(Operator):
    bl_idname = "keyhabit.restore_normals"
    bl_label = "Restore Normals"
    bl_description = "Delete KHB groups/modifiers, shade smooth, and average normals"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object is not a mesh")
            return {'CANCELLED'}
        
        original_mode = getattr(obj, 'mode', 'OBJECT')
        
        # Switch to OBJECT mode
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        
        # Remove KHB vertex groups and modifiers
        removed_groups = 0
        removed_mods = 0
        
        for name in ('KHB_FaceArea', 'KHB_CornerAngle', 'KHB_FaceAreaAngle'):
            # Remove vertex group
            vg = obj.vertex_groups.get(name)
            if vg:
                try:
                    obj.vertex_groups.remove(vg)
                    removed_groups += 1
                except Exception as e:
                    log(f"Failed to remove vertex group {name}: {e}")
            
            # Remove modifier
            mod = obj.modifiers.get(name)
            if mod:
                try:
                    obj.modifiers.remove(mod)
                    removed_mods += 1
                except Exception as e:
                    log(f"Failed to remove modifier {name}: {e}")
        
        # Shade Smooth
        shade_ok = False
        try:
            bpy.ops.object.shade_smooth(keep_sharp_edges=True)
            shade_ok = True
        except Exception:
            try:
                bpy.ops.object.shade_smooth()
                shade_ok = True
            except Exception:
                pass
        
        # Average Normals
        avg_ok = False
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            try:
                bpy.ops.mesh.select_all(action='SELECT')
            except Exception:
                pass
            bpy.ops.mesh.average_normals(average_type='CORNER_ANGLE', weight=50, threshold=0.01)
            avg_ok = True
        except Exception as e:
            log(f"average_normals failed: {e}")
        finally:
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except Exception:
                pass
        
        # Report
        parts = []
        if removed_groups:
            parts.append(f"removed {removed_groups} group(s)")
        if removed_mods:
            parts.append(f"removed {removed_mods} modifier(s)")
        if shade_ok:
            parts.append("shade smooth")
        if avg_ok:
            parts.append("average normals")
        if not parts:
            parts.append("no changes")
        
        self.report({'INFO'}, " | ".join(parts))
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Panel
# -----------------------------------------------------------------------------

class KEYHABIT_PT_locknormal(Panel):
    bl_label = "Lock Normal"
    bl_idname = "KEYHABIT_PT_locknormal"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "KeyHabit"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        in_edit = bool(obj and obj.type == 'MESH' and obj.mode == 'EDIT')
        in_sculpt = bool(obj and obj.type == 'MESH' and obj.mode == 'SCULPT')

        # Weighted Normal Tools
        box = layout.box()
        box.label(text="Weighted Normal Tools", icon='MOD_NORMALEDIT')
        col = box.column(align=True)
        col.enabled = bool(obj and obj.type == 'MESH')
        col.operator(KEYHABIT_OT_weight_face_area.bl_idname, icon='NORMALS_FACE')
        col.operator(KEYHABIT_OT_weight_corner_angle.bl_idname, icon='NORMALS_VERTEX')
        col.operator(KEYHABIT_OT_weight_face_area_angle.bl_idname, icon='NODE_TEXTURE')

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

        if not in_edit and not in_sculpt:
            layout.label(text="Edit Mode or Sculpt Mode required", icon='INFO')

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

classes = (
    KHB_OT_toggle_split_normals,
    KEYHABIT_OT_weight_face_area,
    KEYHABIT_OT_weight_corner_angle,
    KEYHABIT_OT_weight_face_area_angle,
    KEYHABIT_OT_setup_data_transfer,
    KEYHABIT_OT_split_faces_and_weld,
    KEYHABIT_OT_restore_normals,
    KEYHABIT_PT_locknormal,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    log("KHB_Normal registered")

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            log(f"Error unregistering {cls}: {e}")
    log("KHB_Normal unregistered")

# Public symbols for other modules
__all__ = [
    'KHB_OT_toggle_split_normals',
    'KEYHABIT_OT_weight_face_area',
    'KEYHABIT_OT_weight_corner_angle', 
    'KEYHABIT_OT_weight_face_area_angle',
    'KEYHABIT_OT_setup_data_transfer',
    'KEYHABIT_OT_split_faces_and_weld',
    'KEYHABIT_OT_restore_normals',
    'KEYHABIT_PT_locknormal',
    'register',
    'unregister',
]