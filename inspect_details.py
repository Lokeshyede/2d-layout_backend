import struct
import json

glb_path = r'E:\2d alyout\backend\uploads\models\racks_1.glb'
with open(glb_path, 'rb') as f:
    f.read(12)
    chunk_len, chunk_type = struct.unpack('<II', f.read(8))
    data = json.loads(f.read(chunk_len).decode('utf-8'))

nodes = data.get('nodes', [])
meshes = data.get('meshes', [])
materials = data.get('materials', [])
accessors = data.get('accessors', [])

print("=== NODES 0 to 20 ===")
for i in range(min(20, len(nodes))):
    n = nodes[i]
    m_idx = n.get('mesh')
    m_name = meshes[m_idx].get('name') if m_idx is not None else ""
    mat_info = ""
    if m_idx is not None and len(meshes[m_idx].get('primitives', [])) > 0:
        mat_idx = meshes[m_idx]['primitives'][0].get('material')
        if mat_idx is not None:
            mat_info = f"Mat[{mat_idx}]: {materials[mat_idx].get('name')}"
    print(f"Node {i:02d}: name='{n.get('name')}' mesh={m_idx} {m_name} {mat_info} children={n.get('children')}")
    if 'translation' in n: print(f"    T: {n['translation']}")
    if 'rotation' in n: print(f"    R: {n['rotation']}")
    if 'scale' in n: print(f"    S: {n['scale']}")
    if 'matrix' in n: print(f"    M: {n['matrix']}")
