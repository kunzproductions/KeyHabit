"""
KHB_Display - KeyHabit Display System
Complete version with working PNG icons
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

# ==== GLOBAL STATE MANAGEMENT ====
_display_state = {
    'handler': None,
    'enabled': False,
    'preview_collections': {},
    'initialized': False
}

# ==== CONSTANTS ====
KHB_DISPLAY_VERSION = "1.0.2-complete"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18

# ==== COLOR SCHEME ====
class KHB_DisplayColors:
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

# ==== ICON MANAGER - COMPLETE ====
class KHB_IconManager:
    """Complete icon manager with PNG icon loading"""
    
    def __init__(self):
        pass
    
    def khb_load_modifier_icons(self):
        """Load ALL modifier icons"""
        global _display_state
        
        if _display_state['initialized']:
            return True
        
        try:
            # Cleanup any existing collections first
            self._khb_cleanup_existing()
            
            # Create new collection
            pcoll = bpy.utils.previews.new()
            
            # Get addon directory
            addon_dir = Path(__file__).parent
            icons_dir = addon_dir / "icons"
            
            if not icons_dir.exists():
                print(f"❌ KHB_Display: Icons directory not found")
                bpy.utils.previews.remove(pcoll)
                return False
            
            # Load fallback icon first
            loaded_count = 0
            fallback_path = icons_dir / KHB_FALLBACK_ICON
            if fallback_path.exists():
                pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
                loaded_count += 1
                print("✅ KHB_Display: Loaded fallback icon")
            
            # Load ALL modifier icons
            for mod_type, filename in KHB_MODIFIER_ICONS.items():
                icon_path = icons_dir / filename
                if icon_path.exists():
                    try:
                        pcoll.load(mod_type, str(icon_path), 'IMAGE')
                        loaded_count += 1
                        print(f"✅ KHB_Display: Loaded {mod_type} -> {filename}")
                    except Exception as e:
                        print(f"⚠️ KHB_Display: Failed to load {filename} - {e}")
                else:
                    print(f"⚠️ KHB_Display: Missing icon: {filename} for {mod_type}")
            
            # Store collection globally
            _display_state['preview_collections']['main'] = pcoll
            _display_state['initialized'] = True
            
            print(f"🎨 KHB_Display: Icon system initialized ({loaded_count}/{len(KHB_MODIFIER_ICONS)+1} icons loaded)")
            return True
            
        except Exception as e:
            print(f"❌ KHB_Display: Icon loading failed - {e}")
            return False
    
    def khb_get_modifier_texture(self, mod_type):
        """Get GPU texture for modifier type"""
        global _display_state
        
        if not _display_state['initialized']:
            return None
        
        pcoll = _display_state['preview_collections'].get('main')
        if not pcoll:
            return None
        
        # Try get specific modifier icon
        if mod_type in pcoll:
            preview = pcoll[mod_type]
            texture = self._khb_convert_preview_to_texture(preview)
            if texture:
                return texture
        
        # Try fallback icon
        if "FALLBACK" in pcoll:
            preview = pcoll["FALLBACK"]
            return self._khb_convert_preview_to_texture(preview)
        
        return None
    
    def _khb_convert_preview_to_texture(self, preview):
        """Convert preview icon to GPU texture"""
        try:
            if hasattr(preview, 'icon_id') and preview.icon_id > 0:
                if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
                    return gpu.texture.from_icon(preview.icon_id)
        except Exception as e:
            print(f"⚠️ KHB_Display: Texture conversion failed - {e}")
        return None
    
    def _khb_cleanup_existing(self):
        """Clean up existing preview collections"""
        global _display_state
        
        for name, pcoll in _display_state['preview_collections'].items():
            try:
                bpy.utils.previews.remove(pcoll)
                print(f"🧹 KHB_Display: Cleaned up collection '{name}'")
            except Exception as e:
                print(f"⚠️ KHB_Display: Cleanup warning for '{name}' - {e}")
        
        _display_state['preview_collections'].clear()
        _display_state['initialized'] = False
    
    def khb_cleanup_all(self):
        """Complete cleanup"""
        self._khb_cleanup_existing()
        print("🧹 KHB_Display: Complete icon cleanup done")

# ==== GPU RENDERING ====
_image_shader = None

def _get_image_shader():
    """Get cached image shader"""
    global _image_shader
    if _image_shader is None:
        _image_shader = gpu.shader.from_builtin('IMAGE')
    return _image_shader

def _draw_texture(texture, x, y, width, height):
    """Draw texture rectangle to screen"""
    if texture is None:
        return 0
    
    try:
        # Setup geometry
        positions = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
        uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        
        shader = _get_image_shader()
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions, "texCoord": uvs})
        
        # Render
        gpu.state.blend_set('ALPHA')
        shader.bind()
        
        # Bind texture
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
        print(f"⚠️ KHB_Display: Texture rendering failed - {e}")
        gpu.state.blend_set('NONE')
        return 0

def draw_modifier_icon(font_id, x, y, mod_type, icon_size=KHB_ICON_SIZE_PX):
    """Draw modifier icon with PNG support"""
    icon_manager = KHB_IconManager()
    texture = icon_manager.khb_get_modifier_texture(mod_type)
    
    if texture:
        drawn_width = _draw_texture(texture, x, y, icon_size, icon_size)
        if drawn_width > 0:
            return drawn_width
    
    # Fallback: Draw question mark
    blf.size(font_id, int(icon_size * 0.8))
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 0.9, 0.5, 0.1, 1.0)
    blf.draw(font_id, "?")
    text_width = blf.dimensions(font_id, "?")[0]
    return int(max(text_width, icon_size))

# ==== MODIFIER TEXT PROCESSING ====
def get_modifier_display_name(modifier):
    """Get display name for modifier"""
    try:
        enum_prop = bpy.types.Modifier.bl_rna.properties['type']
        return enum_prop.enum_items[modifier.type].name
    except:
        return modifier.type.title().replace('_', ' ')

def get_modifier_line(modifier):
    """Process modifier into text-color pairs"""
    tc = []
    colors = KHB_DisplayColors()
    
    # Geometry Nodes Auto Smooth
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
    
    else:
        # Regular modifier
        tc.extend([
            ('[', colors.BOX),
            (get_modifier_display_name(modifier), colors.LABEL),
            (']', colors.BOX),
            (' ' + modifier.name, colors.NUMBER)
        ])
        
        # Boolean specific info
        if modifier.type == 'BOOLEAN':
            operation = getattr(modifier, 'operation', '')
            if operation:
                tc.append((' ' + operation, colors.FUNCTION))
            
            source_obj = getattr(modifier, 'object', None)
            if source_obj:
                tc.append((' ' + source_obj.name, colors.SOURCE))
    
    return tc

# ==== DISPLAY MANAGER - COMPLETE ====
class KHB_DisplayManager:
    """Complete display manager with icon rendering"""
    
    def khb_enable_display_system(self):
        """Enable display system with icon loading"""
        global _display_state
        
        if _display_state['enabled']:
            print("⚠️ KHB_Display: Already enabled, skipping")
            return
        
        try:
            # Load icons
            icon_manager = KHB_IconManager()
            success = icon_manager.khb_load_modifier_icons()
            if not success:
                print("⚠️ KHB_Display: Icon loading failed, but continuing...")
            
            # Add draw handler
            if _display_state['handler'] is None:
                _display_state['handler'] = bpy.types.SpaceView3D.draw_handler_add(
                    self._khb_draw_complete_overlay,
                    (),
                    'WINDOW',
                    'POST_PIXEL'
                )
            
            _display_state['enabled'] = True
            
            # Force redraw
            self._khb_force_redraw()
            
            print("✅ KHB_Display: Complete display system enabled!")
            
        except Exception as e:
            print(f"❌ KHB_Display: Enable failed - {e}")
            self.khb_disable_display_system()
    
    def khb_disable_display_system(self):
        """Disable display system with complete cleanup"""
        global _display_state
        
        try:
            # Remove draw handler FIRST
            if _display_state['handler'] is not None:
                bpy.types.SpaceView3D.draw_handler_remove(_display_state['handler'], 'WINDOW')
                _display_state['handler'] = None
                print("🧹 KHB_Display: Draw handler removed")
            
            # Cleanup icons
            icon_manager = KHB_IconManager()
            icon_manager.khb_cleanup_all()
            
            _display_state['enabled'] = False
            
            # Force redraw to clear display
            self._khb_force_redraw()
            
            print("❌ KHB_Display: Display system disabled!")
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Disable error - {e}")
            _display_state['enabled'] = False
            _display_state['handler'] = None
    
    def khb_is_enabled(self):
        """Check if system is enabled"""
        global _display_state
        return _display_state['enabled']
    
    def _khb_draw_complete_overlay(self):
        """Complete overlay drawing with icons"""
        if not bpy.context.selected_objects:
            return
        
        font_id = 0
        blf.size(font_id, 12)
        obj = bpy.context.active_object
        y = 15
        
        if obj and obj.type == 'MESH' and obj.modifiers:
            # Draw modifier info with icons
            for modifier in reversed(obj.modifiers):
                x = 20
                
                # Draw modifier icon
                icon_w = draw_modifier_icon(font_id, x, y, modifier.type, KHB_ICON_SIZE_PX)
                x += icon_w + KHB_ICON_PAD_PX
                
                # Draw modifier text info
                text_color_pairs = get_modifier_line(modifier)
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
    
    def _khb_force_redraw(self):
        """Force redraw all 3D viewports"""
        try:
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        except:
            pass

# ==== OPERATORS (Keep existing ones) ====
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

# ==== GLOBAL INSTANCES ====
khb_display_manager = KHB_DisplayManager()

# ==== REGISTRATION ====
khb_display_classes = (
    KHB_OVERLAY_OT_toggle_wireframe,
    KHB_OVERLAY_OT_toggle_edge_length,
    KHB_OVERLAY_OT_toggle_retopology,
    KHB_OVERLAY_OT_toggle_split_normals,
)

def register():
    """Register complete display system"""
    for cls in khb_display_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"❌ KHB_Display: Class registration failed {cls.__name__} - {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Complete version registered")

def unregister():
    """Unregister with complete cleanup"""
    print("🛑 KHB_Display: Starting complete unregistration...")
    
    # Force disable and cleanup
    try:
        khb_display_manager.khb_disable_display_system()
    except:
        pass
    
    # Force cleanup global state
    global _display_state
    try:
        if _display_state['handler'] is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_display_state['handler'], 'WINDOW')
        
        for pcoll in _display_state['preview_collections'].values():
            bpy.utils.previews.remove(pcoll)
        
        _display_state = {
            'handler': None,
            'enabled': False,
            'preview_collections': {},
            'initialized': False
        }
        
        print("🧹 KHB_Display: Complete cleanup done")
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Cleanup error - {e}")
    
    # Unregister classes
    for cls in reversed(khb_display_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KHB_Display: Class unregistration error - {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Complete unregistration done")

if __name__ == "__main__":
    register()
