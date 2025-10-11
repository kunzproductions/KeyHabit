import bpy
from bpy.types import Operator
import bpy.utils.previews
import blf
import math
import gpu
from gpu_extras.batch import batch_for_shader
import os
from pathlib import Path

_handler = None

# ==== CONFIG ====
USE_EMOJI_ICONS = False   # Không dùng emoji nữa, chỉ PNG
ICON_SIZE_PX = 16         # Kích thước icon (px)
ICON_PAD_PX = 4          # Khoảng cách icon -> text (px)

# ==== COLOR CONFIG ====
COLOR_BOX   = (1.0, 0.45, 0.0, 1.0)   # Cam ngoặc vuông/label
COLOR_LABEL = (1.0, 0.45, 0.0, 1.0)   # Cam tiêu đề
COLOR_VAL   = (0.85, 0.92, 0.4, 1.0)  # Xanh lá nhãn thông số
COLOR_NUM   = (1.0, 1.0, 1.0, 1.0)    # Trắng giá trị
COLOR_ON    = (0.2, 0.6, 1.0, 1.0)    # Xanh dương trạng thái bật
COLOR_OFF   = (1.0, 0.25, 0.17, 1.0)  # Đỏ trạng thái tắt
COLOR_FUNC  = COLOR_LABEL
COLOR_SRC   = COLOR_NUM

# ==== ICON SYSTEM ====
preview_collections = {}

# Mapping modifier type -> icon filename
MODIFIER_ICON_MAPPING = {
    # Generate
    'ARRAY': 'blender_icon_mod_array.png',
    'BEVEL': 'blender_icon_mod_bevel.png',
    'BOOLEAN': 'blender_icon_mod_boolean.png',
    'BUILD': 'blender_icon_mod_build.png',
    'DECIMATE': 'blender_icon_mod_decim.png',
    'EDGE_SPLIT': 'blender_icon_mod_edgesplit.png',
    'MASK': 'blender_icon_mod_mask.png',
    'MIRROR': 'blender_icon_mod_mirror.png',
    'MULTIRES': 'blender_icon_mod_multires.png',
    'REMESH': 'blender_icon_mod_remesh.png',
    'SCREW': 'blender_icon_mod_screw.png',
    'SKIN': 'blender_icon_mod_skin.png',
    'SOLIDIFY': 'blender_icon_mod_solidify.png',
    'SUBSURF': 'blender_icon_mod_subsurf.png',
    'TRIANGULATE': 'blender_icon_mod_triangulate.png',
    'WELD': 'blender_icon_mod_weld.png',
    'WIREFRAME': 'blender_icon_mod_wireframe.png',
    
    # Deform
    'CAST': 'blender_icon_mod_cast.png',
    'CURVE': 'blender_icon_mod_curve.png',
    'DISPLACE': 'blender_icon_mod_displace.png',
    'LATTICE': 'blender_icon_mod_lattice.png',
    'MESH_DEFORM': 'blender_icon_mod_meshdeform.png',
    'SHRINKWRAP': 'blender_icon_mod_shrinkwrap.png',
    'SIMPLE_DEFORM': 'blender_icon_mod_simpledeform.png',
    'SMOOTH': 'blender_icon_mod_smooth.png',
    'SURFACE_DEFORM': 'blender_icon_mod_meshdeform.png',  # Dùng chung
    
    # Modify
    'DATA_TRANSFER': 'blender_icon_mod_data_transfer.png',
    'NORMAL_EDIT': 'blender_icon_mod_normaledit.png',
    'UV_PROJECT': 'blender_icon_mod_uvproject.png',
    
    # Physics
    'CLOTH': 'blender_icon_mod_cloth.png',
    'DYNAMIC_PAINT': 'blender_icon_mod_dynamicpaint.png',
    'FLUID': 'blender_icon_mod_fluidsim.png',
    'OCEAN': 'blender_icon_mod_ocean.png',
    'PARTICLE_INSTANCE': 'blender_icon_mod_particle_instance.png',
    'PARTICLE_SYSTEM': 'blender_icon_mod_particles.png',
    'SOFT_BODY': 'blender_icon_mod_soft.png',
    
    # Special
    'NODES': 'blender_icon_geometry_nodes.png',  # Geometry Nodes
}

FALLBACK_ICON = 'blender_icon_question.png'

class IconManager:
    """Quản lý hệ thống icon PNG"""
    
    def __init__(self):
        self.pcoll = None
        self.icons_loaded = False
        
    def load_icons(self):
        global preview_collections
        
        if self.icons_loaded:
            return
            
        # Tạo preview collection
        if "keyhabit_icons" in preview_collections:
            bpy.utils.previews.remove(preview_collections["keyhabit_icons"])
            
        pcoll = bpy.utils.previews.new()
        
        # Đường dẫn đến thư mục icons
        addon_dir = Path(__file__).parent
        icons_dir = addon_dir / "icons"
        
        # Load fallback icon trước
        fallback_path = icons_dir / FALLBACK_ICON
        if fallback_path.exists():
            pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
        
        # Load tất cả modifier icons
        for mod_type, filename in MODIFIER_ICON_MAPPING.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                pcoll.load(mod_type, str(icon_path), 'IMAGE')
                print(f"✅ Loaded icon: {mod_type} -> {filename}")
            else:
                print(f"⚠️ Missing icon: {filename} for {mod_type}")
        
        preview_collections["keyhabit_icons"] = pcoll
        self.pcoll = pcoll
        self.icons_loaded = True
        print(f"🎨 Icon system initialized with {len(pcoll)} icons")
    
    def get_icon_texture(self, mod_type):
        """Lấy texture icon cho modifier type"""
        if not self.icons_loaded:
            self.load_icons()
            
        if self.pcoll is None:
            return None
            
        # Thử lấy icon chính xác
        if mod_type in self.pcoll:
            preview = self.pcoll[mod_type]
            if hasattr(preview, 'icon_id') and preview.icon_id > 0:
                return self._get_texture_from_icon_id(preview.icon_id)
        
        # Fallback icon
        if "FALLBACK" in self.pcoll:
            preview = self.pcoll["FALLBACK"]
            if hasattr(preview, 'icon_id') and preview.icon_id > 0:
                return self._get_texture_from_icon_id(preview.icon_id)
        
        return None
    
    def _get_texture_from_icon_id(self, icon_id):
        """Convert icon_id thành GPU texture"""
        try:
            # Method 1: Direct GPU texture từ icon_id
            if hasattr(gpu, 'texture') and hasattr(gpu.texture, 'from_icon'):
                return gpu.texture.from_icon(icon_id)
        except Exception as e:
            print(f"Error getting texture from icon_id: {e}")
        return None
    
    def cleanup(self):
        """Dọn dẹp preview collections"""
        global preview_collections
        for pcoll in preview_collections.values():
            bpy.utils.previews.remove(pcoll)
        preview_collections.clear()
        self.icons_loaded = False

# Global icon manager
icon_manager = IconManager()

# ==== GPU RENDERING ====
_image_shader = gpu.shader.from_builtin('IMAGE')

def _draw_texture(tex, x, y, w, h):
    """Vẽ texture lên screen"""
    if tex is None:
        return 0
    
    try:
        pos = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
        uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        batch = batch_for_shader(_image_shader, 'TRI_FAN', {"pos": pos, "texCoord": uv})
        
        gpu.state.blend_set('ALPHA')
        _image_shader.bind()
        
        # Bind texture
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
        
    except Exception as e:
        print(f"Error drawing texture: {e}")
        gpu.state.blend_set('NONE')
        return 0

def draw_modifier_icon_png(font_id, x, y, mod_type, icon_size=ICON_SIZE_PX):
    """
    Vẽ icon modifier từ PNG files
    Priority: Custom PNG > Fallback PNG > Emoji
    """
    # Thử lấy PNG texture
    tex = icon_manager.get_icon_texture(mod_type)
    if tex is not None:
        w = int(icon_size)
        h = int(icon_size)
        drawn_w = _draw_texture(tex, x, y, w, h)
        if drawn_w > 0:
            return drawn_w
    
    # Fallback: Vẽ text placeholder
    blf.size(font_id, int(icon_size * 0.7))
    blf.position(font_id, x, y, 0)
    blf.color(font_id, 0.9, 0.5, 0.1, 1.0)
    text = "?"
    blf.draw(font_id, text)
    w = blf.dimensions(font_id, text)[0]
    return int(max(w, icon_size))

# ==== MODIFIER TEXT PROCESSING ====

def get_modifier_display_name(mod):
    """Lấy tên hiển thị của modifier"""
    try:
        enum_prop = bpy.types.Modifier.bl_rna.properties['type']
        return enum_prop.enum_items[mod.type].name
    except Exception:
        return mod.type.title().replace('_', ' ')

def get_modifier_line(mod):
    """Tạo danh sách (text, color) cho modifier"""
    tc = []
    
    # ===== Shader Auto Smooth (Geometry Nodes) =====
    if mod.type == 'NODES' and ("Smooth by Angle" in mod.name or "Shade Auto Smooth" in mod.name):
        tc.append(('[', COLOR_BOX))
        tc.append(('Shade Auto Smooth', COLOR_LABEL))
        tc.append((']', COLOR_BOX))
        tc.append((' ' + mod.name, COLOR_NUM))
        
        angle_deg = None
        ignore_val = None
        if "Input_1" in mod.keys():
            angle_deg = round(mod["Input_1"] * 180 / math.pi, 1)
        if "Socket_1" in mod.keys():
            ignore_val = bool(mod["Socket_1"])
            
        tc.append((' Angle:', COLOR_VAL))
        tc.append((f"{angle_deg if angle_deg is not None else 0.0}°", COLOR_NUM))
        if ignore_val:
            tc.append((' IgnoreSharpness', COLOR_ON))
    else:
        # Modifier thường 
        tc.append(('[', COLOR_BOX))
        tc.append((get_modifier_display_name(mod), COLOR_LABEL))
        tc.append((']', COLOR_BOX))
        tc.append((' ' + mod.name, COLOR_NUM))
        
        # Thông số specific cho từng modifier
        if mod.type == 'MIRROR':
            axes = getattr(mod, 'use_axis', [False, False, False])
            for i, label in enumerate(['X', 'Y', 'Z']):
                col = COLOR_ON if (i < len(axes) and axes[i]) else COLOR_OFF
                tc.append((' ' + label, col))
            mirror_obj = getattr(mod, 'mirror_object', None)
            if mirror_obj:
                tc.append((' Mirror Object:', COLOR_LABEL))
                tc.append((' ' + mirror_obj.name, COLOR_SRC))
                
        elif mod.type == 'BOOLEAN':
            op = getattr(mod, 'operation', '')
            solver = getattr(mod, 'solver', '')
            if op:
                tc.append((' ' + op, COLOR_FUNC))
            if solver == 'BMESH':
                tc.append((' BMESH', COLOR_ON))
            if solver == 'EXACT':
                tc.append((' EXACT', COLOR_ON))
            src_obj = getattr(mod, 'object', None)
            if src_obj:
                tc.append((' ' + src_obj.name, COLOR_SRC))
                
        elif mod.type == 'DISPLACE':
            strength = getattr(mod, 'strength', 0)
            tc.append((' Strength:', COLOR_VAL))
            tc.append((f"{strength:.3f}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg:
                tc.append((' VG:', COLOR_VAL))
                tc.append((vg, COLOR_NUM))
                
        elif mod.type == 'BEVEL':
            amount = getattr(mod, 'width', 0)
            segments = getattr(mod, 'segments', 0)
            tc.append((' Amount:', COLOR_VAL))
            tc.append((f"{amount:.3f}", COLOR_NUM))
            tc.append((' Segment:', COLOR_VAL))
            tc.append((f"{segments}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            lim = getattr(mod, 'limit_method', '')
            if vg:
                tc.append((' VG:', COLOR_VAL))
                tc.append((vg, COLOR_NUM))
            if lim == 'ANGLE':
                tc.append((' ANGLE', COLOR_ON))
            if lim == 'WEIGHT':
                tc.append((' WEIGHT', COLOR_ON))
                
        elif mod.type == 'ARRAY':
            count = getattr(mod, 'count', 0)
            tc.append((' ×', COLOR_VAL))
            tc.append((f"{count}", COLOR_NUM))
            
        elif mod.type == 'SOLIDIFY':
            thickness = getattr(mod, 'thickness', 0)
            tc.append((' T:', COLOR_VAL))
            tc.append((f"{thickness:.3f}", COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg:
                tc.append((' VG:', COLOR_VAL))
                tc.append((vg, COLOR_NUM))
                
        elif mod.type == 'SUBSURF':
            levels = getattr(mod, 'levels', 0)
            tc.append((' Lv', COLOR_VAL))
            tc.append((f"{levels}", COLOR_NUM))
            
        elif mod.type == 'DATA_TRANSFER':
            obj = getattr(mod, 'object', None)
            if obj:
                tc.append((' ← ', COLOR_VAL))
                tc.append((obj.name, COLOR_NUM))
                
        elif mod.type == 'SHRINKWRAP':
            tgt = getattr(mod, 'target', None)
            if tgt:
                tc.append((' → ', COLOR_VAL))
                tc.append((tgt.name, COLOR_NUM))
            vg = getattr(mod, 'vertex_group', '')
            if vg:
                tc.append((' VG:', COLOR_VAL))
                tc.append((vg, COLOR_NUM))
    
    return tc

# ==== CONTROL BUTTONS ====

class ControlButton:
    """Class cho control button overlay"""
    
    def __init__(self, button_id, x, y, size, operator_id, tooltip=""):
        self.button_id = button_id
        self.x = x
        self.y = y
        self.size = size
        self.operator_id = operator_id
        self.tooltip = tooltip
        self.is_pressed = False
        
    def hit_test(self, mouse_x, mouse_y):
        """Kiểm tra chuột có click vào button không"""
        return (self.x <= mouse_x <= self.x + self.size and 
                self.y <= mouse_y <= self.y + self.size)
    
    def execute(self):
        """Thực thi operator của button"""
        try:
            bpy.ops.keyhabit.toggle_wireframe() if self.button_id == 'wireframe' else None
            bpy.ops.keyhabit.toggle_edge_length() if self.button_id == 'edge_length' else None
            bpy.ops.keyhabit.toggle_retopology() if self.button_id == 'retopo' else None
            bpy.ops.keyhabit.toggle_split_normals() if self.button_id == 'split_normals' else None
        except Exception as e:
            print(f"Button execute error: {e}")

# Control buttons toàn cục
control_buttons = []

def init_control_buttons():
    """Khởi tạo control buttons"""
    global control_buttons
    control_buttons.clear()
    
    button_y = 60  # Từ dưới lên
    x = 50
    button_size = 32
    button_gap = 10
    
    buttons_config = [
        ('wireframe', 'Wireframe Overlay'),
        ('edge_length', 'Edge Length'),
        ('retopo', 'Retopology'),
        ('split_normals', 'Split Normals')
    ]
    
    for button_id, tooltip in buttons_config:
        btn = ControlButton(button_id, x, button_y, button_size, 
                          f"keyhabit.toggle_{button_id}", tooltip)
        control_buttons.append(btn)
        x += button_size + button_gap

def draw_control_buttons():
    """Vẽ control buttons overlay"""
    if not control_buttons:
        init_control_buttons()
    
    font_id = 0
    blf.size(font_id, 10)
    
    for button in control_buttons:
        # Vẽ background button
        x, y, size = button.x, button.y, button.size
        
        # Lấy trạng thái overlay
        is_active = get_overlay_state(button.button_id)
        
        # Màu button
        if is_active:
            color = (0.2, 0.6, 1.0, 0.8)  # Xanh dương active
        else:
            color = (0.3, 0.3, 0.3, 0.8)  # Xám inactive
            
        # Vẽ rounded rectangle (simplified)
        _draw_button_bg(x, y, size, size, color)
        
        # Vẽ icon placeholder (có thể thay bằng PNG sau)
        blf.position(font_id, x + size//4, y + size//4, 0)
        blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
        icon_text = button.button_id[0].upper()  # Chữ cái đầu
        blf.draw(font_id, icon_text)

def _draw_button_bg(x, y, w, h, color):
    """Vẽ background button đơn giản"""
    try:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        vertices = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": vertices})
        
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
        gpu.state.blend_set('NONE')
    except Exception as e:
        print(f"Button bg draw error: {e}")

def get_overlay_state(button_id):
    """Lấy trạng thái overlay"""
    try:
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        overlay = space.overlay
                        if button_id == 'wireframe':
                            return overlay.show_wireframes
                        elif button_id == 'edge_length':
                            return overlay.show_extra_edge_length
                        elif button_id == 'retopo':
                            return overlay.show_retopology
                        elif button_id == 'split_normals':
                            return overlay.show_split_normals
    except:
        pass
    return False

# ==== DRAW OVERLAY MAIN ====

def draw_overlay_unified():
    """Draw overlay chính - modifier info + control buttons"""
    if not bpy.context.selected_objects:
        return
    
    font_id = 0
    y = 15
    line_height = 18
    obj = bpy.context.active_object
    
    blf.size(font_id, 12)
    
    if obj and obj.type == 'MESH' and obj.modifiers:
        # Vẽ modifier info
        for mod in reversed(obj.modifiers):
            x = 20
            
            # Vẽ icon
            icon_w = draw_modifier_icon_png(font_id, x, y, mod.type, icon_size=ICON_SIZE_PX)
            x += int(icon_w) + ICON_PAD_PX
            
            # Vẽ text thông tin
            tc = get_modifier_line(mod)
            for txt, col in tc:
                blf.position(font_id, x, y, 0)
                blf.color(font_id, *col)
                blf.draw(font_id, txt)
                text_w = blf.dimensions(font_id, txt)[0]
                x += int(text_w)
            
            y += line_height
    else:
        # Thông báo không có object mesh
        blf.position(font_id, 20, y, 0)
        blf.color(font_id, 1.0, 1.0, 0.2, 1.0)
        blf.draw(font_id, "Không có object MESH được chọn hoặc không có modifier")
    
    # Vẽ control buttons
    draw_control_buttons()

# ==== OPERATORS ====

def iter_view3d_spaces(context):
    """Iterate tất cả VIEW_3D spaces"""
    for area in context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    yield area, space

def tag_redraw_view3d(context):
    """Force redraw VIEW_3D"""
    for area, _ in iter_view3d_spaces(context):
        area.tag_redraw()

class KEYHABIT_OT_toggle_wireframe(Operator):
    bl_idname = "keyhabit.toggle_wireframe"
    bl_label = "Toggle Wireframe Overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_wireframes = not ov.show_wireframes
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KEYHABIT_OT_toggle_edge_length(Operator):
    bl_idname = "keyhabit.toggle_edge_length"
    bl_label = "Toggle Edge Length"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_extra_edge_length = not ov.show_extra_edge_length
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KEYHABIT_OT_toggle_retopology(Operator):
    bl_idname = "keyhabit.toggle_retopology"
    bl_label = "Toggle Retopology Overlay"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_retopology = not ov.show_retopology
        tag_redraw_view3d(context)
        return {'FINISHED'}

class KEYHABIT_OT_toggle_split_normals(Operator):
    bl_idname = "keyhabit.toggle_split_normals"
    bl_label = "Toggle Split Normals"
    bl_options = {'INTERNAL', 'UNDO_GROUPED'}

    def execute(self, context):
        for _, space in iter_view3d_spaces(context):
            ov = space.overlay
            ov.show_split_normals = not ov.show_split_normals
        tag_redraw_view3d(context)
        return {'FINISHED'}

# Modal operator để handle click
class KEYHABIT_OT_overlay_modal(Operator):
    bl_idname = "keyhabit.overlay_modal"
    bl_label = "Overlay Modal Handler"
    
    def modal(self, context, event):
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mouse_x = event.mouse_region_x
            mouse_y = event.mouse_region_y
            
            # Check button hits
            for button in control_buttons:
                if button.hit_test(mouse_x, mouse_y):
                    button.execute()
                    tag_redraw_view3d(context)
                    return {'RUNNING_MODAL'}
        
        if event.type in {'ESC'}:
            return {'CANCELLED'}
            
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

# ==== ENABLE/DISABLE ====

def enable_overlay_unified():
    global _handler
    if _handler is None:
        # Load icons
        icon_manager.load_icons()
        
        # Setup draw handler
        _handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_overlay_unified, (), 'WINDOW', 'POST_PIXEL'
        )
        
        # Initialize buttons
        init_control_buttons()
        
        # Start modal
        bpy.ops.keyhabit.overlay_modal('INVOKE_DEFAULT')
        
        print("✅ Unified Overlay enabled! (PNG icons + Draw Handler)")
        
        # Force redraw
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

def disable_overlay_unified():
    global _handler
    if _handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handler, 'WINDOW')
        _handler = None
        
        # Cleanup icons
        icon_manager.cleanup()
        
        print("❌ Unified Overlay disabled!")
        
        # Force redraw
        for area in bpy.context.window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

# ==== REGISTRATION ====

classes = (
    KEYHABIT_OT_toggle_wireframe,
    KEYHABIT_OT_toggle_edge_length,
    KEYHABIT_OT_toggle_retopology,
    KEYHABIT_OT_toggle_split_normals,
    KEYHABIT_OT_overlay_modal,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Auto enable
    enable_overlay_unified()

def unregister():
    # Disable trước
    disable_overlay_unified()
    
    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
