"""
Walls & Doors System - FoundryVTT-ähnliches Wand- und Türsystem
Ermöglicht Sichtlinien-Blocking und dynamische Türen
"""

import tkinter as tk
from tkinter import ttk, colorchooser
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum
import json
import math
import uuid

# UI Framework importieren
try:
    from ui_framework import UIColors, UISizes, WindowManager, BaseDialog
except ImportError:
    # Fallback
    class UIColors:
        BG_DARK = "#1a1a2e"
        BG_MEDIUM = "#16213e"
        BG_LIGHT = "#0f3460"
        ACCENT = "#e94560"
        TEXT = "#eaeaea"
        TEXT_DIM = "#888888"
        SUCCESS = "#4ecca3"
        WARNING = "#ffc107"
        DANGER = "#ff6b6b"
        BORDER = "#333355"


class WallType(Enum):
    """Verschiedene Wandtypen wie in FoundryVTT"""
    NORMAL = "normal"           # Blockiert Sicht und Bewegung
    TERRAIN = "terrain"         # Blockiert nur Bewegung
    INVISIBLE = "invisible"     # Blockiert nur Sicht
    ETHEREAL = "ethereal"       # Keine Blockierung (für Anmerkungen)
    DOOR = "door"              # Tür - kann geöffnet/geschlossen werden
    SECRET_DOOR = "secret"      # Geheime Tür - nur für GM sichtbar


class DoorState(Enum):
    """Türzustände"""
    CLOSED = "closed"
    OPEN = "open"
    LOCKED = "locked"


@dataclass
class Wall:
    """Einzelne Wand/Tür"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    wall_type: WallType = WallType.NORMAL
    door_state: DoorState = DoorState.CLOSED
    color: str = "#ffaa00"
    thickness: int = 4
    blocks_sight: bool = True
    blocks_movement: bool = True
    blocks_light: bool = True
    
    def __post_init__(self):
        """Blockierung basierend auf Wandtyp setzen"""
        self._update_blocking()
    
    def _update_blocking(self):
        """Blockierung aktualisieren basierend auf Typ und Türstatus"""
        if self.wall_type == WallType.NORMAL:
            self.blocks_sight = True
            self.blocks_movement = True
            self.blocks_light = True
        elif self.wall_type == WallType.TERRAIN:
            self.blocks_sight = False
            self.blocks_movement = True
            self.blocks_light = False
        elif self.wall_type == WallType.INVISIBLE:
            self.blocks_sight = True
            self.blocks_movement = False
            self.blocks_light = True
        elif self.wall_type == WallType.ETHEREAL:
            self.blocks_sight = False
            self.blocks_movement = False
            self.blocks_light = False
        elif self.wall_type in (WallType.DOOR, WallType.SECRET_DOOR):
            # Türen blockieren nur wenn geschlossen/gesperrt
            is_open = self.door_state == DoorState.OPEN
            self.blocks_sight = not is_open
            self.blocks_movement = not is_open
            self.blocks_light = not is_open
    
    def toggle_door(self) -> bool:
        """Tür öffnen/schließen. Gibt True zurück wenn möglich."""
        if self.wall_type not in (WallType.DOOR, WallType.SECRET_DOOR):
            return False
        
        if self.door_state == DoorState.LOCKED:
            return False
        
        if self.door_state == DoorState.CLOSED:
            self.door_state = DoorState.OPEN
        else:
            self.door_state = DoorState.CLOSED
        
        self._update_blocking()
        return True
    
    def unlock(self) -> bool:
        """Tür entsperren"""
        if self.door_state == DoorState.LOCKED:
            self.door_state = DoorState.CLOSED
            self._update_blocking()
            return True
        return False
    
    def lock(self) -> bool:
        """Tür sperren"""
        if self.wall_type in (WallType.DOOR, WallType.SECRET_DOOR):
            self.door_state = DoorState.LOCKED
            self._update_blocking()
            return True
        return False
    
    def get_midpoint(self) -> Tuple[float, float]:
        """Mittelpunkt der Wand"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    def get_length(self) -> float:
        """Länge der Wand"""
        return math.sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)
    
    def point_near_line(self, px: float, py: float, threshold: float = 10) -> bool:
        """Prüft ob ein Punkt nahe der Wand liegt"""
        # Vektor von Start zu Ende
        dx = self.x2 - self.x1
        dy = self.y2 - self.y1
        length_sq = dx * dx + dy * dy
        
        if length_sq == 0:
            # Wand hat keine Länge
            dist = math.sqrt((px - self.x1)**2 + (py - self.y1)**2)
            return dist <= threshold
        
        # Projektion des Punktes auf die Linie
        t = max(0, min(1, ((px - self.x1) * dx + (py - self.y1) * dy) / length_sq))
        
        # Nächster Punkt auf der Linie
        nearest_x = self.x1 + t * dx
        nearest_y = self.y1 + t * dy
        
        # Distanz zum nächsten Punkt
        dist = math.sqrt((px - nearest_x)**2 + (py - nearest_y)**2)
        return dist <= threshold
    
    def to_dict(self) -> dict:
        """Wand als Dictionary für JSON"""
        return {
            'id': self.id,
            'x1': self.x1,
            'y1': self.y1,
            'x2': self.x2,
            'y2': self.y2,
            'wall_type': self.wall_type.value,
            'door_state': self.door_state.value,
            'color': self.color,
            'thickness': self.thickness
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Wall':
        """Wand aus Dictionary erstellen"""
        wall = cls(
            id=data.get('id', str(uuid.uuid4())),
            x1=data.get('x1', 0),
            y1=data.get('y1', 0),
            x2=data.get('x2', 0),
            y2=data.get('y2', 0),
            wall_type=WallType(data.get('wall_type', 'normal')),
            door_state=DoorState(data.get('door_state', 'closed')),
            color=data.get('color', '#ffaa00'),
            thickness=data.get('thickness', 4)
        )
        return wall


class WallLayer:
    """Canvas-Layer für Wände - verwaltet das Zeichnen und Interaktion"""
    
    def __init__(self, canvas: tk.Canvas, wall_manager: 'WallManager'):
        self.canvas = canvas
        self.wall_manager = wall_manager
        
        # Zeichenmodus
        self.drawing_mode = False
        self.current_wall_type = WallType.NORMAL
        
        # Aktuell gezeichnete Wand
        self.start_point: Optional[Tuple[float, float]] = None
        self.preview_line_id = None
        
        # Auswahl
        self.selected_wall: Optional[Wall] = None
        
        # Canvas-IDs für Wände
        self.wall_canvas_ids: Dict[str, int] = {}
        self.door_icon_ids: Dict[str, int] = {}
        
        # Callbacks
        self.on_wall_selected: Optional[Callable[[Wall], None]] = None
        self.on_door_toggled: Optional[Callable[[Wall], None]] = None
        
        # Snap-to-Grid
        self.grid_size = 50
        self.snap_to_grid = True
        
        # Farben für verschiedene Wandtypen
        self.wall_colors = {
            WallType.NORMAL: "#ffaa00",
            WallType.TERRAIN: "#00ff00",
            WallType.INVISIBLE: "#0088ff",
            WallType.ETHEREAL: "#888888",
            WallType.DOOR: "#ff8800",
            WallType.SECRET_DOOR: "#ff00ff"
        }
    
    def enable_drawing(self, wall_type: WallType = WallType.NORMAL):
        """Zeichenmodus aktivieren"""
        self.drawing_mode = True
        self.current_wall_type = wall_type
        self.canvas.config(cursor="crosshair")
        
        # Event-Bindings
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-3>", self._cancel_drawing)
        self.canvas.bind("<Escape>", self._cancel_drawing)
    
    def disable_drawing(self):
        """Zeichenmodus deaktivieren"""
        self.drawing_mode = False
        self.start_point = None
        self.canvas.config(cursor="")
        
        # Preview löschen
        if self.preview_line_id:
            self.canvas.delete(self.preview_line_id)
            self.preview_line_id = None
        
        # Event-Bindings entfernen
        self.canvas.unbind("<Button-1>")
        self.canvas.unbind("<Motion>")
        self.canvas.unbind("<Button-3>")
        self.canvas.unbind("<Escape>")
    
    def enable_selection(self):
        """Auswahlmodus aktivieren"""
        self.drawing_mode = False
        self.canvas.config(cursor="hand2")
        self.canvas.bind("<Button-1>", self._on_select)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
    
    def _snap_to_grid(self, x: float, y: float) -> Tuple[float, float]:
        """Punkt zum Grid snappen"""
        if self.snap_to_grid and self.grid_size > 0:
            x = round(x / self.grid_size) * self.grid_size
            y = round(y / self.grid_size) * self.grid_size
        return x, y
    
    def _on_click(self, event):
        """Klick im Zeichenmodus"""
        x, y = self._snap_to_grid(event.x, event.y)
        
        if self.start_point is None:
            # Erster Punkt
            self.start_point = (x, y)
        else:
            # Zweiter Punkt - Wand erstellen
            wall = self.wall_manager.create_wall(
                x1=self.start_point[0],
                y1=self.start_point[1],
                x2=x,
                y2=y,
                wall_type=self.current_wall_type
            )
            
            # Wand zeichnen
            self._draw_wall(wall)
            
            # Für kontinuierliches Zeichnen: Ende wird neuer Start
            self.start_point = (x, y)
    
    def _on_motion(self, event):
        """Mausbewegung im Zeichenmodus"""
        if self.start_point is None:
            return
        
        x, y = self._snap_to_grid(event.x, event.y)
        
        # Preview-Linie aktualisieren
        if self.preview_line_id:
            self.canvas.delete(self.preview_line_id)
        
        color = self.wall_colors.get(self.current_wall_type, "#ffaa00")
        self.preview_line_id = self.canvas.create_line(
            self.start_point[0], self.start_point[1],
            x, y,
            fill=color,
            width=3,
            dash=(5, 5)
        )
    
    def _cancel_drawing(self, event=None):
        """Aktuelles Zeichnen abbrechen"""
        self.start_point = None
        if self.preview_line_id:
            self.canvas.delete(self.preview_line_id)
            self.preview_line_id = None
    
    def _on_select(self, event):
        """Wand bei Klick auswählen"""
        wall = self.wall_manager.get_wall_at(event.x, event.y)
        
        # Vorherige Auswahl aufheben
        if self.selected_wall:
            self._draw_wall(self.selected_wall)
        
        self.selected_wall = wall
        
        if wall:
            self._draw_wall(wall, selected=True)
            if self.on_wall_selected:
                self.on_wall_selected(wall)
    
    def _on_double_click(self, event):
        """Doppelklick auf Tür zum Öffnen/Schließen"""
        wall = self.wall_manager.get_wall_at(event.x, event.y)
        
        if wall and wall.wall_type in (WallType.DOOR, WallType.SECRET_DOOR):
            if wall.toggle_door():
                self._draw_wall(wall)
                if self.on_door_toggled:
                    self.on_door_toggled(wall)
    
    def _draw_wall(self, wall: Wall, selected: bool = False):
        """Wand auf Canvas zeichnen"""
        # Alte Zeichnung löschen
        if wall.id in self.wall_canvas_ids:
            self.canvas.delete(self.wall_canvas_ids[wall.id])
        if wall.id in self.door_icon_ids:
            self.canvas.delete(self.door_icon_ids[wall.id])
        
        # Farbe bestimmen
        color = self.wall_colors.get(wall.wall_type, wall.color)
        
        # Bei Türen: Zustand anzeigen
        if wall.wall_type in (WallType.DOOR, WallType.SECRET_DOOR):
            if wall.door_state == DoorState.OPEN:
                color = "#00ff00"  # Grün für offen
            elif wall.door_state == DoorState.LOCKED:
                color = "#ff0000"  # Rot für gesperrt
        
        # Liniendicke
        width = wall.thickness
        if selected:
            width += 2
        
        # Linie zeichnen
        dash = None
        if wall.wall_type == WallType.ETHEREAL:
            dash = (3, 3)
        elif wall.wall_type == WallType.INVISIBLE:
            dash = (8, 4)
        
        line_id = self.canvas.create_line(
            wall.x1, wall.y1, wall.x2, wall.y2,
            fill=color,
            width=width,
            dash=dash,
            tags=("wall", f"wall_{wall.id}")
        )
        self.wall_canvas_ids[wall.id] = line_id
        
        # Auswahl-Highlight
        if selected:
            # Endpunkte markieren
            for px, py in [(wall.x1, wall.y1), (wall.x2, wall.y2)]:
                self.canvas.create_oval(
                    px - 5, py - 5, px + 5, py + 5,
                    fill=UIColors.ACCENT,
                    outline="white",
                    tags=("wall", f"wall_{wall.id}_handle")
                )
        
        # Tür-Icon in der Mitte
        if wall.wall_type in (WallType.DOOR, WallType.SECRET_DOOR):
            mid_x, mid_y = wall.get_midpoint()
            
            # Icon je nach Zustand
            if wall.door_state == DoorState.LOCKED:
                icon = "🔒"
            elif wall.door_state == DoorState.OPEN:
                icon = "🚪"
            else:
                icon = "▭"
            
            icon_id = self.canvas.create_text(
                mid_x, mid_y,
                text=icon,
                font=("Segoe UI Emoji", 12),
                fill="white",
                tags=("wall", f"wall_{wall.id}_icon")
            )
            self.door_icon_ids[wall.id] = icon_id
    
    def redraw_all(self):
        """Alle Wände neu zeichnen"""
        # Alte Zeichnungen löschen
        self.canvas.delete("wall")
        self.wall_canvas_ids.clear()
        self.door_icon_ids.clear()
        
        # Alle Wände zeichnen
        for wall in self.wall_manager.walls:
            is_selected = self.selected_wall and self.selected_wall.id == wall.id
            self._draw_wall(wall, selected=is_selected)
    
    def delete_selected(self):
        """Ausgewählte Wand löschen"""
        if self.selected_wall:
            self.wall_manager.delete_wall(self.selected_wall.id)
            self.canvas.delete(f"wall_{self.selected_wall.id}")
            
            # Canvas-IDs entfernen
            if self.selected_wall.id in self.wall_canvas_ids:
                del self.wall_canvas_ids[self.selected_wall.id]
            if self.selected_wall.id in self.door_icon_ids:
                del self.door_icon_ids[self.selected_wall.id]
            
            self.selected_wall = None


class WallManager:
    """Verwaltet alle Wände einer Szene"""
    
    def __init__(self):
        self.walls: List[Wall] = []
    
    def create_wall(self, x1: float, y1: float, x2: float, y2: float,
                   wall_type: WallType = WallType.NORMAL) -> Wall:
        """Neue Wand erstellen"""
        wall = Wall(
            x1=x1, y1=y1,
            x2=x2, y2=y2,
            wall_type=wall_type
        )
        self.walls.append(wall)
        return wall
    
    def delete_wall(self, wall_id: str) -> bool:
        """Wand löschen"""
        for i, wall in enumerate(self.walls):
            if wall.id == wall_id:
                del self.walls[i]
                return True
        return False
    
    def get_wall(self, wall_id: str) -> Optional[Wall]:
        """Wand nach ID finden"""
        for wall in self.walls:
            if wall.id == wall_id:
                return wall
        return None
    
    def get_wall_at(self, x: float, y: float, threshold: float = 10) -> Optional[Wall]:
        """Wand an Position finden"""
        for wall in reversed(self.walls):  # Von oben nach unten
            if wall.point_near_line(x, y, threshold):
                return wall
        return None
    
    def get_walls_blocking_sight(self) -> List[Wall]:
        """Alle Wände die Sicht blockieren"""
        return [w for w in self.walls if w.blocks_sight]
    
    def get_walls_blocking_movement(self) -> List[Wall]:
        """Alle Wände die Bewegung blockieren"""
        return [w for w in self.walls if w.blocks_movement]
    
    def get_walls_blocking_light(self) -> List[Wall]:
        """Alle Wände die Licht blockieren"""
        return [w for w in self.walls if w.blocks_light]
    
    def check_line_of_sight(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Prüft ob Sichtlinie zwischen zwei Punkten frei ist"""
        for wall in self.walls:
            if not wall.blocks_sight:
                continue
            
            if self._lines_intersect(x1, y1, x2, y2,
                                    wall.x1, wall.y1, wall.x2, wall.y2):
                return False
        
        return True
    
    def _lines_intersect(self, x1: float, y1: float, x2: float, y2: float,
                        x3: float, y3: float, x4: float, y4: float) -> bool:
        """Prüft ob zwei Linien sich schneiden"""
        # Berechne Richtungsvektoren
        dx1 = x2 - x1
        dy1 = y2 - y1
        dx2 = x4 - x3
        dy2 = y4 - y3
        
        # Kreuzprodukt
        cross = dx1 * dy2 - dy1 * dx2
        
        if abs(cross) < 1e-10:
            # Linien sind parallel
            return False
        
        # Parameter für Schnittpunkt
        t1 = ((x3 - x1) * dy2 - (y3 - y1) * dx2) / cross
        t2 = ((x3 - x1) * dy1 - (y3 - y1) * dx1) / cross
        
        # Prüfen ob Schnittpunkt auf beiden Liniensegmenten liegt
        return 0 < t1 < 1 and 0 < t2 < 1
    
    def to_dict(self) -> dict:
        """Alle Wände als Dictionary"""
        return {
            'walls': [wall.to_dict() for wall in self.walls]
        }
    
    def from_dict(self, data: dict):
        """Wände aus Dictionary laden"""
        self.walls.clear()
        for wall_data in data.get('walls', []):
            wall = Wall.from_dict(wall_data)
            self.walls.append(wall)
    
    def save_to_file(self, filepath: str):
        """Wände in Datei speichern"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Wände aus Datei laden"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_dict(data)


class WallConfigDialog:
    """Dialog zur Konfiguration einer Wand"""
    
    def __init__(self, parent: tk.Tk, wall: Wall, on_save: Callable[[Wall], None]):
        self.wall = wall
        self.on_save = on_save
        
        # Dialog erstellen
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Wand bearbeiten")
        self.dialog.geometry("350x400")
        self.dialog.configure(bg=UIColors.BG_DARK)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        
        # Zentrieren
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 400) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """UI aufbauen"""
        main_frame = tk.Frame(self.dialog, bg=UIColors.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Titel
        tk.Label(
            main_frame,
            text="Wand-Eigenschaften",
            font=("Segoe UI", 14, "bold"),
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Wandtyp
        type_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        type_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            type_frame,
            text="Typ:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.type_var = tk.StringVar(value=self.wall.wall_type.value)
        type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.type_var,
            values=[t.value for t in WallType],
            state="readonly",
            width=20
        )
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Türstatus (nur für Türen)
        door_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        door_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            door_frame,
            text="Türstatus:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.door_var = tk.StringVar(value=self.wall.door_state.value)
        door_combo = ttk.Combobox(
            door_frame,
            textvariable=self.door_var,
            values=[s.value for s in DoorState],
            state="readonly",
            width=20
        )
        door_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Dicke
        thick_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        thick_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            thick_frame,
            text="Dicke:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.thickness_var = tk.IntVar(value=self.wall.thickness)
        thickness_spin = tk.Spinbox(
            thick_frame,
            from_=1,
            to=20,
            textvariable=self.thickness_var,
            width=10,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        )
        thickness_spin.pack(side=tk.LEFT)
        
        # Farbe
        color_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        color_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            color_frame,
            text="Farbe:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.color_preview = tk.Label(
            color_frame,
            text="  ",
            bg=self.wall.color,
            width=5,
            relief=tk.RAISED
        )
        self.color_preview.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            color_frame,
            text="Wählen...",
            command=self._choose_color,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        # Info
        info_frame = tk.LabelFrame(
            main_frame,
            text="Blockierung",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        )
        info_frame.pack(fill=tk.X, pady=15)
        
        self.sight_var = tk.BooleanVar(value=self.wall.blocks_sight)
        self.move_var = tk.BooleanVar(value=self.wall.blocks_movement)
        self.light_var = tk.BooleanVar(value=self.wall.blocks_light)
        
        tk.Checkbutton(
            info_frame,
            text="Blockiert Sicht",
            variable=self.sight_var,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        tk.Checkbutton(
            info_frame,
            text="Blockiert Bewegung",
            variable=self.move_var,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        tk.Checkbutton(
            info_frame,
            text="Blockiert Licht",
            variable=self.light_var,
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_MEDIUM
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        btn_frame.pack(fill=tk.X, pady=20)
        
        tk.Button(
            btn_frame,
            text="Speichern",
            command=self._save,
            bg=UIColors.SUCCESS,
            fg="white",
            width=10
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Abbrechen",
            command=self.dialog.destroy,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=10
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Löschen",
            command=self._delete,
            bg=UIColors.DANGER,
            fg="white",
            width=10
        ).pack(side=tk.LEFT, padx=5)
    
    def _choose_color(self):
        """Farbe wählen"""
        color = colorchooser.askcolor(
            initialcolor=self.wall.color,
            title="Wandfarbe wählen"
        )
        if color[1]:
            self.wall.color = color[1]
            self.color_preview.configure(bg=color[1])
    
    def _save(self):
        """Änderungen speichern"""
        self.wall.wall_type = WallType(self.type_var.get())
        self.wall.door_state = DoorState(self.door_var.get())
        self.wall.thickness = self.thickness_var.get()
        self.wall.blocks_sight = self.sight_var.get()
        self.wall.blocks_movement = self.move_var.get()
        self.wall.blocks_light = self.light_var.get()
        
        self.on_save(self.wall)
        self.dialog.destroy()
    
    def _delete(self):
        """Wand löschen"""
        self.wall = None
        self.on_save(None)
        self.dialog.destroy()


class WallToolbar(tk.Frame):
    """Toolbar für Wand-Werkzeuge"""
    
    def __init__(self, parent: tk.Widget, wall_layer: WallLayer):
        super().__init__(parent, bg=UIColors.BG_MEDIUM)
        self.wall_layer = wall_layer
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Toolbar-Buttons erstellen"""
        # Titel
        tk.Label(
            self,
            text="Wände & Türen",
            font=("Segoe UI", 11, "bold"),
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Auswahl-Tool
        self.select_btn = tk.Button(
            self,
            text="🔍 Auswahl",
            command=self._enable_select,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        )
        self.select_btn.pack(side=tk.LEFT, padx=2)
        
        # Wand-Tools
        wall_types = [
            (WallType.NORMAL, "⬛ Normal"),
            (WallType.TERRAIN, "🌿 Terrain"),
            (WallType.INVISIBLE, "👁️ Unsichtbar"),
            (WallType.DOOR, "🚪 Tür"),
            (WallType.SECRET_DOOR, "🔐 Geheimtür"),
        ]
        
        for wall_type, label in wall_types:
            btn = tk.Button(
                self,
                text=label,
                command=lambda wt=wall_type: self._enable_draw(wt),
                bg=UIColors.BG_LIGHT,
                fg=UIColors.TEXT
            )
            btn.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Löschen-Button
        tk.Button(
            self,
            text="🗑️ Löschen",
            command=self.wall_layer.delete_selected,
            bg=UIColors.DANGER,
            fg="white"
        ).pack(side=tk.LEFT, padx=2)
        
        # Snap-to-Grid Toggle
        self.snap_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self,
            text="Snap to Grid",
            variable=self.snap_var,
            command=self._toggle_snap,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            selectcolor=UIColors.BG_DARK
        ).pack(side=tk.RIGHT, padx=10)
    
    def _enable_select(self):
        """Auswahlmodus aktivieren"""
        self.wall_layer.disable_drawing()
        self.wall_layer.enable_selection()
    
    def _enable_draw(self, wall_type: WallType):
        """Zeichenmodus für Wandtyp aktivieren"""
        self.wall_layer.disable_drawing()
        self.wall_layer.enable_drawing(wall_type)
    
    def _toggle_snap(self):
        """Snap-to-Grid umschalten"""
        self.wall_layer.snap_to_grid = self.snap_var.get()


# Testfunktion
def test_walls_system():
    """Testet das Wand-System"""
    root = tk.Tk()
    root.title("Wand-System Test")
    root.geometry("1000x700")
    root.configure(bg=UIColors.BG_DARK)
    
    # Manager erstellen
    wall_manager = WallManager()
    
    # Canvas
    canvas = tk.Canvas(
        root,
        bg="#2a2a4a",
        highlightthickness=0
    )
    
    # Grid zeichnen
    for x in range(0, 1000, 50):
        canvas.create_line(x, 0, x, 700, fill="#3a3a5a", dash=(2, 4))
    for y in range(0, 700, 50):
        canvas.create_line(0, y, 1000, y, fill="#3a3a5a", dash=(2, 4))
    
    # Wall Layer
    wall_layer = WallLayer(canvas, wall_manager)
    
    # Toolbar
    toolbar = WallToolbar(root, wall_layer)
    toolbar.pack(fill=tk.X)
    
    canvas.pack(fill=tk.BOTH, expand=True)
    
    # Info-Label
    info_label = tk.Label(
        root,
        text="Links klicken um Wand zu zeichnen | Doppelklick auf Tür zum Öffnen/Schließen",
        bg=UIColors.BG_DARK,
        fg=UIColors.TEXT_DIM
    )
    info_label.pack(pady=5)
    
    # Test-Wände
    test_wall = wall_manager.create_wall(100, 100, 300, 100)
    wall_layer._draw_wall(test_wall)
    
    test_door = wall_manager.create_wall(300, 100, 300, 200, WallType.DOOR)
    wall_layer._draw_wall(test_door)
    
    root.mainloop()


if __name__ == "__main__":
    test_walls_system()
