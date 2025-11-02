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
            
            # Sicherstellen dass texture_storage_dir existiert
            os.makedirs(self.texture_storage_dir, exist_ok=True)
            
            # Berechne Grid-Dimensionen
            width_px, height_px = img.size
            grid_width = width_px // tile_size
            grid_height = height_px // tile_size
            total_tiles = grid_width * grid_height
            
            print(f"📦 PNG-Import: {width_px}x{height_px}px → {grid_width}x{grid_height} Tiles")
            print(f"📁 Speicherpfad: {self.texture_storage_dir}")
            
            # WARNUNG bei zu vielen Tiles (Performance/Memory)
            if total_tiles > 2500:
                print(f"⚠️ WARNUNG: {total_tiles} Tiles ist sehr viel!")
                print(f"💡 Empfehlung:")
                print(f"   - Nutze größere Tile-Größe (z.B. 128px statt 64px)")
                print(f"   - ODER nutze 'Single-Texture-Modus' für große Bilder")
                print(f"   - Editor kann nur ~1000-2000 Tiles flüssig darstellen")
                
                # Optional: Automatisch abbrechen
                if total_tiles > 5000:
                    raise ValueError(
                        f"Zu viele Tiles ({total_tiles})!\n\n"
                        f"Bitte wähle eine größere Tile-Größe (z.B. 128px).\n"
                        f"Oder nutze den 'Single-Texture-Modus' für große Karten."
                    )
            
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
                    
                    # BORDER-REMOVAL: Entferne 1px Border falls vorhanden (schwarze/graue Linien)
                    tile_img = self._remove_tile_border_if_present(tile_img)
                    
                    # Generiere eindeutigen Material-Namen (ohne Leerzeichen!)
                    safe_map_name = map_name.replace(" ", "_").replace("\\", "_").replace("/", "_")
                    material_id = f"{safe_map_name}_x{x}_y{y}"
                    
                    # Speichere Tile-Textur mit NORMALISIERTEN Pfaden
                    tile_filename = f"{safe_map_name}_tile_{x}_{y}.png"
                    tile_path = os.path.join(self.texture_storage_dir, tile_filename)
                    
                    # Normalisiere Pfad (Forward Slashes für Konsistenz)
                    tile_path = tile_path.replace("\\", "/")
                    
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
                "name": map_name,  # Wichtig für Bundle-System!
                "storage_dir": self.texture_storage_dir
            }
            
            # Speichere Map-Daten als JSON (mit normalisiertem Pfad)
            safe_map_name = map_name.replace(" ", "_").replace("\\", "_").replace("/", "_")
            json_path = os.path.join(self.texture_storage_dir, f"{safe_map_name}_map.json")
            json_path = json_path.replace("\\", "/")
            
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
    
    def _remove_tile_border_if_present(self, tile_img):
        """
        Entfernt 1px Border von Tile falls vorhanden (Grid-Lines von importierten PNGs)
        Prüft ob Ränder deutlich dunkler sind als das Innere
        """
        width, height = tile_img.size
        
        # Zu kleine Tiles nicht bearbeiten
        if width < 10 or height < 10:
            return tile_img
        
        # Konvertiere zu RGB falls nötig
        if tile_img.mode == 'RGBA':
            tile_rgb = tile_img.convert('RGB')
        else:
            tile_rgb = tile_img
        
        pixels = tile_rgb.load()
        
        # Sample Ränder (Top, Bottom, Left, Right)
        edge_pixels = []
        
        # Top & Bottom
        for x in range(width):
            edge_pixels.append(pixels[x, 0])  # Top
            edge_pixels.append(pixels[x, height-1])  # Bottom
        
        # Left & Right
        for y in range(height):
            edge_pixels.append(pixels[0, y])  # Left
            edge_pixels.append(pixels[width-1, y])  # Right
        
        # Berechne durchschnittliche Helligkeit der Ränder
        edge_brightness = sum(sum(p) for p in edge_pixels) / (len(edge_pixels) * 3)
        
        # Sample Inneres (Center 50%)
        center_start_x = width // 4
        center_start_y = height // 4
        center_end_x = (width * 3) // 4
        center_end_y = (height * 3) // 4
        
        center_pixels = []
        for y in range(center_start_y, center_end_y, max(1, (center_end_y - center_start_y) // 10)):
            for x in range(center_start_x, center_end_x, max(1, (center_end_x - center_start_x) // 10)):
                center_pixels.append(pixels[x, y])
        
        if not center_pixels:
            return tile_img
        
        center_brightness = sum(sum(p) for p in center_pixels) / (len(center_pixels) * 3)
        
        # Wenn Ränder mindestens 30% dunkler sind als Inneres → Border entfernen
        if edge_brightness < center_brightness * 0.7:
            # Crop 1px von allen Seiten und scale zurück
            cropped = tile_img.crop((1, 1, width-1, height-1))
            return cropped.resize((width, height), Image.LANCZOS)
        
        return tile_img
    
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
