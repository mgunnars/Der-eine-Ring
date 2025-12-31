"""
Hexagon Map Editor - Visueller Editor für Hexagon-Karten

Features:
- SVG laden und Hexagone anzeigen
- Terrain-Modus: Klicken setzt Terrain
- Event-Modus: Events hinzufügen/bearbeiten
- Wetter-Modus: Regionales Wetter setzen
- Speichern/Laden
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
import math
import os
from typing import Optional, Tuple, List, Dict, Set

from hexagon_map_system import (
    HexagonMap, HexTile, HexagonDetector,
    TerrainType, WeatherType, TileEvent
)

# UI Framework importieren
try:
    from ui_framework import (
        UIColors, VTTButton, VTTLabel, VTTFrame,
        center_window, BaseDialog
    )
    UI_FRAMEWORK = True
except ImportError:
    UI_FRAMEWORK = False


class HexTilePropertiesDialog(tk.Toplevel):
    """Dialog zum Bearbeiten eines einzelnen Hex-Tiles"""
    
    def __init__(self, parent, tile: HexTile, hex_map: HexagonMap):
        super().__init__(parent)
        self.tile = tile
        self.hex_map = hex_map
        self.result = None
        
        self.title(f"Tile ({tile.q}, {tile.r}) bearbeiten")
        self.configure(bg="#1a1a2e")
        self.geometry("450x600")
        self.resizable(False, False)
        
        self._center_on_parent(parent)
        self._create_widgets()
        
        self.transient(parent)
        self.grab_set()
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        main = tk.Frame(self, bg="#1a1a2e", padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # === TERRAIN SECTION ===
        tk.Label(main, text="🗺️ TERRAIN", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(0, 5))
        
        terrain_frame = tk.Frame(main, bg="#16213e", padx=10, pady=10)
        terrain_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Terrain Dropdown
        tk.Label(terrain_frame, text="Typ:", bg="#16213e", fg="white").grid(row=0, column=0, sticky=tk.W)
        self.terrain_var = tk.StringVar(value=self.tile.terrain)
        terrain_combo = ttk.Combobox(terrain_frame, textvariable=self.terrain_var,
                                     values=[t.name for t in TerrainType], state="readonly", width=20)
        terrain_combo.grid(row=0, column=1, padx=5, pady=2)
        
        # Custom Name
        tk.Label(terrain_frame, text="Name:", bg="#16213e", fg="white").grid(row=1, column=0, sticky=tk.W)
        self.name_var = tk.StringVar(value=self.tile.terrain_name)
        tk.Entry(terrain_frame, textvariable=self.name_var, width=25,
                bg="#0f3460", fg="white", insertbackground="white").grid(row=1, column=1, padx=5, pady=2)
        
        # Difficulty Modifier
        tk.Label(terrain_frame, text="Schwierigkeit +/-:", bg="#16213e", fg="white").grid(row=2, column=0, sticky=tk.W)
        self.diff_var = tk.DoubleVar(value=self.tile.difficulty_modifier)
        tk.Scale(terrain_frame, variable=self.diff_var, from_=-2, to=3, resolution=0.5,
                orient=tk.HORIZONTAL, length=150, bg="#16213e", fg="white",
                highlightthickness=0).grid(row=2, column=1, padx=5, pady=2)
        
        # === WEATHER SECTION ===
        tk.Label(main, text="🌦️ LOKALES WETTER", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(10, 5))
        
        weather_frame = tk.Frame(main, bg="#16213e", padx=10, pady=10)
        weather_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.use_local_weather = tk.BooleanVar(value=self.tile.local_weather is not None)
        tk.Checkbutton(weather_frame, text="Eigenes Wetter (nicht global)", 
                      variable=self.use_local_weather, bg="#16213e", fg="white",
                      selectcolor="#0f3460", activebackground="#16213e",
                      command=self._toggle_weather).grid(row=0, column=0, columnspan=2, sticky=tk.W)
        
        tk.Label(weather_frame, text="Wetter:", bg="#16213e", fg="white").grid(row=1, column=0, sticky=tk.W)
        self.weather_var = tk.StringVar(value=self.tile.local_weather or "CLEAR")
        self.weather_combo = ttk.Combobox(weather_frame, textvariable=self.weather_var,
                                          values=[w.name for w in WeatherType], state="readonly", width=15)
        self.weather_combo.grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(weather_frame, text="Intensität:", bg="#16213e", fg="white").grid(row=2, column=0, sticky=tk.W)
        self.weather_intensity = tk.DoubleVar(value=self.tile.weather_intensity)
        tk.Scale(weather_frame, variable=self.weather_intensity, from_=0.1, to=2.0, resolution=0.1,
                orient=tk.HORIZONTAL, length=150, bg="#16213e", fg="white",
                highlightthickness=0).grid(row=2, column=1, padx=5, pady=2)
        
        self._toggle_weather()
        
        # === EVENTS SECTION ===
        tk.Label(main, text="⚔️ EVENTS", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(10, 5))
        
        events_frame = tk.Frame(main, bg="#16213e", padx=10, pady=10)
        events_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Event Liste
        self.events_listbox = tk.Listbox(events_frame, height=4, bg="#0f3460", fg="white",
                                         selectbackground="#e94560", width=40)
        self.events_listbox.pack(fill=tk.X, pady=(0, 5))
        self._populate_events()
        
        btn_frame = tk.Frame(events_frame, bg="#16213e")
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="➕ Hinzufügen", command=self._add_event,
                 bg="#0f3460", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="✏️ Bearbeiten", command=self._edit_event,
                 bg="#0f3460", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="🗑️ Löschen", command=self._delete_event,
                 bg="#0f3460", fg="white", width=12).pack(side=tk.LEFT, padx=2)
        
        # === NOTES ===
        tk.Label(main, text="📝 NOTIZEN", font=("Arial", 12, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W, pady=(10, 5))
        
        self.notes_text = tk.Text(main, height=3, bg="#0f3460", fg="white",
                                  insertbackground="white", wrap=tk.WORD)
        self.notes_text.pack(fill=tk.X, pady=(0, 10))
        self.notes_text.insert("1.0", self.tile.notes)
        
        # === BUTTONS ===
        btn_frame = tk.Frame(main, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(btn_frame, text="✓ Speichern", command=self._save,
                 bg="#28a745", fg="white", font=("Arial", 11, "bold"),
                 width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self.destroy,
                 bg="#dc3545", fg="white", font=("Arial", 11),
                 width=15).pack(side=tk.RIGHT, padx=5)
    
    def _toggle_weather(self):
        state = "readonly" if self.use_local_weather.get() else "disabled"
        self.weather_combo.configure(state=state)
    
    def _populate_events(self):
        self.events_listbox.delete(0, tk.END)
        for i, event in enumerate(self.tile.events):
            icon = {"enemy": "⚔️", "treasure": "💎", "npc": "👤", "trap": "⚠️"}.get(event.get("event_type", ""), "📌")
            self.events_listbox.insert(tk.END, f"{icon} {event.get('name', 'Event')} (Diff: {event.get('difficulty', 1)})")
    
    def _add_event(self):
        dialog = EventEditDialog(self, None)
        self.wait_window(dialog)
        if dialog.result:
            self.tile.events.append(dialog.result)
            self._populate_events()
    
    def _edit_event(self):
        sel = self.events_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        dialog = EventEditDialog(self, self.tile.events[idx])
        self.wait_window(dialog)
        if dialog.result:
            self.tile.events[idx] = dialog.result
            self._populate_events()
    
    def _delete_event(self):
        sel = self.events_listbox.curselection()
        if sel:
            self.tile.events.pop(sel[0])
            self._populate_events()
    
    def _save(self):
        self.tile.terrain = self.terrain_var.get()
        self.tile.terrain_name = self.name_var.get()
        self.tile.difficulty_modifier = self.diff_var.get()
        
        if self.use_local_weather.get():
            self.tile.local_weather = self.weather_var.get()
            self.tile.weather_intensity = self.weather_intensity.get()
        else:
            self.tile.local_weather = None
        
        self.tile.notes = self.notes_text.get("1.0", tk.END).strip()
        
        self.result = True
        self.destroy()


class EventEditDialog(tk.Toplevel):
    """Dialog zum Bearbeiten eines Events"""
    
    def __init__(self, parent, event_data: Optional[Dict]):
        super().__init__(parent)
        self.result = None
        self.event_data = event_data or {}
        
        self.title("Event bearbeiten" if event_data else "Neues Event")
        self.configure(bg="#1a1a2e")
        self.geometry("350x300")
        self.resizable(False, False)
        
        self._center_on_parent(parent)
        self._create_widgets()
        
        self.transient(parent)
        self.grab_set()
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 300) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        main = tk.Frame(self, bg="#1a1a2e", padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Event Type
        tk.Label(main, text="Typ:", bg="#1a1a2e", fg="white").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.type_var = tk.StringVar(value=self.event_data.get("event_type", "enemy"))
        type_combo = ttk.Combobox(main, textvariable=self.type_var,
                                  values=["enemy", "treasure", "npc", "trap", "custom"],
                                  state="readonly", width=20)
        type_combo.grid(row=0, column=1, pady=3)
        
        # Name
        tk.Label(main, text="Name:", bg="#1a1a2e", fg="white").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.name_var = tk.StringVar(value=self.event_data.get("name", ""))
        tk.Entry(main, textvariable=self.name_var, width=25,
                bg="#0f3460", fg="white", insertbackground="white").grid(row=1, column=1, pady=3)
        
        # Description
        tk.Label(main, text="Beschreibung:", bg="#1a1a2e", fg="white").grid(row=2, column=0, sticky=tk.NW, pady=3)
        self.desc_text = tk.Text(main, height=3, width=25, bg="#0f3460", fg="white",
                                insertbackground="white", wrap=tk.WORD)
        self.desc_text.grid(row=2, column=1, pady=3)
        self.desc_text.insert("1.0", self.event_data.get("description", ""))
        
        # Difficulty
        tk.Label(main, text="Schwierigkeit:", bg="#1a1a2e", fg="white").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.diff_var = tk.IntVar(value=self.event_data.get("difficulty", 1))
        tk.Scale(main, variable=self.diff_var, from_=1, to=5, orient=tk.HORIZONTAL,
                length=150, bg="#1a1a2e", fg="white", highlightthickness=0).grid(row=3, column=1, pady=3)
        
        # Random?
        self.random_var = tk.BooleanVar(value=self.event_data.get("is_random", False))
        tk.Checkbutton(main, text="Zufällig generiert", variable=self.random_var,
                      bg="#1a1a2e", fg="white", selectcolor="#0f3460",
                      activebackground="#1a1a2e").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=3)
        
        # Buttons
        btn_frame = tk.Frame(main, bg="#1a1a2e")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(15, 0))
        
        tk.Button(btn_frame, text="✓ OK", command=self._save,
                 bg="#28a745", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self.destroy,
                 bg="#dc3545", fg="white", width=10).pack(side=tk.LEFT, padx=5)
    
    def _save(self):
        self.result = {
            "event_type": self.type_var.get(),
            "name": self.name_var.get(),
            "description": self.desc_text.get("1.0", tk.END).strip(),
            "difficulty": self.diff_var.get(),
            "is_random": self.random_var.get(),
            "probability": 1.0,
            "data": {}
        }
        self.destroy()


class TextInputDialog(tk.Toplevel):
    """Dialog zur Eingabe von Text-Annotationen"""
    
    def __init__(self, parent, font_family: str, font_size: int, color: str, bold: bool, italic: bool):
        super().__init__(parent)
        self.result = None
        
        self.title("🏷️ Text hinzufügen")
        self.configure(bg="#1a1a2e")
        self.geometry("400x350")
        self.resizable(False, False)
        
        self._center_on_parent(parent)
        
        main = tk.Frame(self, bg="#1a1a2e", padx=15, pady=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Text-Eingabe
        tk.Label(main, text="Text:", font=("Arial", 11, "bold"),
                bg="#1a1a2e", fg="#e94560").pack(anchor=tk.W)
        self.text_entry = tk.Entry(main, font=("Arial", 14), width=35,
                                   bg="#0f3460", fg="white", insertbackground="white")
        self.text_entry.pack(fill=tk.X, pady=(5, 10))
        self.text_entry.focus()
        
        # Schriftart
        font_frame = tk.Frame(main, bg="#1a1a2e")
        font_frame.pack(fill=tk.X, pady=5)
        tk.Label(font_frame, text="Schrift:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.font_var = tk.StringVar(value=font_family)
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var,
                                  values=["Arial", "Times New Roman", "Courier New", "Georgia",
                                         "Verdana", "Comic Sans MS", "Impact", "Trebuchet MS"],
                                  state="readonly", width=18)
        font_combo.pack(side=tk.LEFT, padx=10)
        
        # Größe
        self.size_var = tk.IntVar(value=font_size)
        tk.Label(font_frame, text="Größe:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT, padx=(10, 0))
        size_spin = tk.Spinbox(font_frame, from_=8, to=72, textvariable=self.size_var,
                               width=4, bg="#0f3460", fg="white")
        size_spin.pack(side=tk.LEFT, padx=5)
        
        # Farbe
        color_frame = tk.Frame(main, bg="#1a1a2e")
        color_frame.pack(fill=tk.X, pady=5)
        tk.Label(color_frame, text="Farbe:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.color_var = color
        self.color_btn = tk.Button(color_frame, text="  ", width=4, bg=color,
                                   command=self._choose_color)
        self.color_btn.pack(side=tk.LEFT, padx=10)
        for c in ["#000000", "#ffffff", "#8B0000", "#006400", "#00008B", "#8B4513", "#FFD700"]:
            btn = tk.Button(color_frame, text="", width=1, bg=c,
                           command=lambda col=c: self._set_color(col))
            btn.pack(side=tk.LEFT, padx=1)
        
        # Stil
        style_frame = tk.Frame(main, bg="#1a1a2e")
        style_frame.pack(fill=tk.X, pady=5)
        self.bold_var = tk.BooleanVar(value=bold)
        tk.Checkbutton(style_frame, text="Fett", variable=self.bold_var,
                      bg="#1a1a2e", fg="white", selectcolor="#0f3460").pack(side=tk.LEFT)
        self.italic_var = tk.BooleanVar(value=italic)
        tk.Checkbutton(style_frame, text="Kursiv", variable=self.italic_var,
                      bg="#1a1a2e", fg="white", selectcolor="#0f3460").pack(side=tk.LEFT, padx=10)
        
        # Rotation
        rot_frame = tk.Frame(main, bg="#1a1a2e")
        rot_frame.pack(fill=tk.X, pady=5)
        tk.Label(rot_frame, text="Rotation:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.rotation_var = tk.IntVar(value=0)
        tk.Scale(rot_frame, variable=self.rotation_var, from_=-180, to=180,
                orient=tk.HORIZONTAL, length=150, bg="#1a1a2e", fg="white",
                highlightthickness=0, troughcolor="#0f3460").pack(side=tk.LEFT, padx=10)
        tk.Label(rot_frame, text="°", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        
        # Buttons
        btn_frame = tk.Frame(main, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        tk.Button(btn_frame, text="✓ Hinzufügen", command=self._ok,
                 bg="#28a745", fg="white", font=("Arial", 11),
                 relief=tk.FLAT, padx=20).pack(side=tk.LEFT, expand=True)
        tk.Button(btn_frame, text="✗ Abbrechen", command=self.destroy,
                 bg="#dc3545", fg="white", font=("Arial", 11),
                 relief=tk.FLAT, padx=20).pack(side=tk.LEFT, expand=True)
        
        # Enter-Taste zum Bestätigen
        self.text_entry.bind("<Return>", lambda e: self._ok())
        
        self.transient(parent)
        self.grab_set()
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
        self.geometry(f"+{x}+{y}")
    
    def _choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.color_var, title="Textfarbe wählen")
        if color[1]:
            self._set_color(color[1])
    
    def _set_color(self, color: str):
        self.color_var = color
        self.color_btn.configure(bg=color)
    
    def _ok(self):
        text = self.text_entry.get().strip()
        if not text:
            messagebox.showwarning("Kein Text", "Bitte gib einen Text ein.")
            return
        
        self.result = {
            'text': text,
            'font': self.font_var.get(),
            'size': self.size_var.get(),
            'color': self.color_var,
            'bold': self.bold_var.get(),
            'italic': self.italic_var.get(),
            'rotation': self.rotation_var.get()
        }
        self.destroy()


class HexagonMapEditor(tk.Toplevel):
    """Hauptfenster des Hexagon-Map-Editors"""
    
    def __init__(self, parent, hex_map: Optional[HexagonMap] = None):
        super().__init__(parent)
        
        self.hex_map = hex_map or HexagonMap("Neue Hexagon-Karte")
        self.current_tool = "select"  # select, draw_hex, place_extent, terrain, event, weather
        self.current_terrain = "PLAINS"
        self.current_weather = "RAIN"
        self.selected_tile: Optional[Tuple[int, int]] = None
        self.current_file_path: Optional[str] = None  # Pfad zur geladenen/gespeicherten Datei
        
        # Zoom/Pan
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None
        self.pan_start = None  # Für mittlere/rechte Maustaste Panning
        
        # Hex-Zeichenmodus Variablen
        self.draw_hex_start: Optional[Tuple[float, float]] = None  # Zentrum des Template-Hex
        self.template_hex_size: float = 0.0  # Größe des gezeichneten Hex
        self.preview_hex: Optional[List[Tuple[int, int]]] = None  # Vorschau-Vertices
        
        # === NORM-HEXAGON SYSTEM ===
        self.norm_hex_center: Optional[Tuple[float, float]] = None  # Zentrum des Norm-Hexagons
        self.norm_hex_size: float = 50.0  # Radius des Norm-Hexagons
        self.extent_hexagons: List[Tuple[float, float]] = []  # Liste von Extent-Punkten (Polygon-Grenze)
        self.dragging_norm_hex: bool = False  # Wird gerade das Norm-Hex verschoben?
        self.resizing_norm_hex: bool = False  # Wird gerade die Größe geändert?
        self.dragging_extent: Optional[int] = None  # Index des gezogenen Extent-Punkts
        
        # === MEHRFACHAUSWAHL ===
        self.selected_tiles: Set[Tuple[int, int]] = set()  # Mehrere ausgewählte Tiles
        self.selection_rect_start: Optional[Tuple[int, int]] = None  # Start der Rechteck-Auswahl
        self.shift_held: bool = False  # Shift für additive Auswahl
        
        # Background image
        self.bg_image: Optional[Image.Image] = None
        self.bg_photo: Optional[ImageTk.PhotoImage] = None
        self.bg_image_path: Optional[str] = None  # Pfad zum Hintergrundbild
        self.bg_visible: bool = True  # Hintergrund sichtbar?
        self.bg_opacity: float = 1.0  # Hintergrund-Transparenz (0-1)
        self.bg_on_top: bool = False  # Hintergrund über Tiles?
        self.hex_outline_only: bool = False  # Hexagone nur als Umriss (ohne Füllung)?
        self.hex_edge_blur: int = 0  # Blur-Stärke entlang der Hexagon-Kanten (0 = kein Blur)
        self.hex_outline_opacity: float = 1.0  # Opacity der Outlines (0-1)
        self.hex_outline_color: str = "#000000"  # Farbe der Hex-Outlines
        self.hex_outline_width: int = 2  # Breite der Hex-Outlines
        self.bg_with_hex_edges: Optional[Image.Image] = None  # Gecachtes Bild mit verschwommenen Kanten
        
        # === EINZELNES HEXAGON VERSCHIEBEN/SKALIEREN ===
        self.moving_tile: Optional[Tuple[int, int]] = None  # Tile das gerade verschoben wird
        self.scaling_tile: Optional[Tuple[int, int]] = None  # Tile das gerade skaliert wird
        self.tile_original_center: Optional[Tuple[float, float]] = None  # Original-Position beim Verschieben
        self.tile_scale_start_dist: float = 0.0  # Startdistanz beim Skalieren
        self.individual_tile_sizes: Dict[Tuple[int, int], float] = {}  # Individuelle Größen pro Tile
        
        # === TEXT ANNOTATIONS ===
        self.text_annotations: List[Dict] = []  # Liste von Text-Annotations
        self.current_text_color: str = "#000000"  # Aktuelle Textfarbe
        self.current_text_size: int = 16  # Aktuelle Schriftgröße
        self.current_font_family: str = "Arial"  # Aktuelle Schriftart
        self.current_text_bold: bool = False  # Fett?
        self.current_text_italic: bool = False  # Kursiv?
        self.selected_annotation: Optional[int] = None  # Index der ausgewählten Annotation
        self.dragging_annotation: Optional[int] = None  # Annotation die gerade verschoben wird
        
        self.title(f"🔷 Hexagon-Editor: {self.hex_map.name}")
        self.configure(bg="#1a1a2e")
        self.geometry("1200x800")
        
        self._create_ui()
        self._bind_events()
        
        # Zentrieren
        self.update_idletasks()
        self._center_on_screen()
    
    def _center_on_screen(self):
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2 - 30
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        # === TOOLBAR mit horizontalem Scrolling ===
        toolbar_container = tk.Frame(self, bg="#0f3460", height=60)
        toolbar_container.pack(fill=tk.X, side=tk.TOP)
        toolbar_container.pack_propagate(False)
        
        # Scroll-Buttons links
        scroll_left_btn = tk.Button(toolbar_container, text="◀", 
                                    command=lambda: self._scroll_toolbar(-200),
                                    bg="#e94560", fg="white", font=("Arial", 12, "bold"),
                                    relief=tk.FLAT, width=2)
        scroll_left_btn.pack(side=tk.LEFT, fill=tk.Y, padx=2)
        
        # Canvas für horizontales Scrolling
        self.toolbar_canvas = tk.Canvas(toolbar_container, bg="#0f3460", 
                                        height=50, highlightthickness=0)
        self.toolbar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scroll-Buttons rechts
        scroll_right_btn = tk.Button(toolbar_container, text="▶", 
                                     command=lambda: self._scroll_toolbar(200),
                                     bg="#e94560", fg="white", font=("Arial", 12, "bold"),
                                     relief=tk.FLAT, width=2)
        scroll_right_btn.pack(side=tk.RIGHT, fill=tk.Y, padx=2)
        
        # Innerer Frame für Toolbar-Inhalt
        toolbar = tk.Frame(self.toolbar_canvas, bg="#0f3460")
        self.toolbar_window = self.toolbar_canvas.create_window((0, 0), window=toolbar, anchor=tk.NW)
        
        # Tool Buttons
        tools = [
            ("🖱️ Auswahl", "select"),
            ("✋ Move/Scale", "move_scale"),
            ("🏷️ Text", "text"),
            ("✏️ Norm-Hex", "draw_hex"),
            ("📍 Extents", "place_extent"),
            ("🔲 Interpolieren", "interpolate"),
            ("🗑️ Löschen", "delete"),
            ("🗺️ Terrain", "terrain"),
            ("⚔️ Events", "event"),
            ("🐉 Boss", "boss"),
            ("🎮 Spawn", "spawn"),
        ]
        
        self.tool_buttons = {}
        for text, tool in tools:
            btn = tk.Button(toolbar, text=text, command=lambda t=tool: self._set_tool(t),
                           bg="#16213e", fg="white", font=("Arial", 10),
                           relief=tk.FLAT, padx=8, pady=5)
            btn.pack(side=tk.LEFT, padx=2, pady=8)
            self.tool_buttons[tool] = btn
        
        self._set_tool("select")
        
        # Separator
        tk.Frame(toolbar, bg="#e94560", width=2).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # File Buttons
        tk.Button(toolbar, text="📂 SVG laden", command=self._load_svg,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        tk.Button(toolbar, text="🖼️ Bild laden", command=self._load_image,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        tk.Button(toolbar, text="💾 Speichern", command=self._save_map,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        tk.Button(toolbar, text="📁 Laden", command=self._load_map,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Separator
        tk.Frame(toolbar, bg="#e94560", width=2).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Grid Button
        tk.Button(toolbar, text="🔲 Grid erstellen", command=self._create_grid_dialog,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Alle Löschen Button
        tk.Button(toolbar, text="🗑️ Alle löschen", command=self._clear_all_tiles,
                 bg="#dc3545", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Terrain Auto-Erkennung
        tk.Button(toolbar, text="🎨 Auto-Terrain", command=self._auto_detect_terrain,
                 bg="#17a2b8", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Random Events
        tk.Button(toolbar, text="🎲 Zufalls-Events", command=self._random_events_dialog,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Toolbar Scrollregion nach Aufbau aktualisieren
        toolbar.update_idletasks()
        self.toolbar_canvas.configure(scrollregion=self.toolbar_canvas.bbox("all"))
        
        # Mausrad-Scrolling für Toolbar
        self.toolbar_canvas.bind("<MouseWheel>", self._on_toolbar_mousewheel)
        toolbar.bind("<MouseWheel>", self._on_toolbar_mousewheel)
        
        # === MAIN AREA ===
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#1a1a2e",
                                    sashwidth=4, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # === CANVAS ===
        canvas_frame = tk.Frame(main_paned, bg="#2a2a2a")
        main_paned.add(canvas_frame, width=900)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#2a2a2a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # === SIDEBAR mit Scrollbar ===
        sidebar_container = tk.Frame(main_paned, bg="#16213e", width=280)
        main_paned.add(sidebar_container)
        
        # Canvas für Scrollbar
        sidebar_canvas = tk.Canvas(sidebar_container, bg="#16213e", highlightthickness=0)
        scrollbar = tk.Scrollbar(sidebar_container, orient=tk.VERTICAL, command=sidebar_canvas.yview)
        
        self.sidebar_frame = tk.Frame(sidebar_canvas, bg="#16213e")
        
        sidebar_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        sidebar_window = sidebar_canvas.create_window((0, 0), window=self.sidebar_frame, anchor=tk.NW)
        
        def configure_scroll(event):
            sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
            sidebar_canvas.itemconfig(sidebar_window, width=event.width)
        
        self.sidebar_frame.bind("<Configure>", configure_scroll)
        
        # Mausrad-Scrolling
        def on_mousewheel(event):
            sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        sidebar_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        self._create_sidebar(self.sidebar_frame)
    
    def _create_sidebar(self, parent):
        """Erstelle Sidebar mit Tool-Optionen"""
        
        # === HINTERGRUND-STEUERUNG (oben für bessere Sichtbarkeit) ===
        tk.Label(parent, text="🖼️ HINTERGRUND", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        bg_frame = tk.Frame(parent, bg="#16213e")
        bg_frame.pack(fill=tk.X, padx=10)
        
        # Sichtbarkeit Toggle
        self.bg_visible_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bg_frame, text="Hintergrund sichtbar", 
                      variable=self.bg_visible_var,
                      bg="#16213e", fg="white", selectcolor="#0f3460",
                      activebackground="#16213e",
                      command=self._toggle_background_var).pack(anchor=tk.W)
        
        # Layer Toggle
        self.bg_on_top_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bg_frame, text="Hintergrund über Tiles", 
                      variable=self.bg_on_top_var,
                      bg="#16213e", fg="white", selectcolor="#0f3460",
                      activebackground="#16213e",
                      command=self._toggle_bg_on_top_var).pack(anchor=tk.W)
        
        # Entfernen Button
        tk.Button(bg_frame, text="🗑️ Hintergrund entfernen", 
                 command=self._remove_background,
                 bg="#dc3545", fg="white", font=("Arial", 9),
                 relief=tk.FLAT).pack(fill=tk.X, pady=(5, 0))
        
        # === HEXAGON DARSTELLUNG ===
        tk.Label(parent, text="🔷 HEXAGON-ANZEIGE", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        hex_display_frame = tk.Frame(parent, bg="#16213e")
        hex_display_frame.pack(fill=tk.X, padx=10)
        
        # Nur Umriss Toggle
        self.hex_outline_only_var = tk.BooleanVar(value=self.hex_outline_only)
        tk.Checkbutton(hex_display_frame, text="Nur Umriss (keine Füllung)", 
                      variable=self.hex_outline_only_var,
                      bg="#16213e", fg="white", selectcolor="#0f3460",
                      activebackground="#16213e",
                      command=self._toggle_hex_outline_only).pack(anchor=tk.W)
        
        # Edge-Blur Slider (Kanten verschwimmen im Hintergrund)
        edge_blur_frame = tk.Frame(hex_display_frame, bg="#16213e")
        edge_blur_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Label(edge_blur_frame, text="Kanten-Blur:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.edge_blur_var = tk.IntVar(value=self.hex_edge_blur)
        tk.Scale(edge_blur_frame, variable=self.edge_blur_var, from_=0, to=20,
                orient=tk.HORIZONTAL, length=100,
                bg="#16213e", fg="white", highlightthickness=0,
                troughcolor="#0f3460", activebackground="#e94560",
                command=self._on_edge_blur_change).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Outline-Opacity Slider
        opacity_frame = tk.Frame(hex_display_frame, bg="#16213e")
        opacity_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(opacity_frame, text="Linien-Opacity:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.outline_opacity_var = tk.DoubleVar(value=self.hex_outline_opacity)
        tk.Scale(opacity_frame, variable=self.outline_opacity_var, from_=0.0, to=1.0,
                resolution=0.1, orient=tk.HORIZONTAL, length=100,
                bg="#16213e", fg="white", highlightthickness=0,
                troughcolor="#0f3460", activebackground="#e94560",
                command=self._on_outline_opacity_change).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Outline-Breite Slider
        outline_width_frame = tk.Frame(hex_display_frame, bg="#16213e")
        outline_width_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(outline_width_frame, text="Linienstärke:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.outline_width_var = tk.IntVar(value=self.hex_outline_width)
        tk.Scale(outline_width_frame, variable=self.outline_width_var, from_=1, to=5,
                orient=tk.HORIZONTAL, length=80,
                bg="#16213e", fg="white", highlightthickness=0,
                troughcolor="#0f3460", activebackground="#e94560",
                command=self._on_outline_width_change).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Outline-Farbe Button
        outline_color_frame = tk.Frame(hex_display_frame, bg="#16213e")
        outline_color_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(outline_color_frame, text="Linienfarbe:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.outline_color_btn = tk.Button(outline_color_frame, text="  ", width=3,
                                           bg=self.hex_outline_color,
                                           command=self._choose_outline_color)
        self.outline_color_btn.pack(side=tk.LEFT, padx=5)
        # Schnellauswahl-Farben
        for color in ["#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff", "#ffff00"]:
            btn = tk.Button(outline_color_frame, text="", width=1, bg=color,
                           command=lambda c=color: self._set_outline_color(c))
            btn.pack(side=tk.LEFT, padx=1)
        
        # === TEXT ANNOTATIONS ===
        tk.Label(parent, text="🏷️ TEXT", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        text_frame = tk.Frame(parent, bg="#16213e")
        text_frame.pack(fill=tk.X, padx=10)
        
        # Schriftgröße
        size_frame = tk.Frame(text_frame, bg="#16213e")
        size_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(size_frame, text="Größe:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.text_size_var = tk.IntVar(value=self.current_text_size)
        tk.Scale(size_frame, variable=self.text_size_var, from_=8, to=72,
                orient=tk.HORIZONTAL, length=100,
                bg="#16213e", fg="white", highlightthickness=0,
                troughcolor="#0f3460", activebackground="#e94560",
                command=self._on_text_size_change).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Schriftart
        font_frame = tk.Frame(text_frame, bg="#16213e")
        font_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(font_frame, text="Schrift:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.font_var = tk.StringVar(value=self.current_font_family)
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, 
                                  values=["Arial", "Times New Roman", "Courier New", "Georgia", 
                                         "Verdana", "Comic Sans MS", "Impact", "Trebuchet MS"],
                                  state="readonly", width=12)
        font_combo.pack(side=tk.LEFT, padx=5)
        font_combo.bind("<<ComboboxSelected>>", self._on_font_change)
        
        # Textfarbe
        color_frame = tk.Frame(text_frame, bg="#16213e")
        color_frame.pack(fill=tk.X, pady=(2, 0))
        tk.Label(color_frame, text="Farbe:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT)
        self.text_color_btn = tk.Button(color_frame, text="  ", width=3,
                                        bg=self.current_text_color,
                                        command=self._choose_text_color)
        self.text_color_btn.pack(side=tk.LEFT, padx=5)
        # Schnellauswahl-Farben
        for color in ["#000000", "#ffffff", "#8B0000", "#006400", "#00008B", "#8B4513"]:
            btn = tk.Button(color_frame, text="", width=1, bg=color,
                           command=lambda c=color: self._set_text_color(c))
            btn.pack(side=tk.LEFT, padx=1)
        
        # Stil-Buttons (Fett, Kursiv)
        style_frame = tk.Frame(text_frame, bg="#16213e")
        style_frame.pack(fill=tk.X, pady=(2, 0))
        self.bold_var = tk.BooleanVar(value=self.current_text_bold)
        tk.Checkbutton(style_frame, text="Fett", variable=self.bold_var,
                      bg="#16213e", fg="white", selectcolor="#0f3460",
                      activebackground="#16213e",
                      command=self._on_text_style_change).pack(side=tk.LEFT)
        self.italic_var = tk.BooleanVar(value=self.current_text_italic)
        tk.Checkbutton(style_frame, text="Kursiv", variable=self.italic_var,
                      bg="#16213e", fg="white", selectcolor="#0f3460",
                      activebackground="#16213e",
                      command=self._on_text_style_change).pack(side=tk.LEFT)
        
        # Text löschen Button
        tk.Button(text_frame, text="🗑️ Ausgewählten Text löschen",
                 command=self._delete_selected_annotation,
                 bg="#dc3545", fg="white", font=("Arial", 9),
                 relief=tk.FLAT).pack(fill=tk.X, pady=(5, 0))
        
        # === TERRAIN PALETTE ===
        tk.Label(parent, text="🗺️ TERRAIN", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        terrain_frame = tk.Frame(parent, bg="#16213e")
        terrain_frame.pack(fill=tk.X, padx=10)
        
        self.terrain_buttons = {}
        row = 0
        col = 0
        for terrain in TerrainType:
            color = terrain.color
            btn = tk.Button(terrain_frame, text=terrain.display_name[:6], width=8,
                           bg=color, fg="black" if self._is_light_color(color) else "white",
                           font=("Arial", 8), relief=tk.RAISED,
                           command=lambda t=terrain.name: self._select_terrain(t))
            btn.grid(row=row, column=col, padx=1, pady=1)
            self.terrain_buttons[terrain.name] = btn
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        # === WEATHER ===
        tk.Label(parent, text="🌦️ WETTER", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(15, 5))
        
        weather_frame = tk.Frame(parent, bg="#16213e")
        weather_frame.pack(fill=tk.X, padx=10)
        
        for weather in WeatherType:
            btn = tk.Button(weather_frame, text=f"{weather.icon} {weather.display_name}",
                           bg="#0f3460", fg="white", font=("Arial", 9),
                           command=lambda w=weather.name: self._select_weather(w))
            btn.pack(fill=tk.X, pady=1)
        
        # === INFO ===
        tk.Label(parent, text="📊 INFO", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(15, 5))
        
        self.info_label = tk.Label(parent, text="Kein Tile ausgewählt",
                                   bg="#0f3460", fg="white", font=("Arial", 9),
                                   justify=tk.LEFT, anchor=tk.NW, wraplength=250)
        self.info_label.pack(fill=tk.X, padx=10, pady=5, ipady=10, ipadx=5)
        
        # === TAG/NACHT ===
        tk.Label(parent, text="🌓 TAG/NACHT", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(15, 5))
        
        daynight_frame = tk.Frame(parent, bg="#16213e")
        daynight_frame.pack(fill=tk.X, padx=10)
        
        self.time_of_day = tk.StringVar(value="noon")
        time_options = [
            ("🌅 Morgen", "morning"),
            ("☀️ Mittag", "noon"),
            ("🌆 Abend", "evening"),
            ("🌙 Nacht", "night"),
        ]
        
        for text, value in time_options:
            rb = tk.Radiobutton(daynight_frame, text=text, variable=self.time_of_day,
                               value=value, bg="#16213e", fg="white",
                               selectcolor="#0f3460", activebackground="#16213e",
                               command=self._update_day_night)
            rb.pack(anchor=tk.W)
        
        # Dunkelheits-Slider
        tk.Label(daynight_frame, text="Dunkelheit:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, pady=(5, 0))
        self.darkness_var = tk.DoubleVar(value=0.0)
        self.darkness_slider = tk.Scale(daynight_frame, variable=self.darkness_var,
                                        from_=0.0, to=1.0, resolution=0.1,
                                        orient=tk.HORIZONTAL, length=200,
                                        bg="#16213e", fg="white", highlightthickness=0,
                                        command=lambda v: self._redraw())
        self.darkness_slider.pack(fill=tk.X)
        
        # === GLOBALES WETTER ===
        tk.Label(parent, text="🌍 GLOBALES WETTER", font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=(15, 5))
        
        global_weather_frame = tk.Frame(parent, bg="#16213e")
        global_weather_frame.pack(fill=tk.X, padx=10)
        
        self.global_weather_var = tk.StringVar(value=self.hex_map.global_weather)
        weather_combo = ttk.Combobox(global_weather_frame, textvariable=self.global_weather_var,
                                     values=[w.name for w in WeatherType], state="readonly", width=15)
        weather_combo.pack(fill=tk.X, pady=2)
        weather_combo.bind("<<ComboboxSelected>>", self._update_global_weather)
        
        # Wetter-Intensität
        tk.Label(global_weather_frame, text="Intensität:", bg="#16213e", fg="white",
                font=("Arial", 9)).pack(anchor=tk.W, pady=(5, 0))
        self.weather_intensity_var = tk.DoubleVar(value=1.0)
        tk.Scale(global_weather_frame, variable=self.weather_intensity_var,
                from_=0.1, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, length=200,
                bg="#16213e", fg="white", highlightthickness=0,
                command=lambda v: self._update_global_weather()).pack(fill=tk.X)
        
        # === STATS ===
        self.stats_label = tk.Label(parent, text=f"Tiles: {len(self.hex_map.tiles)}",
                                    bg="#16213e", fg="white", font=("Arial", 10))
        self.stats_label.pack(anchor=tk.W, padx=10, pady=(15, 5))
        
        # === STEUERUNG HINWEIS ===
        tk.Label(parent, text="🖱️ STEUERUNG", font=("Arial", 10, "bold"),
                bg="#16213e", fg="#888").pack(anchor=tk.W, padx=10, pady=(15, 2))
        tk.Label(parent, text="• Mausrad: Zoom\n• Mittlere Taste/Rechtsklick+Ziehen: Schwenken\n• Linksklick: Tool verwenden",
                bg="#16213e", fg="#666", font=("Arial", 8), justify=tk.LEFT).pack(anchor=tk.W, padx=10)
    
    def _is_light_color(self, hex_color: str) -> bool:
        """Prüfe ob Farbe hell ist"""
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return (r * 299 + g * 587 + b * 114) / 1000 > 128
    
    def _update_day_night(self, event=None):
        """Update Dunkelheit basierend auf Tageszeit"""
        time_darkness = {
            "morning": 0.1,
            "noon": 0.0,
            "evening": 0.3,
            "night": 0.7
        }
        self.darkness_var.set(time_darkness.get(self.time_of_day.get(), 0.0))
        self._redraw()
    
    def _update_global_weather(self, event=None):
        """Update globales Wetter"""
        self.hex_map.global_weather = self.global_weather_var.get()
        self.hex_map.weather_intensity = self.weather_intensity_var.get()
        self._redraw()
    
    def _bind_events(self):
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        
        # Mittlere Maustaste für Panning (Schwenken)
        self.canvas.bind("<Button-2>", self._on_pan_start)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        
        # Rechte Maustaste + Ziehen auch für Panning
        self.canvas.bind("<B3-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_pan_end)
        
        # Double click für Properties
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        
        # Shift für Mehrfachauswahl
        self.bind("<Shift_L>", lambda e: setattr(self, 'shift_held', True))
        self.bind("<Shift_R>", lambda e: setattr(self, 'shift_held', True))
        self.bind("<KeyRelease-Shift_L>", lambda e: setattr(self, 'shift_held', False))
        self.bind("<KeyRelease-Shift_R>", lambda e: setattr(self, 'shift_held', False))
        
        # Escape zum Abbrechen/Deselektieren
        self.bind("<Escape>", self._on_escape)
        
        # Delete für ausgewählte Tiles löschen
        self.bind("<Delete>", self._delete_selected_tiles)
    
    def _on_pan_start(self, event):
        """Starte Panning mit mittlerer Maustaste"""
        self.pan_start = (event.x, event.y)
    
    def _on_pan_drag(self, event):
        """Panning mit mittlerer oder rechter Maustaste"""
        if hasattr(self, 'pan_start') and self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.offset_x += dx
            self.offset_y += dy
            self.pan_start = (event.x, event.y)
            self._redraw()
    
    def _on_pan_end(self, event):
        """Beende Panning"""
        self.pan_start = None

    def _on_escape(self, event):
        """Escape drücken - Auswahl aufheben"""
        self.selected_tile = None
        self.selected_tiles.clear()
        self._redraw()
    
    def _delete_selected_tiles(self, event):
        """Lösche alle ausgewählten Tiles"""
        count = 0
        
        # Einzelauswahl
        if self.selected_tile and self.selected_tile in self.hex_map.tiles:
            del self.hex_map.tiles[self.selected_tile]
            count += 1
            self.selected_tile = None
        
        # Mehrfachauswahl
        for coord in list(self.selected_tiles):
            if coord in self.hex_map.tiles:
                del self.hex_map.tiles[coord]
                count += 1
        self.selected_tiles.clear()
        
        if count > 0:
            print(f"🗑️ {count} Tile(s) gelöscht")
            self._update_stats()
            self._redraw()
    
    def _select_terrain(self, terrain: str):
        self.current_terrain = terrain
        for t, btn in self.terrain_buttons.items():
            if t == terrain:
                btn.configure(relief=tk.SUNKEN)
            else:
                btn.configure(relief=tk.RAISED)
        
        # Wende Terrain auf alle ausgewählten Tiles an
        count = 0
        if self.selected_tiles:
            for coord in self.selected_tiles:
                if coord in self.hex_map.tiles:
                    self.hex_map.tiles[coord].terrain = terrain
                    count += 1
        if self.selected_tile and self.selected_tile in self.hex_map.tiles:
            self.hex_map.tiles[self.selected_tile].terrain = terrain
            count += 1
        
        if count > 0:
            print(f"🗺️ Terrain '{terrain}' auf {count} Tile(s) angewendet")
            self._redraw()
    
    def _select_weather(self, weather: str):
        self.current_weather = weather
        
        # Wende Wetter auf alle ausgewählten Tiles an
        count = 0
        if self.selected_tiles:
            for coord in self.selected_tiles:
                if coord in self.hex_map.tiles:
                    self.hex_map.tiles[coord].local_weather = weather
                    self.hex_map.tiles[coord].weather_intensity = 1.0
                    count += 1
        if self.selected_tile and self.selected_tile in self.hex_map.tiles:
            self.hex_map.tiles[self.selected_tile].local_weather = weather
            self.hex_map.tiles[self.selected_tile].weather_intensity = 1.0
            count += 1
        
        if count > 0:
            print(f"🌦️ Wetter '{weather}' auf {count} Tile(s) angewendet")
            self._redraw()
    
    def _load_svg(self):
        """Lade SVG und erkenne Hexagone"""
        import sys
        
        filepath = filedialog.askopenfilename(
            title="SVG-Karte laden",
            filetypes=[("SVG Dateien", "*.svg"), ("PNG Bilder", "*.png"), ("Alle Dateien", "*.*")]
        )
        if not filepath:
            return
        
        print(f"📂 Datei ausgewählt: {filepath}", flush=True)
        
        # Lade Hintergrundbild ZUERST
        self.bg_image = None
        self.bg_image_path = filepath  # Speichere Pfad für späteres Speichern
        
        if filepath.lower().endswith('.svg'):
            # SVG -> PNG konvertieren
            try:
                import cairosvg
                from io import BytesIO
                
                print("   Konvertiere SVG zu PNG...", flush=True)
                png_data = cairosvg.svg2png(url=filepath, scale=1)
                self.bg_image = Image.open(BytesIO(png_data))
                self.hex_map.image_width = self.bg_image.width
                self.hex_map.image_height = self.bg_image.height
                self.hex_map.background_image_path = filepath
                print(f"✅ SVG als Hintergrund geladen: {self.bg_image.size}", flush=True)
                
            except ImportError as ie:
                print(f"⚠️ cairosvg nicht installiert: {ie}", flush=True)
            except Exception as e:
                print(f"⚠️ SVG-Konvertierung fehlgeschlagen: {e}", flush=True)
                import traceback
                traceback.print_exc()
        else:
            # Direktes Bild laden (PNG, JPG, etc.)
            try:
                self.bg_image = Image.open(filepath)
                self.hex_map.image_width = self.bg_image.width
                self.hex_map.image_height = self.bg_image.height
                self.hex_map.background_image_path = filepath
                print(f"✅ Bild geladen: {self.bg_image.size}", flush=True)
            except Exception as e:
                print(f"⚠️ Konnte Bild nicht laden: {e}", flush=True)
        
        # WICHTIG: Sofort redraw um Hintergrund anzuzeigen
        if self.bg_image:
            print(f"   Zeige Hintergrundbild: {self.bg_image.size}", flush=True)
            self._redraw()
            
            # Zeige Anleitung für den Norm-Hex Workflow (KEINE automatische Erkennung!)
            messagebox.showinfo(
                "Karte geladen",
                f"Karte geladen: {self.bg_image.width}×{self.bg_image.height}px\n\n"
                "Jetzt Grid manuell erstellen:\n"
                "1. Wähle '✏️ Norm-Hex' und zeichne ein Hexagon\n"
                "2. Verschiebe es auf ein Karten-Hexagon\n"
                "3. Wähle '📍 Extents' und markiere die Ecken\n"
                "4. Klicke '🔲 Interpolieren'\n\n"
                "Oder: '🔲 Grid erstellen' für manuelles Raster"
            )
        else:
            messagebox.showwarning("Hintergrund", 
                                  "Konnte Kartenbild nicht laden.\n"
                                  "Die Hexagone werden ohne Hintergrund angezeigt.")
        
        # KEINE automatische Hexagon-Erkennung mehr!
        # Der User erstellt das Grid manuell mit dem Norm-Hex Workflow
        
        self._update_stats()
        print(f"   Rufe _redraw auf, bg_image={self.bg_image is not None}")
        self._redraw()
        print(f"   _redraw fertig")
    
    def _complete_grid_from_detected(self):
        """Vervollständige Grid basierend auf erkannten Hexagonen"""
        if not self.hex_map.tiles:
            return
        
        # Berechne Extents NUR aus erkannten Hexagonen
        tiles = list(self.hex_map.tiles.values())
        min_x = min(t.center_x for t in tiles)
        max_x = max(t.center_x for t in tiles)
        min_y = min(t.center_y for t in tiles)
        max_y = max(t.center_y for t in tiles)
        
        hex_size = self.hex_map.hex_size
        orientation = self.hex_map.orientation
        
        print(f"📐 Erkannte Extents: X={min_x:.0f}-{max_x:.0f}, Y={min_y:.0f}-{max_y:.0f}")
        print(f"   Hex-Größe: {hex_size:.1f}px, Orientierung: {orientation}")
        
        # Berechne Grid-Parameter basierend auf Hex-Geometrie
        if orientation == "pointy-top":
            hex_width = hex_size * math.sqrt(3)
            vert_spacing = hex_size * 1.5  # 3/4 der Höhe
        else:
            hex_width = hex_size * 1.5
            vert_spacing = hex_size * math.sqrt(3)
        
        # Finde ein Referenz-Hexagon für die Ausrichtung
        ref_tile = tiles[0]
        
        # Berechne Grid-Start basierend auf Referenz-Tile
        # Das Grid muss so ausgerichtet sein, dass ref_tile genau getroffen wird
        if orientation == "pointy-top":
            # Berechne welche Reihe/Spalte das Referenz-Tile hat
            ref_row = round((ref_tile.center_y - min_y) / vert_spacing)
            ref_col_offset = (hex_width / 2) if (ref_row % 2 == 1) else 0
            ref_col = round((ref_tile.center_x - min_x - ref_col_offset) / hex_width)
            
            # Berechne tatsächlichen Grid-Start
            start_x = ref_tile.center_x - ref_col * hex_width - ref_col_offset
            start_y = ref_tile.center_y - ref_row * vert_spacing
        else:
            ref_col = round((ref_tile.center_x - min_x) / hex_width)
            ref_row_offset = (vert_spacing / 2) if (ref_col % 2 == 1) else 0
            ref_row = round((ref_tile.center_y - min_y - ref_row_offset) / vert_spacing)
            
            start_x = ref_tile.center_x - ref_col * hex_width
            start_y = ref_tile.center_y - ref_row * vert_spacing - ref_row_offset
        
        # Berechne Anzahl Spalten und Reihen für den erkannten Bereich
        if orientation == "pointy-top":
            cols = int((max_x - start_x) / hex_width) + 2
            rows = int((max_y - start_y) / vert_spacing) + 2
        else:
            cols = int((max_x - start_x) / hex_width) + 2
            rows = int((max_y - start_y) / vert_spacing) + 2
        
        # Lösche alte Tiles und erstelle neues vollständiges Grid
        self.hex_map.tiles.clear()
        
        for r in range(rows):
            for q in range(cols):
                if orientation == "pointy-top":
                    x_offset = (hex_width / 2) if (r % 2 == 1) else 0
                    cx = start_x + q * hex_width + x_offset
                    cy = start_y + r * vert_spacing
                else:
                    y_offset = (vert_spacing / 2) if (q % 2 == 1) else 0
                    cx = start_x + q * hex_width
                    cy = start_y + r * vert_spacing + y_offset
                
                # Prüfe ob Tile innerhalb der erkannten Extents liegt (mit kleinem Puffer)
                puffer = hex_size * 0.5
                if (min_x - puffer) <= cx <= (max_x + puffer) and \
                   (min_y - puffer) <= cy <= (max_y + puffer):
                    tile = HexTile(q=q, r=r, center_x=cx, center_y=cy)
                    self.hex_map.tiles[(q, r)] = tile
        
        print(f"✅ Grid erstellt: {len(self.hex_map.tiles)} Tiles im Bereich der erkannten Hexagone")
    
    def _manual_hex_size_dialog(self):
        """Dialog zur manuellen Eingabe der Hex-Größe"""
        dialog = tk.Toplevel(self)
        dialog.title("📐 Hex-Größe manuell eingeben")
        dialog.configure(bg="#1a1a2e")
        dialog.geometry("350x200")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="Die automatische Erkennung war ungenau.\n"
                            "Bitte gib die Hex-Größe manuell ein:",
                bg="#1a1a2e", fg="white", justify=tk.LEFT).pack(pady=10, padx=15)
        
        frame = tk.Frame(dialog, bg="#1a1a2e")
        frame.pack(pady=10)
        
        tk.Label(frame, text="Hex-Radius (Pixel):", bg="#1a1a2e", fg="white").grid(row=0, column=0, padx=5, pady=5)
        size_var = tk.DoubleVar(value=40.0)
        size_entry = tk.Entry(frame, textvariable=size_var, width=10, bg="#0f3460", fg="white")
        size_entry.grid(row=0, column=1, pady=5)
        
        tk.Label(frame, text="Tipp: Miss ein Hexagon auf der Karte\n(Mitte zu Ecke)", 
                bg="#1a1a2e", fg="#888888", font=("Arial", 9)).grid(row=1, column=0, columnspan=2, pady=5)
        
        def apply():
            self.hex_map.hex_size = size_var.get()
            self.hex_map.tiles.clear()  # Alte Tiles löschen
            print(f"   Manuelle Hex-Größe: {self.hex_map.hex_size:.1f}px")
            dialog.destroy()
            # Jetzt Grid erstellen mit Bild-Extents
            self._create_grid_for_image()
        
        tk.Button(dialog, text="✓ Grid erstellen", command=apply,
                 bg="#28a745", fg="white", padx=20).pack(pady=15)
    
    def _create_grid_for_image(self):
        """Erstelle Grid basierend auf Bildgröße und manueller Hex-Größe"""
        if not self.bg_image:
            return
        
        hex_size = self.hex_map.hex_size
        orientation = self.hex_map.orientation
        
        img_width = self.bg_image.width
        img_height = self.bg_image.height
        
        # Grid-Parameter
        if orientation == "pointy-top":
            hex_width = hex_size * math.sqrt(3)
            vert_spacing = hex_size * 1.5
        else:
            hex_width = hex_size * 1.5
            vert_spacing = hex_size * math.sqrt(3)
        
        cols = int(img_width / hex_width) + 2
        rows = int(img_height / vert_spacing) + 2
        
        # Start bei 0,0
        start_x = hex_size
        start_y = hex_size
        
        self.hex_map.tiles.clear()
        
        for r in range(rows):
            for q in range(cols):
                if orientation == "pointy-top":
                    x_offset = (hex_width / 2) if (r % 2 == 1) else 0
                    cx = start_x + q * hex_width + x_offset
                    cy = start_y + r * vert_spacing
                else:
                    y_offset = (vert_spacing / 2) if (q % 2 == 1) else 0
                    cx = start_x + q * hex_width
                    cy = start_y + r * vert_spacing + y_offset
                
                # Prüfe ob im Bild
                if 0 <= cx <= img_width and 0 <= cy <= img_height:
                    tile = HexTile(q=q, r=r, center_x=cx, center_y=cy)
                    self.hex_map.tiles[(q, r)] = tile
        
        print(f"✅ Grid erstellt: {len(self.hex_map.tiles)} Tiles")
        self._update_stats()
        self._redraw()
    
    def _load_image(self):
        """Lade PNG/JPG als Hintergrund und zeichne Grid manuell"""
        filepath = filedialog.askopenfilename(
            title="Kartenbild laden",
            filetypes=[
                ("Bilder", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Alle Dateien", "*.*")
            ]
        )
        if not filepath:
            return
        
        try:
            self.bg_image = Image.open(filepath)
            self.bg_image_path = filepath  # Speichere Pfad für späteres Speichern
            self.hex_map.image_width = self.bg_image.width
            self.hex_map.image_height = self.bg_image.height
            self.hex_map.background_image_path = filepath
            print(f"✅ Bild geladen: {self.bg_image.size}")
            
            # Zeige Info und frage nach Grid-Erstellung
            messagebox.showinfo(
                "Bild geladen",
                f"Kartenbild geladen: {self.bg_image.width}×{self.bg_image.height}px\n\n"
                "Jetzt kannst du:\n"
                "1. ✏️ 'Hex zeichnen' wählen\n"
                "2. Auf die Karte klicken und ziehen um ein Hexagon zu definieren\n"
                "3. Die Größe anpassen und Grid erstellen"
            )
            
            self._redraw()
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte Bild nicht laden:\n{e}")
    
    def _create_grid_dialog(self):
        """Dialog zum manuellen Grid erstellen"""
        dialog = tk.Toplevel(self)
        dialog.title("Grid erstellen")
        dialog.configure(bg="#1a1a2e")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Spalten:", bg="#1a1a2e", fg="white").grid(row=0, column=0, padx=10, pady=10)
        cols_var = tk.IntVar(value=10)
        tk.Entry(dialog, textvariable=cols_var, width=10, bg="#0f3460", fg="white").grid(row=0, column=1)
        
        tk.Label(dialog, text="Zeilen:", bg="#1a1a2e", fg="white").grid(row=1, column=0, padx=10, pady=10)
        rows_var = tk.IntVar(value=8)
        tk.Entry(dialog, textvariable=rows_var, width=10, bg="#0f3460", fg="white").grid(row=1, column=1)
        
        tk.Label(dialog, text="Hex-Größe:", bg="#1a1a2e", fg="white").grid(row=2, column=0, padx=10, pady=10)
        size_var = tk.IntVar(value=40)
        tk.Entry(dialog, textvariable=size_var, width=10, bg="#0f3460", fg="white").grid(row=2, column=1)
        
        def create():
            self.hex_map.create_grid(cols_var.get(), rows_var.get(), size_var.get())
            self._update_stats()
            self._redraw()
            dialog.destroy()
        
        tk.Button(dialog, text="Erstellen", command=create,
                 bg="#28a745", fg="white").grid(row=3, column=0, columnspan=2, pady=20)
    
    def _clear_all_tiles(self):
        """Lösche alle Hexagone"""
        tile_count = len(self.hex_map.tiles)
        
        if tile_count == 0:
            messagebox.showinfo("Keine Tiles", "Es gibt keine Hexagone zum Löschen.")
            return
        
        result = messagebox.askyesnocancel(
            "Alle löschen?",
            f"Es gibt {tile_count} Hexagone.\n\n"
            "Ja = Alle Hexagone löschen\n"
            "Nein = Nur das Grid löschen (Norm-Hex behalten)\n"
            "Abbrechen = Nichts löschen"
        )
        
        if result is True:
            # Alles löschen
            self.hex_map.tiles.clear()
            self.norm_hex_center = None
            self.norm_hex_size = 50.0
            self.extent_hexagons.clear()
            print(f"🗑️ Alle {tile_count} Hexagone und Norm-Hex gelöscht")
        elif result is False:
            # Nur Grid löschen, Norm-Hex behalten
            self.hex_map.tiles.clear()
            self.extent_hexagons.clear()
            print(f"🗑️ Alle {tile_count} Hexagone gelöscht (Norm-Hex beibehalten)")
        else:
            return
        
        self._update_stats()
        self._redraw()
    
    def _random_events_dialog(self):
        """Dialog für Zufalls-Events"""
        dialog = tk.Toplevel(self)
        dialog.title("Zufalls-Events generieren")
        dialog.configure(bg="#1a1a2e")
        dialog.geometry("300x180")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Event-Typ:", bg="#1a1a2e", fg="white").grid(row=0, column=0, padx=10, pady=10)
        type_var = tk.StringVar(value="enemy")
        ttk.Combobox(dialog, textvariable=type_var, values=["enemy", "treasure", "encounter"],
                    state="readonly", width=15).grid(row=0, column=1)
        
        tk.Label(dialog, text="Wahrscheinlichkeit:", bg="#1a1a2e", fg="white").grid(row=1, column=0, padx=10, pady=10)
        prob_var = tk.DoubleVar(value=0.15)
        tk.Scale(dialog, variable=prob_var, from_=0.05, to=0.5, resolution=0.05,
                orient=tk.HORIZONTAL, length=100, bg="#1a1a2e", fg="white").grid(row=1, column=1)
        
        def generate():
            self.hex_map.generate_random_events(type_var.get(), prob_var.get())
            self._redraw()
            dialog.destroy()
        
        tk.Button(dialog, text="🎲 Generieren", command=generate,
                 bg="#28a745", fg="white").grid(row=2, column=0, columnspan=2, pady=20)
    
    def _save_map(self):
        # Wenn bereits ein Dateipfad bekannt, direkt speichern
        initial_file = self.current_file_path if self.current_file_path else ""
        
        filepath = filedialog.asksaveasfilename(
            title="Hexagon-Karte speichern",
            defaultextension=".json",
            initialfile=os.path.basename(initial_file) if initial_file else "",
            initialdir=os.path.dirname(initial_file) if initial_file else "maps",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            # Speichere Hintergrund-Einstellungen in hex_map
            if hasattr(self, 'bg_image_path') and self.bg_image_path:
                self.hex_map.background_image_path = self.bg_image_path
            self.hex_map.background_visible = self.bg_visible
            self.hex_map.background_on_top = self.bg_on_top
            self.hex_map.hex_outline_only = self.hex_outline_only
            # Speichere Hexagon-Outline-Einstellungen für Projektor-Rendering
            self.hex_map.hex_outline_color = self.hex_outline_color
            self.hex_map.hex_outline_opacity = self.hex_outline_opacity
            # Speichere individuelle Tile-Größen (als string-keys für JSON)
            self.hex_map.individual_tile_sizes = {f"{k[0]},{k[1]}": v for k, v in self.individual_tile_sizes.items()}
            # Speichere Text-Annotations
            self.hex_map.text_annotations = self.text_annotations
            
            self.hex_map.save(filepath)
            self.current_file_path = filepath
            messagebox.showinfo("Gespeichert", f"Karte gespeichert:\n{filepath}")
    
    def _load_map(self):
        filepath = filedialog.askopenfilename(
            title="Hexagon-Karte laden",
            initialdir="maps",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            self.hex_map = HexagonMap.load(filepath)
            self.current_file_path = filepath
            self.title(f"🔷 Hexagon-Editor: {self.hex_map.name}")
            
            # Lade Hintergrund-Einstellungen
            self.bg_visible = getattr(self.hex_map, 'background_visible', True)
            self.bg_on_top = getattr(self.hex_map, 'background_on_top', False)
            self.hex_outline_only = getattr(self.hex_map, 'hex_outline_only', False)
            self.bg_visible_var.set(self.bg_visible)
            self.bg_on_top_var.set(self.bg_on_top)
            self.hex_outline_only_var.set(self.hex_outline_only)
            
            # Lade Hexagon-Outline-Einstellungen
            self.hex_outline_color = getattr(self.hex_map, 'hex_outline_color', '#000000')
            self.hex_outline_opacity = getattr(self.hex_map, 'hex_outline_opacity', 1.0)
            if hasattr(self, 'outline_opacity_var'):
                self.outline_opacity_var.set(self.hex_outline_opacity)
            
            # Lade individuelle Tile-Größen
            saved_sizes = getattr(self.hex_map, 'individual_tile_sizes', {})
            self.individual_tile_sizes = {}
            for k, v in saved_sizes.items():
                parts = k.split(',')
                if len(parts) == 2:
                    try:
                        self.individual_tile_sizes[(int(parts[0]), int(parts[1]))] = v
                    except ValueError:
                        pass
            
            # Lade Text-Annotations
            self.text_annotations = getattr(self.hex_map, 'text_annotations', [])
            if not isinstance(self.text_annotations, list):
                self.text_annotations = []
            
            # Lade Hintergrundbild wenn vorhanden
            bg_path = getattr(self.hex_map, 'background_image_path', None)
            if bg_path and os.path.exists(bg_path):
                try:
                    # Prüfe ob SVG oder Bild
                    if bg_path.lower().endswith('.svg'):
                        try:
                            import cairosvg
                            from io import BytesIO
                            print(f"🖼️ Lade SVG-Hintergrund: {bg_path}")
                            png_data = cairosvg.svg2png(url=bg_path, scale=1)
                            self.bg_image = Image.open(BytesIO(png_data))
                        except ImportError:
                            print(f"⚠️ cairosvg nicht installiert, SVG-Hintergrund wird nicht angezeigt")
                            self.bg_image = None
                    else:
                        print(f"🖼️ Lade Hintergrundbild: {bg_path}")
                        self.bg_image = Image.open(bg_path)
                    
                    if self.bg_image:
                        self.bg_image_path = bg_path
                        print(f"✅ Hintergrundbild geladen: {self.bg_image.size}")
                except Exception as e:
                    print(f"⚠️ Hintergrundbild konnte nicht geladen werden: {e}")
                    self.bg_image = None
            else:
                if bg_path:
                    print(f"⚠️ Hintergrundbild nicht gefunden: {bg_path}")
            
            self._update_stats()
            self._redraw()
    
    def _on_click(self, event):
        x, y = self._canvas_to_map(event.x, event.y)
        
        # === TEXT MODUS ===
        if self.current_tool == "text":
            # Prüfe ob Klick auf bestehende Annotation
            ann_idx = self._find_annotation_at(x, y)
            if ann_idx is not None:
                # Bestehende Annotation ausgewählt
                self.selected_annotation = ann_idx
                self.dragging_annotation = ann_idx
                self.drag_start = (event.x, event.y)
                # Lade Einstellungen der Annotation in UI
                ann = self.text_annotations[ann_idx]
                self.text_size_var.set(ann.get('size', 16))
                self.font_var.set(ann.get('font', 'Arial'))
                self.bold_var.set(ann.get('bold', False))
                self.italic_var.set(ann.get('italic', False))
                self._set_text_color(ann.get('color', '#000000'))
                print(f"🏷️ Text ausgewählt: '{ann['text']}'")
                self._redraw()
                return
            else:
                # Neue Annotation an dieser Stelle
                self.selected_annotation = None
                self._add_text_annotation(x, y)
                return
        
        # === NORM-HEXAGON MODUS ===
        if self.current_tool == "draw_hex":
            # Prüfe ob Klick auf bestehendes Norm-Hex
            if self.norm_hex_center:
                dist = math.sqrt((x - self.norm_hex_center[0])**2 + (y - self.norm_hex_center[1])**2)
                
                # Klick auf Rand (±20%) -> Größe ändern
                if abs(dist - self.norm_hex_size) < self.norm_hex_size * 0.25:
                    self.resizing_norm_hex = True
                    self.drag_start = (event.x, event.y)
                    print(f"📐 Größenänderung gestartet (aktuell: {self.norm_hex_size:.0f}px)")
                    return
                
                # Klick in Mitte -> Verschieben
                if dist < self.norm_hex_size * 0.75:
                    self.dragging_norm_hex = True
                    self.drag_start = (event.x, event.y)
                    return
            
            # Neues Norm-Hex zeichnen
            self.draw_hex_start = (x, y)
            self.template_hex_size = 0
            self.preview_hex = None
            return
        
        # === EXTENT PLATZIEREN/BEARBEITEN ===
        if self.current_tool == "place_extent":
            if not self.norm_hex_center or self.norm_hex_size < 10:
                messagebox.showwarning("Kein Norm-Hexagon", 
                    "Bitte zuerst ein Norm-Hexagon zeichnen!\n\n"
                    "1. Wähle '✏️ Norm-Hex'\n"
                    "2. Klicke und ziehe um Größe zu definieren\n"
                    "3. Verschiebe es auf ein Karten-Hexagon")
                return
            
            # Prüfe ob Klick auf bestehenden Extent (zum Verschieben)
            for i, (ex, ey) in enumerate(self.extent_hexagons):
                dist = math.sqrt((x - ex)**2 + (y - ey)**2)
                if dist < self.norm_hex_size * 0.6:
                    # Extent verschieben
                    self.dragging_extent = i
                    self.drag_start = (event.x, event.y)
                    print(f"📍 Extent E{i+1} wird verschoben")
                    return
            
            # Neuen Extent-Punkt platzieren
            self.extent_hexagons.append((x, y))
            print(f"📍 Extent-Punkt {len(self.extent_hexagons)} platziert bei ({x:.0f}, {y:.0f})")
            self._redraw()
            
            if len(self.extent_hexagons) == 3:
                messagebox.showinfo("Polygon definiert",
                    f"{len(self.extent_hexagons)} Extent-Punkte = Dreieck.\n\n"
                    "• Weitere Punkte für komplexere Formen\n"
                    "• Rechtsklick auf Punkt zum Löschen\n"
                    "• '🔲 Interpolieren' erstellt Grid im Polygon")
            return
        
        # === MOVE/SCALE MODUS ===
        if self.current_tool == "move_scale":
            tile = self.hex_map.get_tile_at_pixel(x, y)
            if tile:
                coord = (tile.q, tile.r)
                # Berechne Distanz zum Zentrum
                dist = math.sqrt((x - tile.center_x)**2 + (y - tile.center_y)**2)
                tile_size = self.individual_tile_sizes.get(coord, self.hex_map.hex_size)
                
                # Klick auf Rand (±25%) -> Skalieren
                if abs(dist - tile_size) < tile_size * 0.3:
                    self.scaling_tile = coord
                    self.tile_scale_start_dist = dist
                    self.drag_start = (event.x, event.y)
                    print(f"📐 Skaliere Hexagon ({tile.q}, {tile.r}) - aktuelle Größe: {tile_size:.0f}px")
                    return
                
                # Klick in Mitte -> Verschieben
                if dist < tile_size * 0.7:
                    self.moving_tile = coord
                    self.tile_original_center = (tile.center_x, tile.center_y)
                    self.drag_start = (event.x, event.y)
                    # Wähle Tile auch aus
                    self.selected_tile = coord
                    self.selected_tiles.clear()
                    print(f"✋ Verschiebe Hexagon ({tile.q}, {tile.r})")
                    self._redraw()
                    return
            # Kein Tile getroffen - Pan starten
            self.drag_start = (event.x, event.y)
            return
        
        # === INTERPOLIEREN ===
        if self.current_tool == "interpolate":
            self._interpolate_grid()
            return
        
        # === LÖSCHEN MODUS ===
        if self.current_tool == "delete":
            tile = self.hex_map.get_tile_at_pixel(x, y)
            if tile:
                # Lösche einzelnes Hexagon
                key = (tile.q, tile.r)
                if key in self.hex_map.tiles:
                    del self.hex_map.tiles[key]
                    print(f"🗑️ Hexagon ({tile.q}, {tile.r}) gelöscht")
                    self._update_stats()
                    self._redraw()
            return
        
        # === STANDARD TILE-OPERATIONEN ===
        tile = self.hex_map.get_tile_at_pixel(x, y)
        
        if tile:
            coord = (tile.q, tile.r)
            
            if self.current_tool == "select":
                if self.shift_held:
                    # Shift gehalten -> zur Mehrfachauswahl hinzufügen/entfernen
                    if coord in self.selected_tiles:
                        self.selected_tiles.remove(coord)
                    else:
                        self.selected_tiles.add(coord)
                else:
                    # Normaler Klick -> Einzelauswahl (Mehrfachauswahl leeren)
                    self.selected_tiles.clear()
                    self.selected_tile = coord
                self._update_info(tile)
                
            elif self.current_tool == "terrain":
                # Terrain auf ausgewählte Tiles anwenden
                if self.selected_tiles:
                    for sel_coord in self.selected_tiles:
                        if sel_coord in self.hex_map.tiles:
                            self.hex_map.tiles[sel_coord].terrain = self.current_terrain
                else:
                    tile.terrain = self.current_terrain
                
            elif self.current_tool == "weather":
                # Wetter auf ausgewählte Tiles anwenden
                if self.selected_tiles:
                    for sel_coord in self.selected_tiles:
                        if sel_coord in self.hex_map.tiles:
                            self.hex_map.tiles[sel_coord].local_weather = self.current_weather
                            self.hex_map.tiles[sel_coord].weather_intensity = 1.0
                else:
                    tile.local_weather = self.current_weather
                    tile.weather_intensity = 1.0
                
            elif self.current_tool == "event":
                # Zeige Event-Dialog
                dialog = EventEditDialog(self, None)
                self.wait_window(dialog)
                if dialog.result:
                    # Event auf ausgewählte Tiles anwenden
                    if self.selected_tiles:
                        for sel_coord in self.selected_tiles:
                            if sel_coord in self.hex_map.tiles:
                                self.hex_map.tiles[sel_coord].events.append(dialog.result.copy())
                    else:
                        tile.events.append(dialog.result)
            
            elif self.current_tool == "boss":
                # Toggle Boss-Hexagon Markierung
                if self.selected_tiles:
                    for sel_coord in self.selected_tiles:
                        if sel_coord in self.hex_map.tiles:
                            current = getattr(self.hex_map.tiles[sel_coord], 'is_boss_hex', False)
                            self.hex_map.tiles[sel_coord].is_boss_hex = not current
                else:
                    current = getattr(tile, 'is_boss_hex', False)
                    tile.is_boss_hex = not current
                print(f"🐉 Boss-Hexagon: {'Markiert' if not current else 'Entfernt'}")
            
            elif self.current_tool == "spawn":
                # Toggle Spawn-Hexagon Markierung (für Spieler-Startpunkte)
                if self.selected_tiles:
                    for sel_coord in self.selected_tiles:
                        if sel_coord in self.hex_map.tiles:
                            current = getattr(self.hex_map.tiles[sel_coord], 'is_spawn_hex', False)
                            self.hex_map.tiles[sel_coord].is_spawn_hex = not current
                else:
                    current = getattr(tile, 'is_spawn_hex', False)
                    tile.is_spawn_hex = not current
                print(f"🎮 Spawn-Hexagon: {'Markiert' if not current else 'Entfernt'}")
            
            self._redraw()
        else:
            # Pan starten
            self.drag_start = (event.x, event.y)
    
    def _on_drag(self, event):
        # === TEXT ANNOTATION VERSCHIEBEN ===
        if self.dragging_annotation is not None and self.dragging_annotation < len(self.text_annotations):
            dx = (event.x - self.drag_start[0]) / self.zoom
            dy = (event.y - self.drag_start[1]) / self.zoom
            self.text_annotations[self.dragging_annotation]['x'] += dx
            self.text_annotations[self.dragging_annotation]['y'] += dy
            self.drag_start = (event.x, event.y)
            self._redraw()
            return
        
        # === NORM-HEX GRÖßE ÄNDERN ===
        if self.resizing_norm_hex and self.norm_hex_center:
            x, y = self._canvas_to_map(event.x, event.y)
            cx, cy = self.norm_hex_center
            # Neue Größe = Abstand zum Zentrum
            new_size = math.sqrt((x - cx)**2 + (y - cy)**2)
            if new_size > 15:  # Mindestgröße
                self.norm_hex_size = new_size
                self.hex_map.hex_size = new_size
            self._redraw()
            return
        
        # === NORM-HEX VERSCHIEBEN ===
        if self.dragging_norm_hex and self.norm_hex_center:
            dx = (event.x - self.drag_start[0]) / self.zoom
            dy = (event.y - self.drag_start[1]) / self.zoom
            self.norm_hex_center = (self.norm_hex_center[0] + dx, self.norm_hex_center[1] + dy)
            self.drag_start = (event.x, event.y)
            self._redraw()
            return
        
        # === EXTENT VERSCHIEBEN ===
        if self.dragging_extent is not None and self.dragging_extent < len(self.extent_hexagons):
            x, y = self._canvas_to_map(event.x, event.y)
            self.extent_hexagons[self.dragging_extent] = (x, y)
            self._redraw()
            return
        
        # === EINZELNES TILE VERSCHIEBEN ===
        if self.moving_tile and self.moving_tile in self.hex_map.tiles:
            dx = (event.x - self.drag_start[0]) / self.zoom
            dy = (event.y - self.drag_start[1]) / self.zoom
            tile = self.hex_map.tiles[self.moving_tile]
            tile.center_x += dx
            tile.center_y += dy
            self.drag_start = (event.x, event.y)
            self._redraw()
            return
        
        # === EINZELNES TILE SKALIEREN ===
        if self.scaling_tile and self.scaling_tile in self.hex_map.tiles:
            x, y = self._canvas_to_map(event.x, event.y)
            tile = self.hex_map.tiles[self.scaling_tile]
            # Neue Größe = Abstand zum Tile-Zentrum
            new_size = math.sqrt((x - tile.center_x)**2 + (y - tile.center_y)**2)
            if new_size > 10:  # Mindestgröße
                self.individual_tile_sizes[self.scaling_tile] = new_size
            self._redraw()
            return
        
        # Hex-Zeichenmodus: Ziehen definiert Größe
        if self.current_tool == "draw_hex" and self.draw_hex_start:
            x, y = self._canvas_to_map(event.x, event.y)
            cx, cy = self.draw_hex_start
            # Berechne Abstand = Hex-Radius
            self.template_hex_size = math.sqrt((x - cx)**2 + (y - cy)**2)
            # Generiere Vorschau
            self.preview_hex = self._generate_hex_preview(cx, cy, self.template_hex_size)
            self._redraw()
            return
        
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.offset_x += dx
            self.offset_y += dy
            self.drag_start = (event.x, event.y)
            self._redraw()
        elif self.current_tool == "terrain":
            # Continuous painting
            x, y = self._canvas_to_map(event.x, event.y)
            tile = self.hex_map.get_tile_at_pixel(x, y)
            if tile:
                tile.terrain = self.current_terrain
                self._redraw()
        elif self.current_tool == "delete":
            # Continuous delete
            x, y = self._canvas_to_map(event.x, event.y)
            tile = self.hex_map.get_tile_at_pixel(x, y)
            if tile:
                key = (tile.q, tile.r)
                if key in self.hex_map.tiles:
                    del self.hex_map.tiles[key]
                    self._update_stats()
                    self._redraw()
    
    def _on_release(self, event):
        # === TEXT ANNOTATION VERSCHIEBEN BEENDEN ===
        if self.dragging_annotation is not None:
            ann = self.text_annotations[self.dragging_annotation]
            print(f"🏷️ Text verschoben: '{ann['text']}' zu ({ann['x']:.0f}, {ann['y']:.0f})")
            self.dragging_annotation = None
            self.drag_start = None
            return
        
        # === NORM-HEX GRÖßE ÄNDERN BEENDEN ===
        if self.resizing_norm_hex:
            self.resizing_norm_hex = False
            self.drag_start = None
            print(f"📐 Norm-Hexagon Größe geändert: {self.norm_hex_size:.0f}px")
            return
        
        # === NORM-HEX VERSCHIEBEN BEENDEN ===
        if self.dragging_norm_hex:
            self.dragging_norm_hex = False
            self.drag_start = None
            print(f"📐 Norm-Hexagon verschoben zu ({self.norm_hex_center[0]:.0f}, {self.norm_hex_center[1]:.0f})")
            return
        
        # === EXTENT VERSCHIEBEN BEENDEN ===
        if self.dragging_extent is not None:
            print(f"📍 Extent E{self.dragging_extent+1} verschoben")
            self.dragging_extent = None
            self.drag_start = None
            return
        
        # === EINZELNES TILE VERSCHIEBEN BEENDEN ===
        if self.moving_tile:
            tile = self.hex_map.tiles.get(self.moving_tile)
            if tile:
                print(f"✋ Hexagon ({tile.q}, {tile.r}) verschoben zu ({tile.center_x:.0f}, {tile.center_y:.0f})")
            self.moving_tile = None
            self.tile_original_center = None
            self.drag_start = None
            self._redraw()
            return
        
        # === EINZELNES TILE SKALIEREN BEENDEN ===
        if self.scaling_tile:
            new_size = self.individual_tile_sizes.get(self.scaling_tile, self.hex_map.hex_size)
            print(f"📐 Hexagon {self.scaling_tile} skaliert auf {new_size:.0f}px")
            self.scaling_tile = None
            self.tile_scale_start_dist = 0.0
            self.drag_start = None
            self._redraw()
            return
        
        # Hex-Zeichenmodus: Speichere als Norm-Hex
        if self.current_tool == "draw_hex" and self.draw_hex_start and self.template_hex_size > 10:
            # Setze als Norm-Hexagon
            self.norm_hex_center = self.draw_hex_start
            self.norm_hex_size = self.template_hex_size
            self.hex_map.hex_size = self.norm_hex_size
            print(f"📐 Norm-Hexagon erstellt: Zentrum=({self.norm_hex_center[0]:.0f}, {self.norm_hex_center[1]:.0f}), Größe={self.norm_hex_size:.1f}px")
            
            messagebox.showinfo("Norm-Hexagon erstellt",
                f"Norm-Hexagon erstellt (Größe: {self.norm_hex_size:.0f}px)\n\n"
                "Jetzt:\n"
                "1. Ziehe am Rand um Größe anzupassen\n"
                "2. Ziehe in der Mitte um zu verschieben\n"
                "3. Wähle '📍 Extents' und setze Polygon-Punkte\n"
                "4. '🔲 Interpolieren' füllt das Polygon")
        
        self.drag_start = None
        self.draw_hex_start = None
        self.preview_hex = None
        self._redraw()
    
    def _scroll_toolbar(self, delta: int):
        """Scrollt die Toolbar horizontal"""
        self.toolbar_canvas.xview_scroll(delta // 20, "units")
    
    def _on_toolbar_mousewheel(self, event):
        """Mausrad-Scrolling für Toolbar"""
        # Horizontal scrollen bei Shift+Mausrad oder normalem Mausrad
        delta = -1 if event.delta > 0 else 1
        self.toolbar_canvas.xview_scroll(delta * 3, "units")
    
    def _set_tool(self, tool: str):
        self.current_tool = tool
        
        # Spezielle Aktion für Interpolieren
        if tool == "interpolate":
            self._interpolate_grid()
            self._set_tool("select")  # Zurück zu Auswahl
            return
        
        # Hinweis für Move/Scale Tool
        if tool == "move_scale":
            print("✋ Move/Scale-Modus: Klicke in die Mitte eines Hexagons zum Verschieben, am Rand zum Skalieren")
        
        for t, btn in self.tool_buttons.items():
            if t == tool:
                btn.configure(bg="#e94560", relief=tk.SUNKEN)
            else:
                btn.configure(bg="#16213e", relief=tk.FLAT)
    
    def _interpolate_grid(self):
        """Interpoliere Grid von Extent-Hexagonen"""
        if not self.norm_hex_center or self.norm_hex_size < 10:
            messagebox.showwarning("Kein Norm-Hexagon", 
                "Bitte zuerst ein Norm-Hexagon zeichnen!")
            return
        
        if len(self.extent_hexagons) < 2:
            # Ohne Extents: Nutze Norm-Hex als einzige Referenz und fülle Bild
            if self.bg_image:
                result = messagebox.askyesno("Ohne Extents interpolieren?",
                    f"Keine Extent-Hexagone gesetzt.\n\n"
                    f"Soll das Grid basierend auf dem Norm-Hexagon\n"
                    f"über das gesamte Bild erstellt werden?")
                if result:
                    self._fill_grid_from_norm_hex()
                return
            else:
                messagebox.showwarning("Keine Extents", 
                    "Bitte mindestens 2 Extent-Hexagone setzen!\n\n"
                    "1. Wähle '📍 Extents'\n"
                    "2. Klicke auf Hexagone an den Ecken der Karte")
                return
        
        # Mit Extents: Interpoliere zwischen ihnen
        self._fill_grid_between_extents()
    
    def _fill_grid_from_norm_hex(self):
        """Fülle Grid basierend auf Norm-Hex über das gesamte Bild"""
        if not self.bg_image or not self.norm_hex_center:
            return
        
        hex_size = self.norm_hex_size
        cx, cy = self.norm_hex_center
        
        # Hex-Geometrie (pointy-top)
        hex_width = hex_size * math.sqrt(3)
        vert_spacing = hex_size * 1.5
        
        # Berechne Grid-Offset basierend auf Norm-Hex Position
        # Das Grid muss so ausgerichtet sein, dass norm_hex_center genau getroffen wird
        
        img_width = self.bg_image.width
        img_height = self.bg_image.height
        
        # Finde heraus welche Reihe/Spalte das Norm-Hex ist
        # und berechne den Start-Offset
        start_x = cx % hex_width
        start_y = cy % vert_spacing
        
        cols = int(img_width / hex_width) + 2
        rows = int(img_height / vert_spacing) + 2
        
        self.hex_map.tiles.clear()
        self.hex_map.hex_size = hex_size
        
        for r in range(rows):
            for q in range(cols):
                x_offset = (hex_width / 2) if (r % 2 == 1) else 0
                tile_cx = start_x + q * hex_width + x_offset
                tile_cy = start_y + r * vert_spacing
                
                # Korrigiere falls außerhalb
                while tile_cx < 0:
                    tile_cx += hex_width
                while tile_cy < 0:
                    tile_cy += vert_spacing
                
                if 0 <= tile_cx <= img_width and 0 <= tile_cy <= img_height:
                    tile = HexTile(q=q, r=r, center_x=tile_cx, center_y=tile_cy)
                    self.hex_map.tiles[(q, r)] = tile
        
        # Extrahiere Farben aus Hintergrundbild
        self._apply_colors_to_tiles()
        
        print(f"✅ Grid erstellt: {len(self.hex_map.tiles)} Tiles")
        self._update_stats()
        self._redraw()
    
    def _fill_grid_between_extents(self):
        """Fülle Grid innerhalb des Extent-Polygons"""
        if len(self.extent_hexagons) < 3:
            # Bei weniger als 3 Punkten: Rechteck zwischen den Punkten
            if len(self.extent_hexagons) == 2:
                self._fill_grid_rectangle()
            return
        
        hex_size = self.norm_hex_size
        
        # Berechne Bounding Box des Polygons
        min_x = min(e[0] for e in self.extent_hexagons)
        max_x = max(e[0] for e in self.extent_hexagons)
        min_y = min(e[1] for e in self.extent_hexagons)
        max_y = max(e[1] for e in self.extent_hexagons)
        
        # Hex-Geometrie (pointy-top)
        hex_width = hex_size * math.sqrt(3)
        vert_spacing = hex_size * 1.5
        
        # Nutze Norm-Hex als Referenz für Ausrichtung
        ref_x, ref_y = self.norm_hex_center
        
        # Berechne Grid-Start basierend auf Norm-Hex
        # Grid muss so ausgerichtet sein dass Norm-Hex-Position genau getroffen wird
        offset_cols = int((ref_x - min_x) / hex_width)
        offset_rows = int((ref_y - min_y) / vert_spacing)
        
        start_x = ref_x - offset_cols * hex_width
        start_y = ref_y - offset_rows * vert_spacing
        
        # Berechne ob Referenz in gerader oder ungerader Reihe liegt
        ref_row_parity = offset_rows % 2
        
        cols = int((max_x - start_x) / hex_width) + 2
        rows = int((max_y - start_y) / vert_spacing) + 2
        
        self.hex_map.tiles.clear()
        self.hex_map.hex_size = hex_size
        
        created = 0
        for r in range(rows):
            for q in range(cols):
                # Offset für Reihen, relativ zur Referenz-Parität
                row_is_odd = (r % 2) != ref_row_parity
                x_offset = (hex_width / 2) if row_is_odd else 0
                
                tile_cx = start_x + q * hex_width + x_offset
                tile_cy = start_y + r * vert_spacing
                
                # Prüfe ob Punkt im Polygon liegt
                if self._point_in_polygon(tile_cx, tile_cy, self.extent_hexagons):
                    tile = HexTile(q=q, r=r, center_x=tile_cx, center_y=tile_cy)
                    self.hex_map.tiles[(q, r)] = tile
                    created += 1
        
        # Extrahiere Farben aus Hintergrundbild
        self._apply_colors_to_tiles()
        
        print(f"✅ Grid interpoliert: {created} Tiles im Polygon mit {len(self.extent_hexagons)} Ecken")
        
        # Extent-Marker NICHT löschen - für weitere Bearbeitung behalten
        # self.extent_hexagons.clear()
        
        self._update_stats()
        self._redraw()
    
    def _fill_grid_rectangle(self):
        """Fülle Grid in einem Rechteck zwischen 2 Extent-Punkten"""
        if len(self.extent_hexagons) < 2:
            return
        
        hex_size = self.norm_hex_size
        
        min_x = min(e[0] for e in self.extent_hexagons)
        max_x = max(e[0] for e in self.extent_hexagons)
        min_y = min(e[1] for e in self.extent_hexagons)
        max_y = max(e[1] for e in self.extent_hexagons)
        
        hex_width = hex_size * math.sqrt(3)
        vert_spacing = hex_size * 1.5
        
        ref_x, ref_y = self.norm_hex_center
        offset_cols = int((ref_x - min_x) / hex_width)
        offset_rows = int((ref_y - min_y) / vert_spacing)
        
        start_x = ref_x - offset_cols * hex_width
        start_y = ref_y - offset_rows * vert_spacing
        ref_row_parity = offset_rows % 2
        
        cols = int((max_x - start_x) / hex_width) + 2
        rows = int((max_y - start_y) / vert_spacing) + 2
        
        self.hex_map.tiles.clear()
        self.hex_map.hex_size = hex_size
        
        puffer = hex_size * 0.5
        created = 0
        for r in range(rows):
            for q in range(cols):
                row_is_odd = (r % 2) != ref_row_parity
                x_offset = (hex_width / 2) if row_is_odd else 0
                
                tile_cx = start_x + q * hex_width + x_offset
                tile_cy = start_y + r * vert_spacing
                
                if (min_x - puffer) <= tile_cx <= (max_x + puffer) and \
                   (min_y - puffer) <= tile_cy <= (max_y + puffer):
                    tile = HexTile(q=q, r=r, center_x=tile_cx, center_y=tile_cy)
                    self.hex_map.tiles[(q, r)] = tile
                    created += 1
        
        # Extrahiere Farben aus Hintergrundbild
        self._apply_colors_to_tiles()
        
        print(f"✅ Grid erstellt: {created} Tiles im Rechteck")
        self._update_stats()
        self._redraw()
    
    def _point_in_polygon(self, x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        """Ray-Casting Algorithmus: Prüfe ob Punkt (x,y) im Polygon liegt"""
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def _get_color_at_position(self, x: float, y: float) -> Optional[str]:
        """Extrahiere die durchschnittliche Farbe aus dem Hintergrundbild an einer Position"""
        if not self.bg_image:
            return None
        
        try:
            # Konvertiere zu RGB wenn nötig
            img = self.bg_image.convert('RGB')
            
            # Samplingbereich (kleiner Kreis um das Zentrum)
            sample_radius = int(self.norm_hex_size * 0.3)  # 30% des Hex-Radius
            
            # Begrenze Koordinaten auf Bildgrenzen
            cx = int(max(0, min(x, img.width - 1)))
            cy = int(max(0, min(y, img.height - 1)))
            
            # Sammle Pixel im Samplingbereich
            r_sum, g_sum, b_sum = 0, 0, 0
            count = 0
            
            for dy in range(-sample_radius, sample_radius + 1):
                for dx in range(-sample_radius, sample_radius + 1):
                    # Nur Pixel innerhalb des Kreises
                    if dx*dx + dy*dy <= sample_radius*sample_radius:
                        px = cx + dx
                        py = cy + dy
                        if 0 <= px < img.width and 0 <= py < img.height:
                            pixel = img.getpixel((px, py))
                            r_sum += pixel[0]
                            g_sum += pixel[1]
                            b_sum += pixel[2]
                            count += 1
            
            if count > 0:
                r = int(r_sum / count)
                g = int(g_sum / count)
                b = int(b_sum / count)
                return f"#{r:02x}{g:02x}{b:02x}"
            
        except Exception as e:
            print(f"⚠️ Farbextraktion fehlgeschlagen: {e}")
        
        return None
    
    def _apply_colors_to_tiles(self):
        """Wende Hintergrundfarben auf alle Tiles an und erkenne Terrain"""
        if not self.bg_image:
            return
        
        print("🎨 Extrahiere Farben aus Hintergrundbild...")
        
        terrain_counts = {}
        
        for tile in self.hex_map.tiles.values():
            color = self._get_color_at_position(tile.center_x, tile.center_y)
            if color:
                tile.fill_color = color
                
                # Versuche Terrain aus Farbe zu erkennen
                terrain = self._detect_terrain_from_color(color)
                if terrain:
                    tile.terrain = terrain
                    terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
        
        # Zeige Statistik
        if terrain_counts:
            print(f"🗺️ Terrain erkannt:")
            for terrain, count in sorted(terrain_counts.items(), key=lambda x: -x[1]):
                print(f"   {terrain}: {count} Tiles")
        
        print(f"✅ Farben für {len(self.hex_map.tiles)} Tiles extrahiert")
    
    def _detect_terrain_from_color(self, hex_color: str) -> Optional[str]:
        """Erkenne Terrain-Typ basierend auf Farbe"""
        # Konvertiere Hex zu RGB
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
        except:
            return None
        
        # Berechne HSV-ähnliche Werte für bessere Erkennung
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        brightness = (max_c + min_c) / 2 / 255  # 0-1
        saturation = 0 if max_c == min_c else (max_c - min_c) / (255 - abs(max_c + min_c - 255))
        
        # Farbton (vereinfacht)
        if max_c == min_c:
            hue = 0
        elif max_c == r:
            hue = 60 * ((g - b) / (max_c - min_c) % 6)
        elif max_c == g:
            hue = 60 * ((b - r) / (max_c - min_c) + 2)
        else:
            hue = 60 * ((r - g) / (max_c - min_c) + 4)
        
        # === TERRAIN-ERKENNUNG ===
        
        # Wasser: Blautöne
        if 180 <= hue <= 250 and saturation > 0.2 and brightness < 0.7:
            return "WATER"
        
        # Schnee/Eis: Sehr hell, wenig Sättigung
        if brightness > 0.85 and saturation < 0.2:
            return "SNOW"
        
        # Wüste/Sand: Gelb-Orange, hell
        if 30 <= hue <= 50 and brightness > 0.5 and saturation > 0.2:
            return "DESERT"
        
        # Berge/Felsen: Grau, mittlere Helligkeit
        if saturation < 0.15 and 0.25 < brightness < 0.65:
            return "MOUNTAINS"
        
        # Dunkler Wald: Dunkelgrün
        if 80 <= hue <= 160 and brightness < 0.25 and g > r:
            return "DARK_FOREST"
        
        # Wald: Grüntöne, mittel-dunkel
        if 70 <= hue <= 170 and saturation > 0.2 and brightness < 0.5 and g > r:
            return "FOREST"
        
        # Sumpf: Dunkelgrün-braun
        if 60 <= hue <= 100 and brightness < 0.4 and saturation < 0.4:
            return "SWAMP"
        
        # Hügel: Brauntöne
        if 20 <= hue <= 45 and saturation > 0.2 and 0.3 < brightness < 0.6:
            return "HILLS"
        
        # Straße: Hellbraun
        if 25 <= hue <= 40 and 0.4 < brightness < 0.65 and saturation > 0.15:
            return "ROAD"
        
        # Ebene/Gras: Hellgrün
        if 70 <= hue <= 150 and saturation > 0.15 and brightness > 0.35:
            return "PLAINS"
        
        # Ruinen: Dunkelgrau
        if saturation < 0.1 and 0.2 < brightness < 0.45:
            return "RUINS"
        
        # Default: Ebene
        return "PLAINS"
    
    def _auto_detect_terrain(self):
        """Automatische Terrain-Erkennung für alle Tiles basierend auf Farben"""
        if not self.hex_map.tiles:
            messagebox.showinfo("Info", "Keine Tiles vorhanden!\n\nErstelle zuerst Tiles mit dem Norm-Hexagon-Workflow.")
            return
        
        if not self.bg_image:
            # Kein Hintergrundbild - nutze vorhandene fill_colors
            terrain_counts = {}
            for tile in self.hex_map.tiles.values():
                if tile.fill_color:
                    terrain = self._detect_terrain_from_color(tile.fill_color)
                    if terrain:
                        tile.terrain = terrain
                        terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
            
            if terrain_counts:
                msg = "🗺️ Terrain erkannt:\n\n"
                for terrain, count in sorted(terrain_counts.items(), key=lambda x: -x[1]):
                    msg += f"• {terrain}: {count} Tiles\n"
                messagebox.showinfo("Auto-Terrain", msg)
            else:
                messagebox.showwarning("Warnung", "Keine Tiles mit Farben gefunden.\n\nLade zuerst ein Hintergrundbild und erstelle Tiles.")
        else:
            # Mit Hintergrundbild - extrahiere Farben und erkenne Terrain
            self._apply_colors_to_tiles()
            
            # Zähle Terrain-Typen
            terrain_counts = {}
            for tile in self.hex_map.tiles.values():
                terrain = tile.terrain
                terrain_counts[terrain] = terrain_counts.get(terrain, 0) + 1
            
            msg = "🗺️ Terrain aus Hintergrundbild erkannt:\n\n"
            for terrain, count in sorted(terrain_counts.items(), key=lambda x: -x[1]):
                msg += f"• {terrain}: {count} Tiles\n"
            messagebox.showinfo("Auto-Terrain", msg)
        
        # Zeichne neu mit Terrain-Farben
        self._redraw()
    
    def _toggle_background_var(self):
        """Toggle Hintergrund über Checkbox-Variable"""
        self.bg_visible = self.bg_visible_var.get()
        status = "sichtbar" if self.bg_visible else "ausgeblendet"
        print(f"🖼️ Hintergrund: {status}")
        self._redraw()
    
    def _toggle_bg_on_top_var(self):
        """Toggle Hintergrund-Layer über Checkbox-Variable"""
        self.bg_on_top = self.bg_on_top_var.get()
        status = "über Tiles" if self.bg_on_top else "unter Tiles"
        print(f"🖼️ Hintergrund: {status}")
        self._redraw()
    
    def _toggle_hex_outline_only(self):
        """Toggle Hexagon-Darstellung: Nur Umriss oder gefüllt"""
        self.hex_outline_only = self.hex_outline_only_var.get()
        status = "nur Umriss" if self.hex_outline_only else "gefüllt"
        print(f"🔷 Hexagone: {status}")
        self._invalidate_edge_blur_cache()
        self._redraw()
    
    def _on_edge_blur_change(self, value):
        """Edge-Blur-Stärke geändert"""
        self.hex_edge_blur = int(value)
        self._invalidate_edge_blur_cache()
        self._redraw()
    
    def _on_outline_opacity_change(self, value):
        """Outline-Opacity geändert"""
        self.hex_outline_opacity = float(value)
        self._redraw()
    
    def _on_outline_width_change(self, value):
        """Outline-Breite geändert"""
        self.hex_outline_width = int(value)
        self._invalidate_edge_blur_cache()
        self._redraw()
    
    def _choose_outline_color(self):
        """Farbauswahl-Dialog für Outline"""
        color = colorchooser.askcolor(initialcolor=self.hex_outline_color, title="Linienfarbe wählen")
        if color[1]:
            self._set_outline_color(color[1])
    
    def _set_outline_color(self, color: str):
        """Setze Outline-Farbe"""
        self.hex_outline_color = color
        self.outline_color_btn.configure(bg=color)
        self._redraw()
    
    # === TEXT ANNOTATION FUNKTIONEN ===
    
    def _on_text_size_change(self, value):
        """Textgröße geändert"""
        self.current_text_size = int(value)
        # Update ausgewählte Annotation wenn vorhanden
        if self.selected_annotation is not None and self.selected_annotation < len(self.text_annotations):
            self.text_annotations[self.selected_annotation]['size'] = self.current_text_size
            self._redraw()
    
    def _on_font_change(self, event=None):
        """Schriftart geändert"""
        self.current_font_family = self.font_var.get()
        if self.selected_annotation is not None and self.selected_annotation < len(self.text_annotations):
            self.text_annotations[self.selected_annotation]['font'] = self.current_font_family
            self._redraw()
    
    def _on_text_style_change(self):
        """Text-Stil geändert (Fett/Kursiv)"""
        self.current_text_bold = self.bold_var.get()
        self.current_text_italic = self.italic_var.get()
        if self.selected_annotation is not None and self.selected_annotation < len(self.text_annotations):
            self.text_annotations[self.selected_annotation]['bold'] = self.current_text_bold
            self.text_annotations[self.selected_annotation]['italic'] = self.current_text_italic
            self._redraw()
    
    def _choose_text_color(self):
        """Farbauswahl-Dialog für Text"""
        color = colorchooser.askcolor(initialcolor=self.current_text_color, title="Textfarbe wählen")
        if color[1]:
            self._set_text_color(color[1])
    
    def _set_text_color(self, color: str):
        """Setze Text-Farbe"""
        self.current_text_color = color
        self.text_color_btn.configure(bg=color)
        if self.selected_annotation is not None and self.selected_annotation < len(self.text_annotations):
            self.text_annotations[self.selected_annotation]['color'] = self.current_text_color
            self._redraw()
    
    def _add_text_annotation(self, x: float, y: float):
        """Füge neue Text-Annotation an Position hinzu"""
        # Dialog für Text-Eingabe
        dialog = TextInputDialog(self, self.current_font_family, self.current_text_size, 
                                 self.current_text_color, self.current_text_bold, self.current_text_italic)
        self.wait_window(dialog)
        
        if dialog.result:
            annotation = {
                'text': dialog.result['text'],
                'x': x,
                'y': y,
                'color': dialog.result.get('color', self.current_text_color),
                'size': dialog.result.get('size', self.current_text_size),
                'font': dialog.result.get('font', self.current_font_family),
                'bold': dialog.result.get('bold', self.current_text_bold),
                'italic': dialog.result.get('italic', self.current_text_italic),
                'rotation': dialog.result.get('rotation', 0)
            }
            self.text_annotations.append(annotation)
            self.selected_annotation = len(self.text_annotations) - 1
            print(f"🏷️ Text hinzugefügt: '{annotation['text']}' bei ({x:.0f}, {y:.0f})")
            self._redraw()
    
    def _delete_selected_annotation(self):
        """Lösche ausgewählte Text-Annotation"""
        if self.selected_annotation is not None and self.selected_annotation < len(self.text_annotations):
            deleted = self.text_annotations.pop(self.selected_annotation)
            print(f"🗑️ Text gelöscht: '{deleted['text']}'")
            self.selected_annotation = None
            self._redraw()
        else:
            messagebox.showinfo("Kein Text ausgewählt", "Bitte zuerst einen Text auf der Karte auswählen.")
    
    def _find_annotation_at(self, x: float, y: float) -> Optional[int]:
        """Finde Annotation an Position"""
        for i, ann in enumerate(self.text_annotations):
            # Ungefähre Hitbox basierend auf Textgröße
            size = ann.get('size', 16)
            text_len = len(ann.get('text', '')) * size * 0.6  # Geschätzte Breite
            ax, ay = ann['x'], ann['y']
            if ax - 10 <= x <= ax + text_len and ay - size <= y <= ay + size // 2:
                return i
        return None
    
    def _invalidate_edge_blur_cache(self):
        """Cache für Edge-Blur invalidieren"""
        self.bg_with_hex_edges = None
    
    def _create_edge_blurred_background(self):
        """Erstelle Hintergrundbild mit verschwommenen Hexagon-Kanten"""
        if not self.bg_image or self.hex_edge_blur <= 0:
            return None
        
        from PIL import ImageFilter, ImageDraw as PILImageDraw
        
        # Erstelle Maske für die Hexagon-Kanten
        mask = Image.new('L', (self.bg_image.width, self.bg_image.height), 0)
        mask_draw = PILImageDraw.Draw(mask)
        
        # Zeichne alle Hexagon-Kanten in die Maske
        edge_width = max(self.hex_edge_blur * 2, self.hex_outline_width * 3)
        for (q, r), tile in self.hex_map.tiles.items():
            vertices = self._get_tile_vertices_for_image(tile)
            # Zeichne Umriss in die Maske
            if len(vertices) >= 6:
                points = [(int(v[0]), int(v[1])) for v in vertices]
                mask_draw.polygon(points, outline=255, width=edge_width)
        
        # Verschwimme das gesamte Originalbild
        blurred = self.bg_image.filter(ImageFilter.GaussianBlur(radius=self.hex_edge_blur))
        
        # Verschwimme auch die Maske für weichere Übergänge
        mask = mask.filter(ImageFilter.GaussianBlur(radius=self.hex_edge_blur // 2 + 1))
        
        # Kombiniere: Original wo keine Kanten, Verschwommen wo Kanten
        result = Image.composite(blurred, self.bg_image, mask)
        
        return result
    
    def _get_tile_vertices_for_image(self, tile) -> list:
        """Berechne Tile-Vertices in Bild-Koordinaten (ohne Zoom/Offset)"""
        coord = (tile.q, tile.r)
        tile_size = self.individual_tile_sizes.get(coord, self.hex_map.hex_size)
        
        vertices = []
        for i in range(6):
            if self.hex_map.orientation == "pointy-top":
                angle_deg = 60 * i - 30
            else:
                angle_deg = 60 * i
            
            angle_rad = math.radians(angle_deg)
            x = tile.center_x + tile_size * math.cos(angle_rad)
            y = tile.center_y + tile_size * math.sin(angle_rad)
            vertices.append((x, y))
        
        return vertices
    
    def _toggle_background(self):
        """Schalte Hintergrund-Sichtbarkeit um"""
        self.bg_visible = not self.bg_visible
        self.bg_visible_var.set(self.bg_visible)
        status = "sichtbar" if self.bg_visible else "ausgeblendet"
        print(f"🖼️ Hintergrund: {status}")
        self._redraw()
    
    def _toggle_bg_on_top(self):
        """Schalte Hintergrund zwischen oben/unten"""
        self.bg_on_top = not self.bg_on_top
        self.bg_on_top_var.set(self.bg_on_top)
        status = "über Tiles" if self.bg_on_top else "unter Tiles"
        print(f"🖼️ Hintergrund: {status}")
        self._redraw()
    
    def _remove_background(self):
        """Entferne Hintergrundbild komplett"""
        if not self.bg_image:
            messagebox.showinfo("Info", "Kein Hintergrundbild geladen.")
            return
        
        if messagebox.askyesno("Hintergrund entfernen", 
                               "Hintergrundbild wirklich entfernen?\n\n"
                               "Die Tile-Farben bleiben erhalten."):
            self.bg_image = None
            self.bg_photo = None
            print("🗑️ Hintergrundbild entfernt")
            self._redraw()
    
    def _generate_hex_preview(self, cx: float, cy: float, size: float) -> List[Tuple[int, int]]:
        """Generiere Hexagon-Vertices für Vorschau (pointy-top)"""
        vertices = []
        for i in range(6):
            angle = math.pi / 6 + i * math.pi / 3  # 30° + i*60°
            x = cx + size * math.cos(angle)
            y = cy + size * math.sin(angle)
            vertices.append(self._map_to_canvas(x, y))
        return vertices
    
    def _show_fill_grid_dialog(self):
        """Dialog: Grid mit dieser Hex-Größe füllen"""
        dialog = tk.Toplevel(self)
        dialog.title("✏️ Grid aus Template erstellen")
        dialog.configure(bg="#1a1a2e")
        dialog.geometry("350x280")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 350) // 2
        y = self.winfo_y() + (self.winfo_height() - 280) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Info
        tk.Label(dialog, text=f"📐 Hex-Größe: {self.template_hex_size:.1f} px",
                font=("Arial", 12, "bold"), bg="#1a1a2e", fg="#e94560").pack(pady=10)
        
        tk.Label(dialog, text="Grid-Bereich füllen:", bg="#1a1a2e", fg="white").pack()
        
        # Optionen
        frame = tk.Frame(dialog, bg="#1a1a2e")
        frame.pack(pady=10)
        
        tk.Label(frame, text="Spalten:", bg="#1a1a2e", fg="white").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        cols_var = tk.IntVar(value=15)
        tk.Entry(frame, textvariable=cols_var, width=8, bg="#0f3460", fg="white").grid(row=0, column=1, pady=5)
        
        tk.Label(frame, text="Zeilen:", bg="#1a1a2e", fg="white").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        rows_var = tk.IntVar(value=12)
        tk.Entry(frame, textvariable=rows_var, width=8, bg="#0f3460", fg="white").grid(row=1, column=1, pady=5)
        
        # Orientierung
        tk.Label(frame, text="Orientierung:", bg="#1a1a2e", fg="white").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        orient_var = tk.StringVar(value="pointy-top")
        orient_combo = ttk.Combobox(frame, textvariable=orient_var, 
                                   values=["pointy-top", "flat-top"], state="readonly", width=12)
        orient_combo.grid(row=2, column=1, pady=5)
        
        # Start-Offset (um Grid an Karte auszurichten)
        tk.Label(frame, text="Start X:", bg="#1a1a2e", fg="white").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        start_x_var = tk.DoubleVar(value=self.draw_hex_start[0] if self.draw_hex_start else 0)
        tk.Entry(frame, textvariable=start_x_var, width=8, bg="#0f3460", fg="white").grid(row=3, column=1, pady=5)
        
        tk.Label(frame, text="Start Y:", bg="#1a1a2e", fg="white").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        start_y_var = tk.DoubleVar(value=self.draw_hex_start[1] if self.draw_hex_start else 0)
        tk.Entry(frame, textvariable=start_y_var, width=8, bg="#0f3460", fg="white").grid(row=4, column=1, pady=5)
        
        def create_grid():
            self.hex_map.hex_size = self.template_hex_size
            self.hex_map.orientation = orient_var.get()
            self._create_aligned_grid(
                cols_var.get(), rows_var.get(),
                start_x_var.get(), start_y_var.get(),
                self.template_hex_size, orient_var.get()
            )
            self._update_stats()
            self._redraw()
            dialog.destroy()
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg="#1a1a2e")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="✓ Grid erstellen", command=create_grid,
                 bg="#28a745", fg="white", padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=dialog.destroy,
                 bg="#dc3545", fg="white", padx=15).pack(side=tk.LEFT, padx=5)
    
    def _create_aligned_grid(self, cols: int, rows: int, start_x: float, start_y: float,
                            hex_size: float, orientation: str):
        """Erstelle Grid ausgerichtet am Start-Punkt"""
        self.hex_map.tiles.clear()
        self.hex_map.hex_size = hex_size
        self.hex_map.orientation = orientation
        
        if orientation == "pointy-top":
            hex_width = hex_size * math.sqrt(3)
            hex_height = hex_size * 2
            vert_spacing = hex_height * 0.75
            
            for r in range(rows):
                for q in range(cols):
                    x_offset = (hex_width / 2) if (r % 2 == 1) else 0
                    cx = start_x + q * hex_width + x_offset
                    cy = start_y + r * vert_spacing
                    
                    tile = HexTile(q=q, r=r, center_x=cx, center_y=cy)
                    self.hex_map.tiles[(q, r)] = tile
        else:
            # flat-top
            hex_width = hex_size * 2
            hex_height = hex_size * math.sqrt(3)
            horiz_spacing = hex_width * 0.75
            
            for r in range(rows):
                for q in range(cols):
                    y_offset = (hex_height / 2) if (q % 2 == 1) else 0
                    cx = start_x + q * horiz_spacing
                    cy = start_y + r * hex_height + y_offset
                    
                    tile = HexTile(q=q, r=r, center_x=cx, center_y=cy)
                    self.hex_map.tiles[(q, r)] = tile
        
        print(f"✅ Grid erstellt: {cols}×{rows} = {len(self.hex_map.tiles)} Tiles, Größe: {hex_size:.1f}px")
    
    def _on_right_click(self, event):
        """Rechtsklick: Properties Dialog oder Extent löschen, oder Panning starten"""
        x, y = self._canvas_to_map(event.x, event.y)
        
        # Panning-Start merken für Rechtsklick + Ziehen
        self.pan_start = (event.x, event.y)
        
        # === EXTENT LÖSCHEN ===
        if self.current_tool == "place_extent":
            for i, (ex, ey) in enumerate(self.extent_hexagons):
                dist = math.sqrt((x - ex)**2 + (y - ey)**2)
                if dist < self.norm_hex_size * 0.6:
                    del self.extent_hexagons[i]
                    print(f"🗑️ Extent-Punkt {i+1} gelöscht")
                    self._redraw()
                    return
        
        # === NORM-HEX LÖSCHEN ===
        if self.current_tool == "draw_hex" and self.norm_hex_center:
            dist = math.sqrt((x - self.norm_hex_center[0])**2 + (y - self.norm_hex_center[1])**2)
            if dist < self.norm_hex_size * 1.2:
                if messagebox.askyesno("Norm-Hex löschen?", "Norm-Hexagon löschen?"):
                    self.norm_hex_center = None
                    self.norm_hex_size = 50.0
                    print("🗑️ Norm-Hexagon gelöscht")
                    self._redraw()
                return
        
        # === TILE PROPERTIES ===
        tile = self.hex_map.get_tile_at_pixel(x, y)
        if tile:
            self._show_tile_properties(tile)
    
    def _on_double_click(self, event):
        """Doppelklick: Properties Dialog"""
        x, y = self._canvas_to_map(event.x, event.y)
        tile = self.hex_map.get_tile_at_pixel(x, y)
        if tile:
            self._show_tile_properties(tile)
    
    def _show_tile_properties(self, tile: HexTile):
        dialog = HexTilePropertiesDialog(self, tile, self.hex_map)
        self.wait_window(dialog)
        if dialog.result:
            self._redraw()
    
    def _on_scroll(self, event):
        # Zoom
        if event.delta > 0:
            self.zoom *= 1.1
        else:
            self.zoom /= 1.1
        self.zoom = max(0.2, min(3.0, self.zoom))
        self._redraw()
    
    def _canvas_to_map(self, cx: int, cy: int) -> Tuple[float, float]:
        """Konvertiere Canvas-Koordinaten zu Map-Koordinaten"""
        x = (cx - self.offset_x) / self.zoom
        y = (cy - self.offset_y) / self.zoom
        return x, y
    
    def _map_to_canvas(self, x: float, y: float) -> Tuple[int, int]:
        """Konvertiere Map-Koordinaten zu Canvas-Koordinaten"""
        cx = int(x * self.zoom + self.offset_x)
        cy = int(y * self.zoom + self.offset_y)
        return cx, cy
    
    def _update_info(self, tile: HexTile):
        """Update Info-Panel"""
        terrain = tile.terrain_type
        coord = (tile.q, tile.r)
        info = f"Position: ({tile.q}, {tile.r})\n"
        info += f"Terrain: {terrain.display_name}\n"
        if tile.terrain_name:
            info += f"Name: {tile.terrain_name}\n"
        info += f"Schwierigkeit: {tile.total_difficulty}\n"
        
        # Zeige individuelle Größe falls vorhanden
        if coord in self.individual_tile_sizes:
            info += f"Größe: {self.individual_tile_sizes[coord]:.0f}px (individuell)\n"
        
        if tile.local_weather:
            weather = WeatherType[tile.local_weather]
            info += f"Wetter: {weather.icon} {weather.display_name}\n"
        
        if tile.events:
            info += f"Events: {len(tile.events)}\n"
            for e in tile.events[:3]:
                info += f"  • {e.get('name', 'Event')}\n"
        
        self.info_label.configure(text=info)
    
    def _update_stats(self):
        self.stats_label.configure(text=f"Tiles: {len(self.hex_map.tiles)}")
    
    def _draw_background(self):
        """Zeichne Hintergrundbild"""
        if not self.bg_image:
            return
        
        # Wähle Bild: Mit Edge-Blur oder Original
        if self.hex_edge_blur > 0 and self.hex_map.tiles:
            # Erstelle Edge-Blur-Bild falls nötig (gecacht)
            if self.bg_with_hex_edges is None:
                print(f"🔄 Erstelle Edge-Blur-Bild (Stärke: {self.hex_edge_blur})...")
                self.bg_with_hex_edges = self._create_edge_blurred_background()
            source_image = self.bg_with_hex_edges if self.bg_with_hex_edges else self.bg_image
        else:
            source_image = self.bg_image
        
        # Skaliere und positioniere Bild
        w = int(source_image.width * self.zoom)
        h = int(source_image.height * self.zoom)
        scaled = source_image.resize((w, h), Image.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(scaled)
        self.canvas.create_image(self.offset_x, self.offset_y, 
                                image=self.bg_photo, anchor=tk.NW, tags="background")
    
    def _redraw(self):
        """Zeichne Canvas neu"""
        self.canvas.delete("all")
        
        # Hintergrundbild (unten) - nur wenn sichtbar und NICHT oben
        if self.bg_image and self.bg_visible and not self.bg_on_top:
            self._draw_background()
        
        # Zeichne Hexagone
        for (q, r), tile in self.hex_map.tiles.items():
            self._draw_hexagon(tile)
        
        # Hintergrundbild (oben) - nur wenn sichtbar und oben
        if self.bg_image and self.bg_visible and self.bg_on_top:
            self._draw_background()
        
        # Zeichne Auswahl (einzeln)
        if self.selected_tile and self.selected_tile in self.hex_map.tiles:
            tile = self.hex_map.tiles[self.selected_tile]
            self._draw_hexagon_outline(tile, "#ffff00", 3)
        
        # Zeichne Mehrfachauswahl
        for coord in self.selected_tiles:
            if coord in self.hex_map.tiles:
                tile = self.hex_map.tiles[coord]
                self._draw_hexagon_outline(tile, "#00ffff", 2)
        
        # === TEXT ANNOTATIONS ZEICHNEN ===
        self._draw_text_annotations()
        
        # === TAG/NACHT OVERLAY ===
        darkness = self.darkness_var.get()
        if darkness > 0:
            # Dunkelheits-Rechteck über alles
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            # Berechne Alpha-Wert (0-255) -> Hex-Farbe
            # Tkinter Canvas unterstützt kein echtes Alpha, daher simulieren wir mit stipple
            self.canvas.create_rectangle(0, 0, canvas_w, canvas_h,
                                        fill="#000020", stipple="gray50" if darkness < 0.5 else "gray75",
                                        outline="", tags="darkness_overlay")
        
        # === WETTER OVERLAY HINWEIS ===
        weather = self.hex_map.global_weather
        if weather and weather != "CLEAR":
            # Zeige Wetter-Indikator
            weather_icons = {
                "RAIN": "🌧️", "RAIN_LIGHT": "🌦️", "RAIN_HEAVY": "⛈️",
                "SNOW": "❄️", "SNOW_LIGHT": "🌨️", "SNOW_HEAVY": "❄️❄️",
                "FOG": "🌫️", "CLOUDY": "☁️", "STORM": "⛈️", "WIND": "💨"
            }
            icon = weather_icons.get(weather, "🌤️")
            self.canvas.create_text(50, 50, text=f"{icon} {weather}",
                                   font=("Arial", 14, "bold"), fill="white",
                                   anchor=tk.NW, tags="weather_indicator")
        
        # === HEX-ZEICHNEN VORSCHAU ===
        if self.current_tool == "draw_hex" and self.preview_hex:
            # Zeichne Vorschau-Hexagon während des Ziehens
            self.canvas.create_polygon(self.preview_hex, 
                                       outline="#00ff00", width=3, fill="",
                                       dash=(5, 3), tags="preview_hex")
            # Zeige Größe
            if self.draw_hex_start:
                cx, cy = self._map_to_canvas(*self.draw_hex_start)
                self.canvas.create_text(cx, cy - 20, 
                                       text=f"📐 {self.template_hex_size:.0f}px",
                                       font=("Arial", 11, "bold"), fill="#00ff00",
                                       tags="preview_hex")
        
        # === NORM-HEXAGON ANZEIGEN ===
        if self.norm_hex_center and self.norm_hex_size > 0:
            # Zeichne das Norm-Hexagon (gelb, dick)
            vertices = []
            cx, cy = self.norm_hex_center
            for i in range(6):
                angle = math.pi / 6 + i * math.pi / 3
                vx = cx + self.norm_hex_size * math.cos(angle)
                vy = cy + self.norm_hex_size * math.sin(angle)
                vertices.append(self._map_to_canvas(vx, vy))
            
            self.canvas.create_polygon(vertices, outline="#ffff00", width=3, fill="",
                                       tags="norm_hex")
            
            # Zeige Info
            cx_canvas, cy_canvas = self._map_to_canvas(cx, cy)
            self.canvas.create_text(cx_canvas, cy_canvas, 
                                   text=f"NORM\n{self.norm_hex_size:.0f}px",
                                   font=("Arial", 9, "bold"), fill="#ffff00",
                                   tags="norm_hex")
        
        # === EXTENT-POLYGON ANZEIGEN ===
        if len(self.extent_hexagons) >= 2:
            # Zeichne Verbindungslinien zwischen Extent-Punkten (Polygon-Umriss)
            polygon_points = []
            for (ex, ey) in self.extent_hexagons:
                polygon_points.append(self._map_to_canvas(ex, ey))
            
            # Schließe das Polygon wenn >= 3 Punkte
            if len(polygon_points) >= 3:
                # Gefülltes halbtransparentes Polygon
                self.canvas.create_polygon(polygon_points, 
                                          outline="#00ffff", width=2,
                                          fill="", dash=(10, 5),
                                          tags="extent_polygon")
                # Schließende Linie
                p0 = polygon_points[0]
                pn = polygon_points[-1]
                self.canvas.create_line(pn[0], pn[1], p0[0], p0[1],
                                       fill="#00ffff", width=2, dash=(10, 5),
                                       tags="extent_polygon")
            else:
                # Bei 2 Punkten: Rechteck andeuten
                p1 = polygon_points[0]
                p2 = polygon_points[1]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                       fill="#00ffff", width=2, dash=(10, 5),
                                       tags="extent_polygon")
                # Zeige Rechteck-Vorschau
                self.canvas.create_rectangle(p1[0], p1[1], p2[0], p2[1],
                                            outline="#00ffff", width=1, dash=(5, 5),
                                            tags="extent_polygon")
        
        # === EXTENT-PUNKTE ANZEIGEN ===
        for i, (ex, ey) in enumerate(self.extent_hexagons):
            cx_canvas, cy_canvas = self._map_to_canvas(ex, ey)
            
            # Kreis um den Punkt
            r = int(12 * self.zoom)
            self.canvas.create_oval(cx_canvas - r, cy_canvas - r, 
                                   cx_canvas + r, cy_canvas + r,
                                   outline="#00ffff", width=3, fill="",
                                   tags="extent_point")
            
            # Nummer anzeigen
            self.canvas.create_text(cx_canvas, cy_canvas, 
                                   text=f"{i+1}",
                                   font=("Arial", 10, "bold"), fill="#ffffff",
                                   tags="extent_point")
    
    def _get_tile_vertices(self, tile: HexTile) -> List[Tuple[float, float]]:
        """Berechne die Vertices eines Tiles mit individueller Größe"""
        coord = (tile.q, tile.r)
        tile_size = self.individual_tile_sizes.get(coord, self.hex_map.hex_size)
        
        vertices = []
        for i in range(6):
            if self.hex_map.orientation == "pointy-top":
                angle_deg = 60 * i - 30
            else:
                angle_deg = 60 * i
            
            angle_rad = math.radians(angle_deg)
            x = tile.center_x + tile_size * math.cos(angle_rad)
            y = tile.center_y + tile_size * math.sin(angle_rad)
            vertices.append((x, y))
        
        return vertices
    
    def _draw_hexagon(self, tile: HexTile):
        """Zeichne ein einzelnes Hexagon"""
        coord = (tile.q, tile.r)
        # Verwende individuelle Größe falls vorhanden
        vertices = self._get_tile_vertices(tile)
        canvas_vertices = [self._map_to_canvas(x, y) for x, y in vertices]
        
        # Farbe
        color = tile.display_color
        
        # Highlight wenn dieses Tile gerade verschoben/skaliert wird
        is_moving = self.moving_tile == coord
        is_scaling = self.scaling_tile == coord
        
        # Berechne Outline-Farbe mit simulierter Opacity (Mischung mit Weiß)
        def blend_color_with_alpha(hex_color: str, alpha: float) -> str:
            """Simuliere Alpha durch Mischung mit Weiß (für helle Hintergründe)"""
            if alpha >= 1.0:
                return hex_color
            if alpha <= 0.0:
                return ""  # Keine Outline
            # Parse hex color
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            # Blend mit Weiß (255, 255, 255) basierend auf Alpha
            # Für dunklere Hintergründe wäre Schwarz besser
            bg = 200  # Mittlerer Grauton als Misch-Basis
            r = int(r * alpha + bg * (1 - alpha))
            g = int(g * alpha + bg * (1 - alpha))
            b = int(b * alpha + bg * (1 - alpha))
            return f"#{r:02x}{g:02x}{b:02x}"
        
        # Nur Umriss-Modus
        if self.hex_outline_only:
            if is_moving or is_scaling:
                outline_color = "#ff00ff"
                outline_width = self.hex_outline_width + 1
            else:
                # Wende Opacity an wenn < 1.0
                if self.hex_outline_opacity <= 0:
                    return  # Keine Outline, nichts zeichnen
                outline_color = blend_color_with_alpha(self.hex_outline_color, self.hex_outline_opacity)
                outline_width = self.hex_outline_width
            
            # Zeichne Outline (oder verwende stipple für transparenten Effekt)
            if self.hex_outline_opacity < 0.5 and self.hex_outline_opacity > 0:
                # Sehr transparent: nutze stipple für gepunkteten Look
                self.canvas.create_polygon(canvas_vertices, outline=self.hex_outline_color, 
                                          width=outline_width, fill="", dash=(2, 2))
            else:
                self.canvas.create_polygon(canvas_vertices, outline=outline_color, 
                                          width=outline_width, fill="")
        # Zeichne gefülltes Hexagon (halbtransparent wenn Hintergrundbild)
        elif self.bg_image:
            # Mit Hintergrundbild: Zeige fill_color als halbtransparenten Fill
            if tile.fill_color:
                # Zeichne gefülltes Hex mit extrahierter Farbe (leicht transparent wirkt durch stipple)
                self.canvas.create_polygon(canvas_vertices, outline=color, width=2, 
                                          fill=tile.fill_color, stipple="gray50")
            else:
                # Nur Umriss wenn keine Farbe extrahiert
                self.canvas.create_polygon(canvas_vertices, outline=color, width=2, fill="")
        else:
            self.canvas.create_polygon(canvas_vertices, fill=color, outline="#333333", width=1)
        
        # Move/Scale Indikator
        if self.current_tool == "move_scale" and (is_moving or is_scaling):
            cx, cy = self._map_to_canvas(tile.center_x, tile.center_y)
            tile_size = self.individual_tile_sizes.get(coord, self.hex_map.hex_size)
            r = int(tile_size * self.zoom * 0.3)
            # Zentrum-Indikator
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#ff00ff", width=2, fill="", dash=(5, 3))
        
        # Event-Marker
        if tile.events:
            cx, cy = self._map_to_canvas(tile.center_x, tile.center_y)
            r = int(8 * self.zoom)
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#ff0000", outline="white")
            self.canvas.create_text(cx, cy, text=str(len(tile.events)), fill="white", font=("Arial", 8))
        
        # Wetter-Marker
        if tile.local_weather:
            cx, cy = self._map_to_canvas(tile.center_x, tile.center_y - self.hex_map.hex_size * 0.4)
            weather = WeatherType[tile.local_weather]
            self.canvas.create_text(cx, cy, text=weather.icon, font=("Arial", 12))
        
        # Boss-Hexagon-Marker (halbtransparentes oranges Overlay)
        if getattr(tile, 'is_boss_hex', False):
            # Zeichne halbtransparentes oranges Overlay
            self.canvas.create_polygon(canvas_vertices, fill="#ff8c00", 
                                       outline="#ff4500", width=3, stipple="gray50")
            # Boss-Icon im Zentrum
            cx, cy = self._map_to_canvas(tile.center_x, tile.center_y)
            self.canvas.create_text(cx, cy, text="🐉", font=("Arial", int(14 * self.zoom)))
        
        # Spawn-Hexagon-Marker (halbtransparentes grünes Overlay für Spieler-Startpunkte)
        if getattr(tile, 'is_spawn_hex', False):
            # Zeichne halbtransparentes grünes Overlay
            self.canvas.create_polygon(canvas_vertices, fill="#00ff00", 
                                       outline="#00aa00", width=3, stipple="gray50")
            # Spawn-Icon im Zentrum
            cx, cy = self._map_to_canvas(tile.center_x, tile.center_y)
            self.canvas.create_text(cx, cy, text="🎮", font=("Arial", int(14 * self.zoom)))
    
    def _draw_hexagon_outline(self, tile: HexTile, color: str, width: int):
        """Zeichne Hexagon-Umriss (für Auswahl)"""
        vertices = self._get_tile_vertices(tile)
        canvas_vertices = [self._map_to_canvas(x, y) for x, y in vertices]
        self.canvas.create_polygon(canvas_vertices, outline=color, width=width, fill="")
    
    def _draw_text_annotations(self):
        """Zeichne alle Text-Annotations"""
        for i, ann in enumerate(self.text_annotations):
            x, y = ann['x'], ann['y']
            cx, cy = self._map_to_canvas(x, y)
            
            text = ann.get('text', '')
            color = ann.get('color', '#000000')
            size = int(ann.get('size', 16) * self.zoom)
            font_family = ann.get('font', 'Arial')
            bold = ann.get('bold', False)
            italic = ann.get('italic', False)
            rotation = ann.get('rotation', 0)
            
            # Erstelle Font-String
            style = ""
            if bold:
                style += "bold "
            if italic:
                style += "italic"
            style = style.strip() if style else "normal"
            
            font = (font_family, max(8, size), style)
            
            # Zeichne Text (tkinter unterstützt keine Rotation direkt)
            # Für Rotation müssten wir PIL nutzen, aber einfacher Text geht so:
            text_id = self.canvas.create_text(cx, cy, text=text, font=font, fill=color,
                                              anchor=tk.W, tags=f"annotation_{i}")
            
            # Highlight wenn ausgewählt
            if i == self.selected_annotation:
                # Zeichne Rahmen um den Text
                bbox = self.canvas.bbox(text_id)
                if bbox:
                    self.canvas.create_rectangle(bbox[0]-3, bbox[1]-3, bbox[2]+3, bbox[3]+3,
                                                outline="#e94560", width=2, dash=(3, 3),
                                                tags=f"annotation_select_{i}")


def open_hexagon_editor(parent=None, hex_map: Optional[HexagonMap] = None):
    """Öffne den Hexagon-Editor"""
    if parent is None:
        root = tk.Tk()
        root.withdraw()
        editor = HexagonMapEditor(root, hex_map)
        editor.mainloop()
    else:
        editor = HexagonMapEditor(parent, hex_map)
    return editor


# Test
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    # Erstelle Test-Map
    test_map = HexagonMap("Test-Karte")
    test_map.create_grid(8, 6, hex_size=45)
    
    # Setze einige Terrains
    test_map.set_terrain(0, 0, "FOREST", "Alter Wald")
    test_map.set_terrain(1, 0, "MOUNTAINS", "Nebelgebirge")
    test_map.set_terrain(2, 1, "WATER", "Anduin")
    test_map.set_terrain(3, 2, "VILLAGE", "Bree")
    
    editor = HexagonMapEditor(root, test_map)
    root.mainloop()
