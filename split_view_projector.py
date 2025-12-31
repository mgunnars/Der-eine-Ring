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
        
        # Canvas und Rendering
        self.main_canvas = None
        self.map_photo = None  # PhotoImage Referenz
        
        # Hexagon-Parameter
        self.hex_size = self.map_data.get("hex_size", 40)
        self.orientation = self.map_data.get("orientation", "pointy")
        
        # Tiles normalisieren (kann Liste oder Dict sein)
        self._normalize_tiles()
        
        # Animation
        self.animation_running = False
        self.animation_id = None
        
        # Webcam-Tracker
        self.webcam_tracker = None
        self.webcam_enabled = False
        
        # Auto-Follow (Viewport folgt Spielerbewegung)
        self.auto_follow_enabled = True
        
        # UI Setup
        self._setup_ui()
    
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
        self._setup_viewports()
        
        # Initial Render
        self.after(100, self.render_all)
    
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
        
        # Mouse Events für Debug/Interaktion
        self.main_canvas.bind('<Button-1>', self._on_click)
        self.main_canvas.bind('<Motion>', self._on_mouse_move)
    
    def _setup_viewports(self):
        """Richtet die Viewports basierend auf Teams ein"""
        self.viewports.clear()
        
        canvas_width = self.main_canvas.winfo_width() or 1280
        canvas_height = self.main_canvas.winfo_height() or 720
        
        if not self.split_enabled or self.num_screens <= 1:
            # Einzelner Viewport
            self.viewports.append(ViewportConfig(
                screen_index=0,
                x_offset=0,
                width=canvas_width,
                height=canvas_height,
                zoom=1.0  # Normaler Zoom für Single-View
            ))
            return
        
        # Multi-Screen Setup
        screen_width = canvas_width // self.num_screens
        teams = list(self.player_manager.teams.values())
        
        for i in range(self.num_screens):
            team = teams[i] if i < len(teams) else None
            
            viewport = ViewportConfig(
                screen_index=i,
                x_offset=i * screen_width,
                width=screen_width,
                height=canvas_height,
                zoom=self.split_zoom,
                team_id=team.id if team else None,
                team_color=team.color if team else "#888888",
                center_q=team.hex_q if team else 0,
                center_r=team.hex_r if team else 0
            )
            self.viewports.append(viewport)
        
        print(f"📺 {len(self.viewports)} Viewports erstellt")
    
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
        Aktualisiert das Viewport-Zentrum sanft zum Ziel.
        Implementiert sanftes Following mit Interpolation.
        """
        # Direkte Aktualisierung für schnelle Reaktion
        # (könnte später durch Interpolation ersetzt werden für sanfteres Following)
        old_q, old_r = viewport.center_q, viewport.center_r
        
        # Nur aktualisieren wenn sich Position geändert hat
        if (old_q, old_r) != (target_q, target_r):
            viewport.center_q = target_q
            viewport.center_r = target_r
            print(f"🎯 Viewport {viewport.screen_index} folgt: ({old_q},{old_r}) -> ({target_q},{target_r})")
    
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
        """Mouse-Click Handler"""
        # Finde welcher Viewport geklickt wurde
        for viewport in self.viewports:
            if viewport.x_offset <= event.x < viewport.x_offset + viewport.width:
                hex_q, hex_r = self._screen_to_hex(event.x, event.y, viewport)
                print(f"🖱️ Viewport {viewport.screen_index}: Hex ({hex_q}, {hex_r})")
                
                # Prüfe ob Boss an Position
                self._check_boss_discovery(hex_q, hex_r)
                break
    
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
        """Konvertiert Hex-Koordinaten zu Pixel-Koordinaten"""
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
        
        # Map-Position berechnen
        map_x = center_px + (rel_x - viewport.width / 2) / viewport.zoom
        map_y = center_py + (rel_y - viewport.height / 2) / viewport.zoom
        
        return self._pixel_to_hex(map_x, map_y)
    
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
    
    # =========================================================
    # RENDERING
    # =========================================================
    
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
        
        # Minimap auf alle Viewports rendern
        if self.minimap_enabled:
            minimap = self._render_minimap()
            for viewport in self.viewports:
                self._overlay_minimap(main_image, minimap, viewport)
        
        # Zu PhotoImage konvertieren und anzeigen
        self.map_photo = ImageTk.PhotoImage(main_image)
        self.main_canvas.delete("all")
        self.main_canvas.create_image(0, 0, anchor=tk.NW, image=self.map_photo)
    
    def _render_viewport(self, viewport: ViewportConfig) -> Image.Image:
        """Rendert einen einzelnen Viewport"""
        # Viewport-Image erstellen
        img = Image.new('RGBA', (viewport.width, viewport.height), (20, 20, 30, 255))
        draw = ImageDraw.Draw(img)
        
        tiles = self._get_tiles_dict()
        
        # Berechne sichtbaren Bereich
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        # Viewport-Grenzen in Map-Koordinaten
        half_w = viewport.width / (2 * viewport.zoom)
        half_h = viewport.height / (2 * viewport.zoom)
        
        # Zeichne alle sichtbaren Hexagone
        for coord_key, tile_data in tiles.items():
            if not isinstance(tile_data, dict):
                continue
            
            try:
                parts = coord_key.split(',')
                q, r = int(parts[0]), int(parts[1])
            except:
                continue
            
            # Hole Tile-Zentrum
            tile_cx = tile_data.get("center_x", 0)
            tile_cy = tile_data.get("center_y", 0)
            
            # Prüfe ob im Viewport sichtbar
            if (tile_cx < center_px - half_w - self.hex_size or
                tile_cx > center_px + half_w + self.hex_size or
                tile_cy < center_py - half_h - self.hex_size or
                tile_cy > center_py + half_h + self.hex_size):
                continue
            
            # Transformiere zu Viewport-Koordinaten
            vx = viewport.width / 2 + (tile_cx - center_px) * viewport.zoom
            vy = viewport.height / 2 + (tile_cy - center_py) * viewport.zoom
            
            # Zeichne Hexagon
            self._draw_hexagon(draw, vx, vy, viewport.zoom, tile_data, viewport)
        
        # Spieler-Tokens zeichnen
        self._draw_players_in_viewport(img, viewport)
        
        # Boss-Overlays zeichnen
        self._draw_bosses_in_viewport(img, viewport)
        
        # Team-Info-Header
        if viewport.team_id:
            team = self.player_manager.get_team(viewport.team_id)
            if team:
                self._draw_team_header(img, team, viewport)
        
        return img
    
    def _draw_hexagon(self, draw: ImageDraw.Draw, cx: float, cy: float, 
                      zoom: float, tile_data: Dict, viewport: ViewportConfig):
        """Zeichnet ein einzelnes Hexagon"""
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
        
        # Füllfarbe
        fill_color = tile_data.get("fill_color", "#444444")
        try:
            if fill_color.startswith('#'):
                r = int(fill_color[1:3], 16)
                g = int(fill_color[3:5], 16)
                b = int(fill_color[5:7], 16)
                fill = (r, g, b, 200)
            else:
                fill = (68, 68, 68, 200)
        except:
            fill = (68, 68, 68, 200)
        
        # Hexagon zeichnen
        draw.polygon(points, fill=fill, outline=(100, 100, 100, 255))
        
        # Spezielle Markierungen
        if tile_data.get("is_boss_hex", False):
            # Boss-Hexagon: Orange Overlay
            draw.polygon(points, fill=(255, 140, 0, 100), outline=(255, 100, 0, 255))
        
        if tile_data.get("is_spawn_hex", False):
            # Spawn-Hexagon: Grünes Overlay
            draw.polygon(points, fill=(0, 255, 0, 80), outline=(0, 200, 0, 255))
    
    def _draw_players_in_viewport(self, img: Image.Image, viewport: ViewportConfig):
        """Zeichnet Spieler-Tokens im Viewport"""
        if not self.player_manager.players:
            return
        
        center_px, center_py = self._hex_to_pixel(viewport.center_q, viewport.center_r)
        
        for player in self.player_manager.players.values():
            if not player.is_active:
                continue
            
            # Prüfe Sichtbarkeit für dieses Team
            if viewport.team_id:
                # Eigenes Team immer sichtbar
                if player.team_id != viewport.team_id:
                    # Andere Teams nur sichtbar wenn nah genug
                    if not self.player_manager.can_team_see_position(
                        viewport.team_id, player.hex_q, player.hex_r):
                        continue
            
            # Player-Position in Pixeln
            player_px, player_py = self._hex_to_pixel(player.hex_q, player.hex_r)
            
            # Transformiere zu Viewport-Koordinaten
            vx = viewport.width / 2 + (player_px - center_px) * viewport.zoom
            vy = viewport.height / 2 + (player_py - center_py) * viewport.zoom
            
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
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), f"👥 {team.name}", fill=(255, 255, 255), font=font)
        
        # Mitglieder-Anzahl
        members = self.player_manager.get_team_members(team.id)
        member_text = f"{len(members)} Spieler"
        draw.text((viewport.width - 100, 10), member_text, fill=(200, 200, 200), font=font)
    
    # =========================================================
    # MINIMAP
    # =========================================================
    
    def _render_minimap(self) -> Image.Image:
        """Rendert die Minimap mit Boss-Positionen und Spieler-Markierungen"""
        size = self.minimap_size
        minimap = Image.new('RGBA', (size, size), (30, 30, 40, 220))
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
                min_x = min(min_x, cx)
                min_y = min(min_y, cy)
                max_x = max(max_x, cx)
                max_y = max(max_y, cy)
        
        if min_x == float('inf'):
            return minimap
        
        # Skalierung berechnen
        map_width = max_x - min_x + self.hex_size * 2
        map_height = max_y - min_y + self.hex_size * 2
        scale = min(size / map_width, size / map_height) * 0.9
        
        offset_x = (size - map_width * scale) / 2 - min_x * scale
        offset_y = (size - map_height * scale) / 2 - min_y * scale
        
        # Boss-Hexagone zeichnen
        for placement in self.boss_manager.placements:
            coord_key = f"{placement.hex_q},{placement.hex_r}"
            tile_data = tiles.get(coord_key, {})
            
            if isinstance(tile_data, dict):
                cx = tile_data.get("center_x", 0)
                cy = tile_data.get("center_y", 0)
            else:
                cx, cy = self._hex_to_pixel(placement.hex_q, placement.hex_r)
            
            mx = cx * scale + offset_x
            my = cy * scale + offset_y
            
            # Boss-Marker
            marker_size = 6
            if placement.revealed:
                # Enthüllt: Roter Punkt mit "!"
                draw.ellipse([(mx - marker_size, my - marker_size),
                              (mx + marker_size, my + marker_size)],
                             fill=(255, 0, 0), outline=(255, 255, 255))
            else:
                # Nicht enthüllt: Oranger Punkt mit "?"
                draw.ellipse([(mx - marker_size, my - marker_size),
                              (mx + marker_size, my + marker_size)],
                             fill=(255, 140, 0), outline=(255, 200, 0))
        
        # Spieler-/Team-Positionen zeichnen
        for team in self.player_manager.teams.values():
            coord_key = f"{team.hex_q},{team.hex_r}"
            tile_data = tiles.get(coord_key, {})
            
            if isinstance(tile_data, dict):
                cx = tile_data.get("center_x", 0)
                cy = tile_data.get("center_y", 0)
            else:
                cx, cy = self._hex_to_pixel(team.hex_q, team.hex_r)
            
            mx = cx * scale + offset_x
            my = cy * scale + offset_y
            
            # Parse Team-Farbe
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
            
            # Team-Marker (Raute)
            marker_size = 5
            points = [
                (mx, my - marker_size),  # Oben
                (mx + marker_size, my),  # Rechts
                (mx, my + marker_size),  # Unten
                (mx - marker_size, my)   # Links
            ]
            draw.polygon(points, fill=(r, g, b), outline=(255, 255, 255))
        
        # Legende
        try:
            legend_font = ImageFont.truetype("arial.ttf", 9)
        except:
            legend_font = ImageFont.load_default()
        
        draw.text((5, size - 25), "🐉 Boss", fill=(255, 140, 0), font=legend_font)
        draw.text((5, size - 12), "◆ Team", fill=(100, 200, 255), font=legend_font)
        
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
        """Verteilt Spieler auf Spawn-Hexagone"""
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
        
        if spawn_hexes:
            self.player_manager.distribute_players_randomly(spawn_hexes)
            
            # Viewports aktualisieren
            self._update_viewport_centers()
            self.render_all()
    
    def _update_viewport_centers(self):
        """Aktualisiert die Viewport-Zentren basierend auf Team-Positionen"""
        teams = list(self.player_manager.teams.values())
        
        for i, viewport in enumerate(self.viewports):
            if i < len(teams):
                team = teams[i]
                viewport.team_id = team.id
                viewport.team_color = team.color
                viewport.center_q = team.hex_q
                viewport.center_r = team.hex_r


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
