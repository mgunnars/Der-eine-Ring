"""
Projektor-Fenster für "Der Eine Ring"
Zeigt die Karte im Vollbild auf einem zweiten Monitor mit Fog-of-War
"""
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import json
import random
from fog_texture_generator import FogTextureGenerator

class ProjectorWindow(tk.Toplevel):
    """Vollbild-Projektor-Fenster für Spieler mit Fog-of-War"""
    
    def __init__(self, parent, map_data=None, webcam_tracker=None):
        super().__init__(parent)
        
        self.title("Der Eine Ring - Projektor")
        self.configure(bg="#0a0a0a", cursor="none")
        
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
        self.check_for_animated_tiles()
        if self.has_animated_tiles:
            print(f"Animation aktiviert: {len(self.animated_positions)} animierte Tiles")
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
        Statische Tiles werden gecacht, nur animierte Tiles werden neu gerendert
        KEIN delete("all") mehr - nur Image-Update für flackerfreies Rendering!
        """
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
        # Offset für Zentrierung
        offset_x = max(0, (canvas_width - total_map_width) // 2)
        offset_y = max(0, (canvas_height - total_map_height) // 2)
        
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
        """Karte verschieben"""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        self.canvas.scan_mark(self.pan_start_x, self.pan_start_y)
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def zoom(self, event):
        """Zoom mit Mausrad"""
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level *= 0.9
        
        self.zoom_level = max(0.5, min(3.0, self.zoom_level))
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
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        self.is_animating = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()
