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
import os

# ==== IMPORT CONTROL (Prevent loop) ====
_khb_module_cache = {}
_khb_importing = False

def safe_import_module(module_name):
    """Safe import with loop prevention"""
    global _khb_module_cache, _khb_importing
    
    # Prevent recursive imports
    if _khb_importing:
        return _khb_module_cache.get(module_name)
    
    _khb_importing = True
    
    try:
        full_name = f'{__name__}.{module_name}'
        
        if module_name in _khb_module_cache:
            # Return cached module (don't reload)
            return _khb_module_cache[module_name]
        
        if full_name in sys.modules:
            module = sys.modules[full_name]
            # Only reload if explicitly requested
        else:
            module = importlib.import_module(f'.{module_name}', package=__name__)
        
        _khb_module_cache[module_name] = module
        print(f"✅ KeyHabit: {module_name} imported successfully")
        return module
        
    except ImportError as e:
        print(f"❌ KeyHabit: Cannot import {module_name} - {e}")
        return None
    except Exception as e:
        print(f"❌ KeyHabit: {module_name} import error - {e}")
        return None
    finally:
        _khb_importing = False

def get_display_module():
    """Get KHB_Display module"""
    return safe_import_module('KHB_Display')

# ==== ADDON PREFERENCES ====
class KHB_AddonPreferences(AddonPreferences):
    """KeyHabit Addon Preferences"""
    bl_idname = __name__
    
    # Display system toggle
    khb_enable_display_system: BoolProperty(
        name="Enable Display System",
        description="Enable modifier overlay display with PNG icons",
        default=False,
        update=lambda self, context: self._khb_update_display_system()
    )
    
    khb_display_icon_size: IntProperty(
        name="Icon Size", default=16, min=12, max=32
    )
    
    def _khb_update_display_system(self):
        """Update display system - NO CONTEXT PARAMETER"""
        display_module = get_display_module()
        
        if display_module is None:
            print("❌ KHB: Display module not available")
            self.khb_enable_display_system = False
            return
        
        try:
            if self.khb_enable_display_system:
                # Apply settings first
                if hasattr(display_module, 'KHB_ICON_SIZE_PX'):
                    display_module.KHB_ICON_SIZE_PX = self.khb_display_icon_size
                
                # Enable system
                display_module.khb_enable_display_system()
                print("✅ KHB: Display System Enabled")
            else:
                # Disable system
                display_module.khb_disable_display_system()
                print("❌ KHB: Display System Disabled")
                
        except Exception as e:
            print(f"❌ KHB: Display update failed - {e}")
            self.khb_enable_display_system = False
    
    def draw(self, context):
        """Draw preferences UI"""
        layout = self.layout
        display_module = get_display_module()
        
        # Header
        box = layout.box()
        box.label(text="KeyHabit Display System", icon='OVERLAY')
        
        if display_module is None:
            # Error state
            error_box = layout.box()
            error_col = error_box.column()
            error_col.alert = True
            error_col.label(text="⚠️ KHB_Display Module Not Found", icon='ERROR')
            
            # Debug info
            try:
                addon_dir = os.path.dirname(__file__)
                files = [f for f in os.listdir(addon_dir) if f.endswith('.py')]
                error_col.label(text=f"Files: {', '.join(files)}")
            except:
                error_col.label(text="Cannot read addon directory")
            
            return
        
        # Main controls
        main_box = layout.box()
        col = main_box.column()
        
        # Status display
        if hasattr(display_module, 'khb_is_enabled') and display_module.khb_is_enabled():
            status_text = "● Status: ACTIVE"
            status_icon = 'CHECKMARK'
        else:
            status_text = "○ Status: INACTIVE"
            status_icon = 'X'
        
        col.label(text=status_text, icon=status_icon)
        
        # Enable/Disable toggle
        row = col.row()
        row.scale_y = 1.2
        row.prop(self, "khb_enable_display_system", 
                text="Display System", toggle=True)
        
        # Settings
        if self.khb_enable_display_system:
            col.separator()
            settings_box = col.box()
            settings_col = settings_box.column()
            settings_col.label(text="Settings:")
            settings_col.prop(self, "khb_display_icon_size")
        
        # Module info
        col.separator()
        info_box = col.box()
        info_col = info_box.column()
        info_col.label(text="Module Info:", icon='INFO')
        
        if hasattr(display_module, 'KHB_DISPLAY_VERSION'):
            info_col.label(text=f"Version: {display_module.KHB_DISPLAY_VERSION}")
        
        if hasattr(display_module, 'KHB_MODIFIER_ICONS'):
            icon_count = len(display_module.KHB_MODIFIER_ICONS)
            info_col.label(text=f"Icons: {icon_count} modifier types")
        
        # Quick actions
        col.separator()
        action_row = col.row(align=True)
        action_row.operator("khb_prefs.reload_icons", text="Reload Icons", icon='FILE_REFRESH')
        action_row.operator("khb_prefs.force_cleanup", text="Cleanup", icon='TRASH')

# ==== OPERATORS ====
class KHB_PREFS_OT_reload_icons(bpy.types.Operator):
    bl_idname = "khb_prefs.reload_icons"
    bl_label = "Reload Icons"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            display_module = get_display_module()
            if display_module:
                display_module.khb_cleanup_icons()
                display_module.khb_load_icons()
                display_module.khb_force_redraw()
                self.report({'INFO'}, "Icons reloaded successfully")
            else:
                self.report({'ERROR'}, "Display module not available")
        except Exception as e:
            self.report({'ERROR'}, f"Reload error: {e}")
        return {'FINISHED'}

class KHB_PREFS_OT_force_cleanup(bpy.types.Operator):
    bl_idname = "khb_prefs.force_cleanup"
    bl_label = "Force Cleanup"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            display_module = get_display_module()
            if display_module:
                display_module.khb_disable_display_system()
                display_module.khb_cleanup_icons()
            
            # Nuclear cleanup
            import gc
            gc.collect()
            
            # Force redraw
            for area in context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            self.report({'INFO'}, "Force cleanup completed")
        except Exception as e:
            self.report({'ERROR'}, f"Cleanup error: {e}")
        return {'FINISHED'}

# ==== REGISTRATION ====
khb_addon_classes = (
    KHB_AddonPreferences,
    KHB_PREFS_OT_reload_icons,
    KHB_PREFS_OT_force_cleanup,
)

def register():
    """Register KeyHabit addon"""
    print("🚀 KeyHabit: Starting registration...")
    
    # Register addon classes
    for cls in khb_addon_classes:
        try:
            bpy.utils.register_class(cls)
            print(f"✅ KeyHabit: {cls.__name__} registered")
        except Exception as e:
            print(f"❌ KeyHabit: {cls.__name__} registration failed - {e}")
    
    # Register modules (only existing ones)
    existing_modules = []
    addon_dir = os.path.dirname(__file__)
    
    for module_name in ['KHB_Normal', 'KHB_Panel', 'KHB_Display']:
        module_file = os.path.join(addon_dir, f"{module_name}.py")
        if os.path.exists(module_file):
            existing_modules.append(module_name)
    
    for module_name in existing_modules:
        module = safe_import_module(module_name)
        if module and hasattr(module, 'register'):
            try:
                module.register()
                print(f"✅ KeyHabit: {module_name} registered")
            except Exception as e:
                print(f"❌ KeyHabit: {module_name} registration failed - {e}")
    
    print("🎯 KeyHabit: Registration complete!")

def unregister():
    """Unregister KeyHabit addon"""
    print("🛑 KeyHabit: Starting unregistration...")
    
    # Disable display first
    try:
        display_module = get_display_module()
        if display_module:
            display_module.khb_disable_display_system()
    except:
        pass
    
    # Unregister modules
    for module_name in ['KHB_Display', 'KHB_Panel', 'KHB_Normal']:
        if module_name in _khb_module_cache:
            module = _khb_module_cache[module_name]
            if hasattr(module, 'unregister'):
                try:
                    module.unregister()
                    print(f"✅ KeyHabit: {module_name} unregistered")
                except Exception as e:
                    print(f"⚠️ KeyHabit: {module_name} unregistration error - {e}")
    
    # Unregister classes
    for cls in reversed(khb_addon_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KeyHabit: {cls.__name__} unregistration error - {e}")
    
    # Clear cache
    _khb_module_cache.clear()
    
    print("👋 KeyHabit: Unregistration complete!")

if __name__ == "__main__":
    register()
