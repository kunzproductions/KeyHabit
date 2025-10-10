# Test nhanh trong blender
# ================== DRAW OVERLAY ==================
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

# ================== OPERATORS & PANEL ==================
# Operator: Toggle Wireframe Overlay
class OBJECT_OT_toggle_wireframe(bpy.types.Operator):
    """Toggle wireframe overlay for selected objects"""
    bl_idname = "object.toggle_wireframe"
    bl_label = "Toggle Wireframe"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                obj.show_wire = not obj.show_wire
                obj.show_all_edges = obj.show_wire
        return {'FINISHED'}

# Operator: Transform Origin to Geometry
class OBJECT_OT_origin_to_geometry(bpy.types.Operator):
    """Set origin to geometry center for selected objects"""
    bl_idname = "object.origin_to_geometry"
    bl_label = "Origin to Geometry"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        self.report({'INFO'}, "Origin moved to geometry center")
        return {'FINISHED'}

# Operator: Transform Origin to 3D Cursor
class OBJECT_OT_origin_to_cursor(bpy.types.Operator):
    """Set origin to 3D cursor for selected objects"""
    bl_idname = "object.origin_to_cursor"
    bl_label = "Origin to 3D Cursor"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        self.report({'INFO'}, "Origin moved to 3D cursor")
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

# Register classes
def register():
    bpy.utils.register_class(OBJECT_OT_toggle_wireframe)
    bpy.utils.register_class(OBJECT_OT_origin_to_geometry)
    bpy.utils.register_class(OBJECT_OT_origin_to_cursor)
    bpy.utils.register_class(VIEW3D_PT_quick_tools)

def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_quick_tools)
    bpy.utils.unregister_class(OBJECT_OT_origin_to_cursor)
    bpy.utils.unregister_class(OBJECT_OT_origin_to_geometry)
    bpy.utils.unregister_class(OBJECT_OT_toggle_wireframe)

if __name__ == "__main__":
    register()
