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
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, IntProperty, EnumProperty
import importlib
import sys

# ==== MODULE LOADING ====
def safe_import_module(module_name):
    """Safely import module with reload support"""
    try:
        full_name = f'{__name__}.{module_name}'
        if full_name in sys.modules:
            module = sys.modules[full_name]
            importlib.reload(module)
        else:
            module = importlib.import_module(f'.{module_name}', package=__name__)
        
        print(f"✅ KeyHabit: {module_name} imported successfully")
        return module
        
    except ImportError as e:
        print(f"❌ KeyHabit: Cannot import {module_name} - {e}")
        return None
    except Exception as e:
        print(f"❌ KeyHabit: {module_name} import error - {e}")
        return None

def get_display_module():
    """Get KHB_Display module"""
    return safe_import_module('KHB_Display')

# ==== ADDON PREFERENCES ====
class KHB_AddonPreferences(AddonPreferences):
    """KeyHabit Addon Preferences"""
    bl_idname = __name__
    
    # Display System Settings
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
    
    khb_display_line_height: IntProperty(
        name="Line Height",
        description="Height between modifier lines",
        default=18,
        min=12,
        max=32,
        update=lambda self, context: self._khb_update_display_settings()
    )
    
    khb_show_control_buttons: BoolProperty(
        name="Show Control Buttons",
        description="Show overlay control buttons in viewport",
        default=True,
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
    
    def _khb_update_display_system(self, context):
        """Toggle display system on/off"""
        display_module = get_display_module()
        
        if display_module is None:
            print("❌ KHB: Display module not available")
            self.khb_enable_display_system = False
            return
        
        try:
            if self.khb_enable_display_system:
                # Update settings first
                self._khb_apply_settings_to_display(display_module)
                # Enable system
                display_module.khb_display_manager.khb_enable_display_system()
                print("✅ KHB: Display System Enabled")
            else:
                # Disable system
                display_module.khb_display_manager.khb_disable_display_system()
                print("❌ KHB: Display System Disabled")
                
        except Exception as e:
            print(f"❌ KHB: Display update failed - {e}")
            self.khb_enable_display_system = False
    
    def _khb_update_display_settings(self):
        """Update display settings"""
        if self.khb_enable_display_system:
            display_module = get_display_module()
            if display_module:
                self._khb_apply_settings_to_display(display_module)
    
    def _khb_apply_settings_to_display(self, display_module):
        """Apply preference settings to display module"""
        try:
            # Update constants
            if hasattr(display_module, 'KHB_ICON_SIZE_PX'):
                display_module.KHB_ICON_SIZE_PX = self.khb_display_icon_size
            if hasattr(display_module, 'KHB_LINE_HEIGHT'):
                display_module.KHB_LINE_HEIGHT = self.khb_display_line_height
            
            # Update button manager
            if hasattr(display_module, 'khb_button_manager'):
                display_module.khb_button_manager.khb_update_settings({
                    'show_buttons': self.khb_show_control_buttons,
                    'position': self.khb_control_button_position,
                })
            
            # Force redraw
            if hasattr(display_module, 'khb_display_manager'):
                display_module.khb_display_manager.khb_force_redraw()
            
        except Exception as e:
            print(f"⚠️ KHB: Settings apply failed - {e}")
    
    def draw(self, context):
        """Draw preferences UI"""
        layout = self.layout
        display_module = get_display_module()
        
        # Header
        box = layout.box()
        row = box.row()
        row.label(text="KeyHabit Display System", icon='OVERLAY')
        
        if display_module is None:
            # Error state
            error_box = layout.box()
            error_col = error_box.column()
            error_col.alert = True
            error_col.label(text="⚠️ KHB_Display Module Not Found", icon='ERROR')
            error_col.label(text="Please ensure KHB_Display.py exists in addon folder")
            
            # Debug info
            debug_box = layout.box()
            debug_col = debug_box.column()
            debug_col.label(text="Available Files:", icon='CONSOLE')
            try:
                addon_dir = os.path.dirname(__file__)
                files = [f for f in os.listdir(addon_dir) if f.endswith('.py')]
                debug_col.label(text=f"Python files: {', '.join(files)}")
            except:
                debug_col.label(text="Cannot read addon directory")
            
            return
        
        # Main controls
        main_box = layout.box()
        col = main_box.column()
        
        # Enable/Disable toggle
        row = col.row(align=True)
        row.scale_y = 1.2
        
        if self.khb_enable_display_system:
            row.prop(self, "khb_enable_display_system", 
                    text="Disable Display System", 
                    icon='HIDE_ON', toggle=True)
            col.separator()
            status_row = col.row()
            status_row.label(text="● Status: ACTIVE", icon='CHECKMARK')
            
            # Settings when enabled
            col.separator()
            settings_box = col.box()
            settings_col = settings_box.column()
            settings_col.label(text="Display Settings:", icon='TOOL_SETTINGS')
            
            row = settings_col.row(align=True)
            row.prop(self, "khb_display_icon_size")
            row.prop(self, "khb_display_line_height")
            
            # Button settings
            button_box = col.box()
            button_col = button_box.column()
            button_col.label(text="Control Buttons:", icon='PREFERENCES')
            
            button_col.prop(self, "khb_show_control_buttons")
            if self.khb_show_control_buttons:
                button_col.prop(self, "khb_control_button_position")
            
        else:
            row.prop(self, "khb_enable_display_system", 
                    text="Enable Display System", 
                    icon='HIDE_OFF', toggle=True)
            col.separator()
            status_row = col.row()
            status_row.label(text="○ Status: DISABLED", icon='X')
        
        # Module info
        col.separator()
        info_box = col.box()
        info_col = info_box.column()
        info_col.label(text="System Info:", icon='INFO')
        
        if hasattr(display_module, 'KHB_DISPLAY_VERSION'):
            info_col.label(text=f"Version: {display_module.KHB_DISPLAY_VERSION}")
        
        if hasattr(display_module, 'KHB_MODIFIER_ICONS'):
            icon_count = len(display_module.KHB_MODIFIER_ICONS)
            info_col.label(text=f"Icons Available: {icon_count} modifier types")
        
        if hasattr(display_module, 'khb_display_manager'):
            is_enabled = display_module.khb_display_manager.khb_is_enabled()
            info_col.label(text=f"Manager Status: {'Active' if is_enabled else 'Inactive'}")
        
        # Quick actions
        col.separator()
        action_box = col.box()
        action_col = action_box.column()
        action_col.label(text="Quick Actions:", icon='TOOL_SETTINGS')
        
        action_row = action_col.row(align=True)
        action_row.operator("khb_prefs.reload_icons", text="Reload Icons", icon='FILE_REFRESH')
        action_row.operator("khb_prefs.test_display", text="Test System", icon='PLAY')
        action_row.operator("khb_prefs.force_cleanup", text="Force Cleanup", icon='TRASH')

# ==== PREFERENCE OPERATORS ====
class KHB_PREFS_OT_reload_icons(bpy.types.Operator):
    """Reload Display System Icons"""
    bl_idname = "khb_prefs.reload_icons"
    bl_label = "Reload Icons"
    bl_description = "Reload all PNG icons for display system"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            display_module = get_display_module()
            if display_module is None:
                self.report({'ERROR'}, "Display module not available")
                return {'CANCELLED'}
            
            # Cleanup and reload icons
            display_module.khb_icon_manager.khb_cleanup()
            success = display_module.khb_icon_manager.khb_load_icons()
            
            if success:
                self.report({'INFO'}, "Icons reloaded successfully")
                display_module.khb_display_manager.khb_force_redraw()
            else:
                self.report({'WARNING'}, "Icon reload failed")
                
        except Exception as e:
            self.report({'ERROR'}, f"Icon reload error: {e}")
        
        return {'FINISHED'}

class KHB_PREFS_OT_test_display(bpy.types.Operator):
    """Test Display System"""
    bl_idname = "khb_prefs.test_display"
    bl_label = "Test Display"
    bl_description = "Test display system functionality"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        display_module = get_display_module()
        
        if display_module is None:
            self.report({'ERROR'}, "Display module not available")
            return {'CANCELLED'}
        
        try:
            # Test components
            if hasattr(display_module, 'khb_display_manager'):
                manager = display_module.khb_display_manager
                self.report({'INFO'}, f"Display manager: {type(manager).__name__}")
                
                # Test icon manager
                if hasattr(display_module, 'khb_icon_manager'):
                    icon_mgr = display_module.khb_icon_manager
                    test_texture = icon_mgr.khb_get_texture('MIRROR')
                    icon_status = "Working" if test_texture else "No texture"
                    self.report({'INFO'}, f"Icon system: {icon_status}")
                
                # Test button manager
                if hasattr(display_module, 'khb_button_manager'):
                    btn_mgr = display_module.khb_button_manager
                    btn_count = len(btn_mgr.buttons)
                    self.report({'INFO'}, f"Button system: {btn_count} buttons")
                
                self.report({'INFO'}, "Display system test completed")
            else:
                self.report({'ERROR'}, "Display manager not found")
                
        except Exception as e:
            self.report({'ERROR'}, f"Test failed: {e}")
        
        return {'FINISHED'}

class KHB_PREFS_OT_force_cleanup(bpy.types.Operator):
    """Force cleanup all resources"""
    bl_idname = "khb_prefs.force_cleanup"
    bl_label = "Force Cleanup"
    bl_description = "Emergency cleanup of all display system resources"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            # Disable display system
            display_module = get_display_module()
            if display_module:
                display_module.khb_display_manager.khb_disable_display_system()
            
            # Nuclear cleanup - remove any orphaned handlers
            try:
                import gc
                gc.collect()
                
                # Force redraw
                for area in context.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                        
            except Exception:
                pass
            
            self.report({'INFO'}, "Force cleanup completed")
            
        except Exception as e:
            self.report({'ERROR'}, f"Force cleanup failed: {e}")
        
        return {'FINISHED'}

# ==== REGISTRATION ====
khb_addon_classes = (
    KHB_AddonPreferences,
    KHB_PREFS_OT_reload_icons,
    KHB_PREFS_OT_test_display,
    KHB_PREFS_OT_force_cleanup,
)

def register():
    """Register KeyHabit addon"""
    print("🚀 KeyHabit: Starting registration...")
    
    # Register addon preferences
    for cls in khb_addon_classes:
        try:
            bpy.utils.register_class(cls)
            print(f"✅ KeyHabit: {cls.__name__} registered")
        except Exception as e:
            print(f"❌ KeyHabit: {cls.__name__} registration failed - {e}")
    
    # Register modules
    modules = ['KHB_Normal', 'KHB_Panel', 'KHB_Display']
    
    for module_name in modules:
        module = safe_import_module(module_name)
        if module and hasattr(module, 'register'):
            try:
                module.register()
                print(f"✅ KeyHabit: {module_name} registered")
            except Exception as e:
                print(f"❌ KeyHabit: {module_name} registration failed - {e}")
        elif module:
            print(f"⚠️ KeyHabit: {module_name} has no register function")
    
    print("🎯 KeyHabit: Registration complete!")
    print("💡 Configure Display System in Edit > Preferences > Add-ons > KeyHabit")

def unregister():
    """Unregister KeyHabit addon"""
    print("🛑 KeyHabit: Starting unregistration...")
    
    # Unregister modules first (reverse order)
    modules = ['KHB_Display', 'KHB_Panel', 'KHB_Normal']
    
    for module_name in modules:
        module = safe_import_module(module_name)
        if module and hasattr(module, 'unregister'):
            try:
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
