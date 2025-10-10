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

#code Button


import bpy
from bpy.types import GizmoGroup, Operator

# ========== Utils ==========

def iter_view3d_spaces(context):
    for area in context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    yield area, space

def tag_redraw_view3d(context):
    for area, _ in iter_view3d_spaces(context):
        area.tag_redraw()

# ========== Operators ==========

class KHABIT_OT_toggle_wireframe(Operator):
    bl_idname = "keyhabit.toggle_wireframe"
    bl_label = "Toggle Wireframe Overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_wireframes = not ov.show_wireframes
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_edge_length(Operator):
    bl_idname = "keyhabit.toggle_edge_length"
    bl_label = "Toggle Edge Length"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_extra_edge_length = not ov.show_extra_edge_length
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_retopo(Operator):
    bl_idname = "keyhabit.toggle_retopology"
    bl_label = "Toggle Retopology Overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_retopology = not ov.show_retopology
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_split_normals(Operator):
    bl_idname = "keyhabit.toggle_split_normals"
    bl_label = "Toggle Split Normals"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_split_normals = not ov.show_split_normals
        tag_redraw_view3d(context)
        return {'FINISHED'}

# ========== GizmoGroup với icon hợp lệ và kiểm tra an toàn ==========

class KHABIT_GGT_overlay_buttons(GizmoGroup):
    bl_idname = "KEYHABIT_GGT_overlay_buttons"
    bl_label = "KeyHabit Overlay Buttons"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    # Tùy chỉnh bố cục
    base_offset_x = 50
    base_offset_y = 50
    btn_scale = 28
    btn_gap = 10

    def setup(self, context):
        # 🔧 SỬA LỖI: Sử dụng icon hợp lệ từ Blender 4.5 enum
        
        # Button 1: Wireframe - dùng SHADING_WIRE thay vì WIRE
        g1 = self.gizmos.new("GIZMO_GT_button_2d")
        g1.target_set_operator("keyhabit.toggle_wireframe")
        g1.icon = 'SHADING_WIRE'  # ✅ Icon hợp lệ
        g1.draw_options = {'BACKDROP', 'OUTLINE'}
        g1.alpha = 0.8
        g1.alpha_highlight = 1.0
        g1.scale_basis = self.btn_scale

        # Button 2: Edge Length - giữ nguyên MOD_EDGESPLIT
        g2 = self.gizmos.new("GIZMO_GT_button_2d")
        g2.target_set_operator("keyhabit.toggle_edge_length")
        g2.icon = 'MOD_EDGESPLIT'  # ✅ Icon hợp lệ
        g2.draw_options = {'BACKDROP', 'OUTLINE'}
        g2.alpha = 0.8
        g2.alpha_highlight = 1.0
        g2.scale_basis = self.btn_scale

        # Button 3: Retopology - giữ nguyên MESH_DATA
        g3 = self.gizmos.new("GIZMO_GT_button_2d")
        g3.target_set_operator("keyhabit.toggle_retopology")
        g3.icon = 'MESH_DATA'  # ✅ Icon hợp lệ
        g3.draw_options = {'BACKDROP', 'OUTLINE'}
        g3.alpha = 0.8
        g3.alpha_highlight = 1.0
        g3.scale_basis = self.btn_scale

        # Button 4: Split Normals - giữ nguyên NORMALS_VERTEX
        g4 = self.gizmos.new("GIZMO_GT_button_2d")
        g4.target_set_operator("keyhabit.toggle_split_normals")
        g4.icon = 'NORMALS_VERTEX'  # ✅ Icon hợp lệ
        g4.draw_options = {'BACKDROP', 'OUTLINE'}
        g4.alpha = 0.8
        g4.alpha_highlight = 1.0
        g4.scale_basis = self.btn_scale

        # Lưu reference gizmos
        self.wireframe_btn = g1
        self.edge_length_btn = g2
        self.retopo_btn = g3
        self.split_normals_btn = g4

    @classmethod
    def poll(cls, context):
        return context.space_data and context.space_data.type == 'VIEW_3D'

    def draw_prepare(self, context):
        # 🔧 SỬA LỖI: Kiểm tra gizmos đã được tạo chưa
        if not all(hasattr(self, attr) for attr in ['wireframe_btn', 'edge_length_btn', 'retopo_btn', 'split_normals_btn']):
            return  # Thoát nếu setup() chưa hoàn thành

        # Tính vị trí gốc trái dưới
        x0 = self.base_offset_x
        y0 = self.base_offset_y

        # Lấy overlay từ space hiện tại
        ov = None
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            break

        if not ov:
            return  # Không có overlay space

        # Màu theo trạng thái
        on_color = (0.2, 0.8, 1.0)
        off_color = (0.8, 0.2, 0.2)

        # Danh sách gizmos và thuộc tính overlay tương ứng
        gizmo_data = [
            (self.wireframe_btn, 'show_wireframes'),
            (self.edge_length_btn, 'show_extra_edge_length'), 
            (self.retopo_btn, 'show_retopology'),
            (self.split_normals_btn, 'show_split_normals')
        ]

        # Thiết lập vị trí theo hàng ngang + trạng thái màu
        x = x0
        for gizmo, overlay_attr in gizmo_data:
            # matrix_basis: cột 3 là translate x/y cho gizmo 2D
            gizmo.matrix_basis[0][3] = x
            gizmo.matrix_basis[1][3] = y0

            # Đọc trạng thái overlay
            is_on = getattr(ov, overlay_attr, False)
            gizmo.color = on_color if is_on else off_color
            gizmo.color_highlight = (1.0, 1.0, 1.0)

            # Tịnh tiến x cho nút kế tiếp
            x += gizmo.scale_basis + self.btn_gap

# ========== Đăng ký / Hủy đăng ký ==========

classes = (
    KHABIT_OT_toggle_wireframe,
    KHABIT_OT_toggle_edge_length,
    KHABIT_OT_toggle_retopo,
    KHABIT_OT_toggle_split_normals,
    KHABIT_GGT_overlay_buttons,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
