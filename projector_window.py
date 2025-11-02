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
import xml.etree.ElementTree as ET
from fog_texture_generator import FogTextureGenerator

class ProjectorWindow(tk.Toplevel):
    """Vollbild-Projektor-Fenster für Spieler mit Fog-of-War"""
    
    def __init__(self, parent, map_data=None, webcam_tracker=None, svg_path=None):
        super().__init__(parent)
        
        self.title("Der Eine Ring - Projektor")
        self.configure(bg="#0a0a0a", cursor="none")
        
        # SVG-Modus Detection
        self.is_svg_mode = svg_path is not None
        self.svg_path = svg_path
        self.svg_renderer = None
        
        if self.is_svg_mode:
            # SVG-Projektor-Modus initialisieren
            from svg_projector import SVGProjectorRenderer
            self.svg_renderer = SVGProjectorRenderer(svg_path)
            self.title("Der Eine Ring - Projektor (SVG)")
            
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
        
        # Detail-Map System
        from detail_map_system import DetailMapSystem
        self.detail_system = DetailMapSystem(self.map_data)
        
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
        
        # CACHING für statische Map-Teile
        self.static_map_cache = None  # PIL Image der statischen Tiles
        self.static_map_size = None  # (width, height, tile_size) für Cache-Invalidierung
        self.animated_positions = []  # Liste von (x, y) Positionen mit animierten Tiles
        self.canvas_image_id = None  # ID des Canvas-Image-Items (für Update statt Delete)
        
        self.setup_ui()
        self.render_map()
        
        # Prüfe ob Animation gebraucht wird
        if self.is_svg_mode:
            # SVG: Prüfe SVG-Daten auf animierte Materialien
            self.check_svg_for_animations()
        else:
            # JSON: Normale Tile-Prüfung
            self.check_for_animated_tiles()
        
        if self.has_animated_tiles:
            print(f"Animation aktiviert: {len(self.animated_positions) if not self.is_svg_mode else len(self.svg_animated_materials)} animierte Tiles")
            self.start_animation()  # Nur starten wenn nötig
        else:
            print("Keine animierten Tiles gefunden - statische Map")
        
    def setup_ui(self):
        """UI-Elemente erstellen"""
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
        
        # Control-Bar nach 5 Sekunden ausblenden
        self.control_visible = True
        self.after(5000, lambda: self.hide_controls())
        
        # Canvas für die Karte
        self.canvas = Canvas(main_frame, bg="#0a0a0a", 
                            highlightthickness=0, cursor="none")
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
        self.info_label = tk.Label(self, text="ESC = Beenden | F11 = Vollbild | Rechtsklick = Detail-Ansicht", 
                                   bg="#0a0a0a", fg="#666666", 
                                   font=("Arial", 10))
        self.info_label.place(x=10, y=10)
        
        # Info nach 3 Sekunden ausblenden
        self.after(3000, lambda: self.info_label.place_forget())
        
    def render_map(self):
        """
        Karte auf dem Canvas rendern - OPTIMIERT MIT CACHING!
        Unterstützt sowohl JSON-Maps (Tile-basiert) als auch SVG-Maps (Vektor-basiert)
        """
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
        
        # Wenn tiles leer ist, erstelle leere Karte
        if not tiles:
            tiles = [["grass" for _ in range(width)] for _ in range(height)]
        
        # Canvas-Größe ermitteln für Zentrierung
        try:
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
        except:
            # Canvas wurde zerstört
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
            print(f"Erstelle statischen Map-Cache ({width}x{height}, {current_tile_size}px)")
            self.static_map_cache = Image.new('RGB', (total_map_width, total_map_height), (10, 10, 10))
            self.static_map_size = cache_key
            
            # Rendere ALLE Tiles einmalig (mit Frame 0 für Animationen)
            for y in range(height):
                for x in range(width):
                    paste_x = x * current_tile_size
                    paste_y = y * current_tile_size
                    
                    if y < len(tiles) and x < len(tiles[y]):
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
                print(f"SVG-Animation: {len(self.svg_animated_materials)} animierte Material-Typen gefunden: {self.svg_animated_materials}")
        
        except Exception as e:
            print(f"⚠️ Fehler beim Parsen der SVG für Animation: {e}")
    
    def check_for_animated_tiles(self):
        """Prüft ob die Map animierte Tiles hat und sammelt ihre Positionen"""
        self.has_animated_tiles = False
        self.animated_positions = []
        
        if not self.map_data or 'tiles' not in self.map_data:
            return
        
        # Liste der animierten Materialien
        animated_materials = {'water', 'forest', 'animated_forest', 'animated_grass', 'village'}
        
        tiles = self.map_data.get('tiles', [])
        
        # DEBUG: Sammle Material-Statistik
        material_counts = {}
        
        # Sammle ALLE animierten Positionen
        for y, row in enumerate(tiles):
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
        
        # DEBUG: Zeige Material-Verteilung
        print("Material-Statistik auf der Map:")
        for mat, count in sorted(material_counts.items()):
            is_anim = "🎬 ANIMIERT" if mat in animated_materials else ""
            print(f"  {mat}: {count} Tiles {is_anim}")
        print(f"\nGesamt: {len(self.animated_positions)} animierte Tiles gefunden")
    
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
        
        # PERFORMANCE: Nur jeden 2. Frame tatsächlich rendern (15 FPS effektiv)
        # Animation läuft trotzdem mit 30 FPS (frame counter erhöht sich), aber Rendering seltener
        self.frame_skip_counter += 1
        if self.frame_skip_counter >= 2:
            self.frame_skip_counter = 0
            # Map rendern (optimiert durch Caching - nur animierte Tiles!)
            self.render_map()
        
        # Nächster Frame nach 33ms (~30 FPS Animation, 15 FPS Rendering)
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
                        print(f"🌫️ Fog-Textur generiert: {fog_tile_size}px, Mode: {fog_texture.mode}")
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
            print(f"🌫️ Fog angewendet auf {fog_count} Tiles (SVG-Modus)")
        
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
        except:
            return
        
        # SVG Original-Größe holen
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
            print(f"🎨 Rendere SVG-Base: {full_width}×{full_height}px (Scale: {current_scale:.2f})")
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
            if viewport_img.mode != 'RGBA':
                viewport_img = viewport_img.convert('RGBA')
            
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
                                print(f"🌫️ SVG-Fog-Textur generiert: {fog_tile_size}px")
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
                print(f"🌫️ SVG: {fog_tiles_count} Fog-Tiles im Viewport gerendert")
            
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
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        self.is_animating = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()
