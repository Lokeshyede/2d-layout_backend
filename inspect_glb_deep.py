import struct
import json
import math

glb_path = r'E:\2d alyout\backend\uploads\models\racks_1.glb'
with open(glb_path, 'rb') as f:
    f.read(12)
    chunk_len, chunk_type = struct.unpack('<II', f.read(8))
    data = json.loads(f.read(chunk_len).decode('utf-8'))

nodes = data.get('nodes', [])
meshes = data.get('meshes', [])
accessors = data.get('accessors', [])
scene = data.get('scenes', [])[data.get('scene', 0)]

print(f"Asset generator: {data.get('asset', {}).get('generator')}")
print(f"Scene root node indices: {scene.get('nodes')}")

def print_tree(node_idx, indent=0):
    node = nodes[node_idx]
    prefix = "  " * indent
    name = node.get('name', 'unnamed')
    mesh_idx = node.get('mesh')
    mesh_name = meshes[mesh_idx].get('name') if mesh_idx is not None else ""
    t = node.get('translation')
    r = node.get('rotation')
    s = node.get('scale')
    m = node.get('matrix')
    extra = []
    if t: extra.append(f"T={t}")
    if r: extra.append(f"R={r}")
    if s: extra.append(f"S={s}")
    if m: extra.append(f"M={m}")
    if mesh_idx is not None: extra.append(f"Mesh[{mesh_idx}]: {mesh_name}")
    print(f"{prefix}- [{node_idx}] '{name}' {' '.join(extra)}")
    for child in node.get('children', []):
        print_tree(child, indent + 1)

print("\n--- NODE HIERARCHY ---")
for root_idx in scene.get('nodes', []):
    print_tree(root_idx)

print("\n--- MESH BOUNDS ---")
for m_idx, mesh in enumerate(meshes):
    name = mesh.get('name')
    for p_idx, prim in enumerate(mesh.get('primitives', [])):
        pos_idx = prim.get('attributes', {}).get('POSITION')
        acc = accessors[pos_idx]
        mn = acc.get('min')
        mx = acc.get('max')
        sz = [mx[i] - mn[i] for i in range(3)]
        print(f"Mesh {m_idx} '{name}': min={mn} max={mx} size={sz}")

print("\n--- MATERIALS ---")
for mat_idx, mat in enumerate(data.get('materials', [])):
    pbr = mat.get('pbrMetallicRoughness', {})
    print(f"Material {mat_idx} '{mat.get('name')}': baseColorFactor={pbr.get('baseColorFactor')}, metallicFactor={pbr.get('metallicFactor')}, roughnessFactor={pbr.get('roughnessFactor')}")
