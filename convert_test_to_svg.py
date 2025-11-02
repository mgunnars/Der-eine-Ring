#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from svg_map_exporter import SVGMapExporter
from texture_manager import TextureManager
from advanced_texture_renderer import AdvancedTextureRenderer

print("Exportiere test_colorful.json zu SVG...")

# Karte laden
with open('maps/test_colorful.json', 'r', encoding='utf-8') as f:
    map_data_json = json.load(f)

# Tiles in Dictionary umwandeln
tiles_dict = {}
for tile in map_data_json.get('tiles', []):
    x = tile.get('x')
    y = tile.get('y')
    material = tile.get('material', 'grass')
    if x is not None and y is not None:
        tiles_dict[(x, y)] = material

print(f"📊 Karte: {map_data_json.get('width')}x{map_data_json.get('height')}")
print(f"   Tiles: {len(tiles_dict)}")

# Manager initialisieren
renderer = AdvancedTextureRenderer()
materials = renderer.base_materials

# SVG exportieren
exporter = SVGMapExporter(tile_size=512)
success = exporter.export_map_to_svg(
    map_data=tiles_dict,
    materials=materials,
    renderer=renderer,
    output_path='maps/test_colorful.svg',
    embed_images=True,
    render_resolution='high'
)

if success:
    print("✅ SVG erstellt: maps/test_colorful.svg")
    print("   Öffne mit: py svg_projector.py maps/test_colorful.svg")
else:
    print("❌ Export fehlgeschlagen")
