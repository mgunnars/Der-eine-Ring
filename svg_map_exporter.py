"""
SVG Map Exporter - Exportiert Tile-Grid als hochauflösende SVG-Datei

Vorteile:
- Verlustfreie Skalierung für Projektor
- Gesamte Karte als EINE Datei
- Unterstützt Animationen
- Kleinere Dateigröße als viele PNGs
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import base64
from io import BytesIO
from PIL import Image
import os


class SVGMapExporter:
    """Exportiert eine Karte als SVG mit eingebetteten Tiles"""
    
    def __init__(self, tile_size=256):
        self.tile_size = tile_size
        
    def export_map_to_svg(self, map_data, materials, renderer, output_path, 
                         embed_images=True, render_resolution="high", max_dimension=2048,
                         use_symbols=False):
        """
        Exportiert die komplette Karte als SVG
        
        Args:
            map_data: Dictionary mit Tile-Informationen {(x,y): material_name}
            materials: Dictionary mit Material-Daten
            renderer: AdvancedTextureRenderer Instanz
            output_path: Pfad zur SVG-Ausgabedatei
            embed_images: Wenn True, werden Bilder als base64 eingebettet
            render_resolution: "low" (256), "high" (512), "ultra" (1024)
            max_dimension: Maximale Pixel pro Dimension (Standard: 2048)
            use_symbols: Wenn True, nutze <symbol>+<use> (kleiner, aber PIL-inkompatibel!)
        """
        # Finde Kartengrenzen
        if not map_data:
            print("Keine Tiles zum Exportieren!")
            return False
            
        min_x = min(x for x, y in map_data.keys())
        max_x = max(x for x, y in map_data.keys())
        min_y = min(y for x, y in map_data.keys())
        max_y = max(y for x, y in map_data.keys())
        
        width_tiles = max_x - min_x + 1
        height_tiles = max_y - min_y + 1
        
        # Auflösungen
        resolutions = {
            "low": self.tile_size,
            "high": self.tile_size * 2,
            "ultra": self.tile_size * 4
        }
        render_size = resolutions.get(render_resolution, self.tile_size * 2)
        
        # SVG Dimensionen BERECHNEN
        svg_width = width_tiles * render_size
        svg_height = height_tiles * render_size
        
        # LIMIT: Max-Dimension prüfen und anpassen
        if svg_width > max_dimension or svg_height > max_dimension:
            scale = min(max_dimension / svg_width, max_dimension / svg_height)
            old_size = render_size
            render_size = int(render_size * scale)
            svg_width = width_tiles * render_size
            svg_height = height_tiles * render_size
            
            print(f"⚠️ AUFLÖSUNGS-LIMIT erreicht!")
            print(f"   Reduziere Tile-Größe: {old_size}px → {render_size}px")
            print(f"   Max-Dimension: {max_dimension}px")
        
        print(f"🎨 Exportiere Karte als SVG...")
        print(f"   Größe: {width_tiles}×{height_tiles} Tiles ({len(map_data)} Tiles)")
        print(f"   Auflösung: {svg_width}×{svg_height}px ({render_resolution})")
        print(f"   Tile-Größe: {render_size}px")
        print(f"   Eingebettete Bilder: {embed_images}")
        
        # SVG Root erstellen
        svg = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'width': str(svg_width),
            'height': str(svg_height),
            'viewBox': f'0 0 {svg_width} {svg_height}',
            'version': '1.1'
        })
        
        # Metadata
        metadata = ET.SubElement(svg, 'metadata')
        ET.SubElement(metadata, 'title').text = "Der Eine Ring - VTT Map"
        ET.SubElement(metadata, 'description').text = f"Exported map: {width_tiles}x{height_tiles} tiles"
        
        # Definitions für wiederverwendbare Elemente (DEDUPLIZIERUNG!)
        defs = ET.SubElement(svg, 'defs')
        
        # Hintergrund
        bg_rect = ET.SubElement(svg, 'rect', {
            'x': '0',
            'y': '0',
            'width': str(svg_width),
            'height': str(svg_height),
            'fill': '#1a1a1a'
        })
        
        # Haupt-Gruppe für alle Tiles
        map_group = ET.SubElement(svg, 'g', {
            'id': 'map-tiles',
            'data-layer': 'base'
        })
        
        # Cache für Material-Bilder + Symbol-Definitionen
        material_cache = {}
        material_symbols = {}  # {material_name: symbol_id}
        
        # PHASE 1: Alle einzigartigen Materialien rendern
        unique_materials = set(map_data.values())
        print(f"   Deduplizierung: {len(map_data)} Tiles → {len(unique_materials)} einzigartige Materialien")
        
        for material_name in unique_materials:
            tile_data = self._render_material_for_svg(
                material_name, materials, renderer, render_size
            )
            
            if tile_data:
                material_cache[material_name] = tile_data
                
                # SYMBOL-MODUS (kleiner, aber PIL-inkompatibel!)
                if use_symbols:
                    # Symbol in <defs> erstellen für Wiederverwendung
                    symbol_id = f"mat_{material_name.replace(' ', '_').replace('.', '_')}"
                    material_symbols[material_name] = symbol_id
                    
                    # Symbol-Definition
                    symbol = ET.SubElement(defs, 'symbol', {
                        'id': symbol_id,
                        'viewBox': f"0 0 {tile_data['size']} {tile_data['size']}"
                    })
                    
                    if embed_images:
                        ET.SubElement(symbol, 'image', {
                            'width': str(tile_data['size']),
                            'height': str(tile_data['size']),
                            'xlink:href': tile_data['data_uri']
                        })
        
        # PHASE 2: Tiles platzieren
        tile_count = 0
        for (grid_x, grid_y), material_name in sorted(map_data.items()):
            # Position im SVG berechnen
            svg_x = (grid_x - min_x) * render_size
            svg_y = (grid_y - min_y) * render_size
            
            tile_data = material_cache.get(material_name)
            
            if tile_data:
                # Für Village: 2 Tiles nach oben verschieben (Rauch-Overlay)
                if material_name == 'village':
                    offset_y = svg_y - (render_size * 2)
                    offset_x = svg_x
                else:
                    offset_y = svg_y
                    offset_x = svg_x
                
                # SYMBOL-MODUS: Referenz zum Symbol
                if use_symbols and material_name in material_symbols:
                    ET.SubElement(map_group, 'use', {
                        'xlink:href': f"#{material_symbols[material_name]}",
                        'x': str(offset_x),
                        'y': str(offset_y),
                        'width': str(render_size),  # IMMER volle Grid-Größe verwenden!
                        'height': str(render_size),  # Tile wird automatisch gestreckt
                        'data-material': material_name,
                        'data-grid': f"{grid_x},{grid_y}"
                    })
                else:
                    # KOMPATIBILITÄTS-MODUS: Direkte <image> Tags
                    # WIDTH/HEIGHT auf render_size setzen, auch wenn Bild kleiner ist!
                    if embed_images:
                        ET.SubElement(map_group, 'image', {
                            'x': str(offset_x),
                            'y': str(offset_y),
                            'width': str(render_size),  # Grid-Größe (z.B. 97px)
                            'height': str(render_size),  # Bild ist vielleicht nur 95px, wird gestreckt
                            'xlink:href': tile_data['data_uri'],
                            'data-material': material_name,
                            'data-grid': f"{grid_x},{grid_y}",
                            'preserveAspectRatio': 'none'  # Stretchable ohne Aspect-Ratio-Lock!
                        })
            
            tile_count += 1
            if tile_count % 50 == 0:
                print(f"   Verarbeitet: {tile_count}/{len(map_data)} Tiles...")
        
        # Animation-Gruppe (für animierte Tiles)
        anim_group = ET.SubElement(svg, 'g', {
            'id': 'animations',
            'data-layer': 'animation'
        })
        
        # GRID ENTFERNT: Für Spieler im Projektor-Modus nicht relevant
        # Grid-Linien sind nur für den Editor sinnvoll, nicht für die finale Projektion
        
        # Fog of War Gruppe (wird separat verwaltet)
        fog_group = ET.SubElement(svg, 'g', {
            'id': 'fog-of-war',
            'data-layer': 'fog',
            'opacity': '0.9'
        })
        
        # SVG formatieren und speichern
        self._save_svg(svg, output_path)
        
        print(f"✅ SVG erfolgreich exportiert: {output_path}")
        print(f"   Dateigröße: {os.path.getsize(output_path) / 1024:.1f} KB")
        
        return True
    
    def _render_material_for_svg(self, material_name, materials, renderer, size):
        """Rendert ein Material in der gewünschten Auflösung"""
        try:
            # SPECIAL: Village braucht 3x Größe für Rauch-Overlay!
            actual_size = size * 3 if material_name == 'village' else size
            
            # Material aus Dateisystem laden oder mit Renderer erzeugen
            # WICHTIG: Wenn material_name wie ein Pfad aussieht (enthält / oder \), direkt verwenden
            if '/' in material_name or '\\' in material_name:
                material_path = material_name  # Direkter Pfad zu importiertem Tile
            else:
                material_path = f"materials/{material_name}.png"  # Material aus Bundle
            
            if os.path.exists(material_path):
                # Lade existierende Textur
                img = Image.open(material_path)
            else:
                # Rendere mit AdvancedTextureRenderer
                if material_name in materials:
                    mat_data = materials[material_name]
                    # Village mit 3x Größe rendern!
                    img = renderer.render_texture(
                        material_name,
                        mat_data.get('type', 'basic'),
                        actual_size
                    )
                else:
                    # Fallback: Einfarbiges Tile
                    img = Image.new('RGB', (actual_size, actual_size), (50, 50, 50))
            
            # Auf Zielgröße skalieren
            if img.size != (actual_size, actual_size):
                img = img.resize((actual_size, actual_size), Image.LANCZOS)
            
            # BORDER-REMOVAL: Entferne Tile-Borders für saubere SVG
            img = self._remove_tile_borders(img)
            
            # PNG OPTIMIERUNG für kleinere Datei
            buffer = BytesIO()
            
            # Konvertiere zu RGB wenn RGBA (spart Speicher bei opaken Bildern)
            if img.mode == 'RGBA' and not self._has_transparency(img):
                img = img.convert('RGB')
            
            # Speichere mit maximaler Kompression
            img.save(buffer, format='PNG', optimize=True, compress_level=9)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            data_uri = f"data:image/png;base64,{img_base64}"
            
            return {
                'data_uri': data_uri,
                'file_path': material_path,
                'size': actual_size  # Korrekte Größe zurückgeben!
            }
            
        except Exception as e:
            print(f"⚠️ Fehler beim Rendern von {material_name}: {e}")
            return None
    
    def _has_transparency(self, img):
        """Prüft ob Bild echte Transparenz hat"""
        if img.mode != 'RGBA':
            return False
        
        alpha = img.getchannel('A')
        return alpha.getextrema()[0] < 255  # Mindestens ein Pixel nicht voll opak
    
    def _remove_tile_borders(self, img):
        """
        Entfernt Tile-Borders (dunkle Ränder) von einem Bild
        Prüft automatisch ob Borders vorhanden sind
        """
        try:
            width, height = img.size
            
            # Zu kleine Bilder nicht bearbeiten
            if width < 10 or height < 10:
                return img
            
            # Zu RGB konvertieren für Analyse
            if img.mode == 'RGBA':
                img_rgb = img.convert('RGB')
            else:
                img_rgb = img
            
            pixels = img_rgb.load()
            
            # Sample Ränder
            edge_samples = []
            for x in [0, width//4, width//2, width*3//4, width-1]:
                edge_samples.append(sum(pixels[x, 0]))
                edge_samples.append(sum(pixels[x, height-1]))
            
            for y in [0, height//4, height//2, height*3//4, height-1]:
                edge_samples.append(sum(pixels[0, y]))
                edge_samples.append(sum(pixels[width-1, y]))
            
            edge_brightness = sum(edge_samples) / len(edge_samples)
            
            # Sample Center
            cx, cy = width // 2, height // 2
            center_samples = [
                sum(pixels[cx, cy]),
                sum(pixels[cx-width//4, cy]),
                sum(pixels[cx+width//4, cy]),
                sum(pixels[cx, cy-height//4]),
                sum(pixels[cx, cy+height//4])
            ]
            center_brightness = sum(center_samples) / len(center_samples)
            
            # AGGRESSIV: Entferne Borders wenn Rand auch nur ETWAS dunkler ist
            # (Threshold: 0.95 = 5% dunkler)
            if edge_brightness < center_brightness * 0.95:
                # WICHTIG: Crop border OHNE resize zurück!
                # Stattdessen geben wir kleineres Bild zurück und lassen SVG mit Overlap platzieren
                border_size = 1  # 1px von jeder Seite = 2px total (besser als 2px = 4px total)
                cropped = img.crop((border_size, border_size, width-border_size, height-border_size))
                return cropped  # KEIN RESIZE - verhindert Interpolations-Artefakte!
            
            return img
            
        except Exception as e:
            return img
    
    def _save_svg(self, svg_element, output_path):
        """Speichert SVG mit schöner Formatierung"""
        # XML-String erstellen
        xml_string = ET.tostring(svg_element, encoding='unicode')
        
        # Schön formatieren
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent='  ')
        
        # XML-Deklaration nur einmal
        pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') 
                               if line.strip() and not line.strip().startswith('<?xml')])
        
        # Header hinzufügen
        final_xml = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + pretty_xml
        
        # Speichern
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_xml)
    
    def export_map_with_fog(self, map_data, materials, renderer, fog_data, output_path):
        """Exportiert Karte MIT Nebel-Overlay"""
        # Erst Basis-Karte exportieren
        success = self.export_map_to_svg(map_data, materials, renderer, output_path)
        
        if success and fog_data:
            # SVG wieder laden und Nebel hinzufügen
            self._add_fog_to_svg(output_path, fog_data)
        
        return success
    
    def _add_fog_to_svg(self, svg_path, fog_data):
        """Fügt Nebel-Layer zur SVG hinzu"""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # Finde fog-of-war Gruppe
            fog_group = root.find(".//*[@id='fog-of-war']")
            
            if fog_group is not None:
                # Nebel als Rechtecke hinzufügen
                for (x, y), visible in fog_data.items():
                    if not visible:
                        # Tile ist im Nebel
                        fog_rect = ET.SubElement(fog_group, 'rect', {
                            'x': str(x * self.tile_size),
                            'y': str(y * self.tile_size),
                            'width': str(self.tile_size),
                            'height': str(self.tile_size),
                            'fill': '#000000',
                            'data-fog': 'true',
                            'data-grid': f"{x},{y}"
                        })
                
                # SVG speichern
                tree.write(svg_path, encoding='utf-8', xml_declaration=True)
                print(f"✅ Nebel-Layer hinzugefügt")
        
        except Exception as e:
            print(f"⚠️ Fehler beim Hinzufügen von Nebel: {e}")


def test_svg_export():
    """Test-Funktion für SVG-Export"""
    print("🧪 SVG Export Test")
    
    # Beispiel Map-Daten
    test_map = {
        (0, 0): "gras",
        (1, 0): "wald",
        (0, 1): "wasser",
        (1, 1): "stein"
    }
    
    exporter = SVGMapExporter(tile_size=256)
    
    # Mock-Daten
    materials = {}
    
    # Einfacher Mock-Renderer
    class MockRenderer:
        def render_texture(self, name, typ, size):
            colors = {
                "gras": (100, 180, 100),
                "wald": (50, 100, 50),
                "wasser": (50, 100, 200),
                "stein": (150, 150, 150)
            }
            color = colors.get(name, (100, 100, 100))
            return Image.new('RGB', (size, size), color)
    
    renderer = MockRenderer()
    
    # Export durchführen
    exporter.export_map_to_svg(
        test_map,
        materials,
        renderer,
        "test_map.svg",
        embed_images=True,
        render_resolution="high"
    )


if __name__ == "__main__":
    test_svg_export()
