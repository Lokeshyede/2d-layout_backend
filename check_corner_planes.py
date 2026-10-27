import numpy as np
from deep_analyze_corner_glb import mesh_world_data

# Analyze back panels normal vectors
for p_idx in [21, 2]:
    d = mesh_world_data[p_idx]
    verts = d['world_verts'] / 0.0254
    # fit a plane to vertices
    c = np.mean(verts, axis=0)
    shifted = verts - c
    cov = np.cov(shifted.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    # normal is the eigenvector with smallest eigenvalue
    normal = eigvecs[:, 0]
    print(f"Panel Mesh {p_idx} normal: [X={normal[0]:.4f}, Y={normal[1]:.4f}, Z={normal[2]:.4f}]")

# Let's check the two back planes formed by Corner Pillar (Mesh 19) and the two uprights (0 and 27)
c19 = mesh_world_data[19]['center_in']
c0 = mesh_world_data[0]['center_in']
c27 = mesh_world_data[27]['center_in']

# The back faces of the rack:
# Wall A connects along Corner to Upright 0
# Wall B connects along Corner to Upright 27
# Let's find the exact back planes:
# What are the extreme back points of Mesh 19, Mesh 0, Mesh 27?
print("\nExtreme points:")
print("Mesh 19 max X:", mesh_world_data[19]['mx_in'][0])
print("Mesh 0 min Z:", mesh_world_data[0]['mn_in'][2])
print("Mesh 27 max Z:", mesh_world_data[27]['mx_in'][2])

# Let's inspect the corner pillar 19:
v19 = mesh_world_data[19]['world_verts'] / 0.0254
print("Corner Pillar 19 bounds in XZ:")
print("  X: min =", v19[:, 0].min(), "max =", v19[:, 0].max())
print("  Z: min =", v19[:, 2].min(), "max =", v19[:, 2].max())

# Let's find the angle between the two back panels!
p21_verts = mesh_world_data[21]['world_verts'] / 0.0254
p2_verts = mesh_world_data[2]['world_verts'] / 0.0254

# For panel 21 (wing 1)
cov21 = np.cov((p21_verts - np.mean(p21_verts, axis=0)).T)
n21 = np.linalg.eigh(cov21)[1][:, 0]
if n21[0] < 0: n21 = -n21 # point generally outwards

# For panel 2 (wing 2)
cov2 = np.cov((p2_verts - np.mean(p2_verts, axis=0)).T)
n2 = np.linalg.eigh(cov2)[1][:, 0]
if n2[0] < 0: n2 = -n2

print(f"Panel 21 normal in XZ: [{n21[0]:.4f}, {n21[2]:.4f}]")
print(f"Panel 2 normal in XZ:  [{n2[0]:.4f}, {n2[2]:.4f}]")

dot_panels = n21[0]*n2[0] + n21[2]*n2[2]
angle_panels = np.degrees(np.arccos(dot_panels))
print(f"Angle between back panels: {angle_panels:.2f} degrees")
