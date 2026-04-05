#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import re

# Read GeoJSON file
geojson_file = "processed/model_outputs/spatial_temporal_analysis/City_Boundary_20260404.geojson"
with open(geojson_file, 'r', encoding='utf-8') as f:
    boundary_geojson = json.load(f)

# Convert to compact JSON format
boundary_json = json.dumps(boundary_geojson, separators=(',', ':'), ensure_ascii=False)

print(f"[OK] GeoJSON loaded: {len(boundary_json)} bytes, {len(boundary_geojson.get('features', []))} features")

# Process Event 1
html1_file = "processed/model_outputs/spatial_temporal_analysis/pm25_event_1_interactive.html"
with open(html1_file, 'r', encoding='utf-8') as f:
    html1_content = f.read()

# Add boundary data variable
insert_point = html1_content.find("var allDaysData = [")
if insert_point > 0:
    boundary_var = f"    var boundaryData = {boundary_json};\n    "
    html1_new = html1_content[:insert_point] + boundary_var + html1_content[insert_point:]

    # Replace entire fetch function call with direct data usage
    html1_new = re.sub(
        r"fetch\('City_Boundary_20260404\.geojson'\)\s*\.then\(response => \{[^}]*\}\)\s*\.then\(data => \{",
        "Promise.resolve(boundaryData).then(data => {",
        html1_new,
        flags=re.DOTALL
    )

    with open(html1_file, 'w', encoding='utf-8') as f:
        f.write(html1_new)
    print("[OK] Event 1 updated")

# Process Event 2
html2_file = "processed/model_outputs/spatial_temporal_analysis/pm25_event_2_interactive.html"
with open(html2_file, 'r', encoding='utf-8') as f:
    html2_content = f.read()

insert_point = html2_content.find("var allDaysData = [")
if insert_point > 0:
    boundary_var = f"    var boundaryData = {boundary_json};\n    "
    html2_new = html2_content[:insert_point] + boundary_var + html2_content[insert_point:]

    html2_new = re.sub(
        r"fetch\('City_Boundary_20260404\.geojson'\)\s*\.then\(response => \{[^}]*\}\)\s*\.then\(data => \{",
        "Promise.resolve(boundaryData).then(data => {",
        html2_new,
        flags=re.DOTALL
    )

    with open(html2_file, 'w', encoding='utf-8') as f:
        f.write(html2_new)
    print("[OK] Event 2 updated")

print("\n[OK] Done!")
