"""
KHB_Display - KeyHabit Display System
Version: 2.0.0-text-only
Chỉ hiển thị thông tin modifier dạng text và icon.
"""

import bpy
import bpy.utils.previews
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from pathlib import Path

# ==== VERSION & CONSTANTS ====
KHB_DISPLAY_VERSION = "2.0.0-text-only"
KHB_ICON_SIZE_PX = 16
KHB_ICON_PAD_PX = 4
KHB_LINE_HEIGHT = 18

# ==== GLOBAL STATE ====
_khb_state = {
    'enabled': False,
    'handler': None,
    'pcoll': None,
    'icons_loaded': False,
    'settings': {
        'use_png': True,
    }
}

# (Các class màu sắc, icon mapping, và hàm load icon vẫn được giữ nguyên)
# ==== COLOR SYSTEM ====
class KHB_Colors:
    BOX = (1.0, 0.45, 0.0, 1.0)
    LABEL = (1.0, 0.45, 0.0, 1.0)
    VALUE = (0.85, 0.92, 0.4, 1.0)
    NUMBER = (1.0, 1.0, 1.0, 1.0)
    ACTIVE = (0.2, 0.6, 1.0, 1.0)
    INACTIVE = (1.0, 0.25, 0.17, 1.0)
    FUNCTION = (1.0, 0.45, 0.0, 1.0)
    SOURCE = (1.0, 1.0, 1.0, 1.0)
    ICON_COLORS = {'BOOLEAN': (1.0, 0.3, 0.3, 0.8), 'MIRROR': (0.3, 0.8, 0.3, 0.8), 'ARRAY': (0.3, 0.3, 1.0, 0.8), 'BEVEL': (1.0, 1.0, 0.3, 0.8), 'SUBSURF': (1.0, 0.3, 1.0, 0.8), 'SOLIDIFY': (0.3, 1.0, 1.0, 0.8), 'DISPLACE': (1.0, 0.6, 0.3, 0.8), 'NODES': (0.6, 0.3, 1.0, 0.8), 'TRIANGULATE': (0.8, 0.8, 0.8, 0.8)}

# ==== MODIFIER ICON MAPPING ====
KHB_MODIFIER_ICONS = {
    'ARRAY': 'blender_icon_mod_array.png', 'BEVEL': 'blender_icon_mod_bevel.png', 'BOOLEAN': 'blender_icon_mod_boolean.png', 'BUILD': 'blender_icon_mod_build.png', 'DECIMATE': 'blender_icon_mod_decim.png', 'EDGE_SPLIT': 'blender_icon_mod_edgesplit.png', 'MASK': 'blender_icon_mod_mask.png', 'MIRROR': 'blender_icon_mod_mirror.png', 'MULTIRES': 'blender_icon_mod_multires.png', 'REMESH': 'blender_icon_mod_remesh.png', 'SCREW': 'blender_icon_mod_screw.png', 'SKIN': 'blender_icon_mod_skin.png', 'SOLIDIFY': 'blender_icon_mod_solidify.png', 'SUBSURF': 'blender_icon_mod_subsurf.png', 'TRIANGULATE': 'blender_icon_mod_triangulate.png', 'WELD': 'blender_icon_mod_weld.png', 'WIREFRAME': 'blender_icon_mod_wireframe.png', 'CAST': 'blender_icon_mod_cast.png', 'CURVE': 'blender_icon_mod_curve.png', 'DISPLACE': 'blender_icon_mod_displace.png', 'LATTICE': 'blender_icon_mod_lattice.png', 'MESH_DEFORM': 'blender_icon_mod_meshdeform.png', 'SHRINKWRAP': 'blender_icon_mod_shrinkwrap.png', 'SIMPLE_DEFORM': 'blender_icon_mod_simpledeform.png', 'SMOOTH': 'blender_icon_mod_smooth.png', 'DATA_TRANSFER': 'blender_icon_mod_data_transfer.png', 'NORMAL_EDIT': 'blender_icon_mod_normaledit.png', 'UV_PROJECT': 'blender_icon_mod_uvproject.png', 'CLOTH': 'blender_icon_mod_cloth.png', 'DYNAMIC_PAINT': 'blender_icon_mod_dynamicpaint.png', 'FLUID': 'blender_icon_mod_fluidsim.png', 'OCEAN': 'blender_icon_mod_ocean.png', 'PARTICLE_INSTANCE': 'blender_icon_mod_particle_instance.png', 'PARTICLE_SYSTEM': 'blender_icon_mod_particles.png', 'SOFT_BODY': 'blender_icon_mod_soft.png', 'NODES': 'blender_icon_geometry_nodes.png'
}
KHB_FALLBACK_ICON = 'blender_icon_question.png'
KHB_TEXT_ABBREV = {
    'BOOLEAN': 'BO', 'MIRROR': 'MI', 'ARRAY': 'AR', 'BEVEL': 'BV', 'SUBSURF': 'SS', 'SOLIDIFY': 'SO', 'DISPLACE': 'DI', 'NODES': 'GN', 'TRIANGULATE': 'TR', 'DECIMATE': 'DE', 'BUILD': 'BU', 'WELD': 'WE', 'CAST': 'CA', 'CURVE': 'CV', 'LATTICE': 'LA', 'MESH_DEFORM': 'MD', 'SHRINKWRAP': 'SW', 'SIMPLE_DEFORM': 'SD', 'SMOOTH': 'SM', 'DATA_TRANSFER': 'DT', 'NORMAL_EDIT': 'NE', 'UV_PROJECT': 'UV', 'CLOTH': 'CL', 'DYNAMIC_PAINT': 'DP', 'FLUID': 'FL', 'OCEAN': 'OC'
}


def khb_load_icons():
    global _khb_state
    if _khb_state['icons_loaded'] or not _khb_state['settings']['use_png']: return True
    try:
        khb_cleanup_icons()
        pcoll = bpy.utils.previews.new()
        addon_dir = Path(__file__).parent
        icons_dir = addon_dir / "icons"
        if not icons_dir.exists():
            print("⚠️ KHB_Display: Icons directory not found, using fallbacks")
            bpy.utils.previews.remove(pcoll)
            return False
        
        loaded_count = 0
        fallback_path = icons_dir / KHB_FALLBACK_ICON
        if fallback_path.exists():
            pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
            loaded_count += 1
        
        for mod_type, filename in KHB_MODIFIER_ICONS.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                try:
                    pcoll.load(mod_type, str(icon_path), 'IMAGE')
                    loaded_count += 1
                except Exception: pass
        
        _khb_state['pcoll'] = pcoll
        _khb_state['icons_loaded'] = True
        print(f"🎨 KHB_Display: Icon system initialized ({loaded_count} icons).")
        return True
    except Exception as e:
        print(f"⚠️ KHB_Display: Icon loading failed - {e}")
        return False

def khb_cleanup_icons():
    global _khb_state
    if _khb_state['pcoll']:
        bpy.utils.previews.remove(_khb_state['pcoll'])
        _khb_state['pcoll'] = None
    _khb_state['icons_loaded'] = False

def khb_get_texture(mod_type):
    global _khb_state
    if not _khb_state['pcoll'] or not _khb_state['settings']['use_png']: return None
    preview = _khb_state['pcoll'].get(mod_type) or _khb_state['pcoll'].get("FALLBACK")
    if preview:
        try:
            icon_data = preview.icon_pixels_float
            if not icon_data: return None
            data_size = len(icon_data)
            pixels_count = data_size // 4
            icon_size = int(pixels_count ** 0.5)
            if icon_size > 0 and icon_size * icon_size * 4 == data_size:
                import numpy as np
                pixels = np.array(icon_data, dtype=np.float32).reshape((icon_size, icon_size, 4))
                buffer_data = gpu.types.Buffer('FLOAT', (icon_size, icon_size, 4), pixels)
                return gpu.types.GPUTexture((icon_size, icon_size), format='RGBA8', data=buffer_data)
        except Exception: pass
    return None

def khb_draw_icon(font_id, x, y, mod_type, size=None):
    if size is None: size = KHB_ICON_SIZE_PX
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
            except Exception: pass
    
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
    except Exception: pass
    
    blf.size(font_id, size - 1)
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 1.0, 0.7, 0.0, 1.0)
    text = KHB_TEXT_ABBREV.get(mod_type, mod_type[:2])
    blf.draw(font_id, text)
    return size

def khb_get_modifier_text(modifier):
    colors = KHB_Colors()
    tc = []
    display_name = modifier.type.replace('_', ' ').title()
    tc.extend([('(', colors.BOX), (display_name, colors.LABEL), (')', colors.BOX), (' ' + modifier.name, colors.NUMBER)])
    if modifier.type == 'BOOLEAN':
        op = getattr(modifier, 'operation', '')
        if op: tc.append((' ' + op, colors.FUNCTION))
        obj = getattr(modifier, 'object', None)
        if obj: tc.append((' → ' + obj.name, colors.SOURCE))
    elif modifier.type == 'MIRROR':
        axes = getattr(modifier, 'use_axis', [False, False, False])
        for i, axis in enumerate(['X', 'Y', 'Z']):
            color = colors.ACTIVE if (i < len(axes) and axes[i]) else colors.INACTIVE
            tc.append((' ' + axis, color))
    elif modifier.type == 'ARRAY':
        tc.extend([(' ×', colors.VALUE), (str(getattr(modifier, 'count', 1)), colors.NUMBER)])
    elif modifier.type == 'SUBSURF':
        tc.extend([(' Lv', colors.VALUE), (str(getattr(modifier, 'levels', 0)), colors.NUMBER)])
    elif modifier.type == 'BEVEL':
        tc.extend([(' W:', colors.VALUE), (f"{getattr(modifier, 'width', 0):.3f}", colors.NUMBER), (' S:', colors.VALUE), (str(getattr(modifier, 'segments', 1)), colors.NUMBER)])
    elif modifier.type == 'NODES' and ("Smooth by Angle" in modifier.name or "Shade Auto Smooth" in modifier.name):
        tc[1] = ('Shade Auto Smooth', colors.LABEL)
        if "Input_1" in modifier.keys():
            import math
            angle_deg = round(modifier["Input_1"] * 180 / math.pi, 1)
            tc.extend([(' Angle:', colors.VALUE), (f"{angle_deg}°", colors.NUMBER)])
    return tc

def khb_draw_overlay():
    try:
        font_id = 0
        blf.size(font_id, 12)
        obj = bpy.context.active_object
        y = 15
        
        if obj and obj.type == 'MESH' and obj.modifiers:
            for modifier in reversed(obj.modifiers):
                x = 20
                icon_width = khb_draw_icon(font_id, x, y, modifier.type)
                x += icon_width + KHB_ICON_PAD_PX
                text_pairs = khb_get_modifier_text(modifier)
                for text, color in text_pairs:
                    blf.position(font_id, x, y, 0)
                    blf.color(font_id, *color)
                    blf.draw(font_id, text)
                    x += int(blf.dimensions(font_id, text)[0])
                y += KHB_LINE_HEIGHT
        else:
            blf.position(font_id, 20, y, 0)
            blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
            blf.draw(font_id, "Select MESH object with modifiers")
            
    except Exception as e:
        print(f"⚠️ KHB_Display: Overlay draw error: {e}")

# ==== SYSTEM CONTROL ====
def khb_enable_display_system():
    global _khb_state
    if _khb_state['enabled']: return True
    try:
        khb_load_icons()
        _khb_state['handler'] = bpy.types.SpaceView3D.draw_handler_add(khb_draw_overlay, (), 'WINDOW', 'POST_PIXEL')
        _khb_state['enabled'] = True
        khb_force_redraw()
        print("✅ KHB_Display: Text-only display system enabled!")
        return True
    except Exception as e:
        print(f"❌ KHB_Display: Enable failed: {e}")
        khb_disable_display_system()
        return False

def khb_disable_display_system():
    global _khb_state
    if not _khb_state['enabled']: return
    try:
        if _khb_state['handler']:
            bpy.types.SpaceView3D.draw_handler_remove(_khb_state['handler'], 'WINDOW')
            _khb_state['handler'] = None
        khb_cleanup_icons()
        _khb_state['enabled'] = False
        khb_force_redraw()
        print("❌ KHB_Display: Display system disabled!")
    except Exception as e:
        print(f"⚠️ KHB_Display: Disable error: {e}")
        _khb_state['enabled'] = False

def khb_force_redraw():
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D': area.tag_redraw()
    except Exception: pass

def khb_emergency_cleanup():
    global _khb_state
    try:
        khb_disable_display_system()
        _khb_state = {'enabled': False, 'handler': None, 'pcoll': None, 'icons_loaded': False, 'settings': {'use_png': True}}
        import gc; gc.collect()
        print("🧹 KHB_Display: Emergency cleanup completed")
    except Exception as e:
        print(f"⚠️ KHB_Display: Emergency cleanup error: {e}")
        
def khb_update_icon_settings(settings):
    global _khb_state
    _khb_state['settings'].update(settings)
    if 'use_png' in settings and _khb_state['enabled']:
        khb_reload_icons()

def khb_reload_icons():
    khb_cleanup_icons()
    if _khb_state['enabled']: return khb_load_icons()
    return True

# ==== REGISTRATION ====
def register():
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Registered")

def unregister():
    print(f"🛑 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistering...")
    khb_emergency_cleanup()
    print(f"🎨 KHB_Display v{KHB_DISPLAY_VERSION}: Unregistered")

