import numpy as np

# Native product bounds from Meshes 0..40:
p_min = np.array([53.4293830, 2.044536e-9, -46.5093620])
p_max = np.array([53.96850356, 2.15999991, -45.53846083])
p_center = (p_min + p_max) / 2.0
p_size = p_max - p_min

print("Native Rack Size (meters):", p_size)
print("Native Rack Size (inches):", p_size / 0.0254)

# Rotation +90 deg around Y:
theta = np.radians(90)
c, s = np.cos(theta), np.sin(theta)
R = np.array([
    [ c, 0, s],
    [ 0, 1, 0],
    [-s, 0, c]
])

# 8 corners of the native product box:
corners = []
for x in [p_min[0], p_max[0]]:
    for y in [p_min[1], p_max[1]]:
        for z in [p_min[2], p_max[2]]:
            corners.append([x, y, z])
corners = np.array(corners)
rot_corners = (R @ corners.T).T

rot_min = rot_corners.min(axis=0)
rot_max = rot_corners.max(axis=0)
rot_center = (rot_min + rot_max) / 2.0
rot_size = rot_max - rot_min

print("\nRotated Rack Size (meters):", rot_size)
print("Rotated Rack Size (inches):", rot_size / 0.0254)
print("Rotated Min (meters):", rot_min)
print("Rotated Max (meters):", rot_max)
print("Rotated Center (meters):", rot_center)

# Target: Base Dimensions
# W = 36", H = 84", D = 24"
base_w = 36.0 * 0.0254 # 0.9144 m
base_h = 84.0 * 0.0254 # 2.1336 m
base_d = 24.0 * 0.0254 # 0.6096 m

scale_x_base = base_w / rot_size[0]
scale_y_base = base_h / rot_size[1]
scale_z_base = base_d / rot_size[2]

print(f"\nStage 1 Base Scale Factors:")
print(f"Scale X (Width) : {scale_x_base:.4f} (from {rot_size[0]/0.0254:.2f}\" to {base_w/0.0254:.2f}\")")
print(f"Scale Y (Height): {scale_y_base:.4f} (from {rot_size[1]/0.0254:.2f}\" to {base_h/0.0254:.2f}\")")
print(f"Scale Z (Depth) : {scale_z_base:.4f} (from {rot_size[2]/0.0254:.2f}\" to {base_d/0.0254:.2f}\")")

# Check wall-mounted anchor:
# We want:
# X centered: X goes from -base_w/2 to +base_w/2
# Y ground: Y goes from 0 to +base_h
# Z wall-mount: back face at Z = 0, front extends to +base_d
# Rotated back face is at rot_min[2] (-53.9685 m)
# Rotated front face is at rot_max[2] (-53.4294 m)
print(f"Back face Z in rotated space: {rot_min[2]:.4f} m")
print(f"Front face Z in rotated space: {rot_max[2]:.4f} m")
print(f"Z span in rotated space: {rot_max[2] - rot_min[2]:.4f} m ({rot_size[2]/0.0254:.2f} inches)")
