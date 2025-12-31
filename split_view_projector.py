"""
Split-View Projektor für "Der Eine Ring" VTT
=============================================

Erweiterter Projektor mit Multi-Screen-Unterstützung:
- Split-View: Teilt den Bildschirm in X Bereiche für verschiedene Teams
- Jedes Team sieht nur seinen Bereich (gezoomt auf Teamposition)
- Minimap zeigt Gesamtübersicht mit Boss-Positionen
- Spieler-Tokens mit Teamfarben und Namen
- Webcam-basiertes Figuren-Tracking

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import Canvas, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
import json
import random
import math
import os
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass

# Import Player System
from player_system import (
    PlayerManager, PlayerDefinition, TeamDefinition,
    PlayerPlacement, SplitViewManager, WebcamFigureTracker,
    TEAM_COLORS
)

# Import Boss System
from boss_system import BossManager, BossDefinition


@dataclass
class ViewportConfig:
    """Konfiguration für einen einzelnen Viewport im Split-Screen"""
    screen_index: int  # 0, 1, 2... für welcher Screen
    x_offset: int  # Pixel-Offset von links
    width: int  # Breite in Pixeln
    height: int  # Höhe in Pixeln
    
    # Karten-Zentrum (Hexagon-Koordinaten)
    center_q: int = 0
    center_r: int = 0
    
    # Zoom-Level (2.0 = 200%)
    zoom: float = 2.0
    
    # Team-Zuordnung
    team_id: Optional[str] = None
    team_color: str = "#4488FF"
    
    # Spawn-Area Extent (Bounding Box der Team-Spieler für Follow-Logik)
    extent_min_q: int = 0
    extent_min_r: int = 0
    extent_max_q: int = 0
    extent_max_r: int = 0


class SplitViewProjector(tk.Toplevel):
    """
    Projektor-Fenster mit Split-View-Unterstützung.
    
    Kann den Bildschirm in mehrere Bereiche aufteilen,
    wobei jedes Team seinen eigenen gezoomten Ausschnitt sieht.
    """
    
    def __init__(self, parent, map_data=None, player_manager=None, 
                 boss_manager=None, num_screens: int = 2, svg_path=None):
        super().__init__(parent)
        
        self.title("Der Eine Ring - Split-View Projektor")
        self.configure(bg="#0a0a0a")
        
        # Vollbild-Setup
        self.attributes('-fullscreen', False)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 90% Bildschirmgröße
        window_width = int(screen_width * 0.95)
        window_height = int(screen_height * 0.9)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Key Bindings
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.bind('<F5>', lambda e: self.refresh_view())
        
        # Map-Daten
        self.map_data = map_data or {"width": 50, "height": 50, "tiles": {}}
        self.svg_path = svg_path
        
        # Manager
        self.player_manager = player_manager or PlayerManager()
        self.boss_manager = boss_manager or BossManager()
        
        # === FOG OF WAR ===
        # Set von enthüllten Hexagonen: {"q,r", "q,r", ...}
        self.fog_revealed: Set[str] = set()
        self.fog_enabled = True  # Fog standardmäßig aktiv
        
        # Projektor-Kompatibilität (für GM-Panel)
        self.is_split_view = True  # Marker für Split-View-Modus
        self.is_svg_mode = bool(svg_path)
        
        # Split-View Konfiguration
        self.num_screens = num_screens
        self.split_enabled = num_screens > 1
        self.viewports: List[ViewportConfig] = []
        
        # Zoom-Level für Split-View (200% Standard)
        self.split_zoom = 2.0
        
        # Minimap-Konfiguration
        self.minimap_enabled = True
        self.minimap_size = 200  # Pixel
        self.minimap_position = "top-right"  # top-right, top-left
        
        # Enthüllte Bosse
        self.discovered_bosses: Set[Tuple[int, int]] = set()
        
        # === GM-PANEL KOMPATIBILITÄT ===
        # Boss-Hexagon-Enthüllung (für Mittelklick im GM-Panel)
        self.revealed_boss_hexes: Dict[Tuple[int, int], bool] = {}  # {(q,r): has_boss}
        self.revealed_bosses: Dict[Tuple[int, int], Any] = {}  # {(q,r): BossDefinition}
        
        # Canvas und Rendering
        self.main_canvas = None
        self.map_photo = None  # PhotoImage Referenz
        
        # Hexagon-Parameter
        self.hex_size = self.map_data.get("hex_size", 40)
        # Orientation normalisieren: "pointy-top" -> "pointy", "flat-top" -> "flat"
        raw_orientation = self.map_data.get("orientation", "pointy")
        if "pointy" in raw_orientation.lower():
            self.orientation = "pointy"
        elif "flat" in raw_orientation.lower():
            self.orientation = "flat"
        else:
            self.orientation = "pointy"
        print(f"🔷 Hex-Parameter: size={self.hex_size}, orientation={self.orientation}")
        
        # Tiles normalisieren (kann Liste oder Dict sein)
        self._normalize_tiles()
        
        # Hintergrundbild laden (SVG oder PNG)
        self.background_image = None
        self._load_background_image()
        
        # Animation
        self.animation_running = False
        self.animation_id = None
        
        # Webcam-Tracker
        self.webcam_tracker = None
        self.webcam_enabled = False
        
        # Auto-Follow (Viewport folgt Spielerbewegung)
        self.auto_follow_enabled = True
        
        # === DRAG & DROP FÜR SPIELER-TOKENS ===
        self.dragging_player = None  # Aktuell gezogener Spieler
        self.drag_start_pos = None   # Start-Position für Drag
        self.drag_viewport = None    # Viewport in dem gedraggt wird
        self.drag_current_pos = None # Aktuelle Drag-Position für Live-Vorschau
        self.drag_target_hex = None  # Ziel-Hex für Hervorhebung
        
        # === EXIT-PUNKTE SYSTEM ===
        # Zufällig ausgewählte Exit-Punkte aus Spawn-Hexagonen (2-4 Stück)
        self.exit_hexagons: List[Tuple[int, int]] = []
        self._generate_exit_points()
        
        # UI Setup
        self._setup_ui()
    
    # === PROJEKTOR-KOMPATIBILITÄT (für GM-Panel) ===
    
    def render_map(self):
        """Alias für render_all - Kompatibilität mit GM-Panel"""
        self.render_all()
    
    def reveal_fog_at_hex(self, q: int, r: int, radius: int = 0):
        """
        Enthüllt Fog-of-War an einer Hexagon-Position.
        
        Args:
            q, r: Hexagon-Koordinaten
            radius: Anzahl Hexagone drumherum die auch enthüllt werden
        """
        # Zentrum enthüllen
        self.fog_revealed.add(f"{q},{r}")
        
        # Radius enthüllen (Hexagon-Nachbarn)
        if radius > 0:
            neighbors = self._get_hex_neighbors_in_radius(q, r, radius)
            for nq, nr in neighbors:
                self.fog_revealed.add(f"{nq},{nr}")
        
        print(f"🌫️ Fog enthüllt bei ({q},{r}) + Radius {radius} = {len(self.fog_revealed)} Hexe sichtbar")
        self.render_all()
    
    def reveal_fog_area(self, hex_list: List[Tuple[int, int]]):
        """Enthüllt mehrere Hexagone auf einmal"""
        for q, r in hex_list:
            self.fog_revealed.add(f"{q},{r}")
        self.render_all()
    
    def hide_fog_at_hex(self, q: int, r: int):
        """Verbirgt ein Hexagon wieder im Fog"""
        key = f"{q},{r}"
        if key in self.fog_revealed:
            self.fog_revealed.remove(key)
        self.render_all()
    
    def reveal_all_fog(self):
        """Enthüllt die gesamte Karte (GM-Modus)"""
        tiles = self._get_tiles_dict()
        for coord_key in tiles.keys():
            self.fog_revealed.add(coord_key)
        self.fog_enabled = False
        print(f"🌫️ Gesamte Karte enthüllt: {len(self.fog_revealed)} Hexe")
        self.render_all()
    
    def reset_fog(self):
        """Setzt Fog-of-War zurück - alles verborgen"""
        self.fog_revealed.clear()
        self.fog_enabled = True
        print("🌫️ Fog-of-War zurückgesetzt")
        self.render_all()
    
    def is_hex_revealed(self, q: int, r: int) -> bool:
        """Prüft ob ein Hexagon enthüllt ist"""
        if not self.fog_enabled:
            return True
        return f"{q},{r}" in self.fog_revealed
    
    def _get_hex_neighbors_in_radius(self, q: int, r: int, radius: int) -> List[Tuple[int, int]]:
        """Gibt alle Hexagone im Radius zurück (Axial-Koordinaten)"""
        neighbors = []
        for dq in range(-radius, radius + 1):
            for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
                if dq != 0 or dr != 0:  # Nicht das Zentrum
                    neighbors.append((q + dq, r + dr))
        return neighbors
    
    def _normalize_tiles(self):
        """
        Normalisiert das Tiles-Format.
        Tiles kann als Dict oder Liste vorliegen - wir konvertieren alles zu Dict.
        """
        tiles = self.map_data.get("tiles", {})
        
        if isinstance(tiles, list):
            # Liste zu Dict konvertieren
            tiles_dict = {}
            for tile in tiles:
                if isinstance(tile, dict):
                    q = tile.get("q", tile.get("hex_q", 0))
                    r = tile.get("r", tile.get("hex_r", 0))
                    coord_key = f"{q},{r}"
                    # center_x/center_y berechnen falls nicht vorhanden
                    if "center_x" not in tile:
                        tile["center_x"], tile["center_y"] = self._hex_to_pixel(q, r)
                    tiles_dict[coord_key] = tile
            self.map_data["tiles"] = tiles_dict
            print(f"📋 Tiles von Liste zu Dict konvertiert: {len(tiles_dict)} Tiles")
        elif not isinstance(tiles, dict):
            # Fallback: Leeres Dict
            self.map_data["tiles"] = {}
            print("⚠️ Ungültiges Tiles-Format - verwende leeres Dict")
    
    def _get_tiles_dict(self) -> Dict:
        """
        Gibt Tiles immer als Dict zurück.
        Sichere Hilfsmethode für alle Stellen die tiles.items() nutzen.
        """
        tiles = self.map_data.get("tiles", {})
        if isinstance(tiles, dict):
            return tiles
        elif isinstance(tiles, list):
            # Nochmal normalisieren falls nötig
            self._normalize_tiles()
            return self.map_data.get("tiles", {})
        return {}
    
    def _load_background_image(self):
        """Lädt das Hintergrundbild (SVG oder PNG) für die Karte"""
        import os
        
        # Mögliche Bildquellen prüfen
        image_path = None
        
        # 1. svg_source aus map_data
        if self.map_data.get("svg_source"):
            image_path = self.map_data["svg_source"]
        # 2. svg_path Parameter
        elif self.svg_path:
            image_path = self.svg_path
        # 3. background_image_path aus map_data
        elif self.map_data.get("background_image_path"):
            image_path = self.map_data["background_image_path"]
        
        if not image_path:
            print("📷 Kein Hintergrundbild gefunden - nur Hexagone werden gerendert")
            return
        
        # Prüfe ob Datei existiert
        if not os.path.exists(image_path):
            print(f"⚠️ Hintergrundbild nicht gefunden: {image_path}")
            return
        
        try:
            if image_path.lower().endswith('.svg'):
                # SVG laden - versuche cairosvg oder konvertiere zu PNG
                self._load_svg_background(image_path)
            else:
                # PNG/JPG direkt laden
                self.background_image = Image.open(image_path).convert('RGBA')
                print(f"✅ Hintergrundbild geladen: {image_path} ({self.background_image.width}x{self.background_image.height})")
        except Exception as e:
            print(f"⚠️ Fehler beim Laden des Hintergrundbilds: {e}")
            self.background_image = None
    
    def _load_svg_background(self, svg_path: str):
        """Lädt eine SVG-Datei als Hintergrundbild"""
        import io
        
        try:
            # Versuche cairosvg
            import cairosvg
            
            # Zielgröße aus map_data oder Standard
            target_width = self.map_data.get("image_width", 2000)
            target_height = self.map_data.get("image_height", 2000)
            
            # SVG zu PNG konvertieren
            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=target_width,
                output_height=target_height
            )
            
            self.background_image = Image.open(io.BytesIO(png_data)).convert('RGBA')
            print(f"✅ SVG-Hintergrund geladen: {svg_path} ({self.background_image.width}x{self.background_image.height})")
            
        except ImportError:
            print("⚠️ cairosvg nicht installiert - SVG-Hintergrund kann nicht geladen werden")
            print("   Installation: pip install cairosvg")
            # Fallback: Versuche mit Pillow (unterstützt keine SVG direkt)
            self.background_image = None
        except Exception as e:
            print(f"⚠️ SVG-Lade-Fehler: {e}")
            self.background_image = None
    
    def _render_background_in_viewport(self, img: Image.Image, viewport: ViewportConfig):
        """
        Rendert den sichtbaren Ausschnitt des Hintergrundbilds in den Viewport.
        Berücksichtigt Zoom und Zentrierung.
        """
        if not self.background_image:
            return
        
        # Viewport-Zentrum in Pixel-Koordinaten der Karte
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        # Sichtbarer Bereich in Karten-Koordinaten (vor Zoom)
        half_w = viewport.width / (2 * viewport.zoom)
        half_h = viewport.height / (2 * viewport.zoom)
        
        # Crop-Box im Hintergrundbild
        src_left = int(center_px - half_w)
        src_top = int(center_py - half_h)
        src_right = int(center_px + half_w)
        src_bottom = int(center_py + half_h)
        
        # Begrenze auf Bildgrenzen
        bg_w, bg_h = self.background_image.size
        
        # Berechne welcher Teil des Hintergrunds sichtbar ist
        crop_left = max(0, src_left)
        crop_top = max(0, src_top)
        crop_right = min(bg_w, src_right)
        crop_bottom = min(bg_h, src_bottom)
        
        # Ist überhaupt etwas sichtbar?
        if crop_left >= crop_right or crop_top >= crop_bottom:
            return
        
        # Ausschnitt aus Hintergrundbild
        try:
            cropped = self.background_image.crop((crop_left, crop_top, crop_right, crop_bottom))
            
            # Zielgröße im Viewport berechnen (mit Zoom)
            target_w = int((crop_right - crop_left) * viewport.zoom)
            target_h = int((crop_bottom - crop_top) * viewport.zoom)
            
            if target_w > 0 and target_h > 0:
                # Skalieren
                scaled = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                # Position im Viewport berechnen
                # Offset für den Fall dass der Crop-Bereich nicht am Rand des sichtbaren Bereichs beginnt
                paste_x = int((crop_left - src_left) * viewport.zoom)
                paste_y = int((crop_top - src_top) * viewport.zoom)
                
                # Ins Viewport-Bild einfügen
                img.paste(scaled, (paste_x, paste_y))
        except Exception as e:
            print(f"⚠️ Hintergrund-Render-Fehler: {e}")
    
    def _setup_ui(self):
        """Erstellt die UI-Elemente"""
        # Control Bar oben
        self.control_bar = tk.Frame(self, bg="#1a1a2e", height=40)
        self.control_bar.pack(side=tk.TOP, fill=tk.X)
        self.control_bar.pack_propagate(False)
        
        # Buttons
        btn_style = {"bg": "#16213e", "fg": "white", "relief": tk.FLAT, "padx": 10}
        
        tk.Button(self.control_bar, text="🔄 Refresh (F5)", command=self.refresh_view,
                  **btn_style).pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(self.control_bar, text="📺 Fullscreen (F11)", command=self.toggle_fullscreen,
                  **btn_style).pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(self.control_bar, text="🎮 GM-Übersicht", command=self._open_gm_overview,
                  bg="#e94560", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Split-View Toggle
        self.split_var = tk.BooleanVar(value=self.split_enabled)
        tk.Checkbutton(self.control_bar, text="🔲 Split-View", variable=self.split_var,
                       command=self._toggle_split_view, bg="#1a1a2e", fg="white",
                       selectcolor="#0f3460", activebackground="#1a1a2e").pack(side=tk.LEFT, padx=10)
        
        # Screen-Anzahl
        tk.Label(self.control_bar, text="Screens:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT)
        self.screen_spinbox = tk.Spinbox(self.control_bar, from_=1, to=4, width=3,
                                         command=self._on_screen_count_changed)
        self.screen_spinbox.delete(0, tk.END)
        self.screen_spinbox.insert(0, str(self.num_screens))
        self.screen_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Team-Zuordnung Button
        tk.Button(self.control_bar, text="👥 Teams zuordnen", command=self._open_team_assignment,
                  bg="#16213e", fg="white", relief=tk.FLAT, padx=8).pack(side=tk.LEFT, padx=5)
        
        # Minimap Toggle
        self.minimap_var = tk.BooleanVar(value=self.minimap_enabled)
        tk.Checkbutton(self.control_bar, text="🗺️ Minimap", variable=self.minimap_var,
                       command=self._toggle_minimap, bg="#1a1a2e", fg="white",
                       selectcolor="#0f3460", activebackground="#1a1a2e").pack(side=tk.LEFT, padx=10)
        
        # Webcam Toggle
        self.webcam_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.control_bar, text="📷 Webcam", variable=self.webcam_var,
                       command=self._toggle_webcam, bg="#1a1a2e", fg="white",
                       selectcolor="#0f3460", activebackground="#1a1a2e").pack(side=tk.LEFT, padx=10)
        
        # Webcam Setup Button
        tk.Button(self.control_bar, text="⚙️ Kamera", command=self._open_webcam_setup,
                  bg="#16213e", fg="white", relief=tk.FLAT, padx=5).pack(side=tk.LEFT, padx=2)
        
        # Auto-Follow Toggle
        self.auto_follow_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.control_bar, text="🎯 Auto-Follow", variable=self.auto_follow_var,
                       command=self._toggle_auto_follow, bg="#1a1a2e", fg="white",
                       selectcolor="#0f3460", activebackground="#1a1a2e").pack(side=tk.LEFT, padx=10)
        
        # Zoom-Anzeige
        self.zoom_label = tk.Label(self.control_bar, text=f"Zoom: {int(self.split_zoom * 100)}%",
                                   bg="#1a1a2e", fg="#e94560", font=("Arial", 10, "bold"))
        self.zoom_label.pack(side=tk.RIGHT, padx=10)
        
        # Zoom-Slider
        self.zoom_slider = tk.Scale(self.control_bar, from_=100, to=400, orient=tk.HORIZONTAL,
                                    command=self._on_zoom_changed, bg="#1a1a2e", fg="white",
                                    highlightthickness=0, length=150, showvalue=False)
        self.zoom_slider.set(int(self.split_zoom * 100))
        self.zoom_slider.pack(side=tk.RIGHT, padx=5)
        
        # Main Canvas
        self.main_canvas = tk.Canvas(self, bg="#0a0a0a", highlightthickness=0)
        self.main_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind resize
        self.main_canvas.bind('<Configure>', self._on_resize)
        
        # Mouse Events für Drag & Drop und Interaktion
        self.main_canvas.bind('<Button-1>', self._on_click)
        self.main_canvas.bind('<B1-Motion>', self._on_drag)
        self.main_canvas.bind('<ButtonRelease-1>', self._on_drag_end)
        self.main_canvas.bind('<Motion>', self._on_mouse_move)
    
    def _setup_viewports(self):
        """Richtet die Viewports basierend auf Teams ein"""
        self.viewports.clear()
        
        canvas_width = self.main_canvas.winfo_width() or 1280
        canvas_height = self.main_canvas.winfo_height() or 720
        
        # Spawn-Hexagone finden für Zentrierung
        spawn_hexes = self._get_spawn_hexagons()
        
        if not self.split_enabled or self.num_screens <= 1:
            # Einzelner Viewport - zentriert auf erstes Spawn-Hex oder Kartenmitte
            center_q, center_r = (0, 0)
            if spawn_hexes:
                center_q, center_r = spawn_hexes[0]
            else:
                # Kartenmitte berechnen
                center_q, center_r = self._get_map_center()
            
            viewport = ViewportConfig(
                screen_index=0,
                x_offset=0,
                width=canvas_width,
                height=canvas_height,
                zoom=1.0,
                center_q=center_q,
                center_r=center_r
            )
            self.viewports.append(viewport)
            return
        
        # Multi-Screen Setup
        screen_width = canvas_width // self.num_screens
        teams = list(self.player_manager.teams.values())
        
        for i in range(self.num_screens):
            team = teams[i] if i < len(teams) else None
            
            # Viewport erstellen
            viewport = ViewportConfig(
                screen_index=i,
                x_offset=i * screen_width,
                width=screen_width,
                height=canvas_height,
                zoom=self.split_zoom,
                team_id=team.id if team else None,
                team_color=team.color if team else "#888888"
            )
            
            # Team-Spawn-Extent berechnen
            if team:
                self._calculate_team_spawn_extent(viewport, team.id)
            elif i < len(spawn_hexes):
                # Einzelnes Spawn-Hex: Extent = dieses Hex + Umgebung
                sq, sr = spawn_hexes[i]
                viewport.center_q = sq
                viewport.center_r = sr
                # Kleiner Extent um das Spawn-Hex
                viewport.extent_min_q = sq - 3
                viewport.extent_max_q = sq + 3
                viewport.extent_min_r = sr - 3
                viewport.extent_max_r = sr + 3
            else:
                # Fallback: Kartenmitte
                viewport.center_q, viewport.center_r = self._get_map_center()
            
            self.viewports.append(viewport)
        
        print(f"📺 {len(self.viewports)} Viewports erstellt")
    
    def _get_spawn_hexagons(self) -> List[Tuple[int, int]]:
        """Findet alle Spawn-Hexagone auf der Karte"""
        tiles = self._get_tiles_dict()
        spawn_hexes = []
        
        for coord_key, tile_data in tiles.items():
            if isinstance(tile_data, dict) and tile_data.get("is_spawn_hex", False):
                try:
                    parts = coord_key.split(',')
                    q, r = int(parts[0]), int(parts[1])
                    spawn_hexes.append((q, r))
                except:
                    pass
        
        return spawn_hexes
    
    def _generate_exit_points(self):
        """
        Generiert zufällige Exit-Punkte aus den Spawn-Hexagonen.
        Wählt 2-4 Spawn-Hexagone als Exit-Punkte aus.
        """
        spawn_hexes = self._get_spawn_hexagons()
        
        if not spawn_hexes:
            print("⚠️ Keine Spawn-Hexagone für Exit-Punkte vorhanden")
            self.exit_hexagons = []
            return
        
        # Bestimme Anzahl der Exit-Punkte (2-4, aber max. Anzahl der Spawn-Hexagone)
        num_exits = min(random.randint(2, 4), len(spawn_hexes))
        
        # Zufällige Auswahl
        self.exit_hexagons = random.sample(spawn_hexes, num_exits)
        
        print(f"🚪 {len(self.exit_hexagons)} Exit-Punkte generiert: {self.exit_hexagons}")
    
    def regenerate_exit_points(self):
        """Generiert neue Exit-Punkte (kann vom GM aufgerufen werden)"""
        self._generate_exit_points()
        self.render_all()
    
    def is_exit_hex(self, q: int, r: int) -> bool:
        """Prüft ob ein Hexagon ein Exit-Punkt ist"""
        return (q, r) in self.exit_hexagons
    
    def _get_map_center(self) -> Tuple[int, int]:
        """Berechnet das Zentrum der Karte"""
        tiles = self._get_tiles_dict()
        if not tiles:
            return (0, 0)
        
        sum_q, sum_r, count = 0, 0, 0
        for coord_key in tiles.keys():
            try:
                parts = coord_key.split(',')
                q, r = int(parts[0]), int(parts[1])
                sum_q += q
                sum_r += r
                count += 1
            except:
                pass
        
        if count > 0:
            return (sum_q // count, sum_r // count)
        return (0, 0)
    
    def _open_gm_overview(self):
        """Öffnet das GM-Übersichtsfenster mit der kompletten Karte"""
        gm_window = GMOverviewWindow(
            self,
            map_data=self.map_data,
            player_manager=self.player_manager,
            boss_manager=self.boss_manager,
            split_view_projector=self
        )
    
    def toggle_fullscreen(self):
        """Wechselt zwischen Vollbild und Fenster"""
        current = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current)
        if not current:
            # Vollbild aktiviert - Control-Bar ausblenden
            self.control_bar.pack_forget()
        else:
            # Fenster-Modus - Control-Bar zeigen
            self.control_bar.pack(side=tk.TOP, fill=tk.X, before=self.main_canvas)
    
    def _toggle_split_view(self):
        """Aktiviert/Deaktiviert Split-View"""
        self.split_enabled = self.split_var.get()
        self._setup_viewports()
        self.render_all()
    
    def _toggle_minimap(self):
        """Aktiviert/Deaktiviert Minimap"""
        self.minimap_enabled = self.minimap_var.get()
        self.render_all()
    
    def _toggle_webcam(self):
        """Aktiviert/Deaktiviert Webcam-Tracking"""
        if self.webcam_var.get():
            self._start_webcam()
        else:
            self._stop_webcam()
    
    def _toggle_auto_follow(self):
        """Aktiviert/Deaktiviert Auto-Follow (Viewport folgt Team-Bewegung)"""
        self.auto_follow_enabled = self.auto_follow_var.get()
        print(f"🎯 Auto-Follow: {'aktiviert' if self.auto_follow_enabled else 'deaktiviert'}")
    
    def _open_webcam_setup(self):
        """Öffnet den Webcam-Setup-Dialog"""
        dialog = WebcamSetupDialog(self, self.webcam_tracker, self.player_manager)
        self.wait_window(dialog)
        
        if dialog.result:
            self.webcam_tracker = dialog.result
            print("✅ Webcam-Einstellungen übernommen")
    
    def _start_webcam(self):
        """Startet Webcam-Tracking"""
        if self.webcam_tracker is None:
            self.webcam_tracker = WebcamFigureTracker(self.player_manager)
        
        # Kamera-Index aus Tracker oder Standard
        camera_index = getattr(self.webcam_tracker, 'camera_index', 0)
        self.webcam_tracker.start_tracking(camera_index)
        self.webcam_enabled = True
        
        # Tracking-Loop starten
        self._webcam_update_loop()
    
    def _stop_webcam(self):
        """Stoppt Webcam-Tracking"""
        if self.webcam_tracker:
            self.webcam_tracker.stop_tracking()
        self.webcam_enabled = False
    
    def _webcam_update_loop(self):
        """Update-Loop für Webcam-Tracking"""
        if not self.webcam_enabled or not self.webcam_tracker:
            return
        
        # Figuren erkennen und Positionen aktualisieren
        detected = self.webcam_tracker.detect_figures()
        
        if detected and getattr(self, 'auto_follow_enabled', True):
            # Viewports aktualisieren wenn Spieler sich bewegt haben (Auto-Follow)
            for player_id, (new_q, new_r) in detected.items():
                player = self.player_manager.get_player(player_id)
                if player and player.team_id:
                    # Viewport-Zentrum auf Team-Position aktualisieren
                    for viewport in self.viewports:
                        if viewport.team_id == player.team_id:
                            # Sanftes Following - Viewport bewegt sich zum Spieler
                            self._update_viewport_follow(viewport, new_q, new_r)
            
            self.render_all()
        
        # Nächster Update in 100ms
        self.after(100, self._webcam_update_loop)
    
    def _update_viewport_follow(self, viewport: ViewportConfig, target_q: int, target_r: int):
        """
        Aktualisiert das Viewport-Zentrum so dass ALLE Spieler des Teams sichtbar bleiben.
        Berechnet Bounding Box aller Team-Spieler und passt Zoom an wenn nötig.
        """
        if not viewport.team_id:
            # Kein Team - einfach auf Ziel zentrieren
            viewport.center_q = target_q
            viewport.center_r = target_r
            return
        
        # Alle aktiven Spieler des Teams sammeln
        team_players = [
            p for p in self.player_manager.players.values()
            if p.team_id == viewport.team_id and p.is_active
        ]
        
        if not team_players:
            viewport.center_q = target_q
            viewport.center_r = target_r
            return
        
        # Bounding Box aller Team-Spieler berechnen
        min_q = min(p.hex_q for p in team_players)
        max_q = max(p.hex_q for p in team_players)
        min_r = min(p.hex_r for p in team_players)
        max_r = max(p.hex_r for p in team_players)
        
        # Zentrum der Bounding Box
        new_center_q = (min_q + max_q) // 2
        new_center_r = (min_r + max_r) // 2
        
        viewport.center_q = new_center_q
        viewport.center_r = new_center_r
        
        # Extent aktualisieren
        viewport.extent_min_q = min_q
        viewport.extent_max_q = max_q
        viewport.extent_min_r = min_r
        viewport.extent_max_r = max_r
        
        # === ZOOM ANPASSEN UM ALLE SPIELER SICHTBAR ZU HALTEN ===
        # Berechne die benötigte Größe in Pixeln
        extent_width_hex = max_q - min_q + 1
        extent_height_hex = max_r - min_r + 1
        
        if extent_width_hex > 1 or extent_height_hex > 1:
            # Spieler sind verteilt - Zoom anpassen
            # Berechne Pixel-Distanz zwischen den äußeren Spielern
            min_px, min_py = self._hex_to_pixel(min_q, min_r)
            max_px, max_py = self._hex_to_pixel(max_q, max_r)
            
            extent_width_px = abs(max_px - min_px) + self.hex_size * 4  # Margin
            extent_height_px = abs(max_py - min_py) + self.hex_size * 4  # Margin
            
            # Berechne benötigten Zoom um alles anzuzeigen
            zoom_for_width = viewport.width / extent_width_px if extent_width_px > 0 else 2.0
            zoom_for_height = viewport.height / extent_height_px if extent_height_px > 0 else 2.0
            
            needed_zoom = min(zoom_for_width, zoom_for_height)
            
            # Begrenze Zoom auf sinnvollen Bereich (0.5 bis 3.0)
            needed_zoom = max(0.5, min(3.0, needed_zoom))
            
            # Nur anpassen wenn Unterschied signifikant
            if abs(needed_zoom - viewport.zoom) > 0.1:
                viewport.zoom = needed_zoom
                print(f"🔍 Viewport {viewport.screen_index} Zoom angepasst: {needed_zoom:.1f}x")
        
        print(f"🎯 Viewport {viewport.screen_index}: Zentrum ({new_center_q},{new_center_r}), Extent: {extent_width_hex}x{extent_height_hex} Hex, {len(team_players)} Spieler")
    
    def update_player_position(self, player_id: str, new_q: int, new_r: int):
        """
        Öffentliche Methode um Spielerposition zu aktualisieren.
        Wird von externen Systemen aufgerufen (z.B. Drag & Drop auf Karte).
        """
        player = self.player_manager.get_player(player_id)
        if not player:
            return
        
        # Alte Position merken
        old_q, old_r = player.hex_q, player.hex_r
        
        # Position aktualisieren
        self.player_manager.move_player(player_id, new_q, new_r)
        
        # Team-Position aktualisieren wenn in Team
        if player.team_id:
            team = self.player_manager.get_team(player.team_id)
            if team:
                team.hex_q = new_q
                team.hex_r = new_r
        
        # Auto-Follow wenn aktiviert
        if getattr(self, 'auto_follow_enabled', True) and player.team_id:
            for viewport in self.viewports:
                if viewport.team_id == player.team_id:
                    self._update_viewport_follow(viewport, new_q, new_r)
        
        self.render_all()
        print(f"🚶 Spieler {player.name} bewegt: ({old_q},{old_r}) -> ({new_q},{new_r})")
    
    def _on_screen_count_changed(self):
        """Callback wenn Screen-Anzahl geändert wird"""
        try:
            self.num_screens = int(self.screen_spinbox.get())
            self._setup_viewports()
            self.render_all()
        except ValueError:
            pass
    
    def _open_team_assignment(self):
        """Öffnet Dialog zur Team-Zuordnung pro Screen"""
        dialog = TeamAssignmentDialog(self, self.player_manager, self.viewports)
        self.wait_window(dialog)
        
        if dialog.result:
            # Aktualisiere Viewports mit neuen Team-Zuordnungen
            for i, team_id in enumerate(dialog.result):
                if i < len(self.viewports):
                    self.viewports[i].team_id = team_id
                    if team_id:
                        team = self.player_manager.get_team(team_id)
                        if team:
                            self.viewports[i].team_color = team.color
                            # Spawn-Area für dieses Team berechnen
                            self._calculate_team_spawn_extent(self.viewports[i], team_id)
            self.render_all()
    
    def _calculate_team_spawn_extent(self, viewport: ViewportConfig, team_id: str):
        """Berechnet die Spawn-Area basierend auf Spieler-Positionen des Teams"""
        
        # WICHTIG: Nutze NUR player.team_id als Quelle (nicht member_ids!)
        team_players = [
            p for p in self.player_manager.players.values()
            if p.team_id == team_id and p.is_active
        ]
        
        if team_players:
            # Bounding Box der Spieler-Positionen
            min_q = min(p.hex_q for p in team_players)
            max_q = max(p.hex_q for p in team_players)
            min_r = min(p.hex_r for p in team_players)
            max_r = max(p.hex_r for p in team_players)
            
            viewport.extent_min_q = min_q
            viewport.extent_max_q = max_q
            viewport.extent_min_r = min_r
            viewport.extent_max_r = max_r
            
            viewport.center_q = (min_q + max_q) // 2
            viewport.center_r = (min_r + max_r) // 2
            
            print(f"📐 Team {team_id}: {len(team_players)} Spieler, Zentrum: ({viewport.center_q},{viewport.center_r})")
            return
        
        # Fallback: Spawn-Hexagone verwenden
        spawn_hexes = self._get_spawn_hexagons()
        if spawn_hexes and viewport.screen_index < len(spawn_hexes):
            # Jeder Viewport bekommt ein anderes Spawn-Hex
            sq, sr = spawn_hexes[viewport.screen_index]
            viewport.center_q = sq
            viewport.center_r = sr
            viewport.extent_min_q = sq
            viewport.extent_max_q = sq
            viewport.extent_min_r = sr
            viewport.extent_max_r = sr
            print(f"📐 Team {team_id}: Spawn-Hex ({sq},{sr})")
    
    def _get_spawn_hexagons_for_team(self, team_id: str) -> List[Tuple[int, int]]:
        """Findet Spawn-Hexagone die einem bestimmten Team zugeordnet sind"""
        tiles = self._get_tiles_dict()
        spawn_hexes = []
        
        for coord_key, tile_data in tiles.items():
            if isinstance(tile_data, dict) and tile_data.get("is_spawn_hex", False):
                # Prüfe ob Team-ID gesetzt ist
                tile_team = tile_data.get("spawn_team_id", tile_data.get("team_id", None))
                if tile_team == team_id or tile_team is None:  # None = allgemeine Spawn-Hexe
                    try:
                        parts = coord_key.split(',')
                        q, r = int(parts[0]), int(parts[1])
                        spawn_hexes.append((q, r))
                    except:
                        pass
        
        return spawn_hexes
    
    def _on_zoom_changed(self, value):
        """Callback wenn Zoom geändert wird"""
        self.split_zoom = float(value) / 100.0
        self.zoom_label.config(text=f"Zoom: {int(self.split_zoom * 100)}%")
        
        for viewport in self.viewports:
            if self.split_enabled:
                viewport.zoom = self.split_zoom
        
        self.render_all()
    
    def _on_resize(self, event):
        """Callback bei Fenster-Resize"""
        self._setup_viewports()
        self.render_all()
    
    def _on_click(self, event):
        """Mouse-Click Handler - startet Drag wenn auf Spieler-Token geklickt"""
        # Finde welcher Viewport geklickt wurde
        for viewport in self.viewports:
            if viewport.x_offset <= event.x < viewport.x_offset + viewport.width:
                hex_q, hex_r = self._screen_to_hex(event.x, event.y, viewport)
                
                # Prüfe ob ein Spieler-Token an dieser Position ist
                clicked_player = self._get_player_at_screen_pos(event.x, event.y, viewport)
                
                if clicked_player:
                    # Prüfe ob Spieler zu diesem Viewport/Team gehört (nur eigene Spieler bewegen)
                    if clicked_player.team_id == viewport.team_id:
                        self.dragging_player = clicked_player
                        self.drag_start_pos = (event.x, event.y)
                        self.drag_viewport = viewport
                        print(f"🎯 Spieler '{clicked_player.name}' ausgewählt zum Bewegen")
                        return
                
                print(f"🖱️ Viewport {viewport.screen_index}: Hex ({hex_q}, {hex_r})")
                
                # Prüfe ob Boss an Position
                self._check_boss_discovery(hex_q, hex_r)
                break
    
    def _on_drag(self, event):
        """Mouse-Drag Handler - zeigt Live-Vorschau des gedraggten Spielers"""
        if not self.dragging_player or not self.drag_viewport:
            return
        
        viewport = self.drag_viewport
        
        # Prüfe ob noch im Viewport
        if not (viewport.x_offset <= event.x < viewport.x_offset + viewport.width):
            return
        
        # Speichere aktuelle Drag-Position für Rendering
        self.drag_current_pos = (event.x, event.y)
        self.drag_target_hex = self._screen_to_hex(event.x, event.y, viewport)
        
        # Re-Render mit Ghost-Token und Ziel-Hex-Hervorhebung
        self.render_all()
    
    def _on_drag_end(self, event):
        """Mouse-Drag Ende - setzt Spieler auf neue Position"""
        if not self.dragging_player or not self.drag_viewport:
            self.dragging_player = None
            self.drag_start_pos = None
            self.drag_viewport = None
            self.drag_current_pos = None
            self.drag_target_hex = None
            return
        
        viewport = self.drag_viewport
        player = self.dragging_player
        
        # Prüfe ob noch im gleichen Viewport
        if not (viewport.x_offset <= event.x < viewport.x_offset + viewport.width):
            print("⚠️ Spieler außerhalb des Viewports losgelassen - Bewegung abgebrochen")
            self.dragging_player = None
            self.drag_start_pos = None
            self.drag_viewport = None
            self.drag_current_pos = None
            self.drag_target_hex = None
            self.render_all()
            return
        
        # Berechne neue Hex-Position
        new_q, new_r = self._screen_to_hex(event.x, event.y, viewport)
        
        # Prüfe ob Hex gültig ist (existiert auf der Karte)
        tiles = self._get_tiles_dict()
        coord_key = f"{new_q},{new_r}"
        if coord_key not in tiles:
            print(f"⚠️ Hex ({new_q},{new_r}) existiert nicht auf der Karte")
            self.dragging_player = None
            self.drag_start_pos = None
            self.drag_viewport = None
            self.drag_current_pos = None
            self.drag_target_hex = None
            self.render_all()
            return
        
        # Prüfe ob Hex bereits von anderem Spieler belegt ist
        for other_player in self.player_manager.players.values():
            if other_player.id != player.id and other_player.is_active:
                if other_player.hex_q == new_q and other_player.hex_r == new_r:
                    print(f"⚠️ Hex ({new_q},{new_r}) ist bereits von '{other_player.name}' belegt!")
                    self.dragging_player = None
                    self.drag_start_pos = None
                    self.drag_viewport = None
                    self.drag_current_pos = None
                    self.drag_target_hex = None
                    self.render_all()
                    return
        
        # Bewegung durchführen
        old_q, old_r = player.hex_q, player.hex_r
        player.hex_q = new_q
        player.hex_r = new_r
        
        print(f"✅ '{player.name}' bewegt: ({old_q},{old_r}) → ({new_q},{new_r})")
        
        # Fog-of-War für neue Position enthüllen
        if self.fog_enabled:
            self.reveal_fog_at_hex(new_q, new_r, radius=2)
        
        # Auto-Follow: Viewport-Zentrum aktualisieren wenn aktiviert
        if self.auto_follow_enabled:
            self._update_viewport_follow(viewport, new_q, new_r)
        
        # Cleanup
        self.dragging_player = None
        self.drag_start_pos = None
        self.drag_viewport = None
        self.drag_current_pos = None
        self.drag_target_hex = None
        
        # Neu rendern
        self.render_all()
    
    def _get_player_at_screen_pos(self, screen_x: int, screen_y: int, viewport: ViewportConfig):
        """
        Findet einen Spieler an der angegebenen Screen-Position.
        Berücksichtigt Token-Größe und Offset für überlappende Spieler.
        Gibt nur Spieler des eigenen Teams zurück!
        """
        if not self.player_manager.players:
            return None
        
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        # Nur Spieler des Viewport-Teams sammeln
        team_players = [
            p for p in self.player_manager.players.values()
            if p.is_active and p.team_id == viewport.team_id
        ]
        
        if not team_players:
            return None
        
        # Sortiere Spieler nach ID für konsistente Reihenfolge
        team_players.sort(key=lambda p: p.id)
        
        # Sammel alle Spieler mit gleichem Hex für Offset-Berechnung
        hex_player_count = {}
        for p in team_players:
            key = (p.hex_q, p.hex_r)
            hex_player_count[key] = hex_player_count.get(key, 0) + 1
        
        # Zähle Spieler am gleichen Hex für Offset
        hex_player_index = {}
        
        best_distance = float('inf')
        best_player = None
        
        for player in team_players:
            # Berechne Offset für überlappende Spieler
            hex_key = (player.hex_q, player.hex_r)
            if hex_key not in hex_player_index:
                hex_player_index[hex_key] = 0
            idx = hex_player_index[hex_key]
            hex_player_index[hex_key] += 1
            
            count = hex_player_count.get(hex_key, 1)
            offset_x, offset_y = self._calculate_token_offset(idx, count, viewport.zoom)
            
            # Player-Position in Pixeln
            player_px, player_py = self._hex_to_pixel(player.hex_q, player.hex_r)
            
            # Transformiere zu Viewport-Koordinaten
            vx = viewport.x_offset + viewport.width / 2 + (player_px - center_px) * viewport.zoom + offset_x
            vy = viewport.height / 2 + (player_py - center_py) * viewport.zoom + offset_y - 10
            
            # Token-Größe für Hitbox
            token_size = int(player.token_size * viewport.zoom * 0.8)
            half_size = token_size // 2
            
            # Prüfe ob Klick innerhalb des Tokens
            if (vx - half_size <= screen_x <= vx + half_size and
                vy - half_size <= screen_y <= vy + half_size):
                # Finde nächsten Spieler zum Klickpunkt
                dist = ((screen_x - vx) ** 2 + (screen_y - vy) ** 2) ** 0.5
                if dist < best_distance:
                    best_distance = dist
                    best_player = player
        
        return best_player
    
    def _calculate_token_offset(self, index: int, total: int, zoom: float) -> Tuple[float, float]:
        """
        Berechnet einen Offset für überlappende Spieler-Tokens am gleichen Hex.
        Verteilt Tokens in einem Kreis um das Hex-Zentrum.
        """
        if total <= 1:
            return (0, 0)
        
        # Kreisförmige Anordnung
        import math
        angle = (2 * math.pi * index) / total
        radius = 15 * zoom  # Abstand vom Zentrum
        
        offset_x = radius * math.cos(angle)
        offset_y = radius * math.sin(angle)
        
        return (offset_x, offset_y)
    
    def _on_mouse_move(self, event):
        """Mouse-Move Handler"""
        pass  # Für Hover-Effekte
    
    def refresh_view(self):
        """Aktualisiert die gesamte Ansicht"""
        self._setup_viewports()
        self.render_all()
    
    # =========================================================
    # KOORDINATEN-KONVERTIERUNG
    # =========================================================
    
    def _hex_to_pixel(self, q: int, r: int) -> Tuple[float, float]:
        """
        Konvertiert Hex-Koordinaten zu Pixel-Koordinaten.
        Verwendet gespeicherte center_x/center_y aus Tile-Daten wenn vorhanden,
        sonst berechnet aus hex_size und orientation.
        """
        # Versuche gespeicherte Koordinaten aus Tiles zu verwenden
        tiles = self._get_tiles_dict()
        coord_key = f"{q},{r}"
        
        if coord_key in tiles:
            tile = tiles[coord_key]
            if isinstance(tile, dict) and "center_x" in tile and "center_y" in tile:
                return (tile["center_x"], tile["center_y"])
        
        # Fallback: Berechne aus Hex-Koordinaten
        if self.orientation == "pointy":
            x = self.hex_size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
            y = self.hex_size * (3 / 2 * r)
        else:
            x = self.hex_size * (3 / 2 * q)
            y = self.hex_size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
        return (x, y)
    
    def _pixel_to_hex(self, x: float, y: float) -> Tuple[int, int]:
        """Konvertiert Pixel zu Hex-Koordinaten (gerundet)"""
        if self.orientation == "pointy":
            q = (math.sqrt(3) / 3 * x - 1 / 3 * y) / self.hex_size
            r = (2 / 3 * y) / self.hex_size
        else:
            q = (2 / 3 * x) / self.hex_size
            r = (-1 / 3 * x + math.sqrt(3) / 3 * y) / self.hex_size
        return (round(q), round(r))
    
    def _screen_to_hex(self, screen_x: int, screen_y: int, viewport: ViewportConfig) -> Tuple[int, int]:
        """Konvertiert Screen-Position zu Hex-Koordinaten für einen Viewport"""
        # Relative Position im Viewport
        rel_x = screen_x - viewport.x_offset
        rel_y = screen_y
        
        # Viewport-Zentrum in Pixeln
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        # Map-Position in Pixel-Koordinaten berechnen
        map_x = center_px + (rel_x - viewport.width / 2) / viewport.zoom
        map_y = center_py + (rel_y - viewport.height / 2) / viewport.zoom
        
        # Finde das nächste Hex anhand der Pixel-Koordinaten
        return self._find_nearest_hex(map_x, map_y)
    
    def _find_nearest_hex(self, pixel_x: float, pixel_y: float) -> Tuple[int, int]:
        """
        Findet das nächste Hexagon zu einer Pixel-Position.
        Verwendet die gespeicherten center_x/center_y aus den Tile-Daten.
        """
        tiles = self._get_tiles_dict()
        
        if not tiles:
            # Fallback zur mathematischen Berechnung
            return self._pixel_to_hex(pixel_x, pixel_y)
        
        best_hex = (0, 0)
        best_distance = float('inf')
        
        for coord_key, tile_data in tiles.items():
            if not isinstance(tile_data, dict):
                continue
            
            # Hole Tile-Zentrum
            if "center_x" in tile_data and "center_y" in tile_data:
                cx = tile_data["center_x"]
                cy = tile_data["center_y"]
            else:
                # Berechne aus Koordinaten
                try:
                    parts = coord_key.split(',')
                    q, r = int(parts[0]), int(parts[1])
                    if self.orientation == "pointy":
                        cx = self.hex_size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
                        cy = self.hex_size * (3 / 2 * r)
                    else:
                        cx = self.hex_size * (3 / 2 * q)
                        cy = self.hex_size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
                except:
                    continue
            
            # Distanz berechnen
            dist = ((pixel_x - cx) ** 2 + (pixel_y - cy) ** 2) ** 0.5
            
            if dist < best_distance:
                best_distance = dist
                try:
                    parts = coord_key.split(',')
                    best_hex = (int(parts[0]), int(parts[1]))
                except:
                    pass
        
        return best_hex
    
    # =========================================================
    # BOSS-ENTHÜLLUNG
    # =========================================================
    
    def _check_boss_discovery(self, q: int, r: int):
        """Prüft ob ein Boss an Position enthüllt werden soll"""
        placement = self.boss_manager.get_placement_at_hex(q, r)
        if placement and not placement.revealed:
            boss = self.boss_manager.reveal_boss_at_hex(q, r)
            if boss:
                self.discovered_bosses.add((q, r))
                self.render_all()
                print(f"🐉 BOSS ENTDECKT: {boss.name} bei ({q}, {r})!")
    
    def mark_boss_hex_revealed(self, q: int, r: int, has_boss: bool):
        """
        Markiert ein Boss-Hexagon als enthüllt (Kompatibilität mit GM-Panel).
        Wird vom Mittelklick im GM-Panel aufgerufen.
        """
        self.revealed_boss_hexes[(q, r)] = has_boss
        
        # Boss tatsächlich enthüllen
        if has_boss:
            placement = self.boss_manager.get_placement_at_hex(q, r)
            if placement and not placement.revealed:
                boss = self.boss_manager.reveal_boss_at_hex(q, r)
                if boss:
                    self.discovered_bosses.add((q, r))
                    self.revealed_bosses[(q, r)] = boss
                    print(f"🐉 BOSS VOM GM ENTHÜLLT: {boss.name} bei ({q}, {r})!")
        
        # Ansicht aktualisieren
        self.render_all()
    
    def show_victory_screen(self, boss):
        """
        Zeigt einen Sieges-Bildschirm wenn ein Boss besiegt wurde.
        Für Split View: Zeigt Overlay auf allen Viewports.
        """
        if not self.main_canvas:
            return
        
        try:
            canvas_width = self.main_canvas.winfo_width()
            canvas_height = self.main_canvas.winfo_height()
            
            if canvas_width < 100 or canvas_height < 100:
                return
            
            # Erstelle Sieges-Overlay
            victory_img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 180))
            draw = ImageDraw.Draw(victory_img)
            
            # Goldener Rahmen in der Mitte
            box_width = min(600, canvas_width - 100)
            box_height = min(300, canvas_height - 100)
            box_x = (canvas_width - box_width) // 2
            box_y = (canvas_height - box_height) // 2
            
            # Goldener Hintergrund
            draw.rounded_rectangle(
                (box_x, box_y, box_x + box_width, box_y + box_height),
                radius=20, fill=(40, 40, 20, 230), outline=(255, 215, 0, 255), width=5
            )
            
            # Schriften
            try:
                font_crown = ImageFont.truetype("arial.ttf", 60)
                font_title = ImageFont.truetype("arial.ttf", 36)
                font_name = ImageFont.truetype("arial.ttf", 24)
                font_hint = ImageFont.truetype("arial.ttf", 14)
            except:
                font_crown = ImageFont.load_default()
                font_title = font_crown
                font_name = font_crown
                font_hint = font_crown
            
            # Krone und SIEG!
            draw.text((canvas_width // 2 - 30, box_y + 20), "👑", font=font_crown)
            draw.text((canvas_width // 2 - 60, box_y + 90), "SIEG!", fill=(255, 215, 0), font=font_title)
            
            # Boss-Name
            boss_text = f"{boss.name} wurde besiegt!"
            bbox = draw.textbbox((0, 0), boss_text, font=font_name)
            text_width = bbox[2] - bbox[0]
            draw.text(((canvas_width - text_width) // 2, box_y + 150), boss_text, 
                     fill=(200, 200, 200), font=font_name)
            
            # Bounty-Hinweis
            bounty_hint = "💰 Bounty vergeben im Boss-Tab!"
            hint_bbox = draw.textbbox((0, 0), bounty_hint, font=font_hint)
            hint_width = hint_bbox[2] - hint_bbox[0]
            draw.text(((canvas_width - hint_width) // 2, box_y + 200), bounty_hint, 
                     fill=(255, 215, 0), font=font_hint)
            
            # Klicken-Hinweis
            click_text = "Klicken zum Fortfahren..."
            click_bbox = draw.textbbox((0, 0), click_text, font=font_hint)
            click_width = click_bbox[2] - click_bbox[0]
            draw.text(((canvas_width - click_width) // 2, box_y + box_height - 30), click_text, 
                     fill=(150, 150, 150), font=font_hint)
            
            # Overlay anzeigen
            self.victory_photo = ImageTk.PhotoImage(victory_img)
            self.victory_overlay_id = self.main_canvas.create_image(
                0, 0, image=self.victory_photo, anchor=tk.NW, tags="victory_overlay"
            )
            
            # Klick-Event zum Schließen
            def close_victory(event=None):
                self.main_canvas.delete("victory_overlay")
                if hasattr(self, 'victory_overlay_id'):
                    del self.victory_overlay_id
                self.render_all()
            
            self.main_canvas.bind("<Button-1>", close_victory, add="+")
            
            # Auto-Close nach 5 Sekunden
            self.after(5000, close_victory)
            
        except Exception as e:
            print(f"⚠️ Victory-Screen-Fehler: {e}")
    
    # =========================================================
    # RENDERING
    # =========================================================
    
    def render_map(self):
        """
        Kompatibilitätsmethode für GM-Panel.
        Ruft render_all() auf für konsistentes Verhalten.
        """
        self.render_all()
    
    def render_all(self):
        """Rendert die gesamte Ansicht"""
        if not self.main_canvas:
            return
        
        canvas_width = self.main_canvas.winfo_width()
        canvas_height = self.main_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        # Hauptbild erstellen
        main_image = Image.new('RGBA', (canvas_width, canvas_height), (10, 10, 10, 255))
        
        if self.split_enabled and len(self.viewports) > 1:
            # Split-View rendern
            for viewport in self.viewports:
                viewport_image = self._render_viewport(viewport)
                main_image.paste(viewport_image, (viewport.x_offset, 0))
                
                # Trennlinie zwischen Viewports
                if viewport.screen_index < len(self.viewports) - 1:
                    draw = ImageDraw.Draw(main_image)
                    line_x = viewport.x_offset + viewport.width
                    draw.line([(line_x, 0), (line_x, canvas_height)], 
                              fill=(100, 100, 100), width=3)
        else:
            # Single-View
            if self.viewports:
                viewport_image = self._render_viewport(self.viewports[0])
                main_image = viewport_image
        
        # Minimap auf alle Viewports rendern - jede Minimap zeigt NUR das eigene Team
        if self.minimap_enabled:
            for viewport in self.viewports:
                # Jeder Viewport bekommt seine eigene Minimap mit nur seinem Team
                minimap = self._render_minimap(for_viewport=viewport)
                self._overlay_minimap(main_image, minimap, viewport)
        
        # Zu PhotoImage konvertieren und anzeigen
        self.map_photo = ImageTk.PhotoImage(main_image)
        self.main_canvas.delete("all")
        self.main_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
    
    def _render_viewport(self, viewport: ViewportConfig) -> Image.Image:
        """Rendert einen einzelnen Viewport"""
        # Viewport-Image erstellen
        img = Image.new('RGBA', (viewport.width, viewport.height), (20, 20, 30, 255))
        
        # === HINTERGRUNDBILD RENDERN ===
        if self.background_image:
            self._render_background_in_viewport(img, viewport)
        
        draw = ImageDraw.Draw(img)
        
        tiles = self._get_tiles_dict()
        
        # Berechne sichtbaren Bereich
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        # Viewport-Grenzen in Map-Koordinaten
        half_w = viewport.width / (2 * viewport.zoom)
        half_h = viewport.height / (2 * viewport.zoom)
        
        # Zeichne Hexagon-Overlays (Spawn, Boss, etc.) - nicht die Grundfarbe wenn Hintergrund vorhanden
        has_background = self.background_image is not None
        
        for coord_key, tile_data in tiles.items():
            if not isinstance(tile_data, dict):
                continue
            
            try:
                parts = coord_key.split(',')
                q, r = int(parts[0]), int(parts[1])
            except:
                continue
            
            # Hole Tile-Zentrum - berechne falls nicht vorhanden
            if "center_x" in tile_data and "center_y" in tile_data:
                tile_cx = tile_data.get("center_x", 0)
                tile_cy = tile_data.get("center_y", 0)
            else:
                # Berechne aus Hex-Koordinaten
                tile_cx, tile_cy = self._hex_to_pixel(q, r)
            
            # Prüfe ob im Viewport sichtbar
            if (tile_cx < center_px - half_w - self.hex_size or
                tile_cx > center_px + half_w + self.hex_size or
                tile_cy < center_py - half_h - self.hex_size or
                tile_cy > center_py + half_h + self.hex_size):
                continue
            
            # Transformiere zu Viewport-Koordinaten
            vx = viewport.width / 2 + (tile_cx - center_px) * viewport.zoom
            vy = viewport.height / 2 + (tile_cy - center_py) * viewport.zoom
            
            # FOG OF WAR: Prüfe ob Hexagon enthüllt ist
            is_revealed = self.is_hex_revealed(q, r)
            
            # Zeichne Hexagon (mit Fog-Status)
            self._draw_hexagon(draw, vx, vy, viewport.zoom, tile_data, viewport, is_revealed, q, r)
        
        # === DRAG-ZIEL-HERVORHEBUNG (NUR Ziel-Hexagon, kein Ghost-Token) ===
        if (self.dragging_player and self.drag_viewport == viewport and 
            self.drag_target_hex and self.drag_current_pos):
            self._draw_drag_highlight(img, draw, viewport)
        
        # Spieler-Tokens zeichnen
        self._draw_players_in_viewport(img, viewport)
        
        # Ghost-Token entfernt - nur Ziel-Hexagon wird hervorgehoben
        
        # Boss-Overlays zeichnen
        self._draw_bosses_in_viewport(img, viewport)
        
        # Team-Info-Header - IMMER zeichnen (auch ohne Team)
        if viewport.team_id:
            team = self.player_manager.get_team(viewport.team_id)
            if team:
                self._draw_team_header(img, team, viewport)
        else:
            # Fallback: Zeige Viewport-Nummer
            self._draw_viewport_header(img, viewport)
        
        return img
    
    def _draw_hexagon(self, draw: ImageDraw.Draw, cx: float, cy: float, 
                      zoom: float, tile_data: Dict, viewport: ViewportConfig,
                      is_revealed: bool = True, q: int = 0, r: int = 0):
        """Zeichnet ein einzelnes Hexagon mit Fog-of-War Unterstützung"""
        scaled_size = self.hex_size * zoom * 0.95
        
        # Hexagon-Punkte berechnen
        points = []
        for i in range(6):
            if self.orientation == "pointy":
                angle = math.pi / 3 * i - math.pi / 6
            else:
                angle = math.pi / 3 * i
            px = cx + scaled_size * math.cos(angle)
            py = cy + scaled_size * math.sin(angle)
            points.append((px, py))
        
        # FOG OF WAR: Wenn nicht enthüllt, dunkel zeichnen
        if not is_revealed and self.fog_enabled:
            # Fog-Hexagon: Dunkles Grau/Schwarz
            draw.polygon(points, fill=(15, 15, 20, 255), outline=(30, 30, 40, 255))
            return
        
        # Wenn Hintergrundbild vorhanden ist, nur Umrisse und Overlays zeichnen
        has_background = self.background_image is not None
        
        if not has_background:
            # Kein Hintergrund - zeichne fill_color
            fill_color = tile_data.get("fill_color", "#444444")
            try:
                if fill_color.startswith('#'):
                    r_c = int(fill_color[1:3], 16)
                    g_c = int(fill_color[3:5], 16)
                    b_c = int(fill_color[5:7], 16)
                    fill = (r_c, g_c, b_c, 200)
                else:
                    fill = (68, 68, 68, 200)
            except:
                fill = (68, 68, 68, 200)
            
            # Hexagon mit Füllfarbe zeichnen
            draw.polygon(points, fill=fill, outline=(100, 100, 100, 255))
        else:
            # Hintergrund vorhanden - nur leichter Umriss
            draw.polygon(points, fill=None, outline=(50, 50, 50, 100))
        
        # Spezielle Markierungen
        if tile_data.get("is_boss_hex", False):
            # Prüfe ob dieses Boss-Hex bereits enthüllt wurde
            is_boss_hex_revealed = (q, r) in self.revealed_boss_hexes
            has_boss_here = self.revealed_boss_hexes.get((q, r), False) if is_boss_hex_revealed else None
            
            if is_boss_hex_revealed:
                if has_boss_here:
                    # Boss gefunden: Rotes Overlay mit Warnung
                    draw.polygon(points, fill=(255, 0, 0, 80), outline=(255, 0, 0, 255))
                # else: Kein Boss hier - KEINE Markierung, normale Textur sichtbar
            else:
                # Noch nicht enthüllt: Orange Overlay (Gefahr/unbekannt)
                draw.polygon(points, fill=(255, 140, 0, 100), outline=(255, 100, 0, 255))
        
        if tile_data.get("is_spawn_hex", False):
            # Spawn-Hexagon: Grünes Overlay
            draw.polygon(points, fill=(0, 255, 0, 80), outline=(0, 200, 0, 255))
        
        # === EXIT-PUNKTE MARKIERUNG ===
        if self.is_exit_hex(q, r):
            # Exit-Punkt: Auffälliges Cyan/Türkis mit Ausrufezeichen-Symbol
            draw.polygon(points, fill=(0, 255, 255, 120), outline=(0, 200, 255, 255))
            
            # Dickerer Rand für bessere Sichtbarkeit
            for i in range(6):
                next_i = (i + 1) % 6
                draw.line([points[i], points[next_i]], fill=(255, 255, 0, 255), width=3)
            
            # "EXIT" oder Tür-Symbol im Zentrum
            try:
                font_size = max(10, int(scaled_size * 0.35))
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Text "EXIT" zentriert
                text = "🚪"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = cx - text_width // 2
                text_y = cy - text_height // 2
                
                # Hintergrund für bessere Lesbarkeit
                draw.ellipse([cx - scaled_size * 0.4, cy - scaled_size * 0.4, 
                             cx + scaled_size * 0.4, cy + scaled_size * 0.4], 
                            fill=(0, 100, 100, 200), outline=(255, 255, 0, 255))
                
                # Text zeichnen
                draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
            except Exception as e:
                pass  # Bei Fehlern still ignorieren
    
    def _draw_players_in_viewport(self, img: Image.Image, viewport: ViewportConfig):
        """Zeichnet Spieler-Tokens im Viewport - mit Offset für überlappende Spieler"""
        if not self.player_manager.players:
            return
        
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        # Hole Team-Objekt für member_ids Check
        viewport_team = self.player_manager.get_team(viewport.team_id) if viewport.team_id else None
        viewport_member_ids = viewport_team.member_ids if viewport_team else []
        
        # Sammel alle sichtbaren Spieler mit gleichem Hex für Offset-Berechnung
        visible_players = []
        
        # Viewport-Center für Sichtbarkeits-Check
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        for player in self.player_manager.players.values():
            if not player.is_active:
                continue
            
            # Prüfe ob Spieler zu diesem Viewport gehört
            is_own_team = (player.team_id == viewport.team_id) or (player.id in viewport_member_ids)
            
            # Prüfe Sichtbarkeit für dieses Team
            if viewport.team_id and not is_own_team:
                # OPTION 1: Andere Teams sichtbar wenn nah genug (basierend auf Sichtradius)
                can_see_by_radius = self.player_manager.can_team_see_position(
                    viewport.team_id, player.hex_q, player.hex_r)
                
                # OPTION 2: Andere Teams sichtbar wenn im Viewport-Extent
                player_px, player_py = self._hex_to_pixel(player.hex_q, player.hex_r)
                vx = viewport.width / 2 + (player_px - center_px) * viewport.zoom
                vy = viewport.height / 2 + (player_py - center_py) * viewport.zoom
                in_viewport_extent = (0 <= vx <= viewport.width and 0 <= vy <= viewport.height)
                
                # Zeige Spieler wenn EINER der Checks zutrifft
                if not (can_see_by_radius or in_viewport_extent):
                    continue
            
            visible_players.append(player)
        
        # WICHTIG: Sortiere nach ID für konsistente Reihenfolge (muss mit _get_player_at_screen_pos übereinstimmen!)
        visible_players.sort(key=lambda p: p.id)
        
        # Zähle Spieler pro Hex für Offset
        hex_player_count = {}
        for p in visible_players:
            key = (p.hex_q, p.hex_r)
            hex_player_count[key] = hex_player_count.get(key, 0) + 1
        
        # Index pro Hex für Offset
        hex_player_index = {}
        
        for player in visible_players:
            # Berechne Offset für überlappende Spieler
            hex_key = (player.hex_q, player.hex_r)
            if hex_key not in hex_player_index:
                hex_player_index[hex_key] = 0
            idx = hex_player_index[hex_key]
            hex_player_index[hex_key] += 1
            
            count = hex_player_count.get(hex_key, 1)
            offset_x, offset_y = self._calculate_token_offset(idx, count, viewport.zoom)
            
            # Player-Position in Pixeln
            player_px, player_py = self._hex_to_pixel(player.hex_q, player.hex_r)
            
            # Transformiere zu Viewport-Koordinaten (mit Offset)
            vx = viewport.width / 2 + (player_px - center_px) * viewport.zoom + offset_x
            vy = viewport.height / 2 + (player_py - center_py) * viewport.zoom + offset_y
            
            # Prüfe ob im Viewport
            if not (0 <= vx <= viewport.width and 0 <= vy <= viewport.height):
                continue
            
            # Token rendern
            token_size = int(player.token_size * viewport.zoom * 0.8)
            token = self.player_manager.render_player_token(player, size=token_size)
            
            # Position für Paste
            paste_x = int(vx - token_size // 2)
            paste_y = int(vy - token_size // 2 - 10)  # Leicht nach oben
            
            # Paste mit Alpha
            try:
                img.paste(token, (paste_x, paste_y), token)
            except Exception as e:
                print(f"Token-Paste-Fehler: {e}")
    
    def _draw_bosses_in_viewport(self, img: Image.Image, viewport: ViewportConfig):
        """Zeichnet Boss-Overlays im Viewport"""
        if not self.boss_manager.placements:
            return
        
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        for placement in self.boss_manager.placements:
            if not placement.revealed:
                continue
            
            boss = self.boss_manager.get_boss(placement.boss_id)
            if not boss:
                continue
            
            # Boss-Position
            boss_px, boss_py = self._hex_to_pixel(placement.hex_q, placement.hex_r)
            
            # Transformiere zu Viewport-Koordinaten
            vx = viewport.width / 2 + (boss_px - center_px) * viewport.zoom
            vy = viewport.height / 2 + (boss_py - center_py) * viewport.zoom
            
            # Prüfe ob im Viewport
            if not (0 <= vx <= viewport.width and 0 <= vy <= viewport.height):
                continue
            
            # Boss-Overlay rendern
            overlay_size = int(100 * viewport.zoom)
            overlay = self.boss_manager.render_boss_overlay(boss, width=overlay_size, height=overlay_size + 40)
            
            # Position für Paste
            paste_x = int(vx - overlay_size // 2)
            paste_y = int(vy - overlay_size - 20)
            
            # Paste mit Alpha
            try:
                img.paste(overlay, (paste_x, paste_y), overlay)
            except:
                pass
    
    def _draw_drag_highlight(self, img: Image.Image, draw: ImageDraw.ImageDraw, viewport: ViewportConfig):
        """Zeichnet den Spieler-Token an der aktuellen Mausposition während des Dragging"""
        if not self.dragging_player or not self.drag_current_pos:
            return
        
        player = self.dragging_player
        if not player:
            return
        
        # Drag-Position - viewport.x_offset abziehen für korrekte Position im Viewport-Bild
        drag_x = self.drag_current_pos[0] - viewport.x_offset
        drag_y = self.drag_current_pos[1]
        
        # Token rendern
        token_size = int(player.token_size * viewport.zoom * 0.8)
        token = self.player_manager.render_player_token(player, size=token_size)
        
        # Token semi-transparent machen für Drag-Effekt
        if token.mode == 'RGBA':
            r, g, b, a = token.split()
            # Alpha auf 70% setzen für sichtbaren aber erkennbaren Drag-Effekt
            a = a.point(lambda x: int(x * 0.7))
            token = Image.merge('RGBA', (r, g, b, a))
        
        # Position für Paste (zentriert auf Maus)
        paste_x = int(drag_x - token_size // 2)
        paste_y = int(drag_y - token_size // 2)
        
        # Paste mit Alpha
        try:
            img.paste(token, (paste_x, paste_y), token)
        except Exception as e:
            pass  # Fehler still ignorieren
    
    def _draw_ghost_token(self, img: Image.Image, viewport: ViewportConfig):
        """Zeichnet semi-transparentes Ghost-Token an aktueller Drag-Position"""
        if not self.dragging_player or not self.drag_current_pos:
            return
        
        # dragging_player ist bereits das PlayerDefinition-Objekt
        player = self.dragging_player
        if not player:
            return
        
        # Drag-Position ist in Viewport-Koordinaten
        drag_x, drag_y = self.drag_current_pos
        
        # Token rendern
        token_size = int(player.token_size * viewport.zoom * 0.8)
        token = self.player_manager.render_player_token(player, size=token_size)
        
        # Token semi-transparent machen
        if token.mode == 'RGBA':
            # Alpha reduzieren für Ghost-Effekt
            r, g, b, a = token.split()
            from PIL import ImageEnhance
            # Alpha auf 50% setzen
            a = a.point(lambda x: int(x * 0.5))
            token = Image.merge('RGBA', (r, g, b, a))
        
        # Position für Paste (zentriert auf Maus)
        paste_x = int(drag_x - token_size // 2)
        paste_y = int(drag_y - token_size // 2)
        
        # Paste mit Alpha
        try:
            img.paste(token, (paste_x, paste_y), token)
        except Exception as e:
            print(f"Ghost-Token-Paste-Fehler: {e}")
    
    def _draw_viewport_header(self, img: Image.Image, viewport: ViewportConfig):
        """Zeichnet Header für Viewport ohne Team-Zuordnung"""
        draw = ImageDraw.Draw(img)
        
        # Hintergrund
        draw.rectangle([(0, 0), (viewport.width, 40)], fill=(0, 0, 0, 180))
        draw.rectangle([(0, 35), (viewport.width, 40)], fill=(100, 100, 100, 255))
        
        # Viewport-Info
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), f"📺 Viewport {viewport.screen_index + 1}", fill=(255, 255, 255), font=font)
        draw.text((viewport.width - 150, 10), f"Zentrum: ({viewport.center_q}, {viewport.center_r})", 
                  fill=(200, 200, 200), font=font)
    
    def _draw_team_header(self, img: Image.Image, team: TeamDefinition, viewport: ViewportConfig):
        """Zeichnet Team-Info am oberen Rand des Viewports"""
        draw = ImageDraw.Draw(img)
        
        # Hintergrund
        draw.rectangle([(0, 0), (viewport.width, 40)], fill=(0, 0, 0, 180))
        
        # Team-Farbe als Akzent
        try:
            color = team.color
            if color.startswith('#'):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
            else:
                r, g, b = 100, 100, 100
        except:
            r, g, b = 100, 100, 100
        
        draw.rectangle([(0, 35), (viewport.width, 40)], fill=(r, g, b, 255))
        
        # Team-Name
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        draw.text((10, 10), f"👥 {team.name}", fill=(255, 255, 255), font=font)
        
        # Mitglieder-Anzahl
        members = self.player_manager.get_team_members(team.id)
        member_text = f"{len(members)} Spieler"
        draw.text((viewport.width - 100, 10), member_text, fill=(200, 200, 200), font=font)
        
        # Drag & Drop Hinweis
        hint_text = "🎯 Klicke & ziehe deine Figur zum Bewegen"
        draw.text((viewport.width // 2 - 100, 12), hint_text, fill=(150, 150, 150), font=font_small)
    
    # =========================================================
    # MINIMAP
    # =========================================================
    
    def _render_minimap(self, for_viewport: ViewportConfig = None) -> Image.Image:
        """
        Rendert die Minimap mit Hintergrundbild, Bossen und Team-Spielern.
        Zeigt NUR das eigene Team (nicht andere Teams!)
        """
        size = self.minimap_size
        minimap = Image.new('RGBA', (size, size), (30, 30, 40, 220))
        
        # Wenn Hintergrundbild vorhanden, als Basis verwenden
        if self.background_image:
            # Hintergrundbild skalieren auf Minimap-Größe
            bg_w, bg_h = self.background_image.size
            scale_factor = min(size / bg_w, size / bg_h) * 0.95
            new_w = int(bg_w * scale_factor)
            new_h = int(bg_h * scale_factor)
            
            if new_w > 0 and new_h > 0:
                scaled_bg = self.background_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                # Zentrieren
                paste_x = (size - new_w) // 2
                paste_y = (size - new_h) // 2
                minimap.paste(scaled_bg, (paste_x, paste_y))
        
        draw = ImageDraw.Draw(minimap)
        
        # Rahmen
        draw.rectangle([(0, 0), (size - 1, size - 1)], outline=(100, 100, 100), width=2)
        
        tiles = self._get_tiles_dict()
        if not tiles:
            return minimap
        
        # Bounding Box der Karte berechnen
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for coord_key, tile_data in tiles.items():
            if isinstance(tile_data, dict):
                cx = tile_data.get("center_x", 0)
                cy = tile_data.get("center_y", 0)
                if cx != 0 or cy != 0:
                    min_x = min(min_x, cx)
                    min_y = min(min_y, cy)
                    max_x = max(max_x, cx)
                    max_y = max(max_y, cy)
        
        if min_x == float('inf'):
            # Fallback: Nutze Bildgröße
            if self.background_image:
                min_x, min_y = 0, 0
                max_x = self.background_image.width
                max_y = self.background_image.height
            else:
                return minimap
        
        # Skalierung berechnen
        map_width = max_x - min_x + self.hex_size * 2
        map_height = max_y - min_y + self.hex_size * 2
        scale = min(size / map_width, size / map_height) * 0.9
        
        offset_x = (size - map_width * scale) / 2 - min_x * scale
        offset_y = (size - map_height * scale) / 2 - min_y * scale
        
        # Boss-Hexagone zeichnen
        # Besiegte Bosse sind für ALLE sichtbar, andere nur wenn vom eigenen Team enthüllt
        own_team_id = for_viewport.team_id if for_viewport else None
        
        for placement in self.boss_manager.placements:
            boss = self.boss_manager.get_boss(placement.boss_id)
            is_defeated = boss and boss.is_defeated
            
            # Besiegte Bosse: Für ALLE auf der Minimap sichtbar!
            # Nicht-besiegte Bosse: Nur wenn enthüllt
            if not is_defeated and not placement.revealed:
                continue  # Versteckte Bosse nicht auf Minimap zeigen
            
            cx, cy = self._hex_to_pixel(placement.hex_q, placement.hex_r)
            
            mx = cx * scale + offset_x
            my = cy * scale + offset_y
            
            # Boss-Marker
            marker_size = 6
            if is_defeated:
                # Besiegter Boss: Grünes X mit Schädel-Symbol - FÜR ALLE SICHTBAR
                marker_size = 8  # Größer für Wichtigkeit
                draw.ellipse([(mx - marker_size, my - marker_size),
                              (mx + marker_size, my + marker_size)],
                             fill=(50, 200, 50), outline=(255, 255, 255), width=2)
                # Schädel-Symbol
                draw.text((mx - 5, my - 5), "☠", fill=(255, 255, 255))
            elif placement.revealed:
                # Enthüllter, aktiver Boss: Rot mit Pulsieren
                draw.ellipse([(mx - marker_size, my - marker_size),
                              (mx + marker_size, my + marker_size)],
                             fill=(255, 0, 0), outline=(255, 255, 255))
        
        # === EXIT-PUNKTE IN MINIMAP ZEICHNEN ===
        for exit_q, exit_r in self.exit_hexagons:
            cx, cy = self._hex_to_pixel(exit_q, exit_r)
            mx = cx * scale + offset_x
            my = cy * scale + offset_y
            
            # Exit-Marker: Cyan Diamant mit gelbem Rand
            marker_size = 7
            exit_points = [
                (mx, my - marker_size),  # Oben
                (mx + marker_size, my),  # Rechts
                (mx, my + marker_size),  # Unten
                (mx - marker_size, my)   # Links
            ]
            draw.polygon(exit_points, fill=(0, 255, 255), outline=(255, 255, 0), width=2)
            
            # Tür-Symbol
            try:
                tiny_font = ImageFont.truetype("arial.ttf", 8)
            except:
                tiny_font = ImageFont.load_default()
            draw.text((mx - 4, my - 4), "🚪", fill=(255, 255, 255), font=tiny_font)
        
        # Hole alle Bounty-Träger (diese sind für ALLE sichtbar)
        bounty_carriers = self.boss_manager.get_all_bounty_carriers()
        
        # NUR Spieler des EIGENEN Teams zeichnen PLUS Bounty-Träger!
        if for_viewport and for_viewport.team_id:
            own_team_id = for_viewport.team_id
            
            for player in self.player_manager.players.values():
                if not player.is_active:
                    continue
                
                # Prüfe ob Spieler gezeigt werden soll:
                # 1. Eigenes Team: IMMER zeigen
                # 2. Bounty-Träger: FÜR ALLE zeigen!
                is_own_team = player.team_id == own_team_id
                has_bounty = player.id in bounty_carriers
                
                if not is_own_team and not has_bounty:
                    continue
                
                cx, cy = self._hex_to_pixel(player.hex_q, player.hex_r)
                mx = cx * scale + offset_x
                my = cy * scale + offset_y
                
                # Spieler-Marker (kleiner Kreis)
                marker_size = 4
                
                # Bounty-Träger bekommen größeren goldenen Marker
                if has_bounty:
                    marker_size = 6
                
                # Spieler-Farbe
                try:
                    color = player.color
                    if color.startswith('#'):
                        r = int(color[1:3], 16)
                        g = int(color[3:5], 16)
                        b = int(color[5:7], 16)
                    else:
                        r, g, b = 100, 200, 255
                except:
                    r, g, b = 100, 200, 255
                
                # Bounty-Träger: Goldener Rand + Pulsieren
                outline_color = (255, 215, 0) if has_bounty else (255, 255, 255)
                outline_width = 2 if has_bounty else 1
                
                draw.ellipse([(mx - marker_size, my - marker_size),
                              (mx + marker_size, my + marker_size)],
                             fill=(r, g, b), outline=outline_color, width=outline_width)
                
                # Bounty-Symbol (💰) über dem Marker
                if has_bounty:
                    try:
                        tiny_font = ImageFont.truetype("arial.ttf", 8)
                    except:
                        tiny_font = ImageFont.load_default()
                    draw.text((mx - 5, my - marker_size - 10), "💰", fill=(255, 215, 0), font=tiny_font)
        
        # Legende
        try:
            legend_font = ImageFont.truetype("arial.ttf", 9)
        except:
            legend_font = ImageFont.load_default()
        
        draw.text((5, size - 50), "🚪 Exit", fill=(0, 255, 255), font=legend_font)
        draw.text((5, size - 38), "🐉 Boss", fill=(255, 140, 0), font=legend_font)
        draw.text((5, size - 25), "☠️ Besiegt", fill=(50, 200, 50), font=legend_font)
        draw.text((5, size - 12), "💰 Bounty", fill=(255, 215, 0), font=legend_font)
        
        return minimap
    
    def _overlay_minimap(self, main_image: Image.Image, minimap: Image.Image, 
                         viewport: ViewportConfig):
        """Überlagert die Minimap auf einen Viewport"""
        margin = 10
        
        if self.minimap_position == "top-right":
            x = viewport.x_offset + viewport.width - self.minimap_size - margin
            y = margin + 45  # Nach Team-Header
        else:  # top-left
            x = viewport.x_offset + margin
            y = margin + 45
        
        main_image.paste(minimap, (x, y), minimap)
    
    # =========================================================
    # SPIELER-MANAGEMENT
    # =========================================================
    
    def distribute_players(self):
        """Verteilt Spieler auf Spawn-Hexagone und Bosse auf Boss-Hexagone"""
        tiles = self._get_tiles_dict()
        spawn_hexes = []
        boss_hexes = []
        
        for coord_key, tile_data in tiles.items():
            if isinstance(tile_data, dict):
                try:
                    parts = coord_key.split(',')
                    q, r = int(parts[0]), int(parts[1])
                    
                    if tile_data.get("is_spawn_hex", False):
                        spawn_hexes.append((q, r))
                    if tile_data.get("is_boss_hex", False):
                        boss_hexes.append((q, r))
                except:
                    pass
        
        # ═══════════════════════════════════════════════════════════
        # BOSS-VERTEILUNG: Verteile definierte Bosse auf Boss-Hexagone
        # ═══════════════════════════════════════════════════════════
        if boss_hexes and self.boss_manager:
            # Prüfe ob bereits Placements existieren
            if not self.boss_manager.placements:
                self.boss_manager.distribute_bosses_randomly(boss_hexes)
            else:
                print(f"✅ {len(self.boss_manager.placements)} Bosse bereits platziert")
        
        if spawn_hexes:
            # Prüfe ob Spieler bereits Teams haben
            players_have_teams = any(
                p.team_id for p in self.player_manager.players.values() if p.is_active
            )
            
            if not players_have_teams:
                # Nur wenn KEINE Teams vorhanden sind, automatisch zuweisen
                self._auto_assign_players_to_teams()
            else:
                print(f"✅ Spieler haben bereits Teams - keine Auto-Zuweisung")
            
            # ═══════════════════════════════════════════════════════════════
            # IMMER NEU VERTEILEN: Teams werden zufällig auf Spawn-Hexe verteilt
            # Jedes Team bekommt ein eigenes Spawn-Hexagon (kein Sharing!)
            # ═══════════════════════════════════════════════════════════════
            import random
            random.shuffle(spawn_hexes)  # Zufällige Reihenfolge
            
            teams = list(self.player_manager.teams.values())
            used_hexes = set()
            
            print(f"🎲 Verteile {len(teams)} Teams auf {len(spawn_hexes)} Spawn-Hexe...")
            
            for i, team in enumerate(teams):
                if i < len(spawn_hexes):
                    spawn_q, spawn_r = spawn_hexes[i]
                    used_hexes.add((spawn_q, spawn_r))
                    
                    # Alle Spieler dieses Teams an diesen Spawn-Punkt setzen
                    team_players = [p for p in self.player_manager.players.values() 
                                   if p.team_id == team.id and p.is_active]
                    
                    for player in team_players:
                        player.hex_q = spawn_q
                        player.hex_r = spawn_r
                        # Aktualisiere auch Placement falls vorhanden
                        for placement in self.player_manager.placements:
                            if placement.player_id == player.id:
                                placement.hex_q = spawn_q
                                placement.hex_r = spawn_r
                                break
                    
                    print(f"   👥 Team '{team.name}' → Spawn ({spawn_q},{spawn_r}) mit {len(team_players)} Spielern")
                else:
                    print(f"   ⚠️ Nicht genug Spawn-Hexe für Team '{team.name}'")
            
            print(f"✅ Teams zufällig verteilt auf {len(used_hexes)} verschiedene Spawn-Punkte")
            
            # WICHTIG: Viewports NACH der Spieler-Verteilung aktualisieren
            self._update_viewport_centers()
            
            # Nochmal Viewports komplett neu einrichten mit korrekten Team-Positionen
            self._setup_viewports()
            
            self.render_all()
    
    def _auto_assign_players_to_teams(self):
        """
        Weist Spieler automatisch Teams zu, wenn sie noch kein Team haben.
        Verteilt Spieler gleichmäßig auf verfügbare Teams.
        """
        teams = list(self.player_manager.teams.values())
        if not teams:
            # Keine Teams vorhanden - erstelle Standard-Teams
            from player_system import TeamDefinition
            team1 = TeamDefinition(name="Team A", color="#4488FF")
            team2 = TeamDefinition(name="Team B", color="#FF4444")
            self.player_manager.add_team(team1)
            self.player_manager.add_team(team2)
            teams = [team1, team2]
            print(f"🎮 Standard-Teams erstellt: {team1.name}, {team2.name}")
        
        # Spieler ohne Team sammeln
        unassigned = [p for p in self.player_manager.players.values() 
                     if not p.team_id and p.is_active]
        
        if not unassigned:
            print("✅ Alle Spieler haben bereits Teams")
            return
        
        # Gleichmäßig auf Teams verteilen
        for i, player in enumerate(unassigned):
            team = teams[i % len(teams)]
            self.player_manager.add_player_to_team(player.id, team.id)
            print(f"👥 Spieler '{player.name}' → Team '{team.name}'")
    
    def _update_viewport_centers(self):
        """Aktualisiert die Viewport-Zentren basierend auf Team-Positionen"""
        teams = list(self.player_manager.teams.values())
        
        for i, viewport in enumerate(self.viewports):
            if i < len(teams):
                team = teams[i]
                viewport.team_id = team.id
                viewport.team_color = team.color
                
                # NUR team_id verwenden (nicht member_ids, da diese inkonsistent sein können)
                team_players = [
                    p for p in self.player_manager.players.values()
                    if p.is_active and p.team_id == team.id
                ]
                
                if team_players:
                    # Zentrum aller Team-Spieler
                    viewport.center_q = sum(p.hex_q for p in team_players) // len(team_players)
                    viewport.center_r = sum(p.hex_r for p in team_players) // len(team_players)
                    print(f"📍 Viewport {i}: Team '{team.name}' mit {len(team_players)} Spielern:")
                    for tp in team_players:
                        print(f"   - {tp.name}: ({tp.hex_q}, {tp.hex_r})")
                    print(f"   → Zentrum: ({viewport.center_q},{viewport.center_r})")
                elif team.hex_q != 0 or team.hex_r != 0:
                    # Fallback: Team-Position aus Team-Objekt
                    viewport.center_q = team.hex_q
                    viewport.center_r = team.hex_r
                    print(f"📍 Viewport {i}: Team '{team.name}' Team-Position: ({viewport.center_q},{viewport.center_r})")


# =========================================================
# GM-ÜBERSICHT FENSTER
# =========================================================

class GMOverviewWindow(tk.Toplevel):
    """
    Separates Fenster für den Spielleiter mit der kompletten Kartenübersicht.
    Ermöglicht das Enthüllen von Bossen und das Verfolgen aller Spieler.
    """
    
    def __init__(self, parent, map_data, player_manager, boss_manager, split_view_projector):
        super().__init__(parent)
        
        self.title("🎮 GM-Übersicht - Komplette Karte")
        self.configure(bg="#0a0a0a")
        
        # Größe: 50% des Bildschirms
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = int(screen_width * 0.5)
        window_height = int(screen_height * 0.6)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Referenzen
        self.map_data = map_data
        self.player_manager = player_manager
        self.boss_manager = boss_manager
        self.split_view_projector = split_view_projector
        
        # Hex-Parameter
        self.hex_size = map_data.get("hex_size", 40)
        self.orientation = map_data.get("orientation", "pointy")
        
        # Zoom und Pan
        self.zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start = None
        
        # Photo-Referenz
        self.map_photo = None
        
        self._setup_ui()
        
        # Initial rendern
        self.after(100, self.render_map)
    
    def _setup_ui(self):
        """Erstellt die UI"""
        # Control Bar
        control_bar = tk.Frame(self, bg="#1a1a2e", height=40)
        control_bar.pack(side=tk.TOP, fill=tk.X)
        control_bar.pack_propagate(False)
        
        btn_style = {"bg": "#16213e", "fg": "white", "relief": tk.FLAT, "padx": 10}
        
        tk.Button(control_bar, text="🔄 Aktualisieren", command=self.render_map,
                  **btn_style).pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(control_bar, text="🎯 Zentrieren", command=self._center_view,
                  **btn_style).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Zoom
        tk.Label(control_bar, text="Zoom:", bg="#1a1a2e", fg="white").pack(side=tk.LEFT, padx=(20, 5))
        
        tk.Button(control_bar, text="➖", command=lambda: self._change_zoom(-0.2),
                  bg="#16213e", fg="white", relief=tk.FLAT, width=3).pack(side=tk.LEFT)
        
        self.zoom_label = tk.Label(control_bar, text="100%", bg="#1a1a2e", fg="#e94560",
                                   font=("Arial", 10, "bold"), width=5)
        self.zoom_label.pack(side=tk.LEFT, padx=5)
        
        tk.Button(control_bar, text="➕", command=lambda: self._change_zoom(0.2),
                  bg="#16213e", fg="white", relief=tk.FLAT, width=3).pack(side=tk.LEFT)
        
        # Info
        tk.Label(control_bar, text="| Klick auf Boss-Hex = Enthüllen | Rechtsklick = Pan",
                 bg="#1a1a2e", fg="#888", font=("Arial", 9)).pack(side=tk.RIGHT, padx=10)
        
        # Canvas
        self.canvas = tk.Canvas(self, bg="#0a0a0a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bindings
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Button-3>', self._on_right_click_start)
        self.canvas.bind('<B3-Motion>', self._on_drag)
        self.canvas.bind('<ButtonRelease-3>', self._on_right_click_end)
        self.canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind('<Configure>', lambda e: self.render_map())
    
    def _change_zoom(self, delta):
        """Ändert den Zoom"""
        self.zoom = max(0.2, min(3.0, self.zoom + delta))
        self.zoom_label.config(text=f"{int(self.zoom * 100)}%")
        self.render_map()
    
    def _center_view(self):
        """Zentriert die Ansicht"""
        self.pan_x = 0
        self.pan_y = 0
        self.render_map()
    
    def _on_click(self, event):
        """Linksklick - Boss enthüllen"""
        # Pixel zu Hex konvertieren
        hex_q, hex_r = self._screen_to_hex(event.x, event.y)
        
        # Prüfe ob Boss an Position
        placement = self.boss_manager.get_placement_at_hex(hex_q, hex_r)
        if placement and not placement.revealed:
            boss = self.boss_manager.reveal_boss_at_hex(hex_q, hex_r)
            if boss:
                print(f"🐉 BOSS ENTHÜLLT: {boss.name} bei ({hex_q}, {hex_r})!")
                self.render_map()
                # Auch Split-View aktualisieren
                if self.split_view_projector:
                    self.split_view_projector.render_all()
    
    def _on_right_click_start(self, event):
        """Rechtsklick Start - Pan beginnen"""
        self.drag_start = (event.x, event.y)
    
    def _on_drag(self, event):
        """Ziehen für Pan"""
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.pan_x += dx
            self.pan_y += dy
            self.drag_start = (event.x, event.y)
            self.render_map()
    
    def _on_right_click_end(self, event):
        """Rechtsklick Ende"""
        self.drag_start = None
    
    def _on_mousewheel(self, event):
        """Mausrad für Zoom"""
        delta = 0.1 if event.delta > 0 else -0.1
        self._change_zoom(delta)
    
    def _hex_to_pixel(self, q: int, r: int) -> Tuple[float, float]:
        """Konvertiert Hex zu Pixel - verwendet gespeicherte center_x/center_y wenn vorhanden"""
        # Versuche gespeicherte Koordinaten aus Tiles
        tiles = self.map_data.get("tiles", {})
        coord_key = f"{q},{r}"
        
        if coord_key in tiles:
            tile = tiles[coord_key]
            if isinstance(tile, dict) and "center_x" in tile and "center_y" in tile:
                return (tile["center_x"], tile["center_y"])
        
        # Fallback: Berechne aus Hex-Koordinaten
        if self.orientation == "pointy":
            x = self.hex_size * (math.sqrt(3) * q + math.sqrt(3) / 2 * r)
            y = self.hex_size * (3 / 2 * r)
        else:
            x = self.hex_size * (3 / 2 * q)
            y = self.hex_size * (math.sqrt(3) / 2 * q + math.sqrt(3) * r)
        return (x, y)
    
    def _screen_to_hex(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """Konvertiert Screen-Koordinaten zu Hex"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Zu Map-Koordinaten
        map_x = (screen_x - canvas_width / 2 - self.pan_x) / self.zoom
        map_y = (screen_y - canvas_height / 2 - self.pan_y) / self.zoom
        
        # Zu Hex
        if self.orientation == "pointy":
            q = (math.sqrt(3) / 3 * map_x - 1 / 3 * map_y) / self.hex_size
            r = (2 / 3 * map_y) / self.hex_size
        else:
            q = (2 / 3 * map_x) / self.hex_size
            r = (-1 / 3 * map_x + math.sqrt(3) / 3 * map_y) / self.hex_size
        
        return (round(q), round(r))
    
    def render_map(self):
        """Rendert die komplette Karte"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        # Bild erstellen
        img = Image.new('RGBA', (canvas_width, canvas_height), (10, 10, 15, 255))
        draw = ImageDraw.Draw(img)
        
        tiles = self.map_data.get("tiles", {})
        if isinstance(tiles, list):
            # Normalisieren
            tiles_dict = {}
            for tile in tiles:
                if isinstance(tile, dict):
                    q = tile.get("q", tile.get("hex_q", 0))
                    r = tile.get("r", tile.get("hex_r", 0))
                    tiles_dict[f"{q},{r}"] = tile
            tiles = tiles_dict
        
        # Alle Hexagone zeichnen
        for coord_key, tile_data in tiles.items():
            if not isinstance(tile_data, dict):
                continue
            
            try:
                parts = coord_key.split(',')
                q, r = int(parts[0]), int(parts[1])
            except:
                continue
            
            # Hex-Zentrum berechnen
            hx, hy = self._hex_to_pixel(q, r)
            
            # Zu Screen-Koordinaten
            sx = canvas_width / 2 + hx * self.zoom + self.pan_x
            sy = canvas_height / 2 + hy * self.zoom + self.pan_y
            
            # Außerhalb des Sichtbereichs?
            if sx < -50 or sx > canvas_width + 50 or sy < -50 or sy > canvas_height + 50:
                continue
            
            # Hexagon zeichnen
            self._draw_hex(draw, sx, sy, tile_data, q, r)
        
        # Spieler zeichnen
        self._draw_players(img)
        
        # Bosse zeichnen
        self._draw_bosses(img)
        
        # Legende
        self._draw_legend(draw, canvas_width, canvas_height)
        
        # Anzeigen
        self.map_photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
    
    def _draw_hex(self, draw, cx, cy, tile_data, q, r):
        """Zeichnet ein Hexagon"""
        scaled_size = self.hex_size * self.zoom * 0.95
        
        # Punkte berechnen
        points = []
        for i in range(6):
            if self.orientation == "pointy":
                angle = math.pi / 3 * i - math.pi / 6
            else:
                angle = math.pi / 3 * i
            px = cx + scaled_size * math.cos(angle)
            py = cy + scaled_size * math.sin(angle)
            points.append((px, py))
        
        # Füllfarbe
        fill_color = tile_data.get("fill_color", "#444444")
        try:
            if fill_color.startswith('#'):
                r_c = int(fill_color[1:3], 16)
                g_c = int(fill_color[3:5], 16)
                b_c = int(fill_color[5:7], 16)
                fill = (r_c, g_c, b_c, 180)
            else:
                fill = (68, 68, 68, 180)
        except:
            fill = (68, 68, 68, 180)
        
        outline_color = (80, 80, 80, 255)
        
        # Spezielle Hexagone
        if tile_data.get("is_boss_hex", False):
            # Boss-Hexagon: Orange Rand
            outline_color = (255, 140, 0, 255)
            fill = (fill[0], fill[1], fill[2], 220)
        
        if tile_data.get("is_spawn_hex", False):
            # Spawn-Hexagon: Grüner Rand
            outline_color = (0, 200, 0, 255)
        
        draw.polygon(points, fill=fill, outline=outline_color)
        
        # === EXIT-PUNKTE MARKIERUNG ===
        if self.split_view_projector and self.split_view_projector.is_exit_hex(q, r):
            # Exit-Punkt: Auffälliges Cyan/Türkis Overlay
            draw.polygon(points, fill=(0, 255, 255, 100), outline=(0, 200, 255, 255))
            
            # Dickerer Rand für bessere Sichtbarkeit (gelb)
            for i in range(6):
                next_i = (i + 1) % 6
                draw.line([points[i], points[next_i]], fill=(255, 255, 0, 255), width=2)
            
            # "EXIT" Symbol im Zentrum
            try:
                font_size = max(8, int(scaled_size * 0.5))
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                text = "🚪"
                draw.text((cx - font_size // 2, cy - font_size // 2), text, fill=(255, 255, 255, 255), font=font)
            except:
                pass
    
    def _draw_players(self, img):
        """Zeichnet Spieler-Positionen"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        draw = ImageDraw.Draw(img)
        
        for team in self.player_manager.teams.values():
            hx, hy = self._hex_to_pixel(team.hex_q, team.hex_r)
            sx = int(canvas_width / 2 + hx * self.zoom + self.pan_x)
            sy = int(canvas_height / 2 + hy * self.zoom + self.pan_y)
            
            # Team-Farbe
            try:
                color = team.color
                if color.startswith('#'):
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                else:
                    r, g, b = 100, 100, 255
            except:
                r, g, b = 100, 100, 255
            
            # Team-Marker (Diamant)
            size = int(12 * self.zoom)
            points = [(sx, sy - size), (sx + size, sy), (sx, sy + size), (sx - size, sy)]
            draw.polygon(points, fill=(r, g, b), outline=(255, 255, 255))
            
            # Team-Name
            try:
                font = ImageFont.truetype("arial.ttf", max(8, int(10 * self.zoom)))
            except:
                font = ImageFont.load_default()
            draw.text((sx + size + 3, sy - 5), team.name, fill=(255, 255, 255), font=font)
    
    def _draw_bosses(self, img):
        """Zeichnet Boss-Positionen"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        draw = ImageDraw.Draw(img)
        
        for placement in self.boss_manager.placements:
            boss = self.boss_manager.get_boss(placement.boss_id)
            if not boss:
                continue
            
            hx, hy = self._hex_to_pixel(placement.hex_q, placement.hex_r)
            sx = int(canvas_width / 2 + hx * self.zoom + self.pan_x)
            sy = int(canvas_height / 2 + hy * self.zoom + self.pan_y)
            
            size = int(10 * self.zoom)
            
            if placement.revealed:
                # Enthüllt: Roter Kreis mit Name
                draw.ellipse([(sx - size, sy - size), (sx + size, sy + size)],
                             fill=(255, 50, 50), outline=(255, 255, 255))
                try:
                    font = ImageFont.truetype("arial.ttf", max(8, int(10 * self.zoom)))
                except:
                    font = ImageFont.load_default()
                draw.text((sx + size + 3, sy - 5), f"🐉 {boss.name}", fill=(255, 100, 100), font=font)
            else:
                # Nicht enthüllt: Oranger Kreis mit "?"
                draw.ellipse([(sx - size, sy - size), (sx + size, sy + size)],
                             fill=(255, 140, 0), outline=(255, 200, 0))
                draw.text((sx - 3, sy - 6), "?", fill=(0, 0, 0), font=ImageFont.load_default())
    
    def _draw_legend(self, draw, width, height):
        """Zeichnet die Legende"""
        try:
            font = ImageFont.truetype("arial.ttf", 11)
        except:
            font = ImageFont.load_default()
        
        y = height - 80
        x = 10
        
        # Hintergrund (größer für Exit-Punkte)
        draw.rectangle([(x, y), (x + 200, height - 10)], fill=(0, 0, 0, 180))
        
        draw.ellipse([(x + 5, y + 8), (x + 15, y + 18)], fill=(255, 140, 0))
        draw.text((x + 20, y + 5), "? = Versteckter Boss", fill=(255, 200, 100), font=font)
        
        draw.ellipse([(x + 5, y + 28), (x + 15, y + 38)], fill=(255, 50, 50))
        draw.text((x + 20, y + 25), "🐉 = Enthüllter Boss", fill=(255, 100, 100), font=font)
        
        # Exit-Punkte in Legende
        draw.ellipse([(x + 5, y + 48), (x + 15, y + 58)], fill=(0, 255, 255), outline=(255, 255, 0))
        draw.text((x + 20, y + 45), "🚪 = Exit-Punkt", fill=(0, 255, 255), font=font)


# =========================================================
# WEBCAM-SETUP DIALOG
# =========================================================

class WebcamSetupDialog(tk.Toplevel):
    """
    Dialog für Webcam-Konfiguration:
    - Kamera-Auswahl (USB-Geräte)
    - Kalibrierung (4 Ecken des Spielfelds)
    - Farb-Zuweisungen für Figuren
    """
    
    def __init__(self, parent, webcam_tracker, player_manager: PlayerManager):
        super().__init__(parent)
        
        self.title("📷 Webcam-Setup")
        self.configure(bg="#1a1a2e")
        self.geometry("800x600")
        
        self.webcam_tracker = webcam_tracker or WebcamFigureTracker(player_manager)
        self.player_manager = player_manager
        self.result = None
        
        # Kamera-Vorschau
        self.camera = None
        self.camera_index = getattr(self.webcam_tracker, 'camera_index', 0)
        self.preview_running = False
        self.preview_photo = None
        
        # Kalibrierung
        self.calibration_points = []  # 4 Eckpunkte
        self.calibration_mode = False
        
        # Verfügbare Kameras ermitteln
        self.available_cameras = self._detect_cameras()
        
        self._setup_ui()
        
        self.transient(parent)
        self.grab_set()
        
        # Beim Schließen aufräumen
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _detect_cameras(self) -> List[Dict]:
        """Erkennt verfügbare Kameras"""
        cameras = []
        try:
            import cv2
            # Teste Indizes 0-9
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        # Kamera-Info
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        cameras.append({
                            "index": i,
                            "name": f"Kamera {i}",
                            "resolution": f"{width}x{height}"
                        })
                    cap.release()
        except ImportError:
            print("⚠️ OpenCV nicht installiert")
        except Exception as e:
            print(f"⚠️ Kamera-Erkennung Fehler: {e}")
        
        if not cameras:
            cameras.append({"index": 0, "name": "Standard-Kamera", "resolution": "Unbekannt"})
        
        return cameras
    
    def _setup_ui(self):
        """Erstellt die UI"""
        # Hauptcontainer
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Linke Seite: Kamera-Vorschau
        preview_frame = tk.Frame(main_frame, bg="#16213e")
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(preview_frame, text="📷 Kamera-Vorschau", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=5)
        
        # Kamera-Auswahl
        cam_select_frame = tk.Frame(preview_frame, bg="#16213e")
        cam_select_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(cam_select_frame, text="Kamera:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        
        camera_names = [f"{c['name']} ({c['resolution']})" for c in self.available_cameras]
        self.camera_var = tk.StringVar(value=camera_names[0] if camera_names else "")
        self.camera_combo = tk.ttk.Combobox(cam_select_frame, textvariable=self.camera_var,
                                            values=camera_names, state="readonly", width=25)
        self.camera_combo.pack(side=tk.LEFT, padx=5)
        self.camera_combo.bind('<<ComboboxSelected>>', self._on_camera_changed)
        
        tk.Button(cam_select_frame, text="🔄 Aktualisieren", command=self._refresh_cameras,
                  bg="#17a2b8", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        
        # Vorschau-Canvas
        self.preview_canvas = tk.Canvas(preview_frame, bg="#0a0a0a", width=480, height=360,
                                        highlightthickness=1, highlightbackground="#444")
        self.preview_canvas.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)
        self.preview_canvas.bind('<Button-1>', self._on_preview_click)
        
        # Start/Stop Buttons
        btn_frame = tk.Frame(preview_frame, bg="#16213e")
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Vorschau starten", command=self._start_preview,
                                   bg="#28a745", fg="white", relief=tk.FLAT)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ Stoppen", command=self._stop_preview,
                                  bg="#dc3545", fg="white", relief=tk.FLAT, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Rechte Seite: Einstellungen
        settings_frame = tk.Frame(main_frame, bg="#16213e", width=280)
        settings_frame.pack(side=tk.RIGHT, fill=tk.Y)
        settings_frame.pack_propagate(False)
        
        tk.Label(settings_frame, text="⚙️ Einstellungen", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        # Kalibrierung
        calib_frame = tk.LabelFrame(settings_frame, text="📐 Kalibrierung", bg="#16213e", fg="white")
        calib_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(calib_frame, text="Klicke 4 Ecken des Spielfelds\nin der Vorschau:", 
                 bg="#16213e", fg="#aaa", justify=tk.LEFT).pack(pady=5, padx=5)
        
        self.calib_status = tk.Label(calib_frame, text="⚪ Nicht kalibriert", 
                                     bg="#16213e", fg="#ff6b6b")
        self.calib_status.pack(pady=5)
        
        self.calib_btn = tk.Button(calib_frame, text="🎯 Kalibrierung starten",
                                   command=self._start_calibration,
                                   bg="#ffc107", fg="black", relief=tk.FLAT)
        self.calib_btn.pack(pady=5, padx=10, fill=tk.X)
        
        tk.Button(calib_frame, text="🔄 Zurücksetzen", command=self._reset_calibration,
                  bg="#6c757d", fg="white", relief=tk.FLAT).pack(pady=5, padx=10, fill=tk.X)
        
        # Figuren-Zuordnung
        figure_frame = tk.LabelFrame(settings_frame, text="🎨 Figuren-Farben", bg="#16213e", fg="white")
        figure_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(figure_frame, text="Spieler -> Figurfarbe zuweisen:", 
                 bg="#16213e", fg="#aaa").pack(pady=5)
        
        # Spieler-Liste mit Farb-Buttons
        self.player_colors_frame = tk.Frame(figure_frame, bg="#16213e")
        self.player_colors_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._populate_player_colors()
        
        # Buttons unten
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="✓ Übernehmen", command=self._save,
                  bg="#28a745", fg="white", relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self._on_close,
                  bg="#dc3545", fg="white", relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
    
    def _populate_player_colors(self):
        """Füllt die Spieler-Farben-Liste"""
        # Alte Widgets entfernen
        for widget in self.player_colors_frame.winfo_children():
            widget.destroy()
        
        for player in self.player_manager.get_all_players():
            row = tk.Frame(self.player_colors_frame, bg="#16213e")
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=player.name, bg="#16213e", fg="white", width=15, anchor=tk.W).pack(side=tk.LEFT)
            
            # Farb-Button
            color_btn = tk.Button(row, text="●", fg=player.color, bg="#0f3460",
                                  relief=tk.FLAT, width=3,
                                  command=lambda p=player: self._pick_figure_color(p))
            color_btn.pack(side=tk.LEFT, padx=5)
            
            tk.Label(row, text="HSV klicken", bg="#16213e", fg="#666", font=("Arial", 8)).pack(side=tk.LEFT)
    
    def _pick_figure_color(self, player: PlayerDefinition):
        """Ermöglicht das Auswählen einer Figurfarbe aus dem Kamerabild"""
        if not self.preview_running:
            messagebox.showinfo("Info", "Bitte zuerst Kamera-Vorschau starten!")
            return
        
        messagebox.showinfo("Farbe wählen", 
            f"Klicke auf die Figur von '{player.name}' im Kamerabild.\n"
            "Die Farbe wird automatisch erkannt.")
        self.color_pick_player = player
    
    def _on_camera_changed(self, event):
        """Wenn eine andere Kamera ausgewählt wird"""
        selection = self.camera_combo.current()
        if selection >= 0 and selection < len(self.available_cameras):
            self.camera_index = self.available_cameras[selection]["index"]
            if self.preview_running:
                self._stop_preview()
                self._start_preview()
    
    def _refresh_cameras(self):
        """Aktualisiert die Kamera-Liste"""
        self.available_cameras = self._detect_cameras()
        camera_names = [f"{c['name']} ({c['resolution']})" for c in self.available_cameras]
        self.camera_combo['values'] = camera_names
        if camera_names:
            self.camera_combo.set(camera_names[0])
    
    def _start_preview(self):
        """Startet die Kamera-Vorschau"""
        try:
            import cv2
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                messagebox.showerror("Fehler", f"Kamera {self.camera_index} konnte nicht geöffnet werden!")
                return
            
            self.preview_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self._update_preview()
            
        except ImportError:
            messagebox.showerror("Fehler", "OpenCV (cv2) ist nicht installiert!\n\n"
                                "Installation: pip install opencv-python")
        except Exception as e:
            messagebox.showerror("Fehler", f"Kamera-Fehler: {e}")
    
    def _stop_preview(self):
        """Stoppt die Kamera-Vorschau"""
        self.preview_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def _update_preview(self):
        """Update-Loop für Kamera-Vorschau"""
        if not self.preview_running or not self.camera:
            return
        
        try:
            import cv2
            ret, frame = self.camera.read()
            if ret:
                # BGR zu RGB konvertieren
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Auf Canvas-Größe skalieren
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Aspect Ratio beibehalten
                    h, w = frame_rgb.shape[:2]
                    scale = min(canvas_width / w, canvas_height / h)
                    new_w, new_h = int(w * scale), int(h * scale)
                    
                    frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
                    
                    # Kalibrierungspunkte zeichnen
                    if self.calibration_points:
                        for i, (px, py) in enumerate(self.calibration_points):
                            # Skalierte Position
                            sx = int(px * scale)
                            sy = int(py * scale)
                            cv2.circle(frame_resized, (sx, sy), 8, (0, 255, 0), 2)
                            cv2.putText(frame_resized, str(i + 1), (sx + 10, sy),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Zu PIL Image
                    img = Image.fromarray(frame_resized)
                    self.preview_photo = ImageTk.PhotoImage(img)
                    
                    # Zentriert auf Canvas
                    x = (canvas_width - new_w) // 2
                    y = (canvas_height - new_h) // 2
                    self.preview_canvas.delete("all")
                    self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.preview_photo)
                    
                    # Kalibrierungs-Anweisung
                    if self.calibration_mode:
                        text = f"Klicke Ecke {len(self.calibration_points) + 1} von 4"
                        self.preview_canvas.create_text(canvas_width // 2, 20, 
                                                        text=text, fill="#00ff00",
                                                        font=("Arial", 14, "bold"))
        except Exception as e:
            print(f"Preview-Fehler: {e}")
        
        # Nächster Frame
        self.after(33, self._update_preview)  # ~30 FPS
    
    def _on_preview_click(self, event):
        """Klick auf Vorschau-Canvas"""
        if not self.preview_running or not self.camera:
            return
        
        # Canvas-Koordinaten zu Kamera-Koordinaten umrechnen
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        try:
            import cv2
            ret, frame = self.camera.read()
            if not ret:
                return
            
            h, w = frame.shape[:2]
            scale = min(canvas_width / w, canvas_height / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            # Offset berechnen (zentriertes Bild)
            x_offset = (canvas_width - new_w) // 2
            y_offset = (canvas_height - new_h) // 2
            
            # Klick in Bildkoordinaten
            img_x = int((event.x - x_offset) / scale)
            img_y = int((event.y - y_offset) / scale)
            
            if 0 <= img_x < w and 0 <= img_y < h:
                if self.calibration_mode:
                    # Kalibrierungspunkt hinzufügen
                    self.calibration_points.append((img_x, img_y))
                    print(f"📍 Kalibrierungspunkt {len(self.calibration_points)}: ({img_x}, {img_y})")
                    
                    if len(self.calibration_points) >= 4:
                        self._finish_calibration()
                
                elif hasattr(self, 'color_pick_player') and self.color_pick_player:
                    # Farbe an Klickposition ermitteln
                    bgr_color = frame[img_y, img_x]
                    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    hsv_color = hsv_frame[img_y, img_x]
                    
                    # Farbe dem Spieler zuweisen
                    player = self.color_pick_player
                    self.webcam_tracker.assign_color_to_player(
                        tuple(hsv_color), player.id
                    )
                    
                    # RGB für Anzeige
                    r, g, b = int(bgr_color[2]), int(bgr_color[1]), int(bgr_color[0])
                    hex_color = f"#{r:02x}{g:02x}{b:02x}"
                    
                    messagebox.showinfo("Farbe zugewiesen",
                        f"Spieler '{player.name}' zugewiesen:\n"
                        f"HSV: {tuple(hsv_color)}\n"
                        f"RGB: {hex_color}")
                    
                    self.color_pick_player = None
                    self._populate_player_colors()
        except Exception as e:
            print(f"Klick-Fehler: {e}")
    
    def _start_calibration(self):
        """Startet den Kalibrierungsmodus"""
        if not self.preview_running:
            messagebox.showinfo("Info", "Bitte zuerst Kamera-Vorschau starten!")
            return
        
        self.calibration_points = []
        self.calibration_mode = True
        self.calib_btn.config(text="⏳ Warte auf 4 Klicks...", state=tk.DISABLED)
        self.calib_status.config(text="🟡 Kalibrierung läuft...", fg="#ffc107")
    
    def _finish_calibration(self):
        """Beendet die Kalibrierung"""
        self.calibration_mode = False
        self.webcam_tracker.calibrate(self.calibration_points)
        
        self.calib_btn.config(text="✅ Neu kalibrieren", state=tk.NORMAL)
        self.calib_status.config(text="🟢 Kalibriert!", fg="#28a745")
        
        messagebox.showinfo("Kalibrierung", 
            "Kalibrierung abgeschlossen!\n\n"
            "Die 4 Ecken des Spielfelds wurden markiert.")
    
    def _reset_calibration(self):
        """Setzt die Kalibrierung zurück"""
        self.calibration_points = []
        self.calibration_mode = False
        self.webcam_tracker.calibration_data = {}
        
        self.calib_btn.config(text="🎯 Kalibrierung starten", state=tk.NORMAL)
        self.calib_status.config(text="⚪ Nicht kalibriert", fg="#ff6b6b")
    
    def _save(self):
        """Speichert Einstellungen und schließt"""
        self.webcam_tracker.camera_index = self.camera_index
        self.result = self.webcam_tracker
        self._on_close()
    
    def _on_close(self):
        """Beim Schließen aufräumen"""
        self._stop_preview()
        self.destroy()


# =========================================================
# SPIELER-EDITOR DIALOG
# =========================================================

class PlayerEditorDialog(tk.Toplevel):
    """Dialog zum Bearbeiten von Spielern und Teams"""
    
    def __init__(self, parent, player_manager: PlayerManager):
        super().__init__(parent)
        
        self.title("🎮 Spieler & Teams")
        self.configure(bg="#1a1a2e")
        self.geometry("700x500")
        
        self.player_manager = player_manager
        self.result = None
        
        self._setup_ui()
        
        self.transient(parent)
        self.grab_set()
    
    def _setup_ui(self):
        """Erstellt die UI"""
        # Notebook für Tabs
        notebook = tk.ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Spieler-Tab
        players_frame = tk.Frame(notebook, bg="#1a1a2e")
        notebook.add(players_frame, text="👤 Spieler")
        self._setup_players_tab(players_frame)
        
        # Teams-Tab
        teams_frame = tk.Frame(notebook, bg="#1a1a2e")
        notebook.add(teams_frame, text="👥 Teams")
        self._setup_teams_tab(teams_frame)
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(btn_frame, text="✓ Speichern", command=self._save,
                  bg="#28a745", fg="white", relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self.destroy,
                  bg="#dc3545", fg="white", relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
    
    def _setup_players_tab(self, parent):
        """Spieler-Tab UI"""
        # Liste
        list_frame = tk.Frame(parent, bg="#16213e")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(list_frame, text="Spieler", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=5)
        
        self.player_listbox = tk.Listbox(list_frame, bg="#0f3460", fg="white",
                                          selectbackground="#e94560")
        self.player_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(list_frame, bg="#16213e")
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(btn_frame, text="➕ Neu", command=self._add_player,
                  bg="#28a745", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="🗑️ Löschen", command=self._remove_player,
                  bg="#dc3545", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        
        # Editor
        edit_frame = tk.Frame(parent, bg="#16213e")
        edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(edit_frame, text="Bearbeiten", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=5)
        
        # Name
        tk.Label(edit_frame, text="Name:", bg="#16213e", fg="white").pack(anchor=tk.W, padx=10)
        self.player_name_var = tk.StringVar()
        tk.Entry(edit_frame, textvariable=self.player_name_var, bg="#0f3460", fg="white",
                 insertbackground="white").pack(fill=tk.X, padx=10, pady=2)
        
        # Farbe
        tk.Label(edit_frame, text="Farbe:", bg="#16213e", fg="white").pack(anchor=tk.W, padx=10, pady=(10, 0))
        
        self.color_frame = tk.Frame(edit_frame, bg="#16213e")
        self.color_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.player_color_var = tk.StringVar(value="#4488FF")
        for name, color in list(TEAM_COLORS.items())[:5]:
            tk.Button(self.color_frame, text="  ", bg=color,
                      command=lambda c=color: self.player_color_var.set(c),
                      width=3, relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        
        # Team-Zuordnung
        tk.Label(edit_frame, text="Team:", bg="#16213e", fg="white").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.player_team_var = tk.StringVar()
        self.team_combo = tk.ttk.Combobox(edit_frame, textvariable=self.player_team_var)
        self.team_combo.pack(fill=tk.X, padx=10, pady=2)
        
        # Aktiv
        self.player_active_var = tk.BooleanVar(value=True)
        tk.Checkbutton(edit_frame, text="Aktiv", variable=self.player_active_var,
                       bg="#16213e", fg="white", selectcolor="#0f3460").pack(anchor=tk.W, padx=10, pady=10)
        
        tk.Button(edit_frame, text="💾 Änderungen übernehmen", command=self._apply_player_changes,
                  bg="#17a2b8", fg="white", relief=tk.FLAT).pack(pady=10)
        
        # Initialisieren
        self._refresh_player_list()
        self._refresh_team_combo()
        self.player_listbox.bind('<<ListboxSelect>>', self._on_player_select)
    
    def _setup_teams_tab(self, parent):
        """Teams-Tab UI"""
        # Liste
        list_frame = tk.Frame(parent, bg="#16213e")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(list_frame, text="Teams", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=5)
        
        self.team_listbox = tk.Listbox(list_frame, bg="#0f3460", fg="white",
                                        selectbackground="#e94560")
        self.team_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(list_frame, bg="#16213e")
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(btn_frame, text="➕ Neu", command=self._add_team,
                  bg="#28a745", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="🗑️ Löschen", command=self._remove_team,
                  bg="#dc3545", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        
        # Editor
        edit_frame = tk.Frame(parent, bg="#16213e")
        edit_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(edit_frame, text="Team bearbeiten", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(pady=5)
        
        # Name
        tk.Label(edit_frame, text="Name:", bg="#16213e", fg="white").pack(anchor=tk.W, padx=10)
        self.team_name_var = tk.StringVar()
        tk.Entry(edit_frame, textvariable=self.team_name_var, bg="#0f3460", fg="white",
                 insertbackground="white").pack(fill=tk.X, padx=10, pady=2)
        
        # Farbe
        tk.Label(edit_frame, text="Team-Farbe:", bg="#16213e", fg="white").pack(anchor=tk.W, padx=10, pady=(10, 0))
        
        self.team_color_frame = tk.Frame(edit_frame, bg="#16213e")
        self.team_color_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.team_color_var = tk.StringVar(value="#4488FF")
        for name, color in TEAM_COLORS.items():
            tk.Button(self.team_color_frame, text="  ", bg=color,
                      command=lambda c=color: self.team_color_var.set(c),
                      width=2, relief=tk.FLAT).pack(side=tk.LEFT, padx=1)
        
        # Mitglieder
        tk.Label(edit_frame, text="Mitglieder:", bg="#16213e", fg="white").pack(anchor=tk.W, padx=10, pady=(10, 0))
        self.members_listbox = tk.Listbox(edit_frame, bg="#0f3460", fg="white", height=5)
        self.members_listbox.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Button(edit_frame, text="💾 Änderungen übernehmen", command=self._apply_team_changes,
                  bg="#17a2b8", fg="white", relief=tk.FLAT).pack(pady=10)
        
        # Initialisieren
        self._refresh_team_list()
        self.team_listbox.bind('<<ListboxSelect>>', self._on_team_select)
    
    def _refresh_player_list(self):
        """Aktualisiert die Spieler-Liste"""
        self.player_listbox.delete(0, tk.END)
        for player in self.player_manager.get_all_players():
            team_info = f" [{player.team_name}]" if player.team_name else ""
            self.player_listbox.insert(tk.END, f"{player.name}{team_info}")
    
    def _refresh_team_list(self):
        """Aktualisiert die Team-Liste"""
        self.team_listbox.delete(0, tk.END)
        for team in self.player_manager.get_all_teams():
            self.team_listbox.insert(tk.END, f"{team.name} ({len(team.member_ids)} Spieler)")
    
    def _refresh_team_combo(self):
        """Aktualisiert die Team-Auswahl"""
        teams = ["(Kein Team)"] + [t.name for t in self.player_manager.get_all_teams()]
        self.team_combo['values'] = teams
    
    def _on_player_select(self, event):
        """Wenn ein Spieler ausgewählt wird"""
        selection = self.player_listbox.curselection()
        if not selection:
            return
        
        players = list(self.player_manager.players.values())
        if selection[0] < len(players):
            player = players[selection[0]]
            self.player_name_var.set(player.name)
            self.player_color_var.set(player.color)
            self.player_active_var.set(player.is_active)
            
            if player.team_name:
                self.player_team_var.set(player.team_name)
            else:
                self.player_team_var.set("(Kein Team)")
    
    def _on_team_select(self, event):
        """Wenn ein Team ausgewählt wird"""
        selection = self.team_listbox.curselection()
        if not selection:
            return
        
        teams = list(self.player_manager.teams.values())
        if selection[0] < len(teams):
            team = teams[selection[0]]
            self.team_name_var.set(team.name)
            self.team_color_var.set(team.color)
            
            # Mitglieder anzeigen
            self.members_listbox.delete(0, tk.END)
            for pid in team.member_ids:
                player = self.player_manager.get_player(pid)
                if player:
                    self.members_listbox.insert(tk.END, player.name)
    
    def _add_player(self):
        """Fügt einen neuen Spieler hinzu"""
        player = PlayerDefinition(name=f"Spieler {len(self.player_manager.players) + 1}")
        self.player_manager.add_player(player)
        self._refresh_player_list()
    
    def _remove_player(self):
        """Entfernt den ausgewählten Spieler"""
        selection = self.player_listbox.curselection()
        if not selection:
            return
        
        players = list(self.player_manager.players.values())
        if selection[0] < len(players):
            self.player_manager.remove_player(players[selection[0]].id)
            self._refresh_player_list()
    
    def _apply_player_changes(self):
        """Übernimmt Änderungen am Spieler"""
        selection = self.player_listbox.curselection()
        if not selection:
            return
        
        players = list(self.player_manager.players.values())
        if selection[0] < len(players):
            player = players[selection[0]]
            player.name = self.player_name_var.get()
            player.color = self.player_color_var.get()
            player.is_active = self.player_active_var.get()
            
            # Team-Zuordnung
            team_name = self.player_team_var.get()
            if team_name == "(Kein Team)":
                self.player_manager.remove_player_from_team(player.id)
            else:
                for team in self.player_manager.teams.values():
                    if team.name == team_name:
                        self.player_manager.add_player_to_team(player.id, team.id)
                        break
            
            self._refresh_player_list()
    
    def _add_team(self):
        """Fügt ein neues Team hinzu"""
        team = TeamDefinition(name=f"Team {len(self.player_manager.teams) + 1}")
        self.player_manager.add_team(team)
        self._refresh_team_list()
        self._refresh_team_combo()
    
    def _remove_team(self):
        """Entfernt das ausgewählte Team"""
        selection = self.team_listbox.curselection()
        if not selection:
            return
        
        teams = list(self.player_manager.teams.values())
        if selection[0] < len(teams):
            self.player_manager.remove_team(teams[selection[0]].id)
            self._refresh_team_list()
            self._refresh_team_combo()
    
    def _apply_team_changes(self):
        """Übernimmt Änderungen am Team"""
        selection = self.team_listbox.curselection()
        if not selection:
            return
        
        teams = list(self.player_manager.teams.values())
        if selection[0] < len(teams):
            team = teams[selection[0]]
            team.name = self.team_name_var.get()
            team.color = self.team_color_var.get()
            
            # Alle Team-Mitglieder auf neue Farbe setzen
            for pid in team.member_ids:
                player = self.player_manager.get_player(pid)
                if player:
                    player.color = team.color
                    player.team_name = team.name
            
            self._refresh_team_list()
            self._refresh_team_combo()
    
    def _save(self):
        """Speichert und schließt"""
        self.result = self.player_manager
        self.destroy()


class TeamAssignmentDialog(tk.Toplevel):
    """
    Dialog zur Zuordnung von Teams zu Split-View Screens.
    
    Ermöglicht:
    - Jeder Screen bekommt ein Team zugewiesen
    - Einzelne Spieler können auch direkt einem Screen zugewiesen werden
    - Vorschau der Spawn-Areas pro Team
    """
    
    def __init__(self, parent, player_manager: PlayerManager, viewports: List[ViewportConfig]):
        super().__init__(parent)
        
        self.title("🎮 Team-Zuordnung zu Screens")
        self.geometry("500x400")
        self.configure(bg="#1a1a2e")
        
        self.player_manager = player_manager
        self.viewports = viewports
        self.result = None
        
        # Team-Auswahl pro Screen
        self.screen_team_vars = []
        
        self._setup_ui()
        
        # Modal
        self.transient(parent)
        self.grab_set()
    
    def _setup_ui(self):
        """Erstellt die UI"""
        # Header
        header = tk.Frame(self, bg="#16213e", height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🎮 Team-Zuordnung zu Screens",
                 bg="#16213e", fg="white", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Beschreibung
        desc_frame = tk.Frame(self, bg="#1a1a2e")
        desc_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(desc_frame, text="Ordne jedem Screen ein Team zu.\n"
                                  "Der Screen wird dann auf die Spawn-Area des Teams gezoomt.",
                 bg="#1a1a2e", fg="#aaaaaa", justify=tk.LEFT).pack(anchor=tk.W)
        
        # Screen-Zuordnungen
        assignment_frame = tk.Frame(self, bg="#0f3460")
        assignment_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar falls viele Screens
        canvas = tk.Canvas(assignment_frame, bg="#0f3460", highlightthickness=0)
        scrollbar = tk.Scrollbar(assignment_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#0f3460")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Teams als Optionen - zähle Spieler aus member_ids ODER aus player.team_id
        teams = list(self.player_manager.teams.values())
        
        def count_team_members(team):
            """Zählt Team-Mitglieder aus beiden Quellen"""
            # Methode 1: member_ids des Teams
            count1 = len(team.member_ids)
            # Methode 2: Spieler mit team_id
            count2 = len([p for p in self.player_manager.players.values() if p.team_id == team.id])
            return max(count1, count2)
        
        team_options = ["-- Kein Team --"] + [f"{t.name} ({count_team_members(t)} Spieler)" for t in teams]
        team_ids = [None] + [t.id for t in teams]
        
        for i, viewport in enumerate(self.viewports):
            row_frame = tk.Frame(scrollable_frame, bg="#16213e", padx=10, pady=8)
            row_frame.pack(fill=tk.X, pady=3)
            
            # Screen-Nummer mit Farbindikator
            screen_label = tk.Label(row_frame, text=f"📺 Screen {i + 1}:", 
                                    bg="#16213e", fg="white", font=("Arial", 11, "bold"), width=12)
            screen_label.pack(side=tk.LEFT, padx=5)
            
            # Aktuelle Farbe anzeigen
            color_box = tk.Label(row_frame, text="  ", bg=viewport.team_color, width=3)
            color_box.pack(side=tk.LEFT, padx=5)
            
            # Team Dropdown
            team_var = tk.StringVar()
            
            # Aktuelles Team vorselektieren
            if viewport.team_id:
                for j, tid in enumerate(team_ids):
                    if tid == viewport.team_id:
                        team_var.set(team_options[j])
                        break
            else:
                team_var.set(team_options[0])
            
            self.screen_team_vars.append((team_var, team_ids, color_box))
            
            team_combo = tk.ttk.Combobox(row_frame, textvariable=team_var, values=team_options, 
                                         state="readonly", width=35)
            team_combo.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            
            # Wenn Team geändert wird, Farbe aktualisieren
            team_combo.bind("<<ComboboxSelected>>", lambda e, idx=i: self._on_team_changed(idx))
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=10, pady=15)
        
        tk.Button(btn_frame, text="❌ Abbrechen", command=self.destroy,
                  bg="#6c757d", fg="white", relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(btn_frame, text="✅ Übernehmen", command=self._apply,
                  bg="#28a745", fg="white", relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(btn_frame, text="🔄 Auto-Zuordnen", command=self._auto_assign,
                  bg="#17a2b8", fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=5)
    
    def _on_team_changed(self, screen_idx: int):
        """Callback wenn Team für Screen geändert wird"""
        team_var, team_ids, color_box = self.screen_team_vars[screen_idx]
        
        # Finde ausgewähltes Team
        selected_text = team_var.get()
        selected_idx = 0
        
        teams = list(self.player_manager.teams.values())
        team_options = ["-- Kein Team --"] + [f"{t.name} ({len([p for p in self.player_manager.players.values() if p.team_id == t.id])} Spieler)" for t in teams]
        
        for i, opt in enumerate(team_options):
            if opt == selected_text:
                selected_idx = i
                break
        
        # Farbe aktualisieren
        if selected_idx > 0 and selected_idx - 1 < len(teams):
            team = teams[selected_idx - 1]
            color_box.configure(bg=team.color)
        else:
            color_box.configure(bg="#888888")
    
    def _auto_assign(self):
        """Ordnet Teams automatisch den Screens zu (in Reihenfolge)"""
        teams = list(self.player_manager.teams.values())
        team_options = ["-- Kein Team --"] + [f"{t.name} ({len([p for p in self.player_manager.players.values() if p.team_id == t.id])} Spieler)" for t in teams]
        
        for i, (team_var, _, color_box) in enumerate(self.screen_team_vars):
            if i < len(teams):
                team_var.set(team_options[i + 1])  # +1 weil Index 0 = "Kein Team"
                color_box.configure(bg=teams[i].color)
            else:
                team_var.set(team_options[0])
                color_box.configure(bg="#888888")
    
    def _apply(self):
        """Übernimmt die Zuordnungen"""
        teams = list(self.player_manager.teams.values())
        team_ids = [None] + [t.id for t in teams]
        team_options = ["-- Kein Team --"] + [f"{t.name} ({len([p for p in self.player_manager.players.values() if p.team_id == t.id])} Spieler)" for t in teams]
        
        result = []
        
        for team_var, _, _ in self.screen_team_vars:
            selected_text = team_var.get()
            
            # Finde Team-ID
            selected_team_id = None
            for i, opt in enumerate(team_options):
                if opt == selected_text:
                    selected_team_id = team_ids[i]
                    break
            
            result.append(selected_team_id)
        
        self.result = result
        print(f"✅ Team-Zuordnung: {result}")
        self.destroy()


if __name__ == "__main__":
    # Test
    root = tk.Tk()
    root.title("Split-View Test")
    root.geometry("400x300")
    
    # Test Player Manager
    pm = PlayerManager()
    
    # Teams erstellen
    team1 = TeamDefinition(name="Die Gefährten", color="#4488FF")
    team2 = TeamDefinition(name="Die Orks", color="#FF4444")
    pm.add_team(team1)
    pm.add_team(team2)
    
    # Spieler
    p1 = PlayerDefinition(name="Frodo")
    p2 = PlayerDefinition(name="Sam")
    p3 = PlayerDefinition(name="Ork-Boss")
    pm.add_player(p1)
    pm.add_player(p2)
    pm.add_player(p3)
    
    pm.add_player_to_team(p1.id, team1.id)
    pm.add_player_to_team(p2.id, team1.id)
    pm.add_player_to_team(p3.id, team2.id)
    
    # Positionen setzen
    team1.hex_q, team1.hex_r = 5, 5
    team2.hex_q, team2.hex_r = 15, 10
    p1.hex_q, p1.hex_r = 5, 5
    p2.hex_q, p2.hex_r = 5, 5
    p3.hex_q, p3.hex_r = 15, 10
    
    # Test Map-Data
    map_data = {
        "width": 20,
        "height": 20,
        "hex_size": 40,
        "orientation": "pointy",
        "tiles": {
            "5,5": {"center_x": 200, "center_y": 200, "is_spawn_hex": True, "fill_color": "#44aa44"},
            "15,10": {"center_x": 600, "center_y": 400, "is_spawn_hex": True, "fill_color": "#aa4444"},
            "10,7": {"center_x": 400, "center_y": 300, "is_boss_hex": True, "fill_color": "#666666"},
        }
    }
    
    def open_projector():
        SplitViewProjector(root, map_data=map_data, player_manager=pm, num_screens=2)
    
    def open_editor():
        PlayerEditorDialog(root, pm)
    
    tk.Button(root, text="🎮 Spieler Editor", command=open_editor).pack(pady=20)
    tk.Button(root, text="📺 Split-View Projektor", command=open_projector).pack(pady=20)
    
    root.mainloop()
