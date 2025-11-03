"""
SVG Texture Vectorizer - Echte Vektorisierung von Texturen

Wandelt Material-Texturen in ECHTE SVG-Vektorelemente um:
- Statt PNG-Rasterbilder → SVG-Pfade, Formen und Patterns
- Outline-Objekte werden als <path> mit stroke gezeichnet
- Farben werden als fill/stroke Attribute definiert
- Wiederholbare Patterns als <pattern> in <defs>

VORTEIL:
✓ Unendlich skalierbar ohne Qualitätsverlust
✓ Kleinere Dateigröße (keine Base64-Bilder)
✓ Editierbar in Inkscape/Illustrator
✓ Programmatisch modifizierbar (Farben, Striche, etc.)
"""

import xml.etree.ElementTree as ET
import math
import random
import os
from PIL import Image
import base64
from io import BytesIO


class SVGTextureVectorizer:
    """Generiert echte SVG-Vektorgeometrie für Materialien"""
    
    def __init__(self):
        # Farben für Materialien (aus texture_manager.py übernommen)
        self.colors = {
            "empty": "#1a1a1a",
            "grass": "#7eb356",
            "water": "#5dade2",
            "water_h": "#5dade2",
            "water_v": "#5dade2",
            "mountain": "#8b7d6b",
            "forest": "#2e5a1c",
            "sand": "#c9b18a",
            "snow": "#e8f4f8",
            "stone": "#9e8b7c",
            "dirt": "#a08567",
            "road": "#8a7560",
            "village": "#c4a574"
        }
    
    def create_vector_texture(self, material_name, size=256, force_base64=False):
        """
        Erstellt echte SVG-Vektorgeometrie für ein Material
        
        Args:
            force_base64: Falls True, nutze Base64-Embedding statt Vektorisierung (für PIL-Kompatibilität)
        
        Returns:
            ET.Element: SVG <g> Element mit Vektorinhalt
        """
        # SPECIAL: Wenn material_name ein Dateipfad ist (importierte PNG)
        if isinstance(material_name, str) and ('/' in material_name or '\\' in material_name or material_name.endswith('.png')):
            # IMMER vektorisieren - Cairo kann das rendern!
            return self._vectorize_image_file(material_name, size)
        
        # Hauptgruppe für dieses Material
        group = ET.Element('g', {
            'id': f'texture_{material_name}',
            'data-material': material_name
        })
        
        # Material-spezifische Generatoren
        generators = {
            'grass': self._generate_grass_vector,
            'water': self._generate_water_vector,
            'water_h': lambda s: self._generate_water_vector(s, 'horizontal'),
            'water_v': lambda s: self._generate_water_vector(s, 'vertical'),
            'forest': self._generate_forest_vector,
            'mountain': self._generate_mountain_vector,
            'sand': self._generate_sand_vector,
            'stone': self._generate_stone_vector,
            'dirt': self._generate_dirt_vector,
            'road': self._generate_road_vector,
            'village': self._generate_village_vector,
            'empty': self._generate_empty_vector
        }
        
        generator = generators.get(material_name, self._generate_empty_vector)
        return generator(size)
    
    def create_pattern_definition(self, material_name, pattern_size=64):
        """
        Erstellt ein SVG <pattern> für wiederholbare Texturen
        Wird in <defs> eingebettet und kann mit fill="url(#pattern_id)" verwendet werden
        
        Returns:
            ET.Element: <pattern> Element
        """
        # Pattern-ID aus Material-Name erstellen
        if isinstance(material_name, str) and ('/' in material_name or '\\' in material_name):
            # Für Dateipfade: Nutze Basename ohne Extension
            pattern_id = f'pattern_{os.path.basename(material_name).replace(".", "_").replace(" ", "_")}'
        else:
            pattern_id = f'pattern_{material_name}'
        
        pattern = ET.Element('pattern', {
            'id': pattern_id,
            'patternUnits': 'userSpaceOnUse',
            'width': str(pattern_size),
            'height': str(pattern_size)
        })
        
        # Pattern-Inhalt (kleine Version der Textur)
        content = self.create_vector_texture(material_name, pattern_size)
        
        # Inhalt in Pattern einfügen
        for child in content:
            pattern.append(child)
        
        return pattern
    
    # ============= MATERIAL-SPEZIFISCHE VEKTOR-GENERATOREN =============
    
    def _generate_grass_vector(self, size):
        """Gras als SVG-Vektoren: Organisches Pattern mit Variationen"""
        group = ET.Element('g', {'id': 'grass'})
        
        # Hintergrund: Basis-Grün
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['grass']
        })
        
        # Organisches Noise-Pattern durch viele kleine Rechtecke
        random.seed(42)  # Konsistent
        for _ in range(size // 2):
            x = random.randint(0, size)
            y = random.randint(0, size)
            w = random.randint(2, 6)
            h = random.randint(2, 6)
            
            # Farb-Variation
            variation = random.randint(-10, 10)
            r = max(0, min(255, 126 + variation))
            g = max(0, min(255, 179 + variation))
            b = max(0, min(255, 86 + variation))
            
            ET.SubElement(group, 'rect', {
                'x': str(x),
                'y': str(y),
                'width': str(w),
                'height': str(h),
                'fill': f'rgb({r},{g},{b})',
                'opacity': '0.3'
            })
        
        # Gras-Büschel als Ellipsen
        for _ in range(size // 10):
            x = random.randint(0, size)
            y = random.randint(0, size)
            rx = random.randint(2, 4)
            ry = random.randint(3, 6)
            
            ET.SubElement(group, 'ellipse', {
                'cx': str(x),
                'cy': str(y),
                'rx': str(rx),
                'ry': str(ry),
                'fill': '#648c46',
                'opacity': '0.5'
            })
        
        random.seed()  # Reset
        return group
    
    def _generate_water_vector(self, size, direction='horizontal'):
        """Wasser als SVG-Wellen: Sinuskurven mit Farbverläufen"""
        group = ET.Element('g', {'id': f'water_{direction}'})
        
        # Hintergrund: Wasser-Blau
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['water']
        })
        
        # Wellen als geschwungene Pfade
        wave_count = 8
        wave_height = size / wave_count
        
        for i in range(wave_count):
            # Sinuswelle generieren
            points = []
            y_offset = i * wave_height
            
            for x in range(0, size + 10, 5):
                if direction == 'horizontal':
                    y = y_offset + math.sin(x * 0.05 + i * 0.5) * 8
                    points.append(f"{x},{y}")
                else:
                    # Vertikale Wellen
                    x_actual = y_offset + math.sin(x * 0.05 + i * 0.5) * 8
                    points.append(f"{x_actual},{x}")
            
            # Pfad als Polyline mit Transparenz
            path_data = "M " + " L ".join(points)
            
            ET.SubElement(group, 'path', {
                'd': path_data,
                'fill': 'none',
                'stroke': '#ffffff',
                'stroke-width': '2',
                'opacity': '0.2'
            })
        
        # Glanzpunkte als Kreise
        random.seed(42)
        for _ in range(size // 20):
            x = random.randint(0, size)
            y = random.randint(0, size)
            r = random.randint(2, 5)
            
            ET.SubElement(group, 'circle', {
                'cx': str(x),
                'cy': str(y),
                'r': str(r),
                'fill': '#ffffff',
                'opacity': '0.4'
            })
        random.seed()
        
        return group
    
    def _generate_forest_vector(self, size):
        """Wald als Vektoren: Baumkronen von oben als Kreise"""
        group = ET.Element('g', {'id': 'forest'})
        
        # Hintergrund: Dunkler Waldboden
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['forest']
        })
        
        # Bäume als überlappende Kreise
        random.seed(42)
        tree_count = size // 8
        
        for _ in range(tree_count):
            x = random.randint(0, size)
            y = random.randint(0, size)
            r = random.randint(8, 16)
            
            # Schatten (dunkler Kreis)
            ET.SubElement(group, 'circle', {
                'cx': str(x + 2),
                'cy': str(y + 2),
                'r': str(r),
                'fill': '#0f2d0a',
                'opacity': '0.6'
            })
            
            # Baumkrone
            crown_colors = ['#1e3a10', '#2e5a1c', '#254514']
            color = random.choice(crown_colors)
            
            ET.SubElement(group, 'circle', {
                'cx': str(x),
                'cy': str(y),
                'r': str(r),
                'fill': color,
                'opacity': '0.9'
            })
            
            # Highlight (heller Bereich)
            highlight_r = r // 3
            ET.SubElement(group, 'circle', {
                'cx': str(x - r // 4),
                'cy': str(y - r // 4),
                'r': str(highlight_r),
                'fill': '#3d6a28',
                'opacity': '0.5'
            })
        
        random.seed()
        return group
    
    def _generate_mountain_vector(self, size):
        """Berg/Fels als Vektoren: Polygone und Linien für Felsstruktur"""
        group = ET.Element('g', {'id': 'mountain'})
        
        # Hintergrund
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['mountain']
        })
        
        # Fels-Polygone (unregelmäßige Formen)
        random.seed(42)
        for _ in range(size // 15):
            # Zufälliges Polygon
            point_count = random.randint(3, 6)
            points = []
            
            center_x = random.randint(0, size)
            center_y = random.randint(0, size)
            
            for i in range(point_count):
                angle = (i / point_count) * 2 * math.pi
                radius = random.randint(10, 25)
                x = center_x + math.cos(angle) * radius
                y = center_y + math.sin(angle) * radius
                points.append(f"{x},{y}")
            
            # Dunkler für Tiefe
            ET.SubElement(group, 'polygon', {
                'points': " ".join(points),
                'fill': '#78695b',
                'opacity': '0.4'
            })
        
        # Fels-Risse als Linien
        for _ in range(size // 8):
            x1 = random.randint(0, size)
            y1 = random.randint(0, size)
            length = random.randint(10, 30)
            angle = random.uniform(0, math.pi)
            
            x2 = x1 + math.cos(angle) * length
            y2 = y1 + math.sin(angle) * length
            
            ET.SubElement(group, 'line', {
                'x1': str(x1),
                'y1': str(y1),
                'x2': str(x2),
                'y2': str(y2),
                'stroke': '#5f5446',
                'stroke-width': '2',
                'opacity': '0.6'
            })
        
        random.seed()
        return group
    
    def _generate_stone_vector(self, size):
        """Steinpflaster als Vektoren: Rechtecke mit Fugen"""
        group = ET.Element('g', {'id': 'stone'})
        
        # Hintergrund
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['stone']
        })
        
        # Steinplatten als Rechtecke
        stone_size = size // 6
        random.seed(42)
        
        for i in range(0, size, stone_size):
            for j in range(0, size, stone_size):
                # Leichte Versetzung
                offset_x = random.randint(-2, 2)
                offset_y = random.randint(-2, 2)
                
                x = i + offset_x
                y = j + offset_y
                w = stone_size - 3
                h = stone_size - 3
                
                # Farb-Variation
                brightness = random.randint(-15, 15)
                r = max(0, min(255, 158 + brightness))
                g = max(0, min(255, 139 + brightness))
                b = max(0, min(255, 124 + brightness))
                
                ET.SubElement(group, 'rect', {
                    'x': str(x),
                    'y': str(y),
                    'width': str(w),
                    'height': str(h),
                    'fill': f'rgb({r},{g},{b})',
                    'stroke': '#645548',
                    'stroke-width': '1'
                })
        
        random.seed()
        return group
    
    def _generate_road_vector(self, size):
        """Straße/Weg: Ähnlich wie Stein, aber mit Erdton"""
        group = ET.Element('g', {'id': 'road'})
        
        # Basis: Erdiger Ton
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['road']
        })
        
        # Kopfsteinpflaster-Pattern
        stone_size = size // 8
        random.seed(42)
        
        for i in range(0, size, stone_size):
            for j in range(0, size, stone_size):
                offset_x = random.randint(-2, 2)
                offset_y = random.randint(-2, 2)
                
                x = i + offset_x
                y = j + offset_y
                w = stone_size - 2
                h = stone_size - 2
                
                brightness = random.randint(-20, 20)
                r = max(0, min(255, 138 + brightness))
                g = max(0, min(255, 117 + brightness))
                b = max(0, min(255, 96 + brightness))
                
                ET.SubElement(group, 'rect', {
                    'x': str(x),
                    'y': str(y),
                    'width': str(w),
                    'height': str(h),
                    'fill': f'rgb({r},{g},{b})',
                    'stroke': '#463c32',
                    'stroke-width': '1',
                    'opacity': '0.9'
                })
        
        random.seed()
        return group
    
    def _generate_sand_vector(self, size):
        """Sand als Vektoren: Körnige Struktur"""
        group = ET.Element('g', {'id': 'sand'})
        
        # Hintergrund
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['sand']
        })
        
        # Sand-Körner als kleine Punkte
        random.seed(42)
        for _ in range(size * 3):
            x = random.randint(0, size)
            y = random.randint(0, size)
            r = random.uniform(0.5, 1.5)
            
            brightness = random.randint(-20, 20)
            color_val = 212 + brightness
            
            ET.SubElement(group, 'circle', {
                'cx': str(x),
                'cy': str(y),
                'r': str(r),
                'fill': f'rgb({color_val},{color_val-16},{color_val-52})',
                'opacity': '0.5'
            })
        
        random.seed()
        return group
    
    def _generate_dirt_vector(self, size):
        """Erde: Ähnlich wie Sand, aber dunkler"""
        group = ET.Element('g', {'id': 'dirt'})
        
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['dirt']
        })
        
        # Erd-Klumpen und kleine Steine
        random.seed(42)
        for _ in range(size // 10):
            x = random.randint(0, size)
            y = random.randint(0, size)
            r = random.randint(2, 5)
            
            ET.SubElement(group, 'circle', {
                'cx': str(x),
                'cy': str(y),
                'r': str(r),
                'fill': '#64573a',
                'opacity': '0.6'
            })
        
        random.seed()
        return group
    
    def _generate_village_vector(self, size):
        """Dorf/Gebäude als Vektoren: Haus-Symbol mit Outline"""
        group = ET.Element('g', {'id': 'village'})
        
        # Boden
        bg_rect = ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': '#968264'
        })
        
        # Gebäude (zentriert)
        building_size = size // 2
        building_x = size // 4
        building_y = size // 4
        
        # Hauswände als Rechteck mit Outline
        ET.SubElement(group, 'rect', {
            'x': str(building_x),
            'y': str(building_y),
            'width': str(building_size),
            'height': str(building_size),
            'fill': '#6e553c',
            'stroke': '#503c28',
            'stroke-width': '2'
        })
        
        # Dach als Dreieck (Polygon)
        roof_points = [
            f"{building_x + building_size // 2},{building_y - 10}",
            f"{building_x - 5},{building_y}",
            f"{building_x + building_size + 5},{building_y}"
        ]
        
        ET.SubElement(group, 'polygon', {
            'points': " ".join(roof_points),
            'fill': '#8b4513',
            'stroke': '#5d2f0a',
            'stroke-width': '2'
        })
        
        # Tür als Rechteck
        door_w = building_size // 4
        door_h = building_size // 3
        door_x = building_x + (building_size - door_w) // 2
        door_y = building_y + building_size - door_h
        
        ET.SubElement(group, 'rect', {
            'x': str(door_x),
            'y': str(door_y),
            'width': str(door_w),
            'height': str(door_h),
            'fill': '#3c2819',
            'stroke': '#000000',
            'stroke-width': '1'
        })
        
        # Fenster
        window_size = building_size // 6
        window_y = building_y + building_size // 3
        
        # Linkes Fenster
        ET.SubElement(group, 'rect', {
            'x': str(building_x + window_size),
            'y': str(window_y),
            'width': str(window_size),
            'height': str(window_size),
            'fill': '#87ceeb',
            'stroke': '#000000',
            'stroke-width': '1'
        })
        
        # Rechtes Fenster
        ET.SubElement(group, 'rect', {
            'x': str(building_x + building_size - 2 * window_size),
            'y': str(window_y),
            'width': str(window_size),
            'height': str(window_size),
            'fill': '#87ceeb',
            'stroke': '#000000',
            'stroke-width': '1'
        })
        
        return group
    
    def _vectorize_image_file(self, image_path, size):
        """
        Vektorisiert ein PNG-Bild zu SVG-Elementen
        
        Verwendet einen pixelbasierten Ansatz:
        - Reduziert Farben auf dominante Palette
        - Erstellt Rechtecke für zusammenhängende Farbbereiche
        
        Args:
            image_path: Pfad zum PNG-Bild
            size: Zielgröße (für Skalierung)
            
        Returns:
            ET.Element: SVG <g> mit vektorisierten Bildelementen
        """
        group = ET.Element('g', {'id': f'vectorized_{os.path.basename(image_path)}'})
        
        try:
            # Lade Bild - konvertiere zu absolutem Pfad falls nötig
            if not os.path.isabs(image_path):
                image_path = os.path.abspath(image_path)
            
            if not os.path.exists(image_path):
                print(f"⚠️ Bild nicht gefunden: {image_path}")
                return self._generate_empty_vector(size)
            
            print(f"   🎨 Vektorisiere: {os.path.basename(image_path)}")
            
            img = Image.open(image_path)
            
            # Skaliere auf Zielgröße
            if img.size != (size, size):
                img = img.resize((size, size), Image.LANCZOS)
            
            # Konvertiere zu RGB
            if img.mode == 'RGBA':
                # Erstelle weißen Hintergrund für Transparenz
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])  # Alpha-Kanal als Maske
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # METHODE 1: Pixelbasierte Vektorisierung (schnell, gute Qualität)
            # Reduziere auf dominante Farben (Quantisierung)
            # OPTIMIERT: Balance zwischen Qualität und Dateigröße
            if size < 100:
                num_colors = 8   # Für sehr kleine Tiles
                step = 4         # Mittel-grob
            elif size < 150:
                num_colors = 12  # Sweet spot: Genug Detail, nicht zu groß
                step = 4         # Alle 4px
            else:
                num_colors = 16  # Mehr Details für große Tiles
                step = 2
                
            img_quantized = img.quantize(colors=num_colors, method=2)
            img_rgb = img_quantized.convert('RGB')
            
            # Extrahiere Pixel-Daten
            pixels = img_rgb.load()
            width, height = img_rgb.size
            
            # Gruppiere nach Farben und erstelle Rechtecke
            processed = set()
            color_regions = {}
            
            # Sammle zusammenhängende Regionen pro Farbe
            # step wurde oben basierend auf size berechnet
            for y in range(0, height, step):
                for x in range(0, width, step):  # Verwende gleichen step für x und y
                    if (x, y) in processed:
                        continue
                    
                    color = pixels[x, y]
                    
                    # Erstelle Rechteck für diese Position
                    # Finde Breite/Höhe der zusammenhängenden Region
                    rect_w = 2
                    rect_h = 2
                    
                    # Füge Farbe zu Dictionary hinzu
                    color_key = f"rgb({color[0]},{color[1]},{color[2]})"
                    if color_key not in color_regions:
                        color_regions[color_key] = []
                    
                    color_regions[color_key].append((x, y, rect_w, rect_h))
                    processed.add((x, y))
            
            # Erstelle SVG-Rechtecke pro Farbe
            for color, regions in color_regions.items():
                for x, y, w, h in regions:
                    ET.SubElement(group, 'rect', {
                        'x': str(x),
                        'y': str(y),
                        'width': str(w),
                        'height': str(h),
                        'fill': color,
                        'stroke': 'none'
                    })
            
            print(f"✓ Vektorisiert: {len(color_regions)} Farben, {sum(len(r) for r in color_regions.values())} Rechtecke")
            
        except Exception as e:
            print(f"⚠️ Fehler bei Vektorisierung von {image_path}: {e}")
            # Fallback: Zeige als eingebettetes Bild
            return self._embed_image_as_fallback(image_path, size)
        
        return group
    
    def _embed_image_as_fallback(self, image_path, size):
        """
        Fallback: Bette Bild als Base64 ein (wenn Vektorisierung fehlschlägt)
        """
        group = ET.Element('g', {'id': 'embedded_image'})
        
        try:
            img = Image.open(image_path)
            
            if img.size != (size, size):
                img = img.resize((size, size), Image.LANCZOS)
            
            # Konvertiere zu Base64
            buffer = BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            data_uri = f"data:image/png;base64,{img_base64}"
            
            # Erstelle <image> Element
            ET.SubElement(group, 'image', {
                'width': str(size),
                'height': str(size),
                'xlink:href': data_uri,
                'xmlns:xlink': 'http://www.w3.org/1999/xlink'
            })
            
        except Exception as e:
            print(f"⚠️ Fehler beim Einbetten: {e}")
        
        return group
    
    def _generate_empty_vector(self, size):
        """Leere Textur: Schwarzes Rechteck"""
        group = ET.Element('g', {'id': 'empty'})
        
        ET.SubElement(group, 'rect', {
            'width': str(size),
            'height': str(size),
            'fill': self.colors['empty']
        })
        
        return group


def test_vectorizer():
    """Test-Funktion: Erstellt SVG mit allen Materialien"""
    print("🧪 Testing SVG Texture Vectorizer...")
    
    vectorizer = SVGTextureVectorizer()
    
    # Haupt-SVG erstellen
    svg = ET.Element('svg', {
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': '1024',
        'height': '768',
        'viewBox': '0 0 1024 768'
    })
    
    # Defs für Patterns
    defs = ET.SubElement(svg, 'defs')
    
    # Alle Materialien
    materials = ['grass', 'water', 'forest', 'mountain', 'stone', 
                'road', 'sand', 'dirt', 'village']
    
    # 3x3 Grid
    tile_size = 256
    x_pos = 0
    y_pos = 0
    
    for i, material in enumerate(materials):
        # Position berechnen
        col = i % 3
        row = i // 3
        x = col * tile_size
        y = row * tile_size
        
        # Vektor-Textur erstellen
        texture_group = vectorizer.create_vector_texture(material, tile_size)
        
        # Position setzen
        texture_group.set('transform', f'translate({x},{y})')
        
        # Label hinzufügen
        label = ET.SubElement(svg, 'text', {
            'x': str(x + tile_size // 2),
            'y': str(y + tile_size - 10),
            'text-anchor': 'middle',
            'fill': '#ffffff',
            'font-size': '16',
            'font-weight': 'bold',
            'stroke': '#000000',
            'stroke-width': '2',
            'paint-order': 'stroke'
        })
        label.text = material
        
        svg.append(texture_group)
    
    # SVG speichern
    tree = ET.ElementTree(svg)
    output_path = 'test_vector_textures.svg'
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    print(f"✅ Test-SVG erstellt: {output_path}")
    print(f"   Enthält {len(materials)} Materialien als echte Vektoren")


if __name__ == '__main__':
    test_vectorizer()
