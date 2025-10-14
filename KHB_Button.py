"""
KeyHabit Button System - Advanced Gizmo Implementation
Version: 1.0.0
Author: MinThuan
Integration: Seamless with existing KeyHabit addon architecture
"""

import bpy
from bpy.types import Gizmo, GizmoGroup, Operator, Panel
from bpy.props import (
    BoolProperty, FloatProperty, EnumProperty, FloatVectorProperty, StringProperty
)
from mathutils import Matrix, Vector
from bpy_extras import view3d_utils
import blf
import gpu
from gpu_extras.batch import batch_for_shader

# ================================
# CONSTANTS & CONFIGURATION
# ================================

KHB_BUTTON_VERSION = "1.0.0"

# Button Actions Registry
KHB_BUTTON_ACTIONS = {
    'KEYFRAME_ADD': {
        'label': 'Add Key',
        'icon': 'KEYFRAME_HLT',
        'color': (0.2, 0.8, 0.2),
        'description': 'Insert keyframe at current frame'
    },
    'KEYFRAME_DELETE': {
        'label': 'Del Key', 
        'icon': 'KEYFRAME',
        'color': (0.8, 0.2, 0.2),
        'description': 'Delete keyframe at current frame'
    },
    'TRANSFORM_RESET': {
        'label': 'Reset',
        'icon': 'LOOP_BACK',
        'color': (0.2, 0.2, 0.8),
        'description': 'Reset object transform to default'
    },
    'TRANSFORM_COPY': {
        'label': 'Copy',
        'icon': 'COPYDOWN',
        'color': (0.8, 0.8, 0.2),
        'description': 'Copy object transform'
    },
    'TRANSFORM_PASTE': {
        'label': 'Paste',
        'icon': 'PASTEDOWN', 
        'color': (0.8, 0.2, 0.8),
        'description': 'Paste stored transform'
    },
    'SELECT_SIMILAR': {
        'label': 'Similar',
        'icon': 'SELECT_EXTEND',
        'color': (0.2, 0.8, 0.8),
        'description': 'Select objects of same type'
    },
    'MODIFIER_ADD': {
        'label': 'Add Mod',
        'icon': 'MODIFIER',
        'color': (0.5, 0.7, 0.3),
        'description': 'Add common modifier'
    },
    'MATERIAL_ASSIGN': {
        'label': 'Material',
        'icon': 'MATERIAL',
        'color': (0.7, 0.5, 0.3),
        'description': 'Assign active material'
    }
}

# Layout Configurations
KHB_LAYOUTS = {
    'CIRCULAR': {
        'name': 'Circular',
        'radius': 3.0,
        'description': 'Arrange buttons in circle around object'
    },
    'LINEAR': {
        'name': 'Linear',
        'spacing': 2.5,
        'description': 'Arrange buttons in horizontal line'
    },
    'GRID': {
        'name': 'Grid',
        'cols': 3,
        'spacing': 2.0,
        'description': 'Arrange buttons in grid pattern'
    },
    'VERTICAL': {
        'name': 'Vertical',
        'spacing': 1.5,
        'description': 'Arrange buttons in vertical stack'
    }
}

# ================================
# SCENE PROPERTIES INTEGRATION
# ================================

def khb_update_button_system(self, context):
    """Update callback for button system changes"""
    # Force viewport refresh
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
    
    # Update gizmo positions if enabled
    if self.khb_button_system_enabled:
        khb_refresh_button_gizmos(context)

def khb_register_button_properties():
    """Register button system properties to Scene"""
    
    # === MAIN CONTROLS ===
    bpy.types.Scene.khb_button_system_enabled = BoolProperty(
        name="Enable Button System",
        description="Enable advanced gizmo button system for KeyHabit",
        default=False,
        update=khb_update_button_system
    )
    
    # === LAYOUT SETTINGS ===
    bpy.types.Scene.khb_button_layout = EnumProperty(
        name="Button Layout",
        description="Layout pattern for button gizmos",
        items=[
            ('CIRCULAR', 'Circular', 'Arrange buttons in circle', 'ORIENTATION_GIMBAL', 0),
            ('LINEAR', 'Linear', 'Arrange buttons in line', 'ARROW_LEFTRIGHT', 1),
            ('GRID', 'Grid', 'Arrange buttons in grid', 'GRID', 2),
            ('VERTICAL', 'Vertical', 'Arrange buttons vertically', 'TRIA_UP_BAR', 3),
            ('HIDDEN', 'Hidden', 'Hide all buttons', 'HIDE_ON', 4)
        ],
        default='CIRCULAR',
        update=khb_update_button_system
    )
    
    # === SIZE & POSITION ===
    bpy.types.Scene.khb_button_size = FloatProperty(
        name="Button Size",
        description="Size multiplier for button gizmos",
        default=1.0,
        min=0.2,
        max=3.0,
        step=0.1,
        update=khb_update_button_system
    )
    
    bpy.types.Scene.khb_button_offset = FloatVectorProperty(
        name="Button Offset",
        description="Position offset for button group (X, Y, Z)",
        size=3,
        default=(0.0, 0.0, 2.0),
        step=50,
        precision=1,
        update=khb_update_button_system
    )
    
    # === VISUAL SETTINGS ===
    bpy.types.Scene.khb_button_alpha = FloatProperty(
        name="Button Transparency",
        description="Transparency of button gizmos",
        default=0.8,
        min=0.1,
        max=1.0,
        step=0.1,
        update=khb_update_button_system
    )
    
    bpy.types.Scene.khb_button_show_labels = BoolProperty(
        name="Show Labels",
        description="Display text labels on buttons",
        default=True,
        update=khb_update_button_system
    )
    
    bpy.types.Scene.khb_button_auto_scale = BoolProperty(
        name="Auto Scale",
        description="Automatically scale buttons based on viewport zoom",
        default=True,
        update=khb_update_button_system
    )
    
    # === ACTIVE BUTTONS ===
    bpy.types.Scene.khb_active_buttons = EnumProperty(
        name="Active Button Set",
        description="Which set of buttons to show",
        items=[
            ('ANIMATION', 'Animation', 'Keyframe and animation tools', 'ANIM', 0),
            ('TRANSFORM', 'Transform', 'Transform and positioning tools', 'OBJECT_ORIGIN', 1),
            ('MODELING', 'Modeling', 'Modeling and modifier tools', 'EDITMODE_HLT', 2),
            ('MATERIAL', 'Material', 'Material and shading tools', 'MATERIAL', 3),
            ('CUSTOM', 'Custom', 'User-defined button set', 'TOOL_SETTINGS', 4)
        ],
        default='ANIMATION',
        update=khb_update_button_system
    )
    
    # === TEMPORARY STORAGE ===
    bpy.types.Scene.khb_temp_location = FloatVectorProperty(
        name="Temp Location", size=3, default=(0.0, 0.0, 0.0)
    )
    bpy.types.Scene.khb_temp_rotation = FloatVectorProperty(
        name="Temp Rotation", size=3, default=(0.0, 0.0, 0.0)
    )
    bpy.types.Scene.khb_temp_scale = FloatVectorProperty(
        name="Temp Scale", size=3, default=(1.0, 1.0, 1.0)
    )

# ================================
# BUTTON OPERATORS
# ================================

class KHB_OT_ButtonAction(Operator):
    """KeyHabit Button Action Operator"""
    bl_idname = "khb.button_action"
    bl_label = "KeyHabit Button Action"
    bl_description = "Execute button action"
    bl_options = {'REGISTER', 'UNDO'}
    
    action_type: StringProperty()
    
    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        
        try:
            if self.action_type == "KEYFRAME_ADD":
                return self.execute_keyframe_add(context, obj)
            elif self.action_type == "KEYFRAME_DELETE":
                return self.execute_keyframe_delete(context, obj, scene)
            elif self.action_type == "TRANSFORM_RESET":
                return self.execute_transform_reset(context, obj)
            elif self.action_type == "TRANSFORM_COPY":
                return self.execute_transform_copy(context, obj, scene)
            elif self.action_type == "TRANSFORM_PASTE":
                return self.execute_transform_paste(context, obj, scene)
            elif self.action_type == "SELECT_SIMILAR":
                return self.execute_select_similar(context, obj, scene)
            elif self.action_type == "MODIFIER_ADD":
                return self.execute_modifier_add(context, obj)
            elif self.action_type == "MATERIAL_ASSIGN":
                return self.execute_material_assign(context, obj)
            else:
                self.report({'ERROR'}, f"Unknown action: {self.action_type}")
                return {'CANCELLED'}
        
        except Exception as e:
            self.report({'ERROR'}, f"Action failed: {str(e)}")
            return {'CANCELLED'}
    
    def execute_keyframe_add(self, context, obj):
        """Add keyframes to active object"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        # Insert keyframes for transform properties
        obj.keyframe_insert(data_path="location")
        obj.keyframe_insert(data_path="rotation_euler")
        obj.keyframe_insert(data_path="scale")
        
        self.report({'INFO'}, f"Keyframes added for {obj.name} at frame {context.scene.frame_current}")
        return {'FINISHED'}
    
    def execute_keyframe_delete(self, context, obj, scene):
        """Delete keyframes from active object"""
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No keyframes to delete")
            return {'CANCELLED'}
        
        frame = scene.frame_current
        try:
            obj.keyframe_delete(data_path="location", frame=frame)
            obj.keyframe_delete(data_path="rotation_euler", frame=frame)
            obj.keyframe_delete(data_path="scale", frame=frame)
            self.report({'INFO'}, f"Keyframes deleted at frame {frame}")
        except RuntimeError:
            self.report({'WARNING'}, f"No keyframes found at frame {frame}")
        
        return {'FINISHED'}
    
    def execute_transform_reset(self, context, obj):
        """Reset object transform"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)
        
        self.report({'INFO'}, f"Transform reset for {obj.name}")
        return {'FINISHED'}
    
    def execute_transform_copy(self, context, obj, scene):
        """Copy object transform"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        scene.khb_temp_location = obj.location
        scene.khb_temp_rotation = obj.rotation_euler
        scene.khb_temp_scale = obj.scale
        
        self.report({'INFO'}, f"Transform copied from {obj.name}")
        return {'FINISHED'}
    
    def execute_transform_paste(self, context, obj, scene):
        """Paste stored transform"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        if not hasattr(scene, 'khb_temp_location'):
            self.report({'WARNING'}, "No transform data to paste")
            return {'CANCELLED'}
        
        obj.location = scene.khb_temp_location
        obj.rotation_euler = scene.khb_temp_rotation  
        obj.scale = scene.khb_temp_scale
        
        self.report({'INFO'}, f"Transform pasted to {obj.name}")
        return {'FINISHED'}
    
    def execute_select_similar(self, context, obj, scene):
        """Select objects of same type"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        obj_type = obj.type
        count = 0
        
        # Deselect all first
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select objects of same type
        for o in scene.objects:
            if o.type == obj_type:
                o.select_set(True)
                count += 1
        
        # Keep active object active
        context.view_layer.objects.active = obj
        
        self.report({'INFO'}, f"Selected {count} {obj_type} objects")
        return {'FINISHED'}
    
    def execute_modifier_add(self, context, obj):
        """Add common modifier based on object type"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        if obj.type != 'MESH':
            self.report({'WARNING'}, "Active object is not a mesh")
            return {'CANCELLED'}
        
        # Add subdivision surface modifier
        modifier = obj.modifiers.new(name="Subdivision", type='SUBSURF')
        modifier.levels = 2
        
        self.report({'INFO'}, f"Subdivision modifier added to {obj.name}")
        return {'FINISHED'}
    
    def execute_material_assign(self, context, obj):
        """Assign active material to object"""
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}
        
        if obj.type != 'MESH':
            self.report({'WARNING'}, "Active object is not a mesh")
            return {'CANCELLED'}
        
        # Get active material
        active_mat = context.object.active_material if context.object else None
        if not active_mat:
            # Create a new material
            mat = bpy.data.materials.new(name="KHB_Material")
            mat.use_nodes = True
            active_mat = mat
        
        # Assign material
        if len(obj.data.materials) == 0:
            obj.data.materials.append(active_mat)
        else:
            obj.data.materials[0] = active_mat
        
        self.report({'INFO'}, f"Material '{active_mat.name}' assigned to {obj.name}")
        return {'FINISHED'}

# ================================
# GIZMO CLASSES
# ================================

class KHB_GT_ButtonGizmo(Gizmo):
    """Advanced Button Gizmo with integrated KeyHabit styling"""
    bl_idname = "KHB_GT_button_gizmo"
    
    def __init__(self):
        self.custom_shape = None
        self.action_type = ""
        self.button_config = {}
        
    def setup(self):
        """Initialize button gizmo with KeyHabit styling"""
        # Create button shape - rounded rectangle
        verts, faces = self.create_button_shape()
        self.custom_shape = self.new_custom_shape('TRIS', verts, faces)
        
        # Get button configuration
        self.button_config = KHB_BUTTON_ACTIONS.get(self.action_type, {})
        
        # Configure appearance
        self.color = self.button_config.get('color', (0.5, 0.5, 0.5))
        self.alpha = 0.8
        self.color_highlight = tuple(min(c + 0.3, 1.0) for c in self.color)
        self.alpha_highlight = 1.0
        
        # Scaling properties
        self.use_draw_scale = True
        self.scale_basis = 0.2
    
    def create_button_shape(self):
        """Create rounded rectangular button shape"""
        import math
        
        width, height = 1.0, 0.4
        corner_radius = 0.1
        segments = 8
        
        verts = []
        faces = []
        
        # Create rounded corners
        corners = [
            (width/2 - corner_radius, height/2 - corner_radius),    # Top-right
            (-width/2 + corner_radius, height/2 - corner_radius),   # Top-left
            (-width/2 + corner_radius, -height/2 + corner_radius),  # Bottom-left
            (width/2 - corner_radius, -height/2 + corner_radius)    # Bottom-right
        ]
        
        # Add center vertex
        verts.append((0, 0, 0))
        center_idx = 0
        
        # Generate vertices for each corner
        for corner_x, corner_y in corners:
            for i in range(segments // 4):
                angle = (i / (segments // 4)) * (math.pi / 2)
                if corners.index((corner_x, corner_y)) == 0:  # Top-right
                    angle = angle
                elif corners.index((corner_x, corner_y)) == 1:  # Top-left  
                    angle = math.pi/2 + angle
                elif corners.index((corner_x, corner_y)) == 2:  # Bottom-left
                    angle = math.pi + angle
                else:  # Bottom-right
                    angle = 3*math.pi/2 + angle
                
                x = corner_x + corner_radius * math.cos(angle)
                y = corner_y + corner_radius * math.sin(angle)
                verts.append((x, y, 0))
        
        # Create faces from center to edge vertices
        vert_count = len(verts)
        for i in range(1, vert_count):
            next_i = i + 1 if i < vert_count - 1 else 1
            faces.append([center_idx, i, next_i])
        
        return verts, faces
    
    def draw(self, context):
        """Draw button gizmo with label"""
        if self.custom_shape:
            self.draw_custom_shape(self.custom_shape)
        
        # Draw label if enabled
        scene = context.scene
        if getattr(scene, 'khb_button_show_labels', True):
            self.draw_button_label(context)
    
    def draw_button_label(self, context):
        """Draw button text label"""
        try:
            label = self.button_config.get('label', self.action_type)
            if not label:
                return
            
            # Get screen coordinates
            region = context.region
            rv3d = context.region_data
            location_3d = self.matrix_world.translation
            location_2d = view3d_utils.location_3d_to_region_2d(
                region, rv3d, location_3d
            )
            
            if location_2d:
                font_id = 0
                
                # Calculate text position (centered)
                text_width = blf.dimensions(font_id, label)[0]
                text_x = location_2d.x - text_width / 2
                text_y = location_2d.y - 6
                
                # Setup font
                blf.position(font_id, text_x, text_y, 0)
                blf.size(font_id, 10, 72)
                blf.color(font_id, 1, 1, 1, 1)
                
                # Draw text with subtle shadow
                blf.position(font_id, text_x + 1, text_y - 1, 0)
                blf.color(font_id, 0, 0, 0, 0.5)  # Shadow
                blf.draw(font_id, label)
                
                blf.position(font_id, text_x, text_y, 0)
                blf.color(font_id, 1, 1, 1, 1)  # Main text
                blf.draw(font_id, label)
                
        except Exception as e:
            # Fail silently for text drawing issues
            pass
    
    def draw_select(self, context, select_id):
        """Draw selection highlight"""
        if self.custom_shape:
            self.draw_custom_shape(self.custom_shape, select_id=select_id)
    
    def invoke(self, context, event):
        """Handle button press"""
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event, tweak):
        """Handle button interaction"""
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            # Execute button action
            bpy.ops.khb.button_action('INVOKE_DEFAULT', action_type=self.action_type)
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

# ================================
# GIZMO GROUP MANAGER
# ================================

class KHB_GGT_ButtonGroup(GizmoGroup):
    """KeyHabit Button Gizmo Group Manager"""
    bl_idname = "KHB_GGT_button_group"
    bl_label = "KeyHabit Button Group"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SCALE'}
    
    @classmethod
    def poll(cls, context):
        """Determine when to show button group"""
        scene = context.scene
        return (
            context.mode == 'OBJECT' and
            context.active_object is not None and
            getattr(scene, 'khb_button_system_enabled', False) and
            getattr(scene, 'khb_button_layout', 'CIRCULAR') != 'HIDDEN'
        )
    
    def setup(self, context):
        """Setup button gizmos based on active button set"""
        scene = context.scene
        
        # Clear existing gizmos
        self.gizmos.clear()
        
        # Get active button set
        button_set = getattr(scene, 'khb_active_buttons', 'ANIMATION')
        layout = getattr(scene, 'khb_button_layout', 'CIRCULAR')
        
        # Define button sets
        button_sets = {
            'ANIMATION': ['KEYFRAME_ADD', 'KEYFRAME_DELETE'],
            'TRANSFORM': ['TRANSFORM_RESET', 'TRANSFORM_COPY', 'TRANSFORM_PASTE'],
            'MODELING': ['MODIFIER_ADD', 'SELECT_SIMILAR'],
            'MATERIAL': ['MATERIAL_ASSIGN'],
            'CUSTOM': ['KEYFRAME_ADD', 'TRANSFORM_RESET', 'MODIFIER_ADD', 'SELECT_SIMILAR']
        }
        
        active_buttons = button_sets.get(button_set, button_sets['ANIMATION'])
        
        # Setup layout
        if layout == 'CIRCULAR':
            self.setup_circular_layout(active_buttons)
        elif layout == 'LINEAR':
            self.setup_linear_layout(active_buttons)
        elif layout == 'GRID':
            self.setup_grid_layout(active_buttons)
        elif layout == 'VERTICAL':
            self.setup_vertical_layout(active_buttons)
    
    def setup_circular_layout(self, buttons):
        """Arrange buttons in circular pattern"""
        import math
        
        config = KHB_LAYOUTS['CIRCULAR']
        radius = config['radius']
        
        for i, action_type in enumerate(buttons):
            angle = (i / len(buttons)) * 2 * math.pi
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            self.create_button_gizmo(action_type, (x, y, 0))
    
    def setup_linear_layout(self, buttons):
        """Arrange buttons in horizontal line"""
        config = KHB_LAYOUTS['LINEAR']
        spacing = config['spacing']
        start_x = -(len(buttons) - 1) * spacing / 2
        
        for i, action_type in enumerate(buttons):
            x = start_x + i * spacing
            self.create_button_gizmo(action_type, (x, 0, 0))
    
    def setup_grid_layout(self, buttons):
        """Arrange buttons in grid pattern"""
        config = KHB_LAYOUTS['GRID']
        cols = config['cols']
        spacing = config['spacing']
        
        for i, action_type in enumerate(buttons):
            row = i // cols
            col = i % cols
            
            x = (col - (cols - 1) / 2) * spacing
            y = -row * spacing
            
            self.create_button_gizmo(action_type, (x, y, 0))
    
    def setup_vertical_layout(self, buttons):
        """Arrange buttons in vertical stack"""
        config = KHB_LAYOUTS['VERTICAL']
        spacing = config['spacing']
        start_y = (len(buttons) - 1) * spacing / 2
        
        for i, action_type in enumerate(buttons):
            y = start_y - i * spacing
            self.create_button_gizmo(action_type, (0, y, 0))
    
    def create_button_gizmo(self, action_type, position):
        """Create individual button gizmo"""
        gizmo = self.gizmos.new("KHB_GT_button_gizmo")
        gizmo.action_type = action_type
        gizmo.matrix_basis = Matrix.Translation(position)
        return gizmo
    
    def refresh(self, context):
        """Update gizmo positions and properties"""
        scene = context.scene
        obj = context.active_object
        
        if not obj:
            return
        
        # Get object transform
        obj_matrix = obj.matrix_world.copy()
        
        # Apply user offset
        offset = getattr(scene, 'khb_button_offset', (0, 0, 2))
        offset_matrix = Matrix.Translation(offset)
        
        # Apply size multiplier
        size = getattr(scene, 'khb_button_size', 1.0)
        alpha = getattr(scene, 'khb_button_alpha', 0.8)
        auto_scale = getattr(scene, 'khb_button_auto_scale', True)
        
        for gizmo in self.gizmos:
            # Calculate final matrix
            final_matrix = obj_matrix @ offset_matrix @ gizmo.matrix_basis
            
            # Apply size scaling
            if auto_scale:
                # Scale based on distance from view
                view_distance = (final_matrix.translation - context.region_data.view_location).length
                scale_factor = max(0.5, min(2.0, view_distance / 10.0))
                size_matrix = Matrix.Scale(size * scale_factor, 4)
            else:
                size_matrix = Matrix.Scale(size, 4)
            
            gizmo.matrix_world = final_matrix @ size_matrix
            
            # Update visual properties
            gizmo.alpha = alpha
            gizmo.alpha_highlight = min(alpha + 0.2, 1.0)

# ================================
# UI INTEGRATION PANELS
# ================================

class KHB_PT_ButtonSystemPanel(Panel):
    """KeyHabit Button System Main Panel"""
    bl_label = "Button System"
    bl_idname = "KHB_PT_button_system_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "KeyHabit"
    bl_order = 0
    
    def draw_header(self, context):
        """Draw panel header with system toggle"""
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "khb_button_system_enabled", text="", icon='GIZMO')
    
    def draw(self, context):
        """Draw main panel content"""
        layout = self.layout
        scene = context.scene
        
        # System status
        col = layout.column(align=True)
        
        # Main enable toggle
        row = col.row()
        row.scale_y = 1.2
        row.prop(scene, "khb_button_system_enabled", toggle=True, 
                text="🎯 Button System Active" if scene.khb_button_system_enabled 
                else "⚫ Enable Button System")
        
        if not scene.khb_button_system_enabled:
            col.label(text="Enable system to access controls", icon='INFO')
            return
        
        # Status info
        col.separator()
        
        # Button set selection
        box = layout.box()
        box.label(text="Active Button Set:", icon='TOOL_SETTINGS')
        box.prop(scene, "khb_active_buttons", text="")
        
        # Layout controls
        box = layout.box()
        box.label(text="Layout Configuration:", icon='ORIENTATION_GIMBAL')
        
        col = box.column(align=True)
        col.prop(scene, "khb_button_layout", text="Pattern")
        
        if scene.khb_button_layout != 'HIDDEN':
            col.separator(factor=0.5)
            
            # Size and position
            row = col.row(align=True)
            row.prop(scene, "khb_button_size", text="Size")
            row.prop(scene, "khb_button_alpha", text="Alpha")
            
            # Position offset
            col.prop(scene, "khb_button_offset", text="Offset")
            
            # Visual options
            col.separator()
            col.prop(scene, "khb_button_show_labels")
            col.prop(scene, "khb_button_auto_scale")

class KHB_PT_ButtonQuickActionsPanel(Panel):
    """Quick Actions Panel"""
    bl_label = "Quick Actions"
    bl_idname = "KHB_PT_button_quick_actions_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "KeyHabit"
    bl_parent_id = "KHB_PT_button_system_panel"
    bl_order = 1
    
    @classmethod
    def poll(cls, context):
        """Only show when button system is enabled"""
        return getattr(context.scene, 'khb_button_system_enabled', False)
    
    def draw(self, context):
        """Draw quick action buttons"""
        layout = self.layout
        scene = context.scene
        
        # Quick action buttons organized by category
        categories = {
            'Animation': ['KEYFRAME_ADD', 'KEYFRAME_DELETE'],
            'Transform': ['TRANSFORM_RESET', 'TRANSFORM_COPY', 'TRANSFORM_PASTE'],
            'Selection': ['SELECT_SIMILAR'],
            'Modeling': ['MODIFIER_ADD', 'MATERIAL_ASSIGN']
        }
        
        for category, actions in categories.items():
            box = layout.box()
            box.label(text=f"{category}:", icon=self.get_category_icon(category))
            
            if len(actions) <= 2:
                row = box.row(align=True)
                for action in actions:
                    config = KHB_BUTTON_ACTIONS.get(action, {})
                    row.operator("khb.button_action", 
                               text=config.get('label', action),
                               icon=config.get('icon', 'NONE')).action_type = action
            else:
                col = box.column(align=True)
                for action in actions:
                    config = KHB_BUTTON_ACTIONS.get(action, {})
                    col.operator("khb.button_action",
                               text=config.get('label', action),
                               icon=config.get('icon', 'NONE')).action_type = action
    
    def get_category_icon(self, category):
        """Get icon for category"""
        icons = {
            'Animation': 'ANIM',
            'Transform': 'OBJECT_ORIGIN',
            'Selection': 'RESTRICT_SELECT_OFF',
            'Modeling': 'MODIFIER'
        }
        return icons.get(category, 'NONE')

class KHB_PT_ButtonAdvancedPanel(Panel):
    """Advanced Button System Settings"""
    bl_label = "Advanced Settings"
    bl_idname = "KHB_PT_button_advanced_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "KeyHabit"
    bl_parent_id = "KHB_PT_button_system_panel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2
    
    @classmethod
    def poll(cls, context):
        """Only show when button system is enabled"""
        return getattr(context.scene, 'khb_button_system_enabled', False)
    
    def draw(self, context):
        """Draw advanced settings"""
        layout = self.layout
        scene = context.scene
        
        # Performance settings
        box = layout.box()
        box.label(text="Performance:", icon='PREFERENCES')
        col = box.column(align=True)
        col.prop(scene, "khb_button_auto_scale")
        
        # Debug information
        box = layout.box()
        box.label(text="System Info:", icon='INFO')
        col = box.column(align=True)
        
        # System status
        col.label(text=f"Version: {KHB_BUTTON_VERSION}")
        col.label(text=f"Active Object: {context.active_object.name if context.active_object else 'None'}")
        col.label(text=f"Mode: {context.mode}")
        
        button_count = len(KHB_BUTTON_ACTIONS)
        layout_count = len(KHB_LAYOUTS)
        col.label(text=f"Available Buttons: {button_count}")
        col.label(text=f"Layout Options: {layout_count}")
        
        # Reset button
        col.separator()
        col.operator("khb.reset_button_system", icon='LOOP_BACK')

# ================================
# UTILITY OPERATORS
# ================================

class KHB_OT_ResetButtonSystem(Operator):
    """Reset Button System to Defaults"""
    bl_idname = "khb.reset_button_system"
    bl_label = "Reset Button System"
    bl_description = "Reset all button system settings to default values"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Reset all button system properties"""
        scene = context.scene
        
        # Reset to default values
        scene.khb_button_system_enabled = False
        scene.khb_button_layout = 'CIRCULAR'
        scene.khb_button_size = 1.0
        scene.khb_button_offset = (0.0, 0.0, 2.0)
        scene.khb_button_alpha = 0.8
        scene.khb_button_show_labels = True
        scene.khb_button_auto_scale = True
        scene.khb_active_buttons = 'ANIMATION'
        
        # Clear temporary data
        scene.khb_temp_location = (0.0, 0.0, 0.0)
        scene.khb_temp_rotation = (0.0, 0.0, 0.0)
        scene.khb_temp_scale = (1.0, 1.0, 1.0)
        
        self.report({'INFO'}, "Button system reset to defaults")
        return {'FINISHED'}

# ================================
# HELPER FUNCTIONS
# ================================

def khb_refresh_button_gizmos(context):
    """Force refresh button gizmos"""
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    area.tag_redraw()

def khb_is_button_system_available():
    """Check if button system is available"""
    try:
        # Check if required Blender version
        return bpy.app.version >= (3, 0, 0)
    except:
        return False

def khb_get_system_info():
    """Get system information dictionary"""
    return {
        'version': KHB_BUTTON_VERSION,
        'button_count': len(KHB_BUTTON_ACTIONS),
        'layout_count': len(KHB_LAYOUTS),
        'available': khb_is_button_system_available()
    }

# ================================
# REGISTRATION
# ================================

# Classes to register
KHB_BUTTON_CLASSES = [
    # Operators
    KHB_OT_ButtonAction,
    KHB_OT_ResetButtonSystem,
    # Gizmos
    KHB_GT_ButtonGizmo,
    KHB_GGT_ButtonGroup,
    # UI Panels
    KHB_PT_ButtonSystemPanel,
    KHB_PT_ButtonQuickActionsPanel, 
    KHB_PT_ButtonAdvancedPanel,
]

def khb_register_button_system():
    """Register button system components"""
    print(f"🎯 KeyHabit Button System v{KHB_BUTTON_VERSION}: Registering...")
    
    # Register properties first
    khb_register_button_properties()
    
    # Register classes
    for cls in KHB_BUTTON_CLASSES:
        try:
            bpy.utils.register_class(cls)
            print(f"✅ Registered: {cls.__name__}")
        except ValueError as e:
            print(f"❌ Failed to register {cls.__name__}: {e}")
    
    print("🎯 KeyHabit Button System: Registration complete!")

def khb_unregister_button_system():
    """Unregister button system components"""
    print("🛑 KeyHabit Button System: Unregistering...")
    
    # Unregister classes in reverse order
    for cls in reversed(KHB_BUTTON_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError as e:
            print(f"⚠️ Failed to unregister {cls.__name__}: {e}")
    
    # Unregister properties
    khb_unregister_button_properties()
    
    print("👋 KeyHabit Button System: Unregistration complete!")

def khb_unregister_button_properties():
    """Unregister button system properties"""
    props_to_remove = [
        'khb_button_system_enabled',
        'khb_button_layout',
        'khb_button_size', 
        'khb_button_offset',
        'khb_button_alpha',
        'khb_button_show_labels',
        'khb_button_auto_scale',
        'khb_active_buttons',
        'khb_temp_location',
        'khb_temp_rotation',
        'khb_temp_scale'
    ]
    
    for prop_name in props_to_remove:
        try:
            delattr(bpy.types.Scene, prop_name)
        except AttributeError:
            pass

# ================================
# INTEGRATION WITH KEYHABIT MAIN
# ================================

def register():
    """Main registration function - called by KeyHabit __init__.py"""
    print(f"🎯 KeyHabit Button System v1.0.0: Registering...")
    # Register properties first
    khb_register_button_properties()
    # Register classes
    for cls in KHB_BUTTON_CLASSES:
        try:
            bpy.utils.register_class(cls)
        except ValueError: # Ignore re-registration errors
            pass
    print("🎯 KeyHabit Button System: Registration complete!")

def unregister():
    """Main unregistration function - called by KeyHabit __init__.py"""
    print("🛑 KeyHabit Button System: Unregistering...")
    # Unregister classes
    for cls in reversed(KHB_BUTTON_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError: pass
    # Unregister properties
    khb_unregister_button_properties()
    print("👋 KeyHabit Button System: Unregistration complete!")

# For testing this module independently
if __name__ == "__main__":
    register()

"""
KeyHabit Button System Integration Notes:

1. INTEGRATION:
   - Add `from . import KHB_Button` to KeyHabit __init__.py
   - Call `KHB_Button.register()` in main register()
   - Call `KHB_Button.unregister()` in main unregister()

2. USAGE:
   - Enable system via panel header toggle
   - Configure layout and appearance in main panel
   - Use quick action buttons for immediate access
   - Gizmos appear in viewport when enabled

3. FEATURES:
   - 🎯 Multiple button layouts (circular, linear, grid, vertical)
   - 🔧 Customizable size, position, transparency
   - 🎨 Color-coded buttons with icons and labels
   - ⚡ Quick action panel integration
   - 🎮 Full gizmo interaction in viewport
   - 💾 Settings saved with .blend file

4. COMPATIBILITY:
   - Integrates seamlessly with existing KeyHabit system
   - Uses KeyHabit naming conventions (khb_ prefix)
   - Follows KeyHabit panel structure and styling
   - Compatible with Blender 3.0+ (gizmo system requirement)
"""
