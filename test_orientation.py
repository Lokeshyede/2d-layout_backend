import numpy as np

# From our earlier analysis:
# Rack Min  (meters): [ 53.42938,   0.00000, -46.50936 ]
# Rack Max  (meters): [ 53.96850,   2.16000, -45.53846 ]
#
# Back panel (Mesh 25..28): X = 53.89m, Y = 0.12..2.16m, Z = -46.48..-45.57m
# Front shelf trim (Mesh 14): X = 53.43m, Y = 0.81m, Z = -46.48..-45.57m
# Left upright (Mesh 18): Z = -46.51..-46.47m, X = 53.46..53.96m
# Right upright (Mesh 6): Z = -45.58..-45.54m, X = 53.46..53.96m

def check_rotation(angle_deg):
    theta = np.radians(angle_deg)
    c = np.cos(theta)
    s = np.sin(theta)
    # Rotation around Y matrix:
    # [ c, 0, s]
    # [ 0, 1, 0]
    # [-s, 0, c]
    R = np.array([
        [ c, 0, s],
        [ 0, 1, 0],
        [-s, 0, c]
    ])

    back_pt = np.array([53.89, 1.0, -46.02])
    front_pt = np.array([53.43, 1.0, -46.02])
    col_left = np.array([53.71, 1.0, -46.49])
    col_right = np.array([53.71, 1.0, -45.56])

    pts = np.array([back_pt, front_pt, col_left, col_right])
    r_pts = (R @ pts.T).T

    print(f"\n--- ROTATION Y = {angle_deg} DEG ---")
    print(f"Back Panel : X={r_pts[0,0]:.2f}, Z={r_pts[0,2]:.2f}")
    print(f"Front Trim : X={r_pts[1,0]:.2f}, Z={r_pts[1,2]:.2f} (Front Z - Back Z = {r_pts[1,2] - r_pts[0,2]:.2f})")
    print(f"Left Col   : X={r_pts[2,0]:.2f}, Z={r_pts[2,2]:.2f}")
    print(f"Right Col  : X={r_pts[3,0]:.2f}, Z={r_pts[3,2]:.2f} (Right X - Left X = {r_pts[3,0] - r_pts[2,0]:.2f})")

check_rotation(90)
check_rotation(-90)
