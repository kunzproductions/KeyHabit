"""
KeyHabit Addon - Advanced Blender Tools
Version: 2.1.0-gizmo
Author: MinThuan
"""

bl_info = {
    "name": "KeyHabit",
    "author": "MinThuan", 
    "version": (2, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > KeyHabit",
    "description": "Advanced tools for 3D modeling with Gizmo button system and modifier display",
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
from pathlib import Path

# ==== MODULE IMPORTS & CACHING ====
_khb_module_cache = {}

def _get_module(module_name):
    """Generic module getter with caching"""
    if module_name not in _khb_module_cache:
        try:
            full_module_name = f'{__name__}.{module_name}'
            if full_module_name in sys.modules:
                module = sys.modules[full_module_name]
            else:
                module = importlib.import_module(f'.{module_name}', package=__name__)
            
            _khb_module_cache[module_name] = module
            return module
        except ImportError as e:
            print(f"❌ KeyHabit: Cannot import {module_name} - {e}")
            return None
        except Exception as e:
            print(f"❌ KeyHabit: {module_name} import error - {e}")
            return None
    
    return _khb_module_cache[module_name]

def _reload_module(module_name):
    """Generic module reloader"""
    try:
        full_module_name = f'{__name__}.{module_name}'
        if full_module_name in sys.modules:
            importlib.reload(sys.modules[full_module_name])
        
        # Clear cache to force fresh import
        _khb_module_cache.pop(module_name, None)
        module = _get_module(module_name)
        
        print(f"✅ KeyHabit: {module_name} reloaded successfully")
        return module
    except Exception as e:
        print(f"❌ KeyHabit: Reload failed for {module_name} - {e}")
        return None

# Getter functions for specific modules
def get_display_module():
    return _get_module('KHB_Display')

def get_button_module():
    return _get_module('KHB_Button')

def reload_display_module():
    return _reload_module('KHB_Display')
    
def reload_button_module():
    return _reload_module('KHB_Button')

# ==== ADDON PREFERENCES ====
class KHB_AddonPreferences(AddonPreferences):
    """KeyHabit Addon Preferences with integrated system controls"""
    bl_idname = __name__
    
    # --- DISPLAY SYSTEM PROPERTIES ---
    khb_enable_display_system: BoolProperty(
        name="Enable Display System",
        description="Enable real-time modifier overlay display",
        default=False,
        update=lambda self, context: self._update_display_system()
    )
    
    # --- BUTTON SYSTEM PROPERTIES ---
    khb_enable_button_system: BoolProperty(
        name="Enable Button System",
        description="Enable advanced gizmo button system",
        default=False,
        update=lambda self, context: self._update_button_system()
    )
    
    # --- INTERNAL METHODS ---
    def _update_display_system(self):
        """Toggle display system on/off"""
        display_module = get_display_module()
        if not display_module:
            self.khb_enable_display_system = False
            return
        
        try:
            if self.khb_enable_display_system:
                if hasattr(display_module, 'khb_enable_display_system'):
                    display_module.khb_enable_display_system()
                    print("✅ KHB: Display System Enabled")
            else:
                if hasattr(display_module, 'khb_disable_display_system'):
                    display_module.khb_disable_display_system()
                    print("❌ KHB: Display System Disabled")
        except Exception as e:
            print(f"❌ KHB: Display toggle failed - {e}")
            self.khb_enable_display_system = False
    
    def _update_button_system(self):
        """Toggle button system on/off"""
        button_module = get_button_module()
        if not button_module:
            self.khb_enable_button_system = False
            return
        
        try:
            # The button system uses a property on the Scene, so we just need to update it
            if hasattr(bpy.types.Scene, 'khb_button_system_enabled'):
                bpy.context.scene.khb_button_system_enabled = self.khb_enable_button_system
                
                status = "Enabled" if self.khb_enable_button_system else "Disabled"
                print(f"✅ KHB: Button System {status}")
            else:
                # This case happens if the button module didn't register its properties
                print(f"⚠️ KHB: Button system property not found!")
                self.khb_enable_button_system = False
                
        except Exception as e:
            print(f"❌ KHB: Button toggle failed - {e}")
            self.khb_enable_button_system = False

    # --- UI DRAWING ---
    def draw(self, context):
        """Draw addon preferences UI"""
        layout = self.layout
        
        # === HEADER ===
        header_box = layout.box()
        header_row = header_box.row()
        header_row.label(text="KeyHabit Systems Control", icon='TOOL_SETTINGS')
        
        # === DISPLAY SYSTEM CONTROL ===
        display_box = layout.box()
        display_col = display_box.column()
        display_col.label(text="🎨 Modifier Display System", icon='OVERLAY')
        
        display_module = get_display_module()
        if not display_module:
            display_col.alert = True
            display_col.label(text="⚠️ Module Not Found", icon='ERROR')
        else:
            display_col.prop(self, "khb_enable_display_system", 
                           text="Enable Modifier Display", toggle=True)
            if self.khb_enable_display_system:
                display_col.label(text="Status: Active", icon='CHECKMARK')
        
        # === BUTTON SYSTEM CONTROL ===
        button_box = layout.box()
        button_col = button_box.column()
        button_col.label(text="🎯 Gizmo Button System", icon='GIZMO')
        
        button_module = get_button_module()
        if not button_module:
            button_col.alert = True
            button_col.label(text="⚠️ Module Not Found", icon='ERROR')
        else:
            button_col.prop(self, "khb_enable_button_system", 
                          text="Enable Gizmo Buttons", toggle=True)
            if self.khb_enable_button_system:
                button_col.label(text="Status: Active", icon='CHECKMARK')
        
        # === QUICK ACTIONS ===
        self._draw_quick_actions(layout)

    def _draw_quick_actions(self, layout):
        """Draw quick action buttons"""
        actions_box = layout.box()
        actions_col = actions_box.column()
        actions_col.label(text="Development Actions:", icon='CONSOLE')
        
        actions_row = actions_col.row(align=True)
        actions_row.operator("khb_prefs.reload_all_modules", text="Reload All Modules", icon='FILE_REFRESH')
        actions_row.operator("khb_prefs.force_cleanup", text="Emergency Cleanup", icon='TRASH')

# ==== PREFERENCE OPERATORS ====
class KHB_PREFS_OT_reload_all_modules(bpy.types.Operator):
    """Reload all KeyHabit modules"""
    bl_idname = "khb_prefs.reload_all_modules"
    bl_label = "Reload All Modules"
    bl_description = "Reload all KeyHabit modules (for development)"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            prefs = context.preferences.addons[__name__].preferences
            
            # Store original states
            display_was_enabled = prefs.khb_enable_display_system
            button_was_enabled = prefs.khb_enable_button_system
            
            # Disable systems before reload
            if display_was_enabled: prefs.khb_enable_display_system = False
            if button_was_enabled: prefs.khb_enable_button_system = False
            
            # Unregister modules if they exist
            if 'KHB_Button' in sys.modules:
                button_module = get_button_module()
                if button_module and hasattr(button_module, 'unregister'):
                    button_module.unregister()
            
            if 'KHB_Display' in sys.modules:
                display_module = get_display_module()
                if display_module and hasattr(display_module, 'unregister'):
                    display_module.unregister()

            # Reload modules
            reload_display_module()
            reload_button_module()

            # Reregister modules
            if 'KHB_Display' in sys.modules:
                display_module = get_display_module()
                if display_module and hasattr(display_module, 'register'):
                    display_module.register()
            
            if 'KHB_Button' in sys.modules:
                button_module = get_button_module()
                if button_module and hasattr(button_module, 'register'):
                    button_module.register()

            # Restore states
            if display_was_enabled: prefs.khb_enable_display_system = True
            if button_was_enabled: prefs.khb_enable_button_system = True
            
            self.report({'INFO'}, "All modules reloaded successfully")
            
        except Exception as e:
            self.report({'ERROR'}, f"Reload error: {e}")
        
        return {'FINISHED'}

class KHB_PREFS_OT_force_cleanup(bpy.types.Operator):
    """Emergency cleanup of all resources"""
    bl_idname = "khb_prefs.force_cleanup"
    bl_label = "Emergency Cleanup"
    bl_description = "Force cleanup all KeyHabit resources"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            # Cleanup display system
            display_module = get_display_module()
            if display_module and hasattr(display_module, 'khb_emergency_cleanup'):
                display_module.khb_emergency_cleanup()
            
            # Cleanup button system (by unregistering)
            button_module = get_button_module()
            if button_module and hasattr(button_module, 'unregister'):
                button_module.unregister()
            
            # Reset preferences
            prefs = context.preferences.addons[__name__].preferences
            prefs.khb_enable_display_system = False
            prefs.khb_enable_button_system = False
            
            self.report({'INFO'}, "Emergency cleanup completed")
            
        except Exception as e:
            self.report({'ERROR'}, f"Cleanup error: {e}")
        
        return {'FINISHED'}

# ==== REGISTRATION ====
khb_classes = (
    KHB_AddonPreferences,
    KHB_PREFS_OT_reload_all_modules,
    KHB_PREFS_OT_force_cleanup,
)

# List of modules to register
khb_modules = [
    'KHB_Display',
    'KHB_Button'  # New module
]

def register():
    """Register KeyHabit addon and all its modules"""
    print("🚀 KeyHabit: Starting registration...")
    
    # Register main addon classes
    for cls in khb_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"❌ KeyHabit: {cls.__name__} registration failed - {e}")
    
    # Register sub-modules
    for module_name in khb_modules:
        module = _get_module(module_name)
        if module and hasattr(module, 'register'):
            try:
                module.register()
                print(f"✅ KeyHabit: {module_name} registered")
            except Exception as e:
                print(f"❌ KeyHabit: {module_name} registration failed - {e}")
        elif not module:
             print(f"⚠️ KeyHabit: {module_name} not found, skipping registration.")
    
    print("🎯 KeyHabit: Registration complete!")
    print("💡 Access Settings: Edit > Preferences > Add-ons > KeyHabit")

def unregister():
    """Unregister KeyHabit addon and all its modules"""
    print("🛑 KeyHabit: Starting unregistration...")
    
    # Unregister sub-modules in reverse order
    for module_name in reversed(khb_modules):
        module = _get_module(module_name)
        if module and hasattr(module, 'unregister'):
            try:
                module.unregister()
                print(f"✅ KeyHabit: {module_name} unregistered")
            except Exception as e:
                print(f"⚠️ KeyHabit: {module_name} unregistration error - {e}")
    
    # Unregister main addon classes
    for cls in reversed(khb_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"⚠️ KeyHabit: {cls.__name__} unregistration error - {e}")
    
    # Clear module cache
    _khb_module_cache.clear()
    
    print("👋 KeyHabit: Unregistration complete!")

if __name__ == "__main__":
    register()

