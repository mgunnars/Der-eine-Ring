"""
Test-Skript: Vergleich PNG-Embedding vs. Echte Vektoren

Erstellt zwei SVG-Dateien zum Vergleich:
1. PNG-Modus: Texturen als Base64-kodierte Rasterbilder
2. VEKTOR-Modus: Texturen als echte SVG-Geometrie

ERGEBNIS:
- Dateigröße
- Skalierbarkeit
- Editierbarkeit in Inkscape/Illustrator
"""

from svg_map_exporter import SVGMapExporter
from svg_texture_vectorizer import SVGTextureVectorizer
from advanced_texture_renderer import AdvancedTextureRenderer
import os
import time


def create_test_map():
    """Erstellt eine Test-Karte mit verschiedenen Materialien"""
    return {
        # Erste Reihe
        (0, 0): "grass",
        (1, 0): "water",
        (2, 0): "forest",
        (3, 0): "mountain",
        
        # Zweite Reihe
        (0, 1): "sand",
        (1, 1): "stone",
        (2, 1): "road",
        (3, 1): "dirt",
        
        # Dritte Reihe
        (0, 2): "village",
        (1, 2): "grass",
        (2, 2): "water",
        (3, 2): "forest",
        
        # Vierte Reihe
        (0, 3): "mountain",
        (1, 3): "sand",
        (2, 3): "stone",
        (3, 3): "road"
    }


def test_export_comparison():
    """Führt den Vergleichstest durch"""
    print("=" * 70)
    print("🧪 TEST: PNG-Embedding vs. Echte SVG-Vektoren")
    print("=" * 70)
    print()
    
    # Test-Daten
    map_data = create_test_map()
    materials = {}  # Leer, da wir nur die Standard-Materialien nutzen
    renderer = AdvancedTextureRenderer()
    exporter = SVGMapExporter(tile_size=256)
    
    # ===== TEST 1: PNG-MODUS (Alte Methode) =====
    print("📦 TEST 1: PNG-Embedding (Raster-Bilder)")
    print("-" * 70)
    
    output_png = "test_export_PNG_MODE.svg"
    start_time = time.time()
    
    exporter.export_map_to_svg(
        map_data=map_data,
        materials=materials,
        renderer=renderer,
        output_path=output_png,
        embed_images=True,
        render_resolution="high",
        use_symbols=False,
        use_vectors=False  # PNG-Modus!
    )
    
    png_time = time.time() - start_time
    png_size = os.path.getsize(output_png) if os.path.exists(output_png) else 0
    
    print(f"   Export-Zeit: {png_time:.2f}s")
    print(f"   Dateigröße: {png_size / 1024:.1f} KB")
    print()
    
    # ===== TEST 2: VEKTOR-MODUS (Neue Methode) =====
    print("🎨 TEST 2: Echte SVG-Vektoren")
    print("-" * 70)
    
    output_vector = "test_export_VECTOR_MODE.svg"
    start_time = time.time()
    
    exporter.export_map_to_svg(
        map_data=map_data,
        materials=materials,
        renderer=renderer,
        output_path=output_vector,
        embed_images=False,  # Nicht relevant für Vektor-Modus
        render_resolution="high",
        use_symbols=False,
        use_vectors=True  # VEKTOR-Modus!
    )
    
    vector_time = time.time() - start_time
    vector_size = os.path.getsize(output_vector) if os.path.exists(output_vector) else 0
    
    print(f"   Export-Zeit: {vector_time:.2f}s")
    print(f"   Dateigröße: {vector_size / 1024:.1f} KB")
    print()
    
    # ===== VERGLEICH =====
    print("=" * 70)
    print("📊 VERGLEICH")
    print("=" * 70)
    print()
    
    print(f"{'Kriterium':<30} {'PNG-Modus':<20} {'Vektor-Modus':<20}")
    print("-" * 70)
    print(f"{'Dateigröße':<30} {png_size/1024:.1f} KB{'':<13} {vector_size/1024:.1f} KB")
    print(f"{'Export-Zeit':<30} {png_time:.2f}s{'':<15} {vector_time:.2f}s")
    print(f"{'Skalierbarkeit':<30} {'Verpixelt':<20} {'Unendlich ✓':<20}")
    print(f"{'Editierbar in Inkscape':<30} {'Nein (Raster)':<20} {'Ja (Vektor) ✓':<20}")
    print(f"{'Farben änderbar':<30} {'Nein':<20} {'Ja (CSS/Attributes) ✓':<20}")
    print(f"{'Animations-fähig':<30} {'Begrenzt':<20} {'Voll ✓':<20}")
    print()
    
    # Größen-Unterschied
    if png_size > 0 and vector_size > 0:
        if vector_size < png_size:
            savings = ((png_size - vector_size) / png_size) * 100
            print(f"💾 Vektor-Modus ist {savings:.1f}% kleiner!")
        else:
            increase = ((vector_size - png_size) / png_size) * 100
            print(f"⚠️ Vektor-Modus ist {increase:.1f}% größer")
            print(f"   (Aber dafür echte Vektoren mit unendlicher Skalierung!)")
    print()
    
    print("=" * 70)
    print("✅ Test abgeschlossen!")
    print()
    print("Öffne die Dateien zum Vergleich:")
    print(f"   1. {output_png}")
    print(f"   2. {output_vector}")
    print()
    print("Tipp: Öffne beide in Inkscape und zoome hinein:")
    print("   → PNG-Modus wird verpixelt")
    print("   → Vektor-Modus bleibt scharf! ✓")
    print("=" * 70)


def test_vectorizer_standalone():
    """Test nur den Vectorizer alleine"""
    print("\n🎨 Standalone Test: SVG Texture Vectorizer\n")
    
    vectorizer = SVGTextureVectorizer()
    vectorizer_module = __import__('svg_texture_vectorizer')
    
    # Nutze die test_vectorizer Funktion aus dem Modul
    vectorizer_module.test_vectorizer()


if __name__ == "__main__":
    # Erst Standalone-Test
    test_vectorizer_standalone()
    
    print("\n" + "=" * 70 + "\n")
    
    # Dann Vergleichstest
    test_export_comparison()
