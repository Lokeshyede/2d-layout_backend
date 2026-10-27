import os
import sys
sys.path.append(r"E:\2d alyout\backend")

from app.services.product_service import validate_and_parse_glb

glb_path = r"E:\Downloads\RACKS (1).glb"
with open(glb_path, "rb") as f:
    data = f.read()

res = validate_and_parse_glb(data, "RACKS (1).glb")
det = res["detected_dimensions"]
print("Detected Dimensions:")
print(f"  Width:  {det.width_inches:.2f}\" ({det.width_mm:.1f} mm)")
print(f"  Height: {det.height_inches:.2f}\" ({det.height_mm:.1f} mm)")
print(f"  Depth:  {det.depth_inches:.2f}\" ({det.depth_mm:.1f} mm)")
print(f"  Meshes count: {res['mesh_count']}")
