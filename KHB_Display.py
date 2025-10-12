"""
KHB_Display - KeyHabit Display System
Version: 1.0.6-FINAL (Fixed texture size + working buttons)
"""

import bpy
from bpy.types import Operator
import bpy.utils.previews
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import os
from pathlib import Path

# ==== GLOBAL STATE ====
_khb_state = {
    'handler': None,
    'modal_op': None,
    'enabled': False,
    'pcoll': None,
    'icons_loaded': False,
    'buttons': [],
    'modal_running': False,
    'last_click_time': 0
}

# ==== CONSTANTS ====
KHB_DISPLAY_VERSION = "1.0.6-FINAL"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18
KHB_BUTTON_SIZE = 28

# ==== COLORS ====
class KHB_DisplayColors:
    BOX = (1.0, 0.45, 0.0, 1.0)
    LABEL = (1.0, 0.45, 0.0, 1.0)
    VALUE = (0.85, 0.92, 0.4, 1.0)
    NUMBER = (1.0, 1.0, 1.0, 1.0)
    ACTIVE = (0.2, 0.6, 1.0, 1.0)
    INACTIVE = (1.0, 0.25, 0.17, 1.0)
    FUNCTION = (1.0, 0.45, 0.0, 1.0)
    SOURCE = (1.0, 1.0, 1.0, 1.0)

# ==== MODIFIER ICONS ====
KHB_MODIFIER_ICONS = {
    'ARRAY': 'blender_icon_mod_array.png',
    'BEVEL': 'blender_icon_mod_bevel.png', 
    'BOOLEAN': 'blender_icon_mod_boolean.png',
    'BUILD': 'blender_icon_mod_build.png',
    'DECIMATE': 'blender_icon_mod_decim.png',
    'MIRROR': 'blender_icon_mod_mirror.png',
    'SOLIDIFY': 'blender_icon_mod_solidify.png',
    'SUBSURF': 'blender_icon_mod_subsurf.png',
    'DISPLACE': 'blender_icon_mod_displace.png',
    'NODES': 'blender_icon_geometry_nodes.png',
    'TRIANGULATE': 'blender_icon_mod_triangulate.png',
    'WELD': 'blender_icon_mod_weld.png',
}
KHB_FALLBACK_ICON = 'blender_icon_question.png'

# ==== ICON FUNCTIONS ====
def khb_load_icons():
    """Load PNG icons with correct size detection"""
    global _khb_state
    
    if _khb_state['icons_loaded']:
        return True
    
    try:
        # Cleanup first
        khb_cleanup_icons()
        
        # Create preview collection
        pcoll = bpy.utils.previews.new()
        
        # Get icons directory
        addon_dir = Path(__file__).parent
        icons_dir = addon_dir / "icons"
        
        if not icons_dir.exists():
            print(f"❌ KHB_Display: Icons directory not found: {icons_dir}")
            bpy.utils.previews.remove(pcoll)
            return False
        
        loaded = 0
        
        # Load fallback first
        fallback_path = icons_dir / KHB_FALLBACK_ICON
        if fallback_path.exists():
            pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
            loaded += 1
            print("✅ KHB_Display: Loaded fallback icon")
        
        # Load modifier icons
        for mod_type, filename in KHB_MODIFIER_ICONS.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                try:
                    pcoll.load(mod_type, str(icon_path), 'IMAGE')
                    loaded += 1
                except Exception as e:
                    print(f"⚠️ KHB_Display: Failed to load {filename}: {e}")
        
        _khb_state['pcoll'] = pcoll
        _khb_state['icons_loaded'] = True
        
        print(f"🎨 KHB_Display: Icon system initialized ({loaded} icons loaded)")
        return True
        
    except Exception as e:
        print(f"❌ KHB_Display: Icon loading failed: {e}")
        return False

def khb_cleanup_icons():
    """Cleanup icon collection"""
    global _khb_state
    
    if _khb_state['pcoll']:
        try:
            bpy.utils.previews.remove(_khb_state['pcoll'])
            print("🧹 KHB_Display: Icons cleaned up")
        except Exception as e:
            print(f"⚠️ KHB_Display: Cleanup error: {e}")
        _khb_state['pcoll'] = None
    
    _khb_state['icons_loaded'] = False

def khb_get_icon_texture(mod_type):
    """Get GPU texture with CORRECT size detection"""
    global _khb_state
    
    if not _khb_state['pcoll']:
        return None
    
    # Try specific modifier icon first
    preview = _khb_state['pcoll'].get(mod_type) or _khb_state['pcoll'].get("FALLBACK")
    if preview and hasattr(preview, 'icon_pixels_float') and preview.icon_pixels_float:
        try:
            icon_data = preview.icon_pixels_float
            data_size = len(icon_data)
            
            # Calculate actual icon size (icons are square)
            # RGBA = 4 components per pixel
            pixels_count = data_size // 4
            icon_size = int(pixels_count ** 0.5)
            
            print(f"🎨 KHB_Display: Icon data size: {data_size}, calculated size: {icon_size}x{icon_size}")
            
            if icon_size > 0 and icon_size * icon_size * 4 == data_size:
                # Create GPU texture with correct size
                import numpy as np
                pixels = np.array(icon_data).reshape((icon_size, icon_size, 4))
                texture = gpu.types.GPUTexture((icon_size, icon_size), format='RGBA8', data=pixels)
                print(f"✅ KHB_Display: Created texture for {mod_type}: {icon_size}x{icon_size}")
                return texture
            else:
                print(f"⚠️ KHB_Display: Invalid icon size calculation for {mod_type}")
                
        except Exception as e:
            print(f"⚠️ KHB_Display: Texture conversion failed for {mod_type}: {e}")
    
    return None

# ==== BUTTON SYSTEM ====
def khb_init_buttons():
    """Initialize control buttons with better positioning"""
    global _khb_state
    
    if _khb_state['buttons']:
        return  # Already initialized
    
    _khb_state['buttons'] = [
        {'id': 'wireframe', 'label': 'W', 'x': 60, 'y': 40, 'op': 'wireframe'},
        {'id': 'edge_length', 'label': 'E', 'x': 95, 'y': 40, 'op': 'edge_length'},
        {'id': 'retopo', 'label': 'R', 'x': 130, 'y': 40, 'op': 'retopo'},
        {'id': 'split_normals', 'label': 'S', 'x': 165, 'y': 40, 'op': 'split_normals'}
    ]
    
    print(f"🎮 KHB_Display: {len(_khb_state['buttons'])} control buttons initialized")

def khb_draw_buttons():
    """Draw control buttons with better visuals"""
    global _khb_state
    
    if not _khb_state['buttons']:
        khb_init_buttons()
    
    font_id = 0
    blf.size(font_id, 12)
    
    for btn in _khb_state['buttons']:
        x, y = btn['x'], btn['y']
        size = KHB_BUTTON_SIZE
        
        # Get button state
        is_active = khb_get_overlay_state(btn['id'])
        
        # Button colors
        if is_active:
            bg_color = (0.1, 0.8, 0.2, 0.9)  # Bright green when active
            border_color = (1.0, 1.0, 1.0, 1.0)  # White border
            text_color = (1.0, 1.0, 1.0, 1.0)
        else:
            bg_color = (0.2, 0.2, 0.2, 0.8)  # Dark gray when inactive
            border_color = (0.6, 0.6, 0.6, 0.8)  # Gray border
            text_color = (0.9, 0.9, 0.9, 1.0)
        
        try:
            # Draw button background
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = [(x, y), (x+size, y), (x+size, y+size), (x, y+size)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", bg_color)
            batch.draw(shader)
            
            # Draw button border
            border_positions = [(x-1, y-1), (x+size+1, y-1), (x+size+1, y+size+1), (x-1, y+size+1), (x-1, y-1)]
            border_batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": border_positions})
            shader.uniform_float("color", border_color)
            border_batch.draw(shader)
            
            gpu.state.blend_set('NONE')
            
            # Draw button label (centered)
            text_x = x + (size // 2) - 4  # Center text
            text_y = y + (size // 2) - 6
            
            blf.position(font_id, text_x, text_y, 0)
            blf.color(font_id, *text_color)
            blf.draw(font_id, btn['label'])
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Button draw error for {btn['id']}: {e}")

def khb_get_overlay_state(button_id):
    """Get current overlay state"""
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
    except Exception as e:
        print(f"⚠️ KHB_Display: Overlay state check failed: {e}")
    return False

def khb_handle_button_click(mouse_x, mouse_y):
    """Handle button clicks with debouncing"""
    global _khb_state
    import time
    
    current_time = time.time()
    if current_time - _khb_state['last_click_time'] < 0.3:  # 300ms debounce
        return False
    
    for btn in _khb_state['buttons']:
        x, y, size = btn['x'], btn['y'], KHB_BUTTON_SIZE
        
        # Check if click is within button bounds
        if x <= mouse_x <= x + size and y <= mouse_y <= y + size:
            try:
                # Execute overlay toggle directly
                success = False
                for area in bpy.context.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                overlay = space.overlay
                                
                                if btn['op'] == 'wireframe':
                                    overlay.show_wireframes = not overlay.show_wireframes
                                    success = True
                                elif btn['op'] == 'edge_length':
                                    overlay.show_extra_edge_length = not overlay.show_extra_edge_length
                                    success = True
                                elif btn['op'] == 'retopo':
                                    overlay.show_retopology = not overlay.show_retopology
                                    success = True
                                elif btn['op'] == 'split_normals':
                                    overlay.show_split_normals = not overlay.show_split_normals
                                    success = True
                                
                                if success:
                                    area.tag_redraw()
                                    _khb_state['last_click_time'] = current_time
                                    print(f"🎯 KHB_Display: Button '{btn['label']}' clicked - {btn['op']} toggled")
                                    return True
                                    
            except Exception as e:
                print(f"⚠️ KHB_Display: Button execution error for {btn['id']}: {e}")
    
    return False

# ==== DRAWING FUNCTIONS ====
def khb_draw_modifier_icon(font_id, x, y, mod_type, size=KHB_ICON_SIZE_PX):
    """Draw modifier icon - PNG with fallback"""
    
    # Try to draw PNG texture first
    texture = khb_get_icon_texture(mod_type)
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
            
            # Only log success occasionally to avoid spam
            return size
        except Exception as e:
            print(f"⚠️ KHB_Display: PNG draw failed for {mod_type}: {e}")
    
    # Fallback: Draw text abbreviation with better styling
    blf.size(font_id, size - 1)
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1.0, 0.7, 0.0, 1.0)  # Orange
    
    # Create abbreviation map
    abbrev_map = {
        'BOOLEAN': 'BO', 'MIRROR': 'MI', 'ARRAY': 'AR', 'BEVEL': 'BV',
        'SUBSURF': 'SS', 'SOLIDIFY': 'SO', 'DISPLACE': 'DI', 'NODES': 'GN',
        'TRIANGULATE': 'TR', 'DECIMATE': 'DE', 'BUILD': 'BU', 'WELD': 'WE'
    }
    
    icon_text = abbrev_map.get(mod_type, mod_type[:2])
    blf.draw(font_id, icon_text)
    
    return size

def khb_get_modifier_text(modifier):
    """Get modifier text with colors"""
    colors = KHB_DisplayColors()
    tc = []
    
    # Basic modifier info
    display_name = modifier.type.replace('_', ' ').title()
    tc.extend([
        ('[', colors.BOX),
        (display_name, colors.LABEL),
        (']', colors.BOX),
        (' ' + modifier.name, colors.NUMBER)
    ])
    
    # Add specific modifier details
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
    
    elif modifier.type == 'NODES':
        # Special handling for Geometry Nodes
        if "Smooth by Angle" in modifier.name or "Shade Auto Smooth" in modifier.name:
            tc[1] = ('Shade Auto Smooth', colors.LABEL)  # Replace display name
            
            # Try to get angle value
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
            # Draw each modifier
            for modifier in reversed(obj.modifiers):
                x = 20
                
                # Draw modifier icon
                icon_w = khb_draw_modifier_icon(font_id, x, y, modifier.type)
                x += icon_w + KHB_ICON_PAD_PX
                
                # Draw modifier text
                text_pairs = khb_get_modifier_text(modifier)
                for text, color in text_pairs:
                    blf.position(font_id, x, y, 0)
                    blf.color(font_id, *color)
                    blf.draw(font_id, text)
                    text_w = blf.dimensions(font_id, text)[0]
                    x += int(text_w)
                
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

# ==== DISPLAY SYSTEM CONTROL ====
def khb_enable_display_system():
    """Enable display system"""
    global _khb_state
    
    if _khb_state['enabled']:
        return
    
    try:
        # Load icons (suppress texture conversion errors for now)
        khb_load_icons()
        
        # Initialize buttons
        khb_init_buttons()
        
        # Add draw handler
        _khb_state['handler'] = bpy.types.SpaceView3D.draw_handler_add(
            khb_draw_overlay, (), 'WINDOW', 'POST_PIXEL'
        )
        
        # Start modal handler for button interactions
        if not _khb_state['modal_running']:
            try:
                bpy.ops.khb_overlay.modal_handler('INVOKE_DEFAULT')
                print("🎮 KHB_Display: Modal handler started")
            except Exception as e:
                print(f"⚠️ KHB_Display: Modal start failed: {e}")
        
        _khb_state['enabled'] = True
        khb_force_redraw()
        
        print("✅ KHB_Display: Display system enabled!")
        
    except Exception as e:
        print(f"❌ KHB_Display: Enable failed: {e}")

def khb_disable_display_system():
    """Disable display system"""
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
        
        # Cleanup icons
        khb_cleanup_icons()
        
        # Reset state
        _khb_state['enabled'] = False
        _khb_state['buttons'].clear()
        
        khb_force_redraw()
        print("❌ KHB_Display: Display system disabled!")
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Disable error: {e}")

def khb_is_enabled():
    return _khb_state['enabled']

def khb_force_redraw():
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except:
        pass

# ==== MODAL OPERATOR FOR BUTTON CLICKS ====
class KHB_OVERLAY_OT_modal_handler(Operator):
    """Modal handler for button interactions"""
    bl_idname = "khb_overlay.modal_handler"
    bl_label = "KHB Overlay Modal Handler"
    
    def modal(self, context, event):
        global _khb_state
        
        # Handle left mouse clicks
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y
            
            print(f"🎯 KHB_Display: Click at ({mouse_x}, {mouse_y})")
            
            # Try to handle button click
            if khb_handle_button_click(mouse_x, mouse_y):
                # Button was clicked, force redraw
                khb_force_redraw()
                return {'RUNNING_MODAL'}
        
        # Check if system is still enabled
        if not _khb_state['enabled'] or not _khb_state['modal_running']:
            print("🛑 KHB_Display: Modal handler stopping")
            return {'CANCELLED'}
        
        # Pass through all other events
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        global _khb_state
        
        if context.area and context.area.type == 'VIEW_3D':
            _khb_state['modal_op'] = self
            _khb_state['modal_running'] = True
            context.window_manager.modal_handler_add(self)
            print("🎮 KHB_Display: Modal handler active for button interactions")
            return {'RUNNING_MODAL'}
        else:
            print("⚠️ KHB_Display: Modal invoke failed - not in VIEW_3D")
            return {'CANCELLED'}

# ==== LEGACY COMPATIBILITY ====
class KHB_IconManager:
    def khb_load_icons(self): return khb_load_icons()
    def khb_cleanup(self): khb_cleanup_icons()

class KHB_DisplayManager:
    def khb_enable_display_system(self): khb_enable_display_system()
    def khb_disable_display_system(self): khb_disable_display_system()
    def khb_is_enabled(self): return khb_is_enabled()
    def khb_force_redraw(self): khb_force_redraw()

class KHB_ButtonManager:
    def khb_update_settings(self, settings): pass

# Global instances
khb_icon_manager = KHB_IconManager()
khb_display_manager = KHB_DisplayManager()
khb_button_manager = KHB_ButtonManager()

# ==== REGISTRATION ====
khb_display_classes = (
    KHB_OVERLAY_OT_modal_handler,
)

def register():
    for cls in khb_display_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"❌ KHB_Display: Registration failed {cls.__name__}: {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Registered")

def unregister():
    print("🛑 KHB_Display: Unregistering...")
    
    # Force disable
    khb_disable_display_system()
    
    # Clean global state
    global _khb_state
    try:
        if _khb_state['handler']:
            bpy.types.SpaceView3D.draw_handler_remove(_khb_state['handler'], 'WINDOW')
        if _khb_state['pcoll']:
            bpy.utils.previews.remove(_khb_state['pcoll'])
    except:
        pass
    
    # Reset state
    _khb_state = {
        'handler': None, 'modal_op': None, 'enabled': False,
        'pcoll': None, 'icons_loaded': False, 'buttons': [],
        'modal_running': False, 'last_click_time': 0
    }
    
    # Unregister classes
    for cls in reversed(khb_display_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KHB_Display: Unregister error: {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistered")

if __name__ == "__main__":
    register()
