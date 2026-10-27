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
materials = data.get('materials', [])
scene = data.get('scenes', [])[data.get('scene', 0)]

print(f"Total Meshes in GLTF: {len(meshes)}")
print(f"Total Nodes in GLTF: {len(nodes)}")

# Compute total model bounds taking node hierarchy into account
def get_transform(node):
    # returns 4x4 matrix
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
        # Quaternion to matrix
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

global_min = np.array([float('inf'), float('inf'), float('inf')])
global_max = np.array([float('-inf'), float('-inf'), float('-inf')])

mesh_details = []

def traverse(node_idx, parent_mat):
    global global_min, global_max
    node = nodes[node_idx]
    local_mat = get_transform(node)
    world_mat = parent_mat @ local_mat
    
    if 'mesh' in node:
        m_idx = node['mesh']
        mesh = meshes[m_idx]
        prim = mesh['primitives'][0]
        pos_acc = accessors[prim['attributes']['POSITION']]
        mn = np.array(pos_acc['min'])
        mx = np.array(pos_acc['max'])
        
        # 8 corners of bbox
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
        world_corners = (world_mat @ corners.T).T[:, :3]
        w_mn = world_corners.min(axis=0)
        w_mx = world_corners.max(axis=0)
        
        global_min = np.minimum(global_min, w_mn)
        global_max = np.maximum(global_max, w_mx)
        
        sz_m = w_mx - w_mn
        sz_in = sz_m / 0.0254
        
        mat_idx = prim.get('material')
        mat_name = materials[mat_idx].get('name') if mat_idx is not None else ''
        
        mesh_details.append({
            'node_idx': node_idx,
            'node_name': node.get('name', ''),
            'mesh_idx': m_idx,
            'mesh_name': mesh.get('name', ''),
            'min_m': w_mn,
            'max_m': w_mx,
            'sz_m': sz_m,
            'sz_in': sz_in,
            'material': mat_name,
            'verts': pos_acc['count']
        })
        
    for child in node.get('children', []):
        traverse(child, world_mat)

for root_idx in scene.get('nodes', []):
    traverse(root_idx, np.identity(4))

total_sz_m = global_max - global_min
total_sz_in = total_sz_m / 0.0254

print(f"\n--- OVERALL NATIVE BOUNDS ---")
print(f"Min (m):  {np.round(global_min, 4)}")
print(f"Max (m):  {np.round(global_max, 4)}")
print(f"Size (m): {np.round(total_sz_m, 4)}")
print(f"Size (in): Width(X)={round(total_sz_in[0], 2)}\", Height(Y)={round(total_sz_in[1], 2)}\", Depth(Z)={round(total_sz_in[2], 2)}\"")

print(f"\n--- ALL MESH DETAILS ({len(mesh_details)} instances) ---")
for d in mesh_details:
    print(f"Mesh {d['mesh_idx']:2d} (Node {d['node_idx']:2d} '{d['node_name']}'): sz_in=[X:{d['sz_in'][0]:5.2f}, Y:{d['sz_in'][1]:5.2f}, Z:{d['sz_in'][2]:5.2f}] | Y-range=[{d['min_m'][1]/0.0254:5.2f}, {d['max_m'][1]/0.0254:5.2f}] | verts={d['verts']} | mat='{d['material']}'")
