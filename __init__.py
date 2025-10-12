"""
KeyHabit Addon - Advanced Blender Tools
Version: 2.0.1-optimized
Author: MinThuan
"""

bl_info = {
    "name": "KeyHabit",
    "author": "MinThuan", 
    "version": (2, 0, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > KeyHabit",
    "description": "Advanced tools for 3D modeling workflow with modifier overlay display",
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

# ==== MODULE CACHE (Prevent import loops) ====
_khb_module_cache = {}

def get_display_module():
    """Get KHB_Display module with caching"""
    if 'KHB_Display' not in _khb_module_cache:
        try:
            module_name = f'{__name__}.KHB_Display'
            if module_name in sys.modules:
                module = sys.modules[module_name]
            else:
                module = importlib.import_module('.KHB_Display', package=__name__)
            
            _khb_module_cache['KHB_Display'] = module
            return module
        except ImportError as e:
            print(f"❌ KeyHabit: Cannot import KHB_Display - {e}")
            return None
        except Exception as e:
            print(f"❌ KeyHabit: KHB_Display import error - {e}")
            return None
    
    return _khb_module_cache['KHB_Display']

def reload_display_module():
    """Force reload display module"""
    try:
        module_name = f'{__name__}.KHB_Display'
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        
        # Clear cache to force fresh import
        _khb_module_cache.pop('KHB_Display', None)
        module = get_display_module()
        
        print("✅ KeyHabit: KHB_Display reloaded successfully")
        return module
    except Exception as e:
        print(f"❌ KeyHabit: Reload failed - {e}")
        return None

# ==== ADDON PREFERENCES ====
class KHB_AddonPreferences(AddonPreferences):
    """KeyHabit Addon Preferences with display system controls"""
    bl_idname = __name__
    
    # === DISPLAY SYSTEM PROPERTIES ===
    khb_enable_display_system: BoolProperty(
        name="Enable Display System",
        description="Enable real-time modifier overlay display with icons and controls",
        default=False,
        update=lambda self, context: self._update_display_system()
    )
    
    khb_icon_size: IntProperty(
        name="Icon Size",
        description="Size of modifier icons in pixels", 
        default=16,
        min=12,
        max=24,
        update=lambda self, context: self._update_display_settings()
    )
    
    khb_line_height: IntProperty(
        name="Line Height",
        description="Vertical spacing between modifier lines",
        default=18,
        min=14,
        max=28,
        update=lambda self, context: self._update_display_settings()
    )
    
    khb_show_buttons: BoolProperty(
        name="Show Control Buttons",
        description="Display interactive overlay control buttons (W/E/R/S)",
        default=True,
        update=lambda self, context: self._update_display_settings()
    )
    
    khb_button_position: EnumProperty(
        name="Button Position",
        description="Position of control buttons in viewport",
        items=[
            ('BOTTOM_LEFT', "Bottom Left", "Position at bottom left"),
            ('BOTTOM_RIGHT', "Bottom Right", "Position at bottom right"),
            ('TOP_LEFT', "Top Left", "Position at top left"),
            ('TOP_RIGHT', "Top Right", "Position at top right"),
        ],
        default='BOTTOM_LEFT',
        update=lambda self, context: self._update_display_settings()
    )
    
    khb_use_png_icons: BoolProperty(
        name="Use PNG Icons",
        description="Try to load PNG icons from icons/ folder (fallback to text if unavailable)",
        default=True,
        update=lambda self, context: self._update_display_settings()
    )
    
    # === INTERNAL METHODS ===
    def _update_display_system(self):
        """Toggle display system on/off"""
        display_module = get_display_module()
        if not display_module:
            self.khb_enable_display_system = False
            return
        
        try:
            if self.khb_enable_display_system:
                # Apply current settings
                self._apply_settings_to_module(display_module)
                # Enable system
                display_module.khb_enable_display_system()
                print("✅ KHB: Display System Enabled")
            else:
                # Disable system
                display_module.khb_disable_display_system()
                print("❌ KHB: Display System Disabled")
        except Exception as e:
            print(f"❌ KHB: Display toggle failed - {e}")
            self.khb_enable_display_system = False
    
    def _update_display_settings(self):
        """Update display settings if system is enabled"""
        if not self.khb_enable_display_system:
            return
        
        display_module = get_display_module()
        if display_module:
            self._apply_settings_to_module(display_module)
    
    def _apply_settings_to_module(self, display_module):
        """Apply preference settings to display module"""
        try:
            # Update global constants
            if hasattr(display_module, 'KHB_ICON_SIZE_PX'):
                display_module.KHB_ICON_SIZE_PX = self.khb_icon_size
            if hasattr(display_module, 'KHB_LINE_HEIGHT'):
                display_module.KHB_LINE_HEIGHT = self.khb_line_height
            
            # Update button settings
            if hasattr(display_module, 'khb_update_button_settings'):
                display_module.khb_update_button_settings({
                    'show_buttons': self.khb_show_buttons,
                    'position': self.khb_button_position
                })
            
            # Update icon settings
            if hasattr(display_module, 'khb_update_icon_settings'):
                display_module.khb_update_icon_settings({
                    'use_png': self.khb_use_png_icons
                })
            
            # Force redraw
            if hasattr(display_module, 'khb_force_redraw'):
                display_module.khb_force_redraw()
                
        except Exception as e:
            print(f"⚠️ KHB: Settings apply failed - {e}")
    
    # === UI DRAWING ===
    def draw(self, context):
        """Draw addon preferences UI"""
        layout = self.layout
        display_module = get_display_module()
        
        # === HEADER ===
        header_box = layout.box()
        header_row = header_box.row()
        header_row.label(text="🎨 KeyHabit Display System", icon='OVERLAY')
        
        if hasattr(display_module, 'KHB_DISPLAY_VERSION'):
            header_row.label(text=f"v{display_module.KHB_DISPLAY_VERSION}")
        
        # === MODULE STATUS CHECK ===
        if not display_module:
            self._draw_error_state(layout)
            return
        
        # === MAIN CONTROLS ===
        main_box = layout.box()
        col = main_box.column()
        
        # System toggle
        toggle_row = col.row()
        toggle_row.scale_y = 1.3
        
        if self.khb_enable_display_system:
            toggle_row.prop(self, "khb_enable_display_system", 
                          text="🟢 Display System Active", toggle=True)
            
            # Active status
            status_row = col.row()
            status_row.label(text="● Status: RUNNING", icon='CHECKMARK')
            
            # Settings when enabled
            self._draw_display_settings(col)
            
        else:
            toggle_row.prop(self, "khb_enable_display_system", 
                          text="⚫ Enable Display System", toggle=True)
            
            # Inactive status
            status_row = col.row()
            status_row.label(text="○ Status: DISABLED", icon='CANCEL')
        
        # === MODULE INFO ===
        self._draw_module_info(layout, display_module)
        
        # === QUICK ACTIONS ===
        self._draw_quick_actions(layout)
    
    def _draw_error_state(self, layout):
        """Draw error state when module is not available"""
        error_box = layout.box()
        error_col = error_box.column()
        error_col.alert = True
        error_col.label(text="⚠️ KHB_Display Module Not Found", icon='ERROR')
        error_col.label(text="The display system module is missing or failed to load")
        
        # Debug info
        debug_box = layout.box()
        debug_col = debug_box.column()
        debug_col.label(text="Troubleshooting:", icon='CONSOLE')
        
        try:
            addon_dir = Path(__file__).parent
            khb_display_path = addon_dir / "KHB_Display.py"
            
            if khb_display_path.exists():
                debug_col.label(text="✓ KHB_Display.py file exists")
                debug_col.label(text="✗ Module import failed (check console for errors)")
            else:
                debug_col.label(text="✗ KHB_Display.py file missing")
                debug_col.label(text="Please ensure the file is in the addon folder")
                
        except Exception:
            debug_col.label(text="Cannot read addon directory")
    
    def _draw_display_settings(self, col):
        """Draw display settings when system is enabled"""
        col.separator()
        
        # Display settings
        display_box = col.box()
        display_col = display_box.column()
        display_col.label(text="Display Settings:", icon='SETTINGS')
        
        settings_row = display_col.row(align=True)
        settings_row.prop(self, "khb_icon_size")
        settings_row.prop(self, "khb_line_height")
        
        display_col.prop(self, "khb_use_png_icons")
        
        # Button settings
        button_box = col.box()
        button_col = button_box.column()
        button_col.label(text="Control Buttons:", icon='PREFERENCES')
        
        button_col.prop(self, "khb_show_buttons")
        if self.khb_show_buttons:
            button_col.prop(self, "khb_button_position", text="Position")
    
    def _draw_module_info(self, layout, display_module):
        """Draw module information"""
        info_box = layout.box()
        info_col = info_box.column()
        info_col.label(text="System Information:", icon='INFO')
        
        # Version info
        if hasattr(display_module, 'KHB_DISPLAY_VERSION'):
            info_col.label(text=f"Display Engine: {display_module.KHB_DISPLAY_VERSION}")
        
        # Icon count
        if hasattr(display_module, 'KHB_MODIFIER_ICONS'):
            icon_count = len(display_module.KHB_MODIFIER_ICONS)
            info_col.label(text=f"Supported Modifiers: {icon_count}")
        
        # System status
        if hasattr(display_module, 'khb_is_enabled'):
            is_active = display_module.khb_is_enabled()
            status_text = "Active" if is_active else "Inactive"
            info_col.label(text=f"Engine Status: {status_text}")
    
    def _draw_quick_actions(self, layout):
        """Draw quick action buttons"""
        actions_box = layout.box()
        actions_col = actions_box.column()
        actions_col.label(text="Quick Actions:", icon='TOOL_SETTINGS')
        
        actions_row = actions_col.row(align=True)
        actions_row.operator("khb_prefs.reload_module", text="Reload Module", icon='FILE_REFRESH')
        actions_row.operator("khb_prefs.reload_icons", text="Reload Icons", icon='IMAGE_DATA')
        actions_row.operator("khb_prefs.force_cleanup", text="Emergency Cleanup", icon='TRASH')

# ==== PREFERENCE OPERATORS ====
class KHB_PREFS_OT_reload_module(bpy.types.Operator):
    """Reload KHB_Display module"""
    bl_idname = "khb_prefs.reload_module"
    bl_label = "Reload Module"
    bl_description = "Reload the display system module (useful during development)"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            # Get current state
            prefs = context.preferences.addons[__name__].preferences
            was_enabled = prefs.khb_enable_display_system
            
            # Disable if currently enabled
            if was_enabled:
                prefs.khb_enable_display_system = False
            
            # Reload module
            module = reload_display_module()
            if module:
                # Re-enable if it was enabled
                if was_enabled:
                    prefs.khb_enable_display_system = True
                
                self.report({'INFO'}, "Display module reloaded successfully")
            else:
                self.report({'ERROR'}, "Module reload failed")
                
        except Exception as e:
            self.report({'ERROR'}, f"Reload error: {e}")
        
        return {'FINISHED'}

class KHB_PREFS_OT_reload_icons(bpy.types.Operator):
    """Reload PNG icons"""
    bl_idname = "khb_prefs.reload_icons"
    bl_label = "Reload Icons"
    bl_description = "Reload all PNG icons from the icons folder"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            display_module = get_display_module()
            if not display_module:
                self.report({'ERROR'}, "Display module not available")
                return {'CANCELLED'}
            
            # Reload icons
            if hasattr(display_module, 'khb_reload_icons'):
                success = display_module.khb_reload_icons()
                if success:
                    self.report({'INFO'}, "Icons reloaded successfully")
                    display_module.khb_force_redraw()
                else:
                    self.report({'WARNING'}, "Icon reload completed with warnings")
            else:
                self.report({'ERROR'}, "Icon reload function not available")
                
        except Exception as e:
            self.report({'ERROR'}, f"Icon reload error: {e}")
        
        return {'FINISHED'}

class KHB_PREFS_OT_force_cleanup(bpy.types.Operator):
    """Emergency cleanup of all resources"""
    bl_idname = "khb_prefs.force_cleanup"
    bl_label = "Emergency Cleanup"
    bl_description = "Force cleanup all display system resources (use if system becomes unresponsive)"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            # Disable display system
            display_module = get_display_module()
            if display_module and hasattr(display_module, 'khb_emergency_cleanup'):
                display_module.khb_emergency_cleanup()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Force viewport redraw
            for area in context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            # Reset preferences
            prefs = context.preferences.addons[__name__].preferences
            prefs.khb_enable_display_system = False
            
            self.report({'INFO'}, "Emergency cleanup completed")
            
        except Exception as e:
            self.report({'ERROR'}, f"Cleanup error: {e}")
        
        return {'FINISHED'}

# ==== REGISTRATION ====
khb_classes = (
    KHB_AddonPreferences,
    KHB_PREFS_OT_reload_module,
    KHB_PREFS_OT_reload_icons,
    KHB_PREFS_OT_force_cleanup,
)

def register():
    """Register KeyHabit addon"""
    print("🚀 KeyHabit: Starting registration...")
    
    # Register addon classes
    for cls in khb_classes:
        try:
            bpy.utils.register_class(cls)
            print(f"✅ KeyHabit: {cls.__name__} registered")
        except Exception as e:
            print(f"❌ KeyHabit: {cls.__name__} registration failed - {e}")
    
    # Register KHB_Display module
    display_module = get_display_module()
    if display_module and hasattr(display_module, 'register'):
        try:
            display_module.register()
            print("✅ KeyHabit: KHB_Display registered")
        except Exception as e:
            print(f"❌ KeyHabit: KHB_Display registration failed - {e}")
    
    print("🎯 KeyHabit: Registration complete!")
    print("💡 Access Display System: Edit > Preferences > Add-ons > KeyHabit")

def unregister():
    """Unregister KeyHabit addon"""
    print("🛑 KeyHabit: Starting unregistration...")
    
    # Unregister KHB_Display module first
    display_module = get_display_module()
    if display_module and hasattr(display_module, 'unregister'):
        try:
            display_module.unregister()
            print("✅ KeyHabit: KHB_Display unregistered")
        except Exception as e:
            print(f"⚠️ KeyHabit: KHB_Display unregistration error - {e}")
    
    # Unregister addon classes
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
