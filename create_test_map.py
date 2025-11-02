"""
Erstellt eine farbige Test-Karte für SVG-Export
"""
import json
from datetime import datetime

print("=" * 60)
print("ERSTELLE FARBIGE TEST-KARTE")
print("=" * 60)

# Erstelle eine 10x10 Karte mit verschiedenen Materialien
width = 10
height = 10

tiles = []
materials = ['grass', 'water', 'forest', 'mountain', 'sand', 'stone']

print(f"\n📐 Erstelle {width}x{height} Karte...")

for y in range(height):
    for x in range(width):
        # Abwechselnde Materialien für visuellen Test
        material = materials[(x + y) % len(materials)]
        
        tile = {
            'x': x,
            'y': y,
            'material': material
        }
        tiles.append(tile)

# Karten-Daten
map_data = {
    'width': width,
    'height': height,
    'tiles': tiles,
    'created': datetime.now().isoformat(),
    'name': 'Farbige Test-Karte',
    'river_directions': {}
}

# Speichern
output_file = 'maps/test_colorful.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(map_data, f, indent=2, ensure_ascii=False)

print(f"✅ Karte erstellt: {output_file}")
print(f"   Tiles: {len(tiles)}")
print(f"   Materialien: {set(t['material'] for t in tiles)}")

print("\n🎨 Jetzt kannst du:")
print(f"   1. Die Karte im Editor öffnen: {output_file}")
print(f"   2. Als SVG exportieren")
print(f"   3. Im SVG-Projektor anschauen")

print("\nOder direkt SVG exportieren:")
print("   py convert_test_to_svg.py")

print("\n" + "=" * 60)

# Erstelle auch direkt ein Export-Script
export_script = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from svg_map_exporter import SVGMapExporter

print("Exportiere test_colorful.json zu SVG...")

# Karte laden
with open('maps/test_colorful.json', 'r', encoding='utf-8') as f:
    map_data = json.load(f)

# SVG exportieren
exporter = SVGMapExporter(map_data)
success = exporter.export_map_to_svg(
    'maps/test_colorful.svg',
    quality='high'
)

if success:
    print("✅ SVG erstellt: maps/test_colorful.svg")
    print("   Öffne mit: py svg_projector.py maps/test_colorful.svg")
else:
    print("❌ Export fehlgeschlagen")
"""

with open('convert_test_to_svg.py', 'w', encoding='utf-8') as f:
    f.write(export_script)

print("✅ Export-Script erstellt: convert_test_to_svg.py")
