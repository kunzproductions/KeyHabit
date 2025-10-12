"""
KHB_Display - KeyHabit Display System
Complete modifier overlay with PNG icons and control buttons
Version: 1.0.2-complete
"""

import bpy
from bpy.types import Operator
import bpy.utils.previews
import blf
import math
import gpu
from gpu_extras.batch import batch_for_shader
import os
from pathlib import Path

# ==== CONSTANTS ====
KHB_DISPLAY_VERSION = "1.0.2-complete"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18
KHB_BUTTON_SIZE = 32
KHB_BUTTON_GAP = 10

# ==== COLOR SCHEME ====
class KHB_DisplayColors:
    """Centralized color management"""
    BOX = (1.0, 0.45, 0.0, 1.0)      # Cam ngoặc vuông
    LABEL = (1.0, 0.45, 0.0, 1.0)    # Cam tiêu đề
    VALUE = (0.85, 0.92, 0.4, 1.0)   # Xanh lá nhãn thông số  
    NUMBER = (1.0, 1.0, 1.0, 1.0)    # Trắng giá trị
    ACTIVE = (0.2, 0.6, 1.0, 1.0)    # Xanh dương trạng thái bật
    INACTIVE = (1.0, 0.25, 0.17, 1.0) # Đỏ trạng thái tắt
    FUNCTION = (1.0, 0.45, 0.0, 1.0) # Cam function
    SOURCE = (1.0, 1.0, 1.0, 1.0)    # Trắng source object

# ==== MODIFIER ICON MAPPING ====
KHB_MODIFIER_ICONS = {
    # Generate
    'ARRAY': 'blender_icon_mod_array.png',
    'BEVEL': 'blender_icon_mod_bevel.png', 
    'BOOLEAN': 'blender_icon_mod_boolean.png',
    'BUILD': 'blender_icon_mod_build.png',
    'DECIMATE': 'blender_icon_mod_decim.png',
    'EDGE_SPLIT': 'blender_icon_mod_edgesplit.png',
    'MASK': 'blender_icon_mod_mask.png',
    'MIRROR': 'blender_icon_mod_mirror.png',
    'MULTIRES': 'blender_icon_mod_multires.png',
    'REMESH': 'blender_icon_mod_remesh.png',
    'SCREW': 'blender_icon_mod_screw.png',
    'SKIN': 'blender_icon_mod_skin.png',
    'SOLIDIFY': 'blender_icon_mod_solidify.png',
    'SUBSURF': 'blender_icon_mod_subsurf.png',
    'TRIANGULATE': 'blender_icon_mod_triangulate.png',
    'WELD': 'blender_icon_mod_weld.png',
    'WIREFRAME': 'blender_icon_mod_wireframe.png',
    
    # Deform
    'CAST': 'blender_icon_mod_cast.png',
    'CURVE': 'blender_icon_mod_curve.png',
    'DISPLACE': 'blender_icon_mod_displace.png',
    'LATTICE': 'blender_icon_mod_lattice.png',
    'MESH_DEFORM': 'blender_icon_mod_meshdeform.png',
    'SHRINKWRAP': 'blender_icon_mod_shrinkwrap.png',
    'SIMPLE_DEFORM': 'blender_icon_mod_simpledeform.png',
    'SMOOTH': 'blender_icon_mod_smooth.png',
    'SURFACE_DEFORM': 'blender_icon_mod_meshdeform.png',
    
    # Modify
    'DATA_TRANSFER': 'blender_icon_mod_data_transfer.png',
    'NORMAL_EDIT': 'blender_icon_mod_normaledit.png',
    'UV_PROJECT': 'blender_icon_mod_uvproject.png',
    
    # Physics
    'CLOTH': 'blender_icon_mod_cloth.png',
    'DYNAMIC_PAINT': 'blender_icon_mod_dynamicpaint.png',
    'FLUID': 'blender_icon_mod_fluidsim.png',
    'OCEAN': 'blender_icon_mod_ocean.png',
    'PARTICLE_INSTANCE': 'blender_icon_mod_particle_instance.png',
    'PARTICLE_SYSTEM': 'blender_icon_mod_particles.png',
    'SOFT_BODY': 'blender_icon_mod_soft.png',
    
    # Special
    'NODES': 'blender_icon_geometry_nodes.png',
}

KHB_FALLBACK_ICON = 'blender_icon_question.png'

# ==== ICON MANAGER ====
class KHB_IconManager:
    """PNG icon loading and management system"""
    
    def __init__(self):
        self.pcoll = None
        self.icons_loaded = False
    
    def khb_load_icons(self):
        """Load all modifier PNG icons"""
        if self.icons_loaded:
            return True
        
        try:
            # Cleanup existing
            self.khb_cleanup()
            
            # Create new preview collection
            self.pcoll = bpy.utils.previews.new()
            
            # Get icons directory
            addon_dir = Path(__file__).parent
            icons_dir = addon_dir / "icons"
            
            if not icons_dir.exists():
                print(f"❌ KHB_Display: Icons directory not found: {icons_dir}")
                return False
            
            loaded_count = 0
            
            # Load fallback icon first
            fallback_path = icons_dir / KHB_FALLBACK_ICON
            if fallback_path.exists():
                self.pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
                loaded_count += 1
                print("✅ KHB_Display: Loaded fallback icon")
            
            # Load all modifier icons
            for mod_type, filename in KHB_MODIFIER_ICONS.items():
                icon_path = icons_dir / filename
                if icon_path.exists():
                    try:
                        self.pcoll.load(mod_type, str(icon_path), 'IMAGE')
                        loaded_count += 1
                        # print(f"✅ KHB_Display: Loaded {mod_type} -> {filename}")
                    except Exception as e:
                        print(f"⚠️ KHB_Display: Failed to load {filename} - {e}")
                else:
                    print(f"⚠️ KHB_Display: Missing icon: {filename} for {mod_type}")
            
            self.icons_loaded = True
            print(f"🎨 KHB_Display: Icon system initialized ({loaded_count}/{len(KHB_MODIFIER_ICONS)+1} icons loaded)")
            return True
            
        except Exception as e:
            print(f"❌ KHB_Display: Icon loading failed - {e}")
            return False
    
    def khb_get_texture(self, mod_type):
        """Get GPU texture for modifier type"""
        if not self.icons_loaded:
            self.khb_load_icons()
        
        if not self.pcoll:
            return None
        
        # Try specific icon first
        if mod_type in self.pcoll:
            preview = self.pcoll[mod_type]
            if hasattr(preview, 'icon_id') and preview.icon_id > 0:
                try:
                    if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
                        return gpu.texture.from_icon(preview.icon_id)
                except Exception:
                    pass
        
        # Try fallback icon
        if "FALLBACK" in self.pcoll:
            preview = self.pcoll["FALLBACK"]
            if hasattr(preview, 'icon_id') and preview.icon_id > 0:
                try:
                    if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
                        return gpu.texture.from_icon(preview.icon_id)
                except Exception:
                    pass
        
        return None
    
    def khb_cleanup(self):
        """Cleanup preview collections"""
        if self.pcoll:
            try:
                bpy.utils.previews.remove(self.pcoll)
                print("🧹 KHB_Display: Icon collection cleaned up")
            except Exception as e:
                print(f"⚠️ KHB_Display: Cleanup warning - {e}")
            
            self.pcoll = None
            self.icons_loaded = False

# ==== CONTROL BUTTON SYSTEM ====
class KHB_ControlButton:
    """Individual control button"""
    
    def __init__(self, button_id, x, y, size, operator_idname, tooltip=""):
        self.button_id = button_id
        self.x = x
        self.y = y
        self.size = size
        self.operator_idname = operator_idname
        self.tooltip = tooltip
    
    def khb_hit_test(self, mouse_x, mouse_y):
        """Test if mouse is over button"""
        return (self.x <= mouse_x <= self.x + self.size and
                self.y <= mouse_y <= self.y + self.size)
    
    def khb_execute(self):
        """Execute button operator"""
        try:
            if self.operator_idname == "khb_overlay.toggle_wireframe":
                bpy.ops.khb_overlay.toggle_wireframe()
            elif self.operator_idname == "khb_overlay.toggle_edge_length":
                bpy.ops.khb_overlay.toggle_edge_length()
            elif self.operator_idname == "khb_overlay.toggle_retopology":
                bpy.ops.khb_overlay.toggle_retopology()
            elif self.operator_idname == "khb_overlay.toggle_split_normals":
                bpy.ops.khb_overlay.toggle_split_normals()
        except Exception as e:
            print(f"⚠️ KHB_Display: Button execution failed - {e}")
    
    def khb_get_overlay_state(self):
        """Get current overlay state"""
        try:
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            overlay = space.overlay
                            if self.button_id == 'wireframe':
                                return overlay.show_wireframes
                            elif self.button_id == 'edge_length':
                                return overlay.show_extra_edge_length
                            elif self.button_id == 'retopo':
                                return overlay.show_retopology
                            elif self.button_id == 'split_normals':
                                return overlay.show_split_normals
        except:
            pass
        return False

class KHB_ButtonManager:
    """Manager for control buttons"""
    
    def __init__(self):
        self.buttons = []
        self.settings = {
            'show_buttons': True,
            'button_size': KHB_BUTTON_SIZE,
            'position': 'BOTTOM_LEFT',
        }
        self.initialized = False
    
    def khb_update_settings(self, new_settings):
        """Update button settings"""
        self.settings.update(new_settings)
        self.initialized = False
        self.khb_init_buttons()
    
    def khb_init_buttons(self):
        """Initialize control buttons"""
        if self.initialized or not self.settings.get('show_buttons', True):
            return
        
        self.buttons.clear()
        
        # Button configurations
        button_configs = [
            ('wireframe', 'khb_overlay.toggle_wireframe', 'Toggle Wireframe'),
            ('edge_length', 'khb_overlay.toggle_edge_length', 'Toggle Edge Length'),
            ('retopo', 'khb_overlay.toggle_retopology', 'Toggle Retopology'),
            ('split_normals', 'khb_overlay.toggle_split_normals', 'Toggle Split Normals')
        ]
        
        # Calculate positions
        button_size = self.settings.get('button_size', KHB_BUTTON_SIZE)
        position = self.settings.get('position', 'BOTTOM_LEFT')
        
        if position == 'BOTTOM_LEFT':
            start_x, start_y = 50, 60
        elif position == 'BOTTOM_RIGHT':
            start_x, start_y = 400, 60
        elif position == 'TOP_LEFT':
            start_x, start_y = 50, 300
        else:  # TOP_RIGHT
            start_x, start_y = 400, 300
        
        x = start_x
        
        # Create buttons
        for button_id, operator_id, tooltip in button_configs:
            button = KHB_ControlButton(
                button_id=button_id,
                x=x,
                y=start_y,
                size=button_size,
                operator_idname=operator_id,
                tooltip=tooltip
            )
            self.buttons.append(button)
            x += button_size + KHB_BUTTON_GAP
        
        self.initialized = True
        print(f"🎮 KHB_Display: {len(self.buttons)} control buttons initialized")
    
    def khb_draw_all_buttons(self):
        """Draw all control buttons"""
        if not self.settings.get('show_buttons', True):
            return
        
        if not self.initialized:
            self.khb_init_buttons()
        
        font_id = 0
        blf.size(font_id, 10)
        
        for button in self.buttons:
            self._khb_draw_single_button(button, font_id)
    
    def _khb_draw_single_button(self, button, font_id):
        """Draw individual button"""
        x, y, size = button.x, button.y, button.size
        is_active = button.khb_get_overlay_state()
        
        # Button colors
        if is_active:
            bg_color = (0.2, 0.6, 1.0, 0.8)    # Blue active
            text_color = (1.0, 1.0, 1.0, 1.0)  # White text
        else:
            bg_color = (0.3, 0.3, 0.3, 0.6)    # Gray inactive
            text_color = (0.7, 0.7, 0.7, 1.0)  # Gray text
        
        # Draw background rectangle
        try:
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", bg_color)
            batch.draw(shader)
            gpu.state.blend_set('NONE')
        except Exception as e:
            print(f"⚠️ KHB_Display: Button bg render error - {e}")
        
        # Draw button label
        try:
            label = button.button_id[0].upper()  # First letter
            text_x = x + size // 3
            text_y = y + size // 3
            
            blf.position(font_id, text_x, text_y, 0)
            blf.color(font_id, *text_color)
            blf.draw(font_id, label)
        except Exception as e:
            print(f"⚠️ KHB_Display: Button text render error - {e}")
    
    def khb_handle_click(self, mouse_x, mouse_y):
        """Handle mouse click on buttons"""
        for button in self.buttons:
            if button.khb_hit_test(mouse_x, mouse_y):
                button.khb_execute()
                return True
        return False

# ==== DISPLAY MANAGER ====
class KHB_DisplayManager:
    """Main display system manager"""
    
    def __init__(self):
        self._handler = None
        self._enabled = False
        self._modal_operator = None
    
    def khb_enable_display_system(self):
        """Enable complete display system"""
        if self._enabled:
            print("⚠️ KHB_Display: Already enabled")
            return
        
        try:
            # Load icons
            success = khb_icon_manager.khb_load_icons()
            if not success:
                print("⚠️ KHB_Display: Icon loading failed, continuing with fallback")
            
            # Initialize buttons
            khb_button_manager.khb_init_buttons()
            
            # Add draw handler
            self._handler = bpy.types.SpaceView3D.draw_handler_add(
                self._khb_draw_overlay,
                (),
                'WINDOW',
                'POST_PIXEL'
            )
            
            # Start modal for button interaction
            try:
                bpy.ops.khb_overlay.modal_handler('INVOKE_DEFAULT')
            except Exception as e:
                print(f"⚠️ KHB_Display: Modal handler start failed - {e}")
            
            self._enabled = True
            self.khb_force_redraw()
            
            print("✅ KHB_Display: Complete display system enabled!")
            
        except Exception as e:
            print(f"❌ KHB_Display: Enable failed - {e}")
            self.khb_disable_display_system()
    
    def khb_disable_display_system(self):
        """Disable complete display system"""
        if not self._enabled:
            return
        
        try:
            # Remove draw handler
            if self._handler:
                bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
                self._handler = None
                print("🧹 KHB_Display: Draw handler removed")
            
            # Cleanup icons
            khb_icon_manager.khb_cleanup()
            
            self._enabled = False
            self.khb_force_redraw()
            
            print("❌ KHB_Display: Display system disabled!")
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Disable error - {e}")
            # Force reset state even if error
            self._enabled = False
            self._handler = None
    
    def khb_is_enabled(self):
        """Check if system is enabled"""
        return self._enabled
    
    def khb_force_redraw(self):
        """Force redraw all 3D viewports"""
        try:
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except Exception as e:
            print(f"⚠️ KHB_Display: Force redraw error - {e}")
    
    def _khb_draw_overlay(self):
        """Main overlay drawing function"""
        if not bpy.context.selected_objects:
            return
        
        try:
            font_id = 0
            blf.size(font_id, 12)
            obj = bpy.context.active_object
            y = 15
            
            if obj and obj.type == 'MESH' and obj.modifiers:
                # Draw each modifier
                for modifier in reversed(obj.modifiers):
                    x = 20
                    
                    # Draw modifier icon
                    icon_width = khb_draw_modifier_icon(font_id, x, y, modifier.type)
                    x += icon_width + KHB_ICON_PAD_PX
                    
                    # Draw modifier text
                    text_color_pairs = khb_get_modifier_text(modifier)
                    for text, color in text_color_pairs:
                        blf.position(font_id, x, y, 0)
                        blf.color(font_id, *color)
                        blf.draw(font_id, text)
                        text_w = blf.dimensions(font_id, text)[0]
                        x += int(text_w)
                    
                    y += KHB_LINE_HEIGHT
            else:
                # No mesh/modifiers message
                blf.position(font_id, 20, y, 0)
                blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
                blf.draw(font_id, "No MESH object selected or no modifiers")
            
            # Draw control buttons
            khb_button_manager.khb_draw_all_buttons()
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Overlay draw error - {e}")

# ==== RENDERING FUNCTIONS ====
def khb_draw_modifier_icon(font_id, x, y, mod_type, icon_size=KHB_ICON_SIZE_PX):
    """Draw modifier icon with PNG support"""
    try:
        texture = khb_icon_manager.khb_get_texture(mod_type)
        
        if texture:
            # Draw PNG icon texture
            positions = [(x, y), (x + icon_size, y), (x + icon_size, y + icon_size), (x, y + icon_size)]
            uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
            
            shader = gpu.shader.from_builtin('IMAGE')
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions, "texCoord": uvs})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            
            try:
                shader.uniform_sampler("image", texture)
                batch.draw(shader)
                gpu.state.blend_set('NONE')
                return icon_size
            except Exception:
                gpu.state.blend_set('NONE')
        
        # Fallback: Draw question mark
        blf.size(font_id, int(icon_size * 0.8))
        blf.position(font_id, x, y, 0)
        blf.color(font_id, 0.9, 0.5, 0.1, 1.0)
        blf.draw(font_id, "?")
        return icon_size
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Icon draw error for {mod_type} - {e}")
        return icon_size

def khb_get_modifier_display_name(modifier):
    """Get human-readable modifier name"""
    try:
        enum_prop = bpy.types.Modifier.bl_rna.properties['type']
        return enum_prop.enum_items[modifier.type].name
    except Exception:
        return modifier.type.title().replace('_', ' ')

def khb_get_modifier_text(modifier):
    """Generate text-color pairs for modifier"""
    tc = []
    colors = KHB_DisplayColors()
    
    # Handle Geometry Nodes Auto Smooth
    if (modifier.type == 'NODES' and 
        ("Smooth by Angle" in modifier.name or "Shade Auto Smooth" in modifier.name)):
        
        tc.extend([
            ('[', colors.BOX),
            ('Shade Auto Smooth', colors.LABEL),
            (']', colors.BOX),
            (' ' + modifier.name, colors.NUMBER)
        ])
        
        # Extract angle
        angle_deg = None
        if "Input_1" in modifier.keys():
            angle_deg = round(modifier["Input_1"] * 180 / math.pi, 1)
        
        tc.extend([
            (' Angle:', colors.VALUE),
            (f"{angle_deg if angle_deg is not None else 30.0}°", colors.NUMBER)
        ])
        
        # Extract ignore setting
        if "Socket_1" in modifier.keys() and bool(modifier["Socket_1"]):
            tc.append((' IgnoreSharpness', colors.ACTIVE))
    
    else:
        # Regular modifier
        tc.extend([
            ('[', colors.BOX),
            (khb_get_modifier_display_name(modifier), colors.LABEL),
            (']', colors.BOX),
            (' ' + modifier.name, colors.NUMBER)
        ])
        
        # Modifier-specific details
        if modifier.type == 'MIRROR':
            axes = getattr(modifier, 'use_axis', [False, False, False])
            for i, label in enumerate(['X', 'Y', 'Z']):
                color = colors.ACTIVE if (i < len(axes) and axes[i]) else colors.INACTIVE
                tc.append((' ' + label, color))
            
            mirror_obj = getattr(modifier, 'mirror_object', None)
            if mirror_obj:
                tc.extend([(' Mirror Object:', colors.LABEL), (' ' + mirror_obj.name, colors.SOURCE)])
        
        elif modifier.type == 'BOOLEAN':
            operation = getattr(modifier, 'operation', '')
            solver = getattr(modifier, 'solver', '')
            
            if operation:
                tc.append((' ' + operation, colors.FUNCTION))
            if solver in ['BMESH', 'EXACT']:
                tc.append((' ' + solver, colors.ACTIVE))
            
            source_obj = getattr(modifier, 'object', None)
            if source_obj:
                tc.append((' ' + source_obj.name, colors.SOURCE))
        
        elif modifier.type == 'BEVEL':
            amount = getattr(modifier, 'width', 0)
            segments = getattr(modifier, 'segments', 0)
            tc.extend([
                (' Amount:', colors.VALUE), (f"{amount:.3f}", colors.NUMBER),
                (' Segments:', colors.VALUE), (f"{segments}", colors.NUMBER)
            ])
            
        elif modifier.type == 'ARRAY':
            count = getattr(modifier, 'count', 0)
            tc.extend([(' ×', colors.VALUE), (f"{count}", colors.NUMBER)])
        
        elif modifier.type == 'SOLIDIFY':
            thickness = getattr(modifier, 'thickness', 0)
            tc.extend([(' T:', colors.VALUE), (f"{thickness:.3f}", colors.NUMBER)])
        
        elif modifier.type == 'SUBSURF':
            levels = getattr(modifier, 'levels', 0)
            tc.extend([(' Lv', colors.VALUE), (f"{levels}", colors.NUMBER)])
        
        elif modifier.type == 'DISPLACE':
            strength = getattr(modifier, 'strength', 0)
            tc.extend([(' Strength:', colors.VALUE), (f"{strength:.3f}", colors.NUMBER)])
        
        elif modifier.type == 'DATA_TRANSFER':
            source_obj = getattr(modifier, 'object', None)
            if source_obj:
                tc.extend([(' ← ', colors.VALUE), (source_obj.name, colors.NUMBER)])
        
        elif modifier.type == 'SHRINKWRAP':
            target_obj = getattr(modifier, 'target', None)
            if target_obj:
                tc.extend([(' → ', colors.VALUE), (target_obj.name, colors.NUMBER)])
    
    return tc

# ==== OVERLAY OPERATORS ====
class KHB_OVERLAY_OT_toggle_wireframe(Operator):
    """Toggle Wireframe Overlay"""
    bl_idname = "khb_overlay.toggle_wireframe"
    bl_label = "Toggle Wireframe Overlay"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_wireframes = not space.overlay.show_wireframes
                        area.tag_redraw()
        return {'FINISHED'}

class KHB_OVERLAY_OT_toggle_edge_length(Operator):
    """Toggle Edge Length Display"""
    bl_idname = "khb_overlay.toggle_edge_length"
    bl_label = "Toggle Edge Length"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_extra_edge_length = not space.overlay.show_extra_edge_length
                        area.tag_redraw()
        return {'FINISHED'}

class KHB_OVERLAY_OT_toggle_retopology(Operator):
    """Toggle Retopology Overlay"""
    bl_idname = "khb_overlay.toggle_retopology"
    bl_label = "Toggle Retopology"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_retopology = not space.overlay.show_retopology
                        area.tag_redraw()
        return {'FINISHED'}

class KHB_OVERLAY_OT_toggle_split_normals(Operator):
    """Toggle Split Normals Display"""
    bl_idname = "khb_overlay.toggle_split_normals"
    bl_label = "Toggle Split Normals"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_split_normals = not space.overlay.show_split_normals
                        area.tag_redraw()
        return {'FINISHED'}

class KHB_OVERLAY_OT_modal_handler(Operator):
    """Modal operator for button interactions"""
    bl_idname = "khb_overlay.modal_handler"
    bl_label = "KHB Overlay Modal Handler"
    
    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y
            
            # Handle button clicks
            if khb_button_manager.khb_handle_click(mouse_x, mouse_y):
                khb_display_manager.khb_force_redraw()
                return {'RUNNING_MODAL'}
        
        if event.type == 'ESC':
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

# ==== GLOBAL INSTANCES (CRITICAL!) ====
khb_icon_manager = KHB_IconManager()
khb_button_manager = KHB_ButtonManager()
khb_display_manager = KHB_DisplayManager()

# ==== REGISTRATION ====
khb_display_classes = (
    KHB_OVERLAY_OT_toggle_wireframe,
    KHB_OVERLAY_OT_toggle_edge_length,
    KHB_OVERLAY_OT_toggle_retopology,
    KHB_OVERLAY_OT_toggle_split_normals,
    KHB_OVERLAY_OT_modal_handler,
)

def register():
    """Register display system"""
    for cls in khb_display_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"❌ KHB_Display: Class registration failed {cls.__name__} - {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Registered")

def unregister():
    """Unregister with complete cleanup"""
    print("🛑 KHB_Display: Starting unregistration...")
    
    # Force disable system
    try:
        khb_display_manager.khb_disable_display_system()
    except Exception as e:
        print(f"⚠️ KHB_Display: Force disable error - {e}")
    
    # Force cleanup global state
    try:
        if khb_display_manager._handler:
            bpy.types.SpaceView3D.draw_handler_remove(khb_display_manager._handler, 'WINDOW')
        khb_icon_manager.khb_cleanup()
    except Exception as e:
        print(f"⚠️ KHB_Display: Force cleanup error - {e}")
    
    # Unregister classes
    for cls in reversed(khb_display_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KHB_Display: Class unregistration error - {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistered")

if __name__ == "__main__":
    register()
    # Auto-enable for testing
    khb_display_manager.khb_enable_display_system()
