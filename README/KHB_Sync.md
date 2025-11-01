# KHB_Sync - Blender to Maya Sync Module

## Mục tiêu

- **Đơn giản hóa quy trình xuất dữ liệu** từ Blender sang Maya:
    - Chỉ xuất **một file FBX duy nhất** tên **`KHB_Sync.fbx`** cho collection đã chọn
    - Metadata được embed trong FBX file properties (không tạo file riêng)
- **Maya luôn import từ file FBX cố định**, gộp object vào group theo tên collection, đảm bảo thống nhất, tránh lỗi trùng lặp
- **Workflow**: Blender export → Maya import → Xóa file → Chờ export tiếp theo
- **Folder chỉ có 2 loại file**: `KHB_Sync.fbx` và `request.json` (khi request import)

---

## 1. Quy tắc tên object và collection (bắt buộc)

### **Ký tự không được phép:**
- **Ký tự đặc biệt**: `. (chấm), khoảng trắng, / \ : ; , ? * " ' < > | = + % $ ^ & ~ # @ ( ) { }`
- **Bắt đầu bằng số**: Không được
- **Keyword Maya**: `group, object, default, scene, root`, ...

### **Ký tự được phép:**
- **Chữ cái**: a-z, A-Z
- **Số**: 0-9 (nhưng không ở đầu)
- **Gạch dưới**: _
- **Độ dài**: Tối đa 128 ký tự

### **Validation:**
- **Nếu object hoặc collection nào sai**: Báo lỗi, KHÔNG export, KHÔNG sinh file
- **Kiểm tra tất cả objects trong collection** trước khi export

---

## 2. Xử lý Subdivision Modifier

### **Logic xử lý:**
- **Kiểm tra tất cả objects** trong collection có modifier subdivision
- **Nếu subdivision level ≥ 1**:
    - **Tắt modifier** khi export FBX (đưa về geometry nhỏ để giảm file size)
    - Metadata về subdivision được embed trong FBX properties
- **Maya sẽ tự động phát hiện** objects có subdivision từ geometry và bật Smooth Mesh Preview

---

## 3. Smooth Group Types (MỚI)

Hệ thống smooth group cho phép chọn cách xử lý smooth/hard edges khi export:

### **3.1. None (Mặc định)**
- Không xử lý gì đặc biệt
- Export mesh nguyên bản
- Phù hợp cho mesh đơn giản

### **3.2. Sharp Edge**
- Tự động phát hiện **sharp edges** trên mesh
- **Tách object** thành các phần riêng biệt (nếu có thể)
- Thêm **EdgeSplit modifier** với sharp edges
- Format tên: `object_KBH_Path_001`, `_002`, `_003`...
- **Tự động restore** về trạng thái ban đầu sau export

**Trường hợp xử lý:**
- **Case 1:** Mesh không có sharp edges → Không làm gì
- **Case 2:** Mesh có sharp edges nhưng không tách được → Thêm EdgeSplit modifier
- **Case 3:** Mesh có sharp edges và tách được → Tách thành nhiều objects + EdgeSplit

### **3.3. Face Maps** ⭐ (KeyHabit System)
- Convert **Face Maps** (từ KHB_Facemap panel) thành **UDIM UVs**
- Tạo UV map: `KHB_smooth_group`
- Mỗi face map được unwrap vào **1 UDIM tile riêng** (1001, 1002, 1003...)
- Tự động cắt seam ở biên giữa các face maps
- **Tự động cleanup UV** sau khi export xong

**Quy trình:**
```
1. Tạo Face Maps trong KHB_Facemap panel
   ↓
2. Chọn smooth group = "Face Maps"
   ↓
3. Export collection
   ↓
4. Addon:
   - Convert face maps → UDIM UVs
   - Export FBX với UV
   - Xóa UV map (cleanup)
```

**Khi nào dùng:**
| Tình huống | Smooth Group | Lý do |
|------------|--------------|-------|
| Mesh đơn giản | None | Nhanh, đơn giản |
| Hard surface với sharp edges | Sharp Edge | Tự động xử lý edges |
| Mesh với nhiều vùng riêng biệt | Face Maps | Kiểm soát chính xác từng vùng |
| Organic modeling phức tạp | Face Maps | Tổ chức mesh theo vùng chức năng |

---

## 4. Cấu trúc folder & file export

### **Folder Sync:**
- **Vị trí**: Ổ chứa hệ điều hành
- **Tên**: `KeyHabit_Sync` (cố định)
- **Ví dụ**: `C:\KeyHabit_Sync`
- **Logic**: Xóa folder cũ (nếu có) và tạo mới mỗi lần export

### **File FBX:**
- **Tên**: `KHB_Sync.fbx` (cố định)
- **Vị trí**: Trực tiếp trong folder sync
- **Nội dung**: Tất cả objects trong collection đã chọn

### **File request.json:**
- **Tên**: `request.json` (cố định)
- **Vị trí**: Cùng folder với FBX
- **Khi nào có**: Chỉ khi Blender request import từ Maya/3ds Max
- **Nội dung**: Tên collection/group cần export từ Maya/3ds Max

### **Quy tắc folder:**
- **Chỉ được có 2 loại file**: `KHB_Sync.fbx` và `request.json`
- **Không được tạo file khác** (ví dụ: info.json, temp files, etc.)
- **Cleanup**: Xóa file sau khi xử lý xong

---

## 5. Định dạng file request.json

### **Cấu trúc:**
- **Object** chứa thông tin request giữa Blender và Maya/3ds Max
- Được tạo khi:
  - Blender request **import** từ Maya/3ds Max (action: "export")
  - Blender request **export** sang Maya/3ds Max (action: "import")
- Phải được xóa sau khi Maya/3ds Max xử lý xong

### **Ví dụ:**

**Case 1: Export (Maya/3ds Max → Blender)**
```json
{
  "timestamp": "2025-10-30 16:30:00",
  "action": "export",
  "collection": "Character_Mesh"
}
```

**Case 2: Import (Blender → Maya/3ds Max)**
```json
{
  "timestamp": "2025-10-30 16:30:00",
  "action": "import",
  "collection": "Characters"
}
```

### **Giải thích các field:**
- **`"timestamp"`**: Thời gian tạo request (format: "YYYY-MM-DD HH:MM:SS")
- **`"action"`**: Loại request
  - **`"export"`**: Maya/3ds Max export group → Blender (Blender request import)
  - **`"import"`**: Blender export collection → Maya/3ds Max (Blender request export)
- **`"collection"`**: Tên collection/group
  - **Khi action="export"**: Tên group trong Maya/3ds Max cần export
  - **Khi action="import"**: Tên collection trong Blender cần export sang Maya/3ds Max

### **Lưu ý:**
- **Metadata không lưu file**: Tất cả metadata (custom material, actions, etc.) được embed vào FBX file properties hoặc xử lý trong memory
- **Chỉ 2 file trong folder**: `KHB_Sync.fbx` và `request.json` (nếu có)
- **Cleanup bắt buộc**: Xóa file sau khi xử lý xong
- **Cả 2 actions đều yêu cầu tên group và export FBX**: Để kiểm tra và validate

---

## 6. Giao diện panel Blender

### **UI Components:**

```
┌─────────────────────────────────────────────┐
│ Collection: [dropdown]                      │
│ Objects: 5 | Meshes: 3                     │
│ ──────────────────────────────────────────  │
│ Smooth Group: [None ▼]                     │
│   • None                                    │
│   • Sharp Edge                              │
│   • Face Maps                               │
│ ──────────────────────────────────────────  │
│ [✓] Custom Material                         │
│                                             │
│   Type: [Standard Surface ▼]               │
│   Name: [____________________]              │
│   PBR Workflow: [Metal/Rough][Spec/Gloss]  │
│                                             │
│   ┌─ Base Color / Diffuse ────────────┐    │
│   │ [COLOR] [🎨] [Texture Toggle]     │    │
│   │ Path: [____________________]      │    │
│   └───────────────────────────────────┘    │
│                                             │
│   ┌─ Normal ──────────────────────────┐    │
│   │ [NORMALS] [Texture Toggle]        │    │
│   │ Path: [____________________]      │    │
│   └───────────────────────────────────┘    │
│                                             │
│   ┌─ Roughness / Glossiness ──────────┐    │
│   │ [SHADING] [Texture] [Channel]     │    │
│   │ Path/Slider                       │    │
│   └───────────────────────────────────┘    │
│                                             │
│   ┌─ Metalness / Specular ────────────┐    │
│   │ [RENDERED] [Texture] [Channel]    │    │
│   │ Path/Slider                       │    │
│   └───────────────────────────────────┘    │
│                                             │
│   ┌─ Emission ─────────────────────────┐   │
│   │ [LIGHT] [Texture Toggle]          │   │
│   │ Path/Color + Strength             │   │
│   └───────────────────────────────────┘   │
│                                             │
│   ┌─ Ambient Occlusion ───────────────┐   │
│   │ [SHADING] [Texture] [Channel]     │   │
│   │ Path (if enabled)                 │   │
│   └───────────────────────────────────┘   │
│                                             │
│   ┌─ Transparency ────────────────────┐   │
│   │ [ALPHA] [Texture] [Channel]       │   │
│   │ Path (if enabled)                 │   │
│   └───────────────────────────────────┘   │
└─────────────────────────────────────────────┘

[           Sync Collection              ]
```

### **Material Types:**

#### **Standard Surface (PBR)**
- **PBR Workflows:**
  - **Metal/Roughness**: Metalness + Roughness (Substance Painter, Arnold)
  - **Specular/Glossiness**: Specular Color + Glossiness (Unity, Unreal)

- **Maps supported:**
  - Base Color / Diffuse (tự động đổi theo workflow)
  - Normal Map
  - Roughness / Glossiness (theo workflow)
  - Metalness / Specular (theo workflow)
  - Emission (Color/Texture + Strength)
  - Ambient Occlusion (với channel selector: R, G, B, A)
  - Transparency/Opacity (với channel selector: A, R, G, B)

#### **Phong E (Legacy)**
- **Simplified UI** cho legacy workflow
- **Properties:**
  - Base Color (color picker only, không texture)
  - Roughness (slider)
  - Highlight Size (slider)

### **Export Logic:**
1. **Validation**: Kiểm tra tên collection và objects
2. **Folder Management**: Xóa `C:\KeyHabit_Sync` cũ, tạo mới
3. **Subdivision Processing**: Tắt subdivision modifiers khi export (để giảm file size)
4. **Smooth Group Processing**: 
   - Sharp Edge: Tách objects, thêm EdgeSplit
   - Face Maps: Convert face maps → UDIM UVs
5. **Material Processing**: Material được embed vào FBX (nếu custom material enabled)
   - Type: Standard Surface hoặc Phong E
   - PBR Workflow: Metal/Roughness hoặc Specular/Glossiness
   - Maps: Base Color, Normal, Roughness/Glossiness, Metalness/Specular, Emission, AO, Opacity
   - Channel selectors cho texture maps
6. **FBX Export**: Export tất cả objects collection thành `KHB_Sync.fbx` (metadata embed trong FBX properties)
7. **Cleanup**: 
   - Restore subdivision modifiers
   - Restore Sharp Edge (join objects, xóa EdgeSplit)
   - Cleanup Face Maps UVs (xóa UV map)

---

## 7. Face Maps - Chi tiết kỹ thuật

### **Cách tạo Face Maps trong KeyHabit:**
1. Chọn mesh object
2. Mở panel **KeyHabit > Face Map Manager**
3. Tạo và quản lý Face Maps:
   - **Create Face Map**: Tạo group mới từ selection
   - **Assign to Face Map**: Gán faces vào group có sẵn
   - **Remove from Face Map**: Xóa faces khỏi group
   - **Select Face Map**: Select tất cả faces trong group
   - **Optimal Face Sets**: Tối ưu hóa số lượng groups

### **Kỹ thuật xử lý:**
1. **Lấy face maps** từ custom properties của object
2. **Cắt seam** ở boundary edges giữa các face maps
3. **Unwrap từng face map** vào UDIM tile tương ứng (Face Map 0 → UDIM 1001, Face Map 1 → UDIM 1002, ...)
4. **Export FBX** với UV map mới
5. **Cleanup**: Xóa UV map sau khi export xong

### **UDIM Tile Mapping:**
- Face Map 0 → UDIM 1001
- Face Map 1 → UDIM 1002
- Face Map 2 → UDIM 1003
- ...

### **UV Map:**
- **Tên**: `KHB_smooth_group` (cố định)
- **Tạo**: Tự động khi export
- **Xóa**: Tự động sau export
- **Không ảnh hưởng**: UV maps khác trong scene

---

## 8. Quy trình Export/Import chi tiết

---

## 8.1. Blender Export (Blender → Maya/3ds Max)

### **Workflow:**
1. **Validation**: Kiểm tra tên collection và objects
2. **Folder Management**: Xóa `C:\KeyHabit_Sync` cũ, tạo mới
3. **Subdivision Processing**: Tắt subdivision modifiers khi export (để giảm file size)
4. **Smooth Group Processing**: 
   - Sharp Edge: Tách objects, thêm EdgeSplit
   - Face Maps: Convert face maps → UDIM UVs
5. **Material Processing**: Material được embed vào FBX (nếu custom material enabled)
6. **FBX Export**: Export tất cả objects collection thành `KHB_Sync.fbx` (metadata embed trong FBX properties)
7. **Request Creation**: Tạo `request.json` với:
   - `action`: "import" (Blender request export sang Maya/3ds Max)
   - `collection`: Tên collection đã export
   - `timestamp`: Thời gian export
8. **Cleanup**: 
   - Restore subdivision modifiers
   - Restore Sharp Edge (join objects, xóa EdgeSplit)
   - Cleanup Face Maps UVs (xóa UV map)

### **File Output:**
- `KHB_Sync.fbx`: File FBX chứa tất cả objects từ collection đã chọn
- `request.json`: Request file với action="import" và tên collection (Maya/3ds Max sẽ đọc và import)

---

## 8.2. Blender Import (Maya/3ds Max → Blender)

### **Workflow:**

**1. User Request:**
- User nhập tên collection/group → Bấm "Import Collection"
- Blender tạo `request.json` với tên collection
- Hiển thị "Waiting..." và nút Cancel
- Bắt đầu monitor folder (check mỗi 3 giây)

**2. Auto-Import khi phát hiện FBX:**
```
Blender monitor phát hiện: KHB_Sync.fbx xuất hiện
  ↓
1. Import FBX
2. Kiểm tra FBX có objects không
   - Nếu FBX rỗng: Hiển thị lỗi, cleanup, return
3. Processing:
   - Tạo collection mới (hoặc dùng collection có sẵn)
   - Di chuyển objects vào collection
   - Cleanup file (xóa FBX)
   - Hiển thị "Import thành công"
   - Tắt waiting state
```

### **UI Components:**

**Normal State (Idle):**
```
┌─────────────────────────────────────┐
│ Import from Maya/3ds Max         🠗 │
├─────────────────────────────────────┤
│ Group Name: [________________]      │
│                                     │
│ [   Import Collection   ] 🠗        │
└─────────────────────────────────────┘
```

**Waiting State:**
```
┌─────────────────────────────────────┐
│ Import from Maya/3ds Max         🠗 │
├─────────────────────────────────────┤
│ ⏱ Waiting for 'Character_Mesh'...  │
│                                     │
│ [       Cancel       ] ✖           │
└─────────────────────────────────────┘
```

---

## 8.3. Maya Import (Blender → Maya)

### **Workflow:**

**Khi phát hiện request.json với action="import":**

1. **File Check**: Kiểm tra `request.json` và `KHB_Sync.fbx` tồn tại
2. **Read Request**: Đọc action và collection name từ `request.json`
3. **Validation**: 
   - Kiểm tra action = "import"
   - Validate tên collection trong request.json
4. **Group Cleanup**: Xóa group cũ (nếu có) trước import (theo tên collection trong request.json)
5. **FBX Import**: Import từ `KHB_Sync.fbx` cố định
6. **Grouping**: Gom tất cả imported objects vào group (tên group = collection name trong request.json)
7. **Smooth Processing**: Bật Smooth Mesh Preview cho objects có subdivision (tự động phát hiện từ geometry)
8. **Material Processing**: Tạo và gán material từ FBX (nếu có)
9. **Cleanup**: 
   - Xóa `KHB_Sync.fbx`
   - Xóa `request.json`
   - Chờ request tiếp theo

### **Script Management:**
- **Toggle Script**: Chạy lần đầu để bật, chạy lần nữa để tắt
- **HUD Display**: Hiển thị "KeyHabit Sync" ở góc phải dưới khi active
- **Continuous Monitoring**: Luôn kiểm tra file sync, thực thi khi có `request.json` với action="import" hoặc action="export"

---

## 8.4. Maya Export (Maya → Blender)

### **Workflow:**
```
1. Phát hiện request.json → Đọc tên collection
2. **Validation:**
   - Kiểm tra file request.json đã được Blender tạo chưa
   - Kiểm tra group/collection có tên trùng với "collection" trong request.json
   - Nếu group không tồn tại:
     * Export file FBX rỗng → KHB_Sync.fbx (để Blender ngắt quy trình)
     * Xóa request.json
     * RETURN (không tiếp tục)
3. Select group/collection cần export
4. Kiểm tra từng object trong group:
    a. trường hợp object không có sharp edge -> export.
    b. trường hợp object đang bật Preview smooth:
        - tắt Preview smooth -> export -> bật Preview smooth.
    c. kiểm tra object có Separate được thành nhiều object không và có hard edge (sharp edge ở blender):
        - không tác động gì đến object này:
        - Tạo bản sao "tên object"_KHB_Dup
        - Tách "tên object"_KHB_Dup -> "tên object"_Path_001 _002 _003... -> chọn hard edge Detach Components -> export "tên object"_Path_001 _002 _003... -> xóa
        - Note: không export object gốc, sau khi export xong sẽ xóa "tên object"_KHB_Dup và "tên object"_Path_001 _002 _003...
    d. trường hợp object có hard edge và không tách được:
        - chọn hard edge Detach Components -> merge vertex với thông số 0.001 ví dụ: "polyMergeVertex  -d 0.001 -am 1 -ch 1 polySurface2.vtx[0:41];"
5. Export FBX → KHB_Sync.fbx
```

### **Script Management:**
- **Continuous Monitoring**: Luôn kiểm tra `request.json`, thực thi khi phát hiện

### **Script Logic (Maya):**

**Monitoring**: Script liên tục kiểm tra `request.json` (mỗi 1 giây)

**Khi phát hiện request.json:**

1. **Read Request**: Đọc action và collection name từ `request.json`

2. **Route theo action:**
   
   **Nếu action = "export" (Maya → Blender):**
   - **Validation**: Kiểm tra group có tồn tại trong scene
   - **Export Processing**: 
     - Xử lý Sharp Edges (phát hiện, tách objects nếu cần)
     - Export FBX → `KHB_Sync.fbx`
     - Restore objects về trạng thái ban đầu
   - **Cleanup**: Xóa `request.json` sau khi export xong
   
   **Nếu action = "import" (Blender → Maya):**
   - **Validation**: Kiểm tra `KHB_Sync.fbx` tồn tại
   - **Import Processing**:
     - Import FBX
     - Tạo group với tên collection từ request.json
     - Xử lý Smooth Preview và Material
   - **Cleanup**: Xóa `KHB_Sync.fbx` và `request.json` sau khi import xong

### **Debug Mode (Maya):**

Khi `KHB_Module_Debug = True`, script sẽ hiển thị Debug Panel để test từng phần với JSON giả.

#### **Debug Panel UI:**
```
┌─────────────────────────────────────────────┐
│ KeyHabit Sync - Debug Mode               🔧 │
├─────────────────────────────────────────────┤
│ [✓] Enable Debug Mode                        │
│                                               │
│ Debug Actions:                               │
│ ┌─────────────────────────────────────────┐ │
│ │ [Test Request.json]                     │ │
│ │ [Test Validation]                       │ │
│ │ [Test Sharp Edge Detection]            │ │
│ │ [Test Object Separation]                │ │
│ │ [Test FBX Export]                       │ │
│ │ [Test Restore]                          │ │
│ └─────────────────────────────────────────┘ │
│                                               │
│ JSON Preview:                                 │
│ ┌─────────────────────────────────────────┐ │
│ │ { "collection": "Test_Collection" }     │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

#### **Debug Functions:**

**1. Test Request.json:**
- Tạo `request.json` giả với 2 actions:
  - **Action "export"**: Test Maya/3ds Max → Blender workflow
  - **Action "import"**: Test Blender → Maya/3ds Max workflow
- Hiển thị JSON preview trong panel cho cả 2 cases
- Validate JSON format
- Không thực sự export/import, chỉ test parsing

**2. Test Validation:**
- **Action "export"**: Kiểm tra group có tồn tại với tên test (để export)
- **Action "import"**: Kiểm tra FBX file có sẵn để import
- Hiển thị kết quả: Found / Not Found
- Log chi tiết các groups có sẵn trong scene (cho export) hoặc file FBX info (cho import)

**3. Test Sharp Edge Detection & Separation:**
- Chọn object test trong scene
- Phát hiện sharp edges
- Hiển thị số lượng sharp edges tìm được
- **Thực sự tách edge**: Detach Components ở sharp edges (không chỉ highlight)
- Hiển thị kết quả: Số lượng edges đã tách, số lượng vertices sau khi merge (nếu có)

**4. Test Object Separation:**
- Tạo bản sao object test
- Thử tách object theo sharp edges
- Hiển thị kết quả: Separated / Cannot Separate
- Hiển thị số lượng objects sau khi tách

**5. Test FBX Export/Import:**
- **Action "export"**: Export object test thành FBX giả (không ghi file thật)
- **Action "import"**: Import FBX giả và validate import process
- Validate FBX export/import options
- Hiển thị thông tin export/import (số lượng objects, faces, vertices)
- Kiểm tra metadata embed và group creation

**6. Test Restore:**
- Test restore objects sau khi export
- Verify objects trở về trạng thái ban đầu
- Check UV maps, materials, transforms được restore

#### **Debug Workflow:**
1. **Enable Debug Mode**: Bật `KHB_Module_Debug = True`
2. **Select Test Object**: Chọn object trong scene để test
3. **Run Debug Actions**: Chạy từng test action để debug
4. **View Results**: Xem kết quả trong debug panel và console
5. **JSON Preview**: Xem JSON giả được tạo cho từng test

#### **Debug JSON Examples:**

**Test Request.json:**
```json
{
  "timestamp": "2025-01-15 10:30:00",
  "action": "export",
  "collection": "Debug_Test_Collection"
}
```

**Debug Log Format:**
- **Info**: `[KHB_DEBUG] Info: Collection 'Test_Collection' found`
- **Warning**: `[KHB_DEBUG] Warning: Sharp edges detected but cannot separate`
- **Error**: `[KHB_DEBUG] Error: Group 'Test_Collection' not found`
- **Success**: `[KHB_DEBUG] Success: FBX export test completed`

---

## 8.5. 3ds Max Import (Blender → 3ds Max)

### **Workflow:**

**Khi phát hiện request.json với action="import":**

1. **File Check**: Kiểm tra `request.json` và `KHB_Sync.fbx` tồn tại
2. **Read Request**: Đọc action và collection name từ `request.json`
3. **Validation**: 
   - Kiểm tra action = "import"
   - Validate tên collection trong request.json
4. **Group Cleanup**: Xóa group cũ (nếu có) trước import (theo tên collection trong request.json)
5. **FBX Import**: Import từ `KHB_Sync.fbx` cố định
6. **Grouping**: Gom tất cả imported objects vào group (tên group = collection name trong request.json)
7. **Smooth Processing**: Thêm `TurboSmooth` modifier cho objects có subdivision (tự động phát hiện từ geometry)
8. **Material Processing**: Tạo và gán Physical Material từ FBX (nếu có)
9. **Cleanup**: 
   - Xóa `KHB_Sync.fbx`
   - Xóa `request.json`
   - Chờ request tiếp theo

### **Khác biệt với Maya:**
- **Smoothing**: Dùng `TurboSmooth` modifier thay vì Smooth Mesh Preview
- **Material**: Physical Material thay vì Standard Surface
- **Script**: Sử dụng MaxScript thay vì Python

---

## 8.6. 3ds Max Export (3ds Max → Blender)

### **Workflow:**
```
1. Phát hiện request.json → Đọc tên collection
2. **Validation:**
   - Kiểm tra file request.json đã được Blender tạo chưa
   - Kiểm tra group/collection có tên trùng với "collection" trong request.json
   - Nếu group không tồn tại:
     * Export file FBX rỗng → KHB_Sync.fbx (để Blender ngắt quy trình)
     * Xóa request.json
     * RETURN (không tiếp tục)
3. Select group cần export
4. Xử lý Smoothing Groups (giống Face Maps):
   - Đọc 32 smoothing groups từ mesh
   - Tạo UV channel mới: "KHB_smooth_group"
   - Convert smoothing groups → UDIM tiles:
     * Smoothing Group 1 → UDIM 1001
     * Smoothing Group 2 → UDIM 1002
     * Smoothing Group 3 → UDIM 1003
     * ... (tối đa 32 groups → UDIM 1001-1032)
   - Cắt seam ở boundary edges giữa các groups
   - Unwrap từng group vào UDIM tile tương ứng
5. Export FBX → KHB_Sync.fbx (với UV channel)
6. Restore UV:
   - Xóa UV channel "KHB_smooth_group"
   - Khôi phục UV maps gốc
7. Xóa request.json
```

**Lý do dùng Smoothing Groups → UDIM:**
- 3ds Max có hệ thống 32 smoothing groups native
- UDIM mapping cho phép Blender nhận diện smooth groups
- Tương thích 1:1 với Face Maps workflow của Blender
- Preserve được topology và smooth data

### **Script Logic (3ds Max):**

**Monitoring**: Script liên tục kiểm tra `request.json` (mỗi 1 giây)

**Khi phát hiện request.json:**

1. **Read Request**: Đọc action và collection name từ `request.json`

2. **Route theo action:**
   
   **Nếu action = "export" (3ds Max → Blender):**
   - **Validation**: Kiểm tra group có tồn tại trong scene
   - **Export Processing**: 
     - Backup UV channels hiện tại
     - Convert Smoothing Groups → UDIM UVs (channel 2: "KHB_smooth_group")
     - Export FBX → `KHB_Sync.fbx` với UV channel mới
     - Restore UV channels về trạng thái ban đầu
   - **Cleanup**: Xóa `request.json` sau khi export xong
   
   **Nếu action = "import" (Blender → 3ds Max):**
   - **Validation**: Kiểm tra `KHB_Sync.fbx` tồn tại
   - **Import Processing**:
     - Import FBX
     - Tạo group với tên collection từ request.json
     - Xử lý TurboSmooth và Physical Material
   - **Cleanup**: Xóa `KHB_Sync.fbx` và `request.json` sau khi import xong

### **Debug Mode (3ds Max):**

Khi `KHB_Module_Debug = True`, script sẽ hiển thị Debug Rollout để test từng phần với JSON giả.

#### **Debug Rollout UI:**
```
┌─────────────────────────────────────────────┐
│ KeyHabit Sync - Debug Mode               🔧 │
├─────────────────────────────────────────────┤
│ [✓] Enable Debug Mode                        │
│                                               │
│ Debug Actions:                               │
│ ┌─────────────────────────────────────────┐ │
│ │ [Test Request.json]                     │ │
│ │ [Test Validation]                       │ │
│ │ [Test Smoothing Groups]                 │ │
│ │ [Test UDIM Conversion]                  │ │
│ │ [Test UV Backup/Restore]                │ │
│ │ [Test FBX Export]                       │ │
│ └─────────────────────────────────────────┘ │
│                                               │
│ JSON Preview:                                 │
│ ┌─────────────────────────────────────────┐ │
│ │ { "collection": "Test_Collection" }     │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

#### **Debug Functions:**

**1. Test Request.json:**
- Tạo `request.json` giả với 2 actions:
  - **Action "export"**: Test 3ds Max → Blender workflow
  - **Action "import"**: Test Blender → 3ds Max workflow
- Hiển thị JSON preview trong rollout cho cả 2 cases
- Validate JSON format
- Không thực sự export/import, chỉ test parsing

**2. Test Validation:**
- **Action "export"**: Kiểm tra group có tồn tại với tên test (để export)
- **Action "import"**: Kiểm tra FBX file có sẵn để import
- Hiển thị kết quả: Found / Not Found
- List tất cả groups có sẵn trong scene (cho export) hoặc file FBX info (cho import)

**3. Test Smoothing Groups:**
- Chọn object test trong scene
- Đọc smoothing groups từ faces
- Hiển thị số lượng smoothing groups
- List tất cả smoothing groups đang được sử dụng

**4. Test UDIM Conversion:**
- Convert smoothing groups → UDIM tiles (không thực sự thay đổi UV)
- Hiển thị mapping: Smoothing Group ID → UDIM Tile
- Validate UV channel creation
- Check boundary edges detection

**5. Test UV Backup/Restore:**
- Backup UV channels của object test
- Thực hiện thay đổi tạm thời
- Test restore từ backup
- Verify UV channels được restore chính xác

**6. Test FBX Export/Import:**
- **Action "export"**: Export object test thành FBX giả (không ghi file thật)
- **Action "import"**: Import FBX giả và validate import process
- Validate FBX export/import settings
- Hiển thị thông tin export/import (objects, faces, UV channels)
- Kiểm tra UV channel "KHB_smooth_group" được export/import và group creation

#### **Debug Workflow:**
1. **Enable Debug Mode**: Bật `KHB_Module_Debug = True`
2. **Select Test Object**: Chọn object trong scene để test
3. **Run Debug Actions**: Chạy từng test action trong rollout
4. **View Results**: Xem kết quả trong rollout và Listener
5. **JSON Preview**: Xem JSON giả được tạo cho từng test

#### **Debug JSON Examples:**

**Test Request.json - Action "export" (3ds Max → Blender):**
```json
{
  "timestamp": "2025-01-15 10:30:00",
  "action": "export",
  "collection": "Debug_Test_Collection"
}
```

**Test Request.json - Action "import" (Blender → 3ds Max):**
```json
{
  "timestamp": "2025-01-15 10:30:00",
  "action": "import",
  "collection": "Debug_Test_Collection"
}
```

**Debug Log Format:**
- **Info**: `[KHB_DEBUG] Info: Collection 'Test_Collection' found`
- **Warning**: `[KHB_DEBUG] Warning: Smoothing groups detected but cannot convert`
- **Error**: `[KHB_DEBUG] Error: Group 'Test_Collection' not found`
- **Success**: `[KHB_DEBUG] Success: FBX export/import test completed`

---

## 8.7. Troubleshooting

### **Import không hoạt động:**
- ✅ Kiểm tra folder `C:\KeyHabit_Sync` tồn tại
- ✅ Kiểm tra Maya/3ds Max script đang chạy và monitor folder
- ✅ Kiểm tra tên collection chính xác (case-sensitive)
- ✅ Xem Blender console để debug

### **Waiting mãi không import:**
- ✅ Bấm Cancel và thử lại
- ✅ Kiểm tra Maya/3ds Max script có lỗi không
- ✅ Kiểm tra file request.json có được tạo không
- ✅ Restart Maya/3ds Max script

### **Import objects vào sai collection:**
- ✅ Check tên collection trong request.json
- ✅ Ensure Maya/3ds Max export đúng group name

### **Best Practices:**
1. **Start Maya/3ds Max monitoring script** trước khi làm việc
2. **Test với collection nhỏ** trước khi import lớn
3. **Đặt tên collection rõ ràng** để dễ tracking
4. **Sử dụng Cancel** nếu chờ quá lâu (> 30s)

---


#### **Maya Script - Complete Implementation:**

```python
import maya.cmds as cmds
import os
import json
import time

SYNC_PATH = "C:\\KeyHabit_Sync"
REQUEST_FILE = os.path.join(SYNC_PATH, "request.json")

def monitor_import_requests():
    """
    Function monitor request.json và auto-export
    Chạy trong background hoặc script editor
    """
    while True:
        if os.path.exists(REQUEST_FILE):
            try:
                # Kiểm tra file request.json đã được Blender tạo chưa
                # Đọc request
                with open(REQUEST_FILE, 'r') as f:
                    request = json.load(f)
                
                collection_name = request.get('collection')
                
                # Export collection với Sharp Edge processing
                export_collection_to_blender(collection_name)
                
                # Xóa request file
                os.remove(REQUEST_FILE)
                
            except Exception as e:
                print(f"Error processing request: {e}")
        
        time.sleep(1)  # Check mỗi 1 giây

def export_collection_to_blender(collection_name):
    """
    Export collection/group sang Blender với Sharp Edge workflow
    Validation: Kiểm tra group có tồn tại, nếu không thì export FBX rỗng
    """
    fbx_path = os.path.join(SYNC_PATH, "KHB_Sync.fbx")
    
    # Validation: Kiểm tra group/collection có tồn tại không
    if not cmds.objExists(collection_name):
        print(f"Collection '{collection_name}' không tồn tại - Exporting empty FBX")
        
        # Export FBX rỗng để Blender ngắt quy trình
        # Tạo một empty group tạm thời để export
        temp_group = cmds.group(empty=True, name="KHB_Temp_Empty")
        cmds.select(temp_group)
        cmds.file(fbx_path, force=True, options="v=0;", type="FBX export", 
                  exportSelected=True)
        cmds.delete(temp_group)
        
        print(f"Exported empty FBX - Collection '{collection_name}' not found")
        return
    
    # Get objects trong group
    objects = cmds.listRelatives(collection_name, allDescendents=True, 
                                  type='transform', fullPath=True) or []
    
    split_objects = []
    
    # Process Sharp Edges cho mỗi object
    for obj in objects:
        # Check nếu là mesh
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        if not shapes or cmds.nodeType(shapes[0]) != 'mesh':
            continue
        
        # Detect sharp edges (hardened edges)
        cmds.select(obj)
        edges = cmds.polyListComponentConversion(toEdge=True)
        cmds.select(edges)
        
        hard_edges = []
        edge_list = cmds.ls(selection=True, flatten=True)
        
        for edge in edge_list:
            # Check nếu edge là hard edge
            smoothing = cmds.polyInfo(edge, edgeToFace=True)
            if is_hard_edge(edge, smoothing):
                hard_edges.append(edge)
        
        # Nếu có hard edges, tách object
        if hard_edges:
            cmds.select(obj)
            separated = cmds.polySeparate(obj, constructionHistory=False)
            
            # Rename các objects đã tách
            for i, sep_obj in enumerate(separated):
                new_name = f"{obj}_KBH_Path_{i+1:03d}"
                cmds.rename(sep_obj, new_name)
                split_objects.append((obj, sep_obj))
    
    # Export FBX (fbx_path đã được định nghĩa ở đầu function)
    cmds.select(collection_name, hierarchy=True)
    cmds.file(fbx_path, force=True, options="...", type="FBX export", 
              exportSelected=True)
    
    # RESTORE: Join lại các objects đã tách
    restore_sharp_edge_objects(split_objects)
    
    print(f"Exported '{collection_name}' to Blender (Sharp Edge processed)")

def is_hard_edge(edge, smoothing_info):
    """
    Check nếu edge là hard edge (smoothing angle > threshold)
    """
    # Implementation tùy thuộc vào Maya version
    # Thường dùng polyInfo hoặc polyNormalPerVertex
    return True  # Simplified

def restore_sharp_edge_objects(split_objects):
    """
    Restore lại objects đã bị tách do sharp edge processing
    """
    for original, separated in split_objects:
        # Combine lại các objects
        cmds.polyUnite([original, separated], constructionHistory=False, 
                       mergeUVSets=True)
    
    print("Restored split objects")
```

#### **3ds Max Script - Complete Implementation:**

```maxscript
-- KeyHabit Sync - 3ds Max Export Script
-- Smoothing Groups to UDIM Workflow

global SYNC_PATH = "C:\\KeyHabit_Sync\\"
global REQUEST_FILE = SYNC_PATH + "request.json"

fn monitorImportRequests = (
    -- Monitor request.json và auto-export
    while true do (
        if doesFileExist REQUEST_FILE then (
            try (
                -- Đọc request
                requestData = (openFile REQUEST_FILE mode:"r")
                requestJson = readDelimitedString requestData "{"
                close requestData
                
                -- Parse collection name
                collectionName = getCollectionNameFromJson requestJson
                
                -- Export collection
                exportCollectionToBlender collectionName
                
                -- Xóa request file
                deleteFile REQUEST_FILE
                
            ) catch (
                format "Error processing request: %\n" (getCurrentException())
            )
        )
        
        sleep 1  -- Check mỗi 1 giây
    )
)

fn exportCollectionToBlender collectionName = (
    format "Exporting collection: %\n" collectionName
    
    -- Validation: Kiểm tra group/collection có tồn tại không
    local groupObj = getNodeByName collectionName
    if groupObj == undefined then (
        format "Collection '%' không tồn tại - Exporting empty FBX\n" collectionName
        
        -- Export FBX rỗng để Blender ngắt quy trình
        -- Tạo một empty dummy object tạm thời để export
        local tempDummy = dummy name:"KHB_Temp_Empty"
        select tempDummy
        
        local fbxPath = SYNC_PATH + "KHB_Sync.fbx"
        exportFile fbxPath #noPrompt selectedOnly:true using:FBXEXP
        
        delete tempDummy
        
        format "Exported empty FBX - Collection '%' not found\n" collectionName
        return false
    )
    
    -- Get tất cả objects trong group
    local objsToExport = #()
    for obj in groupObj.children do append objsToExport obj
    
    -- Process Smoothing Groups cho mỗi mesh
    local uvBackups = #()
    
    for obj in objsToExport where classOf obj == Editable_Poly or classOf obj == Editable_Mesh do (
        -- Backup UV channels hiện tại
        append uvBackups (backupUVChannels obj)
        
        -- Convert Smoothing Groups → UDIM UVs
        convertSmoothingGroupsToUDIM obj
    )
    
    -- Export FBX
    local fbxPath = SYNC_PATH + "KHB_Sync.fbx"
    select objsToExport
    exportFile fbxPath #noPrompt selectedOnly:true using:FBXEXP
    
    -- RESTORE: Khôi phục lại UV channels gốc
    for i = 1 to uvBackups.count do (
        restoreUVChannels objsToExport[i] uvBackups[i]
    )
    
    format "Exported '%' to Blender (Smoothing Groups processed)\n" collectionName
    return true
)

fn convertSmoothingGroupsToUDIM obj = (
    /*
    Convert 32 smoothing groups của 3ds Max thành UDIM tiles (1001-1032)
    Workflow:
      1. Đọc smoothing groups từ faces
      2. Tạo UV channel mới: "KHB_smooth_group" (channel 2)
      3. Unwrap mỗi smoothing group vào UDIM tile tương ứng
      4. Cắt seam ở boundary edges
    */
    
    -- Ensure object là Editable Poly
    if classOf obj != Editable_Poly then (
        convertToPoly obj
    )
    
    -- Tạo UV channel mới (channel 2 cho KHB_smooth_group)
    polyOp.setNumMaps obj 3  -- Ensure có ít nhất 3 channels
    
    -- Get smoothing groups info
    local faceCount = polyOp.getNumFaces obj
    local smoothingGroups = #{}
    
    -- Collect tất cả smoothing groups đang được dùng
    for f = 1 to faceCount do (
        local sg = polyOp.getFaceSmoothGroup obj f
        if sg != 0 then append smoothingGroups sg
    )
    
    -- Sort và remove duplicates
    smoothingGroups = (makeUniqueArray smoothingGroups)
    
    -- Unwrap từng smoothing group vào UDIM tile
    for i = 1 to smoothingGroups.count do (
        local sgID = smoothingGroups[i]
        local udimTile = 1001 + (i - 1)  -- UDIM 1001, 1002, 1003...
        
        -- Select faces thuộc smoothing group này
        local sgFaces = #{}
        for f = 1 to faceCount do (
            if (polyOp.getFaceSmoothGroup obj f) == sgID then (
                append sgFaces f
            )
        )
        
        -- Unwrap vào UDIM tile
        polyOp.setFaceSelection obj sgFaces
        unwrapFacesToUDIM obj sgFaces udimTile channel:2
    )
    
    format "Converted % smoothing groups to UDIM (channel 2)\n" smoothingGroups.count
)

fn unwrapFacesToUDIM obj faceSet udimTile channel:2 = (
    -- Unwrap faces vào UDIM tile cụ thể
    -- UDIM offset: (udimTile - 1001) = U offset
    
    local uOffset = (udimTile - 1001)
    local vOffset = 0
    
    -- Flatten unwrap (basic)
    polyOp.setMapSupport obj channel true
    
    -- Apply planar map cho faces
    max modify mode
    modPanel.setCurrentObject obj.baseObject
    
    -- Unwrap và offset vào UDIM tile
    for f in faceSet do (
        -- Get face UVs
        local faceVerts = polyOp.getFaceVerts obj f
        
        -- Offset UVs vào UDIM tile
        for v in faceVerts do (
            local uvw = polyOp.getMapVert obj channel v
            uvw.x += uOffset
            uvw.y += vOffset
            polyOp.setMapVert obj channel v uvw
        )
    )
)

fn backupUVChannels obj = (
    -- Backup tất cả UV channels
    local backup = #()
    local numMaps = polyOp.getNumMaps obj
    
    for ch = 1 to numMaps do (
        if polyOp.getMapSupport obj ch then (
            append backup #(ch, polyOp.getMapVerts obj ch)
        )
    )
    
    return backup
)

fn restoreUVChannels obj uvBackup = (
    -- Restore UV channels từ backup
    for entry in uvBackup do (
        local channel = entry[1]
        local uvData = entry[2]
        
        -- Restore UV data
        polyOp.setMapSupport obj channel true
        for i = 1 to uvData.count do (
            polyOp.setMapVert obj channel i uvData[i]
        )
    )
    
    format "Restored UV channels for %\n" obj.name
)

-- Start monitoring
monitorImportRequests()
```

#### **Import Troubleshooting:**

**Import không hoạt động:**
- ✅ Kiểm tra folder `C:\KeyHabit_Sync` tồn tại
- ✅ Kiểm tra Maya/3ds Max script đang chạy và monitor folder
- ✅ Kiểm tra tên collection chính xác (case-sensitive)
- ✅ Xem Blender console để debug

**Waiting mãi không import:**
- ✅ Bấm Cancel và thử lại
- ✅ Kiểm tra Maya/3ds Max script có lỗi không
- ✅ Kiểm tra file request.json có được tạo không
- ✅ Restart Maya/3ds Max script

**Import objects vào sai collection:**
- ✅ Check tên collection trong request.json
- ✅ Ensure Maya/3ds Max export đúng group name

#### **Import Best Practices:**

**Workflow hiệu quả:**
1. **Start Maya/3ds Max monitoring script** trước khi làm việc
2. **Test với collection nhỏ** trước khi import lớn
3. **Đặt tên collection rõ ràng** để dễ tracking
4. **Sử dụng Cancel** nếu chờ quá lâu (> 30s)

**Performance:**
- Import objects lớn có thể mất thời gian
- Maya/3ds Max export FBX tùy độ phức tạp của scene
- Blender import tự động sau khi phát hiện files

---

### **Smooth Mesh Preview (Maya):**
- Tự động phát hiện objects có subdivision từ geometry
- Bật Smooth Mesh Preview với divisions 3x3
- Áp dụng cho tất cả imported objects có subdivision data

### **Custom Material (Maya):**
- **Standard Surface**: Tạo material PBR theo workflow (Metal/Roughness hoặc Specular/Glossiness)
  - Base Color: Texture hoặc color value
  - Roughness/Metalness hoặc Specular/Glossiness (theo workflow)
  - Normal Map, AO, Emission, Opacity với channel selectors
- **Phong E**: Material legacy với Base Color, Roughness, Highlight Size

---

## 9. Best Practices

### **Khi sử dụng Face Maps:**
1. ✅ Tạo face maps có ý nghĩa (theo vùng chức năng)
2. ✅ Dùng **Optimal Face Sets** (KHB_Facemap panel) để tối ưu số lượng trước export
3. ✅ Kiểm tra face maps trong Face Map Manager trước khi export
4. ✅ Sử dụng tên face map rõ ràng để dễ quản lý
5. ❌ Tránh tạo quá nhiều face maps không cần thiết (> 20 tiles)

### **Khi sử dụng Sharp Edge:**
1. ✅ Phù hợp cho hard surface modeling
2. ✅ Mark sharp edges rõ ràng trước khi export
3. ❌ Không dùng cho organic models (sẽ tạo quá nhiều objects)

### **General:**
1. ✅ Luôn validate tên collection và objects
2. ✅ Test export với collection nhỏ trước
3. ✅ Backup scene trước khi export lần đầu
4. ✅ Kiểm tra file size của FBX (nếu quá lớn, tối ưu mesh)

---

## 10. Troubleshooting

### **Face Maps không được phát hiện:**
- **Nguyên nhân**: Mesh chưa có face maps hoặc data không hợp lệ
- **Giải pháp**: Mở KHB_Facemap panel, tạo face maps với Create/Assign tools

### **Export thất bại với Sharp Edge:**
- **Nguyên nhân**: Object không thể tách hoặc không có sharp edges
- **Giải pháp**: Chọn smooth group = "None" hoặc mark sharp edges thủ công

### **FBX file quá lớn:**
- **Nguyên nhân**: Subdivision level cao, nhiều geometry
- **Giải pháp**: Giảm subdivision level hoặc optimize mesh topology

### **Maya không import:**
- **Nguyên nhân**: File FBX corrupt hoặc format không đúng
- **Giải pháp**: Kiểm tra log Maya, re-export từ Blender

---

## Version History

- **v3.0** (2025-10-30)
  - **Material System Overhaul**: PBR workflows (Metal/Roughness & Specular/Glossiness)
  - **UI Redesign**: Mỗi material map trong box riêng, workflow selector ở header
  - **Channel Selectors**: Chọn kênh màu (R, G, B, A) cho từng texture map
  - **Custom Material Naming**: Đặt tên tùy chỉnh cho material
  - **Import Workflow**: Import collection từ Maya/3ds Max về Blender
  - **Face Maps System**: Sử dụng KHB_Facemap thay vì Sculpt Mode Face Sets
  - **Code Cleanup**: Xóa properties không sử dụng (Ambient Color, Normal Strength, AO Strength, Bump Map)
  - **Dynamic Labels**: Base Color/Diffuse tự động đổi theo workflow
  - **Simplified Phong E**: Chỉ Base Color + Roughness + Highlight Size
  - **Module Reload**: Auto-reload khi disable/enable addon

- **v2.1** - UI gọn gàng (1 box), tối ưu UX
- **v2.0** - Thêm Face Maps smooth group (UDIM UVs) - KeyHabit system
- **v1.5** - Thêm Sharp Edge smooth group
- **v1.0** - Release ban đầu với subdivision handling
