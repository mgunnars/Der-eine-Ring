"""
Testet das SVG-Rendering direkt
"""
from svg_projector import SVGProjectorRenderer
from PIL import Image

svg_path = 'maps/test_colorful.svg'

print("=" * 60)
print("SVG-RENDERING TEST")
print("=" * 60)

try:
    print("\n📂 Lade SVG...")
    renderer = SVGProjectorRenderer(svg_path)
    print("   ✅ SVG geladen")
    
    print("\n🎨 Rendere zu 800x600px...")
    img = renderer.render_to_size(800, 600)
    
    if img:
        print(f"   ✅ Rendering erfolgreich")
        print(f"   Größe: {img.size}")
        print(f"   Modus: {img.mode}")
        
        # Pixel-Analyse
        pixels = img.load()
        
        # Prüfe verschiedene Positionen
        print("\n🔍 Pixel-Analyse:")
        test_positions = [
            (100, 100, "Oben links"),
            (400, 300, "Mitte"),
            (700, 500, "Unten rechts")
        ]
        
        colors_found = set()
        for x, y, label in test_positions:
            pixel = pixels[x, y]
            colors_found.add(pixel)
            print(f"   {label} ({x},{y}): RGB{pixel}")
        
        # Analyse
        if len(colors_found) == 1:
            print("\n⚠️ PROBLEM: Alle Pixel haben die gleiche Farbe!")
            print(f"   Farbe: RGB{list(colors_found)[0]}")
            if list(colors_found)[0] == (26, 26, 26):
                print("   → Das ist der schwarze Hintergrund")
                print("   → Die Tiles wurden NICHT eingefügt!")
        else:
            print(f"\n✅ {len(colors_found)} verschiedene Farben gefunden")
            print("   → Tiles wurden korrekt gerendert")
        
        # Bild speichern zum Testen
        test_output = 'test_render_output.png'
        img.save(test_output)
        print(f"\n💾 Test-Bild gespeichert: {test_output}")
        print("   → Öffne diese Datei um das Ergebnis zu sehen")
        
    else:
        print("   ❌ Rendering fehlgeschlagen (None zurückgegeben)")

except Exception as e:
    print(f"\n❌ Fehler: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
