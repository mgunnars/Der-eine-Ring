import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from texture_manager import TextureManager
from map_system import MapSystem
from advanced_texture_renderer import AdvancedTextureRenderer
from material_manager import MaterialBar, MaterialManagerWindow
from svg_map_exporter import SVGMapExporter
from svg_projector import SVGProjectorWindow

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

    def create_empty_map(self):
        return [["empty" for _ in range(self.width)] for _ in range(self.height)]

    def set_tile(self, x, y, terrain_type):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.map[y][x] = terrain_type
    
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
        
        tk.Button(file_frame, text="🎨 Material-Manager", bg="#5d2a7d", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.open_material_manager).pack(side=tk.LEFT, padx=5)
        
        # SVG Export & Projektor
        tk.Button(file_frame, text="📐 Als SVG", bg="#7d5d2a", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.export_as_svg).pack(side=tk.LEFT, padx=5)
        
        tk.Button(file_frame, text="🎬 SVG Projektor", bg="#2a7d7d", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.open_svg_projector).pack(side=tk.LEFT, padx=5)
        
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
        
        # Separator
        tk.Label(river_frame, text="|", bg="#1a1a1a", fg="#666").pack(side=tk.LEFT, padx=3)
        
        # Anzeige-Toggle für Flussrichtungs-Vektoren
        self.show_river_vectors = tk.BooleanVar(value=False)
        tk.Checkbutton(river_frame, text="📊 Vektoren", variable=self.show_river_vectors,
                      bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.draw_grid).pack(side=tk.LEFT, padx=2)
        
        # Button zum Umkehren aller verbundenen Flüsse
        tk.Button(river_frame, text="🔄 Fluss umkehren", bg="#5d2a7d", fg="white",
                 font=("Arial", 8), padx=8, pady=2,
                 command=self.reverse_river_flow).pack(side=tk.LEFT, padx=5)
        
        # Canvas für die Karte - EXPANDED LAYOUT
        canvas_frame = tk.Frame(self, bg="#2a2a2a")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas nimmt jetzt VOLLEN Platz ein
        self.canvas = tk.Canvas(canvas_frame, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scroll_frame = tk.Frame(self, bg="#2a2a2a")
        h_scroll_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        h_scroll = tk.Scrollbar(h_scroll_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.TOP, fill=tk.X)
        
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
    
    def export_as_svg(self):
        """Exportiert die aktuelle Karte als SVG"""
        # Datei-Dialog
        filename = filedialog.asksaveasfilename(
            title="Karte als SVG speichern",
            defaultextension=".svg",
            filetypes=[("SVG Dateien", "*.svg"), ("Alle Dateien", "*.*")]
        )
        
        if not filename:
            return
        
        # Auflösungs-Dialog
        resolution = tk.StringVar(value="high")
        dialog = tk.Toplevel(self)
        dialog.title("SVG Export Einstellungen")
        dialog.geometry("400x250")
        dialog.configure(bg="#2a2a2a")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="🎨 SVG Export Einstellungen", 
                bg="#2a2a2a", fg="white", font=("Arial", 14, "bold")).pack(pady=15)
        
        tk.Label(dialog, text="Render-Qualität:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(pady=5)
        
        tk.Radiobutton(dialog, text="🟢 Low (256px) - Schnell, kleine Datei", 
                      variable=resolution, value="low",
                      bg="#2a2a2a", fg="white", selectcolor="#333",
                      font=("Arial", 10)).pack(anchor=tk.W, padx=30)
        
        tk.Radiobutton(dialog, text="🟡 High (512px) - Empfohlen für Projektor", 
                      variable=resolution, value="high",
                      bg="#2a2a2a", fg="white", selectcolor="#333",
                      font=("Arial", 10)).pack(anchor=tk.W, padx=30)
        
        tk.Radiobutton(dialog, text="🔴 Ultra (1024px) - Maximale Qualität (langsam)", 
                      variable=resolution, value="ultra",
                      bg="#2a2a2a", fg="white", selectcolor="#333",
                      font=("Arial", 10)).pack(anchor=tk.W, padx=30)
        
        embed_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dialog, text="Bilder einbetten (größere Datei, aber portabel)",
                      variable=embed_var, bg="#2a2a2a", fg="white",
                      selectcolor="#333", font=("Arial", 9)).pack(pady=10)
        
        def do_export():
            dialog.destroy()
            
            # Map-Daten konvertieren
            map_data = {}
            for y in range(self.height):
                for x in range(self.width):
                    terrain = self.map[y][x]
                    if terrain != "empty":
                        map_data[(x, y)] = terrain
            
            # Materials sammeln (für Renderer)
            materials = self.texture_renderer.registered_materials
            
            # SVG Exporter
            exporter = SVGMapExporter(tile_size=self.tile_size)
            
            try:
                success = exporter.export_map_to_svg(
                    map_data,
                    materials,
                    self.texture_renderer,
                    filename,
                    embed_images=embed_var.get(),
                    render_resolution=resolution.get()
                )
                
                if success:
                    messagebox.showinfo("Erfolg", 
                        f"✅ Karte erfolgreich als SVG exportiert!\n\n"
                        f"Datei: {filename}\n"
                        f"Qualität: {resolution.get()}\n\n"
                        f"Öffne mit 'SVG Projektor' für beste Darstellung!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
        
        tk.Button(dialog, text="📐 Exportieren", bg="#2a7d2a", fg="white",
                 font=("Arial", 11, "bold"), padx=30, pady=8,
                 command=do_export).pack(pady=15)
    
    def open_svg_projector(self):
        """Öffnet den SVG-Projektor"""
        # SVG-Datei auswählen
        filename = filedialog.askopenfilename(
            title="SVG-Karte für Projektor laden",
            filetypes=[("SVG Dateien", "*.svg"), ("Alle Dateien", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            # SVG Projektor Fenster öffnen
            projector = SVGProjectorWindow(filename, fullscreen=False)
            messagebox.showinfo("SVG Projektor", 
                "🎬 SVG Projektor geöffnet!\n\n"
                "Steuerung:\n"
                "• F11: Vollbild\n"
                "• +/-: Zoom\n"
                "• R: Ansicht zurücksetzen\n"
                "• G: Grid ein/aus\n"
                "• ESC: Schließen")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte SVG nicht laden:\n{e}")
    
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
                
                # Flussrichtungs-Vektoren anzeigen (wenn aktiviert und Water-Tile)
                if self.show_river_vectors.get() and terrain == "water":
                    coord_key = f"{x},{y}"
                    direction = self.river_directions.get(coord_key, "right")
                    self.draw_river_vector(x1, y1, direction)
        
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
    
    def draw_river_vector(self, x1, y1, direction):
        """Zeichnet einen Vektor-Pfeil für die Flussrichtung"""
        center_x = x1 + self.tile_size // 2
        center_y = y1 + self.tile_size // 2
        
        # Pfeil-Länge
        arrow_length = self.tile_size // 3
        
        # Richtungs-Vektoren
        direction_vectors = {
            "right": (1, 0),
            "left": (-1, 0),
            "down": (0, 1),
            "up": (0, -1),
            "down-right": (0.707, 0.707),
            "down-left": (-0.707, 0.707),
            "up-right": (0.707, -0.707),
            "up-left": (-0.707, -0.707)
        }
        
        dx, dy = direction_vectors.get(direction, (1, 0))
        
        # End-Punkt des Pfeils
        end_x = center_x + dx * arrow_length
        end_y = center_y + dy * arrow_length
        
        # Zeichne Pfeil mit Schatten für bessere Sichtbarkeit
        # Schatten
        self.canvas.create_line(
            center_x + 1, center_y + 1, end_x + 1, end_y + 1,
            fill="black", width=3, arrow=tk.LAST,
            tags="river_vector"
        )
        # Pfeil
        self.canvas.create_line(
            center_x, center_y, end_x, end_y,
            fill="#00ff00", width=2, arrow=tk.LAST,
            tags="river_vector"
        )
    
    def reverse_river_flow(self):
        """Kehrt die Flussrichtung aller verbundenen Water-Tiles um"""
        if not messagebox.askyesno(
            "Flussrichtung umkehren",
            "Möchten Sie die Flussrichtung aller verbundenen Wasser-Tiles umkehren?"
        ):
            return
        
        # Umkehr-Mapping
        reverse_map = {
            "right": "left",
            "left": "right",
            "up": "down",
            "down": "up",
            "up-right": "down-left",
            "down-left": "up-right",
            "up-left": "down-right",
            "down-right": "up-left"
        }
        
        # Finde alle Water-Tiles und kehre ihre Richtung um
        updated_count = 0
        for y in range(self.height):
            for x in range(self.width):
                if self.map[y][x] == "water":
                    coord_key = f"{x},{y}"
                    if coord_key in self.river_directions:
                        old_dir = self.river_directions[coord_key]
                        new_dir = reverse_map.get(old_dir, old_dir)
                        self.river_directions[coord_key] = new_dir
                        updated_count += 1
        
        # Karte neu zeichnen
        self.draw_grid()
        
        messagebox.showinfo(
            "Erfolg",
            f"Flussrichtung von {updated_count} Wasser-Tiles wurde umgekehrt!"
        )
    
    def auto_detect_river_direction(self, x, y):
        """
        Automatische Erkennung der Flussrichtung basierend auf benachbarten Water-Tiles.
        
        LOGIK:
        - Platziert User rechts von existierendem Wasser → Fluss von links nach rechts
        - Platziert User links → Fluss von rechts nach links  
        - Platziert User oben → Fluss von unten nach oben
        - Platziert User unten → Fluss von oben nach unten
        - Diagonale Muster (Dreieck) → Diagonale Flussrichtung
        - Zickzack → Folge dem Vektor der Linie (immer diagonal)
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
        
        # PRIORITÄT 1: Wenn Nachbarn bereits Richtungen haben, übernehme die häufigste
        if neighbor_directions:
            from collections import Counter
            direction_count = Counter(neighbor_directions)
            most_common_direction = direction_count.most_common(1)[0][0]
            coord_key = f"{x},{y}"
            self.river_directions[coord_key] = most_common_direction
            return
        
        # PRIORITÄT 2: Keine Nachbarn - Default "right"
        if not neighbors:
            coord_key = f"{x},{y}"
            self.river_directions[coord_key] = "right"
            return
        
        # PRIORITÄT 3: Analysiere geometrische Anordnung (WO sind die Nachbarn?)
        # Die Richtung ist ENTGEGENGESETZT zur Nachbar-Position!
        # Wenn Nachbar LINKS ist → Wasser fließt nach RECHTS (weg vom Nachbarn)
        
        has_up = any(dy < 0 for dx, dy in neighbors)      # Nachbar oben
        has_down = any(dy > 0 for dx, dy in neighbors)    # Nachbar unten
        has_left = any(dx < 0 for dx, dy in neighbors)    # Nachbar links
        has_right = any(dx > 0 for dx, dy in neighbors)   # Nachbar rechts
        
        # Zähle Nachbarn pro Richtung
        up_count = sum(1 for dx, dy in neighbors if dy < 0 and dx == 0)
        down_count = sum(1 for dx, dy in neighbors if dy > 0 and dx == 0)
        left_count = sum(1 for dx, dy in neighbors if dx < 0 and dy == 0)
        right_count = sum(1 for dx, dy in neighbors if dx > 0 and dy == 0)
        diagonal_count = sum(1 for dx, dy in neighbors if dx != 0 and dy != 0)
        
        # STRATEGIE: Bestimme aus welcher Richtung das Wasser KOMMT
        # (= wo sind die meisten Nachbarn)
        
        # Fall 1: NUR EINE kardinale Richtung hat Nachbarn → Fluss in Gegenrichtung
        if right_count > 0 and left_count == 0 and up_count == 0 and down_count == 0:
            # User platzierte RECHTS von Wasser → Fluss nach links (vom Nachbarn weg)
            # ABER: Spezifikation sagt "rechts davon platziert → links nach rechts"
            # Das bedeutet: Nachbar ist links, neues Tile rechts, Fluss geht nach rechts!
            direction = "right"
        elif left_count > 0 and right_count == 0 and up_count == 0 and down_count == 0:
            # Nachbar ist rechts, neues Tile links → Fluss nach links
            direction = "left"
        elif down_count > 0 and up_count == 0 and left_count == 0 and right_count == 0:
            # Nachbar ist unten, neues Tile oben → Fluss nach oben
            direction = "up"
        elif up_count > 0 and down_count == 0 and left_count == 0 and right_count == 0:
            # Nachbar ist oben, neues Tile unten → Fluss nach unten
            direction = "down"
        
        # Fall 2: Diagonal - wenn hauptsächlich diagonale Nachbarn
        elif diagonal_count > 0 and (up_count + down_count + left_count + right_count) == 0:
            # Nur diagonale Nachbarn → erkenne Diagonal-Muster
            # Finde dominante diagonale Richtung
            has_upleft = any(dx < 0 and dy < 0 for dx, dy in neighbors)
            has_upright = any(dx > 0 and dy < 0 for dx, dy in neighbors)
            has_downleft = any(dx < 0 and dy > 0 for dx, dy in neighbors)
            has_downright = any(dx > 0 and dy > 0 for dx, dy in neighbors)
            
            # Dreieck-Muster: User platziert Diagonale
            # Beispiel: Tile oben-links → Fluss nach unten-rechts
            if has_upleft and not has_downright:
                direction = "down-right"
            elif has_upright and not has_downleft:
                direction = "down-left"
            elif has_downleft and not has_upright:
                direction = "up-right"
            elif has_downright and not has_upleft:
                direction = "up-left"
            else:
                # Mehrere diagonale Nachbarn - nutze Schwerpunkt
                avg_dx = sum(dx for dx, dy in neighbors) / len(neighbors)
                avg_dy = sum(dy for dx, dy in neighbors) / len(neighbors)
                
                # Fluss geht in Gegenrichtung zum Schwerpunkt
                if avg_dx < 0 and avg_dy < 0:
                    direction = "down-right"
                elif avg_dx > 0 and avg_dy < 0:
                    direction = "down-left"
                elif avg_dx < 0 and avg_dy > 0:
                    direction = "up-right"
                else:
                    direction = "up-left"
        
        # Fall 3: Gemischte Nachbarn (horizontal + vertikal oder + diagonal)
        else:
            # Berechne Schwerpunkt aller Nachbarn
            avg_dx = sum(dx for dx, dy in neighbors) / len(neighbors)
            avg_dy = sum(dy for dx, dy in neighbors) / len(neighbors)
            
            # Schwelle für "stark ausgeprägt"
            threshold = 0.3
            
            # Beide Richtungen ausgeprägt → DIAGONAL
            if abs(avg_dx) > threshold and abs(avg_dy) > threshold:
                # Fluss in Gegenrichtung zum Schwerpunkt
                if avg_dx < 0 and avg_dy < 0:
                    direction = "down-right"
                elif avg_dx > 0 and avg_dy < 0:
                    direction = "down-left"
                elif avg_dx < 0 and avg_dy > 0:
                    direction = "up-right"
                else:
                    direction = "up-left"
            
            # Horizontal dominiert
            elif abs(avg_dx) > abs(avg_dy):
                direction = "right" if avg_dx < 0 else "left"
            
            # Vertikal dominiert
            else:
                direction = "down" if avg_dy < 0 else "up"
        
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