"""
Performance Benchmark: SVG vs PNG Rendering

Vergleicht:
- SVG Export & Rendering Zeit
- PNG Tile-basiertes Rendering Zeit
- Speicherverbrauch
- Dateigrößen
"""

import time
import os
import sys
from PIL import Image
from svg_map_exporter import SVGMapExporter
from svg_projector import SVGProjectorRenderer
from advanced_texture_renderer import AdvancedTextureRenderer


class RenderingBenchmark:
    """Benchmark-Suite für SVG vs PNG Vergleich"""
    
    def __init__(self):
        self.renderer = AdvancedTextureRenderer()
        self.results = []
    
    def create_test_map(self, width, height):
        """Erstellt eine Test-Karte mit verschiedenen Materialien"""
        materials = ["gras", "wald", "wasser", "stein", "weg", "dorf"]
        map_data = {}
        
        for y in range(height):
            for x in range(width):
                # Abwechselnde Materialien für Realismus
                mat_index = (x + y) % len(materials)
                map_data[(x, y)] = materials[mat_index]
        
        return map_data
    
    def benchmark_svg_export(self, map_data, resolution="high"):
        """Benchmark SVG Export"""
        print(f"\n📐 Teste SVG Export ({resolution})...")
        
        exporter = SVGMapExporter(tile_size=256)
        output_file = f"benchmark_svg_{resolution}.svg"
        
        start_time = time.time()
        
        success = exporter.export_map_to_svg(
            map_data,
            {},
            self.renderer,
            output_file,
            embed_images=True,
            render_resolution=resolution
        )
        
        export_time = time.time() - start_time
        
        if success and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024  # KB
            
            print(f"✅ Export erfolgreich")
            print(f"   Zeit: {export_time:.2f}s")
            print(f"   Dateigröße: {file_size:.1f} KB")
            
            return {
                'time': export_time,
                'size_kb': file_size,
                'success': True
            }
        else:
            print(f"❌ Export fehlgeschlagen")
            return {'success': False}
    
    def benchmark_svg_render(self, svg_file, width, height):
        """Benchmark SVG Rendering zu Bildschirmauflösung"""
        print(f"\n🎬 Teste SVG Rendering ({width}×{height})...")
        
        if not os.path.exists(svg_file):
            print(f"❌ SVG Datei nicht gefunden: {svg_file}")
            return {'success': False}
        
        renderer = SVGProjectorRenderer(svg_file)
        
        start_time = time.time()
        image = renderer.render_to_size(width, height, cache=False)
        render_time = time.time() - start_time
        
        if image:
            print(f"✅ Rendering erfolgreich")
            print(f"   Zeit: {render_time:.2f}s")
            print(f"   Auflösung: {image.size}")
            
            return {
                'time': render_time,
                'resolution': image.size,
                'success': True
            }
        else:
            print(f"❌ Rendering fehlgeschlagen")
            return {'success': False}
    
    def benchmark_png_tiles(self, map_data, tile_size=256):
        """Benchmark klassisches PNG Tile-Rendering"""
        print(f"\n🖼️ Teste PNG Tile-Rendering ({tile_size}×{tile_size})...")
        
        start_time = time.time()
        
        # Alle Tiles rendern
        rendered_tiles = {}
        for (x, y), material in map_data.items():
            tile = self.renderer.get_texture(material, tile_size, 0)
            rendered_tiles[(x, y)] = tile
        
        render_time = time.time() - start_time
        
        # Geschätzte Speichergröße
        num_tiles = len(map_data)
        # Jedes Tile: tile_size×tile_size×3 bytes (RGB)
        memory_mb = (num_tiles * tile_size * tile_size * 3) / (1024 * 1024)
        
        print(f"✅ Rendering erfolgreich")
        print(f"   Zeit: {render_time:.2f}s")
        print(f"   Tiles: {num_tiles}")
        print(f"   Speicher (geschätzt): {memory_mb:.1f} MB")
        
        return {
            'time': render_time,
            'tiles': num_tiles,
            'memory_mb': memory_mb,
            'success': True
        }
    
    def benchmark_composite_image(self, map_data, tile_size=256):
        """Benchmark: Compositing aller Tiles zu einem großen Bild"""
        print(f"\n🖼️ Teste PNG Composite-Bild...")
        
        # Kartengrenzen
        if not map_data:
            return {'success': False}
        
        min_x = min(x for x, y in map_data.keys())
        max_x = max(x for x, y in map_data.keys())
        min_y = min(y for x, y in map_data.keys())
        max_y = max(y for x, y in map_data.keys())
        
        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size
        
        start_time = time.time()
        
        # Großes Composite-Bild erstellen
        composite = Image.new('RGB', (width, height), (0, 0, 0))
        
        for (grid_x, grid_y), material in map_data.items():
            tile = self.renderer.get_texture(material, tile_size, 0)
            
            x = (grid_x - min_x) * tile_size
            y = (grid_y - min_y) * tile_size
            
            composite.paste(tile, (x, y))
        
        composite_time = time.time() - start_time
        
        # Als PNG speichern um Dateigröße zu messen
        output_file = "benchmark_composite.png"
        composite.save(output_file, format='PNG', optimize=True)
        file_size = os.path.getsize(output_file) / 1024  # KB
        
        print(f"✅ Composite erfolgreich")
        print(f"   Zeit: {composite_time:.2f}s")
        print(f"   Auflösung: {width}×{height}")
        print(f"   Dateigröße: {file_size:.1f} KB")
        
        return {
            'time': composite_time,
            'resolution': (width, height),
            'size_kb': file_size,
            'success': True
        }
    
    def run_full_benchmark(self, map_sizes=None):
        """Führt vollständigen Benchmark durch"""
        if map_sizes is None:
            map_sizes = [
                (5, 5, "Klein"),
                (10, 10, "Mittel"),
                (20, 20, "Groß")
            ]
        
        print("=" * 70)
        print("🏁 SVG vs PNG Performance Benchmark")
        print("=" * 70)
        
        for width, height, label in map_sizes:
            print(f"\n{'=' * 70}")
            print(f"📊 Test: {label} Karte ({width}×{height} Tiles)")
            print(f"{'=' * 70}")
            
            # Test-Karte erstellen
            map_data = self.create_test_map(width, height)
            num_tiles = len(map_data)
            
            results = {
                'size': (width, height),
                'label': label,
                'tiles': num_tiles
            }
            
            # 1. PNG Tiles
            png_result = self.benchmark_png_tiles(map_data, tile_size=256)
            results['png_tiles'] = png_result
            
            # 2. PNG Composite
            composite_result = self.benchmark_composite_image(map_data, tile_size=256)
            results['png_composite'] = composite_result
            
            # 3. SVG Export (High)
            svg_result = self.benchmark_svg_export(map_data, resolution="high")
            results['svg_export_high'] = svg_result
            
            # 4. SVG Rendering (1920×1080 - Projektor)
            if svg_result['success']:
                svg_render_result = self.benchmark_svg_render(
                    "benchmark_svg_high.svg",
                    1920, 1080
                )
                results['svg_render_1080p'] = svg_render_result
            
            self.results.append(results)
            
            # Zusammenfassung
            self.print_summary(results)
        
        # Finale Vergleichstabelle
        self.print_comparison_table()
    
    def print_summary(self, results):
        """Druckt Zusammenfassung eines Tests"""
        print(f"\n{'─' * 70}")
        print(f"📈 Zusammenfassung: {results['label']}")
        print(f"{'─' * 70}")
        
        if results['png_tiles']['success']:
            print(f"PNG Tiles:       {results['png_tiles']['time']:.2f}s | "
                  f"{results['png_tiles']['memory_mb']:.1f} MB RAM")
        
        if results['png_composite']['success']:
            print(f"PNG Composite:   {results['png_composite']['time']:.2f}s | "
                  f"{results['png_composite']['size_kb']:.1f} KB")
        
        if results['svg_export_high']['success']:
            print(f"SVG Export:      {results['svg_export_high']['time']:.2f}s | "
                  f"{results['svg_export_high']['size_kb']:.1f} KB")
        
        if 'svg_render_1080p' in results and results['svg_render_1080p']['success']:
            print(f"SVG Render:      {results['svg_render_1080p']['time']:.2f}s")
        
        print()
    
    def print_comparison_table(self):
        """Druckt Vergleichstabelle"""
        print("\n" + "=" * 70)
        print("🏆 FINALE VERGLEICHSTABELLE")
        print("=" * 70)
        print()
        print(f"{'Kartengröße':<15} | {'PNG Zeit':<10} | {'SVG Zeit':<10} | {'SVG Größe':<12}")
        print("-" * 70)
        
        for result in self.results:
            label = result['label']
            png_time = result['png_composite'].get('time', 0) if result['png_composite']['success'] else 0
            svg_time = result['svg_export_high'].get('time', 0) if result['svg_export_high']['success'] else 0
            svg_size = result['svg_export_high'].get('size_kb', 0) if result['svg_export_high']['success'] else 0
            
            print(f"{label:<15} | {png_time:>8.2f}s | {svg_time:>8.2f}s | {svg_size:>9.1f} KB")
        
        print("\n" + "=" * 70)
        print("💡 FAZIT:")
        print("=" * 70)
        print("• SVG: Einmalig langsamer Export, aber perfekte Skalierung")
        print("• PNG Composite: Schneller, aber fixe Auflösung")
        print("• Für Projektor: SVG ist IDEAL (verlustfreie Qualität)")
        print("• Für Editor: PNG Tiles bleiben praktisch (schnelle Updates)")
        print("=" * 70)


def main():
    """Hauptfunktion"""
    benchmark = RenderingBenchmark()
    
    # Standard-Tests
    benchmark.run_full_benchmark([
        (5, 5, "Klein (5×5)"),
        (10, 10, "Mittel (10×10)"),
        (15, 15, "Groß (15×15)")
    ])
    
    # Cleanup
    for f in ["benchmark_svg_high.svg", "benchmark_svg_low.svg", 
              "benchmark_svg_ultra.svg", "benchmark_composite.png"]:
        if os.path.exists(f):
            os.remove(f)
            print(f"🗑️ Cleanup: {f} gelöscht")


if __name__ == "__main__":
    main()
