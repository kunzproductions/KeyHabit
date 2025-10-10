import bpy
from bpy.types import GizmoGroup, Operator

# ========== HƯỚNG DẪN SỬ DỤNG (Vietnamese Instructions) ==========
# File này chứa các công cụ nhanh cho Blender với Gizmo UI:
# - Toggle Wireframe: Bật/tắt hiển thị wireframe overlay
# - Toggle Edge Length: Bật/tắt hiển thị độ dài cạnh
# - Toggle Retopology: Bật/tắt hiển thị retopology overlay
# - Toggle Split Normals: Bật/tắt hiển thị split normals
# 
# Cách sử dụng:
# 1. Mở Blender
# 2. Vào Text Editor và load file này
# 3. Chạy script (Alt+P hoặc Run Script)
# 4. Các nút Gizmo sẽ xuất hiện ở góc trái dưới viewport
# 5. Click vào nút để bật/tắt overlay (xanh = bật, xám = tắt)

# ========== Utils ==========

def iter_view3d_spaces(context):
    """Lặp qua tất cả VIEW_3D spaces trong window hiện tại"""
    for area in context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    yield area, space

def tag_redraw_view3d(context):
    """Đánh dấu tất cả VIEW_3D areas để vẽ lại"""
    for area, _ in iter_view3d_spaces(context):
        area.tag_redraw()

# ========== Operators ==========

class KHABIT_OT_toggle_wireframe(Operator):
    """Toggle wireframe overlay trong tất cả 3D viewports"""
    bl_idname = "keyhabit.toggle_wireframe"
    bl_label = "Wireframe"
    bl_description = "Bật/tắt hiển thị wireframe overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_wireframes = not ov.show_wireframes
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_edge_length(Operator):
    """Toggle edge length overlay trong tất cả 3D viewports"""
    bl_idname = "keyhabit.toggle_edge_length"
    bl_label = "Edge Length"
    bl_description = "Bật/tắt hiển thị độ dài cạnh"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_extra_edge_length = not ov.show_extra_edge_length
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_retopo(Operator):
    """Toggle retopology overlay trong tất cả 3D viewports"""
    bl_idname = "keyhabit.toggle_retopology"
    bl_label = "Retopology"
    bl_description = "Bật/tắt hiển thị retopology overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_retopology = not ov.show_retopology
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KHABIT_OT_toggle_split_normals(Operator):
    """Toggle split normals overlay trong tất cả 3D viewports"""
    bl_idname = "keyhabit.toggle_split_normals"
    bl_label = "Split Normals"
    bl_description = "Bật/tắt hiển thị split normals"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_split_normals = not ov.show_split_normals
        tag_redraw_view3d(context)
        return {'FINISHED'}

# ========== GizmoGroup với UI tối ưu ==========

class KHABIT_GGT_overlay_buttons(GizmoGroup):
    """Gizmo buttons để toggle overlays, hiển thị ở góc trái dưới viewport"""
    bl_idname = "KEYHABIT_GGT_overlay_buttons"
    bl_label = "KeyHabit Overlay Buttons"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'PERSISTENT', 'SCALE'}

    # Cấu hình layout - tối ưu cho góc trái dưới
    base_offset_x = 60        # Khoảng cách từ cạnh trái
    base_offset_y = 60        # Khoảng cách từ cạnh dưới
    btn_scale = 32            # Kích thước nút (tăng từ 28 lên 32 cho dễ nhìn)
    btn_gap = 12              # Khoảng cách giữa các nút

    def setup(self, context):
        """Khởi tạo 4 gizmo buttons với icon và operator tương ứng"""
        
        # Button 1: Wireframe Overlay
        g1 = self.gizmos.new("GIZMO_GT_button_2d")
        g1.target_set_operator("keyhabit.toggle_wireframe")
        g1.icon = 'SHADING_WIRE'  # Icon wireframe chuẩn Blender
        g1.draw_options = {'BACKDROP', 'OUTLINE'}
        g1.alpha = 0.85           # Độ trong suốt khi không hover
        g1.alpha_highlight = 1.0  # Độ trong suốt khi hover
        g1.scale_basis = self.btn_scale
        g1.use_draw_scale_controls = False

        # Button 2: Edge Length
        g2 = self.gizmos.new("GIZMO_GT_button_2d")
        g2.target_set_operator("keyhabit.toggle_edge_length")
        g2.icon = 'MOD_EDGESPLIT'  # Icon edge split
        g2.draw_options = {'BACKDROP', 'OUTLINE'}
        g2.alpha = 0.85
        g2.alpha_highlight = 1.0
        g2.scale_basis = self.btn_scale
        g2.use_draw_scale_controls = False

        # Button 3: Retopology
        g3 = self.gizmos.new("GIZMO_GT_button_2d")
        g3.target_set_operator("keyhabit.toggle_retopology")
        g3.icon = 'MESH_DATA'  # Icon mesh data
        g3.draw_options = {'BACKDROP', 'OUTLINE'}
        g3.alpha = 0.85
        g3.alpha_highlight = 1.0
        g3.scale_basis = self.btn_scale
        g3.use_draw_scale_controls = False

        # Button 4: Split Normals
        g4 = self.gizmos.new("GIZMO_GT_button_2d")
        g4.target_set_operator("keyhabit.toggle_split_normals")
        g4.icon = 'NORMALS_VERTEX'  # Icon vertex normals
        g4.draw_options = {'BACKDROP', 'OUTLINE'}
        g4.alpha = 0.85
        g4.alpha_highlight = 1.0
        g4.scale_basis = self.btn_scale
        g4.use_draw_scale_controls = False

        # Lưu reference để sử dụng trong draw_prepare
        self.wireframe_btn = g1
        self.edge_length_btn = g2
        self.retopo_btn = g3
        self.split_normals_btn = g4

    @classmethod
    def poll(cls, context):
        """Chỉ hiển thị trong VIEW_3D space"""
        return context.space_data and context.space_data.type == 'VIEW_3D'

    def draw_prepare(self, context):
        """Cập nhật vị trí và màu sắc của gizmos mỗi frame"""
        # Kiểm tra an toàn: đảm bảo setup() đã hoàn thành
        if not all(hasattr(self, attr) for attr in 
                   ['wireframe_btn', 'edge_length_btn', 'retopo_btn', 'split_normals_btn']):
            return

        # Lấy overlay từ space hiện tại
        ov = None
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            break

        if not ov:
            return

        # Màu sắc theo trạng thái (đồng bộ với Blender UI)
        on_color = (0.3, 0.7, 1.0)    # Xanh dương khi bật (Blender accent color)
        off_color = (0.5, 0.5, 0.5)   # Xám khi tắt (neutral)
        highlight_color = (1.0, 1.0, 1.0)  # Trắng khi hover

        # Danh sách gizmos và thuộc tính overlay tương ứng
        gizmo_data = [
            (self.wireframe_btn, 'show_wireframes'),
            (self.edge_length_btn, 'show_extra_edge_length'),
            (self.retopo_btn, 'show_retopology'),
            (self.split_normals_btn, 'show_split_normals')
        ]

        # Thiết lập vị trí theo hàng ngang và màu sắc
        x = self.base_offset_x
        for gizmo, overlay_attr in gizmo_data:
            # Cập nhật vị trí (matrix_basis: cột 3 là translate x/y)
            gizmo.matrix_basis[0][3] = x
            gizmo.matrix_basis[1][3] = self.base_offset_y

            # Cập nhật màu theo trạng thái overlay
            is_on = getattr(ov, overlay_attr, False)
            gizmo.color = on_color if is_on else off_color
            gizmo.color_highlight = highlight_color

            # Tăng x cho nút tiếp theo
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
    """Đăng ký tất cả classes"""
    for cls in classes:
        bpy.utils.register_class(cls)
    print("KeyHabit Overlay Gizmos đã được đăng ký thành công!")

def unregister():
    """Hủy đăng ký tất cả classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("KeyHabit Overlay Gizmos đã được hủy đăng ký.")

if __name__ == "__main__":
    register()
