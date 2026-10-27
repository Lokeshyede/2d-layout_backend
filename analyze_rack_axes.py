import struct
import json
import numpy as np

glb_path = r'E:\2d alyout\backend\uploads\models\racks_1.glb'
with open(glb_path, 'rb') as f:
    f.read(12)
    chunk_len, chunk_type = struct.unpack('<II', f.read(8))
    data = json.loads(f.read(chunk_len).decode('utf-8'))

nodes = data.get('nodes', [])
meshes = data.get('meshes', [])
accessors = data.get('accessors', [])
scene = data.get('scenes', [])[data.get('scene', 0)]

def get_node_matrix(n):
    if 'matrix' in n:
        return np.array(n['matrix'], dtype=float).reshape(4, 4).T
    T = np.eye(4)
    if 'translation' in n:
        T[0:3, 3] = n['translation']
    R = np.eye(4)
    if 'rotation' in n:
        qx, qy, qz, qw = n['rotation']
        R[0, 0] = 1 - 2*qy*qy - 2*qz*qz
        R[0, 1] = 2*qx*qy - 2*qz*qw
        R[0, 2] = 2*qx*qz + 2*qy*qw
        R[1, 0] = 2*qx*qy + 2*qz*qw
        R[1, 1] = 1 - 2*qx*qx - 2*qz*qz
        R[1, 2] = 2*qy*qz - 2*qx*qw
        R[2, 0] = 2*qx*qz - 2*qy*qw
        R[2, 1] = 2*qy*qz + 2*qx*qw
        R[2, 2] = 1 - 2*qx*qx - 2*qy*qy
    S = np.eye(4)
    if 'scale' in n:
        S[0, 0] = n['scale'][0]
        S[1, 1] = n['scale'][1]
        S[2, 2] = n['scale'][2]
    return T @ R @ S

# Find node path for each mesh
mesh_corners_world = {} # In scene root coordinates (Three.js world coordinates when scene is at 0,0,0)

def collect_mesh_corners(node_idx, parent_mat):
    n = nodes[node_idx]
    world_mat = parent_mat @ get_node_matrix(n)
    m_idx = n.get('mesh')
    if m_idx is not None:
        m = meshes[m_idx]
        pos_idx = m['primitives'][0]['attributes']['POSITION']
        acc = accessors[pos_idx]
        mn = np.array(acc['min'])
        mx = np.array(acc['max'])
        corners = np.array([
            [mn[0], mn[1], mn[2], 1],
            [mn[0], mn[1], mx[2], 1],
            [mn[0], mx[1], mn[2], 1],
            [mn[0], mx[1], mx[2], 1],
            [mx[0], mn[1], mn[2], 1],
            [mx[0], mn[1], mx[2], 1],
            [mx[0], mx[1], mn[2], 1],
            [mx[0], mx[1], mx[2], 1],
        ])
        w_corners = (world_mat @ corners.T).T[:, 0:3]
        if m_idx not in mesh_corners_world:
            mesh_corners_world[m_idx] = []
        mesh_corners_world[m_idx].append(w_corners)
    for c in n.get('children', []):
        collect_mesh_corners(c, world_mat)

for root_idx in scene.get('nodes', []):
    collect_mesh_corners(root_idx, np.eye(4))

# Compute bounding box of rack meshes (0..40) in scene coordinates
rack_pts = []
for m_idx in range(41):
    for c_arr in mesh_corners_world.get(m_idx, []):
        rack_pts.extend(c_arr)

rack_pts = np.array(rack_pts)
r_min = rack_pts.min(axis=0)
r_max = rack_pts.max(axis=0)
r_size = r_max - r_min

print("=== SCENE COORDINATES OF RACK (MESHES 0..40) ===")
print(f"Rack Min  (meters): {r_min}")
print(f"Rack Max  (meters): {r_max}")
print(f"Rack Size (meters): {r_size}")
print(f"Rack Size (inches): {r_size / 0.0254}")

# Look at specific components in scene coordinates
# 1. Upright columns (Mesh 6 and Mesh 18)
col1_pts = np.concatenate(mesh_corners_world[6], axis=0)
col2_pts = np.concatenate(mesh_corners_world[18], axis=0)
print("\nUpright Col 1 (Mesh 6)  Min:", col1_pts.min(axis=0), "Max:", col1_pts.max(axis=0), "Size (in):", (col1_pts.max(axis=0) - col1_pts.min(axis=0))/0.0254)
print("Upright Col 2 (Mesh 18) Min:", col2_pts.min(axis=0), "Max:", col2_pts.max(axis=0), "Size (in):", (col2_pts.max(axis=0) - col2_pts.min(axis=0))/0.0254)

# 2. Bottom shelf (Mesh 00)
shelf0_pts = np.concatenate(mesh_corners_world[0], axis=0)
print("\nBottom Shelf (Mesh 0)   Min:", shelf0_pts.min(axis=0), "Max:", shelf0_pts.max(axis=0), "Size (in):", (shelf0_pts.max(axis=0) - shelf0_pts.min(axis=0))/0.0254)

# 3. Back panels (Mesh 25..28)
back_pts = []
for m_idx in range(25, 29):
    for c_arr in mesh_corners_world[m_idx]:
        back_pts.extend(c_arr)
back_pts = np.array(back_pts)
print("Back Panels (25..28)    Min:", back_pts.min(axis=0), "Max:", back_pts.max(axis=0), "Size (in):", (back_pts.max(axis=0) - back_pts.min(axis=0))/0.0254)
