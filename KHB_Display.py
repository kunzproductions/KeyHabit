"""
KHB_Display - KeyHabit Display System
Version: 1.0.3-stable (Fixed import loop & memory leak)
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

# ==== GLOBAL STATE CONTROL ====
_khb_display_state = {
    'handler': None,
    'enabled': False,
    'pcoll': None,
    'icons_loaded': False,
    'buttons_initialized': False,
    'modal_active': False,
}

# ==== CONSTANTS ====
KHB_DISPLAY_VERSION = "1.0.3-stable"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18
KHB_BUTTON_SIZE = 32

# ==== COLOR SCHEME ====
class KHB_DisplayColors:
    BOX = (1.0, 0.45, 0.0, 1.0)
    LABEL = (1.0, 0.45, 0.0, 1.0)
    VALUE = (0.85, 0.92, 0.4, 1.0)
    NUMBER = (1.0, 1.0, 1.0, 1.0)
    ACTIVE = (0.2, 0.6, 1.0, 1.0)
    INACTIVE = (1.0, 0.25, 0.17, 1.0)
    FUNCTION = (1.0, 0.45, 0.0, 1.0)
    SOURCE = (1.0, 1.0, 1.0, 1.0)

# ==== MODIFIER ICON MAPPING ====
KHB_MODIFIER_ICONS = {
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
    'CAST': 'blender_icon_mod_cast.png',
    'CURVE': 'blender_icon_mod_curve.png',
    'DISPLACE': 'blender_icon_mod_displace.png',
    'LATTICE': 'blender_icon_mod_lattice.png',
    'MESH_DEFORM': 'blender_icon_mod_meshdeform.png',
    'SHRINKWRAP': 'blender_icon_mod_shrinkwrap.png',
    'SIMPLE_DEFORM': 'blender_icon_mod_simpledeform.png',
    'SMOOTH': 'blender_icon_mod_smooth.png',
    'SURFACE_DEFORM': 'blender_icon_mod_meshdeform.png',
    'DATA_TRANSFER': 'blender_icon_mod_data_transfer.png',
    'NORMAL_EDIT': 'blender_icon_mod_normaledit.png',
    'UV_PROJECT': 'blender_icon_mod_uvproject.png',
    'CLOTH': 'blender_icon_mod_cloth.png',
    'DYNAMIC_PAINT': 'blender_icon_mod_dynamicpaint.png',
    'FLUID': 'blender_icon_mod_fluidsim.png',
    'OCEAN': 'blender_icon_mod_ocean.png',
    'PARTICLE_INSTANCE': 'blender_icon_mod_particle_instance.png',
    'PARTICLE_SYSTEM': 'blender_icon_mod_particles.png',
    'SOFT_BODY': 'blender_icon_mod_soft.png',
    'NODES': 'blender_icon_geometry_nodes.png',
}

KHB_FALLBACK_ICON = 'blender_icon_question.png'

# ==== ICON FUNCTIONS (NO CLASS - Prevent import loop) ====
def khb_load_icons():
    """Load icons with proper state management"""
    global _khb_display_state
    
    if _khb_display_state['icons_loaded']:
        return True
    
    try:
        # Cleanup existing first
        khb_cleanup_icons()
        
        # Create new collection
        pcoll = bpy.utils.previews.new()
        
        # Get icons directory
        addon_dir = Path(__file__).parent
        icons_dir = addon_dir / "icons"
        
        if not icons_dir.exists():
            print(f"❌ KHB_Display: Icons directory not found")
            bpy.utils.previews.remove(pcoll)
            return False
        
        loaded_count = 0
        
        # Load fallback
        fallback_path = icons_dir / KHB_FALLBACK_ICON
        if fallback_path.exists():
            pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
            loaded_count += 1
        
        # Load modifier icons
        for mod_type, filename in KHB_MODIFIER_ICONS.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                try:
                    pcoll.load(mod_type, str(icon_path), 'IMAGE')
                    loaded_count += 1
                except Exception:
                    pass
        
        # Store globally
        _khb_display_state['pcoll'] = pcoll
        _khb_display_state['icons_loaded'] = True
        
        print(f"🎨 KHB_Display: Icon system initialized ({loaded_count}/{len(KHB_MODIFIER_ICONS)+1} icons loaded)")
        return True
        
    except Exception as e:
        print(f"❌ KHB_Display: Icon loading failed - {e}")
        return False

def khb_get_texture(mod_type):
    """Get texture for modifier type"""
    global _khb_display_state
    
    pcoll = _khb_display_state['pcoll']
    if not pcoll:
        return None
    
    # Try specific icon
    preview = pcoll.get(mod_type) or pcoll.get("FALLBACK")
    if preview and hasattr(preview, 'icon_id') and preview.icon_id > 0:
        try:
            if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
                return gpu.texture.from_icon(preview.icon_id)
        except:
            pass
    
    return None

def khb_cleanup_icons():
    """Cleanup icons with proper state reset"""
    global _khb_display_state
    
    if _khb_display_state['pcoll']:
        try:
            bpy.utils.previews.remove(_khb_display_state['pcoll'])
            print("🧹 KHB_Display: Icons cleaned up")
        except Exception as e:
            print(f"⚠️ KHB_Display: Cleanup warning - {e}")
        
        _khb_display_state['pcoll'] = None
    
    _khb_display_state['icons_loaded'] = False

# ==== CONTROL BUTTONS ====
_control_buttons = []

def khb_init_buttons():
    """Initialize control buttons (prevent multiple init)"""
    global _khb_display_state, _control_buttons
    
    if _khb_display_state['buttons_initialized']:
        return
    
    _control_buttons.clear()
    
    button_configs = [
        ('W', 50, 60, 'khb_overlay.toggle_wireframe'),
        ('E', 90, 60, 'khb_overlay.toggle_edge_length'),
        ('R', 130, 60, 'khb_overlay.toggle_retopology'),
        ('S', 170, 60, 'khb_overlay.toggle_split_normals')
    ]
    
    for label, x, y, op in button_configs:
        _control_buttons.append({
            'label': label,
            'x': x, 'y': y, 'size': KHB_BUTTON_SIZE,
            'operator': op
        })
    
    _khb_display_state['buttons_initialized'] = True
    print(f"🎮 KHB_Display: {len(_control_buttons)} control buttons initialized")

def khb_draw_buttons():
    """Draw control buttons"""
    if not _control_buttons:
        khb_init_buttons()
    
    font_id = 0
    blf.size(font_id, 12)
    
    for btn in _control_buttons:
        x, y, size = btn['x'], btn['y'], btn['size']
        
        # Simple button background
        try:
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", (0.2, 0.6, 1.0, 0.6))
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            
            # Button text
            blf.position(font_id, x + size//3, y + size//3, 0)
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
            blf.draw(font_id, btn['label'])
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Button draw error - {e}")

# ==== DISPLAY FUNCTIONS ====
def khb_draw_modifier_icon(font_id, x, y, mod_type, icon_size=KHB_ICON_SIZE_PX):
    """Draw modifier icon"""
    texture = khb_get_texture(mod_type)
    
    if texture:
        try:
            positions = [(x, y), (x + icon_size, y), (x + icon_size, y + icon_size), (x, y + icon_size)]
            uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
            
            shader = gpu.shader.from_builtin('IMAGE')
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions, "texCoord": uvs})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_sampler("image", texture)
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            return icon_size
        except:
            pass
    
    # Fallback
    blf.size(font_id, int(icon_size * 0.8))
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 0.9, 0.5, 0.1, 1.0)
    blf.draw(font_id, "?")
    return icon_size

def khb_get_modifier_text(modifier):
    """Get modifier text with colors"""
    colors = KHB_DisplayColors()
    tc = []
    
    # Basic info
    tc.extend([
        ('[', colors.BOX),
        (modifier.type, colors.LABEL),
        (']', colors.BOX),
        (' ' + modifier.name, colors.NUMBER)
    ])
    
    # Boolean specific
    if modifier.type == 'BOOLEAN':
        operation = getattr(modifier, 'operation', '')
        if operation:
            tc.append((' ' + operation, colors.FUNCTION))
        
        source_obj = getattr(modifier, 'object', None)
        if source_obj:
            tc.append((' ' + source_obj.name, colors.SOURCE))
    
    return tc

def khb_draw_overlay():
    """Main overlay draw function - SINGLE INSTANCE"""
    try:
        font_id = 0
        blf.size(font_id, 12)
        obj = bpy.context.active_object
        y = 15
        
        if obj and obj.type == 'MESH' and obj.modifiers:
            for modifier in reversed(obj.modifiers):
                x = 20
                
                # Draw icon
                icon_w = khb_draw_modifier_icon(font_id, x, y, modifier.type)
                x += icon_w + KHB_ICON_PAD_PX
                
                # Draw text
                text_pairs = khb_get_modifier_text(modifier)
                for text, color in text_pairs:
                    blf.position(font_id, x, y, 0)
                    blf.color(font_id, *color)
                    blf.draw(font_id, text)
                    text_w = blf.dimensions(font_id, text)[0]
                    x += int(text_w)
                
                y += KHB_LINE_HEIGHT
        else:
            blf.position(font_id, 20, y, 0)
            blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
            blf.draw(font_id, "No MESH object selected or no modifiers")
        
        # Draw buttons
        khb_draw_buttons()
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Overlay draw error - {e}")

# ==== DISPLAY MANAGER ====
def khb_enable_display_system():
    """Enable display system - SINGLE CALL ONLY"""
    global _khb_display_state
    
    if _khb_display_state['enabled']:
        return  # Already enabled, ignore
    
    try:
        # Load icons
        khb_load_icons()
        
        # Initialize buttons  
        khb_init_buttons()
        
        # Add draw handler
        _khb_display_state['handler'] = bpy.types.SpaceView3D.draw_handler_add(
            khb_draw_overlay,
            (),
            'WINDOW',
            'POST_PIXEL'
        )
        
        _khb_display_state['enabled'] = True
        
        # Force redraw
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        print("✅ KHB_Display: Display system enabled!")
        
    except Exception as e:
        print(f"❌ KHB_Display: Enable failed - {e}")

def khb_disable_display_system():
    """Disable display system with complete cleanup"""
    global _khb_display_state
    
    if not _khb_display_state['enabled']:
        return  # Already disabled
    
    try:
        # Remove draw handler
        if _khb_display_state['handler']:
            bpy.types.SpaceView3D.draw_handler_remove(_khb_display_state['handler'], 'WINDOW')
            _khb_display_state['handler'] = None
        
        # Cleanup icons
        khb_cleanup_icons()
        
        # Reset state
        _khb_display_state['enabled'] = False
        _khb_display_state['buttons_initialized'] = False
        
        # Force redraw
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        print("❌ KHB_Display: Display system disabled!")
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Disable error - {e}")
        # Force reset
        _khb_display_state['enabled'] = False
        _khb_display_state['handler'] = None

def khb_is_enabled():
    """Check if enabled"""
    global _khb_display_state
    return _khb_display_state['enabled']

def khb_force_redraw():
    """Force redraw"""
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except:
        pass

# ==== OVERLAY OPERATORS ====
class KHB_OVERLAY_OT_toggle_wireframe(Operator):
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

# ==== LEGACY COMPATIBILITY (For __init__.py imports) ====
class KHB_IconManager:
    """Legacy wrapper - prevents import errors"""
    def khb_load_icons(self):
        return khb_load_icons()
    def khb_cleanup(self):
        khb_cleanup_icons()
    def khb_get_texture(self, mod_type):
        return khb_get_texture(mod_type)

class KHB_DisplayManager:
    """Legacy wrapper - prevents import errors"""
    def khb_enable_display_system(self):
        khb_enable_display_system()
    def khb_disable_display_system(self):
        khb_disable_display_system()
    def khb_is_enabled(self):
        return khb_is_enabled()
    def khb_force_redraw(self):
        khb_force_redraw()

class KHB_ButtonManager:
    """Legacy wrapper - prevents import errors"""
    def khb_update_settings(self, settings):
        pass  # Settings handled globally
    def khb_init_buttons(self):
        khb_init_buttons()

# Create legacy instances (ONLY ONCE)
khb_icon_manager = KHB_IconManager()
khb_display_manager = KHB_DisplayManager()
khb_button_manager = KHB_ButtonManager()

# ==== REGISTRATION ====
khb_display_classes = (
    KHB_OVERLAY_OT_toggle_wireframe,
    KHB_OVERLAY_OT_toggle_edge_length,
    KHB_OVERLAY_OT_toggle_retopology,
    KHB_OVERLAY_OT_toggle_split_normals,
)

def register():
    """Register display system"""
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Starting registration...")
    
    for cls in khb_display_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"❌ KHB_Display: Class registration failed {cls.__name__} - {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Registered")

def unregister():
    """Unregister with complete cleanup"""
    print(f"🛑 KHB_Display v{KHB_DISPLAY_VERSION}: Starting unregistration...")
    
    # Force disable and cleanup
    khb_disable_display_system()
    
    # Force cleanup global state
    global _khb_display_state, _control_buttons
    
    try:
        if _khb_display_state['handler']:
            bpy.types.SpaceView3D.draw_handler_remove(_khb_display_state['handler'], 'WINDOW')
        
        if _khb_display_state['pcoll']:
            bpy.utils.previews.remove(_khb_display_state['pcoll'])
        
        # Reset all state
        _khb_display_state = {
            'handler': None, 'enabled': False, 'pcoll': None,
            'icons_loaded': False, 'buttons_initialized': False, 'modal_active': False,
        }
        _control_buttons.clear()
        
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
