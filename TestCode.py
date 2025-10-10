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

# --- KeyHabit Toggle Wireframe Overlay và Transform Data Origin ---
import bpy

class KH_OT_ToggleWireframe(bpy.types.Operator):
    bl_idname = "keyhabit.toggle_wireframe"
    bl_label = "Toggle Wireframe Overlay"
    def execute(self, context):
        for area in context.window.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces.active
                space.shading.show_wireframes = not space.shading.show_wireframes
        return {'FINISHED'}

class KH_OT_ToggleDataOrigin(bpy.types.Operator):
    bl_idname = "keyhabit.toggle_data_origin"
    bl_label = "Toggle Transform Data Origin"
    def execute(self, context):
        context.scene.tool_settings.use_transform_data_origin = not context.scene.tool_settings.use_transform_data_origin
        return {'FINISHED'}
# --- Hết đoạn code mới ---
