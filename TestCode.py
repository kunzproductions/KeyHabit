# Test nhanh trong blender

# NOTE: Ưu tiên dùng icon gốc Blender (UI PNG) qua mapping BLENDER_ICON_BY_MOD cập nhật mới nhất.
# - BLENDER_ICON_BY_MOD: ánh xạ chuẩn tên modifier -> tên icon UI (ví dụ 'ARRAY' -> 'MOD_ARRAY').
# - Luôn default dùng icon Blender; emoji chỉ là fallback khi không lấy được texture/icon_id hoặc khi bật USE_EMOJI_ICONS.
# - Code draw icon phải truy cập trực tiếp dict BLENDER_ICON_BY_MOD (không dùng emoji trừ khi fallback).
# - Đảm bảo vẽ icon trước, trả về width + padding để không đè text.

import bpy
import blf
import math
import gpu
from gpu_extras.batch import batch_for_shader

_handler = None

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

# ================ ICON GỐC BLENDER (UI icon) ================
# Mapping cập nhật theo Blender UI icons (tên icon trong enum ICON):
# Tham khảo: icon prefix 'MOD_*' cho hầu hết modifier; một số dùng tên đặc thù.
# Luôn truy cập dict này để lấy icon_name -> icon_id -> GPUTexture. Emoji chỉ fallback.
BLENDER_ICON_BY_MOD = {
    # Generate/Arraying
    'ARRAY'           : 'MOD_ARRAY',
    'BEVEL'           : 'MOD_BEVEL',
    'BOOLEAN'         : 'MOD_BOOLEAN',
    'MIRROR'          : 'MOD_MIRROR',
    'SUBSURF'         : 'MOD_SUBSURF',   # Subdivision Surface
    'SOLIDIFY'        : 'MOD_SOLIDIFY',
    'REMESH'          : 'MOD_REMESH',
    'TRIANGULATE'     : 'MOD_TRIANGULATE',
    'WIREFRAME'       : 'MOD_WIREFRAME',
    'WELD'            : 'MOD_WELD',

    # Deform
    'SIMPLE_DEFORM'   : 'MOD_SIMPLEDEFORM',
    'DISPLACE'        : 'MOD_DISPLACE',
    'SMOOTH'          : 'MOD_SMOOTH',
    'LAPLACIANSMOOTH' : 'MOD_LAPLACIANSMOOTH',
    'SURFACE_DEFORM'  : 'MOD_MESHDEFORM',  # dùng icon deform chung
    'MESH_DEFORM'     : 'MOD_MESHDEFORM',
    'LATTICE'         : 'MOD_LATTICE',
    'SHRINKWRAP'      : 'MOD_SHRINKWRAP',
    'CAST'            : 'MOD_CAST',
    'CURVE'           : 'MOD_CURVE',
    'HOOK'            : 'HOOK',            # icon riêng HOOK
    'LAPLACIANDEFORM' : 'MOD_LAPLACIANDEFORM',

    # Generate/Modify geometry
    'NODES'           : 'GEOMETRY_NODES',  # Geometry Nodes
    'DATA_TRANSFER'   : 'MOD_DATA_TRANSFER',
    'WEIGHTED_NORMAL' : 'MOD_WEIGHTED_NORMAL',
    'NORMAL_EDIT'     : 'MOD_NORMALEDIT',
    'UV_PROJECT'      : 'MOD_UVPROJECT',
    'UV_WARP'         : 'MOD_UVWARP',
    'BEVEL_WEIGHT'    : 'MOD_BEVEL',       # dùng chung icon BEVEL
    'DECIMATE'        : 'MOD_DECIM',
    'EDGE_SPLIT'      : 'MOD_EDGESPLIT',
    'MULTIRES'        : 'MOD_MULTIRES',
    'SCREW'           : 'MOD_SCREW',
    'SKIN'            : 'MOD_SKIN',
    'SOLIDIFY'        : 'MOD_SOLIDIFY',
    'SUBSURF'         : 'MOD_SUBSURF',
    'BUILD'           : 'MOD_BUILD',
    'MASK'            : 'MOD_MASK',
    'MESH_SEQUENCE_CACHE': 'MOD_MESHSEQUENCECACHE',
    'BOOLEAN'         : 'MOD_BOOLEAN',
    'ARRAY'           : 'MOD_ARRAY',

    # Physics/Simulation related
    'CLOTH'           : 'MOD_CLOTH',
    'SOFT_BODY'       : 'MOD_SOFT',
    'FLUID'           : 'MOD_FLUIDSIM',
    'FLUID_SIMULATION': 'MOD_FLUIDSIM',
    'OCEAN'           : 'MOD_OCEAN',
    'DYNAMIC_PAINT'   : 'MOD_DYNAMICPAINT',
    'PARTICLE_INSTANCE': 'MOD_PARTICLE_INSTANCE',
    'PARTICLE_SYSTEM' : 'MOD_PARTICLES',

    # Others
    'SURFACE'         : 'MOD_SURFACE',
    'BOOLEAN'         : 'MOD_BOOLEAN',
}
FALLBACK_ICON_NAME = 'MODIFIER'

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

def _draw_texture(tex, x, y, w, h):
    if tex is None:
        return 0
    pos = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    uv  = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    batch = batch_for_shader(_image_shader, 'TRI_FAN', {"pos": pos, "texCoord": uv})
    gpu.state.blend_set('ALPHA')
    _image_shader.bind()
    try:
        _image_shader.uniform_sampler("image", tex)
    except Exception:
        try:
            tex.bind(0)
        except Exception:
            gpu.state.blend_set('NONE')
            return 0
    batch.draw(_image_shader)
    gpu.state.blend_set('NONE')
    return w

# Trả về GPUTexture từ icon_id (nếu Blender build hỗ trợ)
def _texture_from_icon_id(icon_id):
    try:
        if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
            return gpu.texture.from_icon(icon_id)
    except Exception:
        pass
    return None

# Lấy texture icon từ loại modifier bằng mapping BLENDER_ICON_BY_MOD
# QUAN TRỌNG: Luôn tra BLENDER_ICON_BY_MOD (emoji chỉ fallback sau cùng)
def _get_icon_texture_for_mod(mod_type):
    icon_name = BLENDER_ICON_BY_MOD.get(mod_type, FALLBACK_ICON_NAME)
    icon_id = 0
    try:
        # Một số build hỗ trợ UILayout.icon(...) để lấy icon_id từ tên icon UI
        if hasattr(bpy.types.UILayout, 'icon'):
            icon_id = bpy.types.UILayout.icon(bpy.types.UILayout, icon_name)
    except Exception:
        icon_id = 0
    tex = _texture_from_icon_id(icon_id) if icon_id else None
    return tex

# Vẽ icon modifier: Ưu tiên icon Blender theo BLENDER_ICON_BY_MOD, fallback emoji nếu không lấy được texture
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
    # ===== Shader Auto Smooth (Geometry Nodes) =====
    if mod.type == 'NODES' and ("Smooth by Angle" in mod.name or "Shade Auto Smooth" in mod.name):
        tc.append(('[', COLOR_BOX)); tc.append(('Shade Auto Smooth', COLOR_LABEL)); tc.append((']', COLOR_BOX))
        tc.append((' ' + mod.name, COLOR_NUM))
        angle_deg = None; ignore_val = None
        if "Input_1" in mod.keys():
            angle_deg = round(mod["Input_1"] * 180 / math.pi, 1)
        if "Socket_1" in mod.keys():
            ignore_val = bool(mod["Socket_1"])
        tc.append((' Angle:', COLOR_VAL))
        tc.append((f"{angle_deg if angle_deg is not None else 0.0}°", COLOR_NUM))
        if ignore_val:
            tc.append((' IgnoreSharpness', COLOR_ON))
    else:
        tc.append(('[', COLOR_BOX)); tc.append((get_modifier_display_name(mod), COLOR_LABEL)); tc.append((']', COLOR_BOX))
        tc.append((' ' + mod.name, COLOR_NUM))
        if mod.type == 'MIRROR':
            for i, label in enumerate(['X','Y','Z']):
                col = COLOR_ON if getattr(mod, 'use_axis', [False]*3)[i] else COLOR_OFF
                tc.append((' ' + label, col))
            if getattr(mod, 'mirror_object', None):
                tc.append((' Mirror Object:', COLOR_LABEL)); tc.append((' ' + mod.mirror_object.name, COLOR_SRC))
        elif mod.type == 'BOOLEAN':
            op = getattr(mod, 'operation', '')
            solver = getattr(mod, 'solver', '')
            if op: tc.append((' ' + op, COLOR_FUNC))
            if solver == 'BMESH': tc.append((' BMESH', COLOR_ON))
            if solver == 'EXACT': tc.append((' EXACT', COLOR_ON))
            src_obj = getattr(mod, 'object', None)
            if src_obj: tc.append((' ' + src_obj.name, COLOR_SRC))
        elif mod.type == 'DISPLACE':
            tc.append((' Strength:', COLOR_VAL)); tc.append((f"{getattr(mod,'strength',0):.3f}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))
        elif mod.type == 'BEVEL':
            tc.append((' Amount:', COLOR_VAL)); tc.append((f"{getattr(mod,'width',0):.3f}", COLOR_NUM))
            tc.append((' Segment:', COLOR_VAL)); tc.append((f"{getattr(mod,'segments',0)}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            lim = getattr(mod, 'limit_method', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))
            if lim == 'ANGLE': tc.append((' ANGLE', COLOR_ON))
            if lim == 'WEIGHT': tc.append((' WEIGHT', COLOR_ON))
        elif mod.type == 'ARRAY':
            tc.append((' ×', COLOR_VAL)); tc.append((f"{getattr(mod,'count',0)}", COLOR_NUM))
        elif mod.type == 'SOLIDIFY':
            tc.append((' T:', COLOR_VAL)); tc.append((f"{getattr(mod,'thickness',0):.3f}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))
        elif mod.type == 'SUBSURF':
            tc.append((' Lv', COLOR_VAL)); tc.append((f"{getattr(mod,'levels',0)}", COLOR_NUM))
        elif mod.type == 'DATA_TRANSFER':
            obj = getattr(mod, 'object', None)
            if obj: tc.append((' ← ', COLOR_VAL)); tc.append((obj.name, COLOR_NUM))
        elif mod.type == 'SHRINKWRAP':
            tgt = getattr(mod, 'target', None)
            if tgt: tc.append((' → ', COLOR_VAL)); tc.append((tgt.name, COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))
    return tc

# ================== DRAW OVERLAY ==================

def draw_overlay_demo():
    if not bpy.context.selected_objects:
        return
    font_id, y, lh = 0, 15, 18
    obj = bpy.context.active_object
    blf.size(font_id, 12)
    if obj and obj.type == 'MESH':
        for mod in reversed(obj.modifiers):
            x = 20
            icon_w = draw_modifier_icon(font_id, x, y, mod.type, icon_size=ICON_SIZE_PX)
            x += int(icon_w) + ICON_PAD_PX
            tc = get_modifier_line(mod)
            for txt, col in tc:
                blf.position(font_id, x, y, 0)
                blf.color(font_id, *col)
                blf.draw(font_id, txt)
                text_w = blf.dimensions(font_id, txt)[0]
                x += int(text_w)
            y += lh
    else:
						blf.position(font_id, 20, y, 0)
						blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
						blf.draw(font_id, "Không có object MESH được chọn")
# NOTE: Sử dụng icon gốc của Blender (PNG/UI icon) thay cho emoji.
# - Dùng tên icon UI (MOD_*) -> icon_id -> cố gắng lấy GPUTexture để vẽ bằng shader 2D_IMAGE
# - Fallback: emoji để so sánh (bật USE_EMOJI_ICONS)
# - Đảm bảo vẽ icon trước, lấy width trả về + padding -> KHÔNG đè text.

import bpy
import blf
import math
import gpu
from gpu_extras.batch import batch_for_shader

_handler = None

# ==== CONFIG ====
USE_EMOJI_ICONS = False  # True = dùng emoji legacy để so sánh
ICON_SIZE_PX = 16        # kích thước icon (px)
ICON_PAD_PX = 4          # khoảng cách icon -> text (px)

# ==== COLOR CONFIG ====
COLOR_BOX   = (1.0, 0.45, 0.0, 1.0)   # Cam ngoặc vuông/label
COLOR_LABEL = (1.0, 0.45, 0.0, 1.0)   # Cam tiêu đề
COLOR_VAL   = (0.85, 0.92, 0.4, 1.0)  # Xanh lá nhãn thông số
COLOR_NUM   = (1.0, 1.0, 1.0, 1.0)    # Trắng giá trị
COLOR_ON    = (0.2, 0.6, 1.0, 1.0)    # Xanh dương trạng thái bật
COLOR_OFF   = (1.0, 0.25, 0.17, 1.0)  # Đỏ trạng thái tắt
COLOR_FUNC  = COLOR_LABEL
COLOR_SRC   = COLOR_NUM

# ================ ICON GỐC BLENDER (UI icon) ================
BLENDER_ICON_BY_MOD = {
    'MIRROR': 'MOD_MIRROR',
    'ARRAY': 'MOD_ARRAY',
    'BEVEL': 'MOD_BEVEL',
    'BOOLEAN': 'MOD_BOOLEAN',
    'SOLIDIFY': 'MOD_SOLIDIFY',
    'SUBSURF': 'MOD_SUBSURF',
    'DISPLACE': 'MOD_DISPLACE',
    'SHRINKWRAP': 'MOD_SHRINKWRAP',
    'DATA_TRANSFER': 'MOD_DATA_TRANSFER',
    'NODES': 'GEOMETRY_NODES',
    'SIMPLE_DEFORM': 'MOD_SIMPLEDEFORM',
    'SMOOTH': 'MOD_SMOOTH',
    'DECIMATE': 'MOD_DECIM',
}
FALLBACK_ICON_NAME = 'MODIFIER'

# Emoji legacy để so sánh khi cần
_EMOJI_BY_MOD = {
    'MIRROR': '🪞', 'ARRAY': '📋', 'BEVEL': '💎', 'BOOLEAN': '🔀',
    'SOLIDIFY': '📦', 'SUBSURF': '🌊', 'DISPLACE': '〰️', 'SHRINKWRAP': '🎯',
    'DATA_TRANSFER': '📥', 'NODES': '⚙️', 'SIMPLE_DEFORM': '🌀', 'SMOOTH': '✨', 'DECIMATE': '🔻',
}

# ==== GPU SHADER + TEXTURE VẼ ICON ====
_image_shader = gpu.shader.from_builtin('IMAGE')


def _draw_texture(tex, x, y, w, h):
    if tex is None:
        return 0
    pos = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    batch = batch_for_shader(_image_shader, 'TRI_FAN', {"pos": pos, "texCoord": uv})
    gpu.state.blend_set('ALPHA')
    _image_shader.bind()
    try:
        _image_shader.uniform_sampler("image", tex)
    except Exception:
        try:
            tex.bind(0)
        except Exception:
            gpu.state.blend_set('NONE')
            return 0
    batch.draw(_image_shader)
    gpu.state.blend_set('NONE')
    return w


def _texture_from_icon_id(icon_id):
    # Thử lấy GPUTexture từ icon_id nếu phiên bản hỗ trợ
    try:
        if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
            return gpu.texture.from_icon(icon_id)
    except Exception:
        pass
    return None


def _get_icon_texture_for_mod(mod_type):
    icon_name = BLENDER_ICON_BY_MOD.get(mod_type, FALLBACK_ICON_NAME)
    # Lấy icon_id từ tên icon UI
    icon_id = 0
    try:
        # Blender không có API public trực tiếp: UILayout.icon(...) cần context UI.
        # Một số bản cung cấp bpy.types.UILayout.icon(ui, icon_name) -> icon_id; ở đây thử callable fallback.
        if hasattr(bpy.types.UILayout, 'icon'):
            icon_id = bpy.types.UILayout.icon(bpy.types.UILayout, icon_name)
    except Exception:
        icon_id = 0

    tex = _texture_from_icon_id(icon_id) if icon_id else None
    return tex


def draw_modifier_icon(font_id, x, y, mod_type, icon_size=ICON_SIZE_PX):
    """Vẽ icon gốc Blender qua GPU (ưu tiên), fallback emoji để so sánh.
    Trả về width dùng để canh chữ, giúp loại bỏ đè text.
    """
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
    # ===== Shader Auto Smooth (Geometry Nodes) =====
    if mod.type == 'NODES' and ("Smooth by Angle" in mod.name or "Shade Auto Smooth" in mod.name):
        tc.append(('[', COLOR_BOX)); tc.append(('Shade Auto Smooth', COLOR_LABEL)); tc.append((']', COLOR_BOX))
        tc.append((' ' + mod.name, COLOR_NUM))
        angle_deg = None; ignore_val = None
        if "Input_1" in mod.keys():
            angle_deg = round(mod["Input_1"] * 180 / math.pi, 1)
        if "Socket_1" in mod.keys():
            ignore_val = bool(mod["Socket_1"])
        tc.append((' Angle:', COLOR_VAL))
        tc.append((f"{angle_deg if angle_deg is not None else 0.0}°", COLOR_NUM))
        if ignore_val: tc.append((' IgnoreSharpness', COLOR_ON))

    else:
        tc.append(('[', COLOR_BOX)); tc.append((get_modifier_display_name(mod), COLOR_LABEL)); tc.append((']', COLOR_BOX))
        tc.append((' ' + mod.name, COLOR_NUM))

        if mod.type == 'MIRROR':
            for i, label in enumerate(['X', 'Y', 'Z']):
                col = COLOR_ON if getattr(mod, 'use_axis', [False]*3)[i] else COLOR_OFF
                tc.append((' ' + label, col))
            if getattr(mod, 'mirror_object', None): tc.append((' Mirror Object:', COLOR_LABEL)); tc.append((' ' + mod.mirror_object.name, COLOR_SRC))

        elif mod.type == 'BOOLEAN':
            op = getattr(mod, 'operation', ''); solver = getattr(mod, 'solver', '')
            if op: tc.append((' ' + op, COLOR_FUNC))
            if solver == 'BMESH': tc.append((' BMESH', COLOR_ON))
            if solver == 'EXACT': tc.append((' EXACT', COLOR_ON))
            src_obj = getattr(mod, 'object', None)
            if src_obj: tc.append((' ' + src_obj.name, COLOR_SRC))

        elif mod.type == 'DISPLACE':
            tc.append((' Strength:', COLOR_VAL)); tc.append((f"{getattr(mod, 'strength', 0):.3f}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))

        elif mod.type == 'BEVEL':
            tc.append((' Amount:', COLOR_VAL)); tc.append((f"{getattr(mod, 'width', 0):.3f}", COLOR_NUM))
            tc.append((' Segment:', COLOR_VAL)); tc.append((f"{getattr(mod, 'segments', 0)}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            lim = getattr(mod, 'limit_method', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))
            if lim == 'ANGLE': tc.append((' ANGLE', COLOR_ON))
            if lim == 'WEIGHT': tc.append((' WEIGHT', COLOR_ON))

        elif mod.type == 'ARRAY':
            tc.append((' ×', COLOR_VAL)); tc.append((f"{getattr(mod, 'count', 0)}", COLOR_NUM))

        elif mod.type == 'SOLIDIFY':
            tc.append((' T:', COLOR_VAL)); tc.append((f"{getattr(mod, 'thickness', 0):.3f}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))

        elif mod.type == 'SUBSURF':
            tc.append((' Lv', COLOR_VAL)); tc.append((f"{getattr(mod, 'levels', 0)}", COLOR_NUM))

        elif mod.type == 'DATA_TRANSFER':
            obj = getattr(mod, 'object', None)
            if obj: tc.append((' ← ', COLOR_VAL)); tc.append((obj.name, COLOR_NUM))

        elif mod.type == 'SHRINKWRAP':
            tgt = getattr(mod, 'target', None)
            if tgt: tc.append((' → ', COLOR_VAL)); tc.append((tgt.name, COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg: tc.append((' VG:', COLOR_VAL)); tc.append((vg, COLOR_NUM))
    return tc


# ================== DRAW OVERLAY ==================

def draw_overlay_demo():
    if not bpy.context.selected_objects:
        return
    font_id, y, lh = 0, 15, 18
    obj = bpy.context.active_object
    blf.size(font_id, 12)
    if obj and obj.type == 'MESH':
        for mod in reversed(obj.modifiers):
            x = 20
            icon_w = draw_modifier_icon(font_id, x, y, mod.type, icon_size=ICON_SIZE_PX)
            x += int(icon_w) + ICON_PAD_PX
            tc = get_modifier_line(mod)
            for txt, col in tc:
                blf.position(font_id, x, y, 0)
                blf.color(font_id, *col)
                blf.draw(font_id, txt)
                text_w = blf.dimensions(font_id, txt)[0]
                x += int(text_w)
            y += lh
    else:
        blf.position(font_id, 20, y, 0)
        blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
        blf.draw(font_id, "Không có object MESH được chọn")


def enable_overlay_demo():
    global _handler
    if _handler is None:
        _handler = bpy.types.SpaceView3D.draw_handler_add(draw_overlay_demo, (), 'WINDOW', 'POST_PIXEL')
        print("✅ Overlay demo đã bật! (icon Blender qua GPU, legacy emoji để so sánh)")
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def disable_overlay_demo():
    global _handler
    if _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        _handler = None
        print("❌ Overlay demo đã tắt!")
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

enable_overlay_demo()
