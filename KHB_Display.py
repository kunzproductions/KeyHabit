"""
KeyHabit Display System
Overlay hiển thị modifier info với PNG icons + Control buttons
"""

import bpy
from bpy.types import Operator, PropertyGroup
import bpy.utils.previews
import blf
import math
import gpu
from gpu_extras.batch import batch_for_shader
import os
from pathlib import Path

# ==== GLOBAL CONSTANTS ====
KBH_DISPLAY_VERSION = "1.0.0"
KBH_ICON_SIZE_PX = 16
KBH_ICON_PAD_PX = 4
KBH_LINE_HEIGHT = 18
KBH_BUTTON_SIZE = 32
KBH_BUTTON_GAP = 10

# ==== COLOR SCHEME ====
class KBH_DisplayColors:
    """Centralized color management cho display system"""
    BOX = (1.0, 0.45, 0.0, 1.0)      # Cam ngoặc vuông
    LABEL = (1.0, 0.45, 0.0, 1.0)    # Cam tiêu đề
    VALUE = (0.85, 0.92, 0.4, 1.0)   # Xanh lá nhãn thông số  
    NUMBER = (1.0, 1.0, 1.0, 1.0)    # Trắng giá trị
    ACTIVE = (0.2, 0.6, 1.0, 1.0)    # Xanh dương trạng thái bật
    INACTIVE = (1.0, 0.25, 0.17, 1.0) # Đỏ trạng thái tắt
    FUNCTION = (1.0, 0.45, 0.0, 1.0) # Cam function
    SOURCE = (1.0, 1.0, 1.0, 1.0)    # Trắng source object

# ==== ICON MAPPING ====
KBH_MODIFIER_ICONS = {
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

KBH_FALLBACK_ICON = 'blender_icon_question.png'

# ==== ICON MANAGER CLASS ====
class KBH_IconManager:
    """Quản lý hệ thống PNG icons cho modifier display"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.preview_collections = {}
            self.pcoll = None
            self.icons_loaded = False
            self.__class__._initialized = True
    
    def khb_load_modifier_icons(self):
        """Load tất cả modifier icons từ thư mục icons/"""
        if self.icons_loaded:
            return True
            
        try:
            # Cleanup existing collection
            self._khb_cleanup_existing_collection()
            
            # Create new preview collection
            pcoll = bpy.utils.previews.new()
            
            # Get addon directory
            addon_dir = Path(__file__).parent
            icons_dir = addon_dir / "icons"
            
            if not icons_dir.exists():
                print(f"❌ KBH_Display: Icons directory not found: {icons_dir}")
                return False
            
            # Load fallback icon first
            fallback_path = icons_dir / KBH_FALLBACK_ICON
            if fallback_path.exists():
                pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
                print(f"✅ KBH_Display: Loaded fallback icon")
            
            # Load modifier icons
            loaded_count = 0
            for mod_type, filename in KBH_MODIFIER_ICONS.items():
                icon_path = icons_dir / filename
                if icon_path.exists():
                    pcoll.load(mod_type, str(icon_path), 'IMAGE')
                    loaded_count += 1
                else:
                    print(f"⚠️ KBH_Display: Missing icon: {filename} for {mod_type}")
            
            # Store collection
            self.preview_collections["khb_display_icons"] = pcoll
            self.pcoll = pcoll
            self.icons_loaded = True
            
            print(f"🎨 KBH_Display: Icon system initialized ({loaded_count}/{len(KBH_MODIFIER_ICONS)} icons loaded)")
            return True
            
        except Exception as e:
            print(f"❌ KBH_Display: Failed to load icons - {e}")
            return False
    
    def khb_get_modifier_texture(self, mod_type):
        """Lấy GPU texture cho modifier type"""
        if not self.icons_loaded:
            if not self.khb_load_modifier_icons():
                return None
                
        if self.pcoll is None:
            return None
        
        # Try get specific icon
        if mod_type in self.pcoll:
            preview = self.pcoll[mod_type]
            texture = self._khb_convert_preview_to_texture(preview)
            if texture:
                return texture
        
        # Try fallback icon  
        if "FALLBACK" in self.pcoll:
            preview = self.pcoll["FALLBACK"]
            return self._khb_convert_preview_to_texture(preview)
        
        return None
    
    def _khb_convert_preview_to_texture(self, preview):
        """Convert preview icon thành GPU texture"""
        try:
            if hasattr(preview, 'icon_id') and preview.icon_id > 0:
                if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
                    return gpu.texture.from_icon(preview.icon_id)
        except Exception as e:
            print(f"⚠️ KBH_Display: Texture conversion failed - {e}")
        return None
    
    def _khb_cleanup_existing_collection(self):
        """Cleanup existing preview collection"""
        if "khb_display_icons" in self.preview_collections:
            bpy.utils.previews.remove(self.preview_collections["khb_display_icons"])
            del self.preview_collections["khb_display_icons"]
    
    def khb_cleanup_all(self):
        """Dọn dẹp tất cả preview collections"""
        for pcoll in self.preview_collections.values():
            bpy.utils.previews.remove(pcoll)
        self.preview_collections.clear()
        self.icons_loaded = False
        self.pcoll = None

# Global icon manager instance
khb_icon_manager = KBH_IconManager()

# ==== GPU RENDERING UTILITIES ====
class KBH_GPURenderer:
    """Utilities cho GPU rendering"""
    
    _image_shader = None
    
    @classmethod
    def khb_get_image_shader(cls):
        """Get cached image shader"""
        if cls._image_shader is None:
            cls._image_shader = gpu.shader.from_builtin('IMAGE')
        return cls._image_shader
    
    @classmethod
    def khb_draw_texture_rect(cls, texture, x, y, width, height):
        """Vẽ texture rectangle lên screen"""
        if texture is None:
            return 0
        
        try:
            # Setup geometry
            positions = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
            uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
            
            shader = cls.khb_get_image_shader()
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions, "texCoord": uvs})
            
            # Render
            gpu.state.blend_set('ALPHA')
            shader.bind()
            
            # Bind texture (multiple methods for compatibility)
            try:
                shader.uniform_sampler("image", texture)
            except:
                try:
                    texture.bind(0)
                except:
                    gpu.state.blend_set('NONE')
                    return 0
            
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            return width
            
        except Exception as e:
            print(f"⚠️ KBH_Display: Texture rendering failed - {e}")
            gpu.state.blend_set('NONE')
            return 0
    
    @classmethod
    def khb_draw_rounded_rect(cls, x, y, width, height, color, radius=4):
        """Vẽ rounded rectangle background"""
        try:
            # Simplified rounded rect (just regular rect for now)
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", color)
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            
        except Exception as e:
            print(f"⚠️ KBH_Display: Rectangle drawing failed - {e}")

# ==== MODIFIER TEXT PROCESSOR ====
class KBH_ModifierProcessor:
    """Xử lý thông tin modifier thành text + color"""
    
    @staticmethod
    def khb_get_modifier_display_name(modifier):
        """Lấy tên hiển thị của modifier"""
        try:
            enum_prop = bpy.types.Modifier.bl_rna.properties['type']
            return enum_prop.enum_items[modifier.type].name
        except:
            return modifier.type.title().replace('_', ' ')
    
    @staticmethod
    def khb_process_modifier_info(modifier):
        """
        Xử lý modifier thành list (text, color) pairs
        Returns: List[Tuple[str, Tuple[float, float, float, float]]]
        """
        text_color_pairs = []
        colors = KBH_DisplayColors()
        
        # ===== Geometry Nodes Auto Smooth =====
        if (modifier.type == 'NODES' and 
            ("Smooth by Angle" in modifier.name or "Shade Auto Smooth" in modifier.name)):
            
            text_color_pairs.extend([
                ('[', colors.BOX),
                ('Shade Auto Smooth', colors.LABEL),
                (']', colors.BOX),
                (' ' + modifier.name, colors.NUMBER)
            ])
            
            # Extract angle and ignore values
            angle_deg = None
            ignore_val = None
            
            if "Input_1" in modifier.keys():
                angle_deg = round(modifier["Input_1"] * 180 / math.pi, 1)
            if "Socket_1" in modifier.keys():
                ignore_val = bool(modifier["Socket_1"])
            
            text_color_pairs.extend([
                (' Angle:', colors.VALUE),
                (f"{angle_deg if angle_deg is not None else 0.0}°", colors.NUMBER)
            ])
            
            if ignore_val:
                text_color_pairs.append((' IgnoreSharpness', colors.ACTIVE))
        
        else:
            # Regular modifier
            text_color_pairs.extend([
                ('[', colors.BOX),
                (KBH_ModifierProcessor.khb_get_modifier_display_name(modifier), colors.LABEL),
                (']', colors.BOX),
                (' ' + modifier.name, colors.NUMBER)
            ])
            
            # Specific modifier parameters
            text_color_pairs.extend(
                KBH_ModifierProcessor._khb_get_modifier_specific_info(modifier, colors)
            )
        
        return text_color_pairs
    
    @staticmethod
    def _khb_get_modifier_specific_info(modifier, colors):
        """Lấy thông tin specific cho từng loại modifier"""
        info_pairs = []
        
        if modifier.type == 'MIRROR':
            axes = getattr(modifier, 'use_axis', [False, False, False])
            for i, label in enumerate(['X', 'Y', 'Z']):
                color = colors.ACTIVE if (i < len(axes) and axes[i]) else colors.INACTIVE
                info_pairs.append((' ' + label, color))
            
            mirror_obj = getattr(modifier, 'mirror_object', None)
            if mirror_obj:
                info_pairs.extend([
                    (' Mirror Object:', colors.LABEL),
                    (' ' + mirror_obj.name, colors.SOURCE)
                ])
        
        elif modifier.type == 'BOOLEAN':
            operation = getattr(modifier, 'operation', '')
            solver = getattr(modifier, 'solver', '')
            
            if operation:
                info_pairs.append((' ' + operation, colors.FUNCTION))
            if solver in ['BMESH', 'EXACT']:
                info_pairs.append((' ' + solver, colors.ACTIVE))
            
            source_obj = getattr(modifier, 'object', None)
            if source_obj:
                info_pairs.append((' ' + source_obj.name, colors.SOURCE))
        
        elif modifier.type == 'BEVEL':
            amount = getattr(modifier, 'width', 0)
            segments = getattr(modifier, 'segments', 0)
            
            info_pairs.extend([
                (' Amount:', colors.VALUE),
                (f"{amount:.3f}", colors.NUMBER),
                (' Segment:', colors.VALUE),
                (f"{segments}", colors.NUMBER)
            ])
            
            vertex_group = getattr(modifier, 'vertex_group', '')
            limit_method = getattr(modifier, 'limit_method', '')
            
            if vertex_group:
                info_pairs.extend([(' VG:', colors.VALUE), (vertex_group, colors.NUMBER)])
            if limit_method in ['ANGLE', 'WEIGHT']:
                info_pairs.append((' ' + limit_method, colors.ACTIVE))
        
        elif modifier.type == 'ARRAY':
            count = getattr(modifier, 'count', 0)
            info_pairs.extend([(' ×', colors.VALUE), (f"{count}", colors.NUMBER)])
        
        elif modifier.type == 'SOLIDIFY':
            thickness = getattr(modifier, 'thickness', 0)
            info_pairs.extend([(' T:', colors.VALUE), (f"{thickness:.3f}", colors.NUMBER)])
            
            vertex_group = getattr(modifier, 'vertex_group', '')
            if vertex_group:
                info_pairs.extend([(' VG:', colors.VALUE), (vertex_group, colors.NUMBER)])
        
        elif modifier.type == 'SUBSURF':
            levels = getattr(modifier, 'levels', 0)
            info_pairs.extend([(' Lv', colors.VALUE), (f"{levels}", colors.NUMBER)])
        
        elif modifier.type == 'DISPLACE':
            strength = getattr(modifier, 'strength', 0)
            info_pairs.extend([(' Strength:', colors.VALUE), (f"{strength:.3f}", colors.NUMBER)])
            
            vertex_group = getattr(modifier, 'vertex_group', '')
            if vertex_group:
                info_pairs.extend([(' VG:', colors.VALUE), (vertex_group, colors.NUMBER)])
        
        elif modifier.type == 'DATA_TRANSFER':
            source_obj = getattr(modifier, 'object', None)
            if source_obj:
                info_pairs.extend([(' ← ', colors.VALUE), (source_obj.name, colors.NUMBER)])
        
        elif modifier.type == 'SHRINKWRAP':
            target_obj = getattr(modifier, 'target', None)
            if target_obj:
                info_pairs.extend([(' → ', colors.VALUE), (target_obj.name, colors.NUMBER)])
            
            vertex_group = getattr(modifier, 'vertex_group', '')
            if vertex_group:
                info_pairs.extend([(' VG:', colors.VALUE), (vertex_group, colors.NUMBER)])
        
        return info_pairs

# ==== CONTROL BUTTON SYSTEM ====
class KBH_ControlButton:
    """Control button cho overlay toggles"""
    
    def __init__(self, button_id, x, y, size, operator_idname, tooltip="", icon_name=""):
        self.button_id = button_id
        self.x = x
        self.y = y  
        self.size = size
        self.operator_idname = operator_idname
        self.tooltip = tooltip
        self.icon_name = icon_name
        self.is_hovered = False
    
    def khb_hit_test(self, mouse_x, mouse_y):
        """Test mouse click hit"""
        return (self.x <= mouse_x <= self.x + self.size and
                self.y <= mouse_y <= self.y + self.size)
    
    def khb_execute_operator(self):
        """Execute button operator"""
        try:
            operator = getattr(bpy.ops, self.operator_idname.split('.')[0])
            getattr(operator, self.operator_idname.split('.')[1])()
        except Exception as e:
            print(f"⚠️ KBH_Display: Button execution failed - {e}")
    
    def khb_get_overlay_state(self):
        """Get current overlay state for this button"""
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

class KBH_ButtonManager:
    """Manager cho control buttons"""
    
    def __init__(self):
        self.buttons = []
        self.initialized = False
        self.settings = {
            'show_buttons': True,
            'button_size': 32,
            'position': 'BOTTOM_LEFT',
        }
    
    def khb_update_settings(self, new_settings):
        """Update button settings from preferences"""
        self.settings.update(new_settings)
        
        # Re-initialize buttons with new settings
        if self.initialized:
            self.initialized = False
            self.khb_initialize_buttons()
    
    def khb_initialize_buttons(self):
        """Initialize control buttons với settings"""
        if self.initialized:
            return
        
        self.buttons.clear()
        
        # Skip if buttons disabled
        if not self.settings.get('show_buttons', True):
            return
        
        # Button configuration
        button_configs = [
            ('wireframe', 'khb_overlay.toggle_wireframe', 'Toggle Wireframe', ''),
            ('edge_length', 'khb_overlay.toggle_edge_length', 'Toggle Edge Length', ''),
            ('retopo', 'khb_overlay.toggle_retopology', 'Toggle Retopology', ''),
            ('split_normals', 'khb_overlay.toggle_split_normals', 'Toggle Split Normals', '')
        ]
        
        # Calculate position based on settings
        button_size = self.settings.get('button_size', KBH_BUTTON_SIZE)
        position = self.settings.get('position', 'BOTTOM_LEFT')
        
        if position == 'BOTTOM_LEFT':
            start_x, start_y = 50, 60
        elif position == 'BOTTOM_RIGHT':
            # Calculate from right edge (approximate)
            start_x, start_y = 400, 60  
        elif position == 'TOP_LEFT':
            start_x, start_y = 50, 300
        elif position == 'TOP_RIGHT':
            start_x, start_y = 400, 300
        else:
            start_x, start_y = 50, 60
        
        x = start_x
        
        for button_id, operator_id, tooltip, icon in button_configs:
            button = KBH_ControlButton(
                button_id=button_id,
                x=x,
                y=start_y,
                size=button_size,
                operator_idname=operator_id,
                tooltip=tooltip,
                icon_name=icon
            )
            self.buttons.append(button)
            x += button_size + KBH_BUTTON_GAP
        
        self.initialized = True
    
    
    def khb_draw_all_buttons(self):
        """Vẽ tất cả control buttons"""
        # Check if buttons should be shown
        if not self.settings.get('show_buttons', True):
            return
            
        if not self.initialized:
            self.khb_initialize_buttons()
        
        font_id = 0
        blf.size(font_id, 10)
        
        for button in self.buttons:
            self._khb_draw_single_button(button, font_id)
    
    def _khb_draw_single_button(self, button, font_id):
        """Vẽ một button"""
        x, y, size = button.x, button.y, button.size
        is_active = button.khb_get_overlay_state()
        
        # Button background color
        if is_active:
            bg_color = (0.2, 0.6, 1.0, 0.8)  # Blue active
            text_color = (1.0, 1.0, 1.0, 1.0)  # White text
        else:
            bg_color = (0.3, 0.3, 0.3, 0.6)  # Gray inactive
            text_color = (0.7, 0.7, 0.7, 1.0)  # Gray text
        
        # Draw background
        KBH_GPURenderer.khb_draw_rounded_rect(x, y, size, size, bg_color)
        
        # Draw text label (first letter of button_id)
        blf.position(font_id, x + size//3, y + size//3, 0)
        blf.color(font_id, *text_color)
        label = button.button_id[0].upper()
        blf.draw(font_id, label)
    
    def khb_handle_mouse_click(self, mouse_x, mouse_y):
        """Handle mouse click on buttons"""
        for button in self.buttons:
            if button.khb_hit_test(mouse_x, mouse_y):
                button.khb_execute_operator()
                return True
        return False

# Global button manager
khb_button_manager = KBH_ButtonManager()

# ==== MAIN DISPLAY DRAWER ====
class KBH_DisplayDrawer:
    """Main class cho vẽ overlay display"""
    
    @staticmethod
    def khb_draw_modifier_icon(font_id, x, y, modifier_type, icon_size=KBH_ICON_SIZE_PX):
        """Vẽ icon cho modifier"""
        texture = khb_icon_manager.khb_get_modifier_texture(modifier_type)
        
        if texture:
            drawn_width = KBH_GPURenderer.khb_draw_texture_rect(texture, x, y, icon_size, icon_size)
            if drawn_width > 0:
                return drawn_width
        
        # Fallback text placeholder
        blf.size(font_id, int(icon_size * 0.7))
        blf.position(font_id, x, y, 0)
        blf.color(font_id, 0.9, 0.5, 0.1, 1.0)
        blf.draw(font_id, "?")
        text_width = blf.dimensions(font_id, "?")[0]
        return int(max(text_width, icon_size))
    
    @staticmethod
    def khb_draw_modifier_text_line(font_id, x, y, text_color_pairs):
        """Vẽ text line với multiple colors"""
        current_x = x
        
        for text, color in text_color_pairs:
            blf.position(font_id, current_x, y, 0)
            blf.color(font_id, *color)
            blf.draw(font_id, text)
            text_width = blf.dimensions(font_id, text)[0]
            current_x += int(text_width)
        
        return current_x - x  # Total width drawn
    
    @staticmethod
    def khb_draw_main_overlay():
        """Main draw function cho overlay"""
        # Check có selected objects không
        if not bpy.context.selected_objects:
            return
        
        # Setup font
        font_id = 0
        blf.size(font_id, 12)
        
        # Get active object
        obj = bpy.context.active_object
        y_position = 15
        
        # Draw modifier info
        if obj and obj.type == 'MESH' and obj.modifiers:
            for modifier in reversed(obj.modifiers):
                x_position = 20
                
                # Draw modifier icon
                icon_width = KBH_DisplayDrawer.khb_draw_modifier_icon(
                    font_id, x_position, y_position, modifier.type
                )
                x_position += icon_width + KBH_ICON_PAD_PX
                
                # Draw modifier text info
                text_color_pairs = KBH_ModifierProcessor.khb_process_modifier_info(modifier)
                KBH_DisplayDrawer.khb_draw_modifier_text_line(
                    font_id, x_position, y_position, text_color_pairs
                )
                
                y_position += KBH_LINE_HEIGHT
        else:
            # No mesh object message
            blf.position(font_id, 20, y_position, 0)
            blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
            blf.draw(font_id, "No MESH object selected or no modifiers")
        
        # Draw control buttons
        khb_button_manager.khb_draw_all_buttons()

# ==== OVERLAY OPERATORS ====
class KBH_OVERLAY_OT_toggle_wireframe(Operator):
    """Toggle Wireframe Overlay"""
    bl_idname = "khb_overlay.toggle_wireframe"
    bl_label = "Toggle Wireframe Overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_wireframes = not space.overlay.show_wireframes
        
        # Force redraw
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

class KBH_OVERLAY_OT_toggle_edge_length(Operator):
    """Toggle Edge Length Display"""
    bl_idname = "khb_overlay.toggle_edge_length"
    bl_label = "Toggle Edge Length"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_extra_edge_length = not space.overlay.show_extra_edge_length
        
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

class KBH_OVERLAY_OT_toggle_retopology(Operator):
    """Toggle Retopology Overlay"""
    bl_idname = "khb_overlay.toggle_retopology"
    bl_label = "Toggle Retopology"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_retopology = not space.overlay.show_retopology
        
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

class KBH_OVERLAY_OT_toggle_split_normals(Operator):
    """Toggle Split Normals Display"""
    bl_idname = "khb_overlay.toggle_split_normals"
    bl_label = "Toggle Split Normals"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_split_normals = not space.overlay.show_split_normals
        
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

class KBH_OVERLAY_OT_modal_handler(Operator):
    """Modal handler cho button interactions"""
    bl_idname = "khb_overlay.modal_handler"
    bl_label = "KBH Overlay Modal Handler"
    
    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y
            
            # Handle button clicks
            if khb_button_manager.khb_handle_mouse_click(mouse_x, mouse_y):
                # Force redraw after button click
                for area in context.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                return {'RUNNING_MODAL'}
        
        if event.type == 'ESC':
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

# ==== DISPLAY MANAGER ====
class KBH_DisplayManager:
    """Main manager cho toàn bộ display system"""
    
    _instance = None
    _handler = None
    _enabled = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def khb_enable_display_system(self):
        """Enable modifier display overlay"""
        if self._enabled:
            return
        
        try:
            # Load icons
            success = khb_icon_manager.khb_load_modifier_icons()
            if not success:
                print("⚠️ KBH_Display: Icon loading failed, but continuing...")
            
            # Setup draw handler
            self._handler = bpy.types.SpaceView3D.draw_handler_add(
                KBH_DisplayDrawer.khb_draw_main_overlay,
                (),
                'WINDOW',
                'POST_PIXEL'
            )
            
            # Initialize button system
            khb_button_manager.khb_initialize_buttons()
            
            # Start modal handler
            bpy.ops.khb_overlay.modal_handler('INVOKE_DEFAULT')
            
            self._enabled = True
            
            # Force redraw all 3D viewports
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            print("✅ KBH_Display: Display system enabled!")
            
        except Exception as e:
            print(f"❌ KBH_Display: Enable failed - {e}")
    
    def khb_disable_display_system(self):
        """Disable modifier display overlay"""
        if not self._enabled:
            return
        
        try:
            # Remove draw handler
            if self._handler:
                bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
                self._handler = None
            
            # Cleanup icons
            khb_icon_manager.khb_cleanup_all()
            
            self._enabled = False
            
            # Force redraw
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            print("❌ KBH_Display: Display system disabled!")
            
        except Exception as e:
            print(f"⚠️ KBH_Display: Disable error - {e}")
    
    def khb_is_enabled(self):
        """Check if display system is enabled"""
        return self._enabled

# Global display manager
khb_display_manager = KBH_DisplayManager()

# ==== REGISTRATION ====
khb_display_classes = (
    KBH_OVERLAY_OT_toggle_wireframe,
    KBH_OVERLAY_OT_toggle_edge_length,
    KBH_OVERLAY_OT_toggle_retopology,
    KBH_OVERLAY_OT_toggle_split_normals,
    KBH_OVERLAY_OT_modal_handler,
)

def register():
    """Register display system"""
    # Register classes
    for cls in khb_display_classes:
        bpy.utils.register_class(cls)
    
    print(f"🎨 KBH_Display v{KBH_DISPLAY_VERSION}: Classes registered")

def unregister():
    """Unregister display system"""
    # Disable system first
    khb_display_manager.khb_disable_display_system()
    
    # Unregister classes
    for cls in reversed(khb_display_classes):
        bpy.utils.unregister_class(cls)
    
    print(f"🎨 KBH_Display v{KBH_DISPLAY_VERSION}: Unregistered")

# ==== AUTO-ENABLE FOR TESTING ====
if __name__ == "__main__":
    register()
    khb_display_manager.khb_enable_display_system()

