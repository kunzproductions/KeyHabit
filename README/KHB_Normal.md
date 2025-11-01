# KeyHabit Normal Tools

## Mục tiêu

- **Quản lý Weighted Normal modifiers** với vertex groups để kiểm soát tính toán normal
- **Quy trình Data Transfer** cho custom normals từ source objects
- **Quy trình Split faces và weld** để tạo sharp edges với custom normals
- **Face Set Tools** để chuyển đổi Face Set boundaries thành Sharp Edges
- **Khôi phục normals** về trạng thái mặc định của Blender

---

## 1. Hệ thống Weighted Normal

### **Vertex Groups:**
- **`KHB_FaceArea`**: Weighted normal dựa trên diện tích face
- **`KHB_CornerAngle`**: Weighted normal dựa trên góc corner  
- **`KHB_FaceAreaAngle`**: Weighted normal kết hợp Face Area + Angle

### **Logic Modifier:**
- Mỗi vertex group tương ứng với một Weighted Normal modifier
- Vertices chỉ có thể thuộc một group tại một thời điểm
- Khi chuyển vertex sang group khác, tự động xóa khỏi group cũ

### **Các chế độ Weighted Normal:**
```python
# Face Area: Dựa trên diện tích face
mod.mode = 'FACE_AREA'

# Corner Angle: Dựa trên góc corner
mod.mode = 'CORNER_ANGLE' 

# Face Area + Angle: Kết hợp cả hai
mod.mode = 'FACE_AREA_WITH_ANGLE'
```

---

## 2. Các Operators

### **KEYHABIT_OT_weight_face_area**
- **Mục đích**: Gán vertices vào group `KHB_FaceArea`
- **Input**: Vertices/edges/faces đã chọn trong Edit Mode
- **Logic**:
  1. Chuyển sang Object Mode
  2. Xóa vertices khỏi group `KHB_CornerAngle` (nếu có)
  3. Thêm vertices vào group `KHB_FaceArea`
  4. Đảm bảo Weighted Normal modifier với mode `FACE_AREA`
  5. Chuyển về Edit Mode

### **KEYHABIT_OT_weight_corner_angle**
- **Mục đích**: Gán vertices vào group `KHB_CornerAngle`
- **Input**: Vertices/edges/faces đã chọn trong Edit Mode
- **Logic**: Tương tự Face Area nhưng với mode `CORNER_ANGLE`

### **KEYHABIT_OT_weight_face_area_angle**
- **Mục đích**: Gán vertices vào group `KHB_FaceAreaAngle`
- **Input**: Vertices/edges/faces đã chọn trong Edit Mode
- **Logic**:
  1. Xóa vertices khỏi TẤT CẢ groups khác (`KHB_FaceArea`, `KHB_CornerAngle`)
  2. Thêm vertices vào group `KHB_FaceAreaAngle`
  3. Đảm bảo Weighted Normal modifier với mode `FACE_AREA_WITH_ANGLE`

---

## 3. Quy trình Data Transfer

### **KEYHABIT_OT_setup_data_transfer**
- **Mục đích**: Tạo vertex group và Data Transfer modifier cho custom normals
- **Input**: Vertices/edges/faces đã chọn trong Edit Mode
- **Logic**:
  1. Tạo vertex group với tên `KHB_Data_XX` (XX là số tăng dần)
  2. Tạo Data Transfer modifier với tên `KHB_DataTransfer_XX`
  3. Cấu hình modifier:
     - `use_loop_data = True`
     - `data_types_loops = {'CUSTOM_NORMAL'}`
     - `loop_mapping = 'POLYINTERP_NEAREST'`
     - `vertex_group = vg_name`
  4. Kích hoạt và mở rộng modifier

### **Cấu hình Data Transfer:**
```python
mod.use_loop_data = True
mod.data_types_loops = {'CUSTOM_NORMAL'}
mod.loop_mapping = 'POLYINTERP_NEAREST'
mod.vertex_group = vg_name
mod.show_viewport = True
mod.show_in_editmode = True
mod.show_on_cage = True
```

---

## 4. Quy trình Split Faces và Weld

### **KEYHABIT_OT_split_faces_and_weld**
- **Mục đích**: Split faces đã chọn, xóa vertices khỏi Data Transfer groups, thiết lập weld
- **Input**: Faces đã chọn trong Edit Mode
- **Logic**:
  1. **Xác định boundary vertices** trước khi split (vertices selected nhưng có unselected faces)
  2. **Split faces đã chọn** bằng `bpy.ops.mesh.split()`
  3. **Thu thập boundary vertices** sau split (cả hai bên)
  4. **Tạo boundary vertex group** `KHB_WeldBoundarySharpFace`
  5. **Xóa vertices** khỏi tất cả Data Transfer vertex groups
  6. **Đảm bảo Weld modifier** `KBH_Weld` sau Data Transfer modifiers
  7. **Gán boundary group** cho Weld modifier

### **Phát hiện Boundary:**
```python
# Trước split: tìm vertices selected nhưng có unselected faces
boundary_keys = set()
for v in bm.verts:
    if v.select and any((not f.select) for f in v.link_faces):
        boundary_keys.add(_co_key(v.co))

# Sau split: tìm tất cả vertices có cùng coordinates
boundary_all_indices = [v.index for v in bm.verts if _co_key(v.co) in boundary_keys]
```

### **Thiết lập Weld Modifier:**
```python
weld = obj.modifiers.new(name='KBH_Weld', type='WELD')
weld.merge_threshold = 0.0001
weld.vertex_group = 'KHB_WeldBoundarySharpFace'
weld.show_viewport = True
weld.show_in_editmode = True
weld.show_on_cage = True
```

---

## 5. Face Set Tools

### **KEYHABIT_OT_face_set_to_sharp_edge**
- **Mục đích**: Chuyển đổi Face Set boundaries thành Sharp Edges
- **Input**: Mesh object có Face Sets (tạo trong Sculpt Mode)
- **Supported Modes**: Object Mode và Edit Mode
- **Logic**:
  1. **Lưu trữ mode gốc** của object
  2. **Chuyển sang Edit Mode** nếu cần (từ Object Mode)
  3. **Kiểm tra Face Sets**: Tìm `.sculpt_face_set` layer
  4. **Validate Face Sets**: Cần ít nhất 2 Face Sets để tạo boundaries
  5. **Clear sharp edges**: Xóa tất cả sharp edges hiện tại
  6. **Tìm boundaries**: Edges nối giữa các Face Sets khác nhau
  7. **Mark sharp**: Đánh dấu boundary edges là sharp
  8. **Khôi phục mode gốc** sau khi hoàn thành

### **Face Set Detection:**
```python
# Kiểm tra Face Set layer
face_set_layer = bm.faces.layers.int.get('.sculpt_face_set')
if face_set_layer is None:
    # Không có Face Sets
    return {'CANCELLED'}

# Kiểm tra số lượng Face Sets
face_set_values = set(face[face_set_layer] for face in bm.faces)
if len(face_set_values) <= 1:
    # Cần ít nhất 2 Face Sets
    return {'CANCELLED'}
```

### **Boundary Detection:**
```python
# Tìm edges nối giữa các Face Sets khác nhau
for edge in bm.edges:
    connected_faces = list(edge.link_faces)
    if len(connected_faces) == 2:
        face1, face2 = connected_faces
        face1_set = face1[face_set_layer]
        face2_set = face2[face_set_layer]
        if face1_set != face2_set:
            edge.smooth = False  # Mark as sharp
```

### **Mode Handling:**
```python
# Lưu mode gốc
original_mode = obj.mode

# Chuyển sang Edit Mode nếu cần
if original_mode != 'EDIT':
    bpy.ops.object.mode_set(mode='EDIT')

# ... xử lý Face Sets ...

# Khôi phục mode gốc
if original_mode != 'EDIT':
    bpy.ops.object.mode_set(mode=original_mode)
```

---

## 6. Khôi phục Normals

### **KEYHABIT_OT_restore_normals**
- **Mục đích**: Xóa tất cả KHB groups/modifiers, khôi phục về normal mặc định
- **Logic**:
  1. **Xóa KHB vertex groups**: `KHB_FaceArea`, `KHB_CornerAngle`, `KHB_FaceAreaAngle`
  2. **Xóa KHB Weighted Normal modifiers**: Tương ứng với vertex groups
  3. **Shade Smooth**: `bpy.ops.object.shade_smooth(keep_sharp_edges=True)`
  4. **Average Normals**: `bpy.ops.mesh.average_normals(average_type='CORNER_ANGLE', weight=50, threshold=0.01)`

---

## 7. Các hàm Helper

### **Lựa chọn Vertex:**
```python
def _get_selected_vertices(context) -> List[int]:
    # Thu thập vertices từ selection (vertex/edge/face mode)
    # Trả về danh sách vertex indices đã sắp xếp
    # Hỗ trợ cả Object Mode và Edit Mode
```

### **Coordinate Key:**
```python
def _co_key(vec) -> tuple:
    # Làm tròn coordinates để tránh lỗi float precision
    return (round(vec.x, 6), round(vec.y, 6), round(vec.z, 6))
```

### **Safe Attribute Setting:**
```python
def _safe_set_attr(obj, attr_name: str, value, fallback=None):
    # Set attribute an toàn với fallback
    # Xử lý lỗi và log thông tin
```

### **Weighted Normal Modifier:**
```python
def _ensure_weighted_normal_modifier(obj, mod_name, mode, vgroup_name):
    # Tạo hoặc cập nhật Weighted Normal modifier
    # Set mode, weight=100, keep_sharp=True
    # Gán vertex group
```

### **Vertex Group Management:**
```python
def _move_vertices_between_groups(obj, vertex_indices, from_groups, to_group):
    # Di chuyển vertices giữa các groups
    # Trả về số vertices moved và added_new
```

---

## 8. Ví dụ Quy trình

### **Weighted Normal cơ bản:**
1. Chọn vertices cần smooth
2. Chạy `KEYHABIT_OT_weight_face_area` hoặc `KEYHABIT_OT_weight_corner_angle`
3. Vertices được gán vào group và modifier được tạo

### **Quy trình Data Transfer:**
1. Chọn vertices cần transfer normals
2. Chạy `KEYHABIT_OT_setup_data_transfer`
3. Thiết lập source object trong Data Transfer modifier
4. Custom normals được transfer từ source

### **Quy trình Sharp Edge:**
1. Chọn faces cần split
2. Chạy `KEYHABIT_OT_split_faces_and_weld`
3. Faces được split, vertices bị xóa khỏi Data Transfer groups
4. Weld modifier được thiết lập để merge boundary vertices

### **Quy trình Face Set to Sharp Edge:**
1. **Tạo Face Sets** trong Sculpt Mode (ít nhất 2 Face Sets)
2. **Chuyển sang Object Mode** hoặc Edit Mode
3. **Chạy** `KEYHABIT_OT_face_set_to_sharp_edge`
4. **Kết quả**: Tất cả boundaries giữa Face Sets trở thành Sharp Edges

### **Quy trình Reset:**
1. Chạy `KEYHABIT_OT_restore_normals`
2. Tất cả KHB groups/modifiers bị xóa
3. Object về trạng thái normal mặc định

---

## 9. Ghi chú Kỹ thuật

### **Chuyển đổi Mode:**
- **Weighted Normal operators**: Chuyển sang Object Mode để thao tác vertex groups/modifiers
- **Face Set operator**: Tự động chuyển sang Edit Mode nếu cần, khôi phục mode gốc sau khi hoàn thành
- **Data Transfer operators**: Chuyển sang Object Mode để tạo modifiers
- **Split/Weld operators**: Hoạt động trong Edit Mode

### **Xử lý Lỗi:**
- Try-catch cho tất cả Blender API calls
- Phương thức fallback cho vertex group operations
- Ghi log lỗi với hàm `log()`
- Mode restoration an toàn với error handling

### **Hiệu suất:**
- Thao tác batch cho vertex groups
- Phát hiện boundary hiệu quả với coordinate keys
- Chuyển đổi mode tối thiểu
- Face Set detection nhanh với set operations

### **Tương thích:**
- Hỗ trợ Blender 4.2+ với int weight values
- Fallback cho phiên bản cũ hơn
- Xử lý lỗi mạnh mẽ cho API changes
- Face Set tools hoạt động trên tất cả phiên bản Blender có Sculpt Mode

---

## 10. Cấu trúc Panel UI

### **Face Set Tools:**
- **Vị trí**: Luôn hiển thị ở đầu panel
- **Visibility**: Hiển thị trong cả Object Mode và Edit Mode
- **Enable**: Button luôn enable khi có mesh object
- **Icon**: `SHADING_SOLID`

### **Weighted Normal Tools:**
- **Vị trí**: Sau Face Set Tools
- **Visibility**: Hiển thị khi có mesh object
- **Enable**: Enable khi có mesh object
- **Icons**: `NORMALS_FACE`, `NORMALS_VERTEX`, `NODE_TEXTURE`

### **Data Transfer Tools:**
- **Vị trí**: Sau Weighted Normal Tools
- **Visibility**: Hiển thị khi có mesh object
- **Enable**: Enable khi có mesh object
- **Icon**: `MODIFIER`

### **Restore Tools:**
- **Vị trí**: Cuối panel
- **Visibility**: Hiển thị khi có mesh object
- **Enable**: Enable khi có mesh object
- **Icon**: `RECOVER_LAST`

---

## 11. Lịch sử Cập nhật

### **Version 2.0** (Current)
- ✅ **Face Set Tools**: Thêm tính năng chuyển đổi Face Set boundaries thành Sharp Edges
- ✅ **Multi-mode Support**: Face Set operator hoạt động trong cả Object Mode và Edit Mode
- ✅ **Code Optimization**: Tối ưu hóa code, giảm từ 984 dòng xuống ~750 dòng
- ✅ **Helper Functions**: Thêm các helper functions để tái sử dụng code
- ✅ **Error Handling**: Cải thiện xử lý lỗi và mode restoration

### **Version 1.0** (Previous)
- ✅ **Weighted Normal System**: Hệ thống quản lý Weighted Normal modifiers
- ✅ **Data Transfer Workflow**: Quy trình Data Transfer cho custom normals
- ✅ **Split/Weld Workflow**: Quy trình Split faces và Weld
- ✅ **Restore Functionality**: Khôi phục normals về trạng thái mặc định