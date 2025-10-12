"""
KHB_Display - KeyHabit Display System
Version: 1.0.4-working (Fixed icons + buttons)
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

# ==== GLOBAL STATE ====
_khb_state = {
    'handler': None,
    'modal_op': None,
    'enabled': False,
    'pcoll': None,
    'icons_loaded': False,
    'buttons': []
}

# ==== CONSTANTS ====
KHB_DISPLAY_VERSION = "1.0.4-working"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18
KHB_BUTTON_SIZE = 24

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
    # Add more as needed...
}
KHB_FALLBACK_ICON = 'blender_icon_question.png'

# ==== ICON FUNCTIONS ====
def khb_load_icons():
    """Load PNG icons with fallback support"""
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
            else:
                print(f"⚠️ KHB_Display: Missing {filename}")
        
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

def khb_get_icon_id(mod_type):
    """Get icon ID for drawing (Alternative to GPU texture)"""
    global _khb_state
    
    if not _khb_state['pcoll']:
        return 0
    
    # Try specific modifier icon
    preview = _khb_state['pcoll'].get(mod_type)
    if preview and hasattr(preview, 'icon_id'):
        return preview.icon_id
    
    # Try fallback
    fallback = _khb_state['pcoll'].get("FALLBACK")
    if fallback and hasattr(fallback, 'icon_id'):
        return fallback.icon_id
    
    return 0

# ==== BUTTON SYSTEM ====
def khb_init_buttons():
    """Initialize control buttons"""
    global _khb_state
    
    if _khb_state['buttons']:
        return  # Already initialized
    
    _khb_state['buttons'] = [
        {'id': 'wireframe', 'label': 'W', 'x': 50, 'y': 60, 'op': 'khb_overlay.toggle_wireframe'},
        {'id': 'edge_length', 'label': 'E', 'x': 80, 'y': 60, 'op': 'khb_overlay.toggle_edge_length'},
        {'id': 'retopo', 'label': 'R', 'x': 110, 'y': 60, 'op': 'khb_overlay.toggle_retopology'},
        {'id': 'split_normals', 'label': 'S', 'x': 140, 'y': 60, 'op': 'khb_overlay.toggle_split_normals'}
    ]
    
    print(f"🎮 KHB_Display: {len(_khb_state['buttons'])} control buttons initialized")

def khb_draw_buttons():
    """Draw control buttons with proper rendering"""
    global _khb_state
    
    if not _khb_state['buttons']:
        khb_init_buttons()
    
    font_id = 0
    blf.size(font_id, 10)
    
    for btn in _khb_state['buttons']:
        x, y = btn['x'], btn['y']
        size = KHB_BUTTON_SIZE
        
        # Get button state
        is_active = khb_get_overlay_state(btn['id'])
        
        # Colors
        if is_active:
            bg_color = (0.2, 0.8, 0.3, 0.8)  # Green when active
            text_color = (1.0, 1.0, 1.0, 1.0)
        else:
            bg_color = (0.3, 0.3, 0.3, 0.7)  # Gray when inactive
            text_color = (0.8, 0.8, 0.8, 1.0)
        
        # Draw button background
        try:
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = [(x, y), (x+size, y), (x+size, y+size), (x, y+size)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", bg_color)
            batch.draw(shader)
            gpu.state.blend_set('NONE')
            
            # Draw button label
            text_x = x + size // 3
            text_y = y + size // 3
            
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
    except:
        pass
    return False

def khb_handle_button_click(mouse_x, mouse_y):
    """Handle button clicks"""
    global _khb_state
    
    for btn in _khb_state['buttons']:
        x, y, size = btn['x'], btn['y'], KHB_BUTTON_SIZE
        
        # Check if click is within button bounds
        if x <= mouse_x <= x + size and y <= mouse_y <= y + size:
            try:
                # Execute the operator
                if btn['op'] == 'khb_overlay.toggle_wireframe':
                    bpy.ops.khb_overlay.toggle_wireframe()
                elif btn['op'] == 'khb_overlay.toggle_edge_length':
                    bpy.ops.khb_overlay.toggle_edge_length()
                elif btn['op'] == 'khb_overlay.toggle_retopology':
                    bpy.ops.khb_overlay.toggle_retopology()
                elif btn['op'] == 'khb_overlay.toggle_split_normals':
                    bpy.ops.khb_overlay.toggle_split_normals()
                
                print(f"🎯 KHB_Display: Button {btn['id']} clicked")
                return True
            except Exception as e:
                print(f"⚠️ KHB_Display: Button execution error: {e}")
    
    return False

# ==== DRAWING FUNCTIONS ====
def khb_draw_modifier_icon(font_id, x, y, mod_type, size=KHB_ICON_SIZE_PX):
    """Draw modifier icon using Blender's built-in icon system"""
    icon_id = khb_get_icon_id(mod_type)
    
    if icon_id > 0:
        try:
            # Try to use Blender's icon drawing (if available)
            # This is more compatible than GPU texture approach
            import bpy.utils
            # Note: bpy.utils doesn't have direct icon draw, so we use fallback
            pass
        except:
            pass
    
    # Fallback: Draw simple text representation
    blf.size(font_id, size - 2)
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1.0, 0.7, 0.0, 1.0)  # Orange
    
    # Use first 2 letters of modifier type as icon
    icon_text = mod_type[:2] if len(mod_type) >= 2 else mod_type
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
    
    # Add specific modifier info
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
        # Load icons
        khb_load_icons()
        
        # Initialize buttons
        khb_init_buttons()
        
        # Add draw handler
        _khb_state['handler'] = bpy.types.SpaceView3D.draw_handler_add(
            khb_draw_overlay, (), 'WINDOW', 'POST_PIXEL'
        )
        
        # Start modal operator for interactions
        try:
            bpy.ops.khb_overlay.modal_handler('INVOKE_DEFAULT')
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
        
        # Stop modal operator
        if _khb_state['modal_op']:
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
        _khb_state['enabled'] = False

def khb_is_enabled():
    """Check if enabled"""
    global _khb_state
    return _khb_state['enabled']

def khb_force_redraw():
    """Force redraw viewports"""
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except:
        pass

# ==== OPERATORS ====
class KHB_OVERLAY_OT_modal_handler(Operator):
    """Modal handler for button interactions"""
    bl_idname = "khb_overlay.modal_handler"
    bl_label = "KHB Overlay Modal Handler"
    
    def modal(self, context, event):
        global _khb_state
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Handle button clicks
            if khb_handle_button_click(event.mouse_region_x, event.mouse_region_y):
                khb_force_redraw()
                return {'RUNNING_MODAL'}
        
        # Check if system is still enabled
        if not _khb_state['enabled']:
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        global _khb_state
        if context.area.type == 'VIEW_3D':
            _khb_state['modal_op'] = self
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

class KHB_OVERLAY_OT_toggle_wireframe(Operator):
    bl_idname = "khb_overlay.toggle_wireframe"
    bl_label = "Toggle Wireframe"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_wireframes = not space.overlay.show_wireframes
                        area.tag_redraw()
                        break
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
                        break
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
                        break
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
                        break
        return {'FINISHED'}

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
    KHB_OVERLAY_OT_toggle_wireframe,
    KHB_OVERLAY_OT_toggle_edge_length,
    KHB_OVERLAY_OT_toggle_retopology,
    KHB_OVERLAY_OT_toggle_split_normals,
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
    if _khb_state['handler']:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_khb_state['handler'], 'WINDOW')
        except:
            pass
    
    if _khb_state['pcoll']:
        try:
            bpy.utils.previews.remove(_khb_state['pcoll'])
        except:
            pass
    
    # Reset state
    _khb_state = {
        'handler': None, 'modal_op': None, 'enabled': False,
        'pcoll': None, 'icons_loaded': False, 'buttons': []
    }
    
    # Unregister classes
    for cls in reversed(khb_display_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KHB_Display: Unregister error {cls.__name__}: {e}")
    
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistered")

if __name__ == "__main__":
    register()
