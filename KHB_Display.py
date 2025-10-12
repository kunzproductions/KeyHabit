"""
KHB_Display - KeyHabit Display System
Version: 1.1.0-optimized
Complete modifier overlay system with PNG icons and interactive controls
"""

import bpy
from bpy.types import Operator
import bpy.utils.previews
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import os
from pathlib import Path
import time

# ==== VERSION & CONSTANTS ====
KHB_DISPLAY_VERSION = "1.1.0-optimized"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18
KHB_BUTTON_SIZE = 28

# ==== GLOBAL STATE ====
_khb_state = {
    'enabled': False,
    'handler': None,
    'modal_op': None,
    'modal_running': False,
    'pcoll': None,
    'icons_loaded': False,
    'buttons': [],
    'last_click_time': 0,
    'settings': {
        'show_buttons': True,
        'position': 'BOTTOM_LEFT',
        'use_png': True,
    }
}

# ==== COLOR SYSTEM ====
class KHB_Colors:
    """Centralized color management"""
    # Text colors
    BOX = (1.0, 0.45, 0.0, 1.0)      # Orange brackets
    LABEL = (1.0, 0.45, 0.0, 1.0)    # Orange modifier name
    VALUE = (0.85, 0.92, 0.4, 1.0)   # Green parameter labels
    NUMBER = (1.0, 1.0, 1.0, 1.0)    # White values
    ACTIVE = (0.2, 0.6, 1.0, 1.0)    # Blue for active states
    INACTIVE = (1.0, 0.25, 0.17, 1.0) # Red for inactive states
    FUNCTION = (1.0, 0.45, 0.0, 1.0) # Orange function names
    SOURCE = (1.0, 1.0, 1.0, 1.0)    # White object names
    
    # Button colors
    BUTTON_ACTIVE = (0.1, 0.8, 0.2, 0.9)    # Bright green
    BUTTON_INACTIVE = (0.2, 0.2, 0.2, 0.8)  # Dark gray
    BUTTON_BORDER = (1.0, 1.0, 1.0, 1.0)    # White border
    BUTTON_TEXT = (1.0, 1.0, 1.0, 1.0)      # White text
    
    # Icon colors (for colored square fallbacks)
    ICON_COLORS = {
        'BOOLEAN': (1.0, 0.3, 0.3, 0.8),    # Red
        'MIRROR': (0.3, 0.8, 0.3, 0.8),     # Green
        'ARRAY': (0.3, 0.3, 1.0, 0.8),      # Blue
        'BEVEL': (1.0, 1.0, 0.3, 0.8),      # Yellow
        'SUBSURF': (1.0, 0.3, 1.0, 0.8),    # Magenta
        'SOLIDIFY': (0.3, 1.0, 1.0, 0.8),   # Cyan
        'DISPLACE': (1.0, 0.6, 0.3, 0.8),   # Orange
        'NODES': (0.6, 0.3, 1.0, 0.8),      # Purple
        'TRIANGULATE': (0.8, 0.8, 0.8, 0.8), # Gray
    }

# ==== MODIFIER ICON MAPPING ====
KHB_MODIFIER_ICONS = {
    # Generate modifiers
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
    
    # Deform modifiers
    'CAST': 'blender_icon_mod_cast.png',
    'CURVE': 'blender_icon_mod_curve.png', 
    'DISPLACE': 'blender_icon_mod_displace.png',
    'LATTICE': 'blender_icon_mod_lattice.png',
    'MESH_DEFORM': 'blender_icon_mod_meshdeform.png',
    'SHRINKWRAP': 'blender_icon_mod_shrinkwrap.png',
    'SIMPLE_DEFORM': 'blender_icon_mod_simpledeform.png',
    'SMOOTH': 'blender_icon_mod_smooth.png',
    
    # Modify modifiers
    'DATA_TRANSFER': 'blender_icon_mod_data_transfer.png',
    'NORMAL_EDIT': 'blender_icon_mod_normaledit.png',
    'UV_PROJECT': 'blender_icon_mod_uvproject.png',
    
    # Physics modifiers
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

# Text abbreviations for modifiers
KHB_TEXT_ABBREV = {
    'BOOLEAN': 'BO', 'MIRROR': 'MI', 'ARRAY': 'AR', 'BEVEL': 'BV',
    'SUBSURF': 'SS', 'SOLIDIFY': 'SO', 'DISPLACE': 'DI', 'NODES': 'GN',
    'TRIANGULATE': 'TR', 'DECIMATE': 'DE', 'BUILD': 'BU', 'WELD': 'WE',
    'CAST': 'CA', 'CURVE': 'CV', 'LATTICE': 'LA', 'MESH_DEFORM': 'MD',
    'SHRINKWRAP': 'SW', 'SIMPLE_DEFORM': 'SD', 'SMOOTH': 'SM',
    'DATA_TRANSFER': 'DT', 'NORMAL_EDIT': 'NE', 'UV_PROJECT': 'UV',
    'CLOTH': 'CL', 'DYNAMIC_PAINT': 'DP', 'FLUID': 'FL', 'OCEAN': 'OC'
}

# ==== ICON SYSTEM ====
def khb_load_icons():
    """Load PNG icons with proper error handling"""
    global _khb_state
    
    if _khb_state['icons_loaded'] or not _khb_state['settings']['use_png']:
        return True
    
    try:
        # Clean up existing collection
        khb_cleanup_icons()
        
        # Create new preview collection
        pcoll = bpy.utils.previews.new()
        
        # Get icons directory
        addon_dir = Path(__file__).parent
        icons_dir = addon_dir / "icons"
        
        if not icons_dir.exists():
            print(f"⚠️ KHB_Display: Icons directory not found, using text fallbacks")
            bpy.utils.previews.remove(pcoll)
            return False
        
        loaded_count = 0
        
        # Load fallback icon
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
                    pass  # Silently skip problematic icons
        
        _khb_state['pcoll'] = pcoll
        _khb_state['icons_loaded'] = True
        
        print(f"🎨 KHB_Display: Icon system initialized ({loaded_count} icons loaded)")
        return True
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Icon loading failed - {e}")
        return False

def khb_cleanup_icons():
    """Clean up icon resources"""
    global _khb_state
    
    if _khb_state['pcoll']:
        try:
            bpy.utils.previews.remove(_khb_state['pcoll'])
        except Exception:
            pass
        _khb_state['pcoll'] = None
    
    _khb_state['icons_loaded'] = False

def khb_get_texture(mod_type):
    """Get GPU texture for icon (with proper Buffer conversion)"""
    global _khb_state
    
    if not _khb_state['pcoll'] or not _khb_state['settings']['use_png']:
        return None
    
    # Get preview (try specific type first, then fallback)
    preview = _khb_state['pcoll'].get(mod_type) or _khb_state['pcoll'].get("FALLBACK")
    if not preview or not hasattr(preview, 'icon_pixels_float'):
        return None
    
    try:
        icon_data = preview.icon_pixels_float
        if not icon_data:
            return None
        
        # Calculate icon dimensions
        data_size = len(icon_data)
        pixels_count = data_size // 4  # RGBA
        icon_size = int(pixels_count ** 0.5)
        
        if icon_size > 0 and icon_size * icon_size * 4 == data_size:
            # Convert to proper GPU buffer
            import numpy as np
            pixels = np.array(icon_data, dtype=np.float32).reshape((icon_size, icon_size, 4))
            buffer_data = gpu.types.Buffer('FLOAT', (icon_size, icon_size, 4), pixels)
            texture = gpu.types.GPUTexture((icon_size, icon_size), format='RGBA8', data=buffer_data)
            return texture
            
    except Exception:
        pass  # Silently fall back to other rendering methods
    
    return None

# ==== BUTTON SYSTEM ====
def khb_init_buttons():
    """Initialize control buttons based on settings"""
    global _khb_state
    
    if not _khb_state['settings']['show_buttons']:
        _khb_state['buttons'] = []
        return
    
    # Button configuration
    buttons_config = [
        {'id': 'wireframe', 'label': 'W', 'tooltip': 'Toggle Wireframe'},
        {'id': 'edge_length', 'label': 'E', 'tooltip': 'Toggle Edge Length'},
        {'id': 'retopo', 'label': 'R', 'tooltip': 'Toggle Retopology'},
        {'id': 'split_normals', 'label': 'S', 'tooltip': 'Toggle Split Normals'}
    ]
    
    # Calculate positions based on settings
    position = _khb_state['settings']['position']
    if position == 'BOTTOM_LEFT':
        start_x, start_y = 60, 40
    elif position == 'BOTTOM_RIGHT':
        start_x, start_y = 300, 40
    elif position == 'TOP_LEFT':
        start_x, start_y = 60, 200
    else:  # TOP_RIGHT
        start_x, start_y = 300, 200
    
    # Create button data
    _khb_state['buttons'] = []
    x = start_x
    
    for config in buttons_config:
        _khb_state['buttons'].append({
            'id': config['id'],
            'label': config['label'],
            'tooltip': config['tooltip'],
            'x': x,
            'y': start_y,
            'size': KHB_BUTTON_SIZE
        })
        x += KHB_BUTTON_SIZE + 8  # 8px spacing
    
    if _khb_state['buttons']:
        print(f"🎮 KHB_Display: {len(_khb_state['buttons'])} buttons initialized at {position}")

def khb_draw_buttons():
    """Draw control buttons with proper styling"""
    global _khb_state
    
    if not _khb_state['buttons']:
        return
    
    font_id = 0
    blf.size(font_id, 12)
    colors = KHB_Colors()
    
    for btn in _khb_state['buttons']:
        x, y, size = btn['x'], btn['y'], btn['size']
        is_active = khb_get_overlay_state(btn['id'])
        
        # Choose colors
        bg_color = colors.BUTTON_ACTIVE if is_active else colors.BUTTON_INACTIVE
        text_color = colors.BUTTON_TEXT
        
        try:
            # Draw button background
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = [(x, y), (x+size, y), (x+size, y+size), (x, y+size)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", bg_color)
            batch.draw(shader)
            
            # Draw border
            border_positions = [(x-1, y-1), (x+size+1, y-1), (x+size+1, y+size+1), (x-1, y+size+1), (x-1, y-1)]
            border_batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": border_positions})
            shader.uniform_float("color", colors.BUTTON_BORDER)
            border_batch.draw(shader)
            
            gpu.state.blend_set('NONE')
            
            # Draw text (centered)
            text_x = x + (size // 2) - 4
            text_y = y + (size // 2) - 6
            
            blf.position(font_id, text_x, text_y, 0)
            blf.color(font_id, *text_color)
            blf.draw(font_id, btn['label'])
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Button draw error: {e}")

def khb_get_overlay_state(button_id):
    """Get current overlay state for button"""
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        overlay = space.overlay
                        if button_id == 'wireframe':
                            return overlay.show_wireframes
                        elif button_id == 'edge_length':
                            return overlay.show_extra_edge_length
                        elif button_id == 'retopo':
                            return overlay.show_retopology
                        elif button_id == 'split_normals':
                            return overlay.show_split_normals
    except Exception:
        pass
    return False

def khb_handle_click(mouse_x, mouse_y):
    """Handle button clicks with debouncing"""
    global _khb_state
    
    current_time = time.time()
    if current_time - _khb_state['last_click_time'] < 0.2:  # 200ms debounce
        return False
    
    for btn in _khb_state['buttons']:
        x, y, size = btn['x'], btn['y'], btn['size']
        
        # Hit test
        if x <= mouse_x <= x + size and y <= mouse_y <= y + size:
            try:
                # Toggle overlay directly
                for area in bpy.context.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                overlay = space.overlay
                                
                                if btn['id'] == 'wireframe':
                                    overlay.show_wireframes = not overlay.show_wireframes
                                elif btn['id'] == 'edge_length':
                                    overlay.show_extra_edge_length = not overlay.show_extra_edge_length
                                elif btn['id'] == 'retopo':
                                    overlay.show_retopology = not overlay.show_retopology
                                elif btn['id'] == 'split_normals':
                                    overlay.show_split_normals = not overlay.show_split_normals
                                
                                area.tag_redraw()
                                _khb_state['last_click_time'] = current_time
                                print(f"🎯 KHB_Display: {btn['label']} button clicked")
                                return True
                                
            except Exception as e:
                print(f"⚠️ KHB_Display: Button click error: {e}")
    
    return False

# ==== DRAWING FUNCTIONS ====
def khb_draw_icon(font_id, x, y, mod_type, size=None):
    """Draw modifier icon (PNG, colored square, or text)"""
    if size is None:
        size = KHB_ICON_SIZE_PX
    
    # Method 1: Try PNG texture
    if _khb_state['settings']['use_png']:
        texture = khb_get_texture(mod_type)
        if texture:
            try:
                positions = [(x, y), (x+size, y), (x+size, y+size), (x, y+size)]
                uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
                
                shader = gpu.shader.from_builtin('IMAGE')
                batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions, "texCoord": uvs})
                
                gpu.state.blend_set('ALPHA')
                shader.bind()
                shader.uniform_sampler("image", texture)
                batch.draw(shader)
                gpu.state.blend_set('NONE')
                return size
            except Exception:
                pass
    
    # Method 2: Colored square
    color = KHB_Colors.ICON_COLORS.get(mod_type, (1.0, 0.7, 0.0, 0.8))
    try:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        positions = [(x, y), (x+size, y), (x+size, y+size), (x, y+size)]
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
        
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.blend_set('NONE')
        return size
    except Exception:
        pass
    
    # Method 3: Text fallback
    blf.size(font_id, size - 1)
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1.0, 0.7, 0.0, 1.0)
    text = KHB_TEXT_ABBREV.get(mod_type, mod_type[:2])
    blf.draw(font_id, text)
    
    return size

def khb_get_modifier_text(modifier):
    """Generate modifier text with colors"""
    colors = KHB_Colors()
    tc = []
    
    # Basic info: [Type] Name
    display_name = modifier.type.replace('_', ' ').title()
    tc.extend([
        ('[', colors.BOX),
        (display_name, colors.LABEL),
        (']', colors.BOX),
        (' ' + modifier.name, colors.NUMBER)
    ])
    
    # Type-specific details
    if modifier.type == 'BOOLEAN':
        operation = getattr(modifier, 'operation', '')
        if operation:
            tc.append((' ' + operation, colors.FUNCTION))
        
        obj = getattr(modifier, 'object', None)
        if obj:
            tc.append((' → ' + obj.name, colors.SOURCE))
    
    elif modifier.type == 'MIRROR':
        axes = getattr(modifier, 'use_axis', [False, False, False])
        for i, axis in enumerate(['X', 'Y', 'Z']):
            color = colors.ACTIVE if (i < len(axes) and axes[i]) else colors.INACTIVE
            tc.append((' ' + axis, color))
    
    elif modifier.type == 'ARRAY':
        count = getattr(modifier, 'count', 1)
        tc.extend([(' ×', colors.VALUE), (str(count), colors.NUMBER)])
    
    elif modifier.type == 'SUBSURF':
        levels = getattr(modifier, 'levels', 0)
        tc.extend([(' Lv', colors.VALUE), (str(levels), colors.NUMBER)])
    
    elif modifier.type == 'BEVEL':
        width = getattr(modifier, 'width', 0)
        segments = getattr(modifier, 'segments', 1)
        tc.extend([
            (' W:', colors.VALUE), (f"{width:.3f}", colors.NUMBER),
            (' S:', colors.VALUE), (str(segments), colors.NUMBER)
        ])
    
    elif modifier.type == 'NODES':
        # Special handling for Auto Smooth
        if "Smooth by Angle" in modifier.name or "Shade Auto Smooth" in modifier.name:
            tc[1] = ('Shade Auto Smooth', colors.LABEL)
            
            if "Input_1" in modifier.keys():
                import math
                angle_rad = modifier["Input_1"]
                angle_deg = round(angle_rad * 180 / math.pi, 1)
                tc.extend([(' Angle:', colors.VALUE), (f"{angle_deg}°", colors.NUMBER)])
    
    return tc

def khb_draw_overlay():
    """Main overlay drawing function"""
    try:
        font_id = 0
        blf.size(font_id, 12)
        obj = bpy.context.active_object
        y = 15
        
        if obj and obj.type == 'MESH' and obj.modifiers:
            # Draw modifiers (bottom to top)
            for modifier in reversed(obj.modifiers):
                x = 20
                
                # Draw icon
                icon_width = khb_draw_icon(font_id, x, y, modifier.type)
                x += icon_width + KHB_ICON_PAD_PX
                
                # Draw text info
                text_pairs = khb_get_modifier_text(modifier)
                for text, color in text_pairs:
                    blf.position(font_id, x, y, 0)
                    blf.color(font_id, *color)
                    blf.draw(font_id, text)
                    text_width = blf.dimensions(font_id, text)[0]
                    x += int(text_width)
                
                y += KHB_LINE_HEIGHT
        else:
            # No modifiers message
            blf.position(font_id, 20, y, 0)
            blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
            blf.draw(font_id, "Select MESH object with modifiers")
        
        # Draw control buttons
        khb_draw_buttons()
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Overlay draw error: {e}")

# ==== SYSTEM CONTROL ====
def khb_enable_display_system():
    """Enable the complete display system"""
    global _khb_state
    
    if _khb_state['enabled']:
        return True
    
    try:
        # Load icons
        khb_load_icons()
        
        # Initialize buttons
        khb_init_buttons()
        
        # Add draw handler
        _khb_state['handler'] = bpy.types.SpaceView3D.draw_handler_add(
            khb_draw_overlay, (), 'WINDOW', 'POST_PIXEL'
        )
        
        # Start modal for interactions
        if _khb_state['settings']['show_buttons'] and not _khb_state['modal_running']:
            try:
                bpy.ops.khb_display.modal_handler('INVOKE_DEFAULT')
            except Exception as e:
                print(f"⚠️ KHB_Display: Modal start failed: {e}")
        
        _khb_state['enabled'] = True
        khb_force_redraw()
        
        print("✅ KHB_Display: Display system enabled!")
        return True
        
    except Exception as e:
        print(f"❌ KHB_Display: Enable failed: {e}")
        khb_disable_display_system()
        return False

def khb_disable_display_system():
    """Disable the display system"""
    global _khb_state
    
    if not _khb_state['enabled']:
        return
    
    try:
        # Remove draw handler
        if _khb_state['handler']:
            bpy.types.SpaceView3D.draw_handler_remove(_khb_state['handler'], 'WINDOW')
            _khb_state['handler'] = None
        
        # Stop modal
        _khb_state['modal_running'] = False
        _khb_state['modal_op'] = None
        
        # Cleanup resources
        khb_cleanup_icons()
        
        _khb_state['enabled'] = False
        khb_force_redraw()
        
        print("❌ KHB_Display: Display system disabled!")
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Disable error: {e}")
        _khb_state['enabled'] = False

def khb_is_enabled():
    """Check if system is enabled"""
    return _khb_state['enabled']

def khb_force_redraw():
    """Force redraw all 3D viewports"""
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except Exception:
        pass

def khb_emergency_cleanup():
    """Emergency cleanup of all resources"""
    global _khb_state
    
    try:
        # Force disable
        khb_disable_display_system()
        
        # Reset all state
        _khb_state = {
            'enabled': False, 'handler': None, 'modal_op': None, 'modal_running': False,
            'pcoll': None, 'icons_loaded': False, 'buttons': [], 'last_click_time': 0,
            'settings': {'show_buttons': True, 'position': 'BOTTOM_LEFT', 'use_png': True}
        }
        
        # Force garbage collection
        import gc
        gc.collect()
        
        print("🧹 KHB_Display: Emergency cleanup completed")
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Emergency cleanup error: {e}")

# ==== SETTINGS UPDATE FUNCTIONS ====
def khb_update_button_settings(settings):
    """Update button settings"""
    global _khb_state
    _khb_state['settings'].update(settings)
    khb_init_buttons()  # Reinitialize with new settings

def khb_update_icon_settings(settings):
    """Update icon settings"""
    global _khb_state
    _khb_state['settings'].update(settings)
    if 'use_png' in settings:
        # Reload icons if PNG setting changed
        khb_cleanup_icons()
        if _khb_state['enabled'] and settings['use_png']:
            khb_load_icons()

def khb_reload_icons():
    """Reload all icons"""
    global _khb_state
    khb_cleanup_icons()
    if _khb_state['enabled']:
        return khb_load_icons()
    return True

# ==== MODAL OPERATOR ====
class KHB_DISPLAY_OT_modal_handler(Operator):
    """Modal handler for button interactions"""
    bl_idname = "khb_display.modal_handler"
    bl_label = "KHB Display Modal Handler"
    
    def modal(self, context, event):
        global _khb_state
        
        # Handle mouse clicks
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if khb_handle_click(event.mouse_region_x, event.mouse_region_y):
                return {'RUNNING_MODAL'}
        
        # Stop if system disabled
        if not _khb_state['enabled'] or not _khb_state['modal_running']:
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        global _khb_state
        
        if context.area and context.area.type == 'VIEW_3D':
            _khb_state['modal_op'] = self
            _khb_state['modal_running'] = True
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        
        return {'CANCELLED'}

# ==== LEGACY COMPATIBILITY CLASSES ====
class KHB_IconManager:
    def khb_load_icons(self): return khb_load_icons()
    def khb_cleanup(self): return khb_cleanup_icons()

class KHB_DisplayManager:
    def khb_enable_display_system(self): return khb_enable_display_system()
    def khb_disable_display_system(self): return khb_disable_display_system()
    def khb_is_enabled(self): return khb_is_enabled()
    def khb_force_redraw(self): return khb_force_redraw()

class KHB_ButtonManager:
    def khb_update_settings(self, settings): return khb_update_button_settings(settings)

# Global instances for compatibility
khb_icon_manager = KHB_IconManager()
khb_display_manager = KHB_DisplayManager()
khb_button_manager = KHB_ButtonManager()

# ==== REGISTRATION ====
khb_classes = (
    KHB_DISPLAY_OT_modal_handler,
)

def register():
    """Register display system"""
    for cls in khb_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"❌ KHB_Display: Registration failed {cls.__name__}: {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Registered")

def unregister():
    """Unregister display system"""
    print(f"🛑 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistering...")
    
    # Emergency cleanup
    khb_emergency_cleanup()
    
    # Unregister classes
    for cls in reversed(khb_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KHB_Display: Unregister error: {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistered")

if __name__ == "__main__":
    register()
