import io
import math
import json
from datetime import datetime, timezone
from reportlab.lib.pagesizes import landscape, A3
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

# Human-readable rack type labels
RACK_TYPE_LABELS = {
    'wall_rack_7x3':    "Wall Rack 7' x 3'",
    'wall_rack_7x4':    "Wall Rack 7' x 4'",
    'center_rack_5x3':  "Center Rack 5' x 3'",
    'endcap_5x3':       "Endcap 5' x 3'",
    'corner_rack_2x2x2':"Corner Rack 7' x 3'",
    # legacy keys
    'Wall Rack':        "Wall Rack",
    'Center Rack':      "Center Rack",
    'Endcap':           "Endcap",
    'Corner Rack':      "Corner Rack",
}

def format_feet_inches_val(inches_val: float) -> str:
    if inches_val is None:
        return "0'-0\""
    total_inches = round(abs(inches_val))
    feet = total_inches // 12
    inches = total_inches % 12
    sign = "-" if inches_val < 0 else ""
    return f"{sign}{feet}'-{inches}\""

def generate_architectural_pdf(project_data: dict, survey_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    # A3 Landscape: 1190.55 Ã— 841.89 points
    page_width, page_height = landscape(A3)
    p = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    COLOR_RED        = colors.HexColor("#D32F2F")
    COLOR_DARK       = colors.HexColor("#121212")
    COLOR_GRAY       = colors.HexColor("#666666")
    COLOR_LIGHT_GRAY = colors.HexColor("#E5E7EB")
    COLOR_WALL       = colors.HexColor("#1A1A1A")
    COLOR_WALL_FILL  = colors.HexColor("#E0E0E0")
    COLOR_COLUMN     = colors.HexColor("#2B2B2B")
    COLOR_DOOR       = colors.HexColor("#C62828")
    COLOR_WINDOW     = colors.HexColor("#0288D1")
    COLOR_RACK       = colors.HexColor("#1565C0")
    COLOR_DIMENSION  = colors.HexColor("#B71C1C")

    margin  = 25
    inner_w = page_width  - 2 * margin
    inner_h = page_height - 2 * margin

    # â”€â”€ Outer border
    p.setStrokeColor(COLOR_DARK)
    p.setLineWidth(2.5)
    p.rect(margin, margin, inner_w, inner_h)

    p.setStrokeColor(COLOR_RED)
    p.setLineWidth(1.0)
    p.rect(margin + 4, margin + 4, inner_w - 8, inner_h - 8)

    # â”€â”€ Header
    header_h = 50
    header_y = page_height - margin - header_h
    p.setFillColor(COLOR_DARK)
    p.rect(margin + 4, header_y, inner_w - 8, header_h - 4, fill=1, stroke=0)
    p.setFillColor(COLOR_RED)
    p.rect(margin + 4, header_y, 12, header_h - 4, fill=1, stroke=0)

    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin + 26, header_y + 28, "RETAILFIX")
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(COLOR_RED)
    p.drawString(margin + 125, header_y + 30, "STORE SURVEY & 2D CAD PLATFORM")
    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor("#CCCCCC"))
    p.drawString(margin + 26, header_y + 12, "ARCHITECTURAL STORE SURVEY & FIXTURE LAYOUT DRAWING")

    survey_id   = survey_data.get("surveyId", "RF-SUR-2026-0001")
    survey_date = survey_data.get("surveyDate", datetime.now(timezone.utc).strftime("%d-%m-%Y"))
    revision    = project_data.get("revision", "REV 1")

    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(colors.white)
    p.drawRightString(page_width - margin - 20, header_y + 28, f"SURVEY ID: {survey_id}")
    p.setFont("Helvetica", 9)
    p.setFillColor(COLOR_LIGHT_GRAY)
    p.drawRightString(page_width - margin - 20, header_y + 12, f"DATE: {survey_date}  |  STATUS: APPROVED  |  {revision}")

    # â”€â”€ Footer / Title Block
    footer_h = 135
    footer_y  = margin + 4
    split_x   = margin + inner_w * 0.48

    p.setStrokeColor(COLOR_DARK)
    p.setLineWidth(1.5)
    p.line(margin + 4, footer_y + footer_h, page_width - margin - 4, footer_y + footer_h)
    p.line(split_x, footer_y, split_x, footer_y + footer_h)

    # Notes
    p.setFillColor(COLOR_DARK)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin + 15, footer_y + footer_h - 18, "DRAWING NOTES & SPECIFICATIONS")
    p.setFont("Helvetica", 8)
    p.setFillColor(COLOR_GRAY)
    notes = [
        "1. All dimensions are in architectural Feet & Inches. Do not scale from this drawing.",
        "2. Surveyor to verify all site dimensions and column inward projections prior to fixture fabrication.",
        "3. Standard designation: Height x Width (e.g. Wall Rack 7'x3' = Height 7', Width 3').",
        "4. This drawing is the property of RETAILFIX CAD PLATFORM. Unauthorized reproduction is prohibited.",
        "5. Standard rack modules: Wall Rack (7'x3', 7'x4'), Center Gondola (5'x3'), Endcap (5'x3'), Corner (2'x2'x2')."
    ]
    for i, note in enumerate(notes):
        p.drawString(margin + 15, footer_y + footer_h - 32 - (i * 12), note)

    # Legend
    leg_x = margin + 15
    leg_y  = footer_y + 10
    p.setFont("Helvetica-Bold", 8)
    p.setFillColor(COLOR_DARK)
    p.drawString(leg_x, leg_y + 18, "LEGEND:")
    p.setFillColor(COLOR_WALL_FILL); p.setStrokeColor(COLOR_WALL); p.setLineWidth(1)
    p.rect(leg_x + 50, leg_y + 16, 20, 6, fill=1, stroke=1)
    p.setFillColor(COLOR_DARK); p.setFont("Helvetica", 8)
    p.drawString(leg_x + 75, leg_y + 16, "Wall (9\")")
    p.setStrokeColor(COLOR_DOOR); p.line(leg_x + 130, leg_y + 16, leg_x + 145, leg_y + 22)
    p.drawString(leg_x + 150, leg_y + 16, "Door Swing")
    p.setFillColor(COLOR_COLUMN); p.rect(leg_x + 220, leg_y + 14, 10, 10, fill=1, stroke=0)
    p.drawString(leg_x + 235, leg_y + 16, "Column (Inward)")
    p.setFillColor(colors.HexColor("#E3F2FD")); p.setStrokeColor(COLOR_RACK)
    p.rect(leg_x + 325, leg_y + 14, 18, 10, fill=1, stroke=1)
    p.drawString(leg_x + 348, leg_y + 16, "Display Rack")

    # Title block table
    tb_x = split_x + 10
    tb_w  = page_width - margin - 14 - tb_x

    cust_info   = survey_data.get("customer", {})
    store_info  = survey_data.get("store", {})
    survey_meta = survey_data.get("survey", {})

    title_data = [
        ["PROJECT / STORE:", store_info.get("storeName", "Retail Store"),    "DRAWING NO:", "DWG-001"],
        ["CUSTOMER NAME:",  cust_info.get("customerName", "Customer"),       "REVISION:",   revision],
        ["OWNER / CONTACT:",cust_info.get("ownerName", cust_info.get("mobileNumber", "-")), "SCALE:", project_data.get("scale", '1/4" = 1\'-0"')],
        ["STORE TYPE:",     store_info.get("storeType", "Supermarket"),      "UNIT:",       "Feet + Inches"],
        ["LOCATION / CITY:",f"{cust_info.get('city','')} {cust_info.get('state','')}".strip() or "-", "SURVEYOR:", survey_meta.get("salesmanName", "RetailFix Surveyor")],
    ]
    tb = Table(title_data, colWidths=[tb_w*0.22, tb_w*0.38, tb_w*0.20, tb_w*0.20], rowHeights=[22]*5)
    tb.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('TEXTCOLOR',  (0,0), (-1,-1), COLOR_DARK),
        ('FONTNAME',   (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('FONTNAME',   (0,0), (0,-1),  'Helvetica-Bold'),
        ('FONTNAME',   (2,0), (2,-1),  'Helvetica-Bold'),
        ('TEXTCOLOR',  (0,0), (0,-1),  COLOR_GRAY),
        ('TEXTCOLOR',  (2,0), (2,-1),  COLOR_GRAY),
        ('GRID',       (0,0), (-1,-1), 0.5, COLOR_LIGHT_GRAY),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    tb.wrapOn(p, tb_w, footer_h - 10)
    tb.drawOn(p, tb_x, footer_y + 10)

    # â”€â”€ Main CAD Drawing Area
    cad_x = margin + 8
    cad_y = footer_y + footer_h + 8
    cad_w = inner_w - 16
    cad_h = header_y - cad_y - 8

    p.setFillColor(colors.white)
    p.rect(cad_x, cad_y, cad_w, cad_h, fill=1, stroke=0)

    # Grid
    p.setStrokeColor(colors.HexColor("#F0F3F6"))
    p.setLineWidth(0.5)
    for gx in range(int(cad_x), int(cad_x + cad_w), 40):
        p.line(gx, cad_y, gx, cad_y + cad_h)
    for gy in range(int(cad_y), int(cad_y + cad_h), 40):
        p.line(cad_x, gy, cad_x + cad_w, gy)

    entities = project_data.get("entities", [])
    if entities:
        min_wx, min_wy =  float('inf'),  float('inf')
        max_wx, max_wy = float('-inf'), float('-inf')

        for ent in entities:
            geom     = ent.get("geometry", {})
            ent_type = ent.get("type", "")
            if ent_type == "wall":
                x1,y1 = geom.get("x1",0), geom.get("y1",0)
                x2,y2 = geom.get("x2",0), geom.get("y2",0)
                min_wx,max_wx = min(min_wx,x1,x2), max(max_wx,x1,x2)
                min_wy,max_wy = min(min_wy,y1,y2), max(max_wy,y1,y2)
            elif ent_type in ["column","rack","shutter","glass_gate","partition","door","window"]:
                x, y = geom.get("x",0), geom.get("y",0)
                w = geom.get("width", 36)
                # For racks use depth (floor-plan), not height (vertical)
                d = geom.get("depth", geom.get("height", 24))
                min_wx,max_wx = min(min_wx, x-w), max(max_wx, x+w)
                min_wy,max_wy = min(min_wy, y-d), max(max_wy, y+d)

        if min_wx == float('inf'):
            min_wx, min_wy, max_wx, max_wy = 0, 0, 600, 400

        world_w = max(max_wx - min_wx, 120) + 120
        world_h = max(max_wy - min_wy, 120) + 120

        scale_x = (cad_w - 60) / world_w
        scale_y = (cad_h - 60) / world_h
        cad_scale = min(scale_x, scale_y, 1.2)

        offset_cx  = cad_x + cad_w / 2
        offset_cy  = cad_y + cad_h / 2
        center_wx  = (min_wx + max_wx) / 2
        center_wy  = (min_wy + max_wy) / 2

        def to_pdf_pt(wx, wy):
            """
            Convert CAD world coords â†’ ReportLab page coords.
            IMPORTANT: CAD Y increases downward; ReportLab Y increases upward.
            We flip the Y axis here so the layout is not mirrored vertically.
            """
            px = offset_cx + (wx - center_wx) * cad_scale
            py = offset_cy - (wy - center_wy) * cad_scale   # â† Y flip
            return px, py

        # 4A. Walls
        for ent in entities:
            if ent.get("type") == "wall":
                geom  = ent.get("geometry", {})
                props = ent.get("properties", {})
                thickness = props.get("thickness", 9) * cad_scale
                x1, y1 = to_pdf_pt(geom.get("x1",0), geom.get("y1",0))
                x2, y2 = to_pdf_pt(geom.get("x2",0), geom.get("y2",0))
                p.setStrokeColor(COLOR_WALL)
                p.setLineWidth(max(thickness, 2.5))
                p.setLineCap(1)
                p.line(x1, y1, x2, y2)

                raw_len = math.sqrt((geom.get("x2",0)-geom.get("x1",0))**2 + (geom.get("y2",0)-geom.get("y1",0))**2)
                dim_str = format_feet_inches_val(raw_len)
                mid_x = (x1+x2)/2; mid_y = (y1+y2)/2
                angle = math.atan2(y2-y1, x2-x1)
                perp_x = -math.sin(angle)*14; perp_y = math.cos(angle)*14
                p.setFont("Helvetica-Bold", 7)
                p.setFillColor(COLOR_DIMENSION)
                p.drawString(mid_x+perp_x-12, mid_y+perp_y-3, dim_str)

        # 4B. Columns
        for ent in entities:
            if ent.get("type") == "column":
                geom = ent.get("geometry", {})
                cw = geom.get("width", 24) * cad_scale
                ch = geom.get("height", 24) * cad_scale
                cx, cy = to_pdf_pt(geom.get("x",0), geom.get("y",0))
                p.setFillColor(COLOR_COLUMN); p.setStrokeColor(COLOR_DARK); p.setLineWidth(1)
                p.rect(cx-cw/2, cy-ch/2, cw, ch, fill=1, stroke=1)
                p.setFont("Helvetica", 6); p.setFillColor(colors.white)
                p.drawCentredString(cx, cy-2, "COL")

        # 4C. Doors
        for ent in entities:
            if ent.get("type") == "door":
                geom = ent.get("geometry", {})
                dw = geom.get("width", 36) * cad_scale
                dx, dy = to_pdf_pt(geom.get("x",0), geom.get("y",0))
                p.setStrokeColor(COLOR_DOOR); p.setLineWidth(1.5)
                p.line(dx-dw/2, dy, dx+dw/2, dy)
                p.setLineWidth(0.8)
                p.arc(dx-dw/2, dy-dw, dx-dw/2+2*dw, dy+dw, 0, 90)

        # 4D. Windows
        for ent in entities:
            if ent.get("type") == "window":
                geom = ent.get("geometry", {})
                ww = geom.get("width", 48) * cad_scale
                wx, wy = to_pdf_pt(geom.get("x",0), geom.get("y",0))
                p.setStrokeColor(COLOR_WINDOW); p.setLineWidth(2)
                p.line(wx-ww/2, wy, wx+ww/2, wy)
                p.setLineWidth(0.8)
                p.line(wx-ww/2, wy-3, wx+ww/2, wy-3)
                p.line(wx-ww/2, wy+3, wx+ww/2, wy+3)

        # 4E. Racks - use depth (floor-plan footprint), apply rotation and entity-specific geometry
        for ent in entities:
            if ent.get("type") == "rack":
                geom  = ent.get("geometry", {})
                props = ent.get("properties", {})
                rw = geom.get("width", 36) * cad_scale
                rd = geom.get("depth", 24) * cad_scale
                rx, ry = to_pdf_pt(geom.get("x",0), geom.get("y",0))
                rot_deg = geom.get("rotation", 0) or 0
                rack_type_key = props.get("rackType", "")
                is_corner = "corner" in rack_type_key.lower() or "corner" in str(props.get("productName", "")).lower()
                is_endcap = "endcap" in rack_type_key.lower() or "endcap" in str(props.get("productName", "")).lower()
                is_wall = bool(props.get("attachedWallId")) or "wall" in rack_type_key.lower()

                p.saveState()
                p.translate(rx, ry)
                p.rotate(rot_deg)   # ReportLab rotate is CCW in degrees

                if is_corner:
                    # Authentic 6-vertex L-shaped polygon for corner rack
                    thk = min(18.0 * cad_scale, rw * 0.5, rd * 0.5)
                    p.setFillColor(colors.HexColor("#F0FDF4")) # Soft green
                    p.setStrokeColor(colors.HexColor("#166534"))
                    p.setLineWidth(1.2)
                    path = p.beginPath()
                    path.moveTo(0, 0)
                    path.lineTo(rw, 0)
                    path.lineTo(rw, thk)
                    path.lineTo(thk, thk)
                    path.lineTo(thk, rd)
                    path.lineTo(0, rd)
                    path.close()
                    p.drawPath(path, fill=1, stroke=1)
                elif is_endcap:
                    # Endcap with distinctive purple tint and cap marker
                    p.setFillColor(colors.HexColor("#FDF4FF"))
                    p.setStrokeColor(colors.HexColor("#7C3AED"))
                    p.setLineWidth(1)
                    p.rect(-rw/2, -rd/2, rw, rd, fill=1, stroke=1)
                    # Bold cap bar
                    cap_h = max(3.0, rd * 0.15)
                    p.setFillColor(colors.HexColor("#7C3AED"))
                    p.rect(-rw/2, rd/2 - cap_h, rw, cap_h, fill=1, stroke=0)
                elif is_wall:
                    # Wall rack with blue tint and bold backing line on wall side
                    p.setFillColor(colors.HexColor("#EFF6FF"))
                    p.setStrokeColor(COLOR_RACK)
                    p.setLineWidth(1)
                    p.rect(-rw/2, -rd/2, rw, rd, fill=1, stroke=1)
                    p.setStrokeColor(COLOR_WALL)
                    p.setLineWidth(2.0)
                    p.line(-rw/2, -rd/2, rw/2, -rd/2)
                else:
                    # Center Gondola
                    p.setFillColor(colors.HexColor("#E3F2FD"))
                    p.setStrokeColor(COLOR_RACK)
                    p.setLineWidth(1)
                    p.rect(-rw/2, -rd/2, rw, rd, fill=1, stroke=1)
                    # Center spine line
                    p.setStrokeColor(colors.HexColor("#90CAF9"))
                    p.setLineWidth(0.8)
                    p.line(0, -rd/2, 0, rd/2)

                # Full human-readable rack type label
                rack_label = RACK_TYPE_LABELS.get(rack_type_key, rack_type_key.replace("_", " ").title() if rack_type_key else "Rack")
                p.setFont("Helvetica-Bold", max(5, min(7, int(rw / 8))))
                p.setFillColor(colors.HexColor("#1E293B"))
                label_x = thk/2 if is_corner else 0
                label_y = thk/2 if is_corner else -3
                p.drawCentredString(label_x, label_y, rack_label)
                p.restoreState()

    else:
        p.setFont("Helvetica", 12)
        p.setFillColor(COLOR_GRAY)
        p.drawCentredString(cad_x + cad_w/2, cad_y + cad_h/2, "Initial Drawing Sheet - Layout creation in progress")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
