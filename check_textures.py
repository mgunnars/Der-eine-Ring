"""
Überprüft die Karten-Texturen
"""
import json
import os
from PIL import Image
from texture_manager import TextureManager

print("=" * 60)
print("KARTEN-TEXTUREN ANALYSE")
print("=" * 60)

# Karte laden
with open('maps/beispiel_mittelerde.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

tiles = data.get('tiles', [])
print(f"\n📊 Karten-Info:")
print(f"   Größe: {data.get('width')}x{data.get('height')}")
print(f"   Tiles: {len(tiles)}")

# Materialien sammeln
if tiles:
    if isinstance(tiles, dict):
        tile_list = list(tiles.values())
    else:
        tile_list = tiles
    
    materials = set()
    for tile in tile_list:
        if isinstance(tile, dict):
            materials.add(tile.get('material', 'unknown'))
    
    print(f"\n🎨 Verwendete Materialien: {materials}")

# Texture Manager testen
print("\n🖼️ Texture Manager Test:")
tm = TextureManager()

# Teste ein paar Materialien
test_materials = ['grass', 'water', 'mountain', 'forest']
for mat in test_materials:
    try:
        texture = tm.get_texture(mat, size=64)
        if texture:
            # Prüfe Farbe
            pixels = texture.load()
            sample_color = pixels[32, 32]
            print(f"   {mat}: ✅ {texture.size} - Farbe: RGB{sample_color}")
        else:
            print(f"   {mat}: ❌ None")
    except Exception as e:
        print(f"   {mat}: ❌ Fehler: {e}")

# Detail Maps Ordner prüfen
print(f"\n📁 Detail Maps Ordner:")
if os.path.exists('detail_maps'):
    files = os.listdir('detail_maps')
    print(f"   Gefunden: {len(files)} Dateien")
    for f in files[:10]:
        print(f"   - {f}")
else:
    print(f"   ⚠️ Ordner 'detail_maps' nicht gefunden!")

print("\n" + "=" * 60)
