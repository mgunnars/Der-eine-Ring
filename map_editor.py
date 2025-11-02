"""
Map Editor für "Der Eine Ring"
Vollständiger Karten-Editor mit Material-Manager und River-Direktions-System
Extrahiert aus main.py für modulare Nutzung
"""
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
            self.river_directions = map_data.get("river_directions", {})
        else:
            self.map = self.create_empty_map()
            self.river_directions = {}
        
        # Advanced Texture Renderer
        self.texture_renderer = AdvancedTextureRenderer()
        
        # Texture Manager für Kompatibilität
        self.texture_manager = TextureManager()
        
        # Animation deaktiviert im Editor (Performance)
        self.is_animating = False
        self.animation_id = None
        self.animation_frame = 0
        
        # River Direction Mode
        self.river_direction_mode = tk.StringVar(value="disabled")
        
        # Tile-Size berechnen
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
        # Material-Leiste
        self.material_bar = MaterialBar(
            self, 
            self.texture_renderer,
            on_material_select=self.select_terrain,
            tile_size=self.tile_size
        )
        self.material_bar.pack(side=tk.TOP, fill=tk.X)
        
        # Toolbar
        toolbar = tk.Frame(self, bg="#1a1a1a", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(toolbar, text="🗺️ Map Editor", font=("Arial", 16, "bold"), 
                bg="#1a1a1a", fg="white").pack(side=tk.LEFT, padx=20, pady=10)
        
        # Buttons
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
        
        # Canvas
        canvas_frame = tk.Frame(self, bg="#2a2a2a")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        
        # Canvas-Größe
        canvas_width = self.width * self.tile_size
        canvas_height = self.height * self.tile_size
        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        self.selected_terrain = "grass"
        self.show_coordinates = tk.BooleanVar(value=True)
        
        # Koordinaten-Toggle
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
    
    def open_material_manager(self):
        """Öffnet den Material-Manager"""
        MaterialManagerWindow(self, self.texture_renderer)
    
    def select_terrain(self, terrain):
        """Terrain auswählen"""
        self.selected_terrain = terrain
    
    def draw_grid(self):
        """Grid zeichnen"""
        self.canvas.delete("all")
        self.canvas.image_refs = []
        
        for y in range(self.height):
            for x in range(self.width):
                x1 = x * self.tile_size
                y1 = y * self.tile_size
                
                terrain = self.map[y][x]
                
                # Textur rendern
                texture_img = self.texture_renderer.get_texture(
                    terrain, 
                    self.tile_size, 
                    0  # Statisch
                )
                
                if texture_img:
                    if terrain == 'village' and texture_img.size[0] > self.tile_size:
                        offset_x = x1
                        offset_y = y1 - int(self.tile_size * 2)
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
                
                # Koordinaten
                if self.show_coordinates.get():
                    coord_text = f"{x},{y}"
                    text_x = x1 + self.tile_size // 2
                    text_y = y1 + self.tile_size // 2
                    
                    self.canvas.create_text(text_x + 1, text_y + 1, 
                                          text=coord_text,
                                          fill="black",
                                          font=("Arial", 6, "bold"),
                                          tags="coordinates")
                    self.canvas.create_text(text_x, text_y, 
                                          text=coord_text,
                                          fill="white",
                                          font=("Arial", 6, "bold"),
                                          tags="coordinates")
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_click(self, event):
        """Mausklick"""
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if 0 <= x < self.width and 0 <= y < self.height:
            self.set_tile(x, y, self.selected_terrain)
            self.update_tile(x, y)
    
    def on_canvas_drag(self, event):
        """Drag"""
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.map[y][x] != self.selected_terrain:
                self.set_tile(x, y, self.selected_terrain)
                self.update_tile(x, y)
    
    def update_tile(self, x, y):
        """Einzelnes Tile aktualisieren"""
        terrain = self.map[y][x]
        
        x1 = x * self.tile_size
        y1 = y * self.tile_size
        
        self.canvas.delete(f"tile_{x}_{y}")
        
        texture_img = self.texture_renderer.get_texture(terrain, self.tile_size, 0)
        
        if texture_img:
            if terrain == 'village' and texture_img.size[0] > self.tile_size:
                offset_x = x1
                offset_y = y1 - int(self.tile_size * 2)
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
        
        if self.show_coordinates.get():
            coord_text = f"{x},{y}"
            text_x = x1 + self.tile_size // 2
            text_y = y1 + self.tile_size // 2
            
            self.canvas.create_text(text_x + 1, text_y + 1, 
                                  text=coord_text,
                                  fill="black",
                                  font=("Arial", 6, "bold"),
                                  tags=f"tile_{x}_{y}")
            self.canvas.create_text(text_x, text_y, 
                                  text=coord_text,
                                  fill="white",
                                  font=("Arial", 6, "bold"),
                                  tags=f"tile_{x}_{y}")
    
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
                "tiles": self.map,
                "river_directions": self.river_directions
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
                    self.river_directions = map_data.get("river_directions", {})
                    
                    self.draw_grid()
                    messagebox.showinfo("Erfolg", f"Karte geladen:\n{filename}")
                else:
                    messagebox.showerror("Fehler", "Karte konnte nicht geladen werden")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
    
    def get_map_data(self):
        """Gibt Map-Daten zurück"""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.map,
            "river_directions": self.river_directions
        }
    
    def destroy(self):
        """Aufräumen"""
        self.is_animating = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()
