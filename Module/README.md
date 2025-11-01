# KeyHabit Sync Modules - Maya & 3ds Max

Scripts để đồng bộ hai chiều giữa Blender ↔ Maya/3ds Max.

---

## 📋 Tổng quan

### **Two-Way Sync:**

1. **Blender → Maya/3ds Max** (Export từ Blender)
   - Blender tạo `info.json` + `KHB_Sync.fbx`
   - Maya/3ds Max tự động import

2. **Maya/3ds Max → Blender** (Import vào Blender)
   - Blender tạo `request.json` với tên collection
   - Maya/3ds Max tự động export collection đó
   - Blender tự động import

---

## 🔧 Cài đặt & Sử dụng

### **Maya (Maya_Module.py)**

#### **Cài đặt:**

1. **Copy script vào Maya:**
   ```
   C:\Users\[User]\Documents\maya\scripts\Maya_Module.py
   ```

2. **Chạy script trong Maya Script Editor:**
   ```python
   import Maya_Module
   reload(Maya_Module)
   Maya_Module.toggle_sync_script()
   ```

3. **Tạo shelf button (optional):**
   - Mở Script Editor
   - Paste đoạn code trên
   - Middle-click drag → Shelf
   - Icon: 🔄

#### **Sử dụng:**

**Bật/Tắt Sync:**
```python
import Maya_Module
Maya_Module.toggle_sync_script()
```

- **Lần 1**: Bật sync → Hiện HUD "KeyHabit Sync" ở góc phải dưới
- **Lần 2**: Tắt sync → HUD biến mất

**Force Stop (khi cần):**
```python
Maya_Module.force_stop_sync()
```

**Khi sync đang chạy:**
- ✅ Tự động import khi Blender export (`info.json`)
- ✅ Tự động export khi Blender request (`request.json`)
- ✅ Sharp Edge processing cho export
- ✅ Smooth Mesh Preview cho import

---

### **3ds Max (Max_Module.ms)**

#### **Cài đặt:**

1. **Copy script vào 3ds Max:**
   ```
   C:\Users\[User]\AppData\Local\Autodesk\3dsMax\[Version]\ENU\scripts\Max_Module.ms
   ```

2. **Chạy script trong MaxScript Editor:**
   ```maxscript
   fileIn "C:\\Path\\To\\Max_Module.ms"
   ```

3. **Hoặc tạo MacroScript:**
   ```maxscript
   macroScript KeyHabitSync
   category:"KeyHabit"
   buttonText:"KHB Sync"
   (
       toggleSyncScript()
   )
   ```

#### **Sử dụng:**

**Bật/Tắt Sync:**
```maxscript
toggleSyncScript()
```

- **Lần 1**: Bật sync → MessageBox "KeyHabit Sync: ACTIVE"
- **Lần 2**: Tắt sync → MessageBox "KeyHabit Sync: STOPPED"

**Khi sync đang chạy:**
- ✅ Tự động import khi Blender export (`info.json`)
- ✅ Tự động export khi Blender request (`request.json`)
- ✅ Smoothing Groups → UDIM cho export
- ✅ TurboSmooth modifier cho import

---

## 🔄 Workflow Chi tiết

### **1. Blender → Maya/3ds Max (Normal Export)**

```
[Blender]
  User chọn collection → Bấm "Export Collection"
  ↓
  Tạo info.json + KHB_Sync.fbx
  ↓
[Maya/3ds Max]
  Script phát hiện info.json
  ↓
  Import FBX → Group objects → Apply smooth
  ↓
  Xóa info.json
  ✓ "Import OK"
```

### **2. Maya/3ds Max → Blender (Import Request)**

```
[Blender]
  User nhập tên group → Bấm "Import Collection"
  ↓
  Tạo request.json {"collection": "CharacterGroup"}
  ↓
[Maya/3ds Max]
  Script phát hiện request.json
  ↓
  Export collection với xử lý đặc biệt:
    - Maya: Sharp Edge processing
    - 3ds Max: Smoothing Groups → UDIM
  ↓
  Tạo info.json + KHB_Sync.fbx
  ↓
  Restore objects (join lại, restore UV)
  ↓
  Xóa request.json
  ✓ "Exported to Blender"
  ↓
[Blender]
  Script phát hiện info.json + FBX
  ↓
  Auto import vào collection
  ✓ "Import thành công"
```

---

## 🎯 Tính năng

### **Maya_Module.py:**

**Import (từ Blender):**
- ✅ Import FBX tự động
- ✅ Group objects theo collection name
- ✅ Smooth Mesh Preview (level 3)
- ✅ Custom material support (Phong)
- ✅ Cleanup old groups

**Export (về Blender):**
- ✅ Sharp Edge detection
- ✅ Split objects theo sharp edges
- ✅ Export FBX + info.json
- ✅ Restore objects (join lại)
- ✅ Format tên: `object_KBH_Path_001`

**Utilities:**
- ✅ HUD display (persistent)
- ✅ Toggle on/off
- ✅ Force stop
- ✅ Auto cleanup files

### **Max_Module.ms:**

**Import (từ Blender):**
- ✅ Import FBX tự động
- ✅ Group objects theo collection name
- ✅ TurboSmooth modifier (2 iterations)
- ✅ Cleanup old groups

**Export (về Blender):**
- ✅ Smoothing Groups → UDIM mapping
- ✅ Backup/Restore UV channels
- ✅ Export FBX + info.json
- ✅ 32 smoothing groups → UDIM 1001-1032
- ✅ UV channel 2 cho smooth data

**Utilities:**
- ✅ MessageBox notifications
- ✅ Toggle on/off
- ✅ Auto cleanup files
- ✅ Simple JSON parser

---

## 📁 File Structure

```
C:\KeyHabit_Sync\
├── info.json          # Blender export → Maya/Max import
├── request.json       # Blender request → Maya/Max export
└── KHB_Sync.fbx       # FBX file trao đổi
```

**info.json format:**
```json
[
  {"t": "2025-10-30 16:30:00"},
  {
    "collection": "CharacterMesh",
    "path": "C:/KeyHabit_Sync/KHB_Sync.fbx"
  }
]
```

**request.json format:**
```json
{
  "action": "export",
  "collection": "CharacterMesh",
  "timestamp": "2025-10-30 16:30:00"
}
```

---

## ⚙️ Troubleshooting

### **Maya:**

**Script không chạy:**
```python
# Check trạng thái
import Maya_Module
Maya_Module.get_script_running()  # True/False

# Clear state và restart
Maya_Module.force_stop_sync()
Maya_Module.toggle_sync_script()
```

**HUD không hiện:**
```python
# Test HUD
Maya_Module.test_hud()

# Clear HUD
Maya_Module.clear_sync_hud()
```

**Import không tự động:**
- ✅ Check folder `C:\KeyHabit_Sync` tồn tại
- ✅ Check script đang running
- ✅ Check console có lỗi không

### **3ds Max:**

**Script không hoạt động:**
```maxscript
-- Check trạng thái
logMessage "Check sync status"

-- Restart script
stopSyncScript()
startSyncScript()
```

**Export không có UDIM:**
- ✅ Check object là Editable Poly
- ✅ Check smoothing groups được set
- ✅ Check UV channel 2 có data

---

## 🚀 Best Practices

### **Workflow hiệu quả:**

1. **Bật script khi mở Maya/3ds Max:**
   - Add vào shelf/toolbar
   - Run script tự động khi startup

2. **Đặt tên rõ ràng:**
   - Collection/Group name: `Character_Mesh`, `Environment_Props`
   - Không dùng space, ký tự đặc biệt

3. **Test với scene nhỏ:**
   - Test sync với 1-2 objects trước
   - Verify smooth groups/sharp edges

4. **Monitor console:**
   - Check log messages để debug
   - Xem thời gian export/import

### **Performance:**

- ⚡ Import/Export tự động < 2 giây cho scene nhỏ
- ⏱️ Scene lớn có thể mất 5-10 giây
- 🔄 Sync check mỗi 1 giây (Maya idle event, Max callback)

---

## 📝 Version History

**v3.0** (2025-10-30)
- ✨ Two-way sync (Import + Export)
- 🔄 Maya Sharp Edge processing
- 🎨 3ds Max Smoothing Groups → UDIM
- ⏱️ Auto monitoring với timer
- 🧹 Auto cleanup và restore
- 📦 HUD display (Maya) và MessageBox (Max)

---

## 🔮 Future Features

Có thể mở rộng:
- 🎨 **Material sync** đầy đủ từ Maya/Max về Blender
- 📊 **Progress bar** cho large exports
- 🔔 **Audio notification** khi sync xong
- 🔄 **Batch export** nhiều collections
- 📝 **Log file** chi tiết cho debugging
- ⚡ **Optimized sharp edge detection** (Maya)
- 🎯 **Smart UV packing** (3ds Max)

---

## 📞 Support

Nếu gặp vấn đề:
1. Check console/listener cho error messages
2. Verify folder `C:\KeyHabit_Sync` permissions
3. Test với scene đơn giản
4. Force stop và restart script

**Log location:**
- Maya: Script Editor → History
- 3ds Max: MAXScript Listener

