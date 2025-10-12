# ==== BUTTON SYSTEM (ENHANCED WITH ICONS) ====
# Button icon mapping
KHB_BUTTON_ICONS = {
    'wireframe': 'blender_icon_overlay_wireframe.png',
    'edge_length': 'blender_icon_overlay_edge_length.png', 
    'retopo': 'blender_icon_overlay_retopo.png',
    'split_normals': 'blender_icon_overlay_normals.png'
}

def khb_init_buttons():
    """Initialize control buttons with icons and full names"""
    global _khb_state
    
    if not _khb_state['settings']['show_buttons']:
        _khb_state['buttons'] = []
        return
    
    # Button configuration with full names
    buttons_config = [
        {
            'id': 'wireframe', 
            'label': 'Wireframe', 
            'icon_name': 'wireframe',
            'tooltip': 'Toggle Wireframe Overlay (Show mesh edges)'
        },
        {
            'id': 'edge_length', 
            'label': 'Edge Length', 
            'icon_name': 'edge_length',
            'tooltip': 'Toggle Edge Length Display (Show edge measurements)'
        },
        {
            'id': 'retopo', 
            'label': 'Retopology', 
            'icon_name': 'retopo',
            'tooltip': 'Toggle Retopology Overlay (Show through geometry)'
        },
        {
            'id': 'split_normals', 
            'label': 'Split Normals', 
            'icon_name': 'split_normals',
            'tooltip': 'Toggle Split Normals Display (Show vertex normals)'
        }
    ]
    
    # Calculate positions based on settings
    position = _khb_state['settings']['position']
    if position == 'BOTTOM_LEFT':
        start_x, start_y = 60, 40
    elif position == 'BOTTOM_RIGHT':
        start_x, start_y = 300, 40
    elif position == 'TOP_LEFT':
        start_x, start_y = 60, 200
    else:  # TOP_RIGHT
        start_x, start_y = 300, 200
    
    # Create button data with proper sizing for icon + text
    _khb_state['buttons'] = []
    x = start_x
    
    for config in buttons_config:
        # Calculate button width based on text length
        button_width = max(80, len(config['label']) * 8 + 30)  # Min 80px, scale with text
        
        _khb_state['buttons'].append({
            'id': config['id'],
            'label': config['label'],
            'icon_name': config['icon_name'], 
            'tooltip': config['tooltip'],
            'x': x,
            'y': start_y,
            'width': button_width,
            'height': KHB_BUTTON_SIZE
        })
        x += button_width + 12  # 12px spacing between buttons
    
    if _khb_state['buttons']:
        print(f"🎮 KHB_Display: {len(_khb_state['buttons'])} icon buttons initialized at {position}")

def khb_get_button_icon_texture(icon_name):
    """Get texture for button icon (with fallback to question mark)"""
    global _khb_state
    
    if not _khb_state['pcoll'] or not _khb_state['settings']['use_png']:
        return None
    
    # Try to get specific button icon
    icon_filename = KHB_BUTTON_ICONS.get(icon_name)
    if icon_filename:
        preview = _khb_state['pcoll'].get(icon_name)
        if preview:
            return khb_create_texture_from_preview(preview)
    
    # Fallback to question mark icon
    fallback = _khb_state['pcoll'].get("FALLBACK")
    if fallback:
        return khb_create_texture_from_preview(fallback)
    
    return None

def khb_create_texture_from_preview(preview):
    """Create GPU texture from preview (helper function)"""
    if not preview or not hasattr(preview, 'icon_pixels_float'):
        return None
    
    try:
        icon_data = preview.icon_pixels_float
        if not icon_data:
            return None
        
        # Calculate icon dimensions
        data_size = len(icon_data)
        pixels_count = data_size // 4  # RGBA
        icon_size = int(pixels_count ** 0.5)
        
        if icon_size > 0 and icon_size * icon_size * 4 == data_size:
            # Convert to proper GPU buffer
            import numpy as np
            pixels = np.array(icon_data, dtype=np.float32).reshape((icon_size, icon_size, 4))
            buffer_data = gpu.types.Buffer('FLOAT', (icon_size, icon_size, 4), pixels)
            texture = gpu.types.GPUTexture((icon_size, icon_size), format='RGBA8', data=buffer_data)
            return texture
            
    except Exception:
        pass
    
    return None

def khb_draw_buttons():
    """Draw control buttons with icons and full text labels"""
    global _khb_state
    
    if not _khb_state['buttons']:
        return
    
    font_id = 0
    blf.size(font_id, 11)
    colors = KHB_Colors()
    
    for btn in _khb_state['buttons']:
        x, y = btn['x'], btn['y'] 
        width, height = btn['width'], btn['height']
        is_active = khb_get_overlay_state(btn['id'])
        
        # Choose colors
        if is_active:
            bg_color = colors.BUTTON_ACTIVE  # Bright green
            text_color = colors.BUTTON_TEXT
            border_color = (1.0, 1.0, 1.0, 1.0)  # White border
        else:
            bg_color = colors.BUTTON_INACTIVE  # Dark gray
            text_color = (0.8, 0.8, 0.8, 1.0)   # Gray text
            border_color = (0.6, 0.6, 0.6, 0.8)  # Gray border
        
        try:
            # Draw button background
            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            positions = [(x, y), (x+width, y), (x+width, y+height), (x, y+height)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": positions})
            
            gpu.state.blend_set('ALPHA')
            shader.bind()
            shader.uniform_float("color", bg_color)
            batch.draw(shader)
            
            # Draw border
            border_positions = [
                (x-1, y-1), (x+width+1, y-1), 
                (x+width+1, y+height+1), (x-1, y+height+1), (x-1, y-1)
            ]
            border_batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": border_positions})
            shader.uniform_float("color", border_color)
            border_batch.draw(shader)
            
            gpu.state.blend_set('NONE')
            
            # Draw button icon (left side)
            icon_size = 16
            icon_x = x + 6  # 6px padding from left
            icon_y = y + (height - icon_size) // 2  # Center vertically
            
            # Try to draw PNG icon
            texture = khb_get_button_icon_texture(btn['icon_name'])
            if texture:
                try:
                    # Draw PNG icon
                    icon_positions = [
                        (icon_x, icon_y), (icon_x+icon_size, icon_y), 
                        (icon_x+icon_size, icon_y+icon_size), (icon_x, icon_y+icon_size)
                    ]
                    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
                    
                    icon_shader = gpu.shader.from_builtin('IMAGE')
                    icon_batch = batch_for_shader(icon_shader, 'TRI_FAN', {"pos": icon_positions, "texCoord": uvs})
                    
                    gpu.state.blend_set('ALPHA')
                    icon_shader.bind()
                    icon_shader.uniform_sampler("image", texture)
                    icon_batch.draw(icon_shader)
                    gpu.state.blend_set('NONE')
                    
                except Exception:
                    # Fallback to question mark text
                    blf.position(font_id, icon_x, icon_y, 0)
                    blf.color(font_id, 1.0, 0.7, 0.0, 1.0)  # Orange
                    blf.draw(font_id, "?")
            else:
                # Fallback: Draw question mark
                blf.size(font_id, icon_size - 2)
                blf.position(font_id, icon_x, icon_y, 0)
                blf.color(font_id, 1.0, 0.7, 0.0, 1.0)  # Orange
                blf.draw(font_id, "?")
            
            # Draw button text label (right side)
            blf.size(font_id, 11)  # Reset font size
            text_x = icon_x + icon_size + 6  # 6px padding after icon
            text_y = y + (height // 2) - 6  # Center vertically
            
            blf.position(font_id, text_x, text_y, 0)
            blf.color(font_id, *text_color)
            blf.draw(font_id, btn['label'])
            
        except Exception as e:
            print(f"⚠️ KHB_Display: Button draw error for {btn['id']}: {e}")

def khb_handle_click(mouse_x, mouse_y):
    """Handle button clicks with enhanced hit detection"""
    global _khb_state
    
    current_time = time.time()
    if current_time - _khb_state['last_click_time'] < 0.2:  # 200ms debounce
        return False
    
    for btn in _khb_state['buttons']:
        x, y = btn['x'], btn['y']
        width, height = btn['width'], btn['height']
        
        # Enhanced hit test for wider buttons
        if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
            try:
                # Toggle overlay directly
                success = False
                for area in bpy.context.window.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                overlay = space.overlay
                                
                                if btn['id'] == 'wireframe':
                                    overlay.show_wireframes = not overlay.show_wireframes
                                    success = True
                                elif btn['id'] == 'edge_length':
                                    overlay.show_extra_edge_length = not overlay.show_extra_edge_length
                                    success = True
                                elif btn['id'] == 'retopo':
                                    overlay.show_retopology = not overlay.show_retopology
                                    success = True
                                elif btn['id'] == 'split_normals':
                                    overlay.show_split_normals = not overlay.show_split_normals
                                    success = True
                                
                                if success:
                                    area.tag_redraw()
                                    _khb_state['last_click_time'] = current_time
                                    print(f"🎯 KHB_Display: '{btn['label']}' button clicked")
                                    return True
                                
            except Exception as e:
                print(f"⚠️ KHB_Display: Button click error for {btn['id']}: {e}")
    
    return False

# ==== ENHANCED ICON LOADING (Add button icons to regular loading) ====
def khb_load_icons():
    """Load PNG icons including button icons"""
    global _khb_state
    
    if _khb_state['icons_loaded'] or not _khb_state['settings']['use_png']:
        return True
    
    try:
        # Clean up existing collection
        khb_cleanup_icons()
        
        # Create new preview collection
        pcoll = bpy.utils.previews.new()
        
        # Get icons directory
        addon_dir = Path(__file__).parent
        icons_dir = addon_dir / "icons"
        
        if not icons_dir.exists():
            print(f"⚠️ KHB_Display: Icons directory not found, using fallbacks")
            bpy.utils.previews.remove(pcoll)
            return False
        
        loaded_count = 0
        
        # Load fallback icon (question mark)
        fallback_path = icons_dir / KHB_FALLBACK_ICON
        if fallback_path.exists():
            pcoll.load("FALLBACK", str(fallback_path), 'IMAGE')
            loaded_count += 1
            print("✅ KHB_Display: Loaded fallback icon (question mark)")
        
        # Load modifier icons
        for mod_type, filename in KHB_MODIFIER_ICONS.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                try:
                    pcoll.load(mod_type, str(icon_path), 'IMAGE')
                    loaded_count += 1
                except Exception:
                    pass
        
        # Load button icons
        for button_id, filename in KHB_BUTTON_ICONS.items():
            icon_path = icons_dir / filename
            if icon_path.exists():
                try:
                    pcoll.load(button_id, str(icon_path), 'IMAGE')
                    loaded_count += 1
                    print(f"✅ KHB_Display: Loaded button icon: {button_id}")
                except Exception:
                    print(f"⚠️ KHB_Display: Failed to load button icon: {filename}")
        
        _khb_state['pcoll'] = pcoll
        _khb_state['icons_loaded'] = True
        
        print(f"🎨 KHB_Display: Icon system initialized ({loaded_count} total icons loaded)")
        print("📝 KHB_Display: Button icons will fallback to question mark if not found")
        return True
        
    except Exception as e:
        print(f"⚠️ KHB_Display: Icon loading failed - {e}")
        return False
