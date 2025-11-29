"""
Edge Detection für intelligente Darkness-Polygon-Anpassung
Erkennt Kanten in Texturen und passt Polygone automatisch an Wände/Strukturen an
"""
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from typing import List, Tuple
import math

class EdgeDetector:
    """Kantenerkennung für Texture-basierte Polygon-Optimierung"""
    
    def __init__(self):
        self.edge_strength_threshold = 50  # Mindest-Stärke für erkannte Kanten
        self.snap_distance = 15  # Maximale Distanz zum Snappen (Pixel)
        
    def detect_edges(self, image: Image.Image, blur_radius: int = 2) -> Image.Image:
        """
        Erkenne Kanten im Bild mit Sobel-Filter
        Returns: Grayscale Image mit Kantenstärken
        """
        # Konvertiere zu Grayscale
        gray = image.convert('L')
        
        # Leichter Blur um Rauschen zu reduzieren
        if blur_radius > 0:
            gray = gray.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Sobel-Filter für Kantenerkennung
        # Horizontale Kanten
        sobel_x = gray.filter(ImageFilter.Kernel((3, 3), 
            [-1, 0, 1,
             -2, 0, 2,
             -1, 0, 1], scale=1))
        
        # Vertikale Kanten
        sobel_y = gray.filter(ImageFilter.Kernel((3, 3), 
            [-1, -2, -1,
              0,  0,  0,
              1,  2,  1], scale=1))
        
        # Kombiniere zu Gradientenstärke: sqrt(x² + y²)
        sobel_x_array = np.array(sobel_x, dtype=np.float32)
        sobel_y_array = np.array(sobel_y, dtype=np.float32)
        
        gradient_magnitude = np.sqrt(sobel_x_array**2 + sobel_y_array**2)
        gradient_magnitude = np.clip(gradient_magnitude, 0, 255).astype(np.uint8)
        
        edge_image = Image.fromarray(gradient_magnitude)
        
        # Verstärke Kanten mit threshold
        edge_image = edge_image.point(lambda p: 255 if p > self.edge_strength_threshold else 0)
        
        return edge_image
    
    def snap_polygon_to_edges(self, polygon: List[Tuple[float, float]], 
                             edge_map: Image.Image,
                             snap_distance: int = None) -> List[Tuple[float, float]]:
        """
        Snappe Polygon-Punkte an nahe Kanten
        Args:
            polygon: Liste von (x, y) Punkten
            edge_map: Kantenbild (weiß=Kante, schwarz=keine Kante)
            snap_distance: Max. Distanz zum Snappen (None = use default)
        Returns: Optimiertes Polygon
        """
        if snap_distance is None:
            snap_distance = self.snap_distance
        
        edge_array = np.array(edge_map)
        height, width = edge_array.shape
        
        snapped_polygon = []
        
        for px, py in polygon:
            best_edge_point = (px, py)
            min_distance = float('inf')
            
            # Suche in lokaler Umgebung nach Kanten
            search_x_min = max(0, int(px - snap_distance))
            search_x_max = min(width, int(px + snap_distance + 1))
            search_y_min = max(0, int(py - snap_distance))
            search_y_max = min(height, int(py + snap_distance + 1))
            
            # Finde nächste Kante
            for sy in range(search_y_min, search_y_max):
                for sx in range(search_x_min, search_x_max):
                    if edge_array[sy, sx] > 128:  # Kante gefunden
                        dist = math.sqrt((sx - px)**2 + (sy - py)**2)
                        if dist < min_distance:
                            min_distance = dist
                            best_edge_point = (sx, sy)
            
            # Nur snappen wenn Kante nah genug
            if min_distance <= snap_distance:
                snapped_polygon.append(best_edge_point)
            else:
                snapped_polygon.append((px, py))
        
        return snapped_polygon
    
    def simplify_polygon(self, polygon: List[Tuple[float, float]], 
                        tolerance: float = 2.0) -> List[Tuple[float, float]]:
        """
        Vereinfache Polygon mit Ramer-Douglas-Peucker Algorithmus
        Reduziert Anzahl der Punkte bei ähnlicher Form
        """
        if len(polygon) < 3:
            return polygon
        
        def perpendicular_distance(point, line_start, line_end):
            """Berechne senkrechte Distanz von Punkt zu Linie"""
            x, y = point
            x1, y1 = line_start
            x2, y2 = line_end
            
            # Linienlänge
            line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            if line_length == 0:
                return math.sqrt((x - x1)**2 + (y - y1)**2)
            
            # Projektion
            t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / (line_length**2)))
            proj_x = x1 + t * (x2 - x1)
            proj_y = y1 + t * (y2 - y1)
            
            return math.sqrt((x - proj_x)**2 + (y - proj_y)**2)
        
        def rdp(points, epsilon):
            """Ramer-Douglas-Peucker rekursiv"""
            if len(points) < 3:
                return points
            
            # Finde Punkt mit größter Distanz zur Linie start->end
            max_dist = 0
            max_index = 0
            
            for i in range(1, len(points) - 1):
                dist = perpendicular_distance(points[i], points[0], points[-1])
                if dist > max_dist:
                    max_dist = dist
                    max_index = i
            
            # Wenn max. Distanz > epsilon, teile und rekursiere
            if max_dist > epsilon:
                left = rdp(points[:max_index + 1], epsilon)
                right = rdp(points[max_index:], epsilon)
                return left[:-1] + right
            else:
                return [points[0], points[-1]]
        
        # Schließe Polygon für Algorithmus
        closed_polygon = polygon + [polygon[0]]
        simplified = rdp(closed_polygon, tolerance)
        
        # Entferne letzten Punkt (Duplikat)
        return simplified[:-1] if len(simplified) > 1 else simplified
    
    def optimize_polygon(self, polygon: List[Tuple[float, float]], 
                        texture_image: Image.Image,
                        enable_edge_snap: bool = True,
                        enable_simplify: bool = True) -> List[Tuple[float, float]]:
        """
        Vollständige Polygon-Optimierung mit Edge-Snapping und Vereinfachung
        """
        optimized = polygon.copy()
        
        # Schritt 1: Edge Detection und Snapping
        if enable_edge_snap:
            edge_map = self.detect_edges(texture_image)
            optimized = self.snap_polygon_to_edges(optimized, edge_map)
        
        # Schritt 2: Vereinfachung
        if enable_simplify:
            optimized = self.simplify_polygon(optimized, tolerance=2.5)
        
        return optimized


class SmartDarknessDrawer:
    """Intelligentes Darkness-Zeichnen mit Edge-Awareness"""
    
    def __init__(self, edge_detector: EdgeDetector):
        self.edge_detector = edge_detector
        self.auto_snap = True  # Auto-Snap an Kanten
        self.auto_simplify = True  # Auto-Vereinfachung
    
    def process_drawn_polygon(self, polygon: List[Tuple[float, float]], 
                             texture_image: Image.Image) -> List[Tuple[float, float]]:
        """
        Verarbeite vom User gezeichnetes Polygon mit intelligenter Optimierung
        """
        if not polygon or len(polygon) < 3:
            return polygon
        
        print(f"🔍 Edge-Detection: Optimiere Polygon ({len(polygon)} Punkte)...")
        
        optimized = self.edge_detector.optimize_polygon(
            polygon, 
            texture_image,
            enable_edge_snap=self.auto_snap,
            enable_simplify=self.auto_simplify
        )
        
        print(f"✅ Optimiert: {len(optimized)} Punkte (vorher: {len(polygon)})")
        
        return optimized
