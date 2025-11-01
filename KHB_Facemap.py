# Face Map Manager for Blender
# Manages face groups similar to vertex groups, with color visualization
# Each face can only belong to one face map

import bpy
import bmesh
import json


# ============================================================================
# Color Attribute System
# ============================================================================

COLOR_ATTR_NAME = "FaceMap_Colors"

def get_or_create_color_attribute(mesh):
    """Get or create color attribute for face maps"""
    if COLOR_ATTR_NAME not in mesh.color_attributes:
        # Use FLOAT_COLOR for better precision and CORNER domain for per-face colors
        attr = mesh.color_attributes.new(
            name=COLOR_ATTR_NAME,
            type='FLOAT_COLOR',
            domain='CORNER'
        )
        return attr
    return mesh.color_attributes[COLOR_ATTR_NAME]

def set_active_color_attribute(mesh, active=True):
    """Set face map color attribute as active for viewport display"""
    if COLOR_ATTR_NAME in mesh.color_attributes:
        if active:
            mesh.color_attributes.active_color = mesh.color_attributes[COLOR_ATTR_NAME]
        return True
    return False

def remove_color_attribute(mesh):
    """Remove face map color attribute"""
    if COLOR_ATTR_NAME in mesh.color_attributes:
        mesh.color_attributes.remove(mesh.color_attributes[COLOR_ATTR_NAME])


# ============================================================================
# Persistent Storage (Custom Properties)
# ============================================================================

def save_facemap_data(mesh, manager):
    """Save face map data to mesh custom properties"""
    data = {
        'groups': [{'name': g.name, 'color': list(g.color), 'faces': list(g.faces)} for g in manager.groups],
        'face_to_group': {str(k): v for k, v in manager.face_to_group.items()}
    }
    mesh['facemap_data'] = json.dumps(data)


def load_facemap_data(mesh, manager):
    """Load face map data from mesh custom properties"""
    if 'facemap_data' not in mesh:
        return False
    
    try:
        data = json.loads(mesh['facemap_data'])
        manager.clear()
        
        for group_data in data.get('groups', []):
            group = FaceMapData(group_data['name'], tuple(group_data['color']))
            group.faces = set(group_data['faces'])
            manager.groups.append(group)
        
        manager.face_to_group = {int(k): v for k, v in data.get('face_to_group', {}).items()}
        return True
    except Exception as e:
        print(f"Error loading face map data: {e}")
        return False


def clear_facemap_data(mesh):
    """Clear face map data from mesh custom properties"""
    if 'facemap_data' in mesh:
        del mesh['facemap_data']


# ============================================================================
# Helper Functions
# ============================================================================

def set_viewport_color_display(context, enable=True):
    """Set viewport to show vertex colors"""
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    if enable:
                        space.shading.type = 'SOLID'
                        space.shading.color_type = 'VERTEX'
                    else:
                        space.shading.color_type = 'MATERIAL'


def set_boundary_sharp_edges(bm, manager):
    """Set sharp edges at face map boundaries, returns count"""
    sharp_count = 0
    
    # Clear all sharp edges first
    for edge in bm.edges:
        edge.smooth = True
    
    # Mark boundaries between different face maps as sharp
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            face1_idx = edge.link_faces[0].index
            face2_idx = edge.link_faces[1].index
            
            group1 = manager.face_to_group.get(face1_idx)
            group2 = manager.face_to_group.get(face2_idx)
            
            # Different groups or one has no group
            if (group1 is not None and group2 is not None and group1 != group2) or \
               ((group1 is None) != (group2 is None)):
                edge.smooth = False
                sharp_count += 1
        elif edge.is_boundary:
            edge.smooth = False
            sharp_count += 1
    
    return sharp_count


def enable_auto_smooth(mesh):
    """Enable Auto Smooth (compatible with Blender 3.x and 4.x)"""
    try:
        mesh.use_auto_smooth = True
        mesh.auto_smooth_angle = 3.14159  # 180 degrees
    except AttributeError:
        pass  # Blender 4.0+ - Auto smooth removed


# ============================================================================
# Face Map Data
# ============================================================================

class FaceMapData:
    """Data container for a single face map"""
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.faces = set()


class FaceMapManager:
    """Manages face maps for a mesh"""
    _instance = None
    
    def __init__(self):
        self.groups = []  # List of FaceMapData objects
        self.face_to_group = {}  # {face_index: group_index}
        self.active_group_index = -1
        self.show_colors = False
        self.mesh_object = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def clear(self):
        """Clear all face maps"""
        self.groups.clear()
        self.face_to_group.clear()
        self.active_group_index = -1
    
    # Color palette with 32 high-contrast colors
    FACE_SET_COLORS = [
        (0.90, 0.20, 0.20, 1.0),  # Red
        (0.20, 0.90, 0.20, 1.0),  # Green
        (0.20, 0.40, 0.90, 1.0),  # Blue
        (0.90, 0.90, 0.20, 1.0),  # Yellow
        (0.90, 0.20, 0.90, 1.0),  # Magenta
        (0.20, 0.90, 0.90, 1.0),  # Cyan
        (0.90, 0.50, 0.20, 1.0),  # Orange
        (0.60, 0.20, 0.90, 1.0),  # Purple
        (0.20, 0.90, 0.60, 1.0),  # Mint
        (0.90, 0.60, 0.60, 1.0),  # Light Red
        (0.60, 0.90, 0.60, 1.0),  # Light Green
        (0.60, 0.60, 0.90, 1.0),  # Light Blue
        (0.90, 0.70, 0.20, 1.0),  # Gold
        (0.90, 0.20, 0.60, 1.0),  # Pink
        (0.70, 0.90, 0.20, 1.0),  # Lime
        (0.20, 0.70, 0.90, 1.0),  # Sky Blue
        (0.50, 0.20, 0.60, 1.0),  # Dark Purple
        (0.20, 0.60, 0.50, 1.0),  # Teal
        (0.60, 0.50, 0.20, 1.0),  # Brown
        (0.90, 0.40, 0.70, 1.0),  # Hot Pink
        (0.40, 0.90, 0.70, 1.0),  # Aqua
        (0.70, 0.40, 0.90, 1.0),  # Violet
        (0.90, 0.70, 0.40, 1.0),  # Peach
        (0.40, 0.70, 0.90, 1.0),  # Cornflower
        (0.70, 0.90, 0.40, 1.0),  # Yellow Green
        (0.30, 0.90, 0.30, 1.0),  # Bright Green
        (0.90, 0.30, 0.30, 1.0),  # Bright Red
        (0.30, 0.30, 0.90, 1.0),  # Bright Blue
        (0.90, 0.30, 0.70, 1.0),  # Fuchsia
        (0.70, 0.30, 0.90, 1.0),  # Orchid
        (0.30, 0.90, 0.70, 1.0),  # Spring Green
        (0.90, 0.70, 0.30, 1.0),  # Amber
    ]
    
    def add_group(self, name=None):
        """Add a new face map"""
        if name is None:
            # Format: Face Map 01, Face Map 02, etc.
            name = f"Face Map {len(self.groups) + 1:02d}"
        
        # Use color from palette (cycle through colors)
        color_index = len(self.groups) % len(self.FACE_SET_COLORS)
        color = self.FACE_SET_COLORS[color_index]
        
        group = FaceMapData(name, color)
        self.groups.append(group)
        return len(self.groups) - 1
    
    def remove_group(self, index):
        """Remove a face map"""
        if 0 <= index < len(self.groups):
            # Remove faces from face_to_group mapping
            faces_to_remove = []
            for face_idx, group_idx in self.face_to_group.items():
                if group_idx == index:
                    faces_to_remove.append(face_idx)
                elif group_idx > index:
                    self.face_to_group[face_idx] = group_idx - 1
            
            for face_idx in faces_to_remove:
                del self.face_to_group[face_idx]
            
            self.groups.pop(index)
            
            if self.active_group_index >= len(self.groups):
                self.active_group_index = len(self.groups) - 1
    
    def assign_faces(self, face_indices, group_index):
        """Assign faces to a group (removes from other groups)"""
        if not (0 <= group_index < len(self.groups)):
            return
        
        for face_idx in face_indices:
            # Remove from previous group
            if face_idx in self.face_to_group:
                old_group_idx = self.face_to_group[face_idx]
                if old_group_idx < len(self.groups):
                    self.groups[old_group_idx].faces.discard(face_idx)
            
            # Add to new group
            self.face_to_group[face_idx] = group_index
            self.groups[group_index].faces.add(face_idx)
    
    def update_color_attribute(self, obj, safe_mode=False):
        """Update color attribute based on face maps
        
        Args:
            obj: Mesh object to update
            safe_mode: If True, skip mode changes (safe for draw context)
        """
        if not obj or obj.type != 'MESH':
            return
        
        mode = obj.mode
        
        # In safe mode, only update if already in Object mode
        if safe_mode and mode == 'EDIT':
            # Cannot modify data in safe mode (draw context)
            return
        
        # Need to be in object mode to properly update color attributes
        if mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        try:
            me = obj.data
            color_attr = get_or_create_color_attribute(me)
            
            if len(color_attr.data) != len(me.loops):
                remove_color_attribute(me)
                color_attr = get_or_create_color_attribute(me)
            
            for poly in me.polygons:
                face_idx = poly.index
                
                if face_idx in self.face_to_group:
                    group_idx = self.face_to_group[face_idx]
                    if group_idx < len(self.groups):
                        color = self.groups[group_idx].color
                        face_color = (color[0], color[1], color[2], 1.0)
                    else:
                        face_color = (1.0, 1.0, 1.0, 1.0)
                else:
                    face_color = (0.5, 0.5, 0.5, 1.0)
                
                for loop_idx in poly.loop_indices:
                    color_attr.data[loop_idx].color = face_color
            
            me.update()
        
        finally:
            # Return to original mode
            if mode == 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
    
    def initialize_by_sharp_edges(self, obj):
        """Initialize face maps based on sharp edges using flood fill"""
        self.clear()
        self.mesh_object = obj
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        visited = set()
        
        def flood_fill(start_face):
            stack = [start_face]
            group_faces = []
            
            while stack:
                face = stack.pop()
                if face.index in visited:
                    continue
                
                visited.add(face.index)
                group_faces.append(face.index)
                
                for edge in face.edges:
                    if not edge.smooth:
                        continue
                    for linked_face in edge.link_faces:
                        if linked_face.index not in visited:
                            stack.append(linked_face)
            
            return group_faces
        
        for i, face in enumerate(bm.faces):
            if face.index not in visited:
                group_faces = flood_fill(face)
                if group_faces:
                    group_idx = self.add_group(f"Face Map {i + 1:02d}")
                    self.assign_faces(group_faces, group_idx)
        
        bmesh.update_edit_mesh(obj.data)


# ============================================================================
# Operators
# ============================================================================

class FACEMAP_OT_InitializeBySharp(bpy.types.Operator):
    bl_idname = "facemap.initialize_by_sharp"
    bl_label = "Initialize by Sharp Edges"
    bl_description = "Create face maps based on sharp edges (similar to Face Sets in Sculpt Mode)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.edit_object
    
    def execute(self, context):
        obj = context.edit_object
        
        manager = FaceMapManager.get_instance()
        manager.mesh_object = obj
        
        # Update from edit mode
        obj.update_from_editmode()
        
        # Step 1-4: Initialize face maps by sharp edges
        manager.initialize_by_sharp_edges(obj)
        
        # Step 5: Clear all sharp edges, then set face map boundaries as sharp
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        sharp_count = set_boundary_sharp_edges(bm, manager)
        bmesh.update_edit_mesh(obj.data)
        
        enable_auto_smooth(obj.data)
        
        # Save, update and display
        save_facemap_data(obj.data, manager)
        manager.update_color_attribute(obj)
        manager.show_colors = True
        set_active_color_attribute(obj.data, True)
        set_viewport_color_display(context, True)
        
        self.report({'INFO'}, f"Created {len(manager.groups)} face maps with {sharp_count} boundary sharp edges")
        return {'FINISHED'}


class FACEMAP_OT_ToggleColors(bpy.types.Operator):
    bl_idname = "facemap.toggle_colors"
    bl_label = "Toggle Colors"
    bl_description = "Toggle face map color visualization for all mesh objects"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        return True  # Always available
    
    def execute(self, context):
        manager = FaceMapManager.get_instance()
        manager.show_colors = not manager.show_colors
        
        # Update all mesh objects in scene
        updated_count = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and 'facemap_data' in obj.data:
                if manager.show_colors:
                    # Load data for this object
                    temp_manager = FaceMapManager()
                    if load_facemap_data(obj.data, temp_manager):
                        # Only update if object is in Object mode to avoid disrupting user
                        if obj.mode == 'OBJECT':
                            temp_manager.update_color_attribute(obj, safe_mode=False)
                        # Try to set active color attribute
                        try:
                            set_active_color_attribute(obj.data, True)
                        except:
                            pass  # Ignore if not allowed in this context
                        updated_count += 1
                else:
                    # Just count if exists
                    if COLOR_ATTR_NAME in obj.data.color_attributes:
                        updated_count += 1
        
        if manager.show_colors:
            set_viewport_color_display(context, True)
            self.report({'INFO'}, f"Face map colors enabled ({updated_count} objects)")
        else:
            set_viewport_color_display(context, False)
            self.report({'INFO'}, "Face map colors disabled")
        
        context.area.tag_redraw()
        return {'FINISHED'}


class FACEMAP_OT_CreateFromSelection(bpy.types.Operator):
    bl_idname = "facemap.create_from_selection"
    bl_label = "Create Face Map from Selection"
    bl_description = "Create a new face map and assign selected faces to it"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.edit_object
    
    def execute(self, context):
        manager = FaceMapManager.get_instance()
        obj = context.edit_object
        obj.update_from_editmode()
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        # Get selected faces
        selected_faces = [f.index for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}
        
        # Create new face map and assign faces
        group_idx = manager.add_group()
        manager.active_group_index = group_idx
        manager.assign_faces(selected_faces, group_idx)
        
        # Clear all sharp edges and rebuild from all face map boundaries
        sharp_count = set_boundary_sharp_edges(bm, manager)
        bmesh.update_edit_mesh(obj.data)
        
        enable_auto_smooth(obj.data)
        
        # Save, update and display
        save_facemap_data(obj.data, manager)
        manager.update_color_attribute(obj)
        
        if not manager.show_colors:
            manager.show_colors = True
            set_active_color_attribute(obj.data, True)
            set_viewport_color_display(context, True)
        
        context.area.tag_redraw()
        self.report({'INFO'}, f"Created '{manager.groups[group_idx].name}' with {len(selected_faces)} faces | Rebuilt {sharp_count} sharp edges")
        return {'FINISHED'}


class FACEMAP_OT_Optimize(bpy.types.Operator):
    bl_idname = "facemap.optimize"
    bl_label = "Optimize Face Maps"
    bl_description = "Merge non-adjacent face maps to reduce total count (graph coloring)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.edit_object
    
    def execute(self, context):
        manager = FaceMapManager.get_instance()
        
        if len(manager.groups) < 2:
            self.report({'INFO'}, "Need at least 2 face maps to optimize")
            return {'CANCELLED'}
        
        obj = context.edit_object
        obj.update_from_editmode()
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        # Build adjacency graph
        adjacency = {i: set() for i in range(len(manager.groups))}
        
        for edge in bm.edges:
            if len(edge.link_faces) == 2:
                group1 = manager.face_to_group.get(edge.link_faces[0].index)
                group2 = manager.face_to_group.get(edge.link_faces[1].index)
                
                if group1 is not None and group2 is not None and group1 != group2:
                    adjacency[group1].add(group2)
                    adjacency[group2].add(group1)
        
        # Greedy graph coloring
        colors = {}
        for group_idx in range(len(manager.groups)):
            used_colors = {colors[adj] for adj in adjacency[group_idx] if adj in colors}
            color = 0
            while color in used_colors:
                color += 1
            colors[group_idx] = color
        
        # Merge groups with same color
        new_groups_data = {}
        for group_idx, color in colors.items():
            if color not in new_groups_data:
                new_groups_data[color] = {
                    'name': f"Face Map {color + 1:02d}",
                    'faces': set(),
                    'color': manager.FACE_SET_COLORS[color % len(manager.FACE_SET_COLORS)]
                }
            new_groups_data[color]['faces'].update(manager.groups[group_idx].faces)
        
        # Rebuild face maps
        old_count = len(manager.groups)
        manager.clear()
        
        for color in sorted(new_groups_data.keys()):
            data = new_groups_data[color]
            group = FaceMapData(data['name'], data['color'])
            group.faces = data['faces']
            manager.groups.append(group)
            
            group_idx = len(manager.groups) - 1
            for face_idx in data['faces']:
                manager.face_to_group[face_idx] = group_idx
        
        save_facemap_data(obj.data, manager)
        manager.update_color_attribute(obj)
        context.area.tag_redraw()
        
        new_count = len(manager.groups)
        self.report({'INFO'}, f"Optimized: {old_count} → {new_count} face maps")
        return {'FINISHED'}


class FACEMAP_OT_ClearAll(bpy.types.Operator):
    bl_idname = "facemap.clear_all"
    bl_label = "Clear All"
    bl_description = "Clear all face maps and remove color attributes from active object only"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.edit_object
    
    def execute(self, context):
        manager = FaceMapManager.get_instance()
        obj = context.edit_object
        
        # Only affect the active object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object")
            return {'CANCELLED'}
        
        # Clear sharp edges (only on this object)
        bm = bmesh.from_edit_mesh(obj.data)
        for edge in bm.edges:
            edge.smooth = True
        bmesh.update_edit_mesh(obj.data)
        
        # Clear color attribute (only on this object)
        remove_color_attribute(obj.data)
        
        # Clear from custom properties (only on this object)
        clear_facemap_data(obj.data)
        
        # Clear manager (will reload from other objects when switched)
        manager.clear()
        manager.mesh_object = None
        
        context.area.tag_redraw()
        self.report({'INFO'}, f"Cleared all face maps from '{obj.name}'")
        return {'FINISHED'}


# ============================================================================
# Panel
# ============================================================================

class FACEMAP_PT_Panel(bpy.types.Panel):
    bl_label = "Face Maps"
    bl_idname = "FACEMAP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "KeyHabit"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        return True  # Always show panel
    
    def draw(self, context):
        layout = self.layout
        manager = FaceMapManager.get_instance()
        
        # Show/Hide toggle - always available
        box = layout.box()
        row = box.row()
        row.label(text="Face Maps:", icon='FACE_MAPS')
        
        # Count face maps in current object if in Edit Mode
        if context.mode == 'EDIT_MESH' and context.edit_object:
            obj = context.edit_object
            if obj and obj.data:
                if manager.mesh_object != obj or not manager.groups:
                    if load_facemap_data(obj.data, manager):
                        manager.mesh_object = obj
                        # Note: Cannot set active_color in draw context
            row.label(text=f"{len(manager.groups)}")
        else:
            row.label(text="--")
        
        # Show/Hide button - always visible
        icon = 'HIDE_OFF' if manager.show_colors else 'HIDE_ON'
        row.operator("facemap.toggle_colors", text="", icon=icon)
        
        # Rest of the UI only in Edit Mode
        if context.mode != 'EDIT_MESH':
            box.label(text="Switch to Edit Mode for editing", icon='INFO')
            return
        
        obj = context.edit_object
        if not obj:
            return
        
        if manager.groups:
            col = box.column(align=True)
            for i, group in enumerate(manager.groups):
                row = col.row(align=True)
                is_active = (i == manager.active_group_index)
                op = row.operator("facemap.set_active", text=group.name, emboss=is_active, depress=is_active)
                op.index = i
        else:
            box.label(text="No face maps")
        
        row = box.row(align=True)
        row.operator("facemap.create_from_selection", text="Create", icon='ADD')
        
        if manager.groups:
            row.operator("facemap.clear_all", text="Clear All", icon='TRASH')
        
        layout.separator()
        
        box = layout.box()
        box.label(text="Operations:", icon='MODIFIER')
        
        col = box.column(align=True)
        col.operator("facemap.initialize_by_sharp", text="Initialize by Sharp Edges", icon='MOD_EDGESPLIT')
        
        if manager.groups:
            col.separator()
            col.operator("facemap.optimize", text="Optimize (Merge)", icon='AUTOMERGE_ON')


class FACEMAP_OT_SetActive(bpy.types.Operator):
    bl_idname = "facemap.set_active"
    bl_label = "Set Active"
    bl_description = "Set active face map"
    bl_options = {'INTERNAL'}
    
    index: bpy.props.IntProperty()
    
    def execute(self, context):
        manager = FaceMapManager.get_instance()
        manager.active_group_index = self.index
        return {'FINISHED'}


# ============================================================================
# Registration
# ============================================================================

classes = (
    FACEMAP_OT_InitializeBySharp,
    FACEMAP_OT_ToggleColors,
    FACEMAP_OT_CreateFromSelection,
    FACEMAP_OT_Optimize,
    FACEMAP_OT_ClearAll,
    FACEMAP_OT_SetActive,
    FACEMAP_PT_Panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


if __name__ == "__main__":
    register()
    print("Face Map Manager loaded successfully!")


