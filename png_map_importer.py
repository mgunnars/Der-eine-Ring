"""
PNG Map Importer für "Der Eine Ring"
Importiert komplette Karten als PNG und konvertiert sie in Map-Daten
"""
from PIL import Image
import json
import os
from tkinter import messagebox

class PNGMapImporter:
    """Importiert PNG-Karten und konvertiert sie in Map-Daten"""
    
    def __init__(self):
        self.imported_textures = {}
        self.texture_storage_dir = "imported_maps"
        
        # Erstelle Verzeichnis für importierte Maps
        if not os.path.exists(self.texture_storage_dir):
            os.makedirs(self.texture_storage_dir)
    
    def import_png_map(self, png_path, tile_size=64, map_name=None):
        """
        Importiert eine PNG-Karte und konvertiert sie in Map-Daten
        
        Args:
            png_path: Pfad zur PNG-Datei
            tile_size: Größe eines Tiles in Pixeln (default: 64)
            map_name: Name der Map (optional, sonst Dateiname)
        
        Returns:
            dict: Map-Daten im JSON-Format + SVG-Export-Infos
        """
        try:
            # PNG laden
            img = Image.open(png_path)
            img = img.convert('RGB')  # Sicherstellen dass RGB
            
            # Map-Name bestimmen
            if map_name is None:
                map_name = os.path.splitext(os.path.basename(png_path))[0]
            
            # Berechne Grid-Dimensionen
            width_px, height_px = img.size
            grid_width = width_px // tile_size
            grid_height = height_px // tile_size
            
            print(f"📦 PNG-Import: {width_px}x{height_px}px → {grid_width}x{grid_height} Tiles")
            
            # Erstelle Tile-Grid
            tiles = []
            tile_textures = {}
            tile_counter = 0
            
            for y in range(grid_height):
                row = []
                for x in range(grid_width):
                    # Schneide Tile aus PNG
                    left = x * tile_size
                    top = y * tile_size
                    right = left + tile_size
                    bottom = top + tile_size
                    
                    tile_img = img.crop((left, top, right, bottom))
                    
                    # Generiere eindeutigen Material-Namen
                    material_id = f"imported_{map_name}_tile_{x}_{y}"
                    
                    # Speichere Tile-Textur
                    tile_path = os.path.join(
                        self.texture_storage_dir, 
                        f"{map_name}_tile_{x}_{y}.png"
                    )
                    tile_img.save(tile_path)
                    
                    # Registriere Material
                    tile_textures[material_id] = {
                        "name": f"{map_name} Tile ({x},{y})",
                        "texture_path": tile_path,
                        "color": self._get_average_color(tile_img),
                        "animated": False,
                        "emoji": "🗺️",
                        "position": (x, y)
                    }
                    
                    row.append(material_id)
                    tile_counter += 1
                
                tiles.append(row)
            
            print(f"✅ {tile_counter} Tiles extrahiert und gespeichert")
            
            # Erstelle Map-Daten
            map_data = {
                "width": grid_width,
                "height": grid_height,
                "tiles": tiles,
                "imported_from_png": True,
                "source_png": png_path,
                "tile_size": tile_size,
                "custom_materials": tile_textures,
                "map_name": map_name
            }
            
            # Speichere Map-Daten als JSON
            json_path = os.path.join(self.texture_storage_dir, f"{map_name}_map.json")
            with open(json_path, 'w') as f:
                json.dump(map_data, f, indent=2)
            
            print(f"💾 Map-Daten gespeichert: {json_path}")
            
            return map_data
            
        except Exception as e:
            print(f"❌ Fehler beim PNG-Import: {e}")
            raise
    
    def _get_average_color(self, img):
        """Berechnet durchschnittliche Farbe eines Tiles (für Fallback)"""
        img_small = img.resize((1, 1), Image.Resampling.LANCZOS)
        return img_small.getpixel((0, 0))
    
    def import_png_as_single_texture(self, png_path, material_id=None, map_width=50, map_height=50):
        """
        Importiert PNG als EINE große Textur (skaliert auf gesamte Map)
        
        Args:
            png_path: Pfad zur PNG-Datei
            material_id: Material-ID (optional)
            map_width: Anzahl Tiles in Breite
            map_height: Anzahl Tiles in Höhe
        
        Returns:
            dict: Map-Daten mit einem einzigen Material
        """
        try:
            # PNG laden
            img = Image.open(png_path)
            
            # Map-Name
            map_name = os.path.splitext(os.path.basename(png_path))[0]
            
            if material_id is None:
                material_id = f"imported_{map_name}_full"
            
            # Speichere als Textur
            texture_path = os.path.join(self.texture_storage_dir, f"{map_name}_full.png")
            img.save(texture_path)
            
            # Erstelle Map mit diesem einen Material
            tiles = [[material_id for _ in range(map_width)] for _ in range(map_height)]
            
            # Material-Definition
            custom_material = {
                material_id: {
                    "name": f"{map_name} (Full)",
                    "texture_path": texture_path,
                    "color": self._get_average_color(img.resize((1, 1), Image.Resampling.LANCZOS)),
                    "animated": False,
                    "emoji": "🗺️"
                }
            }
            
            map_data = {
                "width": map_width,
                "height": map_height,
                "tiles": tiles,
                "imported_from_png": True,
                "source_png": png_path,
                "custom_materials": custom_material,
                "map_name": map_name,
                "import_mode": "single_texture"
            }
            
            # Speichern
            json_path = os.path.join(self.texture_storage_dir, f"{map_name}_full_map.json")
            with open(json_path, 'w') as f:
                json.dump(map_data, f, indent=2)
            
            print(f"✅ PNG als einzelne Textur importiert: {map_name}")
            return map_data
            
        except Exception as e:
            print(f"❌ Fehler beim PNG-Import: {e}")
            raise
    
    def load_imported_map(self, json_path):
        """Lädt eine zuvor importierte Map"""
        try:
            with open(json_path, 'r') as f:
                map_data = json.load(f)
            
            print(f"📂 Importierte Map geladen: {map_data.get('map_name', 'Unbekannt')}")
            return map_data
            
        except Exception as e:
            print(f"❌ Fehler beim Laden: {e}")
            raise
    
    def export_imported_map_to_svg(self, map_data, output_path, quality="high"):
        """
        Exportiert eine importierte PNG-Map als SVG
        
        Args:
            map_data: Map-Daten vom Import
            output_path: Ausgabe-Pfad für SVG
            quality: "low", "medium", "high", "ultra"
        """
        try:
            from svg_map_exporter import SVGMapExporter
            
            # Registriere custom materials im Renderer
            from advanced_texture_renderer import AdvancedTextureRenderer
            renderer = AdvancedTextureRenderer()
            
            custom_materials = map_data.get('custom_materials', {})
            for mat_id, mat_info in custom_materials.items():
                # Importiere Textur in Renderer
                renderer.custom_textures[mat_id] = mat_info
                
                # Lade Textur-Datei
                if 'texture_path' in mat_info:
                    renderer.import_texture(mat_id, mat_info['texture_path'])
            
            # Exportiere als SVG
            exporter = SVGMapExporter(renderer)
            
            # Tile-Größe basierend auf Qualität
            tile_sizes = {
                "low": 32,
                "medium": 64,
                "high": 128,
                "ultra": 256
            }
            tile_size = tile_sizes.get(quality, 64)
            
            svg_content = exporter.export_map(map_data, tile_size=tile_size)
            
            # Speichern
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            print(f"✅ SVG exportiert: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Fehler beim SVG-Export: {e}")
            raise
    
    def get_import_preview(self, png_path, tile_size=64, preview_size=400):
        """
        Erstellt ein Preview-Bild mit Grid-Overlay
        
        Args:
            png_path: Pfad zur PNG-Datei
            tile_size: Größe eines Tiles
            preview_size: Maximale Preview-Größe
        
        Returns:
            PIL.Image: Preview-Bild mit Grid
        """
        try:
            img = Image.open(png_path)
            
            # Skaliere für Preview
            img.thumbnail((preview_size, preview_size), Image.Resampling.LANCZOS)
            
            # Berechne Grid basierend auf Skalierung
            scale_factor = img.width / Image.open(png_path).width
            scaled_tile_size = int(tile_size * scale_factor)
            
            # Zeichne Grid
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            
            # Vertikale Linien
            for x in range(0, img.width, scaled_tile_size):
                draw.line([(x, 0), (x, img.height)], fill=(255, 255, 0, 128), width=1)
            
            # Horizontale Linien
            for y in range(0, img.height, scaled_tile_size):
                draw.line([(0, y), (img.width, y)], fill=(255, 255, 0, 128), width=1)
            
            return img
            
        except Exception as e:
            print(f"❌ Fehler beim Preview: {e}")
            return None


# Utility-Funktionen für einfachen Zugriff
def quick_import_png(png_path, tile_size=64):
    """Schneller Import einer PNG-Karte"""
    importer = PNGMapImporter()
    return importer.import_png_map(png_path, tile_size)

def quick_import_and_export_svg(png_path, svg_output_path, tile_size=64, quality="high"):
    """Import PNG → Export SVG in einem Schritt"""
    importer = PNGMapImporter()
    map_data = importer.import_png_map(png_path, tile_size)
    importer.export_imported_map_to_svg(map_data, svg_output_path, quality)
    return map_data
