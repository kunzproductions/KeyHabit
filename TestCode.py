# HƯỚNG DẪN SỬ DỤNG (Vietnamese Instructions)
# File này chứa các công cụ nhanh cho Blender:
# - Toggle Wireframe: Bật/tắt hiển thị wireframe
# - Transform Origin: Di chuyển origin của object
# - Toggle All Modifiers: Bật/tắt tất cả modifiers trong viewport
# - Toggle Subdivision Surface: Bật/tắt modifier Subdivision Surface
# 
# Cách sử dụng:
# 1. Mở Blender
# 2. Vào Text Editor và load file này
# 3. Chạy script (Alt+P hoặc Run Script)
# 4. Panel "Quick Tools" sẽ xuất hiện trong tab Tool ở 3D Viewport

import bpy

# Operator: Toggle Wireframe
class OBJECT_OT_toggle_wireframe(bpy.types.Operator):
    """Toggle wireframe overlay for selected objects"""
    bl_idname = "object.toggle_wireframe"
    bl_label = "Toggle Wireframe"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.show_wire = not obj.show_wire
        return {'FINISHED'}

# Operator: Origin to Geometry
class OBJECT_OT_origin_to_geometry(bpy.types.Operator):
    """Move origin to geometry center"""
    bl_idname = "object.origin_to_geometry"
    bl_label = "Origin to Geometry"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        self.report({'INFO'}, "Origin moved to geometry")
        return {'FINISHED'}

# Operator: Origin to 3D Cursor
class OBJECT_OT_origin_to_cursor(bpy.types.Operator):
    """Move origin to 3D cursor location"""
    bl_idname = "object.origin_to_cursor"
    bl_label = "Origin to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        self.report({'INFO'}, "Origin moved to 3D cursor")
        return {'FINISHED'}

# Operator: Toggle All Modifiers
class OBJECT_OT_toggle_all_modifiers(bpy.types.Operator):
    """Toggle visibility of all modifiers in viewport"""
    bl_idname = "object.toggle_all_modifiers"
    bl_label = "Toggle All Modifiers"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.modifiers:
                # Check current state of first modifier
                first_state = obj.modifiers[0].show_viewport if obj.modifiers else True
                # Toggle all modifiers to opposite state
                for mod in obj.modifiers:
                    mod.show_viewport = not first_state
                self.report({'INFO'}, f"Modifiers {'enabled' if not first_state else 'disabled'} for {obj.name}")
        return {'FINISHED'}

# Operator: Toggle Subdivision Surface
class OBJECT_OT_toggle_subsurf(bpy.types.Operator):
    """Toggle Subdivision Surface modifier visibility in viewport"""
    bl_idname = "object.toggle_subsurf"
    bl_label = "Toggle Subdivision Surface"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        found_subsurf = False
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if mod.type == 'SUBSURF':
                        mod.show_viewport = not mod.show_viewport
                        found_subsurf = True
                        self.report({'INFO'}, f"Subdivision Surface {'enabled' if mod.show_viewport else 'disabled'} for {obj.name}")
        
        if not found_subsurf:
            self.report({'WARNING'}, "No Subdivision Surface modifier found on selected objects")
        
        return {'FINISHED'}

# Panel: Quick Tools
class VIEW3D_PT_quick_tools(bpy.types.Panel):
    """Quick access panel for wireframe and origin tools"""
    bl_label = "Quick Tools"
    bl_idname = "VIEW3D_PT_quick_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    
    def draw(self, context):
        layout = self.layout
        
        # Wireframe section
        box = layout.box()
        box.label(text="Wireframe Overlay")
        box.operator("object.toggle_wireframe", icon='SHADING_WIRE')
        
        # Origin Transform section
        box = layout.box()
        box.label(text="Transform Origin")
        box.operator("object.origin_to_geometry", icon='OBJECT_ORIGIN')
        box.operator("object.origin_to_cursor", icon='PIVOT_CURSOR')
        
        # Modifiers section
        box = layout.box()
        box.label(text="Modifiers Control")
        box.operator("object.toggle_all_modifiers", icon='MODIFIER')
        box.operator("object.toggle_subsurf", icon='MOD_SUBSURF')

# Register classes
def register():
    bpy.utils.register_class(OBJECT_OT_toggle_wireframe)
    bpy.utils.register_class(OBJECT_OT_origin_to_geometry)
    bpy.utils.register_class(OBJECT_OT_origin_to_cursor)
    bpy.utils.register_class(OBJECT_OT_toggle_all_modifiers)
    bpy.utils.register_class(OBJECT_OT_toggle_subsurf)
    bpy.utils.register_class(VIEW3D_PT_quick_tools)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_quick_tools)
    bpy.utils.unregister_class(OBJECT_OT_toggle_subsurf)
    bpy.utils.unregister_class(OBJECT_OT_toggle_all_modifiers)
    bpy.utils.unregister_class(OBJECT_OT_origin_to_cursor)
    bpy.utils.unregister_class(OBJECT_OT_origin_to_geometry)
    bpy.utils.unregister_class(OBJECT_OT_toggle_wireframe)

if __name__ == "__main__":
    register()

