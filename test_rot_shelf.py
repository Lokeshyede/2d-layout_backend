import numpy as np

# Shelf 5-points in native coordinates:
# Back corner: C = [426.25, -766.05]
# Side A: P_A = [408.19, -783.35]
# Side B: P_B = [408.32, -750.64]
# Front A: F_A = [396.20, -771.24]
# Front B: F_B = [396.33, -762.75]

C = np.array([426.25, -766.05])
P_A = np.array([408.19, -783.35])
P_B = np.array([408.32, -750.64])
F_A = np.array([396.20, -771.24])
F_B = np.array([396.33, -762.75])

# Center corner C at (0, 0)
pts = np.array([C, P_A, P_B, F_A, F_B]) - C

# Bisector angle:
vA = pts[1] # [-18.06, -17.30]
vB = pts[2] # [-17.93, +15.41]

# Lengths of back edges
lenA = np.linalg.norm(vA)
lenB = np.linalg.norm(vB)
print(f"Wing A back edge length: {lenA:.2f}\"")
print(f"Wing B back edge length: {lenB:.2f}\"")

# Direction vectors
uA = vA / lenA
uB = vB / lenB

# Angle of bisector
bisector = (uA + uB) / 2.0
bisector = bisector / np.linalg.norm(bisector)
bisector_angle = np.arctan2(bisector[1], bisector[0])
print(f"Bisector vector: {bisector}, angle: {np.degrees(bisector_angle):.2f} deg")

# If we rotate so that bisector points along (-1, -1) [the diagonal of a 90 deg corner in CAD]
# Or rotate so that Wing A aligns with +X axis, and Wing B aligns with +Z axis:
# Let's test rotating pts so that uA is along +X, or bisector is at -135 deg:
rot_angle = -bisector_angle - np.pi * 3 / 4 # align bisector to 225 deg (or -135 deg)
c, s = np.cos(rot_angle), np.sin(rot_angle)
R = np.array([[c, -s], [s, c]])

rot_pts = (R @ pts.T).T
print("\nAfter aligning bisector to (-X, -Z) diagonal (corner at 0,0):")
labels = ["Corner C", "Wing A end", "Wing B end", "Front A", "Front B"]
for lbl, p in zip(labels, rot_pts):
    print(f"  {lbl:12s}: X={p[0]:6.2f}\", Z={p[1]:6.2f}\"")

# Let's test rotating so Wing A is exactly along +X:
angle_A = np.arctan2(uA[1], uA[0])
rot_A = -angle_A # rotates uA to +X (0 rad)
c_a, s_a = np.cos(rot_A), np.sin(rot_A)
R_A = np.array([[c_a, -s_a], [s_a, c_a]])
rot_pts_A = (R_A @ pts.T).T

print("\nAfter rotating so Wing A is along +X axis:")
for lbl, p in zip(labels, rot_pts_A):
    print(f"  {lbl:12s}: X={p[0]:6.2f}\", Z={p[1]:6.2f}\"")
