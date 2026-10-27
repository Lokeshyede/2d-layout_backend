import numpy as np

# Native vector A (Wing A) and vector B (Wing B) from corner pillar (426.25, -766.05):
vA = np.array([-18.06, -17.30])
vB = np.array([-17.93, +15.41])

# In Three.js:
# Rotation around Y axis by angle theta:
# x' = x*cos(theta) + z*sin(theta)
# z' = -x*sin(theta) + z*cos(theta)

def rotate_y(v, deg):
    rad = np.radians(deg)
    c, s = np.cos(rad), np.sin(rad)
    # in Three.js (right-handed):
    # [x', z'] = [x*c + z*s, -x*s + z*c]
    x_new = v[0]*c + v[1]*s
    z_new = -v[0]*s + v[1]*c
    return np.array([x_new, z_new])

# Find theta such that vA is along +X (z' = 0, x' > 0)
# -vA[0]*sin(theta) + vA[1]*cos(theta) = 0 => tan(theta) = vA[1] / vA[0]
theta1 = np.degrees(np.arctan2(vA[1], vA[0]))
print(f"Native angle of vA: {theta1:.2f} deg")

rot_y = -theta1 # in standard math, but let's test for Three.js
for test_deg in [theta1, -theta1, 180 - theta1, 180 + theta1, 45, -45, 135, -135]:
    rA = rotate_y(vA, test_deg)
    rB = rotate_y(vB, test_deg)
    if rA[0] > 20 and abs(rA[1]) < 2:
        print(f"Match found! rot_y = {test_deg:.2f} deg:")
        print(f"  Wing A -> X={rA[0]:.2f}\", Z={rA[1]:.2f}\"")
        print(f"  Wing B -> X={rB[0]:.2f}\", Z={rB[1]:.2f}\"")
    elif rB[0] > 20 and abs(rB[1]) < 2:
        print(f"Match found (B along X)! rot_y = {test_deg:.2f} deg:")
        print(f"  Wing A -> X={rA[0]:.2f}\", Z={rA[1]:.2f}\"")
        print(f"  Wing B -> X={rB[0]:.2f}\", Z={rB[1]:.2f}\"")
