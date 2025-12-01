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
from typing import Optional, Tuple, List, Dict

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


class HexagonMapEditor(tk.Toplevel):
    """Hauptfenster des Hexagon-Map-Editors"""
    
    def __init__(self, parent, hex_map: Optional[HexagonMap] = None):
        super().__init__(parent)
        
        self.hex_map = hex_map or HexagonMap("Neue Hexagon-Karte")
        self.current_tool = "select"  # select, draw_hex, terrain, event, weather
        self.current_terrain = "PLAINS"
        self.current_weather = "RAIN"
        self.selected_tile: Optional[Tuple[int, int]] = None
        
        # Zoom/Pan
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None
        
        # Hex-Zeichenmodus Variablen
        self.draw_hex_start: Optional[Tuple[float, float]] = None  # Zentrum des Template-Hex
        self.template_hex_size: float = 0.0  # Größe des gezeichneten Hex
        self.preview_hex: Optional[List[Tuple[int, int]]] = None  # Vorschau-Vertices
        
        # Background image
        self.bg_image: Optional[Image.Image] = None
        self.bg_photo: Optional[ImageTk.PhotoImage] = None
        
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
        # === TOOLBAR ===
        toolbar = tk.Frame(self, bg="#0f3460", height=50)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)
        
        # Tool Buttons
        tools = [
            ("🖱️ Auswahl", "select"),
            ("✏️ Hex zeichnen", "draw_hex"),
            ("🗺️ Terrain", "terrain"),
            ("⚔️ Events", "event"),
            ("🌦️ Wetter", "weather"),
        ]
        
        self.tool_buttons = {}
        for text, tool in tools:
            btn = tk.Button(toolbar, text=text, command=lambda t=tool: self._set_tool(t),
                           bg="#16213e", fg="white", font=("Arial", 10),
                           relief=tk.FLAT, padx=10, pady=5)
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
        
        # Grid Button
        tk.Button(toolbar, text="🔲 Grid erstellen", command=self._create_grid_dialog,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # Random Events
        tk.Button(toolbar, text="🎲 Zufalls-Events", command=self._random_events_dialog,
                 bg="#16213e", fg="white", font=("Arial", 10),
                 relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=2, pady=8)
        
        # === MAIN AREA ===
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#1a1a2e",
                                    sashwidth=4, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # === CANVAS ===
        canvas_frame = tk.Frame(main_paned, bg="#2a2a2a")
        main_paned.add(canvas_frame, width=900)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#2a2a2a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # === SIDEBAR ===
        sidebar = tk.Frame(main_paned, bg="#16213e", width=280)
        main_paned.add(sidebar)
        
        self._create_sidebar(sidebar)
    
    def _create_sidebar(self, parent):
        """Erstelle Sidebar mit Tool-Optionen"""
        
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
        
        # Double click für Properties
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
    
    def _set_tool(self, tool: str):
        self.current_tool = tool
        for t, btn in self.tool_buttons.items():
            if t == tool:
                btn.configure(bg="#e94560", relief=tk.SUNKEN)
            else:
                btn.configure(bg="#16213e", relief=tk.FLAT)
    
    def _select_terrain(self, terrain: str):
        self.current_terrain = terrain
        for t, btn in self.terrain_buttons.items():
            if t == terrain:
                btn.configure(relief=tk.SUNKEN)
            else:
                btn.configure(relief=tk.RAISED)
    
    def _select_weather(self, weather: str):
        self.current_weather = weather
    
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
                print(f"✅ Bild geladen: {self.bg_image.size}", flush=True)
            except Exception as e:
                print(f"⚠️ Konnte Bild nicht laden: {e}", flush=True)
        
        # WICHTIG: Sofort redraw um Hintergrund anzuzeigen
        if self.bg_image:
            print(f"   Zeige Hintergrundbild: {self.bg_image.size}", flush=True)
            self._redraw()
        else:
            messagebox.showwarning("Hintergrund", 
                                  "Konnte Kartenbild nicht laden.\n"
                                  "Die Hexagone werden ohne Hintergrund angezeigt.")
        
        # DANN Hexagone erkennen
        print("   Starte Hexagon-Erkennung...", flush=True)
        success = self.hex_map.load_from_svg(filepath)
        
        # Zeige Ergebnis
        tile_count = len(self.hex_map.tiles)
        print(f"   {tile_count} Tiles nach Erkennung, hex_size={self.hex_map.hex_size:.1f}")
        
        if tile_count > 0:
            # Automatisch Grid vervollständigen wenn zu wenige erkannt
            # (Erkannte Hexagone dienen als Referenz für Größe/Position)
            result = messagebox.askyesnocancel(
                "Grid vervollständigen?",
                f"{tile_count} Hexagone erkannt (Größe: {self.hex_map.hex_size:.0f}px).\n\n"
                f"Ja = Grid automatisch ausfüllen\n"
                f"Nein = Nur erkannte Hexagone behalten\n"
                f"Abbrechen = Hex-Größe manuell eingeben"
            )
            
            if result is True:  # Ja
                self._complete_grid_from_detected()
            elif result is None:  # Abbrechen -> manuell
                self._manual_hex_size_dialog()
        elif not success:
            # Fallback: Frage nach manueller Grid-Erstellung
            if messagebox.askyesno("Keine Hexagone erkannt",
                                   "Keine Hexagone erkannt.\n"
                                   "Möchtest du ein Grid manuell erstellen?"):
                self._create_grid_dialog()
        
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
            self.hex_map.image_width = self.bg_image.width
            self.hex_map.image_height = self.bg_image.height
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
        filepath = filedialog.asksaveasfilename(
            title="Hexagon-Karte speichern",
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            self.hex_map.save(filepath)
            messagebox.showinfo("Gespeichert", f"Karte gespeichert:\n{filepath}")
    
    def _load_map(self):
        filepath = filedialog.askopenfilename(
            title="Hexagon-Karte laden",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            self.hex_map = HexagonMap.load(filepath)
            self.title(f"🔷 Hexagon-Editor: {self.hex_map.name}")
            self._update_stats()
            self._redraw()
    
    def _on_click(self, event):
        x, y = self._canvas_to_map(event.x, event.y)
        tile = self.hex_map.get_tile_at_pixel(x, y)
        
        if tile:
            if self.current_tool == "select":
                self.selected_tile = (tile.q, tile.r)
                self._update_info(tile)
                
            elif self.current_tool == "terrain":
                tile.terrain = self.current_terrain
                
            elif self.current_tool == "weather":
                tile.local_weather = self.current_weather
                tile.weather_intensity = 1.0
                
            elif self.current_tool == "event":
                # Zeige Event-Dialog
                dialog = EventEditDialog(self, None)
                self.wait_window(dialog)
                if dialog.result:
                    tile.events.append(dialog.result)
            
            self._redraw()
        else:
            # Kein Tile getroffen
            if self.current_tool == "draw_hex":
                # Starte neues Hex-Zeichnen: Setze Zentrum
                self.draw_hex_start = (x, y)
                self.template_hex_size = 0
                self.preview_hex = None
            else:
                # Pan starten
                self.drag_start = (event.x, event.y)
    
    def _on_drag(self, event):
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
    
    def _on_release(self, event):
        # Hex-Zeichenmodus: Beende und zeige Grid-Dialog
        if self.current_tool == "draw_hex" and self.draw_hex_start and self.template_hex_size > 10:
            self._show_fill_grid_dialog()
        
        self.drag_start = None
        self.draw_hex_start = None
        self.preview_hex = None
    
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
        """Rechtsklick: Properties Dialog"""
        x, y = self._canvas_to_map(event.x, event.y)
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
        info = f"Position: ({tile.q}, {tile.r})\n"
        info += f"Terrain: {terrain.display_name}\n"
        if tile.terrain_name:
            info += f"Name: {tile.terrain_name}\n"
        info += f"Schwierigkeit: {tile.total_difficulty}\n"
        
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
    
    def _redraw(self):
        """Zeichne Canvas neu"""
        self.canvas.delete("all")
        
        # Hintergrundbild
        if self.bg_image:
            # Skaliere und positioniere Bild
            w = int(self.bg_image.width * self.zoom)
            h = int(self.bg_image.height * self.zoom)
            scaled = self.bg_image.resize((w, h), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(scaled)
            self.canvas.create_image(self.offset_x, self.offset_y, 
                                    image=self.bg_photo, anchor=tk.NW)
        
        # Zeichne Hexagone
        for (q, r), tile in self.hex_map.tiles.items():
            self._draw_hexagon(tile)
        
        # Zeichne Auswahl
        if self.selected_tile and self.selected_tile in self.hex_map.tiles:
            tile = self.hex_map.tiles[self.selected_tile]
            self._draw_hexagon_outline(tile, "#ffff00", 3)
        
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
    
    def _draw_hexagon(self, tile: HexTile):
        """Zeichne ein einzelnes Hexagon"""
        vertices = self.hex_map._get_hex_vertices(tile.center_x, tile.center_y)
        canvas_vertices = [self._map_to_canvas(x, y) for x, y in vertices]
        
        # Farbe
        color = tile.display_color
        
        # Zeichne gefülltes Hexagon (halbtransparent wenn Hintergrundbild)
        if self.bg_image:
            # Nur Umriss wenn Hintergrund vorhanden
            self.canvas.create_polygon(canvas_vertices, outline=color, width=2, fill="")
        else:
            self.canvas.create_polygon(canvas_vertices, fill=color, outline="#333333", width=1)
        
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
    
    def _draw_hexagon_outline(self, tile: HexTile, color: str, width: int):
        """Zeichne Hexagon-Umriss (für Auswahl)"""
        vertices = self.hex_map._get_hex_vertices(tile.center_x, tile.center_y)
        canvas_vertices = [self._map_to_canvas(x, y) for x, y in vertices]
        self.canvas.create_polygon(canvas_vertices, outline=color, width=width, fill="")


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
