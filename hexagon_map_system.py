"""
Hexagon Map System - Erkennt und verwaltet hexagonale Karten

Features:
- SVG laden und Hexagone erkennen
- Tile-Parameter: Terrain, Schwierigkeit, Events, Wetter
- Speichern/Laden als JSON
- Integration ins Storyboard
"""

import math
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import xml.etree.ElementTree as ET
import random

# Versuche OpenCV für bessere Kantenerkennung
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("⚠️ OpenCV nicht verfügbar - verwende PIL für Hexagon-Erkennung")


class TerrainType(Enum):
    """Terrain-Typen mit Farben und Schwierigkeit"""
    PLAINS = ("Ebene", "#90EE90", 1)
    FOREST = ("Wald", "#228B22", 2)
    HILLS = ("Hügel", "#C4A574", 2)
    MOUNTAINS = ("Berge", "#808080", 4)
    WATER = ("Wasser", "#4169E1", 3)
    SWAMP = ("Sumpf", "#556B2F", 3)
    DESERT = ("Wüste", "#F4A460", 2)
    SNOW = ("Schnee", "#FFFAFA", 2)
    ROAD = ("Straße", "#8B7355", 0.5)
    VILLAGE = ("Siedlung", "#CD853F", 0)
    RUINS = ("Ruinen", "#696969", 1)
    DARK_FOREST = ("Düsterwald", "#1C3A1C", 4)
    
    def __init__(self, display_name: str, color: str, difficulty: float):
        self.display_name = display_name
        self.color = color
        self.difficulty = difficulty


class WeatherType(Enum):
    """Wetter-Typen"""
    CLEAR = ("Klar", "☀️")
    CLOUDY = ("Bewölkt", "☁️")
    RAIN = ("Regen", "🌧️")
    STORM = ("Sturm", "⛈️")
    SNOW = ("Schnee", "❄️")
    FOG = ("Nebel", "🌫️")
    WIND = ("Wind", "💨")
    
    def __init__(self, display_name: str, icon: str):
        self.display_name = display_name
        self.icon = icon


@dataclass
class TileEvent:
    """Ein Event auf einem Tile"""
    event_type: str  # "enemy", "treasure", "npc", "trap", "custom"
    name: str
    description: str = ""
    difficulty: int = 1  # 1-5
    is_random: bool = False  # Zufällig generiert oder GM-platziert
    probability: float = 1.0  # Wahrscheinlichkeit bei random events
    data: Dict = field(default_factory=dict)  # Zusätzliche Daten
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TileEvent':
        return cls(**data)


@dataclass 
class HexTile:
    """Ein einzelnes Hexagon-Tile"""
    # Position
    q: int  # Axial coordinate q (column)
    r: int  # Axial coordinate r (row)
    
    # Pixel-Position (Zentrum)
    center_x: float = 0.0
    center_y: float = 0.0
    
    # Terrain
    terrain: str = "PLAINS"
    terrain_name: str = ""  # Custom name wie "Alter Wald von Mirkwood"
    difficulty_modifier: float = 0.0  # Zusätzlicher Modifikator
    
    # Füllfarbe (aus Hintergrundbild extrahiert)
    fill_color: Optional[str] = None  # Hex-Farbe wie "#A0C050"
    
    # Events
    events: List[Dict] = field(default_factory=list)
    
    # Regionales Wetter (unabhängig vom globalen)
    local_weather: Optional[str] = None  # None = folgt globalem Wetter
    weather_intensity: float = 1.0
    
    # Sichtbarkeit
    explored: bool = False
    visible: bool = True
    
    # Zusätzliche Daten
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    @property
    def terrain_type(self) -> TerrainType:
        try:
            return TerrainType[self.terrain]
        except KeyError:
            return TerrainType.PLAINS
    
    @property
    def total_difficulty(self) -> float:
        """Gesamtschwierigkeit = Basis + Modifikator"""
        return self.terrain_type.difficulty + self.difficulty_modifier
    
    @property
    def display_color(self) -> str:
        """Farbe basierend auf fill_color (aus Bild) oder Terrain"""
        if self.fill_color:
            return self.fill_color
        return self.terrain_type.color
    
    def add_event(self, event: TileEvent):
        self.events.append(event.to_dict())
    
    def remove_event(self, index: int):
        if 0 <= index < len(self.events):
            self.events.pop(index)
    
    def to_dict(self) -> Dict:
        return {
            "q": self.q,
            "r": self.r,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "terrain": self.terrain,
            "terrain_name": self.terrain_name,
            "difficulty_modifier": self.difficulty_modifier,
            "fill_color": self.fill_color,
            "events": self.events,
            "local_weather": self.local_weather,
            "weather_intensity": self.weather_intensity,
            "explored": self.explored,
            "visible": self.visible,
            "notes": self.notes,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HexTile':
        return cls(**data)


class HexagonDetector:
    """Erkennt Hexagone in einem Bild/SVG"""
    
    def __init__(self):
        self.min_hex_size = 30  # Minimale Hexagon-Größe in Pixeln (erhöht!)
        self.max_hex_size = 500  # Maximale Hexagon-Größe
        
    def detect_from_svg(self, svg_path: str) -> Tuple[List[Dict], float, str]:
        """
        Erkennt Hexagone aus einer SVG-Datei
        
        Returns:
            (hexagons, hex_size, orientation)
            - hexagons: Liste von {center_x, center_y, vertices}
            - hex_size: Erkannte Hexagon-Größe
            - orientation: "pointy-top" oder "flat-top"
        """
        print(f"🔍 Lade SVG: {svg_path}")
        
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # SVG Namespace handling
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            
            # Suche nach Polygonen und Pfaden
            hexagons = []
            
            # 1. Suche <polygon> Elemente mit 6 Punkten
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]  # Remove namespace
                
                if tag == 'polygon':
                    points_str = elem.get('points', '')
                    points = self._parse_polygon_points(points_str)
                    
                    if len(points) == 6:
                        hex_data = self._analyze_hexagon(points)
                        if hex_data:
                            hexagons.append(hex_data)
                
                elif tag == 'path':
                    # Parse path data for hexagons
                    d = elem.get('d', '')
                    points = self._parse_path_to_points(d)
                    
                    if len(points) == 6 or len(points) == 7:  # 7 wenn geschlossen
                        hex_data = self._analyze_hexagon(points[:6])
                        if hex_data:
                            hexagons.append(hex_data)
            
            if hexagons:
                # Bestimme Orientierung und Größe
                hex_size = self._calculate_hex_size(hexagons)
                orientation = self._detect_orientation(hexagons)
                
                print(f"✅ {len(hexagons)} Hexagone erkannt")
                print(f"   Größe: {hex_size:.1f}px, Orientierung: {orientation}")
                
                return hexagons, hex_size, orientation
            
            # Fallback: Versuche Kantenerkennung auf gerendertem Bild
            print("⚠️ Keine Polygon-Hexagone gefunden, versuche Bildanalyse...")
            return self._detect_from_rendered_svg(svg_path)
            
        except Exception as e:
            print(f"❌ SVG-Parse-Fehler: {e}")
            return [], 0, "pointy-top"
    
    def _parse_polygon_points(self, points_str: str) -> List[Tuple[float, float]]:
        """Parse SVG polygon points string"""
        points = []
        try:
            # Format: "x1,y1 x2,y2 ..." oder "x1 y1 x2 y2 ..."
            parts = points_str.replace(',', ' ').split()
            for i in range(0, len(parts) - 1, 2):
                x = float(parts[i])
                y = float(parts[i + 1])
                points.append((x, y))
        except:
            pass
        return points
    
    def _parse_path_to_points(self, d: str) -> List[Tuple[float, float]]:
        """Parse SVG path data to points (vereinfacht)"""
        points = []
        try:
            # Vereinfachter Parser für M/L Befehle
            import re
            # Entferne Buchstaben außer Zahlen und Trennzeichen
            coords = re.findall(r'[-+]?\d*\.?\d+', d)
            
            for i in range(0, len(coords) - 1, 2):
                x = float(coords[i])
                y = float(coords[i + 1])
                points.append((x, y))
        except:
            pass
        return points
    
    def _analyze_hexagon(self, points: List[Tuple[float, float]]) -> Optional[Dict]:
        """Analysiere ob 6 Punkte ein gültiges Hexagon bilden"""
        if len(points) != 6:
            return None
        
        # Berechne Zentrum
        cx = sum(p[0] for p in points) / 6
        cy = sum(p[1] for p in points) / 6
        
        # Berechne Abstände vom Zentrum
        distances = [math.sqrt((p[0] - cx)**2 + (p[1] - cy)**2) for p in points]
        avg_dist = sum(distances) / 6
        
        # Prüfe ob alle Abstände ähnlich sind (Toleranz 20%)
        for d in distances:
            if abs(d - avg_dist) / avg_dist > 0.2:
                return None
        
        # Prüfe Winkel zwischen aufeinanderfolgenden Punkten
        angles = []
        for i in range(6):
            p1 = points[i]
            p2 = points[(i + 1) % 6]
            angle = math.atan2(p1[1] - cy, p1[0] - cx)
            angles.append(angle)
        
        return {
            "center_x": cx,
            "center_y": cy,
            "vertices": points,
            "radius": avg_dist
        }
    
    def _calculate_hex_size(self, hexagons: List[Dict]) -> float:
        """Berechne Hexagon-Größe - verwende Median für Robustheit"""
        if not hexagons:
            return 50.0
        
        radii = sorted([h["radius"] for h in hexagons])
        # Verwende Median statt Durchschnitt um Ausreißer zu ignorieren
        mid = len(radii) // 2
        if len(radii) % 2 == 0:
            median = (radii[mid - 1] + radii[mid]) / 2
        else:
            median = radii[mid]
        
        print(f"   Hex-Größen: min={radii[0]:.1f}, median={median:.1f}, max={radii[-1]:.1f}")
        return median
    
    def _detect_orientation(self, hexagons: List[Dict]) -> str:
        """Erkenne ob Hexagone pointy-top oder flat-top sind"""
        if not hexagons:
            return "pointy-top"
        
        # Nehme erstes Hexagon
        hex_data = hexagons[0]
        vertices = hex_data["vertices"]
        cx, cy = hex_data["center_x"], hex_data["center_y"]
        
        # Finde Punkt mit kleinstem Y (oben)
        top_point = min(vertices, key=lambda p: p[1])
        
        # Berechne Winkel vom Zentrum zum oberen Punkt
        angle = math.degrees(math.atan2(top_point[1] - cy, top_point[0] - cx))
        
        # Pointy-top: Spitze bei -90° (oben)
        # Flat-top: Kante bei -90° (oben)
        if abs(angle + 90) < 20:  # Nahe -90°
            return "pointy-top"
        else:
            return "flat-top"
    
    def _detect_from_rendered_svg(self, svg_path: str) -> Tuple[List[Dict], float, str]:
        """Fallback: Rendere SVG und erkenne Hexagone per Bildanalyse"""
        try:
            import cairosvg
            from io import BytesIO
            
            # Rendere SVG zu PNG
            png_data = cairosvg.svg2png(url=svg_path, scale=2)
            image = Image.open(BytesIO(png_data))
            
            return self.detect_from_image(image)
            
        except Exception as e:
            print(f"❌ Bild-Analyse fehlgeschlagen: {e}")
            return [], 0, "pointy-top"
    
    def detect_from_image(self, image: Image.Image) -> Tuple[List[Dict], float, str]:
        """Erkenne Hexagone aus einem Bild per Kantenerkennung"""
        
        if HAS_OPENCV:
            return self._detect_opencv(image)
        else:
            return self._detect_pil(image)
    
    def _detect_opencv(self, image: Image.Image) -> Tuple[List[Dict], float, str]:
        """OpenCV-basierte Hexagon-Erkennung - verbessert für gezeichnete Karten"""
        # Konvertiere zu OpenCV Format
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        hexagons = []
        
        # === METHODE 1: Mehrere Canny-Schwellwerte probieren ===
        for canny_low, canny_high in [(20, 80), (30, 100), (50, 150), (10, 50)]:
            edges = cv2.Canny(gray, canny_low, canny_high)
            
            # Morphologische Operationen um Linien zu verbinden
            kernel = np.ones((2, 2), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Finde Konturen - alle Hierarchie-Ebenen
            contours, hierarchy = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Prüfe Konturgröße
                area = cv2.contourArea(contour)
                if area < 100:  # Zu klein
                    continue
                
                # Approximiere Polygon mit verschiedenen Epsilon-Werten
                for eps_factor in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035]:
                    epsilon = eps_factor * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    # Prüfe auf 6 Ecken (Hexagon)
                    if len(approx) == 6:
                        points = [(p[0][0], p[0][1]) for p in approx]
                        hex_data = self._analyze_hexagon(points)
                        
                        if hex_data:
                            # Prüfe Größe - sehr erweiterte Grenzen
                            if self.min_hex_size * 0.3 <= hex_data["radius"] <= self.max_hex_size * 3:
                                # Prüfe ob nicht bereits erfasst (nahe an bestehendem)
                                is_duplicate = False
                                for existing in hexagons:
                                    dist = math.sqrt((hex_data["center_x"] - existing["center_x"])**2 + 
                                                   (hex_data["center_y"] - existing["center_y"])**2)
                                    if dist < hex_data["radius"] * 0.4:
                                        is_duplicate = True
                                        break
                                if not is_duplicate:
                                    hexagons.append(hex_data)
                        break  # Gefunden, nächste Kontur
            
            # Wenn wir genug gefunden haben, aufhören
            if len(hexagons) > 100:
                break
        
        # === METHODE 2: Template Matching für regelmäßige Grids ===
        if len(hexagons) < 10:
            print(f"   Wenige Hexagone gefunden ({len(hexagons)}), versuche Grid-Erkennung...")
            grid_hexagons = self._detect_hex_grid_pattern(gray, image.width, image.height)
            if grid_hexagons:
                hexagons.extend(grid_hexagons)
        
        if hexagons:
            # Entferne Duplikate
            hexagons = self._remove_duplicate_hexagons(hexagons)
            hex_size = self._calculate_hex_size(hexagons)
            orientation = self._detect_orientation(hexagons)
            print(f"✅ OpenCV: {len(hexagons)} Hexagone erkannt")
            return hexagons, hex_size, orientation
        
        return [], 0, "pointy-top"
    
    def _detect_hex_grid_pattern(self, gray: np.ndarray, width: int, height: int) -> List[Dict]:
        """Erkenne regelmäßiges Hex-Grid durch Linienanalyse"""
        try:
            # Hough-Linien für Hex-Grid-Muster
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=20, maxLineGap=10)
            
            if lines is None or len(lines) < 50:
                return []
            
            # Analysiere dominante Abstände zwischen parallelen Linien
            # Dies hilft die Hex-Größe zu bestimmen
            horizontal_gaps = []
            for i, line1 in enumerate(lines[:100]):
                x1, y1, x2, y2 = line1[0]
                angle = abs(math.atan2(y2-y1, x2-x1))
                # Nur fast-horizontale Linien
                if angle < 0.3 or angle > 2.8:
                    for line2 in lines[i+1:min(i+20, len(lines))]:
                        x3, y3, x4, y4 = line2[0]
                        angle2 = abs(math.atan2(y4-y3, x4-x3))
                        if angle2 < 0.3 or angle2 > 2.8:
                            gap = abs((y1+y2)/2 - (y3+y4)/2)
                            if 15 < gap < 100:
                                horizontal_gaps.append(gap)
            
            if not horizontal_gaps:
                return []
            
            # Häufigster Abstand = Hex-Höhe
            from collections import Counter
            gap_counts = Counter([int(g/5)*5 for g in horizontal_gaps])  # Runde auf 5er
            if not gap_counts:
                return []
            
            most_common_gap = gap_counts.most_common(1)[0][0]
            estimated_hex_height = most_common_gap * 2
            estimated_hex_size = estimated_hex_height / 1.732  # sqrt(3)
            
            print(f"   Grid-Muster erkannt: geschätzte Hex-Größe = {estimated_hex_size:.1f}px")
            
            # Erstelle Grid basierend auf geschätzter Größe
            return self._generate_grid_from_size(estimated_hex_size, width, height)
            
        except Exception as e:
            print(f"   Grid-Erkennung fehlgeschlagen: {e}")
            return []
    
    def _generate_grid_from_size(self, hex_size: float, width: int, height: int) -> List[Dict]:
        """Generiere Hex-Grid basierend auf erkannter Größe"""
        hexagons = []
        
        # Pointy-top Hexagon-Geometrie
        hex_width = hex_size * math.sqrt(3)
        hex_height = hex_size * 2
        vert_spacing = hex_height * 0.75
        
        rows = int(height / vert_spacing) + 1
        cols = int(width / hex_width) + 1
        
        for r in range(rows):
            for q in range(cols):
                # Offset für ungerade Reihen
                x_offset = (hex_width / 2) if (r % 2 == 1) else 0
                
                cx = q * hex_width + hex_width / 2 + x_offset
                cy = r * vert_spacing + hex_size
                
                if cx < width and cy < height:
                    hexagons.append({
                        "center_x": cx,
                        "center_y": cy,
                        "radius": hex_size,
                        "vertices": self._generate_hex_vertices(cx, cy, hex_size)
                    })
        
        return hexagons
    
    def _generate_hex_vertices(self, cx: float, cy: float, size: float) -> List[Tuple[float, float]]:
        """Generiere Hexagon-Vertices (pointy-top)"""
        vertices = []
        for i in range(6):
            angle = math.pi / 6 + i * math.pi / 3  # 30° + i*60°
            x = cx + size * math.cos(angle)
            y = cy + size * math.sin(angle)
            vertices.append((x, y))
        return vertices
    
    def _remove_duplicate_hexagons(self, hexagons: List[Dict]) -> List[Dict]:
        """Entferne doppelte Hexagone basierend auf Zentrum-Nähe"""
        unique = []
        for hex_data in hexagons:
            is_dup = False
            for existing in unique:
                dist = math.sqrt((hex_data["center_x"] - existing["center_x"])**2 + 
                               (hex_data["center_y"] - existing["center_y"])**2)
                min_dist = min(hex_data["radius"], existing["radius"]) * 0.3
                if dist < min_dist:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(hex_data)
        return unique
    
    def _detect_pil(self, image: Image.Image) -> Tuple[List[Dict], float, str]:
        """PIL-basierte Hexagon-Erkennung (Fallback)"""
        # Vereinfachte Erkennung über regelmäßiges Grid
        gray = image.convert('L')
        
        # Kantenerkennung mit Sobel
        from PIL import ImageFilter
        edges = gray.filter(ImageFilter.FIND_EDGES)
        
        # Für jetzt: Schätze Hexagon-Größe aus Bildgröße
        # Annahme: Karte hat ca. 10-20 Hexagone in der Breite
        estimated_hex_size = image.width / 15
        
        print(f"⚠️ PIL-Fallback: Geschätzte Hex-Größe {estimated_hex_size:.1f}px")
        print(f"   Für bessere Erkennung: pip install opencv-python")
        
        return [], estimated_hex_size, "pointy-top"


class HexagonMap:
    """Eine komplette Hexagon-Karte"""
    
    def __init__(self, name: str = "Neue Karte"):
        self.name = name
        self.tiles: Dict[Tuple[int, int], HexTile] = {}  # (q, r) -> HexTile
        
        # Hexagon-Parameter
        self.hex_size = 50.0  # Radius in Pixel
        self.orientation = "pointy-top"  # oder "flat-top"
        
        # Globales Wetter
        self.global_weather = "CLEAR"
        self.weather_intensity = 1.0
        
        # Karten-Metadaten
        self.svg_source: Optional[str] = None
        self.image_width = 0
        self.image_height = 0
        
        # Random Event Generator
        self.random_event_tables: Dict[str, List[Dict]] = {
            "enemy": [
                {"name": "Ork-Späher", "difficulty": 2},
                {"name": "Wolfsrudel", "difficulty": 2},
                {"name": "Räuberbande", "difficulty": 3},
                {"name": "Troll", "difficulty": 4},
                {"name": "Nazgûl-Präsenz", "difficulty": 5},
            ],
            "treasure": [
                {"name": "Vergessenes Lager", "difficulty": 1},
                {"name": "Alter Schrein", "difficulty": 2},
                {"name": "Elfische Ruine", "difficulty": 3},
            ],
            "encounter": [
                {"name": "Reisende", "difficulty": 1},
                {"name": "Händler", "difficulty": 1},
                {"name": "Waldläufer", "difficulty": 2},
            ]
        }
    
    def load_from_svg(self, svg_path: str) -> bool:
        """Lade Hexagone aus SVG"""
        detector = HexagonDetector()
        hexagons, hex_size, orientation = detector.detect_from_svg(svg_path)
        
        if not hexagons:
            print("⚠️ Keine Hexagone erkannt - erstelle Grid manuell")
            return False
        
        self.hex_size = hex_size
        self.orientation = orientation
        self.svg_source = svg_path
        
        # Konvertiere erkannte Hexagone zu Tiles
        for hex_data in hexagons:
            q, r = self._pixel_to_axial(hex_data["center_x"], hex_data["center_y"])
            
            tile = HexTile(
                q=q, r=r,
                center_x=hex_data["center_x"],
                center_y=hex_data["center_y"]
            )
            
            self.tiles[(q, r)] = tile
        
        print(f"✅ {len(self.tiles)} Hexagon-Tiles erstellt")
        return True
    
    def create_grid(self, cols: int, rows: int, hex_size: float = 50.0, 
                   orientation: str = "pointy-top"):
        """Erstelle ein regelmäßiges Hexagon-Grid"""
        self.hex_size = hex_size
        self.orientation = orientation
        self.tiles.clear()
        
        for r in range(rows):
            for q in range(cols):
                cx, cy = self._axial_to_pixel(q, r)
                
                tile = HexTile(
                    q=q, r=r,
                    center_x=cx,
                    center_y=cy
                )
                
                self.tiles[(q, r)] = tile
        
        print(f"✅ Grid erstellt: {cols}×{rows} = {len(self.tiles)} Tiles")
    
    def _axial_to_pixel(self, q: int, r: int) -> Tuple[float, float]:
        """Konvertiere axiale Koordinaten zu Pixel-Position"""
        size = self.hex_size
        
        if self.orientation == "pointy-top":
            x = size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
            y = size * (3 / 2 * r)
        else:  # flat-top
            x = size * (3 / 2 * q)
            y = size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
        
        return x + size, y + size  # Offset für Rand
    
    def _pixel_to_axial(self, x: float, y: float) -> Tuple[int, int]:
        """Konvertiere Pixel-Position zu axialen Koordinaten"""
        size = self.hex_size
        x -= size  # Offset entfernen
        y -= size
        
        if self.orientation == "pointy-top":
            q = (math.sqrt(3) / 3 * x - 1 / 3 * y) / size
            r = (2 / 3 * y) / size
        else:  # flat-top
            q = (2 / 3 * x) / size
            r = (-1 / 3 * x + math.sqrt(3) / 3 * y) / size
        
        return round(q), round(r)
    
    def get_tile_at_pixel(self, x: float, y: float) -> Optional[HexTile]:
        """Finde Tile an Pixel-Position - prüft tatsächliche Tile-Zentren"""
        best_tile = None
        best_dist = float('inf')
        
        # Finde das Tile dessen Zentrum am nächsten zur Klick-Position ist
        for tile in self.tiles.values():
            dist = math.sqrt((x - tile.center_x)**2 + (y - tile.center_y)**2)
            
            # Nur wenn innerhalb des Hex-Radius
            if dist < self.hex_size and dist < best_dist:
                best_dist = dist
                best_tile = tile
        
        return best_tile
    
    def set_terrain(self, q: int, r: int, terrain: str, name: str = ""):
        """Setze Terrain für ein Tile"""
        if (q, r) in self.tiles:
            self.tiles[(q, r)].terrain = terrain
            self.tiles[(q, r)].terrain_name = name
    
    def add_event(self, q: int, r: int, event: TileEvent):
        """Füge Event zu Tile hinzu"""
        if (q, r) in self.tiles:
            self.tiles[(q, r)].add_event(event)
    
    def set_local_weather(self, q: int, r: int, weather: Optional[str], intensity: float = 1.0):
        """Setze lokales Wetter für ein Tile"""
        if (q, r) in self.tiles:
            self.tiles[(q, r)].local_weather = weather
            self.tiles[(q, r)].weather_intensity = intensity
    
    def generate_random_events(self, event_type: str = "enemy", 
                               probability: float = 0.1,
                               terrain_filter: Optional[List[str]] = None):
        """Generiere zufällige Events auf Tiles"""
        if event_type not in self.random_event_tables:
            return
        
        events_placed = 0
        
        for (q, r), tile in self.tiles.items():
            # Filter nach Terrain
            if terrain_filter and tile.terrain not in terrain_filter:
                continue
            
            # Zufällige Platzierung
            if random.random() < probability:
                event_data = random.choice(self.random_event_tables[event_type])
                
                event = TileEvent(
                    event_type=event_type,
                    name=event_data["name"],
                    difficulty=event_data["difficulty"],
                    is_random=True,
                    probability=probability
                )
                
                tile.add_event(event)
                events_placed += 1
        
        print(f"🎲 {events_placed} zufällige {event_type}-Events platziert")
    
    def to_dict(self) -> Dict:
        """Exportiere als Dictionary"""
        return {
            "name": self.name,
            "hex_size": self.hex_size,
            "orientation": self.orientation,
            "global_weather": self.global_weather,
            "weather_intensity": self.weather_intensity,
            "svg_source": self.svg_source,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "tiles": {f"{q},{r}": tile.to_dict() for (q, r), tile in self.tiles.items()},
            "random_event_tables": self.random_event_tables
        }
    
    def save(self, filepath: str):
        """Speichere als JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"💾 Hexagon-Karte gespeichert: {filepath}")
    
    @classmethod
    def load(cls, filepath: str) -> 'HexagonMap':
        """Lade aus JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        hex_map = cls(data.get("name", "Geladene Karte"))
        hex_map.hex_size = data.get("hex_size", 50.0)
        hex_map.orientation = data.get("orientation", "pointy-top")
        hex_map.global_weather = data.get("global_weather", "CLEAR")
        hex_map.weather_intensity = data.get("weather_intensity", 1.0)
        hex_map.svg_source = data.get("svg_source")
        hex_map.image_width = data.get("image_width", 0)
        hex_map.image_height = data.get("image_height", 0)
        
        # Lade Tiles
        tiles_data = data.get("tiles", {})
        for key, tile_data in tiles_data.items():
            q, r = map(int, key.split(','))
            hex_map.tiles[(q, r)] = HexTile.from_dict(tile_data)
        
        # Lade Event-Tabellen
        hex_map.random_event_tables = data.get("random_event_tables", hex_map.random_event_tables)
        
        print(f"📂 Hexagon-Karte geladen: {len(hex_map.tiles)} Tiles")
        return hex_map
    
    def render_preview(self, width: int = 800, height: int = 600, 
                      show_terrain: bool = True,
                      show_events: bool = True,
                      show_weather: bool = True) -> Image.Image:
        """Rendere Vorschau der Hexagon-Karte"""
        img = Image.new('RGBA', (width, height), (40, 40, 40, 255))
        draw = ImageDraw.Draw(img)
        
        for (q, r), tile in self.tiles.items():
            # Berechne Hexagon-Vertices
            vertices = self._get_hex_vertices(tile.center_x, tile.center_y)
            
            # Terrain-Farbe
            if show_terrain:
                color = tile.display_color
                # Konvertiere Hex zu RGB
                r_val = int(color[1:3], 16)
                g_val = int(color[3:5], 16)
                b_val = int(color[5:7], 16)
                draw.polygon(vertices, fill=(r_val, g_val, b_val, 200))
            
            # Rahmen
            draw.polygon(vertices, outline=(100, 100, 100))
            
            # Event-Marker
            if show_events and tile.events:
                cx, cy = tile.center_x, tile.center_y
                draw.ellipse([cx-5, cy-5, cx+5, cy+5], fill=(255, 0, 0))
            
            # Wetter-Icon
            if show_weather and tile.local_weather:
                # Hier könnte ein Wetter-Icon gezeichnet werden
                pass
        
        return img
    
    def _get_hex_vertices(self, cx: float, cy: float) -> List[Tuple[float, float]]:
        """Berechne die 6 Eckpunkte eines Hexagons"""
        vertices = []
        
        for i in range(6):
            if self.orientation == "pointy-top":
                angle_deg = 60 * i - 30
            else:
                angle_deg = 60 * i
            
            angle_rad = math.radians(angle_deg)
            x = cx + self.hex_size * math.cos(angle_rad)
            y = cy + self.hex_size * math.sin(angle_rad)
            vertices.append((x, y))
        
        return vertices


# Test
if __name__ == "__main__":
    # Test: Erstelle Grid
    hex_map = HexagonMap("Mittelerde")
    hex_map.create_grid(10, 8, hex_size=40)
    
    # Setze einige Terrains
    hex_map.set_terrain(0, 0, "FOREST", "Alter Wald")
    hex_map.set_terrain(1, 0, "MOUNTAINS", "Nebelgebirge")
    hex_map.set_terrain(2, 1, "WATER", "Anduin")
    
    # Generiere zufällige Events
    hex_map.generate_random_events("enemy", probability=0.2)
    
    # Speichern
    hex_map.save("test_hexmap.json")
    
    # Laden
    loaded = HexagonMap.load("test_hexmap.json")
    print(f"Geladen: {loaded.name} mit {len(loaded.tiles)} Tiles")
