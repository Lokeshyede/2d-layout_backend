import struct
import json
import numpy as np

glb_path = r'E:\2d alyout\backend\uploads\models\Croner_rack_8a46ed65.glb'
with open(glb_path, 'rb') as f:
    f.read(12)
    chunk_len, chunk_type = struct.unpack('<II', f.read(8))
    data = json.loads(f.read(chunk_len).decode('utf-8'))

nodes = data.get('nodes', [])
meshes = data.get('meshes', [])
accessors = data.get('accessors', [])
buffer_views = data.get('bufferViews', [])
buffers = data.get('buffers', [])
scene = data.get('scenes', [])[data.get('scene', 0)]

# Read binary buffer
with open(glb_path, 'rb') as f:
    f.read(12 + 8 + chunk_len) # Skip JSON chunk
    bin_len, bin_type = struct.unpack('<II', f.read(8))
    bin_data = f.read(bin_len)

def get_transform(node):
    if 'matrix' in node:
        return np.array(node['matrix']).reshape(4, 4).T
    mat = np.identity(4)
    if 'scale' in node:
        s = node['scale']
        mat[0, 0] = s[0]
        mat[1, 1] = s[1]
        mat[2, 2] = s[2]
    if 'rotation' in node:
        qx, qy, qz, qw = node['rotation']
        r = np.array([
            [1 - 2*qy*qy - 2*qz*qz, 2*qx*qy - 2*qz*qw, 2*qx*qz + 2*qy*qw, 0],
            [2*qx*qy + 2*qz*qw, 1 - 2*qx*qx - 2*qz*qz, 2*qy*qz - 2*qx*qw, 0],
            [2*qx*qz - 2*qy*qw, 2*qy*qz + 2*qx*qw, 1 - 2*qx*qx - 2*qy*qy, 0],
            [0, 0, 0, 1]
        ])
        mat = r @ mat
    if 'translation' in node:
        t = node['translation']
        mat[0, 3] = t[0]
        mat[1, 3] = t[1]
        mat[2, 3] = t[2]
    return mat

all_vertices = []

def traverse(node_idx, parent_mat):
    node = nodes[node_idx]
    local_mat = get_transform(node)
    world_mat = parent_mat @ local_mat
    
    if 'mesh' in node:
        m_idx = node['mesh']
        mesh = meshes[m_idx]
        for prim in mesh['primitives']:
            if 'POSITION' in prim['attributes']:
                acc_idx = prim['attributes']['POSITION']
                acc = accessors[acc_idx]
                bv_idx = acc['bufferView']
                bv = buffer_views[bv_idx]
                
                offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
                count = acc['count']
                
                # Assuming FLOAT VEC3
                fmt = f'<{count * 3}f'
                pts = np.array(struct.unpack_from(fmt, bin_data, offset)).reshape(-1, 3)
                
                # Transform to world
                pts_h = np.hstack([pts, np.ones((len(pts), 1))])
                world_pts = (world_mat @ pts_h.T).T[:, :3]
                all_vertices.append(world_pts)
                
    for child in node.get('children', []):
        traverse(child, world_mat)

for root_idx in scene.get('nodes', []):
    traverse(root_idx, np.identity(4))

if all_vertices:
    verts = np.vstack(all_vertices)
    # Ignore Y, project to XZ
    pts_xz = verts[:, [0, 2]]
    min_x, min_z = pts_xz.min(axis=0)
    max_x, max_z = pts_xz.max(axis=0)
    
    # Let's test which of the 4 bounding box corners is EMPTY
    # The L shape has one corner missing.
    corners = {
        'bottom_left': np.array([min_x, min_z]),
        'bottom_right': np.array([max_x, min_z]),
        'top_left': np.array([min_x, max_z]),
        'top_right': np.array([max_x, max_z])
    }
    
    distances = {}
    for name, corner in corners.items():
        # Distance from this corner to the nearest vertex
        dists = np.linalg.norm(pts_xz - corner, axis=1)
        min_dist = dists.min()
        distances[name] = min_dist
    
    # The corner with the LARGEST min_dist to any vertex is the empty "inner" corner!
    empty_corner = max(distances, key=distances.get)
    print("Bounding Box Corners -> Distance to nearest vertex:")
    for k, v in distances.items():
        print(f"{k}: {v:.4f} m")
    
    print(f"Empty inner corner is: {empty_corner}")
    
    outer_corner = None
    if empty_corner == 'top_right': outer_corner = 'bottom_left'
    elif empty_corner == 'bottom_left': outer_corner = 'top_right'
    elif empty_corner == 'top_left': outer_corner = 'bottom_right'
    elif empty_corner == 'bottom_right': outer_corner = 'top_left'
    
    print(f"Outer corner is: {outer_corner}")
    print(f"Outer corner coords: {corners[outer_corner]}")
    
    # Compute leg vectors (assuming outer_corner is the anchor for the legs)
    print(f"To match CAD, inner corner is usually the anchor.")
