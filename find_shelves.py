import struct
import json
import numpy as np

glb_paths = {
    'Corner Rack': r'E:\2d alyout\backend\uploads\models\Croner_rack_8a46ed65.glb',
    'Wall Rack': r'E:\2d alyout\backend\uploads\models\RACKS_a9a323ad.glb',
    'Endcap': r'E:\2d alyout\backend\uploads\models\endcap_7d6c5784.glb'
}

def analyze(name, path):
    with open(path, 'rb') as f:
        f.read(12)
        chunk_len, chunk_type = struct.unpack('<II', f.read(8))
        data = json.loads(f.read(chunk_len).decode('utf-8'))

    nodes = data.get('nodes', [])
    meshes = data.get('meshes', [])
    accessors = data.get('accessors', [])
    buffer_views = data.get('bufferViews', [])
    
    with open(path, 'rb') as f:
        f.read(12)
        f.read(8 + chunk_len)
        bin_len, bin_type = struct.unpack('<II', f.read(8))
        bin_data = f.read(bin_len)

    def get_accessor_data(acc_idx):
        acc = accessors[acc_idx]
        bv_idx = acc.get('bufferView', 0)
        bv = buffer_views[bv_idx]
        offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
        count = acc['count']
        t = acc['type']
        comp = acc['componentType']
        
        type_sizes = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
        num_comps = type_sizes[t]
        
        comp_fmt = {5126: 'f', 5123: 'H', 5125: 'I', 5121: 'B', 5122: 'h'}
        fmt = '<' + str(num_comps * count) + comp_fmt.get(comp, 'f')
        
        raw = struct.unpack_from(fmt, bin_data, offset)
        return np.array(raw).reshape(count, num_comps)

    # Compute global transforms for all nodes
    world_matrices = [np.eye(4) for _ in range(len(nodes))]
    
    def resolve_transform(node_idx, parent_mat):
        node = nodes[node_idx]
        local = np.eye(4)
        if 'matrix' in node:
            local = np.array(node['matrix']).reshape(4,4).T
        else:
            if 'translation' in node:
                t = node['translation']
                local[0:3, 3] = t
            if 'rotation' in node:
                q = node['rotation']
                qx, qy, qz, qw = q
                r = np.array([
                    [1-2*qy**2-2*qz**2, 2*qx*qy-2*qz*qw, 2*qx*qz+2*qy*qw],
                    [2*qx*qy+2*qz*qw, 1-2*qx**2-2*qz**2, 2*qy*qz-2*qx*qw],
                    [2*qx*qz-2*qy*qw, 2*qy*qz+2*qx*qw, 1-2*qx**2-2*qy**2]
                ])
                local[0:3, 0:3] = r
            if 'scale' in node:
                s = node['scale']
                local[0:3, 0:3] *= s
        
        world = parent_mat @ local
        world_matrices[node_idx] = world
        
        for child in node.get('children', []):
            resolve_transform(child, world)
            
    scene = data.get('scenes', [])[data.get('scene', 0)]
    for root in scene.get('nodes', []):
        resolve_transform(root, np.eye(4))
        
    mesh_world_data = {}
    for i, n in enumerate(nodes):
        if 'mesh' in n:
            m_idx = n['mesh']
            m = meshes[m_idx]
            m_name = m.get('name', f"mesh_{m_idx}")
            mat = world_matrices[i]
            
            all_verts = []
            for prim in m['primitives']:
                pos_acc = prim['attributes'].get('POSITION')
                if pos_acc is not None:
                    verts = get_accessor_data(pos_acc)
                    all_verts.append(verts)
            if not all_verts: continue
            
            verts = np.vstack(all_verts)
            
            hom = np.ones((verts.shape[0], 4))
            hom[:, 0:3] = verts
            world_v = (mat @ hom.T).T[:, 0:3]
            
            mn = world_v.min(axis=0) / 0.0254
            mx = world_v.max(axis=0) / 0.0254
            c = (mn + mx) / 2
            s = mx - mn
            
            mesh_world_data[m_idx] = {
                'name': m_name,
                'min': mn,
                'max': mx,
                'center': c,
                'size': s
            }
            
    print(f"\n[{name}] Mesh Analysis:")
    
    global_min_y = min([d['min'][1] for d in mesh_world_data.values()])
    global_max_y = max([d['max'][1] for d in mesh_world_data.values()])
    print(f"OVERALL Y BOUNDS: Min = {global_min_y:.2f}\", Max = {global_max_y:.2f}\"")
    
    for idx, d in mesh_world_data.items():
        # Identify shelves: width > 10, depth > 10, height < 2
        if d['size'][0] > 10 and d['size'][2] > 10 and d['size'][1] < 2:
            print(f"SHELF   - Mesh {idx:2d}: Center Y = {d['center'][1]:6.2f}\", Width = {d['size'][0]:6.2f}\", Depth = {d['size'][2]:6.2f}\", Height = {d['size'][1]:6.2f}\"")
        elif d['size'][0] < 5 and d['size'][2] < 5 and d['size'][1] > 50:
            print(f"UPRIGHT - Mesh {idx:2d}: Center Y = {d['center'][1]:6.2f}\", X = {d['center'][0]:6.2f}\", Z = {d['center'][2]:6.2f}\"")
        elif d['size'][0] > 10 and d['size'][1] > 10 and d['size'][2] < 2:
            print(f"BACK PNL- Mesh {idx:2d}: Center Y = {d['center'][1]:6.2f}\", X = {d['center'][0]:6.2f}\", Z = {d['center'][2]:6.2f}\"")

analyze('Wall Rack', glb_paths['Wall Rack'])
analyze('Corner Rack', glb_paths['Corner Rack'])
