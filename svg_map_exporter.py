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

# Import für echte Vektor-Texturen
try:
    from svg_texture_vectorizer import SVGTextureVectorizer
    _vectorizer = SVGTextureVectorizer()
except ImportError:
    _vectorizer = None
    print("⚠️ SVGTextureVectorizer nicht verfügbar - nutze PNG-Fallback")


class SVGMapExporter:
    """Exportiert eine Karte als SVG mit eingebetteten Tiles"""
    
    def __init__(self, tile_size=256):
        self.tile_size = tile_size
    
    def _get_pattern_id(self, material_name):
        """Erstellt eine gültige Pattern-ID aus dem Material-Namen (konsistent mit SVGTextureVectorizer)"""
        if isinstance(material_name, str) and ('/' in material_name or '\\' in material_name):
            # Für Dateipfade: Nutze Basename ohne Extension
            return f'pattern_{os.path.basename(material_name).replace(".", "_").replace(" ", "_")}'
        else:
            return f'pattern_{material_name}'
        
    def export_map_to_svg(self, map_data, materials, renderer, output_path, 
                         embed_images=True, render_resolution="high", max_dimension=2048,
                         use_symbols=False, use_vectors=True):
        """
        Exportiert die komplette Karte als SVG
        
        Args:
            map_data: Dictionary mit Tile-Informationen {(x,y): material_name}
            materials: Dictionary mit Material-Daten
            renderer: AdvancedTextureRenderer Instanz
            output_path: Pfad zur SVG-Ausgabedatei
            embed_images: Wenn True, werden Bilder als base64 eingebettet (nur wenn use_vectors=False)
            render_resolution: "low" (256), "high" (512), "ultra" (1024)
            max_dimension: Maximale Pixel pro Dimension (Standard: 2048)
            use_symbols: Wenn True, nutze <symbol>+<use> (kleiner, aber PIL-inkompatibel!)
            use_vectors: Wenn True, nutze ECHTE SVG-Vektoren statt PNG-Einbettung (empfohlen!)
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
        print(f"   Modus: {'ECHTE VEKTOREN ✓' if use_vectors and _vectorizer else 'PNG-Einbettung'}")
        print(f"   Eingebettete Bilder: {embed_images}")
        
        # SVG Root erstellen
        svg = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'xmlns:xlink': 'http://www.w3.org/1999/xlink',
            'width': str(svg_width),
            'height': str(svg_height),
            'viewBox': f'0 0 {svg_width} {svg_height}',
            'version': '1.1',
            'shape-rendering': 'crispEdges'  # Verhindert Anti-Aliasing-Gaps beim Zoom!
        })
        
        # Metadata
        metadata = ET.SubElement(svg, 'metadata')
        ET.SubElement(metadata, 'title').text = "Der Eine Ring - VTT Map"
        ET.SubElement(metadata, 'description').text = f"Exported map: {width_tiles}x{height_tiles} tiles"
        
        # Definitions für wiederverwendbare Elemente (DEDUPLIZIERUNG!)
        defs = ET.SubElement(svg, 'defs')
        
        # CSS-Styles für besseres Tile-Rendering beim Zoom
        style = ET.SubElement(defs, 'style')
        style.text = """
            /* Verhindere Tile-Borders beim Herauszoomen */
            #map-tiles image {
                image-rendering: -webkit-optimize-contrast;
                image-rendering: crisp-edges;
            }
            /* Leichtes Aufhellen beim Herauszoomen (Borders weniger sichtbar) */
            @media (max-width: 1000px) {
                #map-tiles {
                    filter: brightness(1.05);
                }
            }
        """
        
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
        
        # VEKTOR-MODUS: Erstelle Vektor-Patterns in <defs>
        if use_vectors and _vectorizer:
            for material_name in unique_materials:
                # Hole texture_path aus Materials-Dictionary (für importierte Maps)
                material_info = materials.get(material_name, {})
                
                # ROBUST: Unterstütze verschiedene Dictionary-Formate
                if isinstance(material_info, dict):
                    # Format 1: {'type': 'custom', 'path': '...'}
                    # Format 2: {'texture_path': '...', 'name': '...', ...}
                    texture_path = material_info.get('path') or material_info.get('texture_path') or material_name
                else:
                    # Fallback: material_info ist selbst der Pfad
                    texture_path = material_info if isinstance(material_info, str) else material_name
                
                # DEBUG: Zeige ersten Pfad
                if material_name == list(unique_materials)[0]:
                    print(f"   🔍 DEBUG: material_name='{material_name}'")
                    print(f"   🔍 DEBUG: texture_path='{texture_path}'")
                
                # Pattern erstellen (mit echtem Dateipfad für importierte Maps)
                pattern = _vectorizer.create_pattern_definition(texture_path, render_size)
                defs.append(pattern)
                
                # Für Symbol-Modus auch Symbol erstellen
                if use_symbols:
                    symbol_id = f"mat_{material_name.replace(' ', '_').replace('.', '_')}"
                    material_symbols[material_name] = symbol_id
                    
                    symbol = ET.SubElement(defs, 'symbol', {
                        'id': symbol_id,
                        'viewBox': f"0 0 {render_size} {render_size}"
                    })
                    
                    # Rechteck mit Pattern-Fill
                    ET.SubElement(symbol, 'rect', {
                        'width': str(render_size),
                        'height': str(render_size),
                        'fill': f"url(#pattern_{material_name})"
                    })
        else:
            # PNG-MODUS: Alte Methode mit Base64-Bildern
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
        
        # PHASE 2: Tiles platzieren (mit Overlap um Zoom-Gaps zu vermeiden)
        tile_count = 0
        overlap = 2  # 2px Überlappung (wichtig beim Herauszoomen!)
        
        for (grid_x, grid_y), material_name in sorted(map_data.items()):
            # Position im SVG berechnen (mit Overlap-Offset)
            svg_x = (grid_x - min_x) * render_size - (overlap if grid_x > min_x else 0)
            svg_y = (grid_y - min_y) * render_size - (overlap if grid_y > min_y else 0)
            
            # Tile-Größe mit Overlap (außer am Rand)
            tile_width = render_size + (overlap if grid_x < max_x else 0)
            tile_height = render_size + (overlap if grid_y < max_y else 0)
            
            # Für Village: 2 Tiles nach oben verschieben (Rauch-Overlay) - nur im PNG-Modus
            if material_name == 'village' and not use_vectors:
                offset_y = svg_y - (render_size * 2)
                offset_x = svg_x
            else:
                offset_y = svg_y
                offset_x = svg_x
            
            # VEKTOR-MODUS: Rechteck mit Pattern-Fill
            if use_vectors and _vectorizer:
                # Hole texture_path aus Materials-Dictionary
                material_info = materials.get(material_name, {})
                
                # ROBUST: Unterstütze verschiedene Dictionary-Formate
                if isinstance(material_info, dict):
                    texture_path = material_info.get('path') or material_info.get('texture_path') or material_name
                else:
                    texture_path = material_info if isinstance(material_info, str) else material_name
                
                # Pattern-ID basiert auf texture_path (nicht material_name!)
                pattern_id = self._get_pattern_id(texture_path)
                
                # Rechteck mit Pattern als Fill
                ET.SubElement(map_group, 'rect', {
                    'x': str(offset_x),
                    'y': str(offset_y),
                    'width': str(tile_width),
                    'height': str(tile_height),
                    'fill': f"url(#{pattern_id})",
                    'data-material': material_name,
                    'data-grid': f"{grid_x},{grid_y}"
                })
            else:
                # PNG-MODUS: Alte Methode
                tile_data = material_cache.get(material_name)
                
                if tile_data:
                    # SYMBOL-MODUS: Referenz zum Symbol
                    if use_symbols and material_name in material_symbols:
                        ET.SubElement(map_group, 'use', {
                            'xlink:href': f"#{material_symbols[material_name]}",
                            'x': str(offset_x),
                            'y': str(offset_y),
                            'width': str(tile_width),  # Mit Overlap!
                            'height': str(tile_height),  # Mit Overlap!
                            'data-material': material_name,
                            'data-grid': f"{grid_x},{grid_y}"
                        })
                    else:
                        # KOMPATIBILITÄTS-MODUS: Direkte <image> Tags
                        if embed_images:
                            ET.SubElement(map_group, 'image', {
                                'x': str(offset_x),
                                'y': str(offset_y),
                                'width': str(tile_width),  # Mit Overlap!
                                'height': str(tile_height),  # Mit Overlap!
                                'xlink:href': tile_data['data_uri'],
                                'data-material': material_name,
                                'data-grid': f"{grid_x},{grid_y}",
                                'preserveAspectRatio': 'none'  # Stretchable!
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
        Entfernt nur die äußerste dunkle Border-Linie (1px)
        WICHTIG: Kein Resize zurück - Overlap im SVG kompensiert!
        """
        try:
            width, height = img.size
            
            # Zu kleine Bilder nicht bearbeiten
            if width < 20 or height < 20:
                return img
            
            # Prüfe ob dunkle Borders vorhanden sind
            if img.mode == 'RGBA':
                img_rgb = img.convert('RGB')
            else:
                img_rgb = img
            
            pixels = img_rgb.load()
            
            # Sample nur die äußerste Pixel-Reihe
            edge_samples = []
            for i in range(min(width, height)):
                if i < width:
                    edge_samples.append(sum(pixels[i, 0]))  # Top
                    edge_samples.append(sum(pixels[i, height-1]))  # Bottom
                if i < height:
                    edge_samples.append(sum(pixels[0, i]))  # Left
                    edge_samples.append(sum(pixels[width-1, i]))  # Right
            
            edge_brightness = sum(edge_samples) / len(edge_samples)
            
            # Sample innere Bereiche (nicht Center, sondern breiter)
            center_samples = []
            for x in range(5, width-5, max(1, width//20)):
                for y in range(5, height-5, max(1, height//20)):
                    center_samples.append(sum(pixels[x, y]))
            
            center_brightness = sum(center_samples) / len(center_samples) if center_samples else edge_brightness
            
            # Wenn Rand deutlich dunkler (>10%) → entfernen
            if edge_brightness < center_brightness * 0.90:
                # Nur 1px entfernen (weniger Artefakte!)
                cropped = img.crop((1, 1, width-1, height-1))
                return cropped  # KEIN RESIZE!
            
            return img
            
        except Exception as e:
            return img
    
    def _save_svg(self, svg_element, output_path):
        """Speichert SVG mit schöner Formatierung"""
        # XML-String erstellen (als UTF-8 Bytes)
        xml_bytes = ET.tostring(svg_element, encoding='utf-8')
        
        # Schön formatieren (parseString akzeptiert Bytes)
        dom = minidom.parseString(xml_bytes)
        pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
        
        # XML-Deklaration nur einmal
        lines = [line for line in pretty_xml.split('\n') 
                if line.strip() and not line.strip().startswith('<?xml')]
        pretty_xml = '\n'.join(lines)
        
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
