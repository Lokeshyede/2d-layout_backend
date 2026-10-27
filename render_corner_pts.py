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

with open(glb_path, 'rb') as f:
    f.read(12 + 8 + chunk_len)
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
        mesh = meshes[node['mesh']]
        for prim in mesh['primitives']:
            if 'POSITION' in prim['attributes']:
                acc = accessors[prim['attributes']['POSITION']]
                bv = buffer_views[acc['bufferView']]
                offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
                count = acc['count']
                pts = np.array(struct.unpack_from(f'<{count * 3}f', bin_data, offset)).reshape(-1, 3)
                pts_h = np.hstack([pts, np.ones((len(pts), 1))])
                world_pts = (world_mat @ pts_h.T).T[:, :3]
                all_vertices.append(world_pts)
    for child in node.get('children', []):
        traverse(child, world_mat)

for root_idx in scene.get('nodes', []):
    traverse(root_idx, np.identity(4))

verts = np.vstack(all_vertices)
pts_xz = verts[:, [0, 2]]
min_x, min_z = pts_xz.min(axis=0)
max_x, max_z = pts_xz.max(axis=0)

grid_size = 40
grid = [[' ' for _ in range(grid_size)] for _ in range(grid_size)]

for x, z in pts_xz:
    gx = int((x - min_x) / (max_x - min_x) * (grid_size - 1))
    gz = int((z - min_z) / (max_z - min_z) * (grid_size - 1))
    grid[gz][gx] = '#'

print("ASCII TOP-DOWN VIEW (X goes right, Z goes down)")
for row in grid:
    print(''.join(row))
