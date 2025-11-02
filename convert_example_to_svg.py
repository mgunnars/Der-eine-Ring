"""
Konvertiert beispiel_mittelerde.json zu SVG
"""

import json
from svg_map_exporter import SVGMapExporter
from advanced_texture_renderer import AdvancedTextureRenderer


def convert_example_map():
    """Konvertiert die Beispielkarte zu SVG"""
    print("🎨 Konvertiere Beispielkarte zu SVG...")
    
    # JSON laden
    with open('maps/beispiel_mittelerde.json', 'r', encoding='utf-8') as f:
        map_data_json = json.load(f)
    
    # In SVG-Format konvertieren
    map_data = {}
    tiles = map_data_json['tiles']
    height = len(tiles)
    width = len(tiles[0]) if tiles else 0
    
    for y in range(height):
        for x in range(width):
            material = tiles[y][x]
            if material != "empty":
                map_data[(x, y)] = material
    
    print(f"   Kartengröße: {width}×{height} ({len(map_data)} Tiles)")
    
    # Renderer
    renderer = AdvancedTextureRenderer()
    
    # SVG Exporter
    exporter = SVGMapExporter(tile_size=256)
    
    # Als High-Quality SVG exportieren
    success = exporter.export_map_to_svg(
        map_data,
        {},  # Materials werden vom Renderer geholt
        renderer,
        'maps/beispiel_mittelerde.svg',
        embed_images=True,
        render_resolution="high"
    )
    
    if success:
        print("✅ Beispielkarte erfolgreich als SVG gespeichert!")
        print("   Datei: maps/beispiel_mittelerde.svg")
        return True
    else:
        print("❌ Konvertierung fehlgeschlagen")
        return False


if __name__ == "__main__":
    convert_example_map()
