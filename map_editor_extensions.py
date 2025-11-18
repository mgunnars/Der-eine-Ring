"""
Map-Editor Erweiterungen: Select-Tool, Context-Menu, Polygon-Tools
Modular, um den Haupt-Editor nicht zu überladen
"""
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageDraw
import math

class SelectTool:
    """Tool zum Auswählen von Objekten (Lights, Polygone)"""
    
    def __init__(self, editor):
        self.editor = editor
        self.selected_light = None
        self.selected_polygon = None
        
    def handle_click(self, x, y):
        """Verarbeite Klick im Select-Modus"""
        # Prüfe Lichtquellen (Tolerance 2 tiles)
        lighting_engine = self.editor.lighting_engine
        light_index = lighting_engine.get_light_at(x, y, tolerance=2)
        if light_index is not None:
            self.select_light(light_index)
            return True
        
        # Prüfe Dunkelheits-Polygone
        for i, polygon in enumerate(lighting_engine.darkness_polygons):
            if self.point_in_polygon(x, y, polygon):
                self.select_polygon(i)
                return True
        
        # Nichts getroffen - Auswahl aufheben
        self.deselect_all()
        return False
    
    def select_light(self, index):
        """Wähle Lichtquelle aus"""
        self.selected_light = index
        self.selected_polygon = None
        self.editor.show_light_context(index)
        self.editor.draw_grid()
        print(f"💡 Lichtquelle {index} ausgewählt")
    
    def select_polygon(self, index):
        """Wähle Polygon aus"""
        self.selected_polygon = index
        self.selected_light = None
        self.editor.show_polygon_context(index)
        self.editor.draw_grid()
        print(f"🌑 Polygon {index} ausgewählt")
    
    def deselect_all(self):
        """Hebe alle Auswahlen auf"""
        self.selected_light = None
        self.selected_polygon = None
        self.editor.hide_context_panel()
        self.editor.draw_grid()
        print("❌ Auswahl aufgehoben")
    
    def point_in_polygon(self, x, y, polygon):
        """Prüfe ob Punkt in Polygon liegt (Ray-Casting)"""
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def draw_selection_markers(self, canvas, tile_size):
        """Zeichne Auswahl-Marker"""
        lighting_engine = self.editor.lighting_engine
        
        # Lichtquellen-Marker
        if self.selected_light is not None and self.selected_light < len(lighting_engine.lights):
            light = lighting_engine.lights[self.selected_light]
            cx = light.x * tile_size + tile_size // 2
            cy = light.y * tile_size + tile_size // 2
            
            # Gelber Ring
            canvas.create_oval(
                cx - 15, cy - 15, cx + 15, cy + 15,
                outline="yellow", width=3, tags="selection"
            )
            # Äußerer pulsierender Ring
            canvas.create_oval(
                cx - 20, cy - 20, cx + 20, cy + 20,
                outline="yellow", width=1, dash=(5, 5), tags="selection"
            )
        
        # Polygon-Marker
        if self.selected_polygon is not None and self.selected_polygon < len(lighting_engine.darkness_polygons):
            polygon = lighting_engine.darkness_polygons[self.selected_polygon]
            
            # Zeichne Kontrollpunkte
            for px, py in polygon:
                cx = px * tile_size + tile_size // 2
                cy = py * tile_size + tile_size // 2
                
                # Großer gelber Punkt für jeden Polygon-Punkt
                canvas.create_oval(
                    cx - 6, cy - 6, cx + 6, cy + 6,
                    fill="yellow", outline="orange", width=2, tags="selection"
                )


class ContextPanel:
    """Kontextabhängiges Properties-Panel"""
    
    def __init__(self, parent_frame):
        self.panel = tk.Frame(parent_frame, bg="#1a1a1a", width=280)
        # Nicht packen - wird nur bei Bedarf angezeigt
        
        # Light Context
        self.light_frame = tk.LabelFrame(self.panel, text="💡 Lichtquelle", 
                                        bg="#1a1a1a", fg="white", font=("Arial", 10, "bold"))
        
        tk.Label(self.light_frame, text="Position:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.light_pos_label = tk.Label(self.light_frame, text="(0, 0)", 
                                        bg="#1a1a1a", fg="#aaa", font=("Arial", 9))
        self.light_pos_label.pack(anchor=tk.W, padx=5)
        
        tk.Label(self.light_frame, text="Typ:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.light_type_label = tk.Label(self.light_frame, text="torch", 
                                         bg="#1a1a1a", fg="#aaa", font=("Arial", 9))
        self.light_type_label.pack(anchor=tk.W, padx=5)
        
        tk.Label(self.light_frame, text="Radius:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.light_radius_var = tk.DoubleVar(value=5.0)
        self.light_radius_slider = tk.Scale(self.light_frame, from_=1, to=15, resolution=0.5,
                                            variable=self.light_radius_var,
                                            orient=tk.HORIZONTAL, bg="#2a2a2a", fg="white",
                                            highlightthickness=0, command=self._on_radius_change)
        self.light_radius_slider.pack(fill=tk.X, padx=5, pady=5)
        
        self.light_radius_label = tk.Label(self.light_frame, text="5.0", 
                                           bg="#1a1a1a", fg="yellow", font=("Arial", 10, "bold"))
        self.light_radius_label.pack(pady=(0, 5))
        
        tk.Label(self.light_frame, text="Intensität:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, padx=5)
        self.light_intensity_var = tk.DoubleVar(value=1.0)
        tk.Scale(self.light_frame, from_=0.1, to=1.5, resolution=0.1,
                variable=self.light_intensity_var, orient=tk.HORIZONTAL,
                bg="#2a2a2a", fg="white", highlightthickness=0,
                command=self._on_intensity_change).pack(fill=tk.X, padx=5, pady=5)
        
        btn_frame = tk.Frame(self.light_frame, bg="#1a1a1a")
        btn_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.delete_light_btn = tk.Button(btn_frame, text="🗑️ Löschen", bg="#7d2a2a", fg="white",
                                          font=("Arial", 9), command=None)
        self.delete_light_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        self.duplicate_light_btn = tk.Button(btn_frame, text="📋 Duplizieren", bg="#2a5d7d", fg="white",
                                             font=("Arial", 9), command=None)
        self.duplicate_light_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # Polygon Context
        self.polygon_frame = tk.LabelFrame(self.panel, text="🌑 Dunkelzone",
                                          bg="#1a1a1a", fg="white", font=("Arial", 10, "bold"))
        
        tk.Label(self.polygon_frame, text="Punkte:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.polygon_points_label = tk.Label(self.polygon_frame, text="0", 
                                             bg="#1a1a1a", fg="#aaa", font=("Arial", 9))
        self.polygon_points_label.pack(anchor=tk.W, padx=5, pady=(0, 10))
        
        poly_btn_frame = tk.Frame(self.polygon_frame, bg="#1a1a1a")
        poly_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.edit_polygon_btn = tk.Button(poly_btn_frame, text="✏️ Bearbeiten", bg="#2a5d8d", fg="white",
                                          font=("Arial", 9), command=None)
        self.edit_polygon_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        self.delete_polygon_btn = tk.Button(poly_btn_frame, text="🗑️ Löschen", bg="#7d2a2a", fg="white",
                                            font=("Arial", 9), command=None)
        self.delete_polygon_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        
        # Callbacks
        self.on_radius_change = None
        self.on_intensity_change = None
        self.on_delete_light = None
        self.on_duplicate_light = None
        self.on_edit_polygon = None
        self.on_delete_polygon = None
    
    def _on_radius_change(self, value):
        val = float(value)
        self.light_radius_label.config(text=f"{val:.1f}")
        if self.on_radius_change:
            self.on_radius_change(val)
    
    def _on_intensity_change(self, value):
        if self.on_intensity_change:
            self.on_intensity_change(float(value))
    
    def show_light_context(self, light):
        """Zeige Light-Properties"""
        self.panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.light_frame.pack(fill=tk.X, padx=5, pady=5)
        self.polygon_frame.pack_forget()
        
        self.light_pos_label.config(text=f"({light.x}, {light.y})")
        self.light_type_label.config(text=light.light_type)
        self.light_radius_var.set(light.radius)
        self.light_intensity_var.set(light.intensity)
    
    def show_polygon_context(self, polygon):
        """Zeige Polygon-Properties"""
        self.panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.polygon_frame.pack(fill=tk.X, padx=5, pady=5)
        self.light_frame.pack_forget()
        
        self.polygon_points_label.config(text=str(len(polygon)))
    
    def hide(self):
        """Verstecke Panel"""
        self.panel.pack_forget()


class SmoothPolygonDrawer:
    """Verbessertes Polygon-Zeichnen (pixelgenau, nicht tile-snapping)"""
    
    def __init__(self):
        self.points = []  # Canvas-Koordinaten (float)
        self.is_drawing = False
    
    def start(self):
        """Starte Zeichnung"""
        self.points = []
        self.is_drawing = True
    
    def add_point(self, canvas_x, canvas_y):
        """Füge Punkt hinzu (Canvas-Koordinaten)"""
        self.points.append((canvas_x, canvas_y))
    
    def finish(self, tile_size):
        """Beende Zeichnung und konvertiere zu Tile-Koordinaten"""
        if len(self.points) < 3:
            return None
        
        # Konvertiere Canvas → Tiles
        tile_polygon = [
            (int(cx / tile_size), int(cy / tile_size))
            for cx, cy in self.points
        ]
        
        # Entferne Duplikate
        unique_polygon = []
        for point in tile_polygon:
            if not unique_polygon or point != unique_polygon[-1]:
                unique_polygon.append(point)
        
        self.is_drawing = False
        self.points = []
        
        return unique_polygon if len(unique_polygon) >= 3 else None
    
    def cancel(self):
        """Abbrechen"""
        self.points = []
        self.is_drawing = False
    
    def draw_preview(self, canvas, color="magenta"):
        """Zeichne Preview der aktuellen Punkte"""
        canvas.delete("smooth_polygon_preview")
        
        if len(self.points) < 2:
            return
        
        # Zeichne Linien zwischen Punkten
        for i in range(len(self.points) - 1):
            x1, y1 = self.points[i]
            x2, y2 = self.points[i + 1]
            canvas.create_line(x1, y1, x2, y2, fill=color, width=2,
                             tags="smooth_polygon_preview")
        
        # Zeichne Punkte
        for cx, cy in self.points:
            canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                             fill=color, outline="white",
                             tags="smooth_polygon_preview")
        
        # Zeige Schließungs-Linie (gestrichelt)
        if len(self.points) >= 3:
            x1, y1 = self.points[-1]
            x2, y2 = self.points[0]
            canvas.create_line(x1, y1, x2, y2, fill=color, width=1,
                             dash=(5, 5), tags="smooth_polygon_preview")


class GeometryTools:
    """Geometrie-basierte Polygon-Erstellung (Rechteck, Kreis, etc.)"""
    
    @staticmethod
    def create_rectangle(x1, y1, x2, y2):
        """Erstelle Rechteck-Polygon"""
        return [
            (x1, y1),
            (x2, y1),
            (x2, y2),
            (x1, y2)
        ]
    
    @staticmethod
    def create_circle(cx, cy, radius, num_points=24):
        """Erstelle Kreis-Polygon"""
        import math
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            points.append((x, y))
        return points
    
    @staticmethod
    def create_ellipse(cx, cy, rx, ry, num_points=24):
        """Erstelle Ellipsen-Polygon"""
        import math
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            x = cx + int(rx * math.cos(angle))
            y = cy + int(ry * math.sin(angle))
            points.append((x, y))
        return points
