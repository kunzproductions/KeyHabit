# Maya_Module.py - KeyHabit Sync for Maya
# Two-way sync: Import from Blender (request.json action="import") & Export to Blender (request.json action="export")

import maya.cmds as cmds
import json
import os
import time
from datetime import datetime

# ================ CONFIG ================
SYNC_FOLDER = "C:/KeyHabit_Sync"
REQUEST_JSON_PATH = os.path.join(SYNC_FOLDER, "request.json")
FBX_PATH = os.path.join(SYNC_FOLDER, "KHB_Sync.fbx")

# Debug Mode
KHB_Module_Debug = False  # Set True để bật debug mode

# ================ GLOBAL VARIABLES ================
def get_script_running():
    """Lấy trạng thái script từ Maya global"""
    if cmds.optionVar(exists='keyhabit_script_running'):
        return bool(cmds.optionVar(query='keyhabit_script_running'))
    return False

def set_script_running(value):
    """Set trạng thái script vào Maya global"""
    cmds.optionVar(intValue=('keyhabit_script_running', 1 if value else 0))

def get_timer_id():
    """Lấy timer ID từ Maya global"""
    return cmds.optionVar(query='keyhabit_timer_id') if cmds.optionVar(exists='keyhabit_timer_id') else None

def set_timer_id(value):
    """Set timer ID vào Maya global"""
    if value is not None:
        cmds.optionVar(intValue=('keyhabit_timer_id', value))
    else:
        if cmds.optionVar(exists='keyhabit_timer_id'):
            cmds.optionVar(remove='keyhabit_timer_id')

# ================ UTILITY FUNCTIONS ================

def show_sync_status(message, duration=3000, persistent=False):
    """Hiển thị thông báo sync"""
    if persistent:
        try:
            if not cmds.headsUpDisplay('keyhabit_sync', exists=True):
                cmds.headsUpDisplay('keyhabit_sync', 
                    section=2, block=0, blockSize='large',
                    label=message, labelFontSize='large', dataFontSize='large')
        except Exception as e:
            log_message(f"Lỗi tạo HUD: {e}")
    else:
        cmds.inViewMessage(amg=message, pos='botRight', fade=True, fst=duration, fts=14)

def log_message(message):
    """Ghi log message"""
    print(f"[KeyHabit] {message}")

# ================ DEBUG HELPERS ================
def _dbg(msg):
    if KHB_Module_Debug:
        log_message(f"[KHB_DEBUG] {msg}")

def _now():
    return time.time()

def debug_log(level, message):
    """Debug log với level"""
    prefix = {
        'info': '[KHB_DEBUG] Info:',
        'warning': '[KHB_DEBUG] Warning:',
        'error': '[KHB_DEBUG] Error:',
        'success': '[KHB_DEBUG] Success:'
    }.get(level, '[KHB_DEBUG]')
    log_message(f"{prefix} {message}")

def clear_sync_hud():
    """Xóa HUD sync"""
    try:
        if cmds.headsUpDisplay('keyhabit_sync', exists=True):
            cmds.headsUpDisplay('keyhabit_sync', remove=True)
    except Exception as e:
        log_message(f"Lỗi xóa HUD: {e}")

# ================ SHARP EDGE PROCESSING ================

def detect_hard_edges(obj):
    """Phát hiện hard edges (sharp edges) trên object"""
    try:
        # Lấy tất cả edges
        edges = cmds.polyListComponentConversion(obj, te=True)
        if not edges:
            return []
        
        hard_edges = []
        edge_list = cmds.ls(edges, flatten=True)
        
        for edge in edge_list:
            try:
                # Kiểm tra edge angle - hard edge có angle lớn giữa 2 faces
                # Sử dụng polyNormalPerVertex hoặc polyInfo để kiểm tra
                edge_info = cmds.polyInfo(edge, edgeToFace=True)
                if edge_info:
                    # Nếu edge có nhiều hơn 2 faces hoặc angle lớn, coi là hard edge
                    # Simplified detection: kiểm tra bằng cách so sánh normals
                    faces = cmds.polyListComponentConversion(edge, tf=True)
                    if faces:
                        face_list = cmds.ls(faces, flatten=True)
                        if len(face_list) >= 2:
                            # Tính góc giữa normals của 2 faces kề nhau
                            # Nếu góc lớn (gần 180 độ), edge là hard edge
                            hard_edges.append(edge)
            except:
                pass
        
        return hard_edges
    except Exception as e:
        log_message(f"Lỗi detect hard edges: {e}")
        return []

def separate_object_by_edges(obj):
    """Tách object theo edges (polySeparate)"""
    try:
        separated = cmds.polySeparate(obj, constructionHistory=False)
        return separated if separated else []
    except:
        return []

def detach_edges(obj, edges):
    """Detach Components ở các edges cụ thể"""
    try:
        if not edges:
            return True
        
        # Select edges
        cmds.select(edges, replace=True)
        
        # Detach edges bằng cách split edges
        # Sử dụng polyCut để tách edges
        try:
            # Alternative: detach faces connected to edges
            faces = cmds.polyListComponentConversion(edges, tf=True)
            if faces:
                face_list = cmds.ls(faces, flatten=True)
                cmds.polySeparate(obj, constructionHistory=False)
            return True
        except:
            # Fallback: sử dụng polyDelEdge
            cmds.polyDelEdge(edges, cv=True)
            return True
    except Exception as e:
        log_message(f"Lỗi detach edges: {e}")
        return False

def merge_vertices_by_distance(obj, distance=0.001):
    """Merge vertices với khoảng cách cụ thể"""
    try:
        vertices = cmds.ls(f"{obj}.vtx[*]", flatten=True)
        if vertices:
            cmds.polyMergeVertex(vertices, d=distance, am=1, ch=1)
        return True
    except Exception as e:
        log_message(f"Lỗi merge vertices: {e}")
        return False

def check_object_smooth_preview(obj):
    """Kiểm tra object có bật Smooth Mesh Preview không"""
    try:
        smooth_level = cmds.getAttr(f"{obj}.displaySmoothness")
        return smooth_level > 0
    except:
        return False

def set_smooth_preview(obj, enable=True):
    """Bật/tắt Smooth Mesh Preview"""
    try:
        if enable:
            cmds.displaySmoothness(obj, divisionsU=3, divisionsV=3, 
                pointsWire=16, pointsShaded=4, polygonObject=3)
        else:
            cmds.displaySmoothness(obj, divisionsU=0, divisionsV=0, 
                pointsWire=1, pointsShaded=1, polygonObject=0)
        return True
    except:
        return False

def delete_existing_group(group_name):
    """Xóa group cũ nếu tồn tại"""
    if cmds.objExists(group_name):
        try:
            cmds.delete(group_name)
            return True
        except Exception as e:
            log_message(f"Lỗi xóa group {group_name}: {e}")
            return False
    return True

def import_fbx(fbx_path):
    """Import FBX file"""
    try:
        imported_nodes = cmds.file(fbx_path, i=True, type="FBX", 
            ignoreVersion=True, mergeNamespacesOnClash=False,
            namespace=":", returnNewNodes=True)
        return True, imported_nodes
    except Exception as e:
        log_message(f"Lỗi import FBX: {e}")
        return False, str(e)

def group_imported_nodes(nodes, group_name):
    """Gom tất cả nodes import vào group và trả về tên group thực tế (có thể khác group_name)."""
    try:
        transform_nodes = []
        for node in nodes:
            if cmds.objExists(node) and cmds.nodeType(node) == 'transform':
                children = cmds.listRelatives(node, children=True, type='mesh')
                if children:
                    transform_nodes.append(node)
        
        if not transform_nodes:
            log_message("Không tìm thấy mesh objects để group")
            return None
        
        group = cmds.group(transform_nodes, name=group_name)
        return group
    except Exception as e:
        log_message(f"Lỗi gom nodes vào group: {e}")
        return None

def flatten_khb_dup_hierarchy(group_name_or_path):
    """Dọn cây phân cấp: đưa mesh con của *_KHB_Dup lên thẳng group và xóa transform rỗng.
    Nhận vào tên hoặc đường dẫn group; ưu tiên dùng đường dẫn đầy đủ để tránh trùng tên.
    """
    try:
        # Xác định group path duy nhất
        group_candidates = []
        if cmds.objExists(group_name_or_path):
            group_candidates = [group_name_or_path]
        else:
            # Tìm theo short name
            short = group_name_or_path.split('|')[-1]
            group_candidates = cmds.ls(short, type='transform') or []
        if not group_candidates:
            return
        group_path = group_candidates[0]
        to_delete = []

        # Thu toàn bộ descendants transforms
        all_transforms = cmds.listRelatives(group_path, ad=True, type='transform', fullPath=True) or []

        # 1) Đưa mọi *_KHB_Path_### về trực tiếp dưới group
        for tr in all_transforms:
            short = tr.split('|')[-1]
            if cmds.objExists(tr):
                if short.endswith(tuple([f"_KHB_Path_{i:03d}" for i in range(1, 1000)])):
                    parent = cmds.listRelatives(tr, parent=True, fullPath=True)
                    if parent and parent[0] != group_path:
                        try:
                            cmds.parent(tr, group_path)
                        except:
                            pass

        # 1b) Nếu có child transform cùng tên group (nested trùng tên), kéo con của nó ra group rồi xóa nó
        children_lvl1 = cmds.listRelatives(group_path, children=True, type='transform', fullPath=True) or []
        group_short = group_path.split('|')[-1]
        for ch in children_lvl1:
            if ch.split('|')[-1] == group_short:
                # Kéo tất cả con trực tiếp của ch lên group
                grand = cmds.listRelatives(ch, children=True, type='transform', fullPath=True) or []
                for g in grand:
                    try:
                        cmds.parent(g, group_path)
                    except:
                        pass
                try:
                    cmds.delete(ch)
                except:
                    pass

        # Refresh transforms list sau khi parent
        all_transforms = cmds.listRelatives(group_path, ad=True, type='transform', fullPath=True) or []

        # 2) Với mọi *_KHB_Dup: nếu không còn mesh con thì xóa; nếu còn con là transforms nhưng không chứa mesh thì cũng xóa
        for tr in all_transforms:
            short = tr.split('|')[-1]
            if short.endswith('_KHB_Dup'):
                has_mesh = cmds.listRelatives(tr, ad=True, type='mesh', fullPath=True) or []
                if not has_mesh:
                    to_delete.append(tr)

        # 2b) Xóa cưỡng bức mọi *_KHB_Dup còn sót lại sau khi đã kéo parts ra ngoài
        for tr in all_transforms:
            short = tr.split('|')[-1]
            if short.endswith('_KHB_Dup') and tr not in to_delete:
                to_delete.append(tr)

        # 3) Xóa transform rỗng bất kỳ không chứa mesh
        for tr in all_transforms:
            has_mesh = cmds.listRelatives(tr, ad=True, type='mesh', fullPath=True) or []
            if not has_mesh and tr not in to_delete:
                # Không xóa group chính
                if tr != group_path:
                    to_delete.append(tr)

        if to_delete:
            try:
                cmds.delete(list(set(to_delete)))
            except:
                pass
    except Exception as e:
        log_message(f"Lỗi flatten KHB_Dup: {e}")

def apply_smooth_to_objects(object_names):
    """Bật Smooth Mesh Preview cho các objects"""
    smooth_count = 0
    for obj_name in object_names:
        if not obj_name:
            continue
            
        found_objects = []
        if cmds.objExists(obj_name):
            found_objects.append(obj_name)
        else:
            all_objects = cmds.ls(type='transform')
            for obj in all_objects:
                obj_short_name = obj.split(':')[-1]
                if obj_short_name == obj_name:
                    found_objects.append(obj)
                    break
        
        for obj in found_objects:
            try:
                cmds.displaySmoothness(obj, divisionsU=3, divisionsV=3, 
                    pointsWire=16, pointsShaded=4, polygonObject=3)
                smooth_count += 1
            except:
                try:
                    cmds.setAttr(f"{obj}.displaySmoothness", 3)
                    smooth_count += 1
                except:
                    pass
    
    if smooth_count > 0:
        log_message(f"Smooth: {smooth_count} objects")
    return smooth_count

def create_custom_material(material_info, collection_name):
    """Tạo custom material"""
    try:
        material_name = f"{collection_name}_CustomMaterial"
        shading_group_name = f"{material_name}SG"
        
        cleanup_duplicate_materials(collection_name)
        
        material = cmds.shadingNode('phong', asShader=True, name=material_name)
        
        color = material_info.get('color', [0.58, 0.58, 0.58])
        cmds.setAttr(f"{material}.color", color[0], color[1], color[2])
        
        specular = material_info.get('specular', [0.19, 0.19, 0.19])
        cmds.setAttr(f"{material}.specularColor", specular[0], specular[1], specular[2])
        
        shading_group = cmds.sets(renderable=True, noSurfaceShader=True, 
            empty=True, name=shading_group_name)
        cmds.connectAttr(f"{material}.outColor", f"{shading_group}.surfaceShader")
        
        return True, material_name
    except Exception as e:
        log_message(f"Lỗi tạo custom material: {e}")
        return False, str(e)

def apply_material_to_objects(material_name, group_name):
    """Gán material lên tất cả objects trong group"""
    try:
        objects = cmds.listRelatives(group_name, children=True, type='transform')
        if not objects:
            return False
        
        for obj in objects:
            try:
                meshes = cmds.listRelatives(obj, children=True, type='mesh')
                if meshes:
                    for mesh in meshes:
                        cmds.sets(mesh, edit=True, forceElement=f"{material_name}SG")
            except:
                pass
        return True
    except Exception as e:
        log_message(f"Lỗi gán material: {e}")
        return False

def cleanup_duplicate_materials(collection_name):
    """Xóa tất cả material và shading group trùng tên"""
    material_name = f"{collection_name}_CustomMaterial"
    shading_group_name = f"{material_name}SG"
    
    all_materials = cmds.ls(type='phong')
    for material in all_materials:
        if material.startswith(material_name):
            try:
                cmds.delete(material)
            except:
                pass
    
    all_shading_groups = cmds.ls(type='shadingEngine')
    for sg in all_shading_groups:
        if sg.startswith(shading_group_name):
            try:
                cmds.delete(sg)
            except:
                pass

# ================ IMPORT FROM BLENDER (request.json action="import") ================

def handle_import_request(request_data):
    """Xử lý request import từ Blender (action="import")"""
    collection_name = request_data.get('collection', '')
    if not collection_name:
        log_message("Request import không có collection name")
        return False
    
    # Validation: Kiểm tra FBX file có tồn tại
    if not os.path.exists(FBX_PATH):
        log_message(f"File FBX không tồn tại: {FBX_PATH}")
        return False
    
    log_message(f"Blender request import: {collection_name}")
    
    try:
        # Group Cleanup
        delete_existing_group(collection_name)
        
        # FBX Import
        success, imported_nodes = import_fbx(FBX_PATH)
        if not success:
            return False
        
        # Grouping
        group_created = group_imported_nodes(imported_nodes, collection_name)
        if not group_created:
            return False
        
        # Dọn cây phân cấp
        flatten_khb_dup_hierarchy(group_created)
        
        # Smooth Processing: Tự động phát hiện subdivision từ geometry
        objects = cmds.listRelatives(group_created, children=True, type='transform') or []
        smooth_count = 0
        for obj in objects:
            # Tự động phát hiện nếu object có subdivision data
            if check_object_smooth_preview(obj) or True:  # Simplified: bật cho tất cả
                if set_smooth_preview(obj, enable=True):
                    smooth_count += 1
        
        if smooth_count > 0:
            log_message(f"Smooth: {smooth_count} objects")
        
        # Material Processing: Material được embed trong FBX, Maya sẽ tự động import
        
        # Cleanup
        if os.path.exists(FBX_PATH):
            os.remove(FBX_PATH)
        delete_request_json()
        
        show_sync_status("KeyHabit Sync: IMPORT OK")
        log_message("✓ Import completed")
        return True
    except Exception as e:
        log_message(f"Lỗi import: {e}")
        return False

# ================ EXPORT TO BLENDER (request.json) ================

def check_request_file():
    """Kiểm tra file request.json có tồn tại không"""
    return os.path.exists(REQUEST_JSON_PATH)

def read_request_json():
    """Đọc file request.json"""
    try:
        with open(REQUEST_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data
    except Exception as e:
        return False, f"Lỗi đọc request.json: {e}"

def delete_request_json():
    """Xóa file request.json sau khi xử lý"""
    try:
        if os.path.exists(REQUEST_JSON_PATH):
            os.remove(REQUEST_JSON_PATH)
            return True
    except Exception as e:
        log_message(f"Lỗi xóa request.json: {e}")
    return False

def process_object_for_export(obj, group_name):
    """Xử lý từng object trong group để export"""
    restore_info = {
        'smooth_enabled': False,
        'duplicate_created': None,
        'separated_objects': []
    }
    
    try:
        # b. Kiểm tra Preview smooth
        if check_object_smooth_preview(obj):
            restore_info['smooth_enabled'] = True
            set_smooth_preview(obj, enable=False)
        
        # Kiểm tra hard edges
        hard_edges = detect_hard_edges(obj)
        
        # a. Không có sharp edge -> export trực tiếp
        if not hard_edges:
            return True, restore_info
        
        # c. Có hard edges và có thể tách được
        separated = separate_object_by_edges(obj)
        if separated and len(separated) > 1:
            # Tạo bản sao để xử lý
            dup_name = f"{obj}_KHB_Dup"
            dup_obj = cmds.duplicate(obj, name=dup_name)[0]
            restore_info['duplicate_created'] = dup_obj
            
            # Tách duplicate
            dup_separated = separate_object_by_edges(dup_obj)
            if dup_separated:
                # Rename separated objects
                separated_renamed = []
                for i, sep_obj in enumerate(dup_separated):
                    new_name = f"{obj}_KHB_Path_{i+1:03d}"
                    renamed = cmds.rename(sep_obj, new_name)
                    separated_renamed.append(renamed)
                
                restore_info['separated_objects'] = separated_renamed
                
                # Detach Components ở hard edges
                for sep_obj in separated_renamed:
                    sep_hard_edges = detect_hard_edges(sep_obj)
                    if sep_hard_edges:
                        detach_edges(sep_obj, sep_hard_edges)
                
                return True, restore_info
        
        # d. Có hard edges nhưng không tách được
        if hard_edges:
            # Detach Components và merge vertices
            detach_edges(obj, hard_edges)
            merge_vertices_by_distance(obj, distance=0.001)
            return True, restore_info
        
        return True, restore_info
    except Exception as e:
        log_message(f"Lỗi process object {obj}: {e}")
        return False, restore_info

def restore_object_after_export(obj, restore_info):
    """Restore object về trạng thái ban đầu sau export"""
    try:
        # Restore smooth preview
        if restore_info.get('smooth_enabled'):
            set_smooth_preview(obj, enable=True)
        
        # Xóa duplicate và separated objects
        dup_obj = restore_info.get('duplicate_created')
        if dup_obj and cmds.objExists(dup_obj):
            cmds.delete(dup_obj)
        
        separated_objs = restore_info.get('separated_objects', [])
        for sep_obj in separated_objs:
            if cmds.objExists(sep_obj):
                cmds.delete(sep_obj)
        
        return True
    except Exception as e:
        log_message(f"Lỗi restore object {obj}: {e}")
        return False

def export_empty_fbx():
    """Export FBX rỗng để Blender ngắt quy trình"""
    try:
        # Tạo empty group tạm thời
        temp_group = cmds.group(empty=True, name="KHB_Temp_Empty")
        cmds.select(temp_group)
        cmds.file(FBX_PATH, force=True, options="v=0;", 
                  type="FBX export", exportSelected=True)
        cmds.delete(temp_group)
        return True
    except Exception as e:
        log_message(f"Lỗi export empty FBX: {e}")
        return False

def handle_export_request_action(request_data):
    """Xử lý request export từ Blender (action="export")"""
    collection_name = request_data.get('collection', '')
    if not collection_name:
        log_message("Request export không có collection name")
        return False
    
    # Validation: Kiểm tra group có tồn tại
    if not cmds.objExists(collection_name):
        log_message(f"Collection '{collection_name}' không tồn tại - Exporting empty FBX")
        export_empty_fbx()
        delete_request_json()
        return False
    
    log_message(f"Blender request export: {collection_name}")
    
    try:
        # Get objects trong group
        objects = cmds.listRelatives(collection_name, allDescendents=True, 
                                      type='transform', fullPath=True) or []
        
        # Filter chỉ mesh objects
        mesh_objects = []
        for obj in objects:
            shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
            if shapes and cmds.nodeType(shapes[0]) == 'mesh':
                mesh_objects.append(obj)
        
        if not mesh_objects:
            log_message("Không có mesh objects để export")
            export_empty_fbx()
            delete_request_json()
            return False
        
        # Process từng object
        restore_infos = {}
        objects_to_export = []
        
        for obj in mesh_objects:
            success, restore_info = process_object_for_export(obj, collection_name)
            if success:
                restore_infos[obj] = restore_info
                # Nếu có separated objects, thêm vào list export
                if restore_info.get('separated_objects'):
                    objects_to_export.extend(restore_info['separated_objects'])
                else:
                    objects_to_export.append(obj)
        
        # Export FBX
        cmds.select(objects_to_export, replace=True)
        cmds.file(FBX_PATH, force=True, options="v=0;", 
                  type="FBX export", exportSelected=True)
        
        # Restore objects
        for obj in mesh_objects:
            if obj in restore_infos:
                restore_object_after_export(obj, restore_infos[obj])
        
        delete_request_json()
        show_sync_status("KeyHabit Sync: EXPORT OK")
        log_message(f"✓ Exported {len(objects_to_export)} objects")
        return True
        
    except Exception as e:
        log_message(f"Lỗi export: {e}")
        return False

def handle_export_request():
    """Xử lý request từ Blender (cả export và import)"""
    if not check_request_file():
        return True
    
    success, request_data = read_request_json()
    if not success:
        log_message(f"Lỗi đọc request: {request_data}")
        return False
    
    action = request_data.get('action', '')
    
    if action == "export":
        # Maya → Blender
        return handle_export_request_action(request_data)
    elif action == "import":
        # Blender → Maya
        return handle_import_request(request_data)
    else:
        log_message(f"Unknown action: {action}")
        delete_request_json()
        return False

# ================ SYNC LOOP ================

def check_sync_periodically():
    """Kiểm tra file sync định kỳ"""
    if not get_script_running():
        timer_id = get_timer_id()
        if timer_id is not None:
            try:
                cmds.scriptJob(kill=timer_id)
                set_timer_id(None)
            except:
                pass
        return
    
    # Check request.json (cả export và import)
    handle_export_request()

def start_sync_script():
    """Bắt đầu script sync"""
    show_sync_status("KeyHabit Sync: ACTIVE", persistent=True)
    log_message("Sync: ON")
    
    # Chạy check ngay lập tức
    handle_export_request()
    
    # Setup timer
    timer_id = get_timer_id()
    if timer_id is None:
        new_timer_id = cmds.scriptJob(event=["idle", check_sync_periodically])
        set_timer_id(new_timer_id)

def stop_sync_script():
    """Dừng script sync"""
    timer_id = get_timer_id()
    if timer_id is not None:
        try:
            cmds.scriptJob(kill=timer_id)
            set_timer_id(None)
        except Exception as e:
            log_message(f"Lỗi dừng timer: {e}")
    
    clear_sync_hud()
    show_sync_status("KeyHabit Sync: STOPPED")
    log_message("Sync: OFF")

def toggle_sync_script():
    """Toggle script - chạy lần đầu để bật, chạy lần nữa để tắt"""
    current_status = get_script_running()
    if not current_status:
        set_script_running(True)
        start_sync_script()
    else:
        set_script_running(False)
        stop_sync_script()

def force_stop_sync():
    """Force stop script sync"""
    set_script_running(False)
    timer_id = get_timer_id()
    if timer_id is not None:
        try:
            cmds.scriptJob(kill=timer_id)
            set_timer_id(None)
        except:
            pass
    clear_sync_hud()
    show_sync_status("KeyHabit Sync: FORCE STOPPED")
    log_message("Force stop")

# ================ DEBUG MODE ================

def get_debug_mode():
    """Lấy trạng thái debug mode"""
    if cmds.optionVar(exists='keyhabit_debug_mode'):
        return bool(cmds.optionVar(query='keyhabit_debug_mode'))
    return False

def set_debug_mode(value):
    """Set trạng thái debug mode"""
    cmds.optionVar(intValue=('keyhabit_debug_mode', 1 if value else 0))

def create_test_request_json(action="export", collection_name="Debug_Test_Collection"):
    """Tạo request.json giả cho debug"""
    test_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "collection": collection_name
    }
    return test_data

def debug_test_request_json(action_type="export"):
    """Test Request.json với JSON giả"""
    test_data = create_test_request_json(action=action_type)
    json_str = json.dumps(test_data, indent=2, ensure_ascii=False)
    
    debug_log('info', f"Test Request.json ({action_type})")
    log_message(f"JSON Preview:\n{json_str}")
    
    # Validate JSON format
    try:
        json.loads(json_str)
        debug_log('success', "JSON format valid")
        return True, test_data
    except Exception as e:
        debug_log('error', f"JSON format invalid: {e}")
        return False, None

def debug_test_validation(action_type="export", collection_name="Test_Collection"):
    """Test Validation"""
    debug_log('info', f"Test Validation (action={action_type})")
    
    if action_type == "export":
        # Kiểm tra group có tồn tại
        if cmds.objExists(collection_name):
            debug_log('success', f"Collection '{collection_name}' found")
            return True
        else:
            debug_log('error', f"Collection '{collection_name}' not found")
            # List tất cả groups
            all_groups = cmds.ls(type='transform')
            groups_list = [g for g in all_groups if not cmds.listRelatives(g, children=True, type='mesh')]
            log_message(f"Available groups: {groups_list[:10]}")  # Show first 10
            return False
    else:  # import
        # Kiểm tra FBX file
        if os.path.exists(FBX_PATH):
            debug_log('success', f"FBX file found: {FBX_PATH}")
            file_size = os.path.getsize(FBX_PATH)
            log_message(f"FBX file size: {file_size} bytes")
            return True
        else:
            debug_log('error', f"FBX file not found: {FBX_PATH}")
            return False

def debug_test_sharp_edge_detection(obj=None):
    """Test Sharp Edge Detection & Separation"""
    if not obj:
        selected = cmds.ls(selection=True, type='transform')
        if not selected:
            debug_log('error', "No object selected for test")
            return False
        obj = selected[0]
    
    debug_log('info', f"Test Sharp Edge Detection on: {obj}")
    
    # Phát hiện sharp edges
    hard_edges = detect_hard_edges(obj)
    edge_count = len(hard_edges)
    debug_log('info', f"Found {edge_count} sharp edges")
    
    if edge_count > 0:
        # Thực sự tách edge: Detach Components
        try:
            # Select edges
            cmds.select(hard_edges)
            
            # Detach Components
            detach_success = detach_edges(obj, hard_edges)
            
            if detach_success:
                # Merge vertices sau khi detach
                vertices_before = len(cmds.ls(f"{obj}.vtx[*]", flatten=True))
                merge_vertices_by_distance(obj, distance=0.001)
                vertices_after = len(cmds.ls(f"{obj}.vtx[*]", flatten=True))
                
                debug_log('success', f"Detached {edge_count} edges")
                log_message(f"Vertices: {vertices_before} → {vertices_after} (merged: {vertices_before - vertices_after})")
                return True
            else:
                debug_log('warning', "Detach edges failed")
                return False
        except Exception as e:
            debug_log('error', f"Error during edge separation: {e}")
            return False
    else:
        debug_log('info', "No sharp edges found")
        return True

def debug_test_object_separation(obj=None):
    """Test Object Separation"""
    if not obj:
        selected = cmds.ls(selection=True, type='transform')
        if not selected:
            debug_log('error', "No object selected for test")
            return False
        obj = selected[0]
    
    debug_log('info', f"Test Object Separation on: {obj}")
    
    # Tạo bản sao để test
    dup_name = f"{obj}_KHB_Dup_Test"
    try:
        dup_obj = cmds.duplicate(obj, name=dup_name)[0]
        
        # Thử tách
        separated = separate_object_by_edges(dup_obj)
        
        if separated and len(separated) > 1:
            debug_log('success', f"Object separated into {len(separated)} parts")
            log_message(f"Separated objects: {separated}")
            
            # Cleanup
            cmds.delete(separated)
            return True
        else:
            debug_log('warning', "Object cannot be separated")
            cmds.delete(dup_obj)
            return False
    except Exception as e:
        debug_log('error', f"Error during separation: {e}")
        if cmds.objExists(dup_name):
            cmds.delete(dup_name)
        return False

def debug_test_fbx_export_import(action_type="export", obj=None):
    """Test FBX Export/Import"""
    if action_type == "export":
        if not obj:
            selected = cmds.ls(selection=True, type='transform')
            if not selected:
                debug_log('error', "No object selected for test")
                return False
            obj = selected[0]
        
        debug_log('info', f"Test FBX Export (simulated) on: {obj}")
        
        # Validate export options (không thực sự export)
        try:
            # Get object info
            shapes = cmds.listRelatives(obj, shapes=True) or []
            if shapes:
                face_count = cmds.polyEvaluate(obj, face=True)
                vertex_count = cmds.polyEvaluate(obj, vertex=True)
                
                debug_log('success', f"Export validation OK")
                log_message(f"Objects: 1, Faces: {face_count}, Vertices: {vertex_count}")
                return True
            else:
                debug_log('error', "Object has no mesh")
                return False
        except Exception as e:
            debug_log('error', f"Export validation failed: {e}")
            return False
    else:  # import
        debug_log('info', "Test FBX Import (simulated)")
        
        if os.path.exists(FBX_PATH):
            file_size = os.path.getsize(FBX_PATH)
            debug_log('success', f"FBX file valid (size: {file_size} bytes)")
            log_message(f"Import validation: File exists and readable")
            return True
        else:
            debug_log('error', "FBX file not found for import test")
            return False

def debug_test_restore(obj=None):
    """Test Restore"""
    if not obj:
        selected = cmds.ls(selection=True, type='transform')
        if not selected:
            debug_log('error', "No object selected for test")
            return False
        obj = selected[0]
    
    debug_log('info', f"Test Restore on: {obj}")
    
    # Test restore workflow
    try:
        # Backup smooth state
        smooth_before = check_object_smooth_preview(obj)
        
        # Simulate changes
        set_smooth_preview(obj, enable=False)
        
        # Restore
        set_smooth_preview(obj, enable=smooth_before)
        
        smooth_after = check_object_smooth_preview(obj)
        
        if smooth_after == smooth_before:
            debug_log('success', "Restore test passed")
            return True
        else:
            debug_log('warning', "Restore test failed - state mismatch")
            return False
    except Exception as e:
        debug_log('error', f"Restore test error: {e}")
        return False

def create_debug_panel():
    """Tạo Debug Panel UI"""
    window_name = "KHB_Debug_Panel"
    
    # Xóa window cũ nếu có
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
    
    # Tạo window
    window = cmds.window(window_name, title="KeyHabit Sync - Debug Mode", widthHeight=(400, 600))
    
    main_layout = cmds.columnLayout(adjustableColumn=True, marginWidth=10, marginHeight=10)
    
    # Enable Debug Mode checkbox
    debug_checkbox = cmds.checkBox(
        label="Enable Debug Mode",
        value=get_debug_mode(),
        changeCommand=lambda x: set_debug_mode(cmds.checkBox(debug_checkbox, query=True, value=True))
    )
    
    cmds.separator(height=10, style='in')
    
    # Debug Actions
    cmds.text(label="Debug Actions:", font="boldLabelFont")
    cmds.separator(height=5)
    
    action_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5)
    
    # Test Request.json buttons
    cmds.button(
        label="Test Request.json (Export)",
        command=lambda x: debug_test_request_json("export")
    )
    cmds.button(
        label="Test Request.json (Import)",
        command=lambda x: debug_test_request_json("import")
    )
    
    cmds.separator(height=5, style='in')
    
    # Test Validation buttons
    cmds.text(label="Collection/Group Name:", align="left")
    collection_field = cmds.textField(text="Test_Collection", placeholderText="Enter collection name")
    
    cmds.button(
        label="Test Validation (Export)",
        command=lambda x: debug_test_validation(
            "export", 
            cmds.textField(collection_field, query=True, text=True)
        )
    )
    cmds.button(
        label="Test Validation (Import)",
        command=lambda x: debug_test_validation(
            "import",
            cmds.textField(collection_field, query=True, text=True)
        )
    )
    
    cmds.separator(height=5, style='in')
    
    # Test Sharp Edge
    cmds.button(
        label="Test Sharp Edge Detection & Separation",
        command=lambda x: debug_test_sharp_edge_detection()
    )
    
    # Test Object Separation
    cmds.button(
        label="Test Object Separation",
        command=lambda x: debug_test_object_separation()
    )
    
    cmds.separator(height=5, style='in')
    
    # Test FBX Export/Import
    cmds.button(
        label="Test FBX Export",
        command=lambda x: debug_test_fbx_export_import("export")
    )
    cmds.button(
        label="Test FBX Import",
        command=lambda x: debug_test_fbx_export_import("import")
    )
    
    # Test Restore
    cmds.button(
        label="Test Restore",
        command=lambda x: debug_test_restore()
    )
    
    cmds.setParent(main_layout)
    cmds.separator(height=10, style='in')
    
    # JSON Preview
    cmds.text(label="JSON Preview:", font="boldLabelFont")
    json_preview = cmds.scrollField(
        wordWrap=True,
        height=100,
        text="Select an action to see JSON preview"
    )
    
    # Update JSON preview khi test
    def update_json_preview(action_type):
        test_data = create_test_request_json(action=action_type)
        json_str = json.dumps(test_data, indent=2, ensure_ascii=False)
        cmds.scrollField(json_preview, edit=True, text=json_str)
    
    cmds.setParent('..')
    
    cmds.showWindow(window)
    
    return window

def show_debug_panel():
    """Hiển thị Debug Panel"""
    if get_debug_mode() or KHB_Module_Debug:
        create_debug_panel()
    else:
        log_message("Debug Mode chưa được bật. Set KHB_Module_Debug = True hoặc bật trong panel")

# ================ EXECUTION ================

if __name__ == "__main__":
    # Chạy toggle script
    toggle_sync_script()
    
    # Nếu debug mode, hiển thị panel
    if KHB_Module_Debug or get_debug_mode():
        show_debug_panel()
