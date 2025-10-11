"""
KeyHabit Addon - Advanced Blender Tools
Version: 2.0.0
"""

bl_info = {
    "name": "KeyHabit", 
    "author": "MinThuan",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > KeyHabit",
    "description": "Advanced tools for 3D modeling workflow",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

# ==== IMPORT FIX - Lazy loading để tránh circular import ====
def _get_display_module():
    """Lazy import KBH_Display để tránh circular import"""
    from . import KBH_Display
    return KBH_Display

def _get_panel_module():
    """Lazy import KBH_Panel"""
    from . import KBH_Panel
    return KBH_Panel

def _get_normal_module():
    """Lazy import KBH_Normal"""
    from . import KBH_Normal
    return KBH_Normal

# ==== ADDON PREFERENCES ====
class KBH_AddonPreferences(AddonPreferences):
    """KeyHabit Addon Preferences"""
    bl_idname = __name__
    
    # ==== DISPLAY SYSTEM SETTINGS ====
    khb_enable_display_system: BoolProperty(
        name="Enable Display System",
        description="Enable modifier overlay display with PNG icons",
        default=False,
        update=lambda self, context: self._khb_update_display_system(context)
    )
    
    khb_display_icon_size: IntProperty(
        name="Icon Size",
        description="Size of modifier icons in pixels",
        default=16,
        min=12,
        max=32,
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    khb_display_icon_padding: IntProperty(
        name="Icon Padding", 
        description="Padding between icon and text",
        default=4,
        min=0,
        max=16,
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    khb_display_line_height: IntProperty(
        name="Line Height",
        description="Height between modifier lines",
        default=18,
        min=12,
        max=32,
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    # ==== OVERLAY CONTROL SETTINGS ====
    khb_show_control_buttons: BoolProperty(
        name="Show Control Buttons",
        description="Show overlay control buttons in viewport",
        default=True,
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    khb_control_button_size: IntProperty(
        name="Button Size",
        description="Size of control buttons",
        default=32,
        min=20,
        max=50,
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    khb_control_button_position: EnumProperty(
        name="Button Position",
        description="Position of control buttons in viewport",
        items=[
            ('BOTTOM_LEFT', "Bottom Left", "Position buttons at bottom left"),
            ('BOTTOM_RIGHT', "Bottom Right", "Position buttons at bottom right"),
            ('TOP_LEFT', "Top Left", "Position buttons at top left"),
            ('TOP_RIGHT', "Top Right", "Position buttons at top right"),
        ],
        default='BOTTOM_LEFT',
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    # ==== COLOR SETTINGS ====
    khb_color_scheme: EnumProperty(
        name="Color Scheme",
        description="Color scheme for overlay display",
        items=[
            ('DEFAULT', "Default", "Default KeyHabit colors"),
            ('BLENDER', "Blender", "Match Blender UI colors"),
            ('CUSTOM', "Custom", "Custom color configuration"),
        ],
        default='DEFAULT',
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    def _khb_update_display_system(self, context):
        """Update display system enable/disable"""
        try:
            KBH_Display = _get_display_module()
            
            if self.khb_enable_display_system:
                # Update settings first
                self._khb_apply_settings_to_display()
                # Enable system
                KBH_Display.khb_display_manager.khb_enable_display_system()
            else:
                # Disable system
                KBH_Display.khb_display_manager.khb_disable_display_system()
        except Exception as e:
            print(f"❌ KBH: Display system update failed - {e}")
    
    def _khb_update_display_settings(self):
        """Update display settings if system is enabled"""
        if self.khb_enable_display_system:
            self._khb_apply_settings_to_display()
            # Force redraw
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    
    def _khb_apply_settings_to_display(self):
        """Apply preference settings to display system"""
        try:
            KBH_Display = _get_display_module()
            
            # Update display constants
            KBH_Display.KBH_ICON_SIZE_PX = self.khb_display_icon_size
            KBH_Display.KBH_ICON_PAD_PX = self.khb_display_icon_padding
            KBH_Display.KBH_LINE_HEIGHT = self.khb_display_line_height
            KBH_Display.KBH_BUTTON_SIZE = self.khb_control_button_size
            
            # Update button manager settings
            if hasattr(KBH_Display.khb_button_manager, 'khb_update_settings'):
                KBH_Display.khb_button_manager.khb_update_settings({
                    'show_buttons': self.khb_show_control_buttons,
                    'button_size': self.khb_control_button_size,
                    'position': self.khb_control_button_position,
                })
            
            print(f"🎨 KBH: Display settings updated")
            
        except Exception as e:
            print(f"⚠️ KBH: Settings update failed - {e}")
    
    def draw(self, context):
        """Draw preferences UI"""
        layout = self.layout
        
        # ==== MAIN HEADER ====
        box = layout.box()
        row = box.row()
        row.label(text="KeyHabit Display System", icon='OVERLAY')
        
        # ==== ENABLE/DISABLE ====
        main_box = layout.box()
        col = main_box.column()
        
        # Main toggle
        row = col.row(align=True)
        row.scale_y = 1.2
        if self.khb_enable_display_system:
            row.prop(self, "khb_enable_display_system", 
                    text="Disable Display System", 
                    icon='HIDE_ON', toggle=True)
        else:
            row.prop(self, "khb_enable_display_system", 
                    text="Enable Display System", 
                    icon='HIDE_OFF', toggle=True)
        
        # Status indicator
        col.separator(factor=0.5)
        status_row = col.row()
        if self.khb_enable_display_system:
            status_row.label(text="● Display System: ACTIVE", icon='CHECKMARK')
        else:
            status_row.label(text="○ Display System: DISABLED", icon='X')
        
        # ==== DISPLAY SETTINGS (only if enabled) ====
        if self.khb_enable_display_system:
            col.separator()
            
            # Icon Settings
            icon_box = col.box()
            icon_col = icon_box.column()
            icon_col.label(text="Icon Settings:", icon='IMAGE_DATA')
            
            row = icon_col.row(align=True)
            row.prop(self, "khb_display_icon_size")
            row.prop(self, "khb_display_icon_padding")
            
            icon_col.prop(self, "khb_display_line_height")
            
            # Control Button Settings
            button_box = col.box()
            button_col = button_box.column()
            button_col.label(text="Control Buttons:", icon='PREFERENCES')
            
            button_col.prop(self, "khb_show_control_buttons")
            
            if self.khb_show_control_buttons:
                row = button_col.row(align=True)
                row.prop(self, "khb_control_button_size")
                row.prop(self, "khb_control_button_position", text="")
            
            # Color Settings
            color_box = col.box()
            color_col = color_box.column()
            color_col.label(text="Appearance:", icon='COLOR')
            color_col.prop(self, "khb_color_scheme")
            
            # Info section
            col.separator()
            info_box = col.box()
            info_col = info_box.column()
            info_col.label(text="Display System Info:", icon='INFO')
            
            # System status
            try:
                KBH_Display = _get_display_module()
                icon_count = len(KBH_Display.KBH_MODIFIER_ICONS)
                loaded_icons = len(KBH_Display.khb_icon_manager.preview_collections.get("khb_display_icons", {}))
                info_col.label(text=f"Icons Available: {loaded_icons}/{icon_count}")
                
                if KBH_Display.khb_display_manager.khb_is_enabled():
                    info_col.label(text="Render Mode: GPU Accelerated")
                    info_col.label(text="Interaction: Modal Handler Active")
                
            except Exception as e:
                info_col.label(text=f"Status: Error - {e}")
        
        # ==== QUICK ACTIONS ====
        if self.khb_enable_display_system:
            col.separator()
            action_box = col.box()
            action_col = action_box.column()
            action_col.label(text="Quick Actions:", icon='TOOL_SETTINGS')
            
            row = action_col.row(align=True)
            row.operator("khb_prefs.reload_icons", text="Reload Icons", icon='FILE_REFRESH')
            row.operator("khb_prefs.reset_display", text="Reset Settings", icon='LOOP_BACK')

# ==== PREFERENCE OPERATORS ====
class KBH_PREFS_OT_reload_icons(bpy.types.Operator):
    """Reload Display System Icons"""
    bl_idname = "khb_prefs.reload_icons"
    bl_label = "Reload Icons"
    bl_description = "Reload all PNG icons for display system"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            KBH_Display = _get_display_module()
            
            # Cleanup and reload icons
            KBH_Display.khb_icon_manager.khb_cleanup_all()
            success = KBH_Display.khb_icon_manager.khb_load_modifier_icons()
            
            if success:
                self.report({'INFO'}, "Icons reloaded successfully")
                # Force redraw
                for area in context.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            else:
                self.report({'WARNING'}, "Icon reload failed")
                
        except Exception as e:
            self.report({'ERROR'}, f"Icon reload error: {e}")
        
        return {'FINISHED'}

class KBH_PREFS_OT_reset_display(bpy.types.Operator):
    """Reset Display Settings"""
    bl_idname = "khb_prefs.reset_display"
    bl_label = "Reset Display Settings"
    bl_description = "Reset all display settings to default values"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            prefs = context.preferences.addons[__name__].preferences
            
            # Reset to defaults
            prefs.khb_display_icon_size = 16
            prefs.khb_display_icon_padding = 4
            prefs.khb_display_line_height = 18
            prefs.khb_control_button_size = 32
            prefs.khb_show_control_buttons = True
            prefs.khb_control_button_position = 'BOTTOM_LEFT'
            prefs.khb_color_scheme = 'DEFAULT'
            
            self.report({'INFO'}, "Display settings reset to defaults")
            
        except Exception as e:
            self.report({'ERROR'}, f"Reset failed: {e}")
        
        return {'FINISHED'}

# ==== ADDON CLASSES ====
khb_addon_classes = (
    KBH_AddonPreferences,
    KBH_PREFS_OT_reload_icons,
    KBH_PREFS_OT_reset_display,
)

def register():
    """Register all KeyHabit modules"""
    print("🚀 KeyHabit: Starting registration...")
    
    # Register addon classes first
    for cls in khb_addon_classes:
        try:
            bpy.utils.register_class(cls)
            print(f"✅ KeyHabit: {cls.__name__} registered")
        except Exception as e:
            print(f"❌ KeyHabit: {cls.__name__} registration failed - {e}")
    
    # Register modules using lazy loading
    khb_modules = [
        ('KBH_Normal', _get_normal_module),
        ('KBH_Panel', _get_panel_module),
        ('KBH_Display', _get_display_module),
    ]
    
    for module_name, module_getter in khb_modules:
        try:
            module = module_getter()
            module.register()
            print(f"✅ KeyHabit: {module_name} registered")
        except Exception as e:
            print(f"❌ KeyHabit: {module_name} registration failed - {e}")
    
    print("🎯 KeyHabit: Registration complete!")
    print("💡 KeyHabit: Configure Display System in Edit > Preferences > Add-ons > KeyHabit")

def unregister():
    """Unregister all KeyHabit modules"""
    print("🛑 KeyHabit: Starting unregistration...")
    
    # Disable display system first
    try:
        KBH_Display = _get_display_module()
        KBH_Display.khb_display_manager.khb_disable_display_system()
    except:
        pass
    
    # Unregister modules in reverse order
    khb_modules = [
        ('KBH_Display', _get_display_module),
        ('KBH_Panel', _get_panel_module),
        ('KBH_Normal', _get_normal_module),
    ]
    
    for module_name, module_getter in khb_modules:
        try:
            module = module_getter()
            module.unregister()
            print(f"✅ KeyHabit: {module_name} unregistered")
        except Exception as e:
            print(f"⚠️ KeyHabit: {module_name} unregistration error - {e}")
    
    # Unregister addon classes
    for cls in reversed(khb_addon_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KeyHabit: {cls.__name__} unregistration error - {e}")
    
    print("👋 KeyHabit: Unregistration complete!")

if __name__ == "__main__":
    register()
