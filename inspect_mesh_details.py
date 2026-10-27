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
materials = data.get('materials', [])
accessors = data.get('accessors', [])

print("=== MESHES 41 to 44 ===")
for i in range(41, 45):
    m = meshes[i]
    prim = m['primitives'][0]
    mat_idx = prim.get('material')
    mat = materials[mat_idx] if mat_idx is not None else {}
    pos_acc = accessors[prim['attributes']['POSITION']]
    print(f"Mesh {i} ({m.get('name')}): count={pos_acc['count']}, min={pos_acc['min']}, max={pos_acc['max']}, mat={mat.get('name')}")

print("\n=== MESHES 0 to 40 (Summary) ===")
total_verts_0_40 = 0
for i in range(41):
    m = meshes[i]
    prim = m['primitives'][0]
    pos_acc = accessors[prim['attributes']['POSITION']]
    total_verts_0_40 += pos_acc['count']
print(f"Total vertices for Meshes 0..40: {total_verts_0_40}")

for i in [0, 4, 6, 8, 10, 13, 14, 18, 25, 26, 29, 38]:
    m = meshes[i]
    prim = m['primitives'][0]
    mat_idx = prim.get('material')
    mat = materials[mat_idx] if mat_idx is not None else {}
    pos_acc = accessors[prim['attributes']['POSITION']]
    sz = [pos_acc['max'][j] - pos_acc['min'][j] for j in range(3)]
    print(f"Mesh {i:02d}: count={pos_acc['count']:4d}, sz={[round(x, 2) for x in sz]}, mat={mat.get('name')}")
