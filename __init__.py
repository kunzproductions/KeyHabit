bl_info = {
    "name": "KeyHabit",
    "author": "Nhen3D, Cursor AI",
    "version": (3, 0, 0),  # Updated to v3.0.0
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > KeyHabit",
    "description": "Lock Normal tools, modifier overlay, viewport displays, mesh analysis, bake set creator. Optimized for nSolve compatibility.",
    "category": "3D View",
}

# ========== MODULE RELOAD MECHANISM ==========
# Auto-reload modules khi addon được reload (fix issue với cached modules)
import sys
import importlib

# Lấy tên package của addon này
_addon_name = __name__

# Danh sách các sub-modules cần reload
_modules = [
    "KHB_Normal",
    "KHB_Display", 
    "KHB_Sync",
    "KHB_Analysis",
    "KHB_BakeSet",
    "KHB_Facemap"
]

# Reload tất cả modules nếu đã được import trước đó
if _addon_name in sys.modules:
    print(f"Reloading {_addon_name} modules...")
    for module_name in _modules:
        full_module_name = f"{_addon_name}.{module_name}"
        if full_module_name in sys.modules:
            print(f"  - Reloading {module_name}")
            importlib.reload(sys.modules[full_module_name])
    print(f"✓ {_addon_name} modules reloaded successfully")

# Import Blender modules
import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty

# Global reference to KHB_Display module
_khb_display_module = None

def update_modifier_overlay(self, context):
    """Callback function khi show_modifier_overlay thay đổi"""
    global _khb_display_module
    
    # Get module reference with lazy loading
    if _khb_display_module is None:
        try:
            # Try different import methods
            try:
                from . import KHB_Display
                _khb_display_module = KHB_Display
            except ImportError:
                # Fallback: try using importlib
                import importlib
                import sys
                module_name = f"{__name__}.KHB_Display"
                if module_name in sys.modules:
                    _khb_display_module = sys.modules[module_name]
                else:
                    _khb_display_module = importlib.import_module(module_name)
        except Exception as e:
            print(f"Error importing KHB_Display: {e}")
            return
    
    # Call functions
    try:
        if self.show_modifier_overlay:
            _khb_display_module.enable_modifier_overlay()
        else:
            _khb_display_module.disable_modifier_overlay()
    except Exception as e:
        print(f"Error calling overlay functions: {e}")

class KEYHABIT_Preferences(AddonPreferences):
    bl_idname = "KeyHabit"
    show_modifier_overlay: BoolProperty(
        name="Show Modifier Overlay",
        description="Enable modifier information overlay in viewport",
        default=False,
        update=update_modifier_overlay,
    )
    def draw(self, context):
        layout = self.layout
        layout.label(text="KeyHabit Add-on Settings")
        
        # Modifier Overlay Settings
        box = layout.box()
        box.label(text="Modifier Overlay", icon='MODIFIER')
        col = box.column(align=True)
        col.prop(self, "show_modifier_overlay")
        col.label(text="Show modifier information in viewport", icon='INFO')

from . import KHB_Normal, KHB_Display, KHB_Sync, KHB_Analysis, KHB_BakeSet, KHB_Facemap

# ========== PERSISTENT HANDLERS ==========
@bpy.app.handlers.persistent
def load_post_handler(dummy):
    """Handler được gọi sau khi load file .blend mới"""
    print("KeyHabit: File loaded, reinitializing addon...")
    
    # Reinitialize display module reference
    global _khb_display_module
    _khb_display_module = None
    
    # Reapply preferences nếu có
    try:
        prefs = bpy.context.preferences.addons.get("KeyHabit")
        if prefs and hasattr(prefs.preferences, 'show_modifier_overlay'):
            if prefs.preferences.show_modifier_overlay:
                # Re-enable overlay nếu nó đã được bật
                update_modifier_overlay(prefs.preferences, bpy.context)
    except Exception as e:
        print(f"KeyHabit: Warning during post-load init: {e}")

def register():
    print("KeyHabit: Registering addon...")
    
    # Register classes
    bpy.utils.register_class(KEYHABIT_Preferences)
    KHB_Normal.register()
    KHB_Analysis.register()
    KHB_Display.register()
    KHB_Sync.register()
    KHB_BakeSet.register()
    KHB_Facemap.register()
    
    # Initialize global variable (lazy loading will happen in callback)
    global _khb_display_module
    _khb_display_module = None
    
    # Register persistent handler
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)
    
    print("✓ KeyHabit registered successfully")

def unregister():
    print("KeyHabit: Unregistering addon...")
    
    # Remove persistent handler
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    
    # Disable modifier overlay trước khi unregister
    global _khb_display_module
    try:
        if _khb_display_module is not None:
            _khb_display_module.disable_modifier_overlay()
    except Exception:
        pass
    
    # Unregister các modules (wrap trong try-except để tránh lỗi)
    try:
        KHB_Facemap.unregister()
    except Exception as e:
        print(f"Error unregistering KHB_Facemap: {e}")
    
    try:
        KHB_BakeSet.unregister()
    except Exception as e:
        print(f"Error unregistering KHB_BakeSet: {e}")
    
    try:
        KHB_Sync.unregister()
    except Exception as e:
        print(f"Error unregistering KHB_Sync: {e}")
    
    try:
        KHB_Display.unregister()
    except Exception as e:
        print(f"Error unregistering KHB_Display: {e}")
    
    try:
        KHB_Analysis.unregister()
    except Exception as e:
        print(f"Error unregistering KHB_Analysis: {e}")
    
    try:
        KHB_Normal.unregister()
    except Exception as e:
        print(f"Error unregistering KHB_Normal: {e}")
    
    try:
        bpy.utils.unregister_class(KEYHABIT_Preferences)
    except Exception as e:
        print(f"Error unregistering KEYHABIT_Preferences: {e}")
    
    # Clear global reference
    _khb_display_module = None
    
    print("✓ KeyHabit unregistered successfully")
