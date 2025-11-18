"""
Erweiterte Zeichen-Tools für professionelles 2.5D VTT
Curve, Polygon, Text und Transform Tools
"""
import tkinter as tk
from PIL import Image, ImageDraw
import math
from typing import List, Tuple, Optional

class BezierCurveTool:
    """Bezier-Kurven für organische Linien (Flüsse, Pfade)"""
    def __init__(self):
        self.points: List[Tuple[int, int]] = []
        self.is_active = False
        self.preview_points = []
        
    def add_point(self, x: int, y: int):
        """Füge Kontrollpunkt hinzu"""
        self.points.append((x, y))
        
    def clear(self):
        """Lösche alle Punkte"""
        self.points.clear()
        self.preview_points.clear()
        
    def calculate_bezier(self, t: float, points: List[Tuple[int, int]]) -> Tuple[float, float]:
        """Berechne Punkt auf Bezier-Kurve (Kubisch)"""
        n = len(points) - 1
        if n < 1:
            return points[0] if points else (0, 0)
        
        # De Casteljau's Algorithmus
        while n > 0:
            new_points = []
            for i in range(n):
                x = (1 - t) * points[i][0] + t * points[i + 1][0]
                y = (1 - t) * points[i][1] + t * points[i + 1][1]
                new_points.append((x, y))
            points = new_points
            n -= 1
        
        return points[0]
        
    def get_curve_points(self, segments: int = 50) -> List[Tuple[int, int]]:
        """Generiere Punkte entlang der Kurve"""
        if len(self.points) < 2:
            return self.points
        
        curve_points = []
        for i in range(segments + 1):
            t = i / segments
            point = self.calculate_bezier(t, self.points)
            curve_points.append((int(point[0]), int(point[1])))
        
        return curve_points
        
    def draw_preview(self, canvas, tile_size: int):
        """Zeichne Vorschau der Kurve"""
        if len(self.points) < 2:
            # Zeige nur Kontrollpunkte
            for x, y in self.points:
                canvas.create_oval(
                    x * tile_size - 3, y * tile_size - 3,
                    x * tile_size + 3, y * tile_size + 3,
                    fill="yellow", outline="orange", width=2,
                    tags="curve_preview"
                )
            return
        
        # Zeichne Kurve
        curve_points = self.get_curve_points()
        for i in range(len(curve_points) - 1):
            x1, y1 = curve_points[i]
            x2, y2 = curve_points[i + 1]
            canvas.create_line(
                x1 * tile_size, y1 * tile_size,
                x2 * tile_size, y2 * tile_size,
                fill="cyan", width=2, tags="curve_preview"
            )
        
        # Zeige Kontrollpunkte
        for x, y in self.points:
            canvas.create_oval(
                x * tile_size - 4, y * tile_size - 4,
                x * tile_size + 4, y * tile_size + 4,
                fill="yellow", outline="orange", width=2,
                tags="curve_preview"
            )
        
        # Verbinde Kontrollpunkte mit gestrichelten Linien
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            canvas.create_line(
                x1 * tile_size, y1 * tile_size,
                x2 * tile_size, y2 * tile_size,
                fill="orange", width=1, dash=(4, 4), tags="curve_preview"
            )


class PolygonTool:
    """Multi-Punkt-Polygon für komplexe Formen"""
    def __init__(self):
        self.points: List[Tuple[int, int]] = []
        self.is_active = False
        self.is_closed = False
        
    def add_point(self, x: int, y: int):
        """Füge Eckpunkt hinzu"""
        self.points.append((x, y))
        
    def close_polygon(self):
        """Schließe Polygon"""
        if len(self.points) >= 3:
            self.is_closed = True
            
    def clear(self):
        """Lösche Polygon"""
        self.points.clear()
        self.is_closed = False
        
    def is_point_inside(self, x: int, y: int) -> bool:
        """Prüfe ob Punkt innerhalb des Polygons liegt (Ray Casting)"""
        if not self.is_closed or len(self.points) < 3:
            return False
        
        intersections = 0
        n = len(self.points)
        
        for i in range(n):
            x1, y1 = self.points[i]
            x2, y2 = self.points[(i + 1) % n]
            
            # Prüfe ob Ray den Edge schneidet
            if (y1 > y) != (y2 > y):
                x_intersection = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if x < x_intersection:
                    intersections += 1
        
        return intersections % 2 == 1
        
    def get_tiles_inside(self, width: int, height: int) -> List[Tuple[int, int]]:
        """Gibt alle Tiles innerhalb des Polygons zurück"""
        if not self.is_closed:
            return []
        
        tiles = []
        for y in range(height):
            for x in range(width):
                if self.is_point_inside(x, y):
                    tiles.append((x, y))
        
        return tiles
        
    def draw_preview(self, canvas, tile_size: int):
        """Zeichne Vorschau des Polygons"""
        if len(self.points) < 1:
            return
        
        # Zeichne Linien zwischen Punkten
        for i in range(len(self.points)):
            x1, y1 = self.points[i]
            
            if i < len(self.points) - 1 or self.is_closed:
                x2, y2 = self.points[(i + 1) % len(self.points)]
                canvas.create_line(
                    x1 * tile_size, y1 * tile_size,
                    x2 * tile_size, y2 * tile_size,
                    fill="cyan", width=2, tags="polygon_preview"
                )
        
        # Zeige Eckpunkte
        for i, (x, y) in enumerate(self.points):
            color = "lime" if i == 0 else "yellow"
            canvas.create_oval(
                x * tile_size - 4, y * tile_size - 4,
                x * tile_size + 4, y * tile_size + 4,
                fill=color, outline="orange", width=2,
                tags="polygon_preview"
            )


class TextTool:
    """Text-Annotations für Beschriftungen"""
    def __init__(self):
        self.texts: List[dict] = []  # {"x": int, "y": int, "text": str, "font": str, "size": int, "color": str}
        
    def add_text(self, x: int, y: int, text: str, font: str = "Arial", size: int = 12, color: str = "white"):
        """Füge Text hinzu"""
        self.texts.append({
            "x": x,
            "y": y,
            "text": text,
            "font": font,
            "size": size,
            "color": color
        })
        
    def remove_text(self, index: int):
        """Entferne Text"""
        if 0 <= index < len(self.texts):
            del self.texts[index]
            
    def get_text_at(self, x: int, y: int, tolerance: int = 2) -> Optional[int]:
        """Finde Text an Position (gibt Index zurück)"""
        for i, text_obj in enumerate(self.texts):
            tx, ty = text_obj["x"], text_obj["y"]
            if abs(tx - x) <= tolerance and abs(ty - y) <= tolerance:
                return i
        return None
        
    def draw_texts(self, canvas, tile_size: int):
        """Zeichne alle Texte"""
        for text_obj in self.texts:
            x = text_obj["x"] * tile_size
            y = text_obj["y"] * tile_size
            
            # Schatten
            canvas.create_text(
                x + 1, y + 1,
                text=text_obj["text"],
                font=(text_obj["font"], text_obj["size"], "bold"),
                fill="black",
                tags="text_annotation"
            )
            
            # Text
            canvas.create_text(
                x, y,
                text=text_obj["text"],
                font=(text_obj["font"], text_obj["size"], "bold"),
                fill=text_obj["color"],
                tags="text_annotation"
            )


class TransformTool:
    """Transformation von Selections (Rotate, Scale, Flip)"""
    def __init__(self):
        self.rotation = 0  # Grad
        self.scale_x = 1.0
        self.scale_y = 1.0
        
    def rotate(self, degrees: float):
        """Rotiere um Grad"""
        self.rotation = (self.rotation + degrees) % 360
        
    def scale(self, factor_x: float, factor_y: float = None):
        """Skaliere"""
        if factor_y is None:
            factor_y = factor_x
        self.scale_x *= factor_x
        self.scale_y *= factor_y
        
    def flip_horizontal(self):
        """Horizontal spiegeln"""
        self.scale_x *= -1
        
    def flip_vertical(self):
        """Vertikal spiegeln"""
        self.scale_y *= -1
        
    def reset(self):
        """Zurücksetzen"""
        self.rotation = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        
    def transform_point(self, x: int, y: int, center_x: int, center_y: int) -> Tuple[int, int]:
        """Transformiere Punkt um Zentrum"""
        # Translate to origin
        tx = x - center_x
        ty = y - center_y
        
        # Scale
        tx *= self.scale_x
        ty *= self.scale_y
        
        # Rotate
        angle_rad = math.radians(self.rotation)
        rx = tx * math.cos(angle_rad) - ty * math.sin(angle_rad)
        ry = tx * math.sin(angle_rad) + ty * math.cos(angle_rad)
        
        # Translate back
        return (int(rx + center_x), int(ry + center_y))
