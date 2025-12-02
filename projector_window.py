"""
Projektor-Fenster für "Der Eine Ring"
Zeigt die Karte im Vollbild auf einem zweiten Monitor mit Fog-of-War
Unterstützt JSON-Maps (Tile-basiert) und SVG-Maps (Vektor-basiert)
"""
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import json
import random
import os
import threading
import xml.etree.ElementTree as ET
from fog_texture_generator import FogTextureGenerator
from lighting_system import LightingEngine
from PIL import Image
import numpy as np
from lighting_system import GPUAcceleratedLightingEngine, GPU_AVAILABLE

# Mapping von Hexagon-Terrain-Typen zu Material-Namen des Texture-Managers
HEXAGON_TERRAIN_TO_MATERIAL = {
    'plains': 'grass',
    'forest': 'forest',
    'hills': 'mountain',  # Hügel -> Berge
    'mountains': 'mountain',
    'water': 'water',
    'swamp': 'swamp',
    'desert': 'sand',
    'snow': 'snow',
    'road': 'road',
    'village': 'village',
    'ruins': 'stone',
    'dark_forest': 'forest',  # Düsterwald -> Wald (mit dunkler Tönung)
}

def normalize_terrain_to_material(terrain_name):
    """Konvertiert Hexagon-Terrain-Namen zu Material-Namen für den Texture-Manager"""
    if not isinstance(terrain_name, str):
        return 'grass'
    
    terrain_lower = terrain_name.lower()
    
    # Prüfe ob es ein bekanntes Hexagon-Terrain ist
    if terrain_lower in HEXAGON_TERRAIN_TO_MATERIAL:
        return HEXAGON_TERRAIN_TO_MATERIAL[terrain_lower]
    
    # Fallback: Benutze den Namen direkt (für normale Maps)
    return terrain_lower

class ProjectorWindow(tk.Toplevel):
    """Vollbild-Projektor-Fenster für Spieler mit Fog-of-War"""
    
    def __init__(self, parent, map_data=None, webcam_tracker=None, svg_path=None):
        super().__init__(parent)
        
        self.title("Der Eine Ring - Projektor")
        self.configure(bg="#0a0a0a", cursor="")
        
        # SVG-Modus Detection
        self.is_svg_mode = svg_path is not None
        self.svg_path = svg_path
        self.svg_renderer = None
        self.original_svg_size = None  # Speichere Original-SVG-Größe
        
        if self.is_svg_mode:
            # SVG-Projektor-Modus initialisieren
            from svg_projector import SVGProjectorRenderer
            self.svg_renderer = SVGProjectorRenderer(svg_path)
            self.title("Der Eine Ring - Projektor (SVG)")
            
            # Hole Original-SVG-Größe aus map_data falls vorhanden
            if map_data and "original_svg_size" in map_data:
                self.original_svg_size = map_data["original_svg_size"]
            
            # SVG-spezifisches Caching
            self.svg_static_cache = None  # Gecachte statische Tiles
            self.svg_cache_size = None    # (width, height, zoom) für Invalidierung
            self.svg_animated_materials = set()  # Set von Material-Namen die animiert sind
            
            # SVG-Viewport (für Zoom/Pan)
            self.svg_viewport_x = 0  # Viewport X-Offset in SVG-Koordinaten
            self.svg_viewport_y = 0  # Viewport Y-Offset in SVG-Koordinaten
            self.svg_base_scale = 1.0  # Basis-Skalierung um ganze Map zu zeigen
        
        # NICHT im Vollbild starten - User kann mit F11 wechseln
        self.attributes('-fullscreen', False)
        self.attributes('-topmost', False)
        
        # Normales Fenster mit guter Größe
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # ESC zum Beenden, F11 für Vollbild-Toggle
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<F11>', lambda e: self.toggle_fullscreen())
        
        # Map-Daten
        self.map_data = map_data or {"width": 50, "height": 50, "tiles": []}
        
        # DEBUG: Zeige was wir bekommen haben
        print(f"🎯 ProjectorWindow initialisiert:")
        print(f"   map_data Parameter: {type(map_data)}")
        if map_data:
            print(f"   Map-Größe: {map_data.get('width', '?')}x{map_data.get('height', '?')}")
            print(f"   Map-Name: {map_data.get('name', 'unbenannt')}")
            tiles = map_data.get('tiles', [])
            print(f"   Tiles vorhanden: {len(tiles) if isinstance(tiles, list) else 'dict' if isinstance(tiles, dict) else 'keine'}")
        else:
            print(f"   ⚠️ KEINE map_data übergeben - verwende Default!")
        
        self.river_directions = self.map_data.get("river_directions", {})  # River flow directions
        
        # Fog-of-War System
        from fog_of_war import FogOfWar
        map_width = self.map_data.get("width", 50)
        map_height = self.map_data.get("height", 50)
        self.fog = FogOfWar(map_width, map_height)
        self.fog_enabled = True  # STANDARDMÄSSIG AKTIVIERT
        
        # FOG TEXTURE GENERATOR - Wiederverwendbare Texturen!
        self.fog_texture_gen = FogTextureGenerator()
        self.fog_photo_cache = {}  # Cache für PIL Images (nicht PhotoImage!)
        
        # Map Photo Reference (für das eine große Bild)
        self.map_photo = None
        
        # WICHTIG: Nur Mitte initial aufdecken (5x5 Bereich)
        center_x = map_width // 2
        center_y = map_height // 2
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = center_x + dx, center_y + dy
                if 0 <= nx < map_width and 0 <= ny < map_height:
                    self.fog.revealed[ny][nx] = True
        
        # Webcam-Tracker
        self.webcam_tracker = webcam_tracker
        
        # Kamera-Controller für Auto-Zoom
        from camera_controller import CameraController
        self.camera = CameraController(map_width, map_height)
        
        # GPU-basierte Rendering-Engine (wird an lighting_engine gebunden, siehe weiter unten)
        # Set to None for now — we'll reuse lighting_engine.gpu_renderer after lighting_engine is created
        self.gpu_renderer = None
        
        # GPU SVG Renderer (für zukünftige GPU-SVG-Rendering)
        self.gpu_svg_renderer = None
        
        # LIGHTING SYSTEM für Projektor
        self.lighting_engine = GPUAcceleratedLightingEngine()
        self.lighting_enabled = False  # Standardmäßig aus
        self.lighting_time = 0.0  # Zeit für Flicker-Animation

        # Lade Lighting-Daten aus map_data falls vorhanden
        if map_data and "lighting" in self.map_data:
            lighting_data = self.map_data["lighting"]

            # Lade ALLE Lighting-Einstellungen (Mode, Darkness-Polygone, etc.)
            self.lighting_engine.from_dict(lighting_data)

            # Projektor: Lighting automatisch aktivieren wenn Lichtquellen vorhanden
            if self.lighting_engine.lights:
                self.lighting_enabled = True
            else:
                self.lighting_enabled = lighting_data.get("enabled", False)

            # Konvertiere alte Pixel-Polygone zu Tile-Koordinaten falls nötig
            if self.lighting_engine.darkness_polygons:
                map_width = self.map_data.get("width", 50)
                map_height = self.map_data.get("height", 50)
                converted_polygons = []
                for polygon in self.lighting_engine.darkness_polygons:
                    if polygon:  # not empty
                        max_x = max(p[0] for p in polygon)
                        max_y = max(p[1] for p in polygon)

                        if max_x > map_width or max_y > map_height:
                            # Pixel-Koordinaten - konvertiere zu Tile (angenommen tile_size=24 aus Editor)
                            tile_polygon = [(p[0] / 24.0, p[1] / 24.0) for p in polygon]
                            converted_polygons.append(tile_polygon)
                        else:
                            # Schon Tile-Koordinaten
                            converted_polygons.append(polygon)
                    else:
                        converted_polygons.append(polygon)

                self.lighting_engine.darkness_polygons = converted_polygons

        # Ensure projector uses the same GPURenderer as the lighting engine (if available)
        # This avoids creating two separate GPU contexts and keeps resources consistent.
        if getattr(self.lighting_engine, 'gpu_renderer', None):
            self.gpu_renderer = self.lighting_engine.gpu_renderer
        elif GPU_AVAILABLE:
            # lighting_engine didn't initialize GPU for some reason — try to create one here and attach it
            try:
                from lighting_system import GPURenderer
                self.gpu_renderer = GPURenderer()
                # attach to lighting_engine for shared use
                self.lighting_engine.gpu_renderer = self.gpu_renderer
                self.lighting_engine.gpu_context = self.gpu_renderer.context
                self.lighting_engine.gpu_queue = self.gpu_renderer.queue
                self.lighting_engine.gpu_program = self.gpu_renderer.program
            except Exception as e:
                self.gpu_renderer = None
        
        # Initialize GPU SVG Renderer if GPU is available
        if GPU_AVAILABLE and self.gpu_renderer:
            try:
                from svg_projector import GPUSVGRenderer
                self.gpu_svg_renderer = GPUSVGRenderer()
            except Exception as e:
                self.gpu_svg_renderer = None
        else:
            self.gpu_svg_renderer = None

        # Detail-Map System (für zukünftige Erweiterungen)
        from detail_map_system import DetailMapSystem
        self.detail_system = DetailMapSystem(self.map_data)  # Nutze self.map_data für Konsistenz
        
        self.setup_ui()
        
        # Auto-Switch für Detail-Maps
        self.auto_detail_switch = True
        
        # Warte bis Fenster vollständig initialisiert ist
        self.update_idletasks()
        
        # Bildschirmgröße ermitteln
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Tile-Größe dynamisch berechnen basierend auf Kartengröße und Bildschirm
        map_width = self.map_data.get("width", 50)
        map_height = self.map_data.get("height", 50)
        
        # Berechne Tile-Größe so, dass Karte den ganzen Bildschirm ausfüllt
        tile_width = screen_width / map_width
        tile_height = screen_height / map_height
        
        # Nimm die kleinere Dimension, damit alles passt
        self.tile_size = int(min(tile_width, tile_height))
        self.tile_size = max(self.tile_size, 16)  # Minimum 16px
        
        self.zoom_level = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        
        # Texturen laden
        from texture_manager import TextureManager
        self.texture_manager = TextureManager()
        
        # Animation für Projektor
        self.animation_frame = 0
        self.animation_id = None
        self.is_animating = False  # Startet False, wird aktiviert wenn nötig
        self.has_animated_tiles = False  # Prüfen ob Map animierte Tiles hat
        self.frame_skip_counter = 0  # Für Performance-Optimierung
        
        # WETTER-OVERLAY SYSTEM (animierte GIFs)
        self.weather_overlay_frames = []  # Liste von PIL Images (GIF Frames)
        self.weather_overlay_current = 0  # Aktueller Frame Index
        self.weather_overlay_enabled = False
        self.weather_overlay_opacity = 0.7  # Transparenz (0-1)
        self.weather_overlay_path = None
        
        # GM-KONTROLLIERTES OVERLAY SYSTEM (separates Layer über Map)
        self.overlay_enabled = False  # Vom GM Panel gesteuert
        self.overlay_frames = []  # Original PIL-Frames vom GM Panel
        self.overlay_photos = []  # Fertige PhotoImages (nur Overlay, nicht composited)
        self.overlay_canvas_item = None  # Separates Canvas-Item für Overlay
        self.overlay_prepared = []  # Legacy
        self.overlay_map_cache = None  # Nicht mehr verwendet
        self.overlay_canvas_size = None  # Aktuelle Canvas-Größe
        self.overlay_loading = False  # True während Vorbereitung
        self.overlay_current = 0
        self.overlay_opacity = 0.9  # Höher für bessere Sichtbarkeit
        self.overlay_speed = 1.0  # Playback speed multiplier
        self.overlay_x = 0  # X-Offset
        self.overlay_y = 0  # Y-Offset
        self.overlay_scale = 1.0  # Skalierung
        self.overlay_mode = "tile"  # tile, stretch, center
        self.overlay_animation_id = None  # after() ID für Animation
        self._overlay_photo_ref = None  # Referenz für GC-Schutz
        
        # Karten-Abdunkelung für Wetter-Effekte
        self.darken_map = False  # True = Karte wird abgedunkelt
        self.darken_amount = 0.3  # Stärke der Abdunkelung (0-1)
        self._darken_canvas_item = None  # Canvas-Item für Abdunkelung
        self._darken_photo = None  # PhotoImage Referenz (GC-Schutz)
        self._darken_size = None  # Cached size
        self._darken_amount_cached = None  # Cached amount
        
        # WETTER-PRESETS (Name -> GIF-Pfad)
        self.weather_presets = {}  # Wird beim Laden gefüllt
        self.weather_folder = os.path.join(os.path.dirname(__file__), "weather_overlays")
        self.current_weather = "clear"  # Aktuelles Wetter
        self.load_weather_presets()
        
        # RANDOM WETTER SYSTEM
        self.random_weather_enabled = False
        self.random_weather_interval = (300, 900)  # 5-15 Minuten in Sekunden
        self.random_weather_duration = (60, 180)   # 1-3 Minuten Wetter-Dauer
        self.random_weather_timer = None
        self.random_weather_end_timer = None
        self.random_weather_types = ["rain", "snow", "storm"]  # Welche Wetter können zufällig kommen
        
        # CACHING für statische Map-Teile
        self.static_map_cache = None  # PIL Image der statischen Tiles
        self.static_map_size = None  # (width, height, tile_size) für Cache-Invalidierung
        self.animated_positions = []  # Liste von (x, y) Positionen mit animierten Tiles
        self.canvas_image_id = None  # ID des Canvas-Image-Items (für Update statt Delete)
        
        # Stelle sicher, dass das Fenster vollständig initialisiert und sichtbar ist
        self.update_idletasks()
        self.lift()
        self.focus_force()
        
        try:
            # Warte bis Fenster vollständig initialisiert ist, dann render
            # self.after(100, self.render_map)  # Commented out for immediate rendering
            self.render_map()  # Render immediately
        except Exception as e:
            import traceback
            traceback.print_exc()
        
        # Prüfe ob Animation gebraucht wird
        if self.is_svg_mode:
            # SVG: Prüfe SVG-Daten auf animierte Materialien
            self.check_svg_for_animations()
        else:
            # JSON: Normale Tile-Prüfung
            self.check_for_animated_tiles()
        
        # Prüfe ob Lichtquellen mit Flacker-Animation existieren
        # WICHTIG: Prüfe auch wenn lighting_enabled False ist, denn flackernde Lichter aktivieren Animation!
        if self.lighting_engine.lights:
            for light in self.lighting_engine.lights:
                if light.flicker and light.flicker != "none":
                    self.has_animated_tiles = True
                    # Aktiviere Lighting automatisch wenn flackernde Lichter vorhanden
                    if not self.lighting_enabled:
                        self.lighting_enabled = True
                    break
        
        if self.has_animated_tiles:
            self.start_animation()  # Nur starten wenn nötig
        else:
            pass
    def gpu_composite_rendering(self, map_image, lighting_overlay, fog_enabled=False, fog_data=None, mode='alpha'):
        """GPU-basiertes Compositing aller Rendering-Layer"""
        # Prefer shared GPU renderer (lighting_engine.gpu_renderer) if available
        gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
        if not gpu:
            # Fallback zur CPU-Version
            return self.cpu_composite_rendering(map_image, lighting_overlay, fog_enabled, fog_data)
        
        try:
            # Ensure overlay is same size as map before uploading
            if lighting_overlay.size != map_image.size:
                lighting_overlay = lighting_overlay.resize(map_image.size, Image.LANCZOS)

            # Konvertiere alle Images zu GPU-Images
            gpu_map = gpu.create_gpu_image(map_image.width, map_image.height, 4)
            gpu_map.gpu_buffer.set(np.array(map_image.convert('RGBA'), dtype=np.float32) / 255.0)

            gpu_lighting = gpu.create_gpu_image(lighting_overlay.width, lighting_overlay.height, 4)
            gpu_lighting.gpu_buffer.set(np.array(lighting_overlay.convert('RGBA'), dtype=np.float32) / 255.0)

            # Two modes supported: 'alpha' or 'multiply'
            if mode == 'alpha':
                # Alpha-Compositing auf GPU
                result_gpu = gpu.alpha_composite_gpu(gpu_map, gpu_lighting)
                final_pil = result_gpu.to_pil_image()

            elif mode == 'multiply':
                # Multiply on GPU: darkened = map * lighting_rgb (per-channel)
                darkened_gpu = gpu.multiply_blend_gpu(gpu_map, gpu_lighting)
                darkened_pil = darkened_gpu.to_pil_image()

                # Use lighting alpha as mask: where alpha strong -> use darkened, else keep original
                lighting_alpha = lighting_overlay.split()[3]
                final_pil = Image.composite(darkened_pil.convert('RGBA'), map_image.convert('RGBA'), lighting_alpha)

            else:
                return self.cpu_composite_rendering(map_image, lighting_overlay, fog_enabled, fog_data)

            # Fog hinzufügen (falls aktiviert) — do fog on PIL side
            if fog_enabled and fog_data:
                final_pil = Image.alpha_composite(final_pil.convert('RGBA'), fog_data.convert('RGBA'))

            return final_pil
            
        except Exception as e:
            return self.cpu_composite_rendering(map_image, lighting_overlay, fog_enabled, fog_data)
    
    def cpu_composite_rendering(self, map_image, lighting_overlay, fog_enabled=False, fog_data=None):
        """CPU-Fallback für Compositing"""
        result = Image.alpha_composite(map_image.convert('RGBA'), lighting_overlay.convert('RGBA'))
        
        if fog_enabled and fog_data:
            result = Image.alpha_composite(result, fog_data.convert('RGBA'))
        
        return result
        
    def setup_ui(self):
        """UI-Elemente erstellen"""
        try:
            # Hauptframe
            main_frame = tk.Frame(self, bg="#0a0a0a")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Control-Bar oben (schwebend, transparent)
            self.control_bar = tk.Frame(self, bg="#1a1a1a", height=40)
            self.control_bar.place(x=10, y=10, width=300, height=40)
            
            # Fog Toggle Button
            self.fog_toggle_btn = tk.Button(self.control_bar, text="🌫️ Nebel: AN",
                                           command=self.toggle_fog_ui,
                                           bg="#4a4a4a", fg="#00ff00",
                                           activebackground="#6a6a6a",
                                           font=("Arial", 11, "bold"),
                                           relief=tk.RAISED, bd=2)
            self.fog_toggle_btn.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True)
            
            # Info-Button (zeigt/versteckt Control-Bar)
            info_btn = tk.Button(self.control_bar, text="ℹ️",
                                command=self.toggle_controls,
                                bg="#3a3a3a", fg="white",
                                font=("Arial", 10, "bold"),
                                relief=tk.RAISED, bd=2, width=3)
            info_btn.pack(side=tk.RIGHT, padx=5, pady=5)
            
            # Wetter-Overlay Button
            self.weather_btn = tk.Button(self.control_bar, text="🌧️",
                                command=self.open_weather_dialog,
                                bg="#3a3a3a", fg="white",
                                font=("Arial", 10, "bold"),
                                relief=tk.RAISED, bd=2, width=3)
            self.weather_btn.pack(side=tk.RIGHT, padx=2, pady=5)
            
            # Control-Bar nach 5 Sekunden ausblenden
            self.control_visible = True
            self.after(5000, lambda: self.hide_controls())
            
            # Canvas für die Karte
            self.canvas = Canvas(main_frame, bg="#0a0a0a", 
                                highlightthickness=0, cursor="")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            # Scrollbars (versteckt, aber funktional)
            self.h_scroll = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, 
                                         command=self.canvas.xview)
            self.v_scroll = tk.Scrollbar(main_frame, orient=tk.VERTICAL, 
                                         command=self.canvas.yview)
            
            self.canvas.configure(xscrollcommand=self.h_scroll.set, 
                                 yscrollcommand=self.v_scroll.set)
            
            # Kamera-Steuerung
            self.canvas.bind('<Button-1>', self.start_pan)
            self.canvas.bind('<B1-Motion>', self.pan)
            self.canvas.bind('<MouseWheel>', self.zoom)
            self.canvas.bind('<Button-3>', self.toggle_detail_view)  # Rechtsklick für Detail-Toggle
            
            self.pan_start_x = 0
            self.pan_start_y = 0
            
            # Info-Text (kann ausgeblendet werden)
            self.info_label = tk.Label(self, text="ESC = Beenden | F11 = Vollbild | W = Wetter-Overlay | Rechtsklick = Detail", 
                                       bg="#0a0a0a", fg="#666666", 
                                       font=("Arial", 10))
            self.info_label.place(x=10, y=10)
            
            # Tastaturkürzel für Wetter
            self.bind('<w>', lambda e: self.open_weather_dialog())
            self.bind('<W>', lambda e: self.toggle_weather_overlay())
            
            # Info nach 3 Sekunden ausblenden
            self.after(3000, lambda: self.info_label.place_forget())
        except Exception as e:
            import traceback
            traceback.print_exc()
        
    def render_map(self):
        """
        Karte auf dem Canvas rendern - OPTIMIERT MIT CACHING!
        Unterstützt sowohl JSON-Maps (Tile-basiert) als auch SVG-Maps (Vektor-basiert)
        """
        # If UI not yet created, schedule a retry
        if not hasattr(self, 'canvas'):
            # try again shortly after UI finishes initializing
            self.after(100, self.render_map)
            return

        # SVG-Modus: Delegiere an SVG-Renderer
        if self.is_svg_mode:
            self.render_svg_map()
            return
        
        # JSON-Modus: Normale Tile-Rendering
        # Sicherheitscheck: Ist das Fenster noch vorhanden?
        try:
            if not self.winfo_exists():
                return
        except:
            return
        
        # Canvas-Hintergrund schwarz setzen (nur einmal nötig)
        if not self.canvas_image_id:
            self.canvas.configure(bg="#0a0a0a")
        
        # Aktuelle Karte (kann Base oder Detail sein)
        current_map = self.detail_system.get_current_map()
        
        width = current_map.get("width", 50)
        height = current_map.get("height", 50)
        tiles = current_map.get("tiles", [])
        
        # DEBUG: Zeige detaillierte Map-Info (nur einmal beim ersten Render)
        if not hasattr(self, '_render_debug_shown'):
            self._render_debug_shown = True
            print(f"🗺️ render_map DEBUG:")
            print(f"   Map-Name: {current_map.get('name', 'unbenannt')}")
            print(f"   Größe: {width}x{height}")
            print(f"   tiles type={type(tiles).__name__}, len={len(tiles) if isinstance(tiles, (list, dict)) else 0}")
            if isinstance(tiles, list) and len(tiles) > 0:
                print(f"   Erste Zeile: {tiles[0][:5] if len(tiles[0]) >= 5 else tiles[0]}...")
            elif isinstance(tiles, dict) and len(tiles) > 0:
                first_keys = list(tiles.keys())[:5]
                print(f"   Erste Keys: {first_keys}")
        
        # Tiles-Format erkennen: Liste (2D-Array) oder Dictionary
        tiles_is_dict = isinstance(tiles, dict)
        
        # Wenn tiles leer ist UND kein Dict, erstelle leere Karte
        if not tiles and not tiles_is_dict:
            tiles = [["grass" for _ in range(width)] for _ in range(height)]
            print(f"   ⚠️ Keine Tiles - erstelle Default grass-Map")
        
        # Canvas-Größe ermitteln für Zentrierung
        try:
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
        except:
            # Canvas wurde zerstört
            return
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.after(500, self.render_map)
            return
        
        # Tile-Größe für aktuellen Zoom berechnen (aber begrenzen)
        current_tile_size = int(self.tile_size * self.zoom_level)
        current_tile_size = max(8, min(current_tile_size, 64))  # Zwischen 8 und 64 Pixel
        
        # Kamera-Controller updaten (für Auto-Zoom)
        self.camera.update(canvas_width, canvas_height)
        
        # Zoom von Kamera übernehmen wenn Auto-Zoom aktiv
        if self.camera.is_auto_zoom_enabled():
            self.zoom_level = self.camera.get_zoom()
            current_tile_size = int(self.tile_size * self.zoom_level)
            current_tile_size = max(8, min(current_tile_size, 64))
        
        # Karten-Gesamtgröße berechnen
        total_map_width = width * current_tile_size
        total_map_height = height * current_tile_size
        
        # Cache-Schlüssel prüfen
        cache_key = (width, height, current_tile_size)
        cache_invalid = self.static_map_cache is None or self.static_map_size != cache_key
        
        # STATISCHE MAP CACHEN (einmalig oder bei Größenänderung)
        if cache_invalid:
            self.static_map_cache = Image.new('RGB', (total_map_width, total_map_height), (10, 10, 10))
            self.static_map_size = cache_key
            
            # Rendere ALLE Tiles einmalig (mit Frame 0 für Animationen)
            for y in range(height):
                for x in range(width):
                    paste_x = x * current_tile_size
                    paste_y = y * current_tile_size
                    
                    # Tile-Zugriff: Unterstütze sowohl Dict als auch 2D-Liste
                    if tiles_is_dict:
                        # Dictionary-Format: "x,y" -> terrain oder Hexagon-Tile-Dict
                        coord_key = f"{x},{y}"
                        tile_data = tiles.get(coord_key, "grass")
                        
                        # Hexagon-Map: tile_data ist ein Dict mit 'terrain', 'fill_color', etc.
                        if isinstance(tile_data, dict):
                            terrain = tile_data.get('terrain', 'PLAINS')
                            # Konvertiere Hexagon-Terrain zu Material-Name
                            terrain = normalize_terrain_to_material(terrain)
                        else:
                            # Normales String-Format
                            terrain = tile_data
                    elif isinstance(tiles, list) and y < len(tiles) and isinstance(tiles[y], list) and x < len(tiles[y]):
                        terrain = tiles[y][x]
                    else:
                        terrain = "grass"
                    
                    # River direction lookup für water tiles
                    river_direction = "right"  # Default
                    if terrain == "water":
                        coord_key = f"{x},{y}"
                        river_direction = self.river_directions.get(coord_key, "right")
                    
                    # Statisches Tile rendern (Frame 0)
                    if hasattr(self.texture_manager, 'advanced_renderer') and self.texture_manager.advanced_renderer:
                        texture_img = self.texture_manager.advanced_renderer.get_texture(
                            terrain, current_tile_size, 0, river_direction  # Frame 0 für Cache!
                        )
                    else:
                        texture_img = self.texture_manager.get_texture(terrain, current_tile_size)
                    
                    if texture_img:
                        # SPECIAL: Village gibt größeres Bild zurück für Overlap
                        if terrain == 'village' and texture_img.size[0] > current_tile_size:
                            if texture_img.mode == 'RGBA':
                                offset_x = paste_x
                                offset_y = paste_y - int(current_tile_size * 2)  # 2 Tiles nach oben
                                self.static_map_cache.paste(texture_img, (offset_x, offset_y), texture_img)
                            else:
                                texture_img = texture_img.convert('RGB')
                                self.static_map_cache.paste(texture_img, (paste_x, paste_y))
                        else:
                            if texture_img.mode != 'RGB':
                                texture_img = texture_img.convert('RGB')
                            self.static_map_cache.paste(texture_img, (paste_x, paste_y))
        
        # Kopiere statischen Cache als Basis
        map_image = self.static_map_cache.copy()
        
        # NUR ANIMIERTE TILES neu rendern (wenn Animation läuft)
        if self.is_animating and self.animated_positions:
            for x, y, material in self.animated_positions:
                paste_x = x * current_tile_size
                paste_y = y * current_tile_size
                
                # River direction lookup für water tiles
                river_direction = "right"  # Default
                if material == "water":
                    coord_key = f"{x},{y}"
                    river_direction = self.river_directions.get(coord_key, "right")
                
                # Animiertes Tile mit aktuellem Frame rendern
                if hasattr(self.texture_manager, 'advanced_renderer') and self.texture_manager.advanced_renderer:
                    texture_img = self.texture_manager.advanced_renderer.get_texture(
                        material, current_tile_size, self.animation_frame, river_direction
                    )
                    
                    if texture_img:
                        # SPECIAL: Village gibt größeres Bild zurück (3x) für Rauch über 2-3 Tiles
                        if material == 'village' and texture_img.size[0] > current_tile_size:
                            # Nutze Alpha-Channel für korrektes Overlapping
                            if texture_img.mode == 'RGBA':
                                # Gebäude am UNTEREN Rand ausrichten
                                # Rauch ragt 2 Tiles nach oben (3x size - 1x tile = 2 tiles overlap)
                                offset_x = paste_x
                                offset_y = paste_y - int(current_tile_size * 2)  # 2 Tiles nach oben!
                                map_image.paste(texture_img, (offset_x, offset_y), texture_img)
                            else:
                                texture_img = texture_img.convert('RGB')
                                map_image.paste(texture_img, (paste_x, paste_y))
                        else:
                            if texture_img.mode != 'RGB':
                                texture_img = texture_img.convert('RGB')
                            map_image.paste(texture_img, (paste_x, paste_y))
        
        # Lighting-Overlay rendern (NACH Tiles, VOR Fog!)
        if self.lighting_enabled and (self.lighting_engine.lights or (self.lighting_engine.lighting_mode == "day" and self.lighting_engine.darkness_polygons)):
            # Konvertiere zu RGBA für Transparenz
            if map_image.mode != 'RGBA':
                map_image = map_image.convert('RGBA')
            
            # Lighting rendern mit Animation
            # Berechne Radius-Skalierung für JSON-Modus
            radius_scale = current_tile_size / 25.0
            
            lighting_overlay = self.lighting_engine.render_lighting(
                width=width,
                height=height,
                tile_size=current_tile_size,
                time_offset=self.lighting_time,  # Für Flacker-Animation!
                radius_scale=radius_scale
            )
            
            # WICHTIG: Map muss RGBA sein!
            if map_image.mode != 'RGBA':
                map_image = map_image.convert('RGBA')
            
            # ═══════════════════════════════════════════════════════════
            # TAG-MODUS: MULTIPLY-BLEND für physikalisch korrekte Schatten
            # ═══════════════════════════════════════════════════════════
            if self.lighting_engine.lighting_mode == "day" and self.lighting_engine.darkness_polygons:
                
                # Separiere RGB und Alpha aus dem Lighting-Overlay
                lighting_rgb = lighting_overlay.convert('RGB')
                lighting_alpha = lighting_overlay.split()[3]  # Alpha-Kanal
                
                # MULTIPLY-BLEND: Multipliziere Map-RGB mit Lighting-RGB
                # Formula: result = (map * lighting) / 255
                # Dies verdunkelt die Map wo lighting dunkel ist
                from PIL import ImageChops
                
                # Konvertiere Map zu RGB für Multiply
                map_rgb = map_image.convert('RGB')
                
                # If GPU is available and we have a shared renderer, prefer GPU path
                gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
                if gpu:
                    try:
                        map_image = self.gpu_composite_rendering(map_image, lighting_overlay, fog_enabled=False, fog_data=None, mode='multiply')
                    except Exception as e:
                        darkened_map = ImageChops.multiply(map_rgb, lighting_rgb)
                        darkened_map = darkened_map.convert('RGBA')
                        map_image = Image.composite(darkened_map, map_image, lighting_alpha)
                else:
                    # Multiply: Verdunkelt die Map (wie echte Schatten)
                    darkened_map = ImageChops.multiply(map_rgb, lighting_rgb)
                    # Konvertiere zurück zu RGBA
                    darkened_map = darkened_map.convert('RGBA')
                    # Wende Multiply nur in Polygon-Bereichen an (mit Alpha-Maske)
                    map_image = Image.composite(darkened_map, map_image, lighting_alpha)
                
            else:
                # NACHT-MODUS oder keine Polygone: Normales Alpha-Composite
                gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
                if gpu:
                    try:
                        map_image = self.gpu_composite_rendering(map_image, lighting_overlay, fog_enabled=False, fog_data=None, mode='alpha')
                    except Exception as e:
                        map_image = Image.alpha_composite(map_image, lighting_overlay)
                else:
                    map_image = Image.alpha_composite(map_image, lighting_overlay)
            
            # Zurück zu RGB für Fog-Rendering
            map_image = map_image.convert('RGB')
        
        # === WETTER-OVERLAY (nach Lighting, vor Fog) ===
        # Altes Weather-System (falls verwendet)
        if self.weather_overlay_enabled and self.weather_overlay_frames:
            weather_frame = self.get_weather_overlay_frame((map_image.width, map_image.height))
            if weather_frame:
                if map_image.mode != 'RGBA':
                    map_image = map_image.convert('RGBA')
                map_image = Image.alpha_composite(map_image, weather_frame)
                map_image = map_image.convert('RGB')
        
        # HINWEIS: GM-Overlay wird jetzt als separates Canvas-Layer angezeigt
        # (siehe overlay_canvas_id und _animate_overlay_fast)
        # Kein Compositing mehr nötig hier - viel performanter!
        
        # Fog-of-War über alles zeichnen
        if self.fog_enabled:
            for y in range(height):
                for x in range(width):
                    if not self.fog.is_revealed(x, y):
                        paste_x = x * current_tile_size
                        paste_y = y * current_tile_size
                        
                        # Fog-Textur holen (gecacht)
                        if current_tile_size not in self.fog_photo_cache:
                            fog_texture = self.fog_texture_gen.get_fog_texture(current_tile_size, "normal")
                            self.fog_photo_cache[current_tile_size] = fog_texture
                        else:
                            fog_texture = self.fog_photo_cache[current_tile_size]
                        
                        # Fog direkt aufs Map-Bild pasten
                        if fog_texture.mode == 'RGBA':
                            map_image.paste(fog_texture, (paste_x, paste_y), fog_texture)
                        else:
                            map_image.paste(fog_texture, (paste_x, paste_y))
        
        # JETZT erst: Konvertiere das EINE große Bild zu PhotoImage
        # Offset für Zentrierung + Pan-Offset
        offset_x = max(0, (canvas_width - total_map_width) // 2) + self.pan_offset_x
        offset_y = max(0, (canvas_height - total_map_height) // 2) + self.pan_offset_y
        
        self.map_photo = ImageTk.PhotoImage(map_image)
        
        # UPDATE statt DELETE+CREATE = kein Flackern!
        if self.canvas_image_id is None:
            # Erstes Mal: Image erstellen
            self.canvas_image_id = self.canvas.create_image(
                offset_x, offset_y, 
                image=self.map_photo, 
                anchor=tk.NW, 
                tags="map"
            )
        else:
            # Nachfolgende Male: Nur Image aktualisieren
            self.canvas.itemconfig(self.canvas_image_id, image=self.map_photo)
            self.canvas.coords(self.canvas_image_id, offset_x, offset_y)
        
        # === KARTEN-ABDUNKELUNG (für Wetter-Effekte) ===
        self._update_darken_layer(canvas_width, canvas_height)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def center_view(self):
        """Karte zentrieren und skalieren für Fullscreen"""
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        bbox = self.canvas.bbox("all")
        if bbox and canvas_width > 1 and canvas_height > 1:
            map_width = bbox[2] - bbox[0]
            map_height = bbox[3] - bbox[1]
            
            # Wenn Karte kleiner als Canvas, zentrieren
            if map_width < canvas_width and map_height < canvas_height:
                x_offset = (canvas_width - map_width) / 2
                y_offset = (canvas_height - map_height) / 2
                self.canvas.move("all", x_offset, y_offset)
            else:
                # Sonst normal zentrieren
                x_center = max(0, (map_width - canvas_width) / 2 / map_width) if map_width > 0 else 0
                y_center = max(0, (map_height - canvas_height) / 2 / map_height) if map_height > 0 else 0
                
                self.canvas.xview_moveto(x_center)
                self.canvas.yview_moveto(y_center)
    
    def start_pan(self, event):
        """Pan-Bewegung starten"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def pan(self, event):
        """Karte/Viewport verschieben"""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        if self.is_svg_mode:
            # SVG: Verschiebe Viewport (negativ weil wir View bewegen, nicht Bild)
            self.svg_viewport_x -= dx
            self.svg_viewport_y -= dy
            self.render_map()
        else:
            # JSON: Auch mit Offset-System für Zoom-Kompatibilität
            self.pan_offset_x += dx
            self.pan_offset_y += dy
            self.render_map()
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def zoom(self, event):
        """Zoom mit Mausrad"""
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level *= 0.9
        
        self.zoom_level = max(0.5, min(5.0, self.zoom_level))  # Max 5x Zoom
        self.render_map()
    
    def toggle_fullscreen(self):
        """Vollbild ein/ausschalten"""
        current = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current)
    
    # ==================== WETTER-OVERLAY SYSTEM ====================
    
    def load_weather_overlay(self, gif_path: str):
        """Lade ein animiertes GIF als Wetter-Overlay"""
        from PIL import Image
        
        try:
            gif = Image.open(gif_path)
            self.weather_overlay_frames = []
            self.weather_overlay_path = gif_path
            
            # Extrahiere alle Frames
            frame_count = 0
            try:
                while True:
                    # Konvertiere zu RGBA
                    frame = gif.copy().convert('RGBA')
                    self.weather_overlay_frames.append(frame)
                    frame_count += 1
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass
            
            if frame_count > 0:
                self.weather_overlay_enabled = True
                self.weather_overlay_current = 0
                # Aktiviere Animation wenn nicht schon aktiv
                if not self.is_animating:
                    self.has_animated_tiles = True
                    self.start_animation()
                print(f"🌧️ Wetter-Overlay geladen: {gif_path} ({frame_count} Frames)")
                return True
            else:
                print(f"⚠️ Keine Frames in GIF gefunden: {gif_path}")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Laden des Wetter-Overlays: {e}")
            return False
    
    def set_weather_overlay_opacity(self, opacity: float):
        """Setze Transparenz des Wetter-Overlays (0.0 - 1.0)"""
        self.weather_overlay_opacity = max(0.0, min(1.0, opacity))
        self.render_map()
    
    def toggle_weather_overlay(self):
        """Wetter-Overlay ein/ausschalten"""
        if self.weather_overlay_frames:
            self.weather_overlay_enabled = not self.weather_overlay_enabled
            self.render_map()
            return self.weather_overlay_enabled
        return False
    
    def clear_weather_overlay(self):
        """Entferne Wetter-Overlay"""
        self.weather_overlay_frames = []
        self.weather_overlay_enabled = False
        self.weather_overlay_current = 0
        self.weather_overlay_path = None
        self.render_map()
    
    def open_weather_dialog(self):
        """Öffne Dialog zum Laden eines Wetter-Overlay GIFs"""
        from tkinter import filedialog, simpledialog
        
        # Wenn bereits ein Overlay geladen ist, frage ob neues laden oder ausschalten
        if self.weather_overlay_frames:
            from tkinter import messagebox
            result = messagebox.askyesnocancel(
                "Wetter-Overlay",
                f"Aktuelles Overlay: {os.path.basename(self.weather_overlay_path or 'Unbekannt')}\n"
                f"Status: {'AN' if self.weather_overlay_enabled else 'AUS'}\n\n"
                "Ja = Neues GIF laden\n"
                "Nein = Overlay ein/ausschalten\n"
                "Abbrechen = Nichts tun"
            )
            
            if result is None:  # Abbrechen
                return
            elif result is False:  # Nein = Toggle
                self.toggle_weather_overlay()
                status = "AN" if self.weather_overlay_enabled else "AUS"
                print(f"🌧️ Wetter-Overlay: {status}")
                return
            # result is True = Ja, neues laden (weiter unten)
        
        # Datei-Dialog für GIF
        gif_path = filedialog.askopenfilename(
            title="Wetter-Overlay GIF auswählen",
            filetypes=[
                ("GIF Animationen", "*.gif"),
                ("Alle Bilddateien", "*.gif;*.png;*.apng"),
                ("Alle Dateien", "*.*")
            ]
        )
        
        if gif_path:
            if self.load_weather_overlay(gif_path):
                # Frage nach Transparenz
                try:
                    opacity = simpledialog.askfloat(
                        "Overlay Transparenz",
                        "Transparenz (0.0 = unsichtbar, 1.0 = voll sichtbar):",
                        initialvalue=0.7,
                        minvalue=0.0,
                        maxvalue=1.0
                    )
                    if opacity is not None:
                        self.set_weather_overlay_opacity(opacity)
                except:
                    pass
                
                self.render_map()
    
    def get_weather_overlay_frame(self, target_size: tuple) -> 'Image':
        """Hole aktuellen Wetter-Overlay Frame, skaliert auf Zielgröße"""
        from PIL import Image
        
        if not self.weather_overlay_frames or not self.weather_overlay_enabled:
            return None
        
        # Aktuellen Frame holen
        frame = self.weather_overlay_frames[self.weather_overlay_current]
        
        # Auf Zielgröße skalieren (tile pattern)
        frame_w, frame_h = frame.size
        target_w, target_h = target_size
        
        # Wenn Frame kleiner als Ziel: Kacheln
        if frame_w < target_w or frame_h < target_h:
            tiled = Image.new('RGBA', target_size, (0, 0, 0, 0))
            for y in range(0, target_h, frame_h):
                for x in range(0, target_w, frame_w):
                    tiled.paste(frame, (x, y))
            result = tiled
        else:
            # Sonst: Skalieren
            result = frame.resize(target_size, Image.Resampling.LANCZOS)
        
        # Opacity anwenden
        if self.weather_overlay_opacity < 1.0:
            # Alpha-Kanal modifizieren
            r, g, b, a = result.split()
            a = a.point(lambda x: int(x * self.weather_overlay_opacity))
            result = Image.merge('RGBA', (r, g, b, a))
        
        return result
    
    def advance_weather_frame(self):
        """Zum nächsten Wetter-Overlay Frame wechseln"""
        if self.weather_overlay_frames and self.weather_overlay_enabled:
            self.weather_overlay_current = (self.weather_overlay_current + 1) % len(self.weather_overlay_frames)
        # Auch GM-Overlay Frame weiterschauen
        if self.overlay_frames and self.overlay_enabled:
            self.overlay_current = (self.overlay_current + 1) % len(self.overlay_frames)
    
    # ============================================================
    # KARTEN-ABDUNKELUNG (für Wetter-Effekte)
    # ============================================================
    
    def _update_darken_layer(self, canvas_width, canvas_height):
        """Aktualisiert oder erstellt ein echtes halbtransparentes Abdunkelungs-Bild über der Karte"""
        from PIL import Image, ImageTk
        
        if self.darken_map and self.overlay_enabled:
            # Prüfe ob Größe sich geändert hat oder neu erstellt werden muss
            need_recreate = (
                self._darken_canvas_item is None or
                not hasattr(self, '_darken_size') or
                self._darken_size != (canvas_width, canvas_height) or
                not hasattr(self, '_darken_amount_cached') or
                self._darken_amount_cached != self.darken_amount
            )
            
            if need_recreate:
                # Erstelle echtes halbtransparentes schwarzes Bild
                # Alpha = darken_amount * 255 (z.B. 0.3 = 76 Alpha)
                alpha = int(self.darken_amount * 255)
                
                # Erstelle RGBA-Bild mit schwarzer Farbe und variablem Alpha
                darken_img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, alpha))
                
                # Konvertiere zu PhotoImage
                self._darken_photo = ImageTk.PhotoImage(darken_img)
                self._darken_size = (canvas_width, canvas_height)
                self._darken_amount_cached = self.darken_amount
                
                # Erstelle oder aktualisiere Canvas-Item
                if self._darken_canvas_item is None:
                    self._darken_canvas_item = self.canvas.create_image(
                        0, 0,
                        image=self._darken_photo,
                        anchor='nw',
                        tags="darken_layer"
                    )
                else:
                    self.canvas.itemconfig(self._darken_canvas_item, image=self._darken_photo)
                
                # Stelle sicher, dass es über der Map aber unter dem Overlay liegt
                self.canvas.tag_raise("darken_layer", "map")
                
            # Nach Overlay positionieren (Overlay soll ÜBER Abdunkelung sein)
            if self.overlay_canvas_item:
                self.canvas.tag_raise("overlay", "darken_layer")
        else:
            # Abdunkelung deaktiviert - entferne Layer falls vorhanden
            if self._darken_canvas_item is not None:
                try:
                    self.canvas.delete(self._darken_canvas_item)
                except:
                    pass
                self._darken_canvas_item = None
                self._darken_photo = None
    
    # ============================================================
    # GM-KONTROLLIERTES OVERLAY SYSTEM
    # ============================================================
    
    def set_overlay_frames(self, frames):
        """Setze Overlay-Frames vom GM Panel"""
        self.overlay_frames = frames
        self.overlay_current = 0
        if frames:
            print(f"🎬 GM-Overlay: {len(frames)} Frames gesetzt")
            # Aktiviere Overlay automatisch wenn Frames gesetzt werden
            self.overlay_enabled = True
            # Starte Overlay-Animation
            self.start_overlay_animation()
        else:
            print("🎬 GM-Overlay: Gelöscht")
            self.stop_overlay_animation()
    
    def start_overlay_animation(self):
        """Startet die Overlay-Animation als SEPARATES Layer über der Map"""
        if not self.overlay_frames:
            return
        
        # Stoppe vorherige Animation
        if self.overlay_animation_id:
            self.after_cancel(self.overlay_animation_id)
            self.overlay_animation_id = None
        
        # Canvas-Größe ermitteln
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w, canvas_h = 800, 600
        
        self.overlay_canvas_size = (canvas_w, canvas_h)
        
        total_frames = len(self.overlay_frames)
        
        # SMOOTH LOOP STRATEGIE:
        # 1. Überspringe die ersten 30% (Anfang des Regenfalls)
        # 2. Überspringe die letzten 10% (Ende kann auch Artefakte haben)
        # 3. Nutze den mittleren Teil und erstelle Cross-Fade am Loop-Punkt
        skip_start = int(total_frames * 0.30)  # Erste 30% überspringen (Regenfall-Start)
        skip_end = int(total_frames * 0.10)    # Letzte 10% überspringen (End-Artefakte)
        
        # Frames aus dem mittleren Bereich
        end_idx = total_frames - skip_end if skip_end > 0 else total_frames
        loop_frames = self.overlay_frames[skip_start:end_idx]
        
        if len(loop_frames) < 20:
            loop_frames = self.overlay_frames  # Fallback
            skip_start = 0
        
        print(f"🎬 Bereite {len(loop_frames)} Frames vor (überspringe erste {skip_start} Anfangs-Frames)...")
        
        # Cross-Fade für nahtlosen Loop: 
        # Die letzten N Frames werden mit den ersten N Frames überblendet
        fade_frames = min(15, len(loop_frames) // 4)  # 15 Frames oder 25% 
        
        # Bereite Frames vor
        prepared_frames = []
        for i, frame in enumerate(loop_frames):
            if frame.mode != 'RGBA':
                frame = frame.convert('RGBA')
            if frame.size != (canvas_w, canvas_h):
                frame = frame.resize((canvas_w, canvas_h), Image.Resampling.BILINEAR)
            
            # Opacity anwenden
            if self.overlay_opacity < 1.0:
                r, g, b, a = frame.split()
                a = a.point(lambda x: int(x * self.overlay_opacity))
                frame = Image.merge('RGBA', (r, g, b, a))
            
            prepared_frames.append(frame)
        
        # Cross-Fade am Loop-Punkt erstellen
        # Ersetze die letzten fade_frames mit Überblendung zu den ersten
        for i in range(fade_frames):
            # Blend-Faktor: 0.0 am Anfang (100% aktueller Frame), 1.0 am Ende (100% erster Frame)
            alpha = i / fade_frames
            
            # Index vom Ende
            end_idx = len(prepared_frames) - fade_frames + i
            # Index vom Anfang
            start_idx = i
            
            if end_idx < len(prepared_frames) and start_idx < len(prepared_frames):
                # Überblende: aktueller End-Frame mit Start-Frame
                end_frame = prepared_frames[end_idx]
                start_frame = prepared_frames[start_idx]
                
                # PIL blend: result = frame1 * (1 - alpha) + frame2 * alpha
                blended = Image.blend(end_frame, start_frame, alpha)
                prepared_frames[end_idx] = blended
        
        print(f"✅ Cross-Fade erstellt ({fade_frames} Frames)")
        
        # Zu PhotoImages konvertieren
        self.overlay_photos = []
        for frame in prepared_frames:
            photo = ImageTk.PhotoImage(frame)
            self.overlay_photos.append(photo)
        
        print(f"✅ {len(self.overlay_photos)} PhotoImages bereit - starte Animation")
        
        # Erstelle separates Canvas-Item für Overlay
        if not hasattr(self, 'overlay_canvas_item') or not self.overlay_canvas_item:
            self.overlay_canvas_item = self.canvas.create_image(
                0, 0, anchor='nw', tags='overlay_anim'
            )
        
        # Animation starten
        self.overlay_current = 0
        self.overlay_loading = False
        self._animate_overlay_fast()
    
    def _prepare_single_frame(self, idx, canvas_w, canvas_h):
        """Nicht mehr verwendet - alles wird in start_overlay_animation gemacht"""
        pass
    
    def _cache_map_for_overlay(self):
        """Cached die aktuelle Map für schnelles Overlay-Compositing"""
        # Hole aktuelle Map-Größe
        canvas_w, canvas_h = self.overlay_canvas_size or (800, 600)
        
        # Für SVG-Maps: Nutze den gecachten static cache
        if self.is_svg_mode and hasattr(self, 'svg_static_cache') and self.svg_static_cache:
            # Crop auf Canvas-Größe (wie in render_svg_map)
            self.overlay_map_cache = self.svg_static_cache.copy()
            if self.overlay_map_cache.size != (canvas_w, canvas_h):
                # Resize auf Canvas-Größe
                self.overlay_map_cache = self.overlay_map_cache.resize(
                    (canvas_w, canvas_h), Image.Resampling.BILINEAR
                )
        else:
            # Für Tile-Maps: Nutze static_map_cache
            if hasattr(self, 'static_map_cache') and self.static_map_cache:
                self.overlay_map_cache = self.static_map_cache.copy()
                if self.overlay_map_cache.size != (canvas_w, canvas_h):
                    self.overlay_map_cache = self.overlay_map_cache.resize(
                        (canvas_w, canvas_h), Image.Resampling.BILINEAR
                    )
            else:
                self.overlay_map_cache = None
    
    def _prepare_overlay_frame(self, idx, canvas_w, canvas_h):
        """Legacy - nicht mehr verwendet"""
        pass
    
    def _animate_overlay_fast(self):
        """SUPER SCHNELLE Animation - nur Overlay-Layer PhotoImage wechseln!"""
        if not self.overlay_enabled or not self.overlay_photos:
            return
        
        try:
            # Aktuelles PhotoImage holen
            photo = self.overlay_photos[self.overlay_current]
            
            # NUR das Overlay-Layer aktualisieren (Map bleibt unberührt!)
            if hasattr(self, 'overlay_canvas_item') and self.overlay_canvas_item:
                self.canvas.itemconfig(self.overlay_canvas_item, image=photo)
                self.canvas.tag_raise('overlay_anim')  # Immer über der Map
            
            # Referenz behalten!
            self._overlay_photo_ref = photo
            
            # Nächster Frame (smooth loop)
            self.overlay_current = (self.overlay_current + 1) % len(self.overlay_photos)
            
            # Timer für nächsten Frame (33ms = ~30fps)
            delay = int(33 / self.overlay_speed)
            self.overlay_animation_id = self.after(delay, self._animate_overlay_fast)
            
        except Exception as e:
            print(f"⚠️ Overlay Fehler: {e}")
    
    def _animate_overlay(self):
        """Legacy - ruft neue schnelle Version auf"""
        self._animate_overlay_fast()
    
    def stop_overlay_animation(self, render_now=True):
        """Stoppt die Overlay-Animation"""
        if self.overlay_animation_id:
            self.after_cancel(self.overlay_animation_id)
            self.overlay_animation_id = None
        
        # Overlay-Layer vom Canvas entfernen
        if hasattr(self, 'overlay_canvas_item') and self.overlay_canvas_item:
            self.canvas.delete('overlay_anim')
            self.overlay_canvas_item = None
        
        # Abdunkelungs-Layer entfernen
        if hasattr(self, '_darken_canvas_item') and self._darken_canvas_item:
            try:
                self.canvas.delete(self._darken_canvas_item)
            except:
                pass
            self._darken_canvas_item = None
            self._darken_photo = None
            self._darken_size = None
            self._darken_amount_cached = None
        
        # Speicher freigeben
        self.overlay_photos = []
        self.overlay_prepared = []
        self.overlay_map_cache = None
        self.overlay_canvas_size = None
        self._overlay_photo_ref = None
    
    def get_overlay_frame(self, target_size: tuple):
        """Hole aktuellen GM-Overlay Frame, skaliert auf Zielgröße"""
        from PIL import Image
        
        if not self.overlay_frames or not self.overlay_enabled:
            return None
        
        # Aktuellen Frame holen
        frame = self.overlay_frames[self.overlay_current]
        
        # Skalierung anwenden
        if self.overlay_scale != 1.0:
            new_w = int(frame.width * self.overlay_scale)
            new_h = int(frame.height * self.overlay_scale)
            frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        frame_w, frame_h = frame.size
        target_w, target_h = target_size
        
        # Ergebnis-Bild erstellen
        result = Image.new('RGBA', target_size, (0, 0, 0, 0))
        
        if self.overlay_mode == "tile":
            # Kacheln mit Offset
            start_x = self.overlay_x % frame_w if frame_w > 0 else 0
            start_y = self.overlay_y % frame_h if frame_h > 0 else 0
            
            for y in range(-frame_h + start_y, target_h, frame_h):
                for x in range(-frame_w + start_x, target_w, frame_w):
                    result.paste(frame, (x, y), frame if frame.mode == 'RGBA' else None)
                    
        elif self.overlay_mode == "stretch":
            # Auf volle Größe strecken
            stretched = frame.resize(target_size, Image.Resampling.LANCZOS)
            result.paste(stretched, (self.overlay_x, self.overlay_y), stretched if stretched.mode == 'RGBA' else None)
            
        elif self.overlay_mode == "center":
            # Zentriert mit Offset
            x = (target_w - frame_w) // 2 + self.overlay_x
            y = (target_h - frame_h) // 2 + self.overlay_y
            result.paste(frame, (x, y), frame if frame.mode == 'RGBA' else None)
        
        # Opacity anwenden
        if self.overlay_opacity < 1.0:
            # Alpha-Kanal modifizieren
            r, g, b, a = result.split()
            a = a.point(lambda x: int(x * self.overlay_opacity))
            result = Image.merge('RGBA', (r, g, b, a))
        
        return result
    
    def load_weather_presets(self):
        """Lade vordefinierte Wetter-Overlays aus dem weather_overlays Ordner"""
        self.weather_presets = {"clear": None}  # Clear = kein Overlay
        
        if not os.path.exists(self.weather_folder):
            os.makedirs(self.weather_folder)
            print(f"📁 Wetter-Ordner erstellt: {self.weather_folder}")
            print(f"   Lege GIF-Dateien dort ab (z.B. rain.gif, snow.gif, storm.gif)")
            return
        
        # Suche nach GIF-Dateien
        for file in os.listdir(self.weather_folder):
            if file.lower().endswith('.gif'):
                name = os.path.splitext(file)[0].lower()
                self.weather_presets[name] = os.path.join(self.weather_folder, file)
                print(f"🌤️ Wetter-Preset geladen: {name}")
    
    def set_weather(self, weather_type: str):
        """Setze ein vordefiniertes Wetter"""
        weather_type = weather_type.lower()
        self.current_weather = weather_type
        
        if weather_type == "clear" or weather_type not in self.weather_presets:
            # Kein Wetter
            self.clear_weather_overlay()
            self.update_weather_button()
            print(f"☀️ Wetter: Klar")
            return True
        
        gif_path = self.weather_presets.get(weather_type)
        if gif_path and os.path.exists(gif_path):
            success = self.load_weather_overlay(gif_path)
            if success:
                self.update_weather_button()
                print(f"🌧️ Wetter: {weather_type}")
            return success
        
        print(f"⚠️ Wetter-Overlay nicht gefunden: {weather_type}")
        return False
    
    def update_weather_button(self):
        """Aktualisiere Wetter-Button Text"""
        if hasattr(self, 'weather_btn'):
            icons = {
                "clear": "☀️",
                "rain": "🌧️",
                "snow": "❄️",
                "storm": "⛈️",
                "fog": "🌫️",
                "leaves": "🍂",
            }
            icon = icons.get(self.current_weather, "🌤️")
            self.weather_btn.config(text=icon)
    
    def open_weather_dialog(self):
        """Öffne Wetter-Auswahl Dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Wetter-Steuerung")
        dialog.geometry("350x450")
        dialog.configure(bg="#2a2a2a")
        dialog.transient(self)
        dialog.grab_set()
        
        # Titel
        tk.Label(dialog, text="🌤️ Wetter-Steuerung", font=("Arial", 14, "bold"),
                bg="#2a2a2a", fg="white").pack(pady=10)
        
        # === Wetter-Buttons ===
        weather_frame = tk.LabelFrame(dialog, text="Wetter auswählen", bg="#2a2a2a", fg="white")
        weather_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Clear-Button
        tk.Button(weather_frame, text="☀️ Klar", command=lambda: [self.set_weather("clear"), dialog.destroy()],
                 bg="#4a7a4a", fg="white", font=("Arial", 11), width=12).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Dynamische Buttons für alle geladenen Presets
        icons = {"rain": "🌧️", "snow": "❄️", "storm": "⛈️", "fog": "🌫️", "leaves": "🍂", "dust": "💨"}
        for name in self.weather_presets:
            if name != "clear":
                icon = icons.get(name, "🌤️")
                btn = tk.Button(weather_frame, text=f"{icon} {name.capitalize()}", 
                               command=lambda n=name: [self.set_weather(n), dialog.destroy()],
                               bg="#4a4a7a", fg="white", font=("Arial", 11), width=12)
                btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # === Custom GIF laden ===
        custom_frame = tk.LabelFrame(dialog, text="Custom Overlay", bg="#2a2a2a", fg="white")
        custom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(custom_frame, text="📁 GIF laden...", command=lambda: self._load_custom_weather(dialog),
                 bg="#5a5a5a", fg="white", font=("Arial", 10)).pack(pady=5)
        
        # === Opacity Slider ===
        opacity_frame = tk.LabelFrame(dialog, text="Deckkraft", bg="#2a2a2a", fg="white")
        opacity_frame.pack(fill=tk.X, padx=10, pady=5)
        
        opacity_var = tk.DoubleVar(value=self.weather_overlay_opacity * 100)
        opacity_slider = tk.Scale(opacity_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                 variable=opacity_var, bg="#3a3a3a", fg="white",
                                 highlightthickness=0, troughcolor="#1a1a1a",
                                 command=lambda v: self.set_weather_overlay_opacity(float(v)/100))
        opacity_slider.pack(fill=tk.X, padx=10, pady=5)
        
        # === Random Wetter ===
        random_frame = tk.LabelFrame(dialog, text="🎲 Zufälliges Wetter", bg="#2a2a2a", fg="white")
        random_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.random_weather_var = tk.BooleanVar(value=self.random_weather_enabled)
        random_check = tk.Checkbutton(random_frame, text="Aktiviert", variable=self.random_weather_var,
                                     bg="#2a2a2a", fg="white", selectcolor="#3a3a3a",
                                     command=self._toggle_random_weather)
        random_check.pack(anchor=tk.W, padx=10)
        
        # Intervall
        interval_frame = tk.Frame(random_frame, bg="#2a2a2a")
        interval_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(interval_frame, text="Intervall (Min):", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        self.interval_min_var = tk.StringVar(value=str(self.random_weather_interval[0] // 60))
        self.interval_max_var = tk.StringVar(value=str(self.random_weather_interval[1] // 60))
        tk.Entry(interval_frame, textvariable=self.interval_min_var, width=4, bg="#3a3a3a", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Label(interval_frame, text="-", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        tk.Entry(interval_frame, textvariable=self.interval_max_var, width=4, bg="#3a3a3a", fg="white").pack(side=tk.LEFT, padx=2)
        
        # Dauer
        duration_frame = tk.Frame(random_frame, bg="#2a2a2a")
        duration_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(duration_frame, text="Dauer (Min):", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        self.duration_min_var = tk.StringVar(value=str(self.random_weather_duration[0] // 60))
        self.duration_max_var = tk.StringVar(value=str(self.random_weather_duration[1] // 60))
        tk.Entry(duration_frame, textvariable=self.duration_min_var, width=4, bg="#3a3a3a", fg="white").pack(side=tk.LEFT, padx=2)
        tk.Label(duration_frame, text="-", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        tk.Entry(duration_frame, textvariable=self.duration_max_var, width=4, bg="#3a3a3a", fg="white").pack(side=tk.LEFT, padx=2)
        
        # Speichern Button
        tk.Button(random_frame, text="Einstellungen speichern", 
                 command=lambda: self._save_random_settings(),
                 bg="#4a6a4a", fg="white").pack(pady=5)
        
        # === Status ===
        status_text = f"Aktuell: {self.current_weather.capitalize()}"
        if self.random_weather_enabled:
            status_text += " | 🎲 Zufällig AN"
        tk.Label(dialog, text=status_text, bg="#2a2a2a", fg="#aaaaaa").pack(pady=10)
        
        # Schließen Button
        tk.Button(dialog, text="Schließen", command=dialog.destroy,
                 bg="#5a5a5a", fg="white", font=("Arial", 10)).pack(pady=10)
    
    def _load_custom_weather(self, dialog):
        """Lade ein benutzerdefiniertes GIF"""
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="Wetter-Overlay GIF auswählen",
            filetypes=[("GIF Dateien", "*.gif"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            if self.load_weather_overlay(filepath):
                self.current_weather = "custom"
                self.update_weather_button()
                dialog.destroy()
    
    def _toggle_random_weather(self):
        """Toggle zufälliges Wetter"""
        self.random_weather_enabled = self.random_weather_var.get()
        
        if self.random_weather_enabled:
            self._start_random_weather_timer()
            print("🎲 Zufälliges Wetter aktiviert")
        else:
            self._stop_random_weather_timer()
            print("🎲 Zufälliges Wetter deaktiviert")
    
    def _save_random_settings(self):
        """Speichere Random-Wetter Einstellungen"""
        try:
            min_interval = int(self.interval_min_var.get()) * 60
            max_interval = int(self.interval_max_var.get()) * 60
            min_duration = int(self.duration_min_var.get()) * 60
            max_duration = int(self.duration_max_var.get()) * 60
            
            self.random_weather_interval = (min(min_interval, max_interval), max(min_interval, max_interval))
            self.random_weather_duration = (min(min_duration, max_duration), max(min_duration, max_duration))
            
            print(f"🎲 Random-Einstellungen: Intervall {self.random_weather_interval[0]//60}-{self.random_weather_interval[1]//60} Min, "
                  f"Dauer {self.random_weather_duration[0]//60}-{self.random_weather_duration[1]//60} Min")
            
            # Neu starten wenn aktiv
            if self.random_weather_enabled:
                self._stop_random_weather_timer()
                self._start_random_weather_timer()
        except ValueError:
            print("⚠️ Ungültige Eingabe für Random-Einstellungen")
    
    def _start_random_weather_timer(self):
        """Starte Timer für nächstes zufälliges Wetter"""
        import random
        
        # Zufälliges Intervall bis zum nächsten Wetter-Event
        interval = random.randint(self.random_weather_interval[0], self.random_weather_interval[1])
        
        self.random_weather_timer = self.after(interval * 1000, self._trigger_random_weather)
        print(f"⏱️ Nächstes Wetter in {interval // 60} Minuten")
    
    def _stop_random_weather_timer(self):
        """Stoppe Random-Wetter Timer"""
        if self.random_weather_timer:
            self.after_cancel(self.random_weather_timer)
            self.random_weather_timer = None
        if self.random_weather_end_timer:
            self.after_cancel(self.random_weather_end_timer)
            self.random_weather_end_timer = None
    
    def _trigger_random_weather(self):
        """Löse zufälliges Wetter-Event aus"""
        import random
        
        # Wähle zufälliges Wetter aus verfügbaren Presets
        available = [w for w in self.random_weather_types if w in self.weather_presets]
        
        if available:
            weather = random.choice(available)
            duration = random.randint(self.random_weather_duration[0], self.random_weather_duration[1])
            
            print(f"🎲 Zufälliges Wetter: {weather} für {duration // 60} Minuten")
            self.set_weather(weather)
            
            # Timer zum Beenden des Wetters
            self.random_weather_end_timer = self.after(duration * 1000, self._end_random_weather)
        else:
            # Kein Wetter verfügbar, neuen Timer starten
            self._start_random_weather_timer()
    
    def _end_random_weather(self):
        """Beende aktuelles Random-Wetter und starte neuen Timer"""
        print(f"🎲 Wetter endet, zurück zu klar")
        self.set_weather("clear")
        
        # Starte Timer für nächstes Wetter
        if self.random_weather_enabled:
            self._start_random_weather_timer()
    
    # ==================== ENDE WETTER-OVERLAY ====================

    def toggle_fog_ui(self):
        """Nebel per Button ein/ausschalten"""
        self.fog_enabled = not self.fog_enabled
        
        if self.fog_enabled:
            self.fog_toggle_btn.config(text="🌫️ Nebel: AN", fg="#00ff00")
        else:
            self.fog_toggle_btn.config(text="🌫️ Nebel: AUS", fg="#ff0000")
        
        self.render_map()
    
    def toggle_controls(self):
        """Control-Bar ein/ausblenden"""
        if self.control_visible:
            self.hide_controls()
        else:
            self.show_controls()
    
    def hide_controls(self):
        """Control-Bar ausblenden"""
        if hasattr(self, 'control_bar'):
            self.control_bar.place_forget()
            self.control_visible = False
    
    def show_controls(self):
        """Control-Bar einblenden"""
        if hasattr(self, 'control_bar'):
            self.control_bar.place(x=10, y=10, width=300, height=40)
            self.control_visible = True
            # Nach 5 Sekunden wieder ausblenden
            self.after(5000, lambda: self.hide_controls())
    
    def update_map(self, map_data):
        """Karte aktualisieren"""
        self.map_data = map_data
        self.river_directions = map_data.get("river_directions", {})  # Update river directions
        self.detail_system.update_base_map(map_data)
        
        # WICHTIG: Fog-Cache leeren bei Map-Update
        self.fog_photo_cache.clear()
        
        # WICHTIG: Auch den internen Cache des FogGenerators leeren
        if hasattr(self, 'fog_generator') and self.fog_generator:
            self.fog_generator.clear_cache()
        
        # WICHTIG: TextureManager-Cache leeren für neue Water-Farbe
        if hasattr(self, 'texture_manager') and self.texture_manager:
            self.texture_manager.clear_cache()
        
        self.render_map()
    
    def toggle_detail_view(self, event=None):
        """Wechselt zwischen Basis- und Detail-Ansicht"""
        if self.detail_system.is_in_detail_view():
            # Zurück zur Basis
            self.detail_system.switch_to_base()
        else:
            # Zur Detail wechseln (wenn verfügbar an aktueller Position)
            if self.webcam_tracker:
                current_tile = self.webcam_tracker.get_current_tile()
                if current_tile:
                    self.detail_system.auto_switch_on_position(current_tile[0], current_tile[1])
        
        self.render_map()
    
    def check_svg_for_animations(self):
        """Prüft SVG auf animierte Materialien"""
        self.has_animated_tiles = False
        self.svg_animated_materials = set()
        
        if not self.svg_renderer or not self.svg_renderer.svg_data:
            return
        
        # Parse SVG und finde alle data-material Attribute
        try:
            root = ET.fromstring(self.svg_renderer.svg_data)
            namespaces = {'svg': 'http://www.w3.org/2000/svg'}
            
            # Animierte Materialien
            animated_materials = {'water', 'forest', 'animated_forest', 'animated_grass', 'village'}
            
            # Finde alle image-Elemente mit data-material
            for img in root.findall('.//svg:image[@data-material]', namespaces):
                material = img.get('data-material')
                if material in animated_materials:
                    self.svg_animated_materials.add(material)
                    self.has_animated_tiles = True
            
            if self.has_animated_tiles:
                pass
        
        except Exception as e:
            pass
    
    def check_for_animated_tiles(self):
        """Prüft ob die Map animierte Tiles hat und sammelt ihre Positionen"""
        self.has_animated_tiles = False
        self.animated_positions = []
        
        if not self.map_data or 'tiles' not in self.map_data:
            return
        
        # Liste der animierten Materialien
        animated_materials = {'water', 'forest', 'animated_forest', 'animated_grass', 'village'}
        
        tiles = self.map_data.get('tiles', [])
        width = self.map_data.get('width', 50)
        height = self.map_data.get('height', 50)
        
        # DEBUG: Sammle Material-Statistik
        material_counts = {}
        
        # Prüfe ob tiles ein Dict oder Liste ist
        tiles_is_dict = isinstance(tiles, dict)
        
        if tiles_is_dict:
            # Dictionary-Format: "x,y" -> material oder Hexagon-Tile-Daten
            for coord_key, tile_data in tiles.items():
                # Parse Koordinaten
                try:
                    x, y = map(int, coord_key.split(','))
                except:
                    continue
                
                # Hexagon-Map: tile_data ist ein Dict mit 'terrain', 'fill_color', etc.
                # Normale Map: tile_data ist ein String (Material-Name)
                if isinstance(tile_data, dict):
                    # Hexagon-Tile-Format
                    raw_terrain = tile_data.get('terrain', 'PLAINS')
                    # Konvertiere zu Material-Name
                    material = normalize_terrain_to_material(raw_terrain)
                else:
                    # Normales String-Format
                    material = tile_data
                
                # Statistik sammeln
                material_counts[material] = material_counts.get(material, 0) + 1
                
                is_animated = False
                if material in animated_materials:
                    is_animated = True
                elif isinstance(material, str) and material.startswith('custom_'):
                    custom_info = self.texture_manager.custom_materials.get(material)
                    if custom_info and custom_info.get('frames', 0) > 1:
                        is_animated = True
                
                if is_animated:
                    self.animated_positions.append((x, y, material))
                    self.has_animated_tiles = True
        else:
            # 2D-Liste Format
            for y, row in enumerate(tiles):
                if not isinstance(row, list):
                    continue
                for x, material in enumerate(row):
                    # Statistik sammeln
                    material_counts[material] = material_counts.get(material, 0) + 1
                    
                    is_animated = False
                    
                    if material in animated_materials:
                        is_animated = True
                    elif material.startswith('custom_'):
                        # Prüfe custom materials mit Frames
                        custom_info = self.texture_manager.custom_materials.get(material)
                        if custom_info and custom_info.get('frames', 0) > 1:
                            is_animated = True
                    
                    if is_animated:
                        self.animated_positions.append((x, y, material))
                        self.has_animated_tiles = True
    
    def start_animation(self):
        """Startet die Animation für Wasser, Wälder, etc."""
        self.is_animating = True
        if self.is_animating:
            self.animate_tiles()
    
    def animate_tiles(self):
        """Animiert Wasser und andere animierte Materialien im Projektor"""
        if not self.is_animating:
            return
        
        # Frame erhöhen - 240 Frames für längere, langsamere Loops
        self.animation_frame = (self.animation_frame + 1) % 240
        
        # Wetter-Overlay Frame weiterschalten
        if self.weather_overlay_enabled and self.weather_overlay_frames:
            # Alle 2 Animation-Frames den Wetter-Frame weiterschalten (15 FPS für Wetter)
            if self.animation_frame % 2 == 0:
                self.advance_weather_frame()
        
        # Lighting-Animation (für flackernde Lichter) - WICHTIG: Immer updaten!
        if self.lighting_enabled:
            self.lighting_time += 0.033  # 33ms = ~30 FPS
            # Update lighting engine time offset für Flacker-Effekt
            self.lighting_engine.update_animation(0.033)
            
            # WICHTIG: Bei Lighting-Animation statischen Cache NICHT verwenden!
            # Sonst wird nur das Base-Image cached und Lighting-Änderungen sind nicht sichtbar
            if self.is_svg_mode and self.lighting_engine.lights:
                # Cache NUR für das SVG-Base-Image behalten, Lighting wird jedes Mal neu gerendert
                pass  # svg_static_cache bleibt erhalten, aber Lighting-Layer wird neu gerendert
        
        # PERFORMANCE: Nur jeden 2. Frame tatsächlich rendern (15 FPS effektiv)
        # Bei Lighting mit Flicker: Jeden Frame rendern für flüssiges Flackern!
        self.frame_skip_counter += 1
        
        # Bei aktiven flackernden Lichtern: Keine Frames überspringen
        has_flickering_lights = any(light.flicker for light in self.lighting_engine.lights) if self.lighting_enabled else False
        skip_frames = 1 if has_flickering_lights else 2
        
        if self.frame_skip_counter >= skip_frames:
            self.frame_skip_counter = 0
            # Map rendern (optimiert durch Caching - nur animierte Tiles!)
            self.render_map()
        
        # Nächster Frame nach 33ms (~30 FPS Animation)
        self.animation_id = self.after(33, self.animate_tiles)
    
    def apply_fog_to_image(self, img, svg_mode=False):
        """Wendet Fog-of-War auf ein PIL Image an (für SVG-Modus)"""
        if not self.fog_enabled or not self.fog:
            return img
        
        # Konvertiere zu RGBA für Transparenz
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Fog-Layer erstellen
        fog_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # Map-Dimensionen aus fog system holen (korrekte Tile-Anzahl!)
        map_width = self.fog.width
        map_height = self.fog.height
        
        # Tile-Größe im gerenderten Bild
        tile_width = img.width / map_width
        tile_height = img.height / map_height
        
        # DEBUG
        fog_count = 0
        
        # Zeichne Fog-Texturen über nicht-revealed Bereiche
        for y in range(map_height):
            for x in range(map_width):
                if not self.fog.is_revealed(x, y):
                    fog_count += 1
                    x1 = int(x * tile_width)
                    y1 = int(y * tile_height)
                    
                    # Fog-Textur holen mit passender Größe
                    fog_tile_size = int(max(tile_width, tile_height))
                    
                    if fog_tile_size not in self.fog_photo_cache:
                        fog_texture = self.fog_texture_gen.get_fog_texture(fog_tile_size, "normal")
                        self.fog_photo_cache[fog_tile_size] = fog_texture
                    else:
                        fog_texture = self.fog_photo_cache[fog_tile_size]
                    
                    # Skaliere Fog-Textur auf exakte Tile-Größe falls nötig
                    if fog_texture.size != (int(tile_width), int(tile_height)):
                        fog_texture = fog_texture.resize((int(tile_width), int(tile_height)), Image.LANCZOS)
                    
                    # Paste Fog-Textur aufs Layer
                    if fog_texture.mode == 'RGBA':
                        fog_layer.paste(fog_texture, (x1, y1), fog_texture)
                    else:
                        fog_layer.paste(fog_texture, (x1, y1))
        
        if fog_count > 0:
            pass
        
        # Kombiniere Bild mit Fog-Layer
        img = Image.alpha_composite(img, fog_layer)
        return img.convert('RGB')
    
    def render_svg_map(self):
        """Rendert SVG-Map mit Viewport-basiertem Zoom/Pan (wie Kamera)"""
        try:
            # Canvas-Größe ermitteln
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
        except Exception as e:
            return
        
        # Prüfe ob Canvas-Größen gültig sind
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        # SVG Original-Größe: Nutze original_svg_size wenn vorhanden, sonst aus File
        if self.original_svg_size:
            svg_width, svg_height = self.original_svg_size
        else:
            root = ET.fromstring(self.svg_renderer.svg_data)
            svg_width = int(root.get('width', '1000').replace('px', ''))
            svg_height = int(root.get('height', '1000').replace('px', ''))
        
        # Berechne Basis-Scale um ganze Map zu zeigen (nur einmal beim Start)
        if self.svg_base_scale == 1.0:
            scale_w = canvas_width / svg_width
            scale_h = canvas_height / svg_height
            self.svg_base_scale = min(scale_w, scale_h)
        
        # Aktuelle Skalierung = Basis * Zoom
        current_scale = self.svg_base_scale * self.zoom_level
        
        # FULL SVG rendern mit aktueller Skalierung
        full_width = int(svg_width * current_scale)
        full_height = int(svg_height * current_scale)
        
        # Cache-Key
        cache_key = (full_width, full_height)
        cache_invalid = self.svg_static_cache is None or self.svg_cache_size != cache_key
        
        # STATISCHES RENDERING (nur bei Größenänderung)
        if cache_invalid:
            
            # Try GPU SVG rendering first if available
            if self.gpu_svg_renderer:
                try:
                    self.gpu_svg_renderer.create_canvas(full_width, full_height)
                    self.gpu_svg_renderer.clear_canvas(0, 0, 0, 1)  # Black background
                    
                    # Parse SVG and render basic shapes with GPU
                    root = ET.fromstring(self.svg_renderer.svg_data)
                    namespaces = {'svg': 'http://www.w3.org/2000/svg'}
                    
                    # Render basic rectangles (most SVG maps use simple rects for tiles)
                    for rect in root.findall('.//svg:rect', namespaces):
                        x = float(rect.get('x', 0)) * current_scale
                        y = float(rect.get('y', 0)) * current_scale
                        width = float(rect.get('width', 0)) * current_scale
                        height = float(rect.get('height', 0)) * current_scale
                        
                        # Get fill color
                        fill = rect.get('fill', '#000000')
                        if fill.startswith('#'):
                            # Convert hex to RGB
                            r = int(fill[1:3], 16) / 255.0
                            g = int(fill[3:5], 16) / 255.0
                            b = int(fill[5:7], 16) / 255.0
                            self.gpu_svg_renderer.render_rect(int(x), int(y), int(width), int(height), r, g, b, 1.0)
                    
                    rendered_full = self.gpu_svg_renderer.get_image()
                    if rendered_full:
                        pass
                    else:
                        raise Exception("GPU-SVG-Renderer returned None")
                        
                except Exception as e:
                    rendered_full = self.svg_renderer.render_to_size(full_width, full_height, cache=False)
            else:
                # CPU-based rendering with CairoSVG
                rendered_full = self.svg_renderer.render_to_size(full_width, full_height, cache=False)
            
            if rendered_full is None:
                return
            
            self.svg_static_cache = rendered_full.copy()
            self.svg_cache_size = cache_key
        
        # Kopiere statischen Cache
        rendered_full = self.svg_static_cache.copy()
        
        # ANIMIERTE TILES übermalen (wenn Animation läuft)
        if self.is_animating and self.has_animated_tiles:
            if not hasattr(self, 'texture_manager'):
                from texture_manager import TextureManager
                self.texture_manager = TextureManager()
            
            # Parse SVG für animierte Tiles
            root = ET.fromstring(self.svg_renderer.svg_data)
            namespaces = {'svg': 'http://www.w3.org/2000/svg'}
            
            for img_elem in root.findall('.//svg:image[@data-material]', namespaces):
                material = img_elem.get('data-material')
                
                if material in self.svg_animated_materials:
                    x = float(img_elem.get('x', 0))
                    y = float(img_elem.get('y', 0))
                    width = float(img_elem.get('width', 64))
                    
                    # Skalierte Position
                    scaled_x = int(x * current_scale)
                    scaled_y = int(y * current_scale)
                    scaled_size = int(width * current_scale)
                    
                    # Rendere animiertes Tile
                    if hasattr(self.texture_manager, 'advanced_renderer'):
                        animated_tile = self.texture_manager.advanced_renderer.get_texture(
                            material, scaled_size, self.animation_frame
                        )
                        
                        if animated_tile:
                            if material == 'village' and animated_tile.size[0] > scaled_size:
                                if animated_tile.mode == 'RGBA':
                                    offset_y = scaled_y - int(scaled_size * 2)
                                    rendered_full.paste(animated_tile, (scaled_x, offset_y), animated_tile)
                            else:
                                if animated_tile.mode != 'RGB':
                                    animated_tile = animated_tile.convert('RGB')
                                rendered_full.paste(animated_tile, (scaled_x, scaled_y))
        
        # VIEWPORT-CROP: Schneide sichtbaren Bereich aus
        # Viewport-Position (in Full-Image-Koordinaten)
        view_x = int(self.svg_viewport_x)
        view_y = int(self.svg_viewport_y)
        
        # Begrenze Viewport
        view_x = max(0, min(view_x, full_width - canvas_width))
        view_y = max(0, min(view_y, full_height - canvas_height))
        
        # WICHTIG: Schreibe begrenzte Werte zurück!
        self.svg_viewport_x = view_x
        self.svg_viewport_y = view_y
        
        # Wenn Bild kleiner als Canvas, zentrieren
        if full_width <= canvas_width:
            view_x = -(canvas_width - full_width) // 2
        if full_height <= canvas_height:
            view_y = -(canvas_height - full_height) // 2
        
        # Crop auf Canvas-Größe
        if view_x >= 0 and view_y >= 0:
            viewport_img = rendered_full.crop((
                view_x,
                view_y,
                min(view_x + canvas_width, full_width),
                min(view_y + canvas_height, full_height)
            ))
        else:
            # Zentrieren wenn Bild kleiner als Canvas
            viewport_img = Image.new('RGB', (canvas_width, canvas_height), (10, 10, 10))
            paste_x = max(0, -view_x)
            paste_y = max(0, -view_y)
            crop_x = max(0, view_x)
            crop_y = max(0, view_y)
            cropped = rendered_full.crop((crop_x, crop_y, full_width, full_height))
            viewport_img.paste(cropped, (paste_x, paste_y))
        
        # Konvertiere zu RGBA für Lighting/Fog
        if viewport_img.mode != 'RGBA':
            viewport_img = viewport_img.convert('RGBA')
        
        # Lighting-Overlay rendern (SVG-Modus: skaliert auf full_width/full_height)
        if self.lighting_enabled and (self.lighting_engine.lights or (self.lighting_engine.lighting_mode == "day" and self.lighting_engine.darkness_polygons)):
            # Berechne Tile-Größe aus SVG-Original und Fog-Grid
            tile_width_px = (svg_width * current_scale) / self.fog.width
            tile_height_px = (svg_height * current_scale) / self.fog.height
            avg_tile_size = int((tile_width_px + tile_height_px) / 2)
            
            # Rendere Lighting direkt in PIXEL-Größe des gerenderten SVG (nicht in Tile-Grid!)
            # Das verhindert Größen-Mismatches und Streifen
            # WICHTIG: Berechne radius_scale basierend auf Tile-Größe
            # Standard Tile-Size ist 25px, skaliere Radien entsprechend
            radius_scale = avg_tile_size / 25.0
            
            lighting_full = self.lighting_engine.render_lighting(
                width=self.fog.width,
                height=self.fog.height,
                tile_size=avg_tile_size,
                time_offset=self.lighting_time,
                radius_scale=radius_scale
            )
            
            # Crop Lighting auf gleichen Viewport wie Map
            if view_x >= 0 and view_y >= 0:
                lighting_viewport = lighting_full.crop((
                    view_x,
                    view_y,
                    min(view_x + canvas_width, full_width),
                    min(view_y + canvas_height, full_height)
                ))
            else:
                lighting_viewport = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
                paste_x = max(0, -view_x)
                paste_y = max(0, -view_y)
                crop_x = max(0, view_x)
                crop_y = max(0, view_y)
                lighting_cropped = lighting_full.crop((crop_x, crop_y, full_width, full_height))
                lighting_viewport.paste(lighting_cropped, (paste_x, paste_y))
            
            # ═══════════════════════════════════════════════════════════
            # COMPOSITE LIGHTING: TAG-MODUS = MULTIPLY, NACHT = ALPHA
            # ═══════════════════════════════════════════════════════════
            from PIL import ImageChops
            if lighting_viewport.size == viewport_img.size:
                # TAG-MODUS: Multiply-Blend für physikalisch korrekte Schatten
                if self.lighting_engine.lighting_mode == "day" and self.lighting_engine.darkness_polygons:

                    # Prefer GPU when available
                    gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
                    if gpu:
                        try:
                            viewport_img = self.gpu_composite_rendering(viewport_img, lighting_viewport, fog_enabled=False, fog_data=None, mode='multiply')
                        except Exception as e:
                            lighting_rgb = lighting_viewport.convert('RGB')
                            lighting_alpha = lighting_viewport.split()[3]
                            viewport_rgb = viewport_img.convert('RGB')
                            darkened_map = ImageChops.multiply(viewport_rgb, lighting_rgb)
                            darkened_map = darkened_map.convert('RGBA')
                            viewport_img = Image.composite(darkened_map, viewport_img, lighting_alpha)
                    else:
                        lighting_rgb = lighting_viewport.convert('RGB')
                        lighting_alpha = lighting_viewport.split()[3]
                        viewport_rgb = viewport_img.convert('RGB')
                        darkened_map = ImageChops.multiply(viewport_rgb, lighting_rgb)
                        darkened_map = darkened_map.convert('RGBA')
                        viewport_img = Image.composite(darkened_map, viewport_img, lighting_alpha)
                else:
                    # NACHT-MODUS: Normales Alpha-Composite
                    gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
                    if gpu:
                        try:
                            viewport_img = self.gpu_composite_rendering(viewport_img, lighting_viewport, fog_enabled=False, fog_data=None, mode='alpha')
                        except Exception as e:
                            viewport_img = Image.alpha_composite(viewport_img, lighting_viewport)
                    else:
                        viewport_img = Image.alpha_composite(viewport_img, lighting_viewport)
            else:
                # Fallback: Resize Lighting-Viewport
                lighting_viewport = lighting_viewport.resize(viewport_img.size, Image.LANCZOS)
                
                # Auch hier: Tag-Modus Check
                if self.lighting_engine.lighting_mode == "day" and self.lighting_engine.darkness_polygons:
                    gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
                    if gpu:
                        try:
                            viewport_img = self.gpu_composite_rendering(viewport_img, lighting_viewport, fog_enabled=False, fog_data=None, mode='multiply')
                        except Exception as e:
                            lighting_rgb = lighting_viewport.convert('RGB')
                            lighting_alpha = lighting_viewport.split()[3]
                            viewport_rgb = viewport_img.convert('RGB')
                            darkened_map = ImageChops.multiply(viewport_rgb, lighting_rgb)
                            darkened_map = darkened_map.convert('RGBA')
                            viewport_img = Image.composite(darkened_map, viewport_img, lighting_alpha)
                    else:
                        lighting_rgb = lighting_viewport.convert('RGB')
                        lighting_alpha = lighting_viewport.split()[3]
                        viewport_rgb = viewport_img.convert('RGB')
                        darkened_map = ImageChops.multiply(viewport_rgb, lighting_rgb)
                        darkened_map = darkened_map.convert('RGBA')
                        viewport_img = Image.composite(darkened_map, viewport_img, lighting_alpha)
                else:
                    gpu = self.gpu_renderer or getattr(self.lighting_engine, 'gpu_renderer', None)
                    if gpu:
                        try:
                            viewport_img = self.gpu_composite_rendering(viewport_img, lighting_viewport, fog_enabled=False, fog_data=None, mode='alpha')
                        except Exception as e:
                            viewport_img = Image.alpha_composite(viewport_img, lighting_viewport)
                    else:
                        viewport_img = Image.alpha_composite(viewport_img, lighting_viewport)
        elif not self.lighting_enabled:
            pass
        elif not self.lighting_engine.lights:
            pass
        
        # === WETTER-OVERLAY (nach Lighting, vor Fog) ===
        # HINWEIS: GM-Overlay wird jetzt als separates animiertes Layer gehandhabt
        # Hier nur noch das alte Weather-System (falls verwendet)
        if self.weather_overlay_enabled and self.weather_overlay_frames:
            weather_frame = self.get_weather_overlay_frame(viewport_img.size)
            if weather_frame:
                # Konvertiere zu RGBA für Alpha-Composite
                if viewport_img.mode != 'RGBA':
                    viewport_img = viewport_img.convert('RGBA')
                # Composite
                viewport_img = Image.alpha_composite(viewport_img, weather_frame)
        
        # HINWEIS: GM-Overlay wird jetzt als separates Canvas-Layer angezeigt
        # (siehe overlay_canvas_id und _animate_overlay_fast)
        # Kein Compositing mehr nötig hier!
        
        # Fog-of-War anwenden (auf ORIGINALER Tile-Grid-Basis)
        if self.fog_enabled and self.fog:
            # Berechne welche Tiles im Viewport sichtbar sind
            tile_width = svg_width / self.fog.width
            tile_height = svg_height / self.fog.height
            
            # In Viewport-Koordinaten
            start_tile_x = int((view_x / current_scale) / tile_width)
            start_tile_y = int((view_y / current_scale) / tile_height)
            end_tile_x = int(((view_x + canvas_width) / current_scale) / tile_width) + 1
            end_tile_y = int(((view_y + canvas_height) / current_scale) / tile_height) + 1
            
            # Fog-Layer erstellen
            fog_layer = Image.new('RGBA', viewport_img.size, (0, 0, 0, 0))
            
            fog_tiles_count = 0
            
            for ty in range(max(0, start_tile_y), min(self.fog.height, end_tile_y)):
                for tx in range(max(0, start_tile_x), min(self.fog.width, end_tile_x)):
                    if not self.fog.is_revealed(tx, ty):
                        fog_tiles_count += 1
                        
                        # Tile-Position im Full-Image
                        tile_x = tx * tile_width * current_scale
                        tile_y = ty * tile_height * current_scale
                        tile_w = tile_width * current_scale
                        tile_h = tile_height * current_scale
                        
                        # Relativ zum Viewport
                        x1 = int(tile_x - view_x)
                        y1 = int(tile_y - view_y)
                        
                        # Nur zeichnen wenn im sichtbaren Bereich
                        if x1 + tile_w > 0 and y1 + tile_h > 0 and x1 < canvas_width and y1 < canvas_height:
                            # FOG-TEXTUR verwenden statt Verdunkelung!
                            fog_tile_size = int(max(tile_w, tile_h))
                            
                            if fog_tile_size not in self.fog_photo_cache:
                                fog_texture = self.fog_texture_gen.get_fog_texture(fog_tile_size, "normal")
                                self.fog_photo_cache[fog_tile_size] = fog_texture
                            else:
                                fog_texture = self.fog_photo_cache[fog_tile_size]
                            
                            # Skaliere auf exakte Größe
                            if fog_texture.size != (int(tile_w), int(tile_h)):
                                fog_texture = fog_texture.resize((int(tile_w), int(tile_h)), Image.LANCZOS)
                            
                            # Paste Fog-Textur
                            if fog_texture.mode == 'RGBA':
                                fog_layer.paste(fog_texture, (x1, y1), fog_texture)
                            else:
                                fog_layer.paste(fog_texture, (x1, y1))
            
            if fog_tiles_count > 0:
                pass
            
            viewport_img = Image.alpha_composite(viewport_img, fog_layer)
            viewport_img = viewport_img.convert('RGB')
        
        # Auf Canvas anzeigen
        photo = ImageTk.PhotoImage(viewport_img)
        
        if self.canvas_image_id:
            self.canvas.itemconfig(self.canvas_image_id, image=photo)
        else:
            self.canvas_image_id = self.canvas.create_image(
                0, 0,
                image=photo, anchor=tk.NW
            )
        
        self.canvas.photo = photo
        
        # === KARTEN-ABDUNKELUNG (für Wetter-Effekte) ===
        self._update_darken_layer(canvas_width, canvas_height)
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        if hasattr(self, 'is_animating'):
            self.is_animating = False
        if hasattr(self, 'animation_id') and self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()
