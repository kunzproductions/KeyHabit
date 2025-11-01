# KHB_Analysis.py - KeyHabit Mesh Analysis Module
# Analyze mesh topology: Non-manifold, Triangles, N-gons, Small faces, Concave faces, Boundary edges, Loose edges/vertices

import bpy
from mathutils import Vector
import gpu
from gpu_extras.batch import batch_for_shader
import time


class DrawFace:
    '''Draw colored faces in the 3D view.'''
    
    def __init__(self, tris_points, color):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.color = color
        self.batch = self._create_batch(tris_points)
    
    def _create_batch(self, tris_points):
        vertices = [v for tri in tris_points for v in tri]
        return batch_for_shader(self.shader, 'TRIS', {"pos": vertices})
    
    def update_batch(self, tris_points):
        self.batch = self._create_batch(tris_points)
    
    def draw(self, context):
        gpu.state.face_culling_set('BACK')
        gpu.state.depth_test_set('NONE')
        gpu.state.blend_set('ALPHA_PREMULT')
        
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        self.batch.draw(self.shader)
        
        gpu.state.face_culling_set('NONE')


class DrawEdge:
    '''Draw colored edges in the 3D view.'''
    
    def __init__(self, edge_lines, color, line_width=3.0):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.color = color
        self.line_width = line_width
        self.batch = self._create_batch(edge_lines)
    
    def _create_batch(self, edge_lines):
        vertices = [v for edge in edge_lines for v in edge]
        return batch_for_shader(self.shader, 'LINES', {"pos": vertices})
    
    def update_batch(self, edge_lines):
        self.batch = self._create_batch(edge_lines)
    
    def draw(self, context):
        # Vẽ edges với độ sâu ưu tiên để dễ thấy
        gpu.state.depth_test_set('ALWAYS')  # Luôn vẽ trên cùng
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(self.line_width)
        
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        self.batch.draw(self.shader)
        
        # Reset
        gpu.state.line_width_set(1.0)
        gpu.state.depth_test_set('LESS_EQUAL')


class DrawVertex:
    '''Draw colored points (vertices) in the 3D view.'''
    
    def __init__(self, points, color, point_size=5.0):
        self.shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self.color = color
        self.point_size = point_size
        self.batch = self._create_batch(points)
    
    def _create_batch(self, points):
        if not points:
            points = []
        return batch_for_shader(self.shader, 'POINTS', {"pos": points})
    
    def update_batch(self, points):
        self.batch = self._create_batch(points)
    
    def draw(self, context):
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.blend_set('ALPHA')
        gpu.state.point_size_set(self.point_size)
        
        self.shader.bind()
        self.shader.uniform_float('color', self.color)
        self.batch.draw(self.shader)
        
        gpu.state.point_size_set(1.0)


class KHABIT_OT_AnalyzeCheck(bpy.types.Operator):
    bl_idname = "keyhabit.analyze_check"
    bl_label = "Mesh Analysis"
    bl_description = "Analyze mesh topology: Non-manifold (priority!), N-gons, Small faces, Concave faces, Boundary edges, Loose geometry"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Operator state
    _operator = None
    _running = False
    
    # Face data
    ngon_tris: list = []
    ngons: list = []
    small_faces_tris: list = []
    small_faces: list = []
    concave_faces_tris: list = []
    concave_faces: list = []
    boundary_edges: list = []
    loose_vertices: list = []  # Vertices không thuộc bất kỳ face nào
    loose_edges: list = []  # Edges không thuộc bất kỳ face nào
    non_manifold_vertices: list = []  # Non-manifold vertices
    non_manifold_edges: list = []  # Non-manifold edges (3+ faces)
    degenerate_face_edges: list = []  # Edges của degenerate faces (zero-area, collapsed vertices)
    degenerate_faces: list = []  # Degenerate faces
    
    # Drawing handlers
    _handles = []
    _callbacks = []
    
    # OPTIMIZATION: Throttle update rate để tránh lag
    _last_update_time = 0.0
    _update_interval = 1.0  # Update tối đa 1 lần/giây (tối ưu cho hiệu suất cao)
    
    # Edge ratio threshold for small face detection
    edge_ratio: bpy.props.FloatProperty(
        name="Edge Ratio",
        description="Min/Max edge ratio threshold (faces with ratio < X% are small)",
        default=1.0,
        min=0.1,
        max=50.0,
        precision=1,
        subtype='PERCENTAGE',
        update=lambda self, ctx: self._update_mesh(ctx)
    )
    
    # Concave detection threshold
    concave_threshold: bpy.props.FloatProperty(
        name="Concave Threshold",
        description="Sensitivity for detecting concave faces",
        default=0.1,
        min=0.01,
        max=1.0,
        precision=2,
        update=lambda self, ctx: self._update_mesh(ctx)
    )
    
    # Colors
    NGON_COLOR = (1.0, 0.0, 0.0, 0.1)      # Red
    SMALL_COLOR = (0.0, 0.5, 1.0, 0.1)     # Blue
    CONCAVE_COLOR = (1.0, 0.0, 1.0, 0.1)   # Magenta
    BOUNDARY_COLOR = (0.0, 1.0, 0.0, 1.0)  # Green (solid)
    LOOSE_VERTEX_COLOR = (0.0, 1.0, 1.0, 1.0)  # Cyan (solid)
    LOOSE_EDGE_COLOR = (0.0, 1.0, 1.0, 1.0)  # Cyan (solid)
    NON_MANIFOLD_VERTEX_COLOR = (1.0, 1.0, 0.0, 1.0)  # Yellow (solid) - Nghiêm trọng!
    NON_MANIFOLD_EDGE_COLOR = (1.0, 1.0, 0.0, 1.0)  # Yellow (solid) - Nghiêm trọng!
    DEGENERATE_EDGE_COLOR = (0.0, 0.5, 1.0, 1.0)  # Blue (solid) - Giống Small Face
    
    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D' and context.mode == 'EDIT_MESH'
    
    def invoke(self, context, event):
        # Toggle
        if self.__class__._operator:
            self.__class__._operator.end(context)
            return {'CANCELLED'}
        
        self._running = True
        self.__class__._operator = self
        
        # OPTIMIZATION: Reset throttle timer
        self._last_update_time = 0.0
        
        obj = context.edit_object
        obj.update_from_editmode()
        
        self._analyze_mesh(obj.data, obj.matrix_world)
        self._setup_drawing(context)
        
        bpy.app.handlers.depsgraph_update_post.append(self._depsgraph_update)
        context.window_manager.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if not self._running or context.mode != 'EDIT_MESH':
            self.end(context)
            return {'CANCELLED'}
        
        if event.type == 'ESC':
            self.end(context)
            return {'CANCELLED'}
        
        # OPTIMIZATION: Không redraw mỗi MOUSEMOVE - chỉ PASS_THROUGH
        # Viewport sẽ tự redraw khi cần, không cần force mỗi lần di chuột
        # if event.type == 'MOUSEMOVE':
        #     context.area.tag_redraw()
        
        return {'PASS_THROUGH'}
    
    def end(self, context):
        self._running = False
        self.__class__._operator = None
        
        # Clear data
        self.ngon_tris.clear()
        self.ngons.clear()
        self.small_faces_tris.clear()
        self.small_faces.clear()
        self.concave_faces_tris.clear()
        self.concave_faces.clear()
        self.boundary_edges.clear()
        self.loose_vertices.clear()
        self.loose_edges.clear()
        self.non_manifold_vertices.clear()
        self.non_manifold_edges.clear()
        self.degenerate_face_edges.clear()
        self.degenerate_faces.clear()
        
        # Remove handlers
        for handle in self._handles:
            bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
        self._handles.clear()
        self._callbacks.clear()
        
        if self._depsgraph_update in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(self._depsgraph_update)
        
        if context.area:
            context.area.tag_redraw()
    
    def _update_mesh(self, context):
        if self._running and context.edit_object:
            obj = context.edit_object
            obj.update_from_editmode()
            self._analyze_mesh(obj.data, obj.matrix_world)
            self._update_drawing()
            
            # OPTIMIZATION: Không cần tag_redraw - depsgraph sẽ tự trigger redraw
    
    def _depsgraph_update(self, scene, depsgraph):
        # OPTIMIZATION: Throttle update rate - tránh update quá nhiều lần/giây
        current_time = time.time()
        if current_time - self._last_update_time < self._update_interval:
            return  # Skip update nếu chưa đủ thời gian
        
        obj = bpy.context.edit_object
        if not obj:
            return
        
        # OPTIMIZATION: Chỉ update khi object thực sự thay đổi
        for update in depsgraph.updates:
            if isinstance(update.id, bpy.types.Object) and update.id.original == obj:
                obj.update_from_editmode()
                self._analyze_mesh(obj.data, obj.matrix_world)
                self._update_drawing()
                self._last_update_time = current_time  # Cập nhật thời gian
                break
    
    def _setup_drawing(self, context):
        self._callbacks = [
            DrawFace(self.ngon_tris, self.NGON_COLOR),
            DrawFace(self.small_faces_tris, self.SMALL_COLOR),
            DrawFace(self.concave_faces_tris, self.CONCAVE_COLOR),
            DrawEdge(self.boundary_edges, self.BOUNDARY_COLOR, line_width=3.0),
            DrawEdge(self.loose_edges, self.LOOSE_EDGE_COLOR, line_width=4.0),
            DrawVertex(self.loose_vertices, self.LOOSE_VERTEX_COLOR, point_size=6.0),
            DrawEdge(self.non_manifold_edges, self.NON_MANIFOLD_EDGE_COLOR, line_width=5.0),
            DrawVertex(self.non_manifold_vertices, self.NON_MANIFOLD_VERTEX_COLOR, point_size=8.0),
            DrawEdge(self.degenerate_face_edges, self.DEGENERATE_EDGE_COLOR, line_width=4.0)
        ]
        
        for callback in self._callbacks:
            handle = bpy.types.SpaceView3D.draw_handler_add(
                callback.draw, (context,), 'WINDOW', 'POST_VIEW'
            )
            self._handles.append(handle)
    
    def _update_drawing(self):
        if len(self._callbacks) == 9:
            self._callbacks[0].update_batch(self.ngon_tris)
            self._callbacks[1].update_batch(self.small_faces_tris)
            self._callbacks[2].update_batch(self.concave_faces_tris)
            self._callbacks[3].update_batch(self.boundary_edges)
            self._callbacks[4].update_batch(self.loose_edges)
            self._callbacks[5].update_batch(self.loose_vertices)
            self._callbacks[6].update_batch(self.non_manifold_edges)
            self._callbacks[7].update_batch(self.non_manifold_vertices)
            self._callbacks[8].update_batch(self.degenerate_face_edges)
    
    def _analyze_mesh(self, me, matrix):
        '''Analyze mesh and categorize faces'''
        me.calc_loop_triangles()
        
        # Clear previous data
        self.ngon_tris.clear()
        self.ngons.clear()
        self.small_faces_tris.clear()
        self.small_faces.clear()
        self.concave_faces_tris.clear()
        self.concave_faces.clear()
        self.boundary_edges.clear()
        self.loose_vertices.clear()
        self.loose_edges.clear()
        self.non_manifold_vertices.clear()
        self.non_manifold_edges.clear()
        self.degenerate_face_edges.clear()
        self.degenerate_faces.clear()
        
        # ========== TẠO BMESH MỘT LẦN DUY NHẤT (OPTIMIZATION) ==========
        # Tạo bmesh để xử lý cả degenerate faces và non-manifold vertices
        
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        # ========== PHÁT HIỆN DEGENERATE FACES (ƯU TIÊN RẤT CAO) ==========
        # Degenerate faces: zero-area faces, collapsed vertices, zero-length edges
        
        degenerate_face_set = set()
        AREA_THRESHOLD = 0.000001  # Ngưỡng diện tích rất nhỏ
        DISTANCE_THRESHOLD = 0.0001  # Ngưỡng khoảng cách vertices
        
        for face in bm.faces:
            if face.hide:
                continue
            
            is_degenerate = False
            
            # Check 1: Face có diện tích = 0 hoặc gần 0
            if face.calc_area() < AREA_THRESHOLD:
                is_degenerate = True
            
            # Check 2: Face có 2+ vertices ở cùng vị trí (hoặc rất gần)
            if not is_degenerate:
                verts = [matrix @ v.co for v in face.verts]
                for i in range(len(verts)):
                    for j in range(i + 1, len(verts)):
                        if (verts[i] - verts[j]).length < DISTANCE_THRESHOLD:
                            is_degenerate = True
                            break
                    if is_degenerate:
                        break
            
            # Check 3: Face có zero-length edge
            if not is_degenerate:
                for edge in face.edges:
                    edge_length = edge.calc_length()
                    if edge_length < DISTANCE_THRESHOLD:
                        is_degenerate = True
                        break
            
            if is_degenerate:
                degenerate_face_set.add(face.index)
                self.degenerate_faces.append(me.polygons[face.index])
                
                # Vẽ TẤT CẢ edges của degenerate face
                for edge in face.edges:
                    v1_co = matrix @ edge.verts[0].co
                    v2_co = matrix @ edge.verts[1].co
                    self.degenerate_face_edges.append((v1_co, v2_co))
        
        # ========== PHÁT HIỆN NON-MANIFOLD (ƯU TIÊN CAO NHẤT) ==========
        
        # Find vertices used by faces
        vertices_in_faces = set()
        vertex_edge_count = {}  # Đếm edges của mỗi vertex
        
        for poly in me.polygons:
            if poly.hide:
                continue
            vertices_in_faces.update(poly.vertices)
        
        # Build edge-face mapping và vertex-edge mapping
        edge_face_count = {}
        for poly in me.polygons:
            if poly.hide:
                continue
            for i in range(len(poly.vertices)):
                v1 = poly.vertices[i]
                v2 = poly.vertices[(i + 1) % len(poly.vertices)]
                edge_key = tuple(sorted([v1, v2]))
                edge_face_count[edge_key] = edge_face_count.get(edge_key, 0) + 1
        
        # Detect non-manifold edges (3+ faces)
        non_manifold_edge_set = set()
        for edge_key, count in edge_face_count.items():
            if count >= 3:  # Non-manifold: edge có 3+ faces
                non_manifold_edge_set.add(edge_key)
                v1_co = matrix @ me.vertices[edge_key[0]].co
                v2_co = matrix @ me.vertices[edge_key[1]].co
                self.non_manifold_edges.append((v1_co, v2_co))
        
        # Detect non-manifold vertices (dùng chung bmesh đã tạo ở trên)
        # SỬ DỤNG bmesh.verts[].is_manifold để detect CHÍNH XÁC
        non_manifold_vertex_set = set()
        for vert in bm.verts:
            if not vert.hide:
                is_non_manifold = False
                
                # METHOD 1: Sử dụng is_manifold attribute của BMesh (CHÍNH XÁC NHẤT)
                # is_manifold = False khi vertex có bất kỳ vấn đề topology nào
                if hasattr(vert, 'is_manifold'):
                    # Blender 2.91+ có attribute is_manifold
                    is_non_manifold = not vert.is_manifold
                else:
                    # Fallback cho Blender cũ hơn: Manual checks
                    edge_count = len(vert.link_edges)
                    face_count = len(vert.link_faces)
                    
                    # Non-manifold conditions:
                    # 1. Vertex nằm trong non-manifold edge (edge có 3+ faces)
                    # 2. Vertex có >2 boundary edges
                    # 3. Wire edges mixed với faces
                    # 4. Vertex có disjoint face fans (faces không liên tục)
                    
                    # Check 1: Vertex có trong non-manifold edge
                    for edge in vert.link_edges:
                        edge_key = tuple(sorted([v.index for v in edge.verts]))
                        if edge_key in non_manifold_edge_set:
                            is_non_manifold = True
                            break
                    
                    # Check 2: Vertex có >2 boundary edges (T-junction, Y-junction, etc.)
                    if not is_non_manifold and face_count > 0:
                        boundary_edge_count = sum(1 for e in vert.link_edges if e.is_boundary)
                        if boundary_edge_count > 2:
                            is_non_manifold = True
                    
                    # Check 3: Wire edges (edges không có face) mixed với faces
                    if not is_non_manifold and face_count > 0:
                        wire_edges = [e for e in vert.link_edges if len(e.link_faces) == 0]
                        if len(wire_edges) > 0:
                            is_non_manifold = True
                    
                    # Check 4: Disjoint face fans - các faces không tạo thành disk topology liên tục
                    # Đây là trường hợp khó nhất: vertex có faces nhưng chúng tách rời nhau
                    if not is_non_manifold and face_count > 1:
                        # Build face connectivity graph qua vertex
                        visited_faces = set()
                        stack = [vert.link_faces[0]]
                        visited_faces.add(vert.link_faces[0])
                        
                        # DFS từ face đầu tiên để tìm tất cả faces liên thông qua edges của vertex
                        while stack:
                            current_face = stack.pop()
                            # Tìm các faces khác liên kết với current_face qua edges của vertex này
                            for edge in vert.link_edges:
                                if current_face in edge.link_faces:
                                    for neighbor_face in edge.link_faces:
                                        if neighbor_face not in visited_faces and neighbor_face in vert.link_faces:
                                            visited_faces.add(neighbor_face)
                                            stack.append(neighbor_face)
                        
                        # Nếu không phải tất cả faces đều được visit → có disjoint components → non-manifold
                        if len(visited_faces) < face_count:
                            is_non_manifold = True
                
                if is_non_manifold:
                    non_manifold_vertex_set.add(vert.index)
                    vert_co = matrix @ vert.co
                    self.non_manifold_vertices.append(vert_co)
        
        # OPTIMIZATION: Giải phóng bmesh sau khi dùng xong
        bm.free()
        
        # ========== LOOSE GEOMETRY (BỎ QUA NẾU ĐÃ LÀ NON-MANIFOLD) ==========
        
        # Find loose vertices (vertices not in any face) - BỎ QUA non-manifold
        loose_vertex_set = set()
        for vert in me.vertices:
            if not vert.hide and vert.index not in vertices_in_faces:
                if vert.index not in non_manifold_vertex_set:  # BỎ QUA non-manifold
                    loose_vertex_set.add(vert.index)
                    vert_co = matrix @ vert.co
                    self.loose_vertices.append(vert_co)
        
        # Collect boundary edges (count == 1) - BỎ QUA non-manifold
        for edge_key, count in edge_face_count.items():
            if count == 1 and edge_key not in non_manifold_edge_set:  # BỎ QUA non-manifold
                v1_co = matrix @ me.vertices[edge_key[0]].co
                v2_co = matrix @ me.vertices[edge_key[1]].co
                self.boundary_edges.append((v1_co, v2_co))
        
        # Find loose edges (edges not connected to any face)
        # BỎ QUA non-manifold VÀ edges có cả 2 vertices trong loose_vertex_set
        for edge in me.edges:
            if edge.hide:
                continue
            edge_key = tuple(sorted([edge.vertices[0], edge.vertices[1]]))
            
            # BỎ QUA nếu là non-manifold
            if edge_key in non_manifold_edge_set:
                continue
            
            # BỎ QUA nếu cả 2 vertices đều trong loose_vertex_set
            v1_idx, v2_idx = edge.vertices[0], edge.vertices[1]
            if v1_idx in loose_vertex_set and v2_idx in loose_vertex_set:
                continue  # Đã được thể hiện qua loose vertices
            
            # Nếu edge không có trong edge_face_count, nghĩa là không thuộc face nào
            if edge_key not in edge_face_count:
                v1_co = matrix @ me.vertices[v1_idx].co
                v2_co = matrix @ me.vertices[v2_idx].co
                self.loose_edges.append((v1_co, v2_co))
        
        # Classify faces
        small_faces = set()
        concave_faces = set()
        
        for poly in me.polygons:
            if poly.hide:
                continue
            
            # Check small faces (edge ratio)
            if self._is_small_face(me, poly, matrix):
                small_faces.add(poly.index)
            
            # Check concave faces (4+ vertices only)
            elif len(poly.vertices) >= 4 and self._is_concave_face(me, poly, matrix):
                concave_faces.add(poly.index)
        
        # Build triangle batches (priority: n-gon > concave face > small face)
        for i, loop in enumerate(me.loop_triangles):
            poly = me.polygons[me.loop_triangle_polygons[i].value]
            if poly.hide:
                continue
            
            tri = tuple(matrix @ me.vertices[j].co for j in loop.vertices)
            
            # Priority 1: N-gon (5+ vertices) - show as red
            if len(poly.vertices) > 4:
                self.ngon_tris.append(tri)
            # Priority 2: Concave face - show as magenta
            elif poly.index in concave_faces:
                self.concave_faces_tris.append(tri)
                if poly not in self.concave_faces:
                    self.concave_faces.append(poly)
            # Priority 3: Small face - show as blue
            elif poly.index in small_faces:
                self.small_faces_tris.append(tri)
                if poly not in self.small_faces:
                    self.small_faces.append(poly)
        
        # Count n-gons
        self.ngons = [p for p in me.polygons if len(p.vertices) > 4 and not p.hide]
    
    def _is_small_face(self, me, poly, matrix):
        '''Check if face has small edge ratio (min/max < threshold)'''
        verts = poly.vertices
        if len(verts) < 3:
            return False
        
        # Get edge lengths
        edge_lengths = []
        for i in range(len(verts)):
            v1 = matrix @ me.vertices[verts[i]].co
            v2 = matrix @ me.vertices[verts[(i + 1) % len(verts)]].co
            edge_lengths.append((v2 - v1).length)
        
        min_edge = min(edge_lengths)
        max_edge = max(edge_lengths)
        
        if max_edge < 0.0001:
            return False
        
        ratio = (min_edge / max_edge) * 100.0
        return ratio < self.edge_ratio
    
    def _is_concave_face(self, me, poly, matrix):
        '''Check if face is concave (has any interior angle > 180 degrees)'''
        n = len(poly.vertices)
        if n < 4:
            return False
        
        verts = [matrix @ me.vertices[i].co for i in poly.vertices]
        
        # Get polygon normal
        poly_normal = (matrix.to_3x3() @ poly.normal).normalized()
        
        # Check each vertex for concavity using the sign of cross products
        # For a convex polygon, all cross products should point in same direction as normal
        positive_count = 0
        negative_count = 0
        
        for i in range(n):
            v0 = verts[i]
            v1 = verts[(i + 1) % n]
            v2 = verts[(i + 2) % n]
            
            # Get edges
            edge1 = v1 - v0
            edge2 = v2 - v1
            
            # Skip degenerate edges
            if edge1.length < 0.0001 or edge2.length < 0.0001:
                continue
            
            # Calculate cross product
            cross = edge1.cross(edge2)
            
            # Check direction relative to polygon normal
            dot_normal = cross.dot(poly_normal)
            
            # Count positive and negative orientations
            if dot_normal > self.concave_threshold:
                positive_count += 1
            elif dot_normal < -self.concave_threshold:
                negative_count += 1
        
        # Concave if we have both positive and negative orientations
        # This means some vertices bend inward
        return positive_count > 0 and negative_count > 0


class KHABIT_OT_SelectLooseVertices(bpy.types.Operator):
    bl_idname = "keyhabit.select_loose_vertices"
    bl_label = "Select Loose Vertices"
    bl_description = "Select all loose vertices (vertices not connected to any face)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for v in bm.verts:
            v.select = False
        
        # Select loose vertices
        for v in bm.verts:
            if not v.hide and len(v.link_faces) == 0:
                v.select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len([v for v in bm.verts if v.select])} loose vertices")
        return {'FINISHED'}


class KHABIT_OT_SelectLooseEdges(bpy.types.Operator):
    bl_idname = "keyhabit.select_loose_edges"
    bl_label = "Select Loose Edges"
    bl_description = "Select all loose edges (edges not connected to any face)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for e in bm.edges:
            e.select = False
        
        # Select loose edges
        for e in bm.edges:
            if not e.hide and len(e.link_faces) == 0:
                e.select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len([e for e in bm.edges if e.select])} loose edges")
        return {'FINISHED'}


class KHABIT_OT_SelectBoundaryEdges(bpy.types.Operator):
    bl_idname = "keyhabit.select_boundary_edges"
    bl_label = "Select Boundary Edges"
    bl_description = "Select all boundary edges (edges with only one face)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for e in bm.edges:
            e.select = False
        
        # Select boundary edges
        for e in bm.edges:
            if not e.hide and e.is_boundary:
                e.select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len([e for e in bm.edges if e.select])} boundary edges")
        return {'FINISHED'}


class KHABIT_OT_SelectNgons(bpy.types.Operator):
    bl_idname = "keyhabit.select_ngons"
    bl_label = "Select N-gons"
    bl_description = "Select all n-gons (faces with more than 4 vertices)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for f in bm.faces:
            f.select = False
        
        # Select n-gons
        count = 0
        for f in bm.faces:
            if not f.hide and len(f.verts) > 4:
                f.select = True
                count += 1
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {count} n-gons")
        return {'FINISHED'}


class KHABIT_OT_SelectSmallFaces(bpy.types.Operator):
    bl_idname = "keyhabit.select_small_faces"
    bl_label = "Select Small Faces"
    bl_description = "Select all small faces detected by analysis"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        
        # Get operator
        op = KHABIT_OT_AnalyzeCheck._operator
        if not op:
            return {'CANCELLED'}
        
        # Select small faces
        for face in op.small_faces:
            bm.faces[face.index].select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len(op.small_faces)} small faces")
        return {'FINISHED'}


class KHABIT_OT_SelectConcaveFaces(bpy.types.Operator):
    bl_idname = "keyhabit.select_concave_faces"
    bl_label = "Select Concave Faces"
    bl_description = "Select all concave faces detected by analysis"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        
        # Get operator
        op = KHABIT_OT_AnalyzeCheck._operator
        if not op:
            return {'CANCELLED'}
        
        # Select concave faces
        for face in op.concave_faces:
            bm.faces[face.index].select = True
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {len(op.concave_faces)} concave faces")
        return {'FINISHED'}


class KHABIT_OT_SelectNonManifoldVertices(bpy.types.Operator):
    bl_idname = "keyhabit.select_non_manifold_vertices"
    bl_label = "Select Non-Manifold Vertices"
    bl_description = "Select all non-manifold vertices"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        
        # Switch to vertex selection mode (required for select_non_manifold)
        bpy.context.tool_settings.mesh_select_mode = (True, False, False)
        
        # Select using Blender's built-in non-manifold select
        bpy.ops.mesh.select_non_manifold(
            extend=False,
            use_wire=True,
            use_boundary=False,
            use_multi_face=True,
            use_non_contiguous=True,
            use_verts=True
        )
        
        count = len([v for v in bm.verts if v.select])
        self.report({'INFO'}, f"Selected {count} non-manifold vertices")
        return {'FINISHED'}


class KHABIT_OT_SelectNonManifoldEdges(bpy.types.Operator):
    bl_idname = "keyhabit.select_non_manifold_edges"
    bl_label = "Select Non-Manifold Edges"
    bl_description = "Select all non-manifold edges (3+ faces)"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and KHABIT_OT_AnalyzeCheck._operator
    
    def execute(self, context):
        import bmesh
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        
        # Select non-manifold edges (3+ faces)
        count = 0
        for edge in bm.edges:
            if not edge.hide and len(edge.link_faces) >= 3:
                edge.select = True
                count += 1
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {count} non-manifold edges")
        return {'FINISHED'}


class KHABIT_PT_AnalysisPanel(bpy.types.Panel):
    '''Panel for Mesh Analysis settings'''
    bl_label = "Mesh Analysis"
    bl_idname = "KHABIT_PT_analysis_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "KeyHabit"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        return (context.area.type == 'VIEW_3D' and 
                context.object and 
                context.object.type == 'MESH')
    
    def draw(self, context):
        layout = self.layout
        op = KHABIT_OT_AnalyzeCheck._operator
        
        # Check if in Edit Mode
        if context.mode != 'EDIT_MESH':
            layout.label(text="Switch to Edit Mode", icon='INFO')
            layout.label(text="to use Mesh Analysis")
            return
        
        # Toggle button
        if op is None:
            layout.operator("keyhabit.analyze_check", text="Start Analysis", icon='PLAY')
            layout.label(text="Click to start mesh analysis", icon='INFO')
        else:
            # Active analysis controls
            layout.operator("keyhabit.analyze_check", text="Stop Analysis", icon='PAUSE')
            
            layout.separator()
            
            box = layout.box()
            box.label(text="Detection Settings:", icon='SETTINGS')
            
            # Small Face Settings
            col = box.column(align=True)
            col.label(text="Small Face Detection:")
            col.prop(op, "edge_ratio", slider=True)
            col.label(text=f"Found: {len(op.small_faces)} faces", icon='INFO')
            
            # Separator
            col.separator()
            
            # Concave Face Settings
            col.label(text="Concave Face Detection:")
            col.prop(op, "concave_threshold", slider=True)
            col.label(text=f"Found: {len(op.concave_faces)} faces", icon='INFO')
            
            # Separator
            box.separator()
            
            # Statistics with Select buttons
            box2 = layout.box()
            box2.label(text="Quick Select:", icon='RESTRICT_SELECT_OFF')
            
            # ========== TOPOLOGY ISSUES ==========
            # N-gons
            row = box2.row(align=True)
            row.label(text=f"N-gons: {len(op.ngons)}", icon='MESH_DATA')
            if len(op.ngons) > 0:
                row.operator("keyhabit.select_ngons", text="", icon='RESTRICT_SELECT_OFF')
            
            # Small Faces
            row = box2.row(align=True)
            row.label(text=f"Small Faces: {len(op.small_faces)}", icon='MESH_DATA')
            if len(op.small_faces) > 0:
                row.operator("keyhabit.select_small_faces", text="", icon='RESTRICT_SELECT_OFF')
            
            # Concave Faces
            row = box2.row(align=True)
            row.label(text=f"Concave Faces: {len(op.concave_faces)}", icon='MESH_DATA')
            if len(op.concave_faces) > 0:
                row.operator("keyhabit.select_concave_faces", text="", icon='RESTRICT_SELECT_OFF')
            
            # Boundary Edges
            row = box2.row(align=True)
            row.label(text=f"Boundary Edges: {len(op.boundary_edges)}", icon='EDGESEL')
            if len(op.boundary_edges) > 0:
                row.operator("keyhabit.select_boundary_edges", text="", icon='RESTRICT_SELECT_OFF')
            
            # Non-Manifold (chỉ hiển thị vertices để tránh lỗi selection mode)
            if len(op.non_manifold_vertices) > 0:
                row = box2.row(align=True)
                row.label(text=f"Non-Manifold Verts: {len(op.non_manifold_vertices)}", icon='VERTEXSEL')
                row.operator("keyhabit.select_non_manifold_vertices", text="", icon='RESTRICT_SELECT_OFF')
            
            # ========== LOOSE GEOMETRY (Cyan) ==========
            if len(op.loose_edges) > 0 or len(op.loose_vertices) > 0:
                box2.separator()
                box2.label(text="Loose Geometry:", icon='INFO')
            
            # Loose Edges
            if len(op.loose_edges) > 0:
                row = box2.row(align=True)
                row.label(text=f"  Loose Edges: {len(op.loose_edges)}", icon='EDGESEL')
                row.operator("keyhabit.select_loose_edges", text="", icon='RESTRICT_SELECT_OFF')
            
            # Loose Vertices
            if len(op.loose_vertices) > 0:
                row = box2.row(align=True)
                row.label(text=f"  Loose Vertices: {len(op.loose_vertices)}", icon='VERTEXSEL')
                row.operator("keyhabit.select_loose_vertices", text="", icon='RESTRICT_SELECT_OFF')


# Register
def register():
    bpy.utils.register_class(KHABIT_OT_AnalyzeCheck)
    bpy.utils.register_class(KHABIT_OT_SelectLooseVertices)
    bpy.utils.register_class(KHABIT_OT_SelectLooseEdges)
    bpy.utils.register_class(KHABIT_OT_SelectBoundaryEdges)
    bpy.utils.register_class(KHABIT_OT_SelectNgons)
    bpy.utils.register_class(KHABIT_OT_SelectSmallFaces)
    bpy.utils.register_class(KHABIT_OT_SelectConcaveFaces)
    bpy.utils.register_class(KHABIT_OT_SelectNonManifoldVertices)
    bpy.utils.register_class(KHABIT_OT_SelectNonManifoldEdges)
    bpy.utils.register_class(KHABIT_PT_AnalysisPanel)


def unregister():
    try:
        bpy.utils.unregister_class(KHABIT_PT_AnalysisPanel)
        bpy.utils.unregister_class(KHABIT_OT_SelectNonManifoldEdges)
        bpy.utils.unregister_class(KHABIT_OT_SelectNonManifoldVertices)
        bpy.utils.unregister_class(KHABIT_OT_SelectConcaveFaces)
        bpy.utils.unregister_class(KHABIT_OT_SelectSmallFaces)
        bpy.utils.unregister_class(KHABIT_OT_SelectNgons)
        bpy.utils.unregister_class(KHABIT_OT_SelectBoundaryEdges)
        bpy.utils.unregister_class(KHABIT_OT_SelectLooseEdges)
        bpy.utils.unregister_class(KHABIT_OT_SelectLooseVertices)
        bpy.utils.unregister_class(KHABIT_OT_AnalyzeCheck)
    except Exception as e:
        print(f"Error unregistering analysis classes: {e}")


if __name__ == "__main__":
    register()

