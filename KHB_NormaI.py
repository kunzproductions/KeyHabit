import bpy
import bmesh
from bpy.types import Operator
from bpy.props import BoolProperty, StringProperty, IntProperty, FloatProperty
from typing import List, Set

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _addon_name() -> str:
    # In a packaged add-on, __package__ resolves to the top-level folder (e.g., 'KeyHabit')
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

def _selected_vertex_indices_in_edit_mode(context) -> List[int]:
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    sel_mode = context.tool_settings.mesh_select_mode  # (v, e, f)
    sel: Set[int] = set()
    
    if sel_mode[0]:  # vertex select
        for v in bm.verts:
            if v.select:
                sel.add(v.index)
    
    if sel_mode[1]:  # edge select
        for e in bm.edges:
            if e.select:
                for v in e.verts:
                    sel.add(v.index)
    
    if sel_mode[2]:  # face select
        for f in bm.faces:
            if f.select:
                for v in f.verts:
                    sel.add(v.index)
    
    return sorted(sel)

def _selected_face_vertex_indices(context) -> List[int]:
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    
    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    sel = set()
    for f in bm.faces:
        if f.select:
            for v in f.verts:
                sel.add(v.index)
    
    return sorted(sel)

def _selected_indices_by_mode(context, mode_key: str) -> List[int]:
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
        return []
    
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    
    sel: Set[int] = set()
    
    if mode_key == 'VERT':
        for v in bm.verts:
            if v.select:
                sel.add(v.index)
    elif mode_key == 'EDGE':
        for e in bm.edges:
            if e.select:
                for v in e.verts:
                    sel.add(v.index)
    else:  # 'FACE'
        for f in bm.faces:
            if f.select:
                for v in f.verts:
                    sel.add(v.index)
    
    return sorted(sel)

def _co_key(vec) -> tuple:
    # Round coordinates to avoid float equality issues when matching vertices pre/post split
    try:
        return (round(vec.x, 6), round(vec.y, 6), round(vec.z, 6))
    except Exception:
        # Fallback if a plain tuple is passed
        return (round(vec[0], 6), round(vec[1], 6), round(vec[2], 6))

def _ensure_weighted_normal_modifier(
    obj: bpy.types.Object,
    mod_name: str,
    mode: str,
    vgroup_name: str,
):
    mod = obj.modifiers.get(mod_name)
    if mod is None:
        mod = obj.modifiers.new(name=mod_name, type='WEIGHTED_NORMAL')
        
        # Initial setup only when creating new modifier
        try:
            mod.mode = mode  # 'FACE_AREA' or 'CORNER_ANGLE'
        except Exception as e:
            log(f"Failed to set Weighted Normal 'mode': {e}")
        
        try:
            mod.weight = int(100)  # Blender 4.2 expects int in range [0, 100]
        except Exception as e:
            log(f"Failed to set Weighted Normal 'weight': {e}")
        
        try:
            mod.keep_sharp = True
        except Exception as e:
            log(f"Failed to set Weighted Normal 'keep_sharp': {e}")
        
        # Ensure modifier visibility and on-cage behavior in Edit Mode
        try:
            mod.show_viewport = True
        except Exception as e:
            log(f"Failed to set Weighted Normal 'show_viewport': {e}")
        
        try:
            mod.show_in_editmode = True
        except Exception as e:
            log(f"Failed to set Weighted Normal 'show_in_editmode': {e}")
        
        try:
            mod.show_on_cage = True
        except Exception as e:
            log(f"Failed to set Weighted Normal 'show_on_cage': {e}")
        
        log(f"Created Weighted Normal modifier: {mod_name} mode={mode}")
    
    # Coerce weight to int even for existing modifiers (compat with older versions)
    try:
        w = getattr(mod, "weight", 100)
        w_int = int(round(w)) if isinstance(w, (int, float)) else 100
        if w_int < 0:
            w_int = 0
        elif w_int > 100:
            w_int = 100
        mod.weight = w_int
    except Exception as e:
        log(f"Failed to coerce Weighted Normal 'weight' to int: {e}")
    
    # Always update the vertex group (requirement: if modifier exists, only add vertex group)
    try:
        mod.vertex_group = vgroup_name
    except Exception as e:
        log(f"Failed to set Weighted Normal 'vertex_group': {e}")

# -----------------------------------------------------------------------------
# Operators Toggle display_split_normals
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

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

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
        sel_indices = _selected_vertex_indices_in_edit_mode(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No vertices from selection (vertex/edge/face) to process")
            return {'CANCELLED'}
        
        target_vg_name = 'KHB_FaceArea'
        other_vg_name = 'KHB_CornerAngle'
        mod_name = target_vg_name
        
        # Switch to OBJECT mode to manipulate vertex groups safely
        bpy.ops.object.mode_set(mode='OBJECT')
        
        target_vg = _ensure_vgroup(obj, target_vg_name)
        other_vg = obj.vertex_groups.get(other_vg_name)
        
        moved = 0
        added_new = 0
        
        for vidx in sel_indices:
            in_other = False
            in_target_before = False
            
            if other_vg is not None:
                try:
                    other_vg.weight(vidx)
                    in_other = True
                except RuntimeError:
                    in_other = False
            
            if target_vg is not None:
                try:
                    target_vg.weight(vidx)
                    in_target_before = True
                except RuntimeError:
                    in_target_before = False
            
            if in_other:
                other_vg.remove([vidx])
                moved += 1
            
            # Count as new only if it wasn't in target and also not moved from other
            if not in_target_before and not in_other:
                added_new += 1
            
            # Add to target group
            target_vg.add([vidx], 1.0, 'REPLACE')
        
        # Ensure modifier exists and uses the correct vertex group
        _ensure_weighted_normal_modifier(obj, mod_name, 'FACE_AREA', target_vg_name)
        
        # Return to EDIT mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        if moved > 0 and added_new > 0:
            msg = f"-{moved} vertex {other_vg_name} > {target_vg_name} | +{added_new} vertex"
        elif moved > 0:
            msg = f"-{moved} vertex {other_vg_name} > {target_vg_name}"
        elif added_new > 0:
            msg = f"+{added_new} vertex > {target_vg_name}"
        else:
            msg = f"vertex already exists in {target_vg_name}"
        
        self.report({'WARNING'} if moved > 0 else {'INFO'}, msg)
        log(f"FaceArea: added_new={added_new}, moved={moved}")
        
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
        sel_indices = _selected_vertex_indices_in_edit_mode(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No vertices from selection (vertex/edge/face) to process")
            return {'CANCELLED'}
        
        target_vg_name = 'KHB_CornerAngle'
        other_vg_name = 'KHB_FaceArea'
        mod_name = target_vg_name
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        target_vg = _ensure_vgroup(obj, target_vg_name)
        other_vg = obj.vertex_groups.get(other_vg_name)
        
        moved = 0
        added_new = 0
        
        for vidx in sel_indices:
            in_other = False
            in_target_before = False
            
            if other_vg is not None:
                try:
                    other_vg.weight(vidx)
                    in_other = True
                except RuntimeError:
                    in_other = False
            
            if target_vg is not None:
                try:
                    target_vg.weight(vidx)
                    in_target_before = True
                except RuntimeError:
                    in_target_before = False
            
            if in_other:
                other_vg.remove([vidx])
                moved += 1
            
            # Count as new only if it wasn't in target and also not moved from other
            if not in_target_before and not in_other:
                added_new += 1
            
            target_vg.add([vidx], 1.0, 'REPLACE')
        
        _ensure_weighted_normal_modifier(obj, mod_name, 'CORNER_ANGLE', target_vg_name)
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        if moved > 0 and added_new > 0:
            msg = f"-{moved} vertex {other_vg_name} > {target_vg_name} | +{added_new} vertex"
        elif moved > 0:
            msg = f"-{moved} vertex {other_vg_name} > {target_vg_name}"
        elif added_new > 0:
            msg = f"+{added_new} vertex > {target_vg_name}"
        else:
            msg = f"vertex already exists in {target_vg_name}"
        
        self.report({'WARNING'} if moved > 0 else {'INFO'}, msg)
        log(f"CornerAngle: added_new={added_new}, moved={moved}")
        
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
        sel_indices = _selected_vertex_indices_in_edit_mode(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No vertices from selection (vertex/edge/face) to process")
            return {'CANCELLED'}
        
        target_vg_name = 'KHB_FaceAreaAngle'
        other_vg_names = ['KHB_FaceArea', 'KHB_CornerAngle']
        mod_name = target_vg_name
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        target_vg = _ensure_vgroup(obj, target_vg_name)
        
        moved = 0
        added_new = 0
        
        for vidx in sel_indices:
            in_target_before = False
            
            # Remove vertex from ALL other groups (FaceArea & CornerAngle), không chỉ cái đầu tiên
            for other_name in other_vg_names:
                other_vg = obj.vertex_groups.get(other_name)
                if other_vg is not None:
                    try:
                        other_vg.weight(vidx)
                        other_vg.remove([vidx])
                        moved += 1
                    except RuntimeError:
                        continue
            
            # Kiểm tra đã có trong group target chưa
            if target_vg is not None:
                try:
                    target_vg.weight(vidx)
                    in_target_before = True
                except RuntimeError:
                    in_target_before = False
            
            if not in_target_before:
                added_new += 1
            
            target_vg.add([vidx], 1.0, 'REPLACE')
        
        # Đảm bảo modifier đúng
        _ensure_weighted_normal_modifier(obj, mod_name, 'FACE_AREA_WITH_ANGLE', target_vg_name)
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        msg = f"Removed from FaceArea/CornerAngle, added {added_new} new vertices to {target_vg_name}"
        self.report({'INFO'}, msg)
        log(f"FaceAreaAngle: added_new={added_new}, moved={moved}")
        
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
        
        # Collect vertices from current selection (verts/edges/faces)
        sel_indices = _selected_vertex_indices_in_edit_mode(context)
        
        if not sel_indices:
            self.report({'WARNING'}, "No selection to build Data Transfer group")
            return {'CANCELLED'}
        
        # Create names with incremental suffix
        bpy.ops.object.mode_set(mode='OBJECT')
        
        suffix = 1
        while suffix < 100 and obj.vertex_groups.get(f"KHB_Data_{suffix:02d}") is not None:
            suffix += 1
        
        vg_name = f"KHB_Data_{suffix:02d}"
        mod_name = f"KHB_DataTransfer_{suffix:02d}"
        
        # Create/Update vertex group
        vg = _ensure_vgroup(obj, vg_name)
        
        try:
            vg.add(sel_indices, 1.0, 'REPLACE')
        except Exception:
            for i in sel_indices:
                try:
                    vg.add([i], 1.0, 'REPLACE')
                except Exception:
                    pass
        
        # Create or reuse Data Transfer modifier
        mod = obj.modifiers.get(mod_name)
        if mod is None:
            mod = obj.modifiers.new(name=mod_name, type='DATA_TRANSFER')
        
        try:
            mod.use_loop_data = True
            mod.data_types_loops = {'CUSTOM_NORMAL'}
            mod.loop_mapping = 'POLYINTERP_NEAREST'
            mod.vertex_group = vg_name
            mod.show_viewport = True
            mod.show_in_editmode = True
            mod.show_on_cage = True
            
            # Make sure source is empty; user will set it later if needed
            mod.object = None
        except Exception as e:
            log(f"Failed to configure Data Transfer: {e}")
        
        # Activate and expand the modifier
        try:
            idx = list(obj.modifiers).index(mod)
            obj.modifiers.active_index = idx
            mod.show_expanded = True
        except Exception:
            pass
        
        # Back to EDIT mode
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
        
        # Ensure faces selection exists
        face_sel_indices_before = _selected_face_vertex_indices(context)
        
        if not face_sel_indices_before:
            self.report({'WARNING'}, "No selected faces to split")
            return {'CANCELLED'}
        
        # Identify boundary vertices (selected verts touching any unselected face) BEFORE split
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
        
        # Refresh selection (post-split) and collect vertex indices again
        face_sel_indices_after = _selected_face_vertex_indices(context)
        
        # Collect all boundary vertices (both sides after split)
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        boundary_all_indices = [v.index for v in bm.verts if _co_key(v.co) in boundary_keys]
        
        # Switch to OBJECT to manipulate vertex groups and modifiers safely
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Ensure boundary vertex group for weld
        boundary_vg_name = 'KHB_WeldBoundarySharpFace'
        vg_boundary = _ensure_vgroup(obj, boundary_vg_name)
        
        if boundary_all_indices:
            try:
                vg_boundary.add(boundary_all_indices, 1.0, 'REPLACE')
            except Exception:
                # Fallback add one by one
                for vidx in boundary_all_indices:
                    try:
                        vg_boundary.add([vidx], 1.0, 'REPLACE')
                    except Exception:
                        pass
        
        # Remove selected face vertices only from vertex groups used in Data Transfer modifiers
        removed_vertices_total = 0
        affected_groups = 0
        idx_set = set(face_sel_indices_after)
        
        # Collect Data Transfer modifiers and their vertex groups
        dt_mods = [m for m in obj.modifiers if m.type == 'DATA_TRANSFER']
        dt_vgroups = []
        
        for m in dt_mods:
            name = getattr(m, 'vertex_group', '')
            if name:
                dt_vgroups.append(name)
        
        # Deduplicate while preserving order
        seen = set()
        dt_vgroups_unique = []
        for name in dt_vgroups:
            if name not in seen:
                dt_vgroups_unique.append(name)
                seen.add(name)
        
        for name in dt_vgroups_unique:
            vg = obj.vertex_groups.get(name)
            if not vg:
                continue
            
            removed_here = 0
            for vidx in idx_set:
                try:
                    vg.weight(vidx)
                    removed_here += 1
                except RuntimeError:
                    pass
            
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
        
        # Ensure Weld modifier named KBH_Weld and place it after last Data Transfer modifier
        weld = obj.modifiers.get('KBH_Weld')
        
        if weld is None:
            try:
                weld = obj.modifiers.new(name='KBH_Weld', type='WELD')
                
                # Sensible defaults
                try:
                    weld.merge_threshold = 0.0001
                except Exception:
                    pass
                
                try:
                    weld.show_viewport = True
                    weld.show_in_editmode = True
                    weld.show_on_cage = True
                except Exception:
                    pass
                
            except Exception as e:
                self.report({'ERROR'}, f"Failed to add Weld modifier: {e}")
                
                # Go back to EDIT mode and exit
                bpy.ops.object.mode_set(mode='EDIT')
                return {'CANCELLED'}
        else:
            # Ensure visibility in edit/cage
            try:
                weld.show_viewport = True
                weld.show_in_editmode = True
                weld.show_on_cage = True
            except Exception:
                pass
        
        # Assign weld to boundary vertex group
        try:
            weld.vertex_group = boundary_vg_name
        except Exception:
            pass
        
        # Reorder weld after the last DATA_TRANSFER modifier
        try:
            dt_indices = [i for i, m in enumerate(obj.modifiers) if m.type == 'DATA_TRANSFER']
            if dt_indices:
                target_index = max(dt_indices) + 1
                
                # Clamp target index to the valid range
                if target_index > len(obj.modifiers) - 1:
                    target_index = len(obj.modifiers) - 1
                
                bpy.ops.object.modifier_move_to_index(modifier=weld.name, index=target_index)
        except Exception as e:
            log(f"Failed to reorder KBH_Weld after DATA_TRANSFER: {e}")
        
        # Return to EDIT mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        msg_parts = ["Split faces"]
        if boundary_all_indices:
            msg_parts.append(f"boundary {len(boundary_all_indices)} -> {boundary_vg_name}")
        if affected_groups:
            msg_parts.append(f"removed {removed_vertices_total} vtx from {affected_groups} group(s)")
        if dt_mods:
            msg_parts.append("Weld after DataTransfer")
        else:
            msg_parts.append("Weld added")
        
        self.report({'INFO'}, " | ".join(msg_parts))
        
        return {'FINISHED'}

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
        
        # Switch to OBJECT mode to edit groups/modifiers safely
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        
        # Remove KHB vertex groups
        removed_groups = 0
        for name in ('KHB_FaceArea', 'KHB_CornerAngle', 'KHB_FaceAreaAngle'):
            vg = obj.vertex_groups.get(name)
            if vg:
                try:
                    obj.vertex_groups.remove(vg)
                    removed_groups += 1
                except Exception as e:
                    log(f"Failed to remove vertex group {name}: {e}")
        
        # Remove KHB Weighted Normal modifiers
        removed_mods = 0
        for name in ('KHB_FaceArea', 'KHB_CornerAngle', 'KHB_FaceAreaAngle'):
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
        except Exception as e:
            log(f"shade_smooth keep_sharp_edges failed: {e}")
            try:
                bpy.ops.object.shade_smooth()
                shade_ok = True
            except Exception as e2:
                log(f"shade_smooth default failed: {e2}")
        
        # Average Normals across the mesh (Edit Mode)
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
            # Restore original mode
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except Exception:
                pass
        
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
        log(f"RestoreNormals: groups={removed_groups}, mods={removed_mods}, shade={shade_ok}, average={avg_ok}")
        
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

classes = (
    KEYHABIT_OT_weight_face_area,
    KEYHABIT_OT_weight_corner_angle,
    KEYHABIT_OT_weight_face_area_angle,
    KEYHABIT_OT_setup_data_transfer,
    KEYHABIT_OT_split_faces_and_weld,
    KEYHABIT_OT_restore_normals,
    KHB_OT_toggle_split_normals,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    log("KHB_Normal registered")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    log("KHB_Normal unregistered")

# Public symbols for other modules
__all__ = [
    'KEYHABIT_OT_weight_face_area',
    'KEYHABIT_OT_weight_corner_angle', 
    'KEYHABIT_OT_weight_face_area_angle',
    'KEYHABIT_OT_setup_data_transfer',
    'KEYHABIT_OT_split_faces_and_weld',
    'KEYHABIT_OT_restore_normals',
    'register',
    'unregister',
]
