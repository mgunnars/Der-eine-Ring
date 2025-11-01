<<<<<<< HEAD
class TextureGenerator:
    def __init__(self, size):
        self.size = size
        self.textures = self.generate_textures()

    def generate_textures(self):
        # Logic for generating textures
        return {"grass": "grass_texture", "water": "water_texture"}

class MapEditor:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.map = self.create_empty_map()
        self.texture_generator = TextureGenerator((width, height))
=======
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from texture_manager import TextureManager
from map_system import MapSystem
from advanced_texture_renderer import AdvancedTextureRenderer
from material_manager import MaterialBar, MaterialManagerWindow

class MapEditor(tk.Frame):
    def __init__(self, parent, width=50, height=50, map_data=None):
        super().__init__(parent, bg="#2a2a2a")
        self.width = width
        self.height = height
        
        # Map System
        self.map_system = MapSystem()
        
        # Wenn Map-Daten übergeben wurden, diese laden
        if map_data:
            self.width = map_data.get("width", width)
            self.height = map_data.get("height", height)
            self.map = map_data.get("tiles", self.create_empty_map())
            self.river_directions = map_data.get("river_directions", {})  # River-Richtungen
        else:
            self.map = self.create_empty_map()
            self.river_directions = {}  # River-Richtungen Dictionary (key: "x,y", value: direction)
        
        # NEUER Advanced Texture Renderer
        self.texture_renderer = AdvancedTextureRenderer()
        
        # Alter Texture Manager für Kompatibilität
        self.texture_manager = TextureManager()
        
        # ANIMATION DEAKTIVIERT für Performance (zu viele PhotoImages)
        self.is_animating = False  # Animation ausgeschaltet
        self.animation_id = None
        self.animation_frame = 0  # Immer Frame 0 = statisch
        
        # River Direction Mode
        self.river_direction_mode = tk.StringVar(value="disabled")  # disabled, up, down, left, right
        
        # Tile-Size FRÜH berechnen (für MaterialBar)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        available_width = screen_width - 50
        available_height = screen_height - 300
        tile_width = available_width / self.width
        tile_height = available_height / self.height
        self.tile_size = int(min(tile_width, tile_height))
        self.tile_size = max(self.tile_size, 16)
        self.tile_size = min(self.tile_size, 64)
        
        self.setup_ui()
>>>>>>> 1b8b352 (Initial commit: Der Eine Ring VTT System)

    def create_empty_map(self):
        return [["empty" for _ in range(self.width)] for _ in range(self.height)]

    def set_tile(self, x, y, terrain_type):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.map[y][x] = terrain_type
<<<<<<< HEAD
=======
    
    def setup_ui(self):
        """UI-Elemente erstellen"""
        # NEUE Material-Leiste (ein-/ausklappbar, scrollbar, A-Z sortiert)
        self.material_bar = MaterialBar(
            self, 
            self.texture_renderer,
            on_material_select=self.select_terrain,
            tile_size=self.tile_size  # Tile-Größe übergeben für Editor
        )
        self.material_bar.pack(side=tk.TOP, fill=tk.X)
        
        # Toolbar
        toolbar = tk.Frame(self, bg="#1a1a1a", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(toolbar, text="🗺️ Map Editor", font=("Arial", 16, "bold"), 
                bg="#1a1a1a", fg="white").pack(side=tk.LEFT, padx=20, pady=10)
        
        # Speichern/Laden Buttons
        file_frame = tk.Frame(toolbar, bg="#1a1a1a")
        file_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(file_frame, text="💾 Speichern", bg="#2a7d2a", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.save_map).pack(side=tk.LEFT, padx=5)
        
        tk.Button(file_frame, text="📁 Laden", bg="#2a5d8d", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.load_map).pack(side=tk.LEFT, padx=5)
        
        tk.Button(file_frame, text="� Material-Manager", bg="#5d2a7d", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.open_material_manager).pack(side=tk.LEFT, padx=5)
        
        # River Direction Controls
        river_frame = tk.Frame(toolbar, bg="#1a1a1a")
        river_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(river_frame, text="🌊 Flussrichtung:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(river_frame, text="Aus", variable=self.river_direction_mode,
                      value="disabled", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        # Kardinal-Richtungen
        tk.Radiobutton(river_frame, text="↑", variable=self.river_direction_mode,
                      value="up", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        tk.Radiobutton(river_frame, text="↓", variable=self.river_direction_mode,
                      value="down", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        tk.Radiobutton(river_frame, text="←", variable=self.river_direction_mode,
                      value="left", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        tk.Radiobutton(river_frame, text="→", variable=self.river_direction_mode,
                      value="right", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        # Separator
        tk.Label(river_frame, text="|", bg="#1a1a1a", fg="#666").pack(side=tk.LEFT, padx=3)
        
        # Diagonale Richtungen
        tk.Radiobutton(river_frame, text="↖", variable=self.river_direction_mode,
                      value="up-left", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        tk.Radiobutton(river_frame, text="↗", variable=self.river_direction_mode,
                      value="up-right", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        tk.Radiobutton(river_frame, text="↙", variable=self.river_direction_mode,
                      value="down-left", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        tk.Radiobutton(river_frame, text="↘", variable=self.river_direction_mode,
                      value="down-right", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_river_mode_status).pack(side=tk.LEFT)
        
        # Canvas für die Karte
        canvas_frame = tk.Frame(self, bg="#2a2a2a")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scroll = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        # Grid zeichnen - Tile-Größe dynamisch an Bildschirm anpassen
        # Hole echte verfügbare Bildschirm-Größe
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Reserviere Platz für UI-Elemente (MaterialBar ~200px, Toolbar ~60px, Scrollbars ~20px)
        available_width = screen_width - 50  # Kleine Ränder
        available_height = screen_height - 300  # UI-Elemente + Ränder
        
        tile_width = available_width / self.width
        tile_height = available_height / self.height
        
        self.tile_size = int(min(tile_width, tile_height))
        self.tile_size = max(self.tile_size, 16)  # Minimum 16px statt 20px
        self.tile_size = min(self.tile_size, 64)  # Maximum bleibt 64px
        
        # Canvas-Größe an berechnete Map-Größe anpassen
        canvas_width = self.width * self.tile_size
        canvas_height = self.height * self.tile_size
        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        self.selected_terrain = "grass"
        self.show_coordinates = tk.BooleanVar(value=True)
        
        # Koordinaten-Toggle in Toolbar
        coord_check = tk.Checkbutton(toolbar, text="📍 Koordinaten", 
                                     variable=self.show_coordinates,
                                     bg="#1a1a1a", fg="white",
                                     selectcolor="#2a2a2a",
                                     font=("Arial", 9),
                                     command=self.draw_grid)
        coord_check.pack(side=tk.RIGHT, padx=10)
        
        self.draw_grid()
        
        # Maus-Events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        
        # Animation starten
        self.start_animation()
    
    def open_material_manager(self):
        """Öffnet den Material-Manager"""
        MaterialManagerWindow(self, self.texture_renderer)
    
    def select_terrain(self, terrain):
        """Terrain auswählen"""
        self.selected_terrain = terrain
        # Aktualisiere Material-Bar Auswahl
        # (wird von MaterialBar selbst verwaltet)
    
    def draw_grid(self):
        """Grid mit Texturen und optionalen Koordinaten zeichnen"""
        self.canvas.delete("all")
        self.canvas.image_refs = []  # Für PhotoImage-Referenzen
        
        for y in range(self.height):
            for x in range(self.width):
                x1 = x * self.tile_size
                y1 = y * self.tile_size
                
                terrain = self.map[y][x]
                
                # River direction lookup für water tiles
                river_direction = "right"  # Default
                if terrain == "water":
                    coord_key = f"{x},{y}"
                    river_direction = self.river_directions.get(coord_key, "right")
                
                # NEUE Textur vom Advanced Renderer holen
                texture_img = self.texture_renderer.get_texture(
                    terrain, 
                    self.tile_size, 
                    self.animation_frame,
                    river_direction
                )
                
                if texture_img:
                    # SPECIAL: Village gibt größeres Bild zurück (3x) - richtig positionieren
                    if terrain == 'village' and texture_img.size[0] > self.tile_size:
                        # Village-Gebäude am UNTEREN Rand des Tiles ausrichten
                        offset_x = x1
                        offset_y = y1 - int(self.tile_size * 2)  # 2 Tiles nach oben!
                        photo = ImageTk.PhotoImage(texture_img)
                        self.canvas.create_image(offset_x, offset_y, image=photo, anchor=tk.NW, 
                                               tags=f"tile_{x}_{y}")
                        self.canvas.image_refs.append(photo)
                    else:
                        # Als PhotoImage für Canvas
                        photo = ImageTk.PhotoImage(texture_img)
                        self.canvas.create_image(x1, y1, image=photo, anchor=tk.NW, 
                                               tags=f"tile_{x}_{y}")
                        self.canvas.image_refs.append(photo)
                else:
                    # Fallback
                    color = self.texture_manager.get_color(terrain)
                    self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size,
                                                fill=color, outline="#333333",
                                                tags=f"tile_{x}_{y}")
                
                # Koordinaten anzeigen (wenn aktiviert)
                if self.show_coordinates.get():
                    coord_text = f"{x},{y}"
                    text_x = x1 + self.tile_size // 2
                    text_y = y1 + self.tile_size // 2
                    
                    # Schatten für bessere Lesbarkeit
                    self.canvas.create_text(text_x + 1, text_y + 1, 
                                          text=coord_text,
                                          fill="black",
                                          font=("Arial", 6, "bold"),
                                          tags="coordinates")
                    # Text
                    self.canvas.create_text(text_x, text_y, 
                                          text=coord_text,
                                          fill="white",
                                          font=("Arial", 6, "bold"),
                                          tags="coordinates")
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_click(self, event):
        """Mausklick auf Canvas"""
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if 0 <= x < self.width and 0 <= y < self.height:
            # Check if river direction mode is active
            river_mode = self.river_direction_mode.get()
            if river_mode != "disabled":
                # Set river direction for this tile (only if it's water)
                if self.map[y][x] == "water":
                    coord_key = f"{x},{y}"
                    self.river_directions[coord_key] = river_mode
                    self.update_tile(x, y)  # Refresh tile with new direction
            else:
                # Normal tile placement
                self.set_tile(x, y, self.selected_terrain)
                
                # Auto-detect river direction for water tiles
                if self.selected_terrain == "water":
                    self.auto_detect_river_direction(x, y)
                
                self.update_tile(x, y)
    
    def on_canvas_drag(self, event):
        """Maus-Drag für kontinuierliches Zeichnen"""
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if 0 <= x < self.width and 0 <= y < self.height:
            # Check if river direction mode is active
            river_mode = self.river_direction_mode.get()
            if river_mode != "disabled":
                # Set river direction for water tiles while dragging
                if self.map[y][x] == "water":
                    coord_key = f"{x},{y}"
                    if self.river_directions.get(coord_key) != river_mode:  # Only update if changed
                        self.river_directions[coord_key] = river_mode
                        self.update_tile(x, y)
            else:
                # Normal tile placement
                if self.map[y][x] != self.selected_terrain:  # Nur wenn anders
                    self.set_tile(x, y, self.selected_terrain)
                    
                    # Auto-detect river direction for water tiles
                    if self.selected_terrain == "water":
                        self.auto_detect_river_direction(x, y)
                    
                    self.update_tile(x, y)
    
    def update_tile(self, x, y):
        """Einzelnes Tile aktualisieren"""
        terrain = self.map[y][x]
        
        x1 = x * self.tile_size
        y1 = y * self.tile_size
        
        # Altes Tile löschen (mit allen zugehörigen Elementen)
        self.canvas.delete(f"tile_{x}_{y}")
        
        # River direction lookup für water tiles
        river_direction = "right"  # Default
        if terrain == "water":
            coord_key = f"{x},{y}"
            river_direction = self.river_directions.get(coord_key, "right")
        
        # NEUE Textur vom Advanced Renderer
        # WICHTIG: Immer Frame 0 (statisch) im Editor für Performance!
        texture_img = self.texture_renderer.get_texture(
            terrain, 
            self.tile_size, 
            0,  # IMMER Frame 0 = keine Animation im Editor
            river_direction
        )
        
        if texture_img:
            # SPECIAL: Village gibt größeres Bild zurück (3x) - richtig positionieren
            if terrain == 'village' and texture_img.size[0] > self.tile_size:
                # Village-Gebäude am UNTEREN Rand des Tiles ausrichten
                # Rauch ragt 2 Tiles nach oben
                offset_x = x1
                offset_y = y1 - int(self.tile_size * 2)  # 2 Tiles nach oben!
                photo = ImageTk.PhotoImage(texture_img)
                self.canvas.create_image(offset_x, offset_y, image=photo, anchor=tk.NW, 
                                       tags=f"tile_{x}_{y}")
                self.canvas.image_refs.append(photo)
            else:
                photo = ImageTk.PhotoImage(texture_img)
                self.canvas.create_image(x1, y1, image=photo, anchor=tk.NW, 
                                       tags=f"tile_{x}_{y}")
                self.canvas.image_refs.append(photo)
        else:
            color = self.texture_manager.get_color(terrain)
            self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size,
                                        fill=color, outline="#333333",
                                        tags=f"tile_{x}_{y}")
        
        # Koordinaten neu zeichnen (wenn aktiviert)
        if self.show_coordinates.get():
            coord_text = f"{x},{y}"
            text_x = x1 + self.tile_size // 2
            text_y = y1 + self.tile_size // 2
            
            # Schatten
            self.canvas.create_text(text_x + 1, text_y + 1, 
                                  text=coord_text,
                                  fill="black",
                                  font=("Arial", 6, "bold"),
                                  tags=f"tile_{x}_{y}")
            # Text
            self.canvas.create_text(text_x, text_y, 
                                  text=coord_text,
                                  fill="white",
                                  font=("Arial", 6, "bold"),
                                  tags=f"tile_{x}_{y}")
    
    def update_river_mode_status(self):
        """Called when river direction mode changes"""
        mode = self.river_direction_mode.get()
        if mode != "disabled":
            # Update window title to show active mode
            direction_names = {
                "up": "↑ Oben", 
                "down": "↓ Unten", 
                "left": "← Links", 
                "right": "→ Rechts",
                "up-left": "↖ Oben-Links",
                "up-right": "↗ Oben-Rechts",
                "down-left": "↙ Unten-Links",
                "down-right": "↘ Unten-Rechts"
            }
            self.master.title(f"Der Eine Ring - Map Editor [Flussrichtung: {direction_names[mode]}]")
        else:
            self.master.title("Der Eine Ring - Map Editor")
    
    def auto_detect_river_direction(self, x, y):
        """
        Automatische Erkennung der Flussrichtung basierend auf benachbarten Water-Tiles.
        Analysiert die Ausrichtung des gesamten Flusses (horizontal/vertikal/diagonal).
        """
        # Prüfe alle 8 Nachbarn
        neighbors = []
        directions_map = {
            (0, -1): "up",     # Oben
            (0, 1): "down",    # Unten
            (-1, 0): "left",   # Links
            (1, 0): "right",   # Rechts
            (-1, -1): "up-left",    # Diagonal oben-links
            (1, -1): "up-right",    # Diagonal oben-rechts
            (-1, 1): "down-left",   # Diagonal unten-links
            (1, 1): "down-right"    # Diagonal unten-rechts
        }
        
        neighbor_directions = []
        for dx, dy in directions_map.keys():
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if self.map[ny][nx] == "water":
                    coord_key = f"{nx},{ny}"
                    # Hole die Richtung des Nachbarn (falls gesetzt)
                    neighbor_dir = self.river_directions.get(coord_key)
                    if neighbor_dir:
                        neighbor_directions.append(neighbor_dir)
                    neighbors.append((dx, dy))
        
        # Wenn es Nachbarn mit Richtungen gibt, übernehme die häufigste
        if neighbor_directions:
            # Zähle Häufigkeit der Richtungen
            from collections import Counter
            direction_count = Counter(neighbor_directions)
            most_common_direction = direction_count.most_common(1)[0][0]
            coord_key = f"{x},{y}"
            self.river_directions[coord_key] = most_common_direction
            return
        
        # Keine Nachbarn mit Richtung - erkenne aus Geometrie
        if not neighbors:
            # Kein Nachbar - Default "right"
            coord_key = f"{x},{y}"
            self.river_directions[coord_key] = "right"
            return
        
        # Analysiere geometrische Anordnung der Nachbarn
        # Zähle in welche Richtungen Nachbarn liegen
        has_up = any(dy < 0 for dx, dy in neighbors)      # Nachbar oben
        has_down = any(dy > 0 for dx, dy in neighbors)    # Nachbar unten
        has_left = any(dx < 0 for dx, dy in neighbors)    # Nachbar links
        has_right = any(dx > 0 for dx, dy in neighbors)   # Nachbar rechts
        
        # Zähle wie viele Nachbarn in jede Richtung
        up_count = sum(1 for dx, dy in neighbors if dy < 0)
        down_count = sum(1 for dx, dy in neighbors if dy > 0)
        left_count = sum(1 for dx, dy in neighbors if dx < 0)
        right_count = sum(1 for dx, dy in neighbors if dx > 0)
        
        # LOGIK: Wenn Nachbarn oben sind, fließt Wasser nach unten
        #        Wenn Nachbarn links sind, fließt Wasser nach rechts
        
        # Berechne Flow-Tendenz
        # Mehr oben = fließt nach unten, mehr unten = fließt nach oben
        vertical_tendency = up_count - down_count  # Positiv = fließt nach unten
        horizontal_tendency = left_count - right_count  # Positiv = fließt nach rechts
        
        # Entscheide welche Richtung dominiert
        # NEUE LOGIK: Wenn BEIDE Richtungen signifikant sind (>0), dann DIAGONAL!
        abs_v = abs(vertical_tendency)
        abs_h = abs(horizontal_tendency)
        
        # Beide Richtungen vorhanden? → Diagonal (auch wenn nicht gleich stark!)
        if abs_v > 0 and abs_h > 0:
            # DIAGONAL - kombiniere beide Richtungen
            if vertical_tendency > 0 and horizontal_tendency > 0:
                direction = "down-right"  # Nachbarn oben-links → fließt unten-rechts
            elif vertical_tendency > 0 and horizontal_tendency < 0:
                direction = "down-left"   # Nachbarn oben-rechts → fließt unten-links
            elif vertical_tendency < 0 and horizontal_tendency > 0:
                direction = "up-right"    # Nachbarn unten-links → fließt oben-rechts
            elif vertical_tendency < 0 and horizontal_tendency < 0:
                direction = "up-left"     # Nachbarn unten-rechts → fließt oben-links
            else:
                direction = "right"  # Fallback
                
        # Nur eine Richtung dominant?
        elif abs_h > abs_v:
            # Horizontaler Fluss dominiert
            direction = "right" if horizontal_tendency > 0 else "left"
        elif abs_v > abs_h:
            # Vertikaler Fluss dominiert
            direction = "down" if vertical_tendency > 0 else "up"
        else:
            # Beide 0 - Default
            direction = "right"
        
        coord_key = f"{x},{y}"
        self.river_directions[coord_key] = direction
    
    def save_map(self):
        """Karte speichern"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialdir="maps"
        )
        
        if filename:
            map_data = {
                "width": self.width,
                "height": self.height,
                "tiles": self.map
            }
            
            try:
                self.map_system.export_map(map_data, filename)
                messagebox.showinfo("Erfolg", f"Karte gespeichert:\n{filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}")
    
    def load_map(self):
        """Karte laden"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialdir="maps"
        )
        
        if filename:
            try:
                map_data = self.map_system.load_map(filename)
                
                if map_data:
                    self.width = map_data["width"]
                    self.height = map_data["height"]
                    self.map = map_data["tiles"]
                    
                    # Neu zeichnen
                    self.draw_grid()
                    messagebox.showinfo("Erfolg", f"Karte geladen:\n{filename}")
                else:
                    messagebox.showerror("Fehler", "Karte konnte nicht geladen werden")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
    
    def get_map_data(self):
        """Gibt die aktuellen Map-Daten zurück"""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.map,
            "river_directions": self.river_directions
        }
    
    def start_animation(self):
        """Startet die Wasser-Animation"""
        # DEAKTIVIERT im Editor für Performance
        # Animation nur im Projektor-Modus
        pass
    
    def animate_water(self):
        """Animiert Wasser und andere animierte Tiles im Editor"""
        # DEAKTIVIERT - Editor zeigt nur statische Texturen
        # Verhindert Ruckeln und "Fail to allocate bitmap" Fehler
        return
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        self.is_animating = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()
>>>>>>> 1b8b352 (Initial commit: Der Eine Ring VTT System)

class DerEineRingApp:
    def __init__(self):
        self.map_editor = MapEditor(10, 10)

    def run(self):
        # Main loop for the application
        print("Running Der Eine Ring Map Editor")
        self.map_editor.set_tile(0, 0, "grass")

if __name__ == "__main__":
    app = DerEineRingApp()
    app.run()