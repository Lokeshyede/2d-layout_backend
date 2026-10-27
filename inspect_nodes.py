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

print(f"Total nodes: {len(nodes)}, Total meshes: {len(meshes)}")

def get_node_matrix(n):
    if 'matrix' in n:
        return np.array(n['matrix'], dtype=float).reshape(4, 4).T
    # TRS
    T = np.eye(4)
    if 'translation' in n:
        T[0:3, 3] = n['translation']
    R = np.eye(4)
    if 'rotation' in n:
        # quaternion [x, y, z, w]
        qx, qy, qz, qw = n['rotation']
        # rotation matrix from quaternion
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

# Traverse and compute world bounds for each node/mesh
mesh_world_boxes = {}

def traverse(node_idx, parent_mat, path=""):
    n = nodes[node_idx]
    local_mat = get_node_matrix(n)
    world_mat = parent_mat @ local_mat
    name = n.get('name', f'node_{node_idx}')
    cur_path = f"{path}/{name}"
    m_idx = n.get('mesh')
    if m_idx is not None:
        m = meshes[m_idx]
        pos_idx = m['primitives'][0]['attributes']['POSITION']
        acc = accessors[pos_idx]
        mn = np.array(acc['min'])
        mx = np.array(acc['max'])
        # 8 corners
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
        world_corners = (world_mat @ corners.T).T[:, 0:3]
        w_min = world_corners.min(axis=0)
        w_max = world_corners.max(axis=0)
        w_size = w_max - w_min
        print(f"Mesh[{m_idx:02d}] {name:30s} | LocSz: [{mx[0]-mn[0]:.2f}, {mx[1]-mn[1]:.2f}, {mx[2]-mn[2]:.2f}] | WorldMin: {np.round(w_min, 2)} | WorldMax: {np.round(w_max, 2)} | WorldSize: {np.round(w_size, 2)} | Path: {cur_path}")

    for c in n.get('children', []):
        traverse(c, world_mat, cur_path)

for root_idx in scene.get('nodes', []):
    traverse(root_idx, np.eye(4))
