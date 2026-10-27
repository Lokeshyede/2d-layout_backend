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
materials = data.get('materials', [])
scene = data.get('scenes', [])[data.get('scene', 0)]

# Read binary buffer
with open(glb_path, 'rb') as f:
    f.seek(12 + 8 + chunk_len)
    bin_chunk_len, bin_chunk_type = struct.unpack('<II', f.read(8))
    bin_data = f.read(bin_chunk_len)

def get_accessor_data(acc_idx):
    acc = accessors[acc_idx]
    bv = buffer_views[acc['bufferView']]
    offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    count = acc['count']
    type_str = acc['type'] # VEC3, SCALAR, etc.
    comp_type = acc['componentType'] # 5126 for FLOAT
    
    if comp_type == 5126: # FLOAT
        fmt = '<f'
        item_size = 4
    elif comp_type == 5123: # UNSIGNED_SHORT
        fmt = '<H'
        item_size = 2
    elif comp_type == 5125: # UNSIGNED_INT
        fmt = '<I'
        item_size = 4
    else:
        raise ValueError(f"Unsupported component type {comp_type}")
        
    num_comps = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[type_str]
    stride = bv.get('byteStride', num_comps * item_size)
    
    arr = []
    for i in range(count):
        elem_offset = offset + i * stride
        vals = struct.unpack_from(f"<{num_comps}{fmt[-1]}", bin_data, elem_offset)
        arr.append(vals if num_comps > 1 else vals[0])
    return np.array(arr)

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

mesh_world_data = {}

def traverse(node_idx, parent_mat):
    node = nodes[node_idx]
    local_mat = get_transform(node)
    world_mat = parent_mat @ local_mat
    
    if 'mesh' in node:
        m_idx = node['mesh']
        mesh = meshes[m_idx]
        prim = mesh['primitives'][0]
        pos_idx = prim['attributes']['POSITION']
        verts = get_accessor_data(pos_idx)
        
        # Transform vertices to world coordinates
        homo_verts = np.hstack([verts, np.ones((len(verts), 1))])
        world_verts = (world_mat @ homo_verts.T).T[:, :3]
        
        mn = world_verts.min(axis=0)
        mx = world_verts.max(axis=0)
        center = (mn + mx) / 2.0
        sz_m = mx - mn
        sz_in = sz_m / 0.0254
        center_in = center / 0.0254
        mn_in = mn / 0.0254
        mx_in = mx / 0.0254
        
        mesh_world_data[m_idx] = {
            'node_idx': node_idx,
            'node_name': node.get('name', ''),
            'mesh_idx': m_idx,
            'mesh_name': mesh.get('name', ''),
            'world_verts': world_verts,
            'mn_m': mn,
            'mx_m': mx,
            'center_m': center,
            'sz_m': sz_m,
            'sz_in': sz_in,
            'center_in': center_in,
            'mn_in': mn_in,
            'mx_in': mx_in,
            'local_mat': local_mat,
            'world_mat': world_mat
        }
        
    for child in node.get('children', []):
        traverse(child, world_mat)

for root_idx in scene.get('nodes', []):
    traverse(root_idx, np.identity(4))

print("="*60)
print("1. OVERALL BOUNDS")
all_verts = np.vstack([d['world_verts'] for d in mesh_world_data.values()])
g_min = all_verts.min(axis=0)
g_max = all_verts.max(axis=0)
g_sz = g_max - g_min
print(f"Native X: {g_sz[0]/0.0254:.2f}\" (range: {g_min[0]/0.0254:.2f} to {g_max[0]/0.0254:.2f})")
print(f"Native Y: {g_sz[1]/0.0254:.2f}\" (range: {g_min[1]/0.0254:.2f} to {g_max[1]/0.0254:.2f})")
print(f"Native Z: {g_sz[2]/0.0254:.2f}\" (range: {g_min[2]/0.0254:.2f} to {g_max[2]/0.0254:.2f})")

print("="*60)
print("2. UPRIGHTS ANALYSIS (Meshes 0, 19, 27)")
for u_idx in [0, 19, 27]:
    d = mesh_world_data[u_idx]
    print(f"Upright Mesh {u_idx} ('{d['mesh_name']}'):")
    print(f"  Center: X={d['center_in'][0]:.2f}\", Y={d['center_in'][1]:.2f}\", Z={d['center_in'][2]:.2f}\"")
    print(f"  Bounds Min: X={d['mn_in'][0]:.2f}\", Y={d['mn_in'][1]:.2f}\", Z={d['mn_in'][2]:.2f}\"")
    print(f"  Bounds Max: X={d['mx_in'][0]:.2f}\", Y={d['mx_in'][1]:.2f}\", Z={d['mx_in'][2]:.2f}\"")
    print(f"  Size: W_X={d['sz_in'][0]:.2f}\", H_Y={d['sz_in'][1]:.2f}\", D_Z={d['sz_in'][2]:.2f}\"")

c0 = mesh_world_data[0]['center_in']
c19 = mesh_world_data[19]['center_in']
c27 = mesh_world_data[27]['center_in']

print(f"\nUpright Distances (Floor plane XZ):")
print(f"  dist(Mesh 0, Mesh 19)   = {np.hypot(c0[0]-c19[0], c0[2]-c19[2]):.2f}\"")
print(f"  dist(Mesh 19, Mesh 27)  = {np.hypot(c19[0]-c27[0], c19[2]-c27[2]):.2f}\"")
print(f"  dist(Mesh 0, Mesh 27)   = {np.hypot(c0[0]-c27[0], c0[2]-c27[2]):.2f}\"")

# Vectors from corner pillar (Mesh 19) to wing uprights (0 and 27)
vec_19_to_0 = np.array([c0[0] - c19[0], c0[2] - c19[2]])
vec_19_to_27 = np.array([c27[0] - c19[0], c27[2] - c19[2]])
angle = np.degrees(np.arccos(np.dot(vec_19_to_0, vec_19_to_27) / (np.linalg.norm(vec_19_to_0) * np.linalg.norm(vec_19_to_27))))
print(f"  Vector 19 -> 0:  dX={vec_19_to_0[0]:.2f}\", dZ={vec_19_to_0[1]:.2f}\"")
print(f"  Vector 19 -> 27: dX={vec_19_to_27[0]:.2f}\", dZ={vec_19_to_27[1]:.2f}\"")
print(f"  Angle between wings: {angle:.2f} degrees")

print("="*60)
print("3. SHELVES DETAILED ANALYSIS (Meshes 3, 4, 11, 12, 13, 29)")
shelf_indices = [3, 4, 11, 12, 13, 29]
# Sort by height Y
shelf_indices.sort(key=lambda idx: mesh_world_data[idx]['center_in'][1])

for s_idx in shelf_indices:
    d = mesh_world_data[s_idx]
    verts = d['world_verts'] / 0.0254
    # Compute 2D convex hull / corners in XZ
    print(f"Shelf Mesh {s_idx}:")
    print(f"  Center: X={d['center_in'][0]:.2f}\", Y={d['center_in'][1]:.2f}\", Z={d['center_in'][2]:.2f}\"")
    print(f"  Size: W_X={d['sz_in'][0]:.2f}\", H_Y={d['sz_in'][1]:.2f}\", D_Z={d['sz_in'][2]:.2f}\"")
    print(f"  Min: X={d['mn_in'][0]:.2f}\", Z={d['mn_in'][2]:.2f}\" | Max: X={d['mx_in'][0]:.2f}\", Z={d['mx_in'][2]:.2f}\"")
    # Let's inspect vertex distribution to see if the shelf itself is L-shaped or rectangular!
    # Sample some vertices
    xz_pts = verts[:, [0, 2]]
    print(f"  Vertex count: {len(verts)}, unique XZ points: {len(np.unique(np.round(xz_pts, 2), axis=0))}")
    # Print extreme vertices
    unique_xz = np.unique(np.round(xz_pts, 2), axis=0)
    print(f"  Unique 2D footprint vertices:\n{unique_xz}")

print("="*60)
print("4. BRACKETS ANALYSIS (Meshes 14, 15, 16, 28, 31, 32)")
bracket_indices = [14, 15, 16, 28, 31, 32]
bracket_indices.sort(key=lambda idx: mesh_world_data[idx]['center_in'][1])

for b_idx in bracket_indices:
    d = mesh_world_data[b_idx]
    print(f"Bracket Mesh {b_idx}:")
    print(f"  Center: X={d['center_in'][0]:.2f}\", Y={d['center_in'][1]:.2f}\", Z={d['center_in'][2]:.2f}\"")
    print(f"  Size: W_X={d['sz_in'][0]:.2f}\", H_Y={d['sz_in'][1]:.2f}\", D_Z={d['sz_in'][2]:.2f}\"")
    print(f"  Min: X={d['mn_in'][0]:.2f}\", Y={d['mn_in'][1]:.2f}\", Z={d['mn_in'][2]:.2f}\"")
    print(f"  Max: X={d['mx_in'][0]:.2f}\", Y={d['mx_in'][1]:.2f}\", Z={d['mx_in'][2]:.2f}\"")

print("="*60)
print("5. SHELF <-> BRACKET SPATIAL RELATIONSHIP")
for s_idx in shelf_indices:
    s_d = mesh_world_data[s_idx]
    s_cy = s_d['center_in'][1]
    # find closest bracket by Y
    closest_b = min(bracket_indices, key=lambda b: abs(mesh_world_data[b]['center_in'][1] - s_cy))
    b_d = mesh_world_data[closest_b]
    b_cy = b_d['center_in'][1]
    print(f"Shelf {s_idx:2d} (Y={s_cy:5.2f}\") <---> Bracket {closest_b:2d} (Y={b_cy:5.2f}\")  [delta Y = {b_cy - s_cy:+.2f}\"]")

print("="*60)
print("6. BACK PANELS / CENTRAL PANELS ANALYSIS")
panel_indices = [1, 2, 7, 10, 20, 21, 22, 23, 24, 30]
panel_indices.sort(key=lambda idx: mesh_world_data[idx]['center_in'][1])
for p_idx in panel_indices:
    d = mesh_world_data[p_idx]
    print(f"Panel Mesh {p_idx:2d}: Center=[X:{d['center_in'][0]:5.2f}, Y:{d['center_in'][1]:5.2f}, Z:{d['center_in'][2]:5.2f}] | Size=[X:{d['sz_in'][0]:5.2f}, Y:{d['sz_in'][1]:5.2f}, Z:{d['sz_in'][2]:5.2f}]")
