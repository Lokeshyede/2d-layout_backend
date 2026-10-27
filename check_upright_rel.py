import numpy as np
from deep_analyze_corner_glb import mesh_world_data

C = np.array([426.25, -766.05])
u0 = mesh_world_data[0]
u27 = mesh_world_data[27]
u19 = mesh_world_data[19]

# Get world vertices of the uprights in inches relative to corner C
v0 = (u0['world_verts'][:, [0, 2]] / 0.0254) - C
v27 = (u27['world_verts'][:, [0, 2]] / 0.0254) - C
v19 = (u19['world_verts'][:, [0, 2]] / 0.0254) - C

# Compute angle of Wing A from C to Upright 0
c0_rel = (u0['center_in'][[0, 2]]) - C
c27_rel = (u27['center_in'][[0, 2]]) - C

print("Relative to corner C [426.25, -766.05]:")
print(f"Upright 19 center: {u19['center_in'][[0, 2]] - C}")
print(f"Upright 0  center: {c0_rel}, dist: {np.linalg.norm(c0_rel):.2f}\"")
print(f"Upright 27 center: {c27_rel}, dist: {np.linalg.norm(c27_rel):.2f}\"")

# Let's check rotation where C is (0,0) and the back faces of Upright 19, Upright 0, Upright 27 define the two wall contact planes!
# Let's find the outermost vertices (back planes) that would touch the two walls.
print("\nMesh 0 vertices min/max relative to C:")
print(f"  X range: [{v0[:,0].min():.2f}, {v0[:,0].max():.2f}], Z range: [{v0[:,1].min():.2f}, {v0[:,1].max():.2f}]")
print("Mesh 27 vertices min/max relative to C:")
print(f"  X range: [{v27[:,0].min():.2f}, {v27[:,0].max():.2f}], Z range: [{v27[:,1].min():.2f}, {v27[:,1].max():.2f}]")
print("Mesh 19 vertices min/max relative to C:")
print(f"  X range: [{v19[:,0].min():.2f}, {v19[:,0].max():.2f}], Z range: [{v19[:,1].min():.2f}, {v19[:,1].max():.2f}]")
