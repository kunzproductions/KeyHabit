# KHB_Display.py - KeyHabit Display Module
# Modifier overlay display with Blender icons and gizmo buttons

import bpy
from bpy.types import GizmoGroup, Operator
from mathutils import Vector
import blf
import math
import gpu
from gpu_extras.batch import batch_for_shader

# Import KHB_Analysis for button state checking
try:
    from . import KHB_Analysis
except ImportError:
    import KHB_Analysis

_handler = None
_gizmo_group_instance = None  # Global reference to gizmo group

# ==== CONFIG ====
USE_EMOJI_ICONS = False   # True = dùng emoji legacy để test UI/fallback khi thiếu icon
ICON_SIZE_PX   = 16       # kích thước icon (px)
ICON_PAD_PX    = 4        # khoảng cách icon -> text (px)

# ==== COLOR CONFIG ====
COLOR_BOX   = (1.0, 0.45, 0.0, 1.0)   # Cam ngoặc vuông/label
COLOR_LABEL = (1.0, 0.45, 0.0, 1.0)   # Cam tiêu đề
COLOR_VAL   = (0.85, 0.92, 0.4, 1.0)  # Xanh lá nhãn thông số
COLOR_NUM   = (1.0, 1.0, 1.0, 1.0)    # Trắng giá trị
COLOR_ON    = (0.2, 0.6, 1.0, 1.0)    # Xanh dương trạng thái bật
COLOR_OFF   = (1.0, 0.25, 0.17, 1.0)  # Đỏ trạng thái tắt
COLOR_FUNC  = COLOR_LABEL
COLOR_SRC   = COLOR_NUM

# ================ CUSTOM ICON MAPPING ================
# Sử dụng icon PNG từ thư mục icons thay vì icon Blender gốc
import os

def get_icon_path():
    """Lấy đường dẫn thư mục icons"""
    return os.path.join(os.path.dirname(__file__), 'icons')

# Mapping modifier type -> tên file icon PNG
CUSTOM_ICON_BY_MOD = {
    # Generate/Arraying
    'ARRAY'           : 'blender_icon_mod_array.png',
    'BEVEL'           : 'blender_icon_mod_bevel.png',
    'BOOLEAN'         : 'blender_icon_mod_boolean.png',
    'MIRROR'          : 'blender_icon_mod_mirror.png',
    'SUBSURF'         : 'blender_icon_mod_subsurf.png',
    'SOLIDIFY'        : 'blender_icon_mod_solidify.png',
    'REMESH'          : 'blender_icon_mod_remesh.png',
    'TRIANGULATE'     : 'blender_icon_mod_triangulate.png',
    'WIREFRAME'       : 'blender_icon_mod_wireframe.png',
    'WELD'            : 'blender_icon_mod_weld.png',

    # Deform
    'SIMPLE_DEFORM'   : 'blender_icon_mod_simpledeform.png',
    'DISPLACE'        : 'blender_icon_mod_displace.png',
    'SMOOTH'          : 'blender_icon_mod_smooth.png',
    'LAPLACIANSMOOTH' : 'blender_icon_mod_smooth.png',  # dùng chung icon smooth
    'SURFACE_DEFORM'  : 'blender_icon_mod_meshdeform.png',
    'MESH_DEFORM'     : 'blender_icon_mod_meshdeform.png',
    'LATTICE'         : 'blender_icon_mod_lattice.png',
    'SHRINKWRAP'      : 'blender_icon_mod_shrinkwrap.png',
    'CAST'            : 'blender_icon_mod_cast.png',
    'CURVE'           : 'blender_icon_mod_curve.png',
    'HOOK'            : 'blender_icon_question.png',  # fallback
    'LAPLACIANDEFORM' : 'blender_icon_mod_smooth.png',

    # Generate/Modify geometry
    'NODES'           : 'blender_icon_geometry_nodes.png',
    'DATA_TRANSFER'   : 'blender_icon_mod_data_transfer.png',
    'WEIGHTED_NORMAL' : 'blender_icon_mod_normaledit.png',
    'NORMAL_EDIT'     : 'blender_icon_mod_normaledit.png',
    'UV_PROJECT'      : 'blender_icon_mod_uvproject.png',
    'UV_WARP'         : 'blender_icon_mod_uvproject.png',  # dùng chung icon
    'BEVEL_WEIGHT'    : 'blender_icon_mod_bevel.png',
    'DECIMATE'        : 'blender_icon_mod_decim.png',
    'EDGE_SPLIT'      : 'blender_icon_mod_edgesplit.png',
    'MULTIRES'        : 'blender_icon_mod_multires.png',
    'SCREW'           : 'blender_icon_mod_screw.png',
    'SKIN'            : 'blender_icon_mod_skin.png',
    'BUILD'           : 'blender_icon_mod_build.png',
    'MASK'            : 'blender_icon_mod_mask.png',

    # Physics/Simulation related
    'CLOTH'           : 'blender_icon_mod_cloth.png',
    'SOFT_BODY'       : 'blender_icon_mod_soft.png',
    'FLUID'           : 'blender_icon_mod_fluidsim.png',
    'FLUID_SIMULATION': 'blender_icon_mod_fluidsim.png',
    'OCEAN'           : 'blender_icon_mod_ocean.png',
    'DYNAMIC_PAINT'   : 'blender_icon_mod_dynamicpaint.png',
    'PARTICLE_INSTANCE': 'blender_icon_mod_particle_instance.png',
    'PARTICLE_SYSTEM' : 'blender_icon_mod_particles.png',
}

FALLBACK_ICON_PATH = os.path.join(get_icon_path(), 'blender_icon_question.png')

# Emoji legacy để so sánh khi cần (fallback UI test)
_EMOJI_BY_MOD = {
    'ARRAY':'📦', 'BEVEL':'💎', 'BOOLEAN':'🔀', 'MIRROR':'🪞', 'SUBSURF':'🌊', 'SOLIDIFY':'📦',
    'REMESH':'🧊', 'TRIANGULATE':'🔺', 'WIREFRAME':'#️⃣', 'WELD':'🧲',
    'SIMPLE_DEFORM':'🌀', 'DISPLACE':'〰️', 'SMOOTH':'✨', 'LAPLACIANSMOOTH':'♾️', 'SURFACE_DEFORM':'🧩',
    'MESH_DEFORM':'🧩', 'LATTICE':'#️⃣', 'SHRINKWRAP':'🎯', 'CAST':'🎲', 'CURVE':'➰', 'HOOK':'🪝',
    'LAPLACIANDEFORM':'♾️', 'NODES':'⚙️', 'DATA_TRANSFER':'📥', 'WEIGHTED_NORMAL':'📏', 'NORMAL_EDIT':'📐',
    'UV_PROJECT':'🗺️', 'UV_WARP':'🧭', 'BEVEL_WEIGHT':'⚖️', 'DECIMATE':'🔻', 'EDGE_SPLIT':'✂️', 'MULTIRES':'🧱',
    'SCREW':'🔩', 'SKIN':'🧍', 'BUILD':'🏗️', 'MASK':'🎭', 'MESH_SEQUENCE_CACHE':'🗂️',
    'CLOTH':'🧣', 'SOFT_BODY':'🍮', 'FLUID':'💧', 'FLUID_SIMULATION':'💧', 'OCEAN':'🌊', 'DYNAMIC_PAINT':'🎨',
    'PARTICLE_INSTANCE':'🔁', 'PARTICLE_SYSTEM':'✨', 'SURFACE':'🌐'
}

# ==== GPU SHADER + TEXTURE VẼ ICON ====
_image_shader = gpu.shader.from_builtin('IMAGE')

# ==== VẼ KHUNG CHO TEXT ====
def draw_text_background(x, y, text_width, text_height, padding=4, bg_color=(0.1, 0.1, 0.1, 0.8)):
    """Vẽ khung nền cho text với padding"""
    import gpu
    from gpu_extras.batch import batch_for_shader
    
    # Tính kích thước khung
    frame_x = x - padding
    frame_y = y - padding
    frame_w = text_width + padding * 2
    frame_h = text_height + padding * 2
    
    # Tạo vertices cho khung
    vertices = (
        (frame_x, frame_y),
        (frame_x + frame_w, frame_y),
        (frame_x + frame_w, frame_y + frame_h),
        (frame_x, frame_y + frame_h)
    )
    
    # Tạo batch và vẽ
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_float("color", bg_color)
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def _draw_texture(tex, x, y, w, h):
    if tex is None:
        return 0
    
    pos = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    uv  = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    batch = batch_for_shader(_image_shader, 'TRI_FAN', {"pos": pos, "texCoord": uv})
    gpu.state.blend_set('ALPHA')
    _image_shader.bind()
    
    try:
        # Thử bind texture
        if hasattr(tex, 'bind'):
            tex.bind(0)
            _image_shader.uniform_sampler("image", tex)
        else:
            # Fallback: sử dụng image trực tiếp
            _image_shader.uniform_sampler("image", tex)
    except Exception as e:
        print(f"Error binding texture: {e}")
        gpu.state.blend_set('NONE')
        return 0
    
    batch.draw(_image_shader)
    gpu.state.blend_set('NONE')
    return w

# Load PNG icon từ file
def _load_png_icon(icon_path):
    """Load PNG icon từ file path"""
    try:
        import bpy
        # Load image từ file
        image = bpy.data.images.load(icon_path)
        # Tạo GPUTexture từ image
        if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_image'):
            return gpu.texture.from_image(image)
        else:
            # Fallback: sử dụng image trực tiếp
            return image
    except Exception as e:
        print(f"Error loading icon {icon_path}: {e}")
    return None

# OPTIMIZATION: Cache modifier icons để không load lại mỗi frame
_modifier_icon_cache = {}

# OPTIMIZATION: Cache modifier state để không loop modifiers mỗi frame
_modifier_state_cache = {
    'object_name': None,
    'modifiers_hash': None,
    'all_modifiers_on': False,
    'subdivision_on': False,
    'last_update_time': 0.0
}
_CACHE_UPDATE_INTERVAL = 0.5  # Update cache tối đa 2 lần/giây (tối ưu cho hiệu suất)

# OPTIMIZATION: Cache modifier text để không tạo text list mỗi frame
_modifier_text_cache = {
    'object_name': None,
    'modifiers_hash': None,
    'text_lines': [],  # List of (mod_index, text_chunks)
    'last_update_time': 0.0
}

def _update_modifier_state_cache(obj):
    """Update modifier state cache - chỉ gọi khi cần thiết"""
    global _modifier_state_cache
    import time
    
    current_time = time.time()
    
    # Kiểm tra xem có cần update không
    if obj is None or not hasattr(obj, 'modifiers'):
        _modifier_state_cache['object_name'] = None
        return
    
    # Tạo hash từ modifiers để detect thay đổi
    mod_hash = hash((
        obj.name,
        len(obj.modifiers),
        tuple((m.type, m.show_viewport, getattr(m, 'levels', 0)) for m in obj.modifiers)
    ))
    
    # Nếu object hoặc modifiers thay đổi, hoặc đã quá lâu → update
    need_update = (
        _modifier_state_cache['object_name'] != obj.name or
        _modifier_state_cache['modifiers_hash'] != mod_hash or
        (current_time - _modifier_state_cache['last_update_time']) > _CACHE_UPDATE_INTERVAL
    )
    
    if need_update:
        # Update cache
        _modifier_state_cache['object_name'] = obj.name
        _modifier_state_cache['modifiers_hash'] = mod_hash
        _modifier_state_cache['all_modifiers_on'] = any(mod.show_viewport for mod in obj.modifiers) if obj.modifiers else False
        
        # Check subdivision
        subdivision_on = False
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF' and mod.levels > 0:
                subdivision_on = True
                break
        _modifier_state_cache['subdivision_on'] = subdivision_on
        _modifier_state_cache['last_update_time'] = current_time

def _get_cached_modifier_state(obj, state_name):
    """Lấy modifier state từ cache"""
    global _modifier_state_cache
    
    # Update cache nếu cần
    _update_modifier_state_cache(obj)
    
    # Return cached value
    return _modifier_state_cache.get(state_name, False)

def _update_modifier_text_cache(obj):
    """Update modifier text cache - chỉ gọi khi cần thiết"""
    global _modifier_text_cache
    import time
    
    current_time = time.time()
    
    if obj is None or not hasattr(obj, 'modifiers'):
        _modifier_text_cache['object_name'] = None
        _modifier_text_cache['text_lines'] = []
        return
    
    # Tạo hash chi tiết từ modifiers (bao gồm cả properties)
    mod_hash = hash((
        obj.name,
        len(obj.modifiers),
        tuple((
            m.name,
            m.type,
            m.show_viewport,
            m.show_render,
            m.show_in_editmode,
            m.show_on_cage,
            getattr(m, 'levels', None),
            getattr(m, 'render_levels', None),
        ) for m in obj.modifiers)
    ))
    
    # Chỉ update khi cần
    need_update = (
        _modifier_text_cache.get('object_name') != obj.name or
        _modifier_text_cache.get('modifiers_hash') != mod_hash or
        (current_time - _modifier_text_cache.get('last_update_time', 0.0)) > _CACHE_UPDATE_INTERVAL
    )
    
    if need_update:
        # Update cache
        _modifier_text_cache['object_name'] = obj.name
        _modifier_text_cache['modifiers_hash'] = mod_hash
        _modifier_text_cache['text_lines'] = []
        
        # Build text lines cho mỗi modifier
        for mod in obj.modifiers:
            text_chunks = get_modifier_line(mod)
            _modifier_text_cache['text_lines'].append((mod, text_chunks))
        
        _modifier_text_cache['last_update_time'] = current_time

def _get_cached_modifier_text_lines(obj):
    """Lấy modifier text lines từ cache"""
    global _modifier_text_cache
    
    # Update cache nếu cần
    _update_modifier_text_cache(obj)
    
    # Return cached lines
    return _modifier_text_cache.get('text_lines', [])

# Lấy texture icon từ loại modifier bằng mapping CUSTOM_ICON_BY_MOD
def _get_icon_texture_for_mod(mod_type):
    # OPTIMIZATION: Check cache trước
    if mod_type in _modifier_icon_cache:
        return _modifier_icon_cache[mod_type]
    
    icon_filename = CUSTOM_ICON_BY_MOD.get(mod_type, 'blender_icon_question.png')
    icon_path = os.path.join(get_icon_path(), icon_filename)
    
    # Kiểm tra file tồn tại
    if not os.path.exists(icon_path):
        print(f"Icon file not found: {icon_path}")
        icon_path = FALLBACK_ICON_PATH
    
    # Load và cache
    texture = _load_png_icon(icon_path)
    _modifier_icon_cache[mod_type] = texture
    return texture

# Vẽ icon modifier: Sử dụng icon PNG từ thư mục icons, fallback emoji nếu không load được
# Trả về width để canh chữ an toàn.
def draw_modifier_icon(font_id, x, y, mod_type, icon_size=ICON_SIZE_PX):
    if not USE_EMOJI_ICONS:
        tex = _get_icon_texture_for_mod(mod_type)
        if tex is not None:
            w = int(icon_size)
            h = int(icon_size)
            _draw_texture(tex, x, y, w, h)
            return w
    # Fallback emoji
    emoji = _EMOJI_BY_MOD.get(mod_type, '🔧')
    blf.size(font_id, int(icon_size * 0.9))
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 0.9, 0.9, 0.9, 1.0)
    blf.draw(font_id, emoji)
    w = blf.dimensions(font_id, emoji)[0]
    return int(max(w, icon_size))

# ================== TEXT PHẦN MODIFIERS ==================

def get_modifier_display_name(mod):
    try:
        enum_prop = bpy.types.Modifier.bl_rna.properties['type']
        return enum_prop.enum_items[mod.type].name
    except Exception:
        return mod.type.title().replace('_', ' ')


def get_modifier_line(mod):
    tc = []
    
    # Kiểm tra trạng thái modifier để quyết định màu sắc
    COLOR_DISABLED = (0.3, 0.3, 0.3, 1.0)  # Màu đen xám khi tắt
    COLOR_ERROR = COLOR_OFF  # Màu đỏ khi có lỗi (1.0, 0.25, 0.17, 1.0)
    
    # Kiểm tra xem modifier có bị tắt không
    is_disabled = not getattr(mod, 'show_viewport', True)
    
    # Kiểm tra các trường hợp lỗi
    has_error = False
    if mod.type == 'BOOLEAN':
        # Boolean không có object
        if not getattr(mod, 'object', None):
            has_error = True
    elif mod.type == 'SUBSURF':
        # Subdivision level = 0
        if getattr(mod, 'levels', 0) == 0:
            has_error = True
    
    # Chọn màu cho bracket và label
    if is_disabled:
        box_color = COLOR_DISABLED
        label_color = COLOR_DISABLED
        name_color = COLOR_DISABLED
    elif has_error:
        box_color = COLOR_ERROR
        label_color = COLOR_ERROR
        name_color = COLOR_NUM  # Tên modifier vẫn giữ màu bình thường
    else:
        box_color = COLOR_BOX
        label_color = COLOR_LABEL
        name_color = COLOR_NUM
    
    # ===== Shader Auto Smooth (Geometry Nodes) =====
    if mod.type == 'NODES' and ("Smooth by Angle" in mod.name or "Shade Auto Smooth" in mod.name):
        tc.append(('[', box_color)); tc.append(('Shade Auto Smooth', label_color)); tc.append((']', box_color))
        tc.append((' ' + mod.name, name_color))
        angle_deg = None; ignore_val = None
        if "Input_1" in mod.keys():
            angle_deg = round(mod["Input_1"] * 180 / math.pi, 1)
        if "Socket_1" in mod.keys():
            ignore_val = bool(mod["Socket_1"])
        tc.append((' Angle:', COLOR_VAL if not is_disabled else COLOR_DISABLED))
        tc.append((f"{angle_deg if angle_deg is not None else 0.0}°", name_color))
        if ignore_val:
            tc.append((' IgnoreSharpness', COLOR_ON if not is_disabled else COLOR_DISABLED))
    else:
        tc.append(('[', box_color)); tc.append((get_modifier_display_name(mod), label_color)); tc.append((']', box_color))
        tc.append((' ' + mod.name, name_color))
        
        # Các thông số sẽ dùng màu disabled nếu modifier bị tắt
        val_color = COLOR_VAL if not is_disabled else COLOR_DISABLED
        num_color = name_color
        on_color = COLOR_ON if not is_disabled else COLOR_DISABLED
        off_color = COLOR_OFF if not is_disabled else COLOR_DISABLED
        
        if mod.type == 'MIRROR':
            for i, label in enumerate(['X','Y','Z']):
                col = on_color if getattr(mod, 'use_axis', [False]*3)[i] else off_color
                tc.append((' ' + label, col))
            if getattr(mod, 'mirror_object', None):
                tc.append((' Mirror Object:', val_color)); tc.append((' ' + mod.mirror_object.name, num_color))
        elif mod.type == 'BOOLEAN':
            op = getattr(mod, 'operation', '')
            solver = getattr(mod, 'solver', '')
            if op: tc.append((' ' + op, val_color))
            if solver == 'BMESH': tc.append((' BMESH', on_color))
            if solver == 'EXACT': tc.append((' EXACT', on_color))
            src_obj = getattr(mod, 'object', None)
            if src_obj: 
                tc.append((' ' + src_obj.name, num_color))
            elif has_error:
                tc.append((' [NO OBJECT]', COLOR_ERROR))
        elif mod.type == 'DISPLACE':
            tc.append((' Strength:', val_color)); tc.append((f"{getattr(mod,'strength',0):.3f}", num_color))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', val_color)); tc.append((vg, num_color))
        elif mod.type == 'BEVEL':
            tc.append((' Amount:', val_color)); tc.append((f"{getattr(mod,'width',0):.3f}", num_color))
            tc.append((' Segment:', val_color)); tc.append((f"{getattr(mod,'segments',0)}", num_color))
            vg = getattr(mod, 'vertex_group', '')
            lim = getattr(mod, 'limit_method', '')
            if vg: tc.append((' VG:', val_color)); tc.append((vg, num_color))
            if lim == 'ANGLE': tc.append((' ANGLE', on_color))
            if lim == 'WEIGHT': tc.append((' WEIGHT', on_color))
        elif mod.type == 'ARRAY':
            tc.append((' ×', val_color)); tc.append((f"{getattr(mod,'count',0)}", num_color))
        elif mod.type == 'SOLIDIFY':
            tc.append((' T:', val_color)); tc.append((f"{getattr(mod,'thickness',0):.3f}", num_color))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', val_color)); tc.append((vg, num_color))
        elif mod.type == 'SUBSURF':
            level = getattr(mod,'levels',0)
            tc.append((' Lv', val_color)); tc.append((f"{level}", num_color))
            if has_error:
                tc.append((' [LEVEL=0]', COLOR_ERROR))
        elif mod.type == 'DATA_TRANSFER':
            obj = getattr(mod, 'object', None)
            if obj: tc.append((' ← ', val_color)); tc.append((obj.name, num_color))
        elif mod.type == 'SHRINKWRAP':
            tgt = getattr(mod, 'target', None)
            if tgt: tc.append((' → ', val_color)); tc.append((tgt.name, num_color))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', val_color)); tc.append((vg, num_color))
    return tc

# ================== DRAW OVERLAY ==================

def draw_overlay_demo():
    # OPTIMIZATION: Chỉ vẽ khi cần thiết - tránh xung đột với nSolve
    # Kiểm tra context hợp lệ
    if not bpy.context.area or bpy.context.area.type != 'VIEW_3D':
        return
    
    # Vẽ modifier info CHỈ KHI có MESH object với modifiers
    if bpy.context.selected_objects:
        obj = bpy.context.active_object
        if obj and obj.type == 'MESH' and obj.modifiers:
            # Chỉ vẽ modifier overlay khi có modifiers
            font_id, lh = 0, 18
            blf.size(font_id, 12)
            
            # Padding bên trái chung cho cả text và button
            left_padding = 50  # Khớp với base_offset_x của GizmoGroup
            
            # Tính toán vị trí bắt đầu cho modifier info (từ trên xuống)
            y_start = 80  # Vị trí Y thấp hơn = lùi xuống phía dưới màn hình
            y = y_start
            
            # OPTIMIZATION: Vẽ modifier info từ cache thay vì tạo mới mỗi frame
            cached_lines = _get_cached_modifier_text_lines(obj)
            for mod, tc in reversed(cached_lines):
                x = left_padding
                icon_w = draw_modifier_icon(font_id, x, y, mod.type, icon_size=ICON_SIZE_PX)
                x += int(icon_w) + ICON_PAD_PX
                # tc đã được cache - không cần gọi get_modifier_line mỗi frame
                for txt, col in tc:
                    blf.position(font_id, x, y, 0)
                    blf.color(font_id, *col)
                    blf.draw(font_id, txt)
                    text_w = blf.dimensions(font_id, txt)[0]
                    x += int(text_w)
                y += lh
    
    # Vẽ icon buttons LUÔN LUÔN (không phụ thuộc vào modifiers)
    draw_simple_icon_buttons(bpy.context)

def draw_rect(x, y, width, height, color):
    """Vẽ hình chữ nhật"""
    vertices = ((x, y), (x + width, y), (x + width, y + height), (x, y + height))
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def draw_rounded_rect(x, y, width, height, radius, color):
    """Vẽ hình chữ nhật bo góc"""
    import math
    
    vertices = []
    segments = 8  # Số segments cho mỗi góc
    
    # Tạo vertices cho hình chữ nhật bo góc
    # Góc dưới trái
    for i in range(segments + 1):
        angle = math.pi + i * (math.pi / 2) / segments
        vx = x + radius + math.cos(angle) * radius
        vy = y + radius + math.sin(angle) * radius
        vertices.append((vx, vy))
    
    # Góc dưới phải
    for i in range(segments + 1):
        angle = 1.5 * math.pi + i * (math.pi / 2) / segments
        vx = x + width - radius + math.cos(angle) * radius
        vy = y + radius + math.sin(angle) * radius
        vertices.append((vx, vy))
    
    # Góc trên phải
    for i in range(segments + 1):
        angle = i * (math.pi / 2) / segments
        vx = x + width - radius + math.cos(angle) * radius
        vy = y + height - radius + math.sin(angle) * radius
        vertices.append((vx, vy))
    
    # Góc trên trái
    for i in range(segments + 1):
        angle = 0.5 * math.pi + i * (math.pi / 2) / segments
        vx = x + radius + math.cos(angle) * radius
        vy = y + height - radius + math.sin(angle) * radius
        vertices.append((vx, vy))
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
    
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def draw_icon_simple(x, y, size, color):
    """Vẽ icon (hình vuông) - fallback khi không load được PNG"""
    draw_rect(x, y, size, size, color)

# Cache để lưu texture đã load
_icon_texture_cache = {}

def draw_icon_png(x, y, size, icon_path, tint_color):
    """Vẽ icon PNG với màu tint và bo góc"""
    global _icon_texture_cache
    
    # Bo góc
    corner_radius = 4
    
    # Kiểm tra file tồn tại
    if not os.path.exists(icon_path):
        # Fallback: vẽ hình vuông màu bo góc
        draw_rounded_rect(x, y, size, size, corner_radius, tint_color)
        return
    
    # Load texture từ cache hoặc load mới
    if icon_path not in _icon_texture_cache:
        try:
            # Load image
            img = bpy.data.images.load(icon_path, check_existing=True)
            _icon_texture_cache[icon_path] = img
        except Exception as e:
            print(f"Error loading icon {icon_path}: {e}")
            draw_rounded_rect(x, y, size, size, corner_radius, tint_color)
            return
    
    img = _icon_texture_cache[icon_path]
    
    # Vẽ background với màu tint (bo góc)
    draw_rounded_rect(x, y, size, size, corner_radius, tint_color)
    
    # Vẽ icon PNG nhỏ hơn lên trên background (padding 4px)
    icon_padding = 4
    icon_x = x + icon_padding
    icon_y = y + icon_padding
    icon_size = size - icon_padding * 2
    
    try:
        # Tạo vertices và UV coords cho icon nhỏ hơn
        vertices = (
            (icon_x, icon_y), 
            (icon_x + icon_size, icon_y), 
            (icon_x + icon_size, icon_y + icon_size), 
            (icon_x, icon_y + icon_size)
        )
        uvs = ((0, 0), (1, 0), (1, 1), (0, 1))
        
        # Bind texture
        if img.bindcode == 0:
            img.gl_load()
        
        # Vẽ texture
        shader = gpu.shader.from_builtin('IMAGE')
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices, "texCoord": uvs})
        
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_sampler("image", gpu.texture.from_image(img))
        batch.draw(shader)
        gpu.state.blend_set('NONE')
    except Exception as e:
        print(f"Error drawing icon texture: {e}")
        # Fallback: chỉ vẽ background màu
        pass

def draw_simple_icon_buttons(context):
    """Vẽ icon buttons với PNG icons"""
    global _gizmo_group_instance
    
    try:
        # OPTIMIZATION: Kiểm tra context sớm để tránh vòng lặp không cần thiết
        if not context or not context.window or not context.window.screen:
            return
        
        gizmo_group = _gizmo_group_instance
        if not gizmo_group or not hasattr(gizmo_group, 'button_positions'):
            return
        
        # Lấy overlay state - tối ưu hóa bằng cách dùng context.area trực tiếp
        if context.area and context.area.type == 'VIEW_3D':
            ov = context.area.spaces[0].overlay
        else:
            # Fallback: tìm trong screen areas
            ov = None
            for area in context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    ov = area.spaces[0].overlay
                    break
        
        if not ov:
            return
        
        # Colors (với opacity 50%)
        on_color = (0.2, 0.8, 1.0, 0.5)   # Xanh - khi bật
        off_color = (0.0, 0.0, 0.0, 0.5)  # Đen - khi tắt
        hover_color = (1.0, 1.0, 0.0, 0.5)  # Vàng - khi hover
        
        for i, (name, button, icon_path, overlay_attr) in enumerate(gizmo_group.button_info):
            if i >= len(gizmo_group.button_positions):
                continue
            
            pos = gizmo_group.button_positions[i]
            
            # Kiểm tra trạng thái
            if overlay_attr is None:
                # Xử lý riêng cho các button đặc biệt
                is_on = False
                obj = context.active_object
                
                if name == "All Modifiers" and obj and hasattr(obj, 'modifiers'):
                    # OPTIMIZATION: Sử dụng cache thay vì loop modifiers mỗi frame
                    is_on = _get_cached_modifier_state(obj, 'all_modifiers_on')
                
                elif name == "Subdivision" and obj and obj.type == 'MESH':
                    # OPTIMIZATION: Sử dụng cache thay vì loop modifiers mỗi frame
                    is_on = _get_cached_modifier_state(obj, 'subdivision_on')
                
                elif name == "Transform Origin":
                    # Kiểm tra trạng thái transform origin
                    is_on = context.scene.tool_settings.use_transform_data_origin
                
                elif name == "Shading Data" and obj and obj.type == 'MESH':
                    # Kiểm tra xem mesh có shading data (sharp_face hoặc custom split normals)
                    mesh = obj.data
                    is_on = False
                    
                    # Check 1: sharp_face attribute (Blender 4.1+ shading data)
                    has_sharp_face = False
                    if hasattr(mesh, 'attributes') and 'sharp_face' in mesh.attributes:
                        has_sharp_face = True
                    
                    # Check 2: Custom split normals data
                    has_custom_normals = False
                    if hasattr(mesh, 'has_custom_normals') and mesh.has_custom_normals:
                        has_custom_normals = True
                    
                    # Nút sáng nếu có BẤT KỲ cái nào
                    is_on = has_sharp_face or has_custom_normals
                
                elif name == "Analyze Check":
                    # Kiểm tra xem Analyze Check có đang chạy không
                    is_on = KHB_Analysis.KHABIT_OT_AnalyzeCheck._operator is not None
            else:
                # Overlay buttons bình thường
                is_on = getattr(ov, overlay_attr, False)
            
            is_hover = hasattr(button, 'is_highlight') and button.is_highlight
            
            # Chọn màu
            color = hover_color if is_hover else (on_color if is_on else off_color)
            
            # Vẽ icon PNG với màu tint
            draw_icon_png(pos['x'], pos['y'], pos['icon_size'], icon_path, color)
            
    except (ReferenceError, Exception):
        _gizmo_group_instance = None
# ================== MODIFIER OVERLAY FUNCTIONS ==================
# Moved to preferences - no longer need operator

def enable_modifier_overlay():
    """Enable modifier overlay from external call"""
    global _handler
    if _handler is None:
        _handler = bpy.types.SpaceView3D.draw_handler_add(draw_overlay_demo, (), 'WINDOW', 'POST_PIXEL')
        # OPTIMIZATION: Tag redraw thông qua helper function
        tag_redraw_view3d(bpy.context)

def disable_modifier_overlay():
    """Disable modifier overlay from external call"""
    global _handler
    if _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        _handler = None
        # OPTIMIZATION: Tag redraw thông qua helper function
        tag_redraw_view3d(bpy.context)


#code Button

# ========== Utils ==========

def iter_view3d_spaces(context):
    for area in context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    yield area, space

def tag_redraw_view3d(context):
    # OPTIMIZATION: Chỉ tag redraw area hiện tại thay vì loop tất cả areas
    if context.area and context.area.type == 'VIEW_3D':
        context.area.tag_redraw()
    else:
        # Fallback: nếu không có context.area, mới loop
        for area, _ in iter_view3d_spaces(context):
            area.tag_redraw()
            break  # Chỉ tag 1 area đầu tiên

# ========== Operators ==========

class KHABIT_OT_toggle_wireframe(Operator):
    bl_idname = "keyhabit.toggle_wireframe"
    bl_label = "Wireframe"
    bl_description = "Toggle wireframe overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_wireframes = not ov.show_wireframes
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_edge_length(Operator):
    bl_idname = "keyhabit.toggle_edge_length"
    bl_label = "Edge Length"
    bl_description = "Toggle edge length display"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_extra_edge_length = not ov.show_extra_edge_length
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_retopo(Operator):
    bl_idname = "keyhabit.toggle_retopology"
    bl_label = "Retopology"
    bl_description = "Toggle retopology overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_retopology = not ov.show_retopology
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_all_modifiers(Operator):
    bl_idname = "keyhabit.toggle_all_modifiers"
    bl_label = "Toggle All Modifiers"
    bl_description = "Toggle viewport visibility of all modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not hasattr(obj, 'modifiers'):
            self.report({'WARNING'}, "No object with modifiers selected")
            return {'CANCELLED'}
        
        if len(obj.modifiers) == 0:
            self.report({'INFO'}, "Object has no modifiers")
            return {'CANCELLED'}
        
        # Kiểm tra trạng thái hiện tại - nếu có bất kỳ modifier nào đang bật thì tắt hết, ngược lại bật hết
        any_enabled = any(mod.show_viewport for mod in obj.modifiers)
        
        for mod in obj.modifiers:
            mod.show_viewport = not any_enabled
        
        status = "Disabled" if any_enabled else "Enabled"
        self.report({'INFO'}, f"{status} all {len(obj.modifiers)} modifier(s)")
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_subsurf(Operator):
    bl_idname = "keyhabit.toggle_subsurf"
    bl_label = "Toggle Subdivision"
    bl_description = "Toggle Subdivision Surface modifier (Level 3 when on, Level 0 when off)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Need to select a MESH object")
            return {'CANCELLED'}
        
        # Tìm modifier Subdivision Surface
        subsurf_mod = None
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                subsurf_mod = mod
                break
        
        # Nếu chưa có, tạo mới
        if subsurf_mod is None:
            subsurf_mod = obj.modifiers.new(name="Subdivision", type='SUBSURF')
            subsurf_mod.levels = 3
            subsurf_mod.render_levels = 3
            subsurf_mod.show_viewport = True
            self.report({'INFO'}, "Added Subdivision Surface modifier (Level 3)")
        else:
            # Nếu đã có, toggle giữa level 0 và 3
            if subsurf_mod.levels == 0:
                subsurf_mod.levels = 3
                subsurf_mod.render_levels = 3
                subsurf_mod.show_viewport = True
                self.report({'INFO'}, "Enabled Subdivision (Level 3)")
            else:
                subsurf_mod.levels = 0
                subsurf_mod.render_levels = 0
                self.report({'INFO'}, "Disabled Subdivision (Level 0)")
        
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_transform_origin(Operator):
    bl_idname = "keyhabit.toggle_transform_origin"
    bl_label = "Transform Origin Only"
    bl_description = "Toggle transform origin only mode"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        current_state = context.scene.tool_settings.use_transform_data_origin
        context.scene.tool_settings.use_transform_data_origin = not current_state
        
        status = "Enabled" if not current_state else "Disabled"
        self.report({'INFO'}, f"{status} Transform Origin Only")
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_mesh_analysis(Operator):
    bl_idname = "keyhabit.toggle_mesh_analysis"
    bl_label = "Mesh Analysis (Distort)"
    bl_description = "Toggle mesh analysis - distortion display"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            
            # Toggle mesh analysis
            if ov.show_statvis:
                # Nếu đang bật, tắt đi
                ov.show_statvis = False
                self.report({'INFO'}, "Disabled Mesh Analysis")
            else:
                # Nếu đang tắt, bật lên và set type = DISTORT
                ov.show_statvis = True
                context.scene.tool_settings.statvis.type = 'DISTORT'
                self.report({'INFO'}, "Enabled Mesh Analysis (Distort)")
        
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_custom_normals(Operator):
    bl_idname = "keyhabit.toggle_custom_normals"
    bl_label = "Clear Shading Data"
    bl_description = "Remove sharp_face attribute and custom split normals data → Only Sharp Edges affect shading"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and 
                context.active_object.type == 'MESH')

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Need to select a MESH object")
            return {'CANCELLED'}
        
        mesh = obj.data
        is_edit_mode = context.mode == 'EDIT_MESH'
        
        # Kiểm tra xem mesh có shading data không
        has_sharp_face = hasattr(mesh, 'attributes') and 'sharp_face' in mesh.attributes
        has_custom_normals = mesh.has_custom_normals
        
        if not has_sharp_face and not has_custom_normals:
            self.report({'INFO'}, "No shading data to remove")
            return {'CANCELLED'}
        
        try:
            removed_items = []
            
            # === REMOVE SHARP_FACE ATTRIBUTE ===
            if has_sharp_face:
                try:
                    # Remove sharp_face attribute
                    mesh.attributes.remove(mesh.attributes['sharp_face'])
                    removed_items.append("sharp_face")
                except Exception as e:
                    print(f"Error removing sharp_face: {e}")
            
            # === REMOVE CUSTOM SPLIT NORMALS ===
            if has_custom_normals:
                # Bước 1: Tắt auto smooth nếu đang bật (để tránh conflict)
                if hasattr(mesh, 'use_auto_smooth'):
                    mesh.use_auto_smooth = False
                
                # Bước 2: Clear custom split normals data
                if is_edit_mode:
                    # Trong Edit Mode: dùng operator
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
                    obj.update_from_editmode()
                else:
                    # Trong Object Mode: switch sang Edit Mode để clear
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.customdata_custom_splitnormals_clear()
                    bpy.ops.object.mode_set(mode='OBJECT')
                
                removed_items.append("custom normals")
            
            # Bước 3: Update mesh
            mesh.update()
            
            # Bước 4: Áp dụng shade smooth với keep_sharp_edges
            # Điều này đảm bảo CHỈ sharp edges ảnh hưởng đến shading
            try:
                # Đảm bảo ở Object Mode khi chạy shade_smooth
                current_mode = context.mode
                if current_mode == 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='OBJECT')
                
                # Chạy shade smooth với keep_sharp_edges=True
                # Nghĩa là: smooth mọi nơi NGOẠI TRỪ sharp edges
                bpy.ops.object.shade_smooth(keep_sharp_edges=True)
                
                # Quay lại mode ban đầu
                if current_mode == 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='EDIT')
                
                removed_text = " + ".join(removed_items)
                self.report({'INFO'}, f"Removed {removed_text} → Only Sharp Edges affect shading")
            except Exception as e:
                removed_text = " + ".join(removed_items)
                self.report({'INFO'}, f"Removed {removed_text}")
                print(f"Could not apply shade_smooth: {e}")
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Đảm bảo quay về mode ban đầu nếu có lỗi
            try:
                if is_edit_mode and context.mode != 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='EDIT')
                elif not is_edit_mode and context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            return {'CANCELLED'}
        
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_analyze_check(Operator):
    bl_idname = "keyhabit.toggle_analyze_check"
    bl_label = "Mesh Analysis Check"
    bl_description = "Toggle mesh topology analysis (Triangles, N-gons, Small faces, Concave, Boundary edges)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        # Toggle analysis check
        bpy.ops.keyhabit.analyze_check('INVOKE_DEFAULT')
        
        # Get status
        is_running = KHB_Analysis.KHABIT_OT_AnalyzeCheck._operator is not None
        status = "Enabled" if is_running else "Disabled"
        self.report({'INFO'}, f"{status} Mesh Analysis")
        
        tag_redraw_view3d(context)
        return {'FINISHED'}

# ========== GizmoGroup với icon hợp lệ và kiểm tra an toàn ==========

class KHABIT_GGT_overlay_buttons(GizmoGroup):
    bl_idname = "KEYHABIT_GGT_overlay_buttons"
    bl_label = "KeyHabit Overlay Buttons"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    base_offset_x = 50  # Padding bên trái (khớp với text)
    base_offset_y = 20  # Vị trí Y thấp hơn = lùi xuống phía dưới màn hình

    def setup(self, context):
        global _gizmo_group_instance
        _gizmo_group_instance = self
        
        # Tạo 10 gizmo buttons với tooltip
        button_configs = [
            ("keyhabit.toggle_all_modifiers", "Toggle All Modifiers"),
            ("keyhabit.toggle_subsurf", "Toggle Subdivision"),
            ("keyhabit.toggle_wireframe", "Wireframe"),
            ("keyhabit.toggle_edge_length", "Edge Length"),
            ("keyhabit.toggle_split_normals", "Split Normals"),
            ("keyhabit.toggle_custom_normals", "Clear Shading Data"),
            ("keyhabit.toggle_retopology", "Retopology"),
            ("keyhabit.toggle_transform_origin", "Transform Origin Only"),
            ("keyhabit.toggle_mesh_analysis", "Mesh Analysis (Distort)"),
            ("keyhabit.toggle_analyze_check", "Mesh Analysis Check")
        ]
        
        buttons = []
        for op, tooltip in button_configs:
            g = self.gizmos.new("GIZMO_GT_button_2d")
            g.target_set_operator(op)
            g.draw_options = set()
            g.alpha = 0.0
            g.alpha_highlight = 0.5
            
            # Thêm tooltip (label)
            try:
                # Gán bl_label cho gizmo để hiển thị tooltip
                if hasattr(g, 'use_draw_modal'):
                    g.use_draw_modal = False
                # Tooltip sẽ được hiển thị từ operator bl_label
            except:
                pass
            
            buttons.append(g)
        
        self.all_mods_btn, self.subsurf_btn, self.wireframe_btn, self.edge_length_btn, self.split_normals_btn, self.custom_normals_btn, self.retopo_btn, self.transform_origin_btn, self.mesh_analysis_btn, self.analyze_check_btn = buttons
        
        # Lấy đường dẫn thư mục icons
        icon_dir = get_icon_path()
        
        self.button_info = [
            ("All Modifiers", self.all_mods_btn, os.path.join(icon_dir, 'blender_icon_modifier_data.png'), None),  # None = kiểm tra trạng thái riêng
            ("Subdivision", self.subsurf_btn, os.path.join(icon_dir, 'blender_icon_mod_subsurf.png'), None),
            ("Wireframe", self.wireframe_btn, os.path.join(icon_dir, 'blender_icon_mod_wireframe.png'), 'show_wireframes'),
            ("Edge Length", self.edge_length_btn, os.path.join(icon_dir, 'blender_icon_driver_distance.png'), 'show_extra_edge_length'),
            ("Split Normals", self.split_normals_btn, os.path.join(icon_dir, 'blender_icon_mod_normaledit.png'), 'show_split_normals'),
            ("Shading Data", self.custom_normals_btn, os.path.join(icon_dir, 'blender_icon_mod_smooth.png'), None),
            ("Retopology", self.retopo_btn, os.path.join(icon_dir, 'blender_icon_mod_lineart.png'), 'show_retopology'),
            ("Transform Origin", self.transform_origin_btn, os.path.join(icon_dir, 'blender_icon_transform_origins.png'), None),
            ("Mesh Analysis", self.mesh_analysis_btn, os.path.join(icon_dir, 'blender_icon_ghost_enabled.png'), 'show_statvis'),
            ("Analyze Check", self.analyze_check_btn, os.path.join(icon_dir, 'blender_icon_ghost_disabled.png'), None)
        ]

    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.type == 'VIEW_3D'
    
    def __del__(self):
        global _gizmo_group_instance
        if _gizmo_group_instance == self:
            _gizmo_group_instance = None

    def draw_prepare(self, context):
        if not all(hasattr(self, attr) for attr in ['all_mods_btn', 'subsurf_btn', 'wireframe_btn', 'edge_length_btn', 'split_normals_btn', 'custom_normals_btn', 'retopo_btn', 'transform_origin_btn', 'mesh_analysis_btn', 'analyze_check_btn']):
            return
        
        global _gizmo_group_instance
        _gizmo_group_instance = self

        x = self.base_offset_x
        y = self.base_offset_y
        self.button_positions = []
        
        icon_size = 32  # Kích thước icon (to gấp đôi so với 16px cũ)
        button_size = icon_size
        
        for name, button, icon_path, overlay_attr in self.button_info:
            # Đặt vị trí và kích thước gizmo
            button.matrix_basis[0][3] = x + button_size / 2
            button.matrix_basis[1][3] = y + button_size / 2
            button.scale_basis = button_size * 0.8
            
            # Lưu thông tin
            self.button_positions.append({
                'x': x,
                'y': y,
                'width': button_size,
                'height': button_size,
                'icon_size': icon_size
            })
            
            x += button_size + 20  # Khoảng cách giữa các button

# Removed text handler - using text gizmos instead

# ========== Đăng ký / Hủy đăng ký ==========

classes = (
    KHABIT_OT_toggle_wireframe,
    KHABIT_OT_toggle_edge_length,
    KHABIT_OT_toggle_retopo,
    KHABIT_OT_toggle_all_modifiers,
    KHABIT_OT_toggle_subsurf,
    KHABIT_OT_toggle_transform_origin,
    KHABIT_OT_toggle_mesh_analysis,
    KHABIT_OT_toggle_custom_normals,
    KHABIT_OT_toggle_analyze_check,
    KHABIT_GGT_overlay_buttons,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    # Disable overlay if active
    global _handler, _gizmo_group_instance, _icon_texture_cache, _modifier_icon_cache
    global _modifier_state_cache, _modifier_text_cache
    
    if _handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        except Exception:
            pass
        _handler = None
    
    # Clear gizmo group reference
    _gizmo_group_instance = None
    
    # OPTIMIZATION: Clear all caches
    _icon_texture_cache.clear()
    _modifier_icon_cache.clear()
    _modifier_state_cache.clear()
    _modifier_text_cache.clear()
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls}: {e}")

if __name__ == "__main__":
    register()
