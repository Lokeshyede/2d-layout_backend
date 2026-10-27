import numpy as np

def test_obb_collision():
    # Rack at X=100, Z=200, Width=36, Depth=24, Rotation Y = 35 deg (wall-mounted: Z from 0 to 24 local)
    rack_pos = np.array([100.0, 200.0])
    w, d = 36.0, 24.0
    rot_deg = 35.0
    rot_rad = np.radians(rot_deg)

    # Player radius = 10"
    player_radius = 10.0

    # Test point: player trying to walk into the front of the rack
    # In local rack space: front is at local Z = 24. A point at local Z = 28 is 4" away (< 10" radius) -> should collide!
    # Let's compute world position of this point:
    local_pt = np.array([0.0, 28.0])
    c, s = np.cos(rot_rad), np.sin(rot_rad)
    world_pt = rack_pos + np.array([local_pt[0] * c + local_pt[1] * s, -local_pt[0] * s + local_pt[1] * c])

    # Now let's test collision detection from world_pt:
    delta = world_pt - rack_pos
    # Inverse rotation:
    local_test = np.array([delta[0] * c - delta[1] * s, delta[0] * s + delta[1] * c])
    
    # Clamp to box [-w/2, w/2] x [0, d]
    closest_x = np.clip(local_test[0], -w/2, w/2)
    closest_z = np.clip(local_test[1], 0, d)
    
    dist = np.hypot(local_test[0] - closest_x, local_test[1] - closest_z)
    print(f"World Player Pos: {world_pt}")
    print(f"Local Player Pos: {local_test}")
    print(f"Closest Box Point: [{closest_x}, {closest_z}]")
    print(f"Distance to Box: {dist:.2f} (Player Radius = {player_radius})")
    print(f"Colliding: {dist < player_radius}")

    if dist < player_radius:
        penetration = player_radius - dist
        # Push vector in local space
        if dist > 1e-4:
            local_normal = (local_test - np.array([closest_x, closest_z])) / dist
        else:
            local_normal = np.array([0.0, 1.0])
        # World normal
        world_normal = np.array([local_normal[0] * c + local_normal[1] * s, -local_normal[0] * s + local_normal[1] * c])
        resolved_world = world_pt + world_normal * penetration
        print(f"Resolved World Pos: {resolved_world}")

test_obb_collision()
