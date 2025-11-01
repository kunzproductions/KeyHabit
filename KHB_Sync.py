# KHB_Sync.py - KeyHabit Sync Module
# Tính năng export collection sang FBX và tạo file info.json cho Maya sync

import bpy
import os
import json
import re
import bmesh
from datetime import datetime
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, BoolProperty, FloatVectorProperty, EnumProperty

# ================ VALIDATION FUNCTIONS ================

def validate_name(name):
    """
    Kiểm tra tên object/collection theo quy tắc:
    - Không chứa: . (chấm), khoảng trắng, / \ : ; , ? * " ' < > | = + % $ ^ & ~ # @ ( ) { }
    - Không bắt đầu bằng số
    - Không trùng keyword: group, object, default, scene, root
    - Độ dài tối đa 128 ký tự
    - Chỉ gồm: a-z, A-Z, 0-9, _
    """
    if not name:
        return False, "Tên không được để trống"
    
    # Kiểm tra độ dài
    if len(name) > 128:
        return False, "Tên quá dài (tối đa 128 ký tự)"
    
    # Kiểm tra ký tự không được phép
    forbidden_chars = r'[.\s/\\:;,?*"\'<>|=+%$^&~#@(){}]'
    if re.search(forbidden_chars, name):
        return False, "Tên chứa ký tự không được phép"
    
    # Kiểm tra bắt đầu bằng số
    if name[0].isdigit():
        return False, "Tên không được bắt đầu bằng số"
    
    # Kiểm tra keyword cấm
    forbidden_keywords = ['group', 'object', 'default', 'scene', 'root']
    if name.lower() in forbidden_keywords:
        return False, f"Tên '{name}' trùng với keyword cấm"
    
    # Kiểm tra chỉ chứa ký tự hợp lệ
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        return False, "Tên chỉ được chứa a-z, A-Z, 0-9, _"
    
    return True, "Tên hợp lệ"

def validate_collection(collection):
    """Kiểm tra collection và tất cả objects trong đó"""
    # Kiểm tra tên collection
    is_valid, message = validate_name(collection.name)
    if not is_valid:
        return False, f"Collection '{collection.name}': {message}"
    
    # Kiểm tra tất cả objects trong collection
    for obj in collection.objects:
        is_valid, message = validate_name(obj.name)
        if not is_valid:
            return False, f"Object '{obj.name}': {message}"
    
    return True, "Collection và objects hợp lệ"

# ================ SUBDIVISION HANDLING ================

def get_subdivision_objects(collection):
    """Lấy danh sách objects có subdivision modifier với level >= 1"""
    subdivision_objects = []
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'SUBSURF' and mod.levels >= 1:
                    subdivision_objects.append(obj.name)
                    break
    
    return subdivision_objects

def disable_subdivision_modifiers(collection):
    """Tắt tất cả subdivision modifiers trong collection"""
    disabled_count = 0
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'SUBSURF' and mod.levels >= 1:
                    mod.show_viewport = False
                    disabled_count += 1
    
    return disabled_count

def restore_subdivision_modifiers(collection):
    """Khôi phục tất cả subdivision modifiers trong collection"""
    restored_count = 0
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'SUBSURF' and mod.levels >= 1:
                    mod.show_viewport = True
                    restored_count += 1
    
    return restored_count

# ================ SHARP EDGE HANDLING ================

def has_sharp_edges(obj):
    """
    Kiểm tra xem object có sharp edges hay không
    """
    try:
        if obj.type != 'MESH':
            return False
        
        if not obj.data:
            return False
        
        # Kiểm tra mesh data
        mesh = obj.data
        sharp_edges = [edge for edge in mesh.edges if edge.use_edge_sharp]
        
        return len(sharp_edges) > 0
    except Exception:
        return False


def try_separate_object(obj):
    """
    Thử tách object thành các phần riêng biệt
    """
    if obj.type != 'MESH':
        return [obj]
    
    # Set active object
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    
    # Separate by loose parts
    bpy.ops.mesh.separate(type='LOOSE')
    
    # Lấy danh sách objects sau khi tách
    selected_objects = bpy.context.selected_objects.copy()
    
    return selected_objects

def add_edge_split_modifier(obj):
    """
    Thêm EdgeSplit modifier cho object
    """
    if obj.type != 'MESH':
        return False
    
    # Thêm EdgeSplit modifier
    edge_split_mod = obj.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
    edge_split_mod.use_edge_sharp = True
    
    return True

def rename_objects_with_path_format(objects, base_name):
    """
    Đổi tên objects theo format _KBH_Path_001, _002...
    """
    renamed_objects = []
    
    for i, obj in enumerate(objects):
        new_name = f"{base_name}_KBH_Path_{i+1:03d}"
        
        # Tìm tên không trùng
        counter = i + 1
        while bpy.data.objects.get(new_name):
            counter += 1
            new_name = f"{base_name}_KBH_Path_{counter:03d}"
        
        obj.name = new_name
        renamed_objects.append(obj)
    
    return renamed_objects

def process_object_sharp_edge(obj):
    """
    Xử lý sharp edge cho một object theo 3 trường hợp đơn giản
    """
    try:
        original_name = obj.name
        original_modifiers = [mod.name for mod in obj.modifiers]
        
        # Bước 1: Kiểm tra trạng thái ban đầu
        has_sharp = has_sharp_edges(obj)
        
        # Lưu thông tin để khôi phục
        restore_data = {
            'original_name': original_name,
            'original_modifiers': original_modifiers,
            'case_type': None,
            'separated_objects': [],
            'added_edge_split': False
        }
        
        # Bước 2: Xử lý theo trường hợp
        if not has_sharp:
            # Trường hợp 1: Không có sharp edge
            restore_data['case_type'] = 'case_1'
            return restore_data, []
        
        else:
            # Trường hợp 2 hoặc 3: Có sharp edge
            return process_sharp_edges_case(obj, restore_data)
    
    except Exception as e:
        print(f"Error in process_object_sharp_edge: {e}")
        # Return default case_1 if error
        return {
            'original_name': obj.name if obj else 'unknown',
            'original_modifiers': [],
            'case_type': 'case_1',
            'separated_objects': [],
            'added_edge_split': False
        }, []

def process_sharp_edges_case(obj, restore_data):
    """
    Xử lý trường hợp 2 hoặc 3: Có sharp edge
    """
    # Thử tách object
    separated_objects = try_separate_object(obj)
    
    if len(separated_objects) == 1:
        # Trường hợp 2: Không tách được
        add_edge_split_modifier(obj)
        restore_data['case_type'] = 'case_2'
        restore_data['added_edge_split'] = True
        return restore_data, []
    else:
        # Trường hợp 3: Tách được
        # Đổi tên và thêm EdgeSplit modifier
        renamed_objects = rename_objects_with_path_format(separated_objects, obj.name)
        
        for renamed_obj in renamed_objects:
            add_edge_split_modifier(renamed_obj)
        
        restore_data['case_type'] = 'case_3'
        restore_data['separated_objects'] = [obj.name for obj in renamed_objects]
        restore_data['added_edge_split'] = True
        
        return restore_data, renamed_objects


def apply_sharp_edge_to_collection(collection):
    """
    Xử lý sharp edge cho toàn bộ collection
    """
    sharp_edge_data = {}  # Lưu thông tin để khôi phục sau
    created_objects = []  # Danh sách objects mới được tạo
    
    try:
        for obj in collection.objects:
            if obj.type == 'MESH':
                try:
                    # Lưu tên gốc trước khi xử lý
                    original_obj_name = obj.name
                    
                    # Xử lý object
                    restore_data, new_objects = process_object_sharp_edge(obj)
                    
                    # Lưu thông tin với tên gốc
                    sharp_edge_data[original_obj_name] = restore_data
                    created_objects.extend(new_objects)
                except Exception as e:
                    print(f"Error processing object {obj.name}: {e}")
                    # Skip this object and continue
                    continue
    
    except Exception as e:
        print(f"Error in apply_sharp_edge_to_collection: {e}")
    
    return sharp_edge_data, created_objects


def restore_sharp_edge_collection(collection, sharp_edge_data, created_objects):
    """
    Khôi phục trạng thái ban đầu của collection sau khi export
    """
    # Khôi phục từng object
    for original_name, restore_data in sharp_edge_data.items():
        case_type = restore_data['case_type']
        
        if case_type == 'case_1':
            # Không cần khôi phục
            pass
        
        elif case_type == 'case_2':
            # Xóa EdgeSplit modifier
            obj = bpy.data.objects.get(original_name)
            if obj and 'EdgeSplit' in obj.modifiers:
                obj.modifiers.remove(obj.modifiers['EdgeSplit'])
        
        elif case_type == 'case_3':
            # Join objects + xóa EdgeSplit modifiers
            restore_separated_objects(original_name, restore_data['separated_objects'])
    
    # Xóa các objects mới được tạo (nếu còn sót lại)
    for obj in created_objects:
        if obj and obj.name in bpy.data.objects:
            # Kiểm tra xem object này có phải là object gốc đã được khôi phục không
            is_restored_original = False
            for original_name in sharp_edge_data.keys():
                if obj.name == original_name:
                    is_restored_original = True
                    break
            
            # Chỉ xóa nếu không phải là object gốc đã được khôi phục
            if not is_restored_original:
                bpy.data.objects.remove(obj, do_unlink=True)

def restore_separated_objects(original_name, separated_object_names):
    """
    Khôi phục các objects đã tách
    """
    # Tìm tất cả objects
    all_objects = []
    for obj_name in separated_object_names:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            # Xóa EdgeSplit modifier
            if 'EdgeSplit' in obj.modifiers:
                obj.modifiers.remove(obj.modifiers['EdgeSplit'])
            all_objects.append(obj)
    
    if len(all_objects) > 1:
        # Join tất cả objects
        bpy.ops.object.select_all(action='DESELECT')
        
        for obj in all_objects:
            obj.select_set(True)
        
        bpy.context.view_layer.objects.active = all_objects[0]
        bpy.ops.object.join()
        
        # Đổi tên về tên gốc
        all_objects[0].name = original_name
        
        # Đảm bảo object được thêm vào collection gốc
        # Tìm collection gốc chứa object
        for collection in bpy.data.collections:
            if original_name in collection.objects:
                # Object đã có trong collection, không cần làm gì
                break
        else:
            # Object không có trong collection nào, thêm vào scene collection
            if original_name not in bpy.context.scene.collection.objects:
                bpy.context.scene.collection.objects.link(bpy.data.objects[original_name])
    
    elif len(all_objects) == 1:
        # Chỉ có 1 object, đổi tên
        all_objects[0].name = original_name

# ================ FACE MAPS TO UDIM UV FUNCTIONS ================

def get_face_maps_from_object(obj):
    """Lấy face maps từ custom properties, trả về dict {face_map_id: [face_indices]}"""
    if not obj or obj.type != 'MESH':
        return {}
    
    mesh = obj.data
    
    # Kiểm tra có face map data không
    if 'facemap_data' not in mesh:
        return {}
    
    try:
        import json
        data = json.loads(mesh['facemap_data'])
        
        face_maps_dict = {}
        for i, group_data in enumerate(data.get('groups', [])):
            face_maps_dict[i] = list(group_data['faces'])
        
        return face_maps_dict
    except Exception as e:
        print(f"Error loading face map data: {e}")
        return {}

def cut_seams_for_face_maps(bm, face_maps_dict):
    """Cắt seam ở boundary edges giữa các face maps"""
    face_to_map = {}
    for face_map_id, face_indices in face_maps_dict.items():
        for face_idx in face_indices:
            face_to_map[face_idx] = face_map_id
    
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    seam_count = 0
    for edge in bm.edges:
        linked_faces = edge.link_faces
        
        if len(linked_faces) >= 2:
            face_maps = {face_to_map[f.index] for f in linked_faces if f.index in face_to_map}
            if len(face_maps) > 1:
                edge.seam = True
                seam_count += 1
        elif len(linked_faces) == 1:
            edge.seam = True
            seam_count += 1
    
    return seam_count

def scale_and_pack_uvs(bm, face_map, uv_layer_bm, margin):
    """Scale và pack UVs vào [0,1] với margin"""
    if not face_map:
        return
    
    bm.faces.ensure_lookup_table()
    
    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')
    
    for face_idx in face_map:
        if face_idx >= len(bm.faces):
            continue
        for loop in bm.faces[face_idx].loops:
            uv = loop[uv_layer_bm].uv
            min_u, max_u = min(min_u, uv.x), max(max_u, uv.x)
            min_v, max_v = min(min_v, uv.y), max(max_v, uv.y)
    
    width = max_u - min_u
    height = max_v - min_v
    
    if width == 0 or height == 0:
        return
    
    available_space = 1.0 - (2 * margin)
    scale = min(available_space / width, available_space / height)
    
    for face_idx in face_map:
        if face_idx >= len(bm.faces):
            continue
        for loop in bm.faces[face_idx].loops:
            uv = loop[uv_layer_bm].uv
            u = (uv.x - min_u) * scale + margin + (available_space - width * scale) / 2
            v = (uv.y - min_v) * scale + margin + (available_space - height * scale) / 2
            loop[uv_layer_bm].uv = (u, v)

def unwrap_face_map_to_udim(obj, bm, face_map, uv_layer_bm, udim_tile, margin):
    """Unwrap face map vào UDIM tile với padding"""
    tile_offset = udim_tile - 1001
    offset_x = tile_offset % 10
    offset_y = tile_offset // 10
    
    bm.faces.ensure_lookup_table()
    
    for item in [*bm.faces, *bm.edges, *bm.verts]:
        item.select = False
    
    faces_to_unwrap = []
    for face_idx in face_map:
        if face_idx < len(bm.faces):
            face = bm.faces[face_idx]
            face.select = True
            faces_to_unwrap.append(face)
            for edge in face.edges:
                edge.select = True
            for vert in face.verts:
                vert.select = True
    
    if not faces_to_unwrap:
        return
    
    bm.to_mesh(obj.data)
    obj.data.update()
    
    uv_layer_mesh = obj.data.uv_layers.get("KHB_smooth_group")
    if not uv_layer_mesh:
        return
    obj.data.uv_layers.active = uv_layer_mesh
    
    try:
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=margin)
    except Exception:
        try:
            bpy.ops.uv.smart_project(island_margin=margin)
        except:
            pass
    
    bm.clear()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    uv_layer_bm = bm.loops.layers.uv.get("KHB_smooth_group", bm.loops.layers.uv.active)
    
    scale_and_pack_uvs(bm, face_map, uv_layer_bm, margin)
    
    for face_idx in face_map:
        if face_idx >= len(bm.faces):
            continue
        for loop in bm.faces[face_idx].loops:
            uv = loop[uv_layer_bm].uv
            loop[uv_layer_bm].uv = (uv.x + offset_x, uv.y + offset_y)

def convert_face_maps_to_udim_uvs(obj, margin=0.01):
    """Chuyển face maps thành UDIM UVs"""
    if not obj or obj.type != 'MESH':
        return False, "Object không phải là mesh"
    
    face_maps_dict = get_face_maps_from_object(obj)
    if not face_maps_dict:
        return False, "Không tìm thấy face maps"
    
    uv_name = "KHB_smooth_group"
    
    existing_uv = obj.data.uv_layers.get(uv_name)
    if existing_uv:
        obj.data.uv_layers.remove(existing_uv)
    
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    cut_seams_for_face_maps(bm, face_maps_dict)
    
    bm.to_mesh(obj.data)
    obj.data.update()
    
    uv_layer_mesh = obj.data.uv_layers.new(name=uv_name)
    obj.data.uv_layers.active = uv_layer_mesh
    
    bm.clear()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    
    uv_layer_bm = bm.loops.layers.uv.get(uv_name) or bm.loops.layers.uv.new(uv_name)
    
    for idx, (face_map_id, face_indices) in enumerate(sorted(face_maps_dict.items())):
        udim_tile = 1001 + idx
        unwrap_face_map_to_udim(obj, bm, face_indices, uv_layer_bm, udim_tile, margin)
    
    bm.to_mesh(obj.data)
    bm.free()
    
    uv_layer = obj.data.uv_layers.get(uv_name)
    if uv_layer:
        obj.data.uv_layers.active = uv_layer
    
    return True, f"Created UV map with {len(face_maps_dict)} UDIM tiles"

def apply_face_maps_to_collection(collection, margin=0.01):
    """Áp dụng face maps to UDIM cho tất cả mesh objects trong collection"""
    processed_objects = []
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            success, message = convert_face_maps_to_udim_uvs(obj, margin)
            if success:
                processed_objects.append(obj.name)
    
    return processed_objects

def cleanup_face_maps_uvs(collection):
    """Xóa UV KHB_smooth_group sau khi export"""
    cleaned_count = 0
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            uv_layer = obj.data.uv_layers.get("KHB_smooth_group")
            if uv_layer:
                obj.data.uv_layers.remove(uv_layer)
                cleaned_count += 1
    
    return cleaned_count

# ================ TEXTURE HELPER FUNCTIONS ================

def build_texture_data(use_texture, color_value, texture_path):
    """
    Tạo data cho texture/color
    Returns: dict với 'type' ('color' hoặc 'texture') và giá trị tương ứng
    """
    if use_texture and texture_path:
        return {
            "type": "texture",
            "path": texture_path
        }
    else:
        return {
            "type": "color",
            "value": list(color_value) if hasattr(color_value, '__iter__') else color_value
        }

def validate_texture_path(path):
    """
    Kiểm tra file texture có tồn tại và đúng format không
    """
    if not path:
        return False, "Đường dẫn rỗng"
    
    # Kiểm tra extension
    valid_extensions = ['.png', '.psd', '.tga', '.jpg', '.jpeg', '.tif', '.tiff', '.exr']
    ext = os.path.splitext(path)[1].lower()
    
    if ext not in valid_extensions:
        return False, f"Format không hỗ trợ: {ext}"
    
    # Kiểm tra file tồn tại
    if not os.path.exists(path):
        return False, "File không tồn tại"
    
    return True, "OK"

# ================ EXPORT FUNCTIONS ================

def get_sync_folder_path():
    """Lấy đường dẫn folder sync (ổ C)"""
    return "C:\\KeyHabit_Sync"

def ensure_sync_folder():
    """Kiểm tra thư mục KeyHabit_Sync, nếu đã tồn tại thì xóa và tạo lại"""
    sync_path = get_sync_folder_path()
    
    # Xóa folder cũ nếu tồn tại
    if os.path.exists(sync_path):
        import shutil
        try:
            shutil.rmtree(sync_path)
        except Exception as e:
            print(f"Warning: Could not remove existing sync folder: {e}")
    
    # Tạo folder mới
    try:
        os.makedirs(sync_path)
    except Exception as e:
        raise Exception(f"Could not create sync folder: {e}")
    
    return sync_path

def export_fbx(collection, sync_path, custom_material=None):
    """Export toàn bộ objects collection sang FBX với tên cố định"""
    fbx_path = os.path.join(sync_path, "KHB_Sync.fbx")
    
    # Lưu selection hiện tại
    original_selection = bpy.context.selected_objects.copy()
    original_active = bpy.context.active_object
    
    try:
        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select toàn bộ objects trong collection
        for obj in collection.objects:
            obj.select_set(True)
        
        # Set active object (chọn object đầu tiên)
        if collection.objects:
            bpy.context.view_layer.objects.active = collection.objects[0]
        
        # Export FBX - chỉ export selection (toàn bộ objects collection)
        bpy.ops.export_scene.fbx(
            filepath=fbx_path,
            use_selection=True,  # Chỉ export objects đã select
            use_active_collection=False,  # Không dùng active collection
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            use_armature_deform_only=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            path_mode='AUTO',
            embed_textures=False,
            batch_mode='OFF',
            use_batch_own_dir=True,
            use_metadata=True
        )
        
        return True, fbx_path
        
    except Exception as e:
        return False, str(e)
    
    finally:
        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = original_active

def create_info_json(collection, fbx_path, subdivision_objects, custom_material=None):
    """Tạo file info.json theo format quy định (siêu gọn)"""
    info_data = []
    
    # Timestamp (phần tử đầu)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_data.append({"t": timestamp})
    
    # Collection info (object ghi tên collection, lệnh import FBX cố định)
    collection_info = {
        "collection": collection.name,
        "path": fbx_path  # Không cần escape, json.dumps() sẽ tự động xử lý
    }
    
    # Custom material info (nếu có)
    if custom_material and custom_material.get('enabled', False):
        mat_type = custom_material.get('type', 'STANDARD_SURFACE')
        mat_info = {
            "enabled": True,
            "type": mat_type
        }
        
        # Material Name (nếu có)
        material_name = custom_material.get('material_name', '').strip()
        if material_name:
            mat_info["name"] = material_name
        else:
            mat_info["name"] = collection.name  # Dùng tên collection nếu không có tên tùy chỉnh
        
        # Base Color (tất cả material đều có)
        mat_info["color"] = build_texture_data(
            custom_material.get('use_color_texture', False),
            custom_material.get('color', [0.58, 0.58, 0.58]),
            custom_material.get('color_texture_path', '')
        )
        
        # Emission (common property)
        mat_info["emission"] = build_texture_data(
            custom_material.get('use_emission_texture', False),
            custom_material.get('emission_color', [0.0, 0.0, 0.0]),
            custom_material.get('emission_texture_path', '')
        )
        mat_info["emission_strength"] = custom_material.get('emission_strength', 1.0)
        
        # PBR Maps - chỉ cho Standard Surface
        if mat_type == 'STANDARD_SURFACE':
            # AO Map
            if custom_material.get('use_ao_map', False):
                mat_info["ao_map"] = {
                    "enabled": True,
                    "path": custom_material.get('ao_map_path', ''),
                    "channel": custom_material.get('ao_channel', 'R')
                }
            
            # Normal Map
            if custom_material.get('use_normal_map', False):
                mat_info["normal_map"] = {
                    "enabled": True,
                    "path": custom_material.get('normal_map_path', '')
                }
            
            # Opacity Map
            if custom_material.get('use_opacity_map', False):
                mat_info["opacity_map"] = {
                    "enabled": True,
                    "path": custom_material.get('opacity_map_path', ''),
                    "channel": custom_material.get('opacity_channel', 'A')
                }
        
        # Thêm thuộc tính riêng cho từng loại material
        if mat_type == 'STANDARD_SURFACE':
            # PBR workflow
            pbr_workflow = custom_material.get('pbr_workflow', 'METAL_ROUGHNESS')
            mat_info["pbr_workflow"] = pbr_workflow
            
            # METAL/ROUGHNESS Workflow
            if pbr_workflow == 'METAL_ROUGHNESS':
                mat_info["metalness"] = build_texture_data(
                    custom_material.get('use_metalness_texture', False),
                    custom_material.get('metalness', 0.0),
                    custom_material.get('metalness_texture_path', '')
                )
                if custom_material.get('use_metalness_texture', False):
                    mat_info["metalness"]["channel"] = custom_material.get('metalness_channel', 'B')
                
                mat_info["roughness"] = build_texture_data(
                    custom_material.get('use_roughness_texture', False),
                    custom_material.get('roughness', 0.5),
                    custom_material.get('roughness_texture_path', '')
                )
                if custom_material.get('use_roughness_texture', False):
                    mat_info["roughness"]["channel"] = custom_material.get('roughness_channel', 'G')
            
            # SPECULAR/GLOSSINESS Workflow
            else:  # SPECULAR_GLOSSINESS
                mat_info["specular_color"] = build_texture_data(
                    custom_material.get('use_specular_texture', False),
                    custom_material.get('specular', [0.19, 0.19, 0.19]),
                    custom_material.get('specular_texture_path', '')
                )
                # Specular is RGB color, no channel needed
                
                mat_info["glossiness"] = build_texture_data(
                    custom_material.get('use_glossiness_texture', False),
                    custom_material.get('glossiness', 0.5),
                    custom_material.get('glossiness_texture_path', '')
                )
                if custom_material.get('use_glossiness_texture', False):
                    mat_info["glossiness"]["channel"] = custom_material.get('glossiness_channel', 'G')
            
            # Common properties
            mat_info["specular_weight"] = custom_material.get('specular_weight', 1.0)
            mat_info["ior"] = custom_material.get('ior', 1.5)
        
        elif mat_type == 'PHONG_E':
            # Legacy workflow - đơn giản, không dùng texture cho specular/roughness
            mat_info["specular_color"] = {
                "type": "color",
                "value": list(custom_material.get('specular', [0.19, 0.19, 0.19]))
            }
            mat_info["roughness"] = custom_material.get('phong_roughness', 0.5)
            mat_info["highlight_size"] = custom_material.get('highlight_size', 0.3)
        
        collection_info["custom_material"] = mat_info
    
    info_data.append(collection_info)
    
    # Subdivision actions (lệnh sdiv cho mỗi object subdivision)
    for obj_name in subdivision_objects:
        info_data.append({
            "a": "sdiv",
            "n": obj_name
        })
    
    return info_data

def save_info_json(info_data, sync_path):
    """Lưu file info.json"""
    json_path = os.path.join(sync_path, "info.json")
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(info_data, f, indent=2, ensure_ascii=False)
        return True, json_path
    except Exception as e:
        return False, str(e)

# ================ IMPORT FUNCTIONS ================

def create_import_request(collection_name, sync_path):
    """
    Tạo file request.json để yêu cầu Maya/3ds Max export collection
    """
    request_data = {
        "action": "export",
        "collection": collection_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    request_path = os.path.join(sync_path, "request.json")
    
    try:
        with open(request_path, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)
        return True, request_path
    except Exception as e:
        return False, str(e)

def check_import_ready(sync_path):
    """
    Kiểm tra xem Maya/3ds Max đã export xong chưa (có file info.json + FBX)
    """
    info_path = os.path.join(sync_path, "info.json")
    fbx_path = os.path.join(sync_path, "KHB_Sync.fbx")
    
    # Kiểm tra cả 2 file tồn tại
    if os.path.exists(info_path) and os.path.exists(fbx_path):
        return True, info_path, fbx_path
    
    return False, None, None

def import_fbx_file(fbx_path, collection_name, smooth_objects=None):
    """
    Import FBX file vào Blender và tạo collection mới
    smooth_objects: list of {"name": "object_name", "level": 2}
    """
    try:
        # Import FBX
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        # Get imported objects (những objects vừa được select sau import)
        imported_objects = bpy.context.selected_objects.copy()
        
        if not imported_objects:
            return False, "Không có object nào được import"
        
        # Filter: CHỈ LẤY MESH OBJECTS, BỎ QUA EMPTY (từ Maya group)
        mesh_objects = []
        empty_objects = []
        
        for obj in imported_objects:
            if obj.type == 'MESH':
                mesh_objects.append(obj)
            elif obj.type == 'EMPTY':
                empty_objects.append(obj)
        
        if not mesh_objects:
            return False, "Không có mesh object nào được import"
        
        # Tạo collection mới hoặc lấy collection đã tồn tại
        if collection_name in bpy.data.collections:
            collection = bpy.data.collections[collection_name]
        else:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)
        
        # Di chuyển CHỈ MESH OBJECTS vào collection
        for obj in mesh_objects:
            # Unparent (remove parent nếu có - thường là Empty từ Maya)
            if obj.parent:
                matrix_copy = obj.matrix_world.copy()
                obj.parent = None
                obj.matrix_world = matrix_copy
            
            # Unlink từ tất cả collections hiện tại
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            
            # Link vào collection mới
            if obj.name not in collection.objects:
                collection.objects.link(obj)
        
        # Xóa Empty objects (Maya groups)
        for empty in empty_objects:
            try:
                bpy.data.objects.remove(empty, do_unlink=True)
            except:
                pass

        # ========== JOIN các phần _KHB_Path_### về object gốc ==========
        import re as _re

        def _strip_khb_path(name: str):
            m = _re.match(r"^(.*)_KHB_Path_\d{3}$", name)
            return m.group(1) if m else None

        base_to_parts = {}
        for obj in list(collection.objects):
            if obj.type != 'MESH':
                continue
            base = _strip_khb_path(obj.name)
            if base:
                base_to_parts.setdefault(base, []).append(obj)

        for base, parts in base_to_parts.items():
            # Lọc chỉ các phần vẫn tồn tại và còn thuộc một collection
            valid_parts = []
            for p in parts:
                try:
                    if (p and p.type == 'MESH' and p.name in bpy.data.objects and
                        getattr(p, 'users_collection', None) and len(p.users_collection) > 0):
                        valid_parts.append(p)
                except Exception:
                    continue

            if len(valid_parts) <= 1:
                continue
            # Join parts an toàn
            try:
                bpy.ops.object.select_all(action='DESELECT')
                for p in valid_parts:
                    try:
                        p.select_set(True)
                    except Exception:
                        pass
                # Đặt active là phần đầu tiên hợp lệ
                try:
                    bpy.context.view_layer.objects.active = valid_parts[0]
                except Exception:
                    pass
                bpy.ops.object.join()
                # Sau join, đối tượng còn lại là valid_parts[0]
                try:
                    valid_parts[0].name = base
                except Exception:
                    pass
                # Làm mới view layer trước khi thao tác tiếp
                try:
                    bpy.context.view_layer.update()
                except Exception:
                    pass
            except Exception:
                pass

        # Lấy lại danh sách objects trong collection sau khi join
        collection_objects_snapshot = list(collection.objects)

        # ========== Xóa custom normals và tắt auto smooth ==========
        def _clear_custom_normals(obj):
            try:
                if obj.type == 'MESH' and obj.data:
                    me = obj.data
                    if hasattr(me, 'has_custom_normals') and me.has_custom_normals:
                        me.normals_split_custom_set(None)
                    if hasattr(me, 'use_auto_smooth'):
                        me.use_auto_smooth = False
            except Exception:
                pass

        for obj in collection_objects_snapshot:
            try:
                _clear_custom_normals(obj)
            except Exception:
                pass

        # ========== Chuẩn hóa vật liệu: bỏ hậu tố .### về tên gốc nếu tồn tại ==========
        def _base_mat_name(name: str):
            m = _re.match(r"^(.*)\.(\d{3})$", name)
            return m.group(1) if m else name

        # Dùng snapshot sau join để tránh tham chiếu Object đã bị xóa
        for obj in collection_objects_snapshot:
            if obj.type != 'MESH':
                continue
            if not obj.data or not hasattr(obj.data, 'materials'):
                continue
            try:
                for i, slot in enumerate(obj.material_slots):
                    mat = slot.material
                    if not mat:
                        continue
                    base_name = _base_mat_name(mat.name)
                    # Nếu tồn tại material gốc (không hậu tố), dùng lại để tránh tạo bản sao .###
                    base_mat = bpy.data.materials.get(base_name)
                    if base_mat and base_mat != mat:
                        slot.material = base_mat
            except Exception:
                continue
        
        # Apply Subdivision Surface modifier cho smooth objects
        subdivision_count = 0
        if smooth_objects:
            for obj in mesh_objects:
                # Check nếu object trong danh sách smooth
                for smooth_info in smooth_objects:
                    # Match tên (có thể có suffix .001, .002)
                    obj_base_name = obj.name.split('.')[0]
                    smooth_name = smooth_info.get("name", "")
                    
                    if obj_base_name == smooth_name or obj.name == smooth_name:
                        # Tạo Subdivision Surface modifier
                        subsurf = obj.modifiers.new(name="Subdivision", type='SUBSURF')
                        
                        # Maya smooth level mapping:
                        # Maya level 1 = Blender viewport 1, render 1
                        # Maya level 2 = Blender viewport 1, render 2
                        # Maya level 3 = Blender viewport 2, render 2
                        maya_level = smooth_info.get("level", 2)
                        
                        if maya_level == 1:
                            subsurf.levels = 1
                            subsurf.render_levels = 1
                        elif maya_level == 2:
                            subsurf.levels = 1
                            subsurf.render_levels = 2
                        else:  # level 3
                            subsurf.levels = 2
                            subsurf.render_levels = 2
                        
                        subdivision_count += 1
                        break
        
        result_msg = f"Import thành công {len(mesh_objects)} mesh object(s)"
        if subdivision_count > 0:
            result_msg += f" ({subdivision_count} subdivision)"
        
        return True, result_msg + f" vào collection '{collection_name}'"
    
    except Exception as e:
        return False, f"Import thất bại: {str(e)}"

def cleanup_import_files(sync_path):
    """
    Xóa các file import (request.json, info.json, FBX) sau khi import xong
    """
    files_to_remove = ["request.json", "info.json", "KHB_Sync.fbx"]
    removed_count = 0
    
    for filename in files_to_remove:
        file_path = os.path.join(sync_path, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                removed_count += 1
            except Exception as e:
                print(f"Warning: Could not remove {filename}: {e}")
    
    return removed_count

# ================ PROPERTIES ================

class KHB_SyncProperties(PropertyGroup):
    """Properties cho sync settings"""
    
    selected_collection: StringProperty(
        name="Collection",
        description="Collection để export",
        default=""
    )
    
    use_custom_material: BoolProperty(
        name="Custom Material",
        description="Sử dụng material tùy chỉnh",
        default=False
    )
    
    # ========== BASE COLOR ==========
    material_color: FloatVectorProperty(
        name="Color",
        description="Màu diffuse/albedo",
        subtype='COLOR',
        default=(0.58, 0.58, 0.58),
        min=0.0,
        max=1.0
    )
    
    use_color_texture: BoolProperty(
        name="Use Texture",
        description="Sử dụng texture thay vì màu solid",
        default=False
    )
    
    color_texture_path: StringProperty(
        name="Texture Path",
        description="Đường dẫn đến file texture (png, psd, tga)",
        default="",
        subtype='FILE_PATH'
    )
    
    # ========== SPECULAR ==========
    material_specular: FloatVectorProperty(
        name="Specular",
        description="Màu specular",
        subtype='COLOR',
        default=(0.19, 0.19, 0.19),
        min=0.0,
        max=1.0
    )
    
    use_specular_texture: BoolProperty(
        name="Use Texture",
        description="Sử dụng texture cho specular",
        default=False
    )
    
    specular_texture_path: StringProperty(
        name="Specular Texture",
        description="Đường dẫn đến file texture specular",
        default="",
        subtype='FILE_PATH'
    )
    
    # ========== EMISSION ==========
    mat_emission_color: FloatVectorProperty(
        name="Emission",
        description="Màu phát sáng",
        subtype='COLOR',
        default=(0.0, 0.0, 0.0),
        min=0.0,
        max=1.0
    )
    
    mat_emission_strength: bpy.props.FloatProperty(
        name="Emission Strength",
        description="Cường độ phát sáng",
        default=1.0,
        min=0.0,
        max=10.0
    )
    
    use_emission_texture: BoolProperty(
        name="Use Texture",
        description="Sử dụng texture cho emission",
        default=False
    )
    
    emission_texture_path: StringProperty(
        name="Emission Texture",
        description="Đường dẫn đến file texture emission",
        default="",
        subtype='FILE_PATH'
    )
    
    # ========== NORMAL MAPPING ==========
    use_normal_map: BoolProperty(
        name="Use Normal Map",
        description="Sử dụng normal mapping (DirectX hoặc OpenGL)",
        default=False
    )
    
    normal_map_path: StringProperty(
        name="Normal Map",
        description="Đường dẫn đến file normal map",
        default="",
        subtype='FILE_PATH'
    )
    
    # ========== AMBIENT OCCLUSION ==========
    use_ao_map: BoolProperty(
        name="Use AO Map",
        description="Sử dụng Ambient Occlusion map",
        default=False
    )
    
    ao_map_path: StringProperty(
        name="AO Map",
        description="Đường dẫn đến file AO map",
        default="",
        subtype='FILE_PATH'
    )
    
    ao_channel: EnumProperty(
        name="AO Channel",
        description="Kênh màu cho AO",
        items=[
            ('R', "R (Red)", "Red channel"),
            ('G', "G (Green)", "Green channel"),
            ('B', "B (Blue)", "Blue channel"),
            ('A', "A (Alpha)", "Alpha channel"),
        ],
        default='R'
    )
    
    # ========== OPACITY ==========
    use_opacity_map: BoolProperty(
        name="Use Opacity Map",
        description="Sử dụng opacity/alpha map",
        default=False
    )
    
    opacity_map_path: StringProperty(
        name="Opacity Map",
        description="Đường dẫn đến file opacity map",
        default="",
        subtype='FILE_PATH'
    )
    
    opacity_channel: EnumProperty(
        name="Opacity Channel",
        description="Kênh màu cho Opacity",
        items=[
            ('A', "A (Alpha)", "Alpha channel"),
            ('R', "R (Red)", "Red channel"),
            ('G', "G (Green)", "Green channel"),
            ('B', "B (Blue)", "Blue channel"),
        ],
        default='A'
    )
    
    material_type: EnumProperty(
        name="Material Type",
        description="Loại material Maya",
        items=[
            ('STANDARD_SURFACE', "Standard Surface", "PBR workflow (Arnold) - Cho Substance Painter", 'SHADING_RENDERED', 0),
            ('PHONG_E', "Phong E", "Legacy workflow - Maya Phong E shader", 'SHADING_SOLID', 1),
        ],
        default='STANDARD_SURFACE'
    )
    
    material_name: StringProperty(
        name="Material Name",
        description="Tên tùy chỉnh cho material (để trống sẽ dùng tên collection)",
        default="",
        maxlen=128
    )
    
    # ========== STANDARD SURFACE Properties ==========
    # Workflow selection
    pbr_workflow: EnumProperty(
        name="PBR Workflow",
        description="Chọn workflow PBR",
        items=[
            ('METAL_ROUGHNESS', "Metal/Roughness", "Metal/Roughness workflow (Substance Painter, Arnold)", 'BRUSH_DATA', 0),
            ('SPECULAR_GLOSSINESS', "Specular/Glossiness", "Specular/Glossiness workflow (Unity, Unreal)", 'SMOOTHCURVE', 1),
        ],
        default='METAL_ROUGHNESS'
    )
    
    mat_metalness: bpy.props.FloatProperty(
        name="Metalness",
        description="Độ kim loại (0=Non-metal, 1=Metal)",
        default=0.0,
        min=0.0,
        max=1.0
    )
    
    mat_roughness: bpy.props.FloatProperty(
        name="Roughness",
        description="Độ nhám bề mặt (0=Smooth, 1=Rough)",
        default=0.5,
        min=0.0,
        max=1.0
    )
    
    mat_glossiness: bpy.props.FloatProperty(
        name="Glossiness",
        description="Độ bóng bề mặt (0=Rough, 1=Smooth)",
        default=0.5,
        min=0.0,
        max=1.0
    )
    
    mat_specular_weight: bpy.props.FloatProperty(
        name="Specular Weight",
        description="Cường độ specular",
        default=1.0,
        min=0.0,
        max=1.0
    )
    
    mat_ior: bpy.props.FloatProperty(
        name="IOR",
        description="Index of Refraction",
        default=1.5,
        min=1.0,
        max=3.0
    )
    
    # ========== PHONG E Properties ==========
    mat_phong_roughness: bpy.props.FloatProperty(
        name="Roughness",
        description="Độ nhám (Phong E)",
        default=0.5,
        min=0.0,
        max=1.0
    )
    
    mat_highlight_size: bpy.props.FloatProperty(
        name="Highlight Size",
        description="Kích thước highlight",
        default=0.3,
        min=0.0,
        max=1.0
    )
    
    # ========== METALNESS (for Standard Surface) ==========
    use_metalness_texture: BoolProperty(
        name="Use Metalness Texture",
        description="Sử dụng texture cho metalness",
        default=False
    )
    
    metalness_texture_path: StringProperty(
        name="Metalness Texture",
        description="Đường dẫn đến file texture metalness",
        default="",
        subtype='FILE_PATH'
    )
    
    metalness_channel: EnumProperty(
        name="Metalness Channel",
        description="Kênh màu cho Metalness",
        items=[
            ('R', "R (Red)", "Red channel"),
            ('G', "G (Green)", "Green channel"),
            ('B', "B (Blue)", "Blue channel"),
            ('A', "A (Alpha)", "Alpha channel"),
        ],
        default='B'
    )
    
    # ========== ROUGHNESS TEXTURE ==========
    use_roughness_texture: BoolProperty(
        name="Use Roughness Texture",
        description="Sử dụng texture cho roughness",
        default=False
    )
    
    roughness_texture_path: StringProperty(
        name="Roughness Texture",
        description="Đường dẫn đến file texture roughness",
        default="",
        subtype='FILE_PATH'
    )
    
    roughness_channel: EnumProperty(
        name="Roughness Channel",
        description="Kênh màu cho Roughness",
        items=[
            ('R', "R (Red)", "Red channel"),
            ('G', "G (Green)", "Green channel"),
            ('B', "B (Blue)", "Blue channel"),
            ('A', "A (Alpha)", "Alpha channel"),
        ],
        default='G'
    )
    
    # ========== GLOSSINESS TEXTURE ==========
    use_glossiness_texture: BoolProperty(
        name="Use Glossiness Texture",
        description="Sử dụng texture cho glossiness",
        default=False
    )
    
    glossiness_texture_path: StringProperty(
        name="Glossiness Texture",
        description="Đường dẫn đến file texture glossiness",
        default="",
        subtype='FILE_PATH'
    )
    
    glossiness_channel: EnumProperty(
        name="Glossiness Channel",
        description="Kênh màu cho Glossiness",
        items=[
            ('R', "R (Red)", "Red channel"),
            ('G', "G (Green)", "Green channel"),
            ('B', "B (Blue)", "Blue channel"),
            ('A', "A (Alpha)", "Alpha channel"),
        ],
        default='G'
    )
    
    smooth_group_type: EnumProperty(
        name="Smooth Group",
        description="Chọn phương pháp smooth group",
        items=[
            ('NONE', "None", "Không áp dụng smooth group", 'BLANK1', 0),
            ('SHARP_EDGE', "Sharp Edge", "Tách object theo sharp edges và thêm EdgeSplit modifier", 'MOD_EDGESPLIT', 1),
            ('FACE_MAPS', "Face Maps", "Convert face maps thành UDIM UVs", 'FACE_MAPS', 2),
        ],
        default='NONE'
    )
    
    # ========== MODE SELECTION ==========
    sync_mode: EnumProperty(
        name="Sync Mode",
        description="Chọn chế độ Import hoặc Export",
        items=[
            ('EXPORT', "Export", "Export collection từ Blender sang Maya/3ds Max", 'EXPORT', 0),
            ('IMPORT', "Import", "Import collection từ Maya/3ds Max về Blender", 'IMPORT', 1),
        ],
        default='EXPORT'
    )
    
    # ========== IMPORT PROPERTIES ==========
    import_collection_name: StringProperty(
        name="Collection Name",
        description="Tên collection/group từ Maya/3ds Max để import",
        default="",
        maxlen=128
    )
    
    is_waiting_import: BoolProperty(
        name="Waiting for Import",
        description="Đang chờ Maya/3ds Max export",
        default=False
    )

# ================ OPERATORS ================

class KHB_OT_sync_collection(Operator):
    """Operator chính để sync collection"""
    bl_idname = "keyhabit.sync_collection"
    bl_label = "Sync Collection"
    bl_description = "Export collection sang FBX và tạo file info.json cho Maya sync"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.khb_sync_props
        
        # Kiểm tra collection đã chọn
        if not props.selected_collection:
            self.report({'ERROR'}, "Vui lòng chọn collection để sync")
            return {'CANCELLED'}
        
        collection = bpy.data.collections.get(props.selected_collection)
        if not collection:
            self.report({'ERROR'}, f"Collection '{props.selected_collection}' không tồn tại")
            return {'CANCELLED'}
        
        # Validate collection và objects
        is_valid, message = validate_collection(collection)
        if not is_valid:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
        
        # Kiểm tra và tạo lại folder sync (xóa cũ nếu có)
        try:
            sync_path = ensure_sync_folder()
        except Exception as e:
            self.report({'ERROR'}, f"Không thể tạo folder sync: {e}")
            return {'CANCELLED'}
        
        # Lấy danh sách subdivision objects trước khi tắt
        subdivision_objects = get_subdivision_objects(collection)
        
        # Tắt subdivision modifiers
        disabled_count = disable_subdivision_modifiers(collection)
        
        # Xử lý Smooth Group theo loại đã chọn
        sharp_edge_data = None
        created_objects = []
        face_maps_objects = []
        
        if props.smooth_group_type == 'SHARP_EDGE':
            try:
                sharp_edge_data, created_objects = apply_sharp_edge_to_collection(collection)
            except Exception as e:
                self.report({'ERROR'}, f"Sharp Edge processing failed: {e}")
                return {'CANCELLED'}
        
        elif props.smooth_group_type == 'FACE_MAPS':
            try:
                face_maps_objects = apply_face_maps_to_collection(collection)
                if not face_maps_objects:
                    self.report({'WARNING'}, "Không có object nào có face maps")
            except Exception as e:
                self.report({'ERROR'}, f"Face Maps processing failed: {e}")
                return {'CANCELLED'}
        
        try:
            # Export FBX
            success, result = export_fbx(collection, sync_path)
            if not success:
                self.report({'ERROR'}, f"Export FBX thất bại: {result}")
                return {'CANCELLED'}
            
            fbx_path = result
            
            # Tạo custom material info
            custom_material = None
            if props.use_custom_material:
                custom_material = {
                    'enabled': True,
                    'type': props.material_type,
                    'material_name': props.material_name,
                    
                    # Base Color
                    'color': list(props.material_color),
                    'use_color_texture': props.use_color_texture,
                    'color_texture_path': props.color_texture_path,
                    
                    # Specular
                    'specular': list(props.material_specular),
                    'use_specular_texture': props.use_specular_texture,
                    'specular_texture_path': props.specular_texture_path,
                    
                    # Emission
                    'emission_color': list(props.mat_emission_color),
                    'emission_strength': props.mat_emission_strength,
                    'use_emission_texture': props.use_emission_texture,
                    'emission_texture_path': props.emission_texture_path,
                    
                    # Normal Map
                    'use_normal_map': props.use_normal_map,
                    'normal_map_path': props.normal_map_path,
                    
                    # AO Map
                    'use_ao_map': props.use_ao_map,
                    'ao_map_path': props.ao_map_path,
                    'ao_channel': props.ao_channel,
                    
                    # Opacity
                    'use_opacity_map': props.use_opacity_map,
                    'opacity_map_path': props.opacity_map_path,
                    'opacity_channel': props.opacity_channel,
                    
                    # Standard Surface - PBR Workflow
                    'pbr_workflow': props.pbr_workflow,
                    'metalness': props.mat_metalness,
                    'use_metalness_texture': props.use_metalness_texture,
                    'metalness_texture_path': props.metalness_texture_path,
                    'metalness_channel': props.metalness_channel,
                    
                    # Roughness
                    'roughness': props.mat_roughness,
                    'use_roughness_texture': props.use_roughness_texture,
                    'roughness_texture_path': props.roughness_texture_path,
                    'roughness_channel': props.roughness_channel,
                    
                    # Glossiness
                    'glossiness': props.mat_glossiness,
                    'use_glossiness_texture': props.use_glossiness_texture,
                    'glossiness_texture_path': props.glossiness_texture_path,
                    'glossiness_channel': props.glossiness_channel,
                    
                    'specular_weight': props.mat_specular_weight,
                    'ior': props.mat_ior,
                    
                    # Phong E
                    'phong_roughness': props.mat_phong_roughness,
                    'highlight_size': props.mat_highlight_size
                }
            
            # Tạo info.json
            info_data = create_info_json(collection, fbx_path, subdivision_objects, custom_material)
            
            # Lưu info.json
            success, result = save_info_json(info_data, sync_path)
            if not success:
                self.report({'ERROR'}, f"Lưu info.json thất bại: {result}")
                return {'CANCELLED'}
            
            # Báo cáo thành công
            message_parts = [f"Sync thành công: {collection.name}"]
            message_parts.append("Folder sync đã được tạo lại")
            message_parts.append("FBX: KHB_Sync.fbx")
            message_parts.append("Info: info.json")
            if disabled_count > 0:
                message_parts.append(f"Tắt {disabled_count} subdivision modifier(s)")
            if subdivision_objects:
                message_parts.append(f"{len(subdivision_objects)} object(s) có subdivision")
            if props.use_custom_material:
                message_parts.append("Custom material enabled")
            if props.smooth_group_type == 'SHARP_EDGE' and created_objects:
                message_parts.append(f"Sharp Edge: {len(created_objects)} object(s) tách")
            if props.smooth_group_type == 'FACE_MAPS' and face_maps_objects:
                message_parts.append(f"Face Maps: {len(face_maps_objects)} object(s) processed")
            
            self.report({'INFO'}, " | ".join(message_parts))
            
        finally:
            # Khôi phục subdivision modifiers
            if disabled_count > 0:
                restore_subdivision_modifiers(collection)
            
            # Khôi phục Sharp Edge
            if props.smooth_group_type == 'SHARP_EDGE' and sharp_edge_data and created_objects:
                try:
                    restore_sharp_edge_collection(collection, sharp_edge_data, created_objects)
                except Exception as e:
                    print(f"Warning: Could not restore Sharp Edge state: {e}")
            
            # Cleanup Face Maps UVs
            if props.smooth_group_type == 'FACE_MAPS' and face_maps_objects:
                try:
                    cleaned_count = cleanup_face_maps_uvs(collection)
                    if cleaned_count > 0:
                        print(f"Cleaned up {cleaned_count} UV maps")
                except Exception as e:
                    print(f"Warning: Could not cleanup Face Maps UVs: {e}")
        
        return {'FINISHED'}

class KHB_OT_import_collection(Operator):
    """Operator để bắt đầu import collection từ Maya/3ds Max"""
    bl_idname = "keyhabit.import_collection"
    bl_label = "Import Collection"
    bl_description = "Request Maya/3ds Max export collection và import vào Blender"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        props = context.scene.khb_sync_props
        
        # Validate tên collection
        if not props.import_collection_name:
            self.report({'ERROR'}, "Vui lòng nhập tên collection/group để import")
            return {'CANCELLED'}
        
        is_valid, message = validate_name(props.import_collection_name)
        if not is_valid:
            self.report({'ERROR'}, f"Tên collection không hợp lệ: {message}")
            return {'CANCELLED'}
        
        # Ensure sync folder exists và dọn dẹp
        try:
            sync_path = ensure_sync_folder()
        except Exception as e:
            self.report({'ERROR'}, f"Không thể tạo folder sync: {e}")
            return {'CANCELLED'}
        
        # Tạo file request.json
        success, result = create_import_request(props.import_collection_name, sync_path)
        if not success:
            self.report({'ERROR'}, f"Tạo request thất bại: {result}")
            return {'CANCELLED'}
        
        # Set waiting state
        props.is_waiting_import = True
        
        # Start modal operator để monitor
        bpy.ops.keyhabit.monitor_import('INVOKE_DEFAULT')
        
        self.report({'INFO'}, f"Đang chờ Maya/3ds Max export '{props.import_collection_name}'...")
        return {'FINISHED'}

class KHB_OT_monitor_import(Operator):
    """Modal operator để monitor folder và tự động import khi ready"""
    bl_idname = "keyhabit.monitor_import"
    bl_label = "Monitor Import"
    bl_description = "Monitor folder sync và import FBX khi ready"
    
    _timer = None
    _check_interval = 1.0  # Check mỗi 1 giây
    
    def modal(self, context, event):
        props = context.scene.khb_sync_props
        
        # Nếu user cancel
        if not props.is_waiting_import:
            self.cancel(context)
            return {'CANCELLED'}
        
        # Check theo interval
        if event.type == 'TIMER':
            sync_path = get_sync_folder_path()
            
            # Kiểm tra folder sync có tồn tại không
            if not os.path.exists(sync_path):
                props.is_waiting_import = False
                self.report({'ERROR'}, "Folder sync không tồn tại")
                self.cancel(context)
                return {'CANCELLED'}
            
            # Kiểm tra file ready
            ready, info_path, fbx_path = check_import_ready(sync_path)
            
            if ready:
                # Đọc info.json để lấy smooth_objects
                smooth_objects = None
                try:
                    with open(info_path, 'r', encoding='utf-8') as f:
                        info_data = json.load(f)
                        if len(info_data) >= 2:
                            smooth_objects = info_data[1].get("smooth_objects", None)
                except:
                    pass
                
                # Import FBX với smooth info
                success, message = import_fbx_file(fbx_path, props.import_collection_name, smooth_objects)
                
                if success:
                    # Cleanup files
                    cleanup_import_files(sync_path)
                    
                    # Reset state
                    props.is_waiting_import = False
                    
                    self.report({'INFO'}, message)
                    self.cancel(context)
                    return {'FINISHED'}
                else:
                    # Import failed
                    props.is_waiting_import = False
                    self.report({'ERROR'}, message)
                    self.cancel(context)
                    return {'CANCELLED'}
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        self._timer = wm.event_timer_add(self._check_interval, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def cancel(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None

class KHB_OT_cancel_import(Operator):
    """Operator để cancel import"""
    bl_idname = "keyhabit.cancel_import"
    bl_label = "Cancel Import"
    bl_description = "Hủy việc chờ import"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        props = context.scene.khb_sync_props
        props.is_waiting_import = False
        
        # Cleanup request file nếu có
        sync_path = get_sync_folder_path()
        if os.path.exists(sync_path):
            request_path = os.path.join(sync_path, "request.json")
            if os.path.exists(request_path):
                try:
                    os.remove(request_path)
                except Exception as e:
                    print(f"Warning: Could not remove request.json: {e}")
        
        self.report({'INFO'}, "Đã hủy import")
        return {'FINISHED'}

# ================ PANEL ================

class KHB_PT_sync_panel(Panel):
    """Panel UI cho sync"""
    bl_label = "Sync Collection"
    bl_idname = "KHB_PT_sync_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "KeyHabit"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.khb_sync_props
        
        # ========== MODE SELECTOR ==========
        box = layout.box()
        row = box.row(align=True)
        row.prop(props, "sync_mode", expand=True)
        
        layout.separator()
        
        # ========== IMPORT MODE ==========
        if props.sync_mode == 'IMPORT':
            import_box = layout.box()
            import_box.label(text="Import from Maya/3ds Max", icon='IMPORT')
            
            if props.is_waiting_import:
                # Waiting state
                col = import_box.column(align=True)
                row = col.row()
                row.label(text=f"⏱ Waiting for '{props.import_collection_name}'...", icon='TIME')
                
                row = col.row()
                row.scale_y = 1.5
                row.operator("keyhabit.cancel_import", text="Cancel", icon='CANCEL')
            else:
                # Normal state
                row = import_box.row()
                row.prop(props, "import_collection_name", text="Group Name")
                
                # Validation
                group_name = props.import_collection_name.strip()
                is_valid_name = False
                validation_message = ""
                
                if group_name:
                    is_valid_name, validation_message = validate_name(group_name)
                    
                    if not is_valid_name:
                        # Show validation error
                        row = import_box.row()
                        row.alert = True
                        row.label(text=f"✗ {validation_message}", icon='ERROR')
                
                # Import button
                row = import_box.row()
                row.scale_y = 2.0
                row.enabled = bool(group_name) and is_valid_name
                row.operator("keyhabit.import_collection", text="Import Collection", icon='IMPORT')
        
        # ========== EXPORT MODE ==========
        else:  # EXPORT mode
            # ========== COLLECTION SELECTION ==========
            box = layout.box()
            box.label(text="Collection", icon='OUTLINER_COLLECTION')
            
            row = box.row()
            row.prop_search(props, "selected_collection", bpy.data, "collections", text="")
            
            if not props.selected_collection:
                box.label(text="⚠ Chọn collection để export", icon='ERROR')
                return
            
            collection = bpy.data.collections.get(props.selected_collection)
            if not collection:
                box.label(text="⚠ Collection không tồn tại", icon='ERROR')
                return
            
            # Validation info
            is_valid, message = validate_collection(collection)
            if not is_valid:
                box.label(text=f"✗ {message}", icon='ERROR')
                return
            
            # Object count với icon
            mesh_count = sum(1 for obj in collection.objects if obj.type == 'MESH')
            split = box.split(factor=0.5)
            col = split.column()
            col.label(text=f"Objects: {len(collection.objects)}")
            col = split.column()
            col.label(text=f"Meshes: {mesh_count}")
            
            # ========== SMOOTH GROUP ==========
            layout.separator()
            box = layout.box()
            box.label(text="Smooth Group", icon='MOD_SMOOTH')
            
            row = box.row()
            row.prop(props, "smooth_group_type", text="")
            
            # ========== CUSTOM MATERIAL ==========
            layout.separator()
            box = layout.box()
            
            row = box.row()
            row.prop(props, "use_custom_material", text="Custom Material", icon='MATERIAL')
            
            if props.use_custom_material:
                box.separator()
                
                # Material Type
                row = box.row()
                row.prop(props, "material_type", text="Type")
                
                # Material Name (chỉ cho Standard Surface)
                if props.material_type == 'STANDARD_SURFACE':
                    row = box.row()
                    row.prop(props, "material_name", text="Name", icon='COPY_ID')
                    
                    # PBR Workflow Selector
                    row = box.row()
                    row.label(text="PBR Workflow:")
                    row = box.row()
                    row.prop(props, "pbr_workflow", expand=True)
                
                box.separator()
                
                # ===== STANDARD SURFACE (PBR Workflow) =====
                if props.material_type == 'STANDARD_SURFACE':
                    
                    # === 1. Base Color / Diffuse ===
                    mapbox = box.box()
                    col = mapbox.column(align=True)
                    row = col.row(align=True)
                    if props.pbr_workflow == 'SPECULAR_GLOSSINESS':
                        row.label(text="Diffuse", icon='COLOR')
                    else:
                        row.label(text="Base Color", icon='COLOR')
                    row.prop(props, "use_color_texture", text="", icon='TEXTURE')
                    if props.use_color_texture:
                        col.prop(props, "color_texture_path", text="")
                    else:
                        col.prop(props, "material_color", text="")
                
                    # === 2. Normal ===
                    mapbox = box.box()
                    col = mapbox.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Normal", icon='NORMALS_FACE')
                    row.prop(props, "use_normal_map", text="", icon='TEXTURE')
                    if props.use_normal_map:
                        col.prop(props, "normal_map_path", text="")
                
                    # === 3. Roughness/Glossiness (theo workflow) ===
                    if props.pbr_workflow == 'METAL_ROUGHNESS':
                        mapbox = box.box()
                        col = mapbox.column(align=True)
                        row = col.row(align=True)
                        row.label(text="Roughness", icon='SHADING_TEXTURE')
                        row.prop(props, "use_roughness_texture", text="", icon='TEXTURE')
                        if props.use_roughness_texture:
                            row.prop(props, "roughness_channel", text="")
                            col.prop(props, "roughness_texture_path", text="")
                        else:
                            col.prop(props, "mat_roughness", text="", slider=True)
                    else:  # SPECULAR_GLOSSINESS
                        mapbox = box.box()
                        col = mapbox.column(align=True)
                        row = col.row(align=True)
                        row.label(text="Glossiness", icon='SHADING_TEXTURE')
                        row.prop(props, "use_glossiness_texture", text="", icon='TEXTURE')
                        if props.use_glossiness_texture:
                            row.prop(props, "glossiness_channel", text="")
                            col.prop(props, "glossiness_texture_path", text="")
                        else:
                            col.prop(props, "mat_glossiness", text="", slider=True)
                
                    # === 4. Metalness/Specular (theo workflow) ===
                    if props.pbr_workflow == 'METAL_ROUGHNESS':
                        mapbox = box.box()
                        col = mapbox.column(align=True)
                        row = col.row(align=True)
                        row.label(text="Metalness", icon='SHADING_RENDERED')
                        row.prop(props, "use_metalness_texture", text="", icon='TEXTURE')
                        if props.use_metalness_texture:
                            row.prop(props, "metalness_channel", text="")
                            col.prop(props, "metalness_texture_path", text="")
                        else:
                            col.prop(props, "mat_metalness", text="", slider=True)
                    else:  # SPECULAR_GLOSSINESS
                        mapbox = box.box()
                        col = mapbox.column(align=True)
                        row = col.row(align=True)
                        row.label(text="Specular", icon='SHADING_RENDERED')
                        row.prop(props, "use_specular_texture", text="", icon='TEXTURE')
                        if props.use_specular_texture:
                            col.prop(props, "specular_texture_path", text="")
                        else:
                            col.prop(props, "material_specular", text="")
                
                    # === 5. Emission ===
                    mapbox = box.box()
                    col = mapbox.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Emission", icon='LIGHT')
                    row.prop(props, "use_emission_texture", text="", icon='TEXTURE')
                    if props.use_emission_texture:
                        col.prop(props, "emission_texture_path", text="")
                    else:
                        col.prop(props, "mat_emission_color", text="")
                
                    # === 6. Ambient Occlusion ===
                    mapbox = box.box()
                    col = mapbox.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Ambient Occlusion", icon='SHADING_SOLID')
                    row.prop(props, "use_ao_map", text="", icon='TEXTURE')
                    if props.use_ao_map:
                        row.prop(props, "ao_channel", text="")
                        col.prop(props, "ao_map_path", text="")
                
                    # === 7. Transparency (Opacity) ===
                    mapbox = box.box()
                    col = mapbox.column(align=True)
                    row = col.row(align=True)
                    row.label(text="Transparency", icon='IMAGE_ALPHA')
                    row.prop(props, "use_opacity_map", text="", icon='TEXTURE')
                    if props.use_opacity_map:
                        row.prop(props, "opacity_channel", text="")
                        col.prop(props, "opacity_map_path", text="")
            
            # ===== PHONG E (Legacy - Đơn giản) =====
            elif props.material_type == 'PHONG_E':
                # ===== BASE COLOR - Chỉ color picker =====
                col = box.column(align=True)
                col.label(text="Base Color:", icon='COLOR')
                col.prop(props, "material_color", text="")
                
                # ===== LEGACY PROPERTIES =====
                box.separator()
                col = box.column(align=True)
                col.label(text="Phong E (Legacy):", icon='SHADING_SOLID')
                col.prop(props, "mat_phong_roughness", text="Roughness", slider=True)
                col.prop(props, "mat_highlight_size", text="Highlight Size", slider=True)
        
            # ========== SYNC BUTTON ==========
            layout.separator()
            row = layout.row()
            row.scale_y = 2.0
            row.operator("keyhabit.sync_collection", text="Export Collection", icon='EXPORT')

# ================ REGISTRATION ================

classes = (
    KHB_SyncProperties,
    KHB_OT_sync_collection,
    KHB_OT_import_collection,
    KHB_OT_monitor_import,
    KHB_OT_cancel_import,
    KHB_PT_sync_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register properties
    bpy.types.Scene.khb_sync_props = bpy.props.PointerProperty(type=KHB_SyncProperties)

def unregister():
    # Unregister properties
    try:
        if hasattr(bpy.types.Scene, 'khb_sync_props'):
            del bpy.types.Scene.khb_sync_props
    except Exception as e:
        print(f"Error removing khb_sync_props: {e}")
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls}: {e}")

if __name__ == "__main__":
    register()
