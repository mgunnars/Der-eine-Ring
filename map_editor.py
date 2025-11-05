"""
Map Editor für "Der Eine Ring"
Vollständiger Karten-Editor mit Material-Manager und River-Direktions-System
Extrahiert aus main.py für modulare Nutzung
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import subprocess
import sys
import os
from texture_manager import TextureManager
from map_system import MapSystem
from advanced_texture_renderer import AdvancedTextureRenderer
from material_manager import MaterialBar, MaterialManagerWindow
from material_bundle_manager import MaterialBundleManager

class MapEditor(tk.Frame):
    def __init__(self, parent, width=50, height=50, map_data=None):
        super().__init__(parent, bg="#2a2a2a")
        self.width = width
        self.height = height
        
        # Map System
        self.map_system = MapSystem()
        
        # Bundle Manager initialisieren
        self.bundle_manager = MaterialBundleManager()
        
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
        
        # WICHTIG: Custom Materials laden (z.B. von PNG-Import)
        if map_data and "custom_materials" in map_data:
            custom_materials = map_data["custom_materials"]
            print(f"📦 Lade {len(custom_materials)} Custom-Materialien...")
            
            # PRÜFE ob Bundle bereits existiert (verhindert Doppelerstellung!)
            map_name = map_data.get("name", "imported_map")
            bundle_id = f"{map_name.lower().replace(' ', '_')}_bundle"
            
            # Nur erstellen wenn noch nicht vorhanden
            if bundle_id not in self.bundle_manager.bundles and len(custom_materials) > 20:
                self.bundle_manager.create_bundle_from_materials(
                    bundle_id=bundle_id,
                    name=map_name,
                    materials=list(custom_materials.keys()),
                    description=f"Auto-Bundle aus {map_name}",
                    icon="🏘️",
                    always_loaded=False
                )
                print(f"📦 Auto-Bundle erstellt: {bundle_id}")
            else:
                if bundle_id in self.bundle_manager.bundles:
                    print(f"📦 Bundle '{bundle_id}' bereits vorhanden (überspringe Erstellung)")
            
            for mat_id, mat_info in custom_materials.items():
                # Registriere Material im Renderer
                self.texture_renderer.custom_textures[mat_id] = mat_info
                
                # Importiere Textur-Datei
                if 'texture_path' in mat_info:
                    try:
                        self.texture_renderer.import_texture(mat_id, mat_info['texture_path'])
                    except Exception as e:
                        print(f"  ⚠️ Fehler bei {mat_id}: {e}")
            
            print(f"✅ Custom-Materialien geladen!")
            
            # Auto-aktiviere Bundle falls vorhanden
            if bundle_id in self.bundle_manager.bundles:
                self.bundle_manager.activate_bundle(bundle_id)
        
        # Texture Manager für Kompatibilität
        self.texture_manager = TextureManager()
        
        # Animation deaktiviert im Editor (Performance)
        self.is_animating = False
        self.animation_id = None
        self.animation_frame = 0
        
        # River Direction Mode
        self.river_direction_mode = tk.StringVar(value="disabled")
        
        # === FREEHAND DRAWING MODE ===
        self.draw_mode = tk.StringVar(value="tile")  # "tile" oder "brush"
        self.brush_size = 1  # Wie viele Tiles der Pinsel malt
        self.is_drawing = False
        
        # Selected terrain - WICHTIG: Vor UI-Setup initialisieren!
        self.selected_terrain = "grass"
        
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
        
        # Performance-Mode bei großen Maps (>1000 Tiles)
        self.total_tiles = self.width * self.height
        self.performance_mode = self.total_tiles > 1000
        
        if self.performance_mode:
            print(f"⚡ Performance-Mode aktiviert ({self.total_tiles} Tiles)")
            print(f"   - Kleinere Tile-Größe (max 32px)")
            print(f"   - Koordinaten standardmäßig aus")
            self.tile_size = min(self.tile_size, 32)  # Noch kleiner bei großen Maps
        
        self.setup_ui()

    def create_empty_map(self):
        return [["empty" for _ in range(self.width)] for _ in range(self.height)]

    def set_tile(self, x, y, terrain_type):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.map[y][x] = terrain_type
    
    def setup_ui(self):
        """UI-Elemente erstellen - Layout wie MapDraw"""
        
        # =================== TOP TOOLBAR ===================
        top_frame = tk.Frame(self, bg="#1a1a1a", height=60)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        top_frame.pack_propagate(False)
        
        tk.Label(top_frame, text="🗺️ Map Editor", font=("Arial", 16, "bold"), 
                bg="#1a1a1a", fg="white").pack(side=tk.LEFT, padx=20, pady=10)
        
        # File Operations
        file_frame = tk.LabelFrame(top_frame, text="📁 Datei", bg="#1a1a1a", fg="white", font=("Arial", 9))
        file_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)
        
        tk.Button(file_frame, text="💾 Speichern", bg="#2a7d2a", fg="white",
                 font=("Arial", 9), command=self.save_map).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="📁 Laden", bg="#2a5d8d", fg="white",
                 font=("Arial", 9), command=self.load_map).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="📤 SVG", bg="#2a5d7d", fg="white",
                 font=("Arial", 9), command=self.export_as_svg).pack(side=tk.LEFT, padx=2)
        
        # Draw Mode
        mode_frame = tk.LabelFrame(top_frame, text="🖌️ Modus", bg="#1a1a1a", fg="white", font=("Arial", 9))
        mode_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)
        
        tk.Radiobutton(mode_frame, text="📍 Tile", variable=self.draw_mode, value="tile",
                      bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Radiobutton(mode_frame, text="🖌️ Pinsel", variable=self.draw_mode, value="brush",
                      bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # Brush Size
        self.brush_size_var = tk.IntVar(value=1)
        tk.Label(mode_frame, text="Größe:", bg="#1a1a1a", fg="white",
                font=("Arial", 8)).pack(side=tk.LEFT, padx=(10, 2))
        brush_scale = tk.Scale(mode_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                              variable=self.brush_size_var, 
                              command=lambda v: setattr(self, 'brush_size', int(v)),
                              bg="#2a2a2a", fg="white", troughcolor="#1a1a1a",
                              highlightthickness=0, length=80, width=10)
        brush_scale.pack(side=tk.LEFT, padx=2)
        
        # MapDraw Button
        tk.Button(top_frame, text="🎨 MapDraw", bg="#8d5a2a", fg="white",
                 font=("Arial", 10, "bold"), padx=15, pady=5,
                 command=self.open_map_draw).pack(side=tk.RIGHT, padx=20)
        
        # =================== LEFT PANEL - MATERIALS ===================
        left_frame = tk.Frame(self, bg="#1a1a1a", width=300)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="🎨 Materialien", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Bundle Selector
        bundle_selector_frame = tk.Frame(left_frame, bg="#1a1a1a")
        bundle_selector_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(bundle_selector_frame, text="� Bundle:", bg="#1a1a1a", fg="#888",
                font=("Arial", 9)).pack(side=tk.LEFT)
        
        tk.Button(bundle_selector_frame, text="⚙️", bg="#3a3a3a", fg="white",
                 font=("Arial", 8), width=3, command=self.open_bundle_manager).pack(side=tk.RIGHT)
        
        # Bundle buttons
        self.bundle_button_frame = tk.Frame(left_frame, bg="#1a1a1a")
        self.bundle_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.bundle_buttons = {}
        self.refresh_bundle_buttons()
        
        # Material List (scrollable)
        material_list_frame = tk.Frame(left_frame, bg="#1a1a1a")
        material_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        material_canvas = tk.Canvas(material_list_frame, bg="#2a2a2a", highlightthickness=0)
        material_scrollbar = tk.Scrollbar(material_list_frame, orient=tk.VERTICAL, 
                                         command=material_canvas.yview)
        
        self.material_list_inner = tk.Frame(material_canvas, bg="#2a2a2a")
        
        material_canvas.create_window((0, 0), window=self.material_list_inner, anchor=tk.NW)
        material_canvas.configure(yscrollcommand=material_scrollbar.set)
        
        material_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        material_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.material_list_canvas = material_canvas
        self.material_list_inner.bind("<Configure>", 
            lambda e: material_canvas.configure(scrollregion=material_canvas.bbox("all")))
        
        self.populate_material_list()
        
        # =================== CANVAS - CENTER ===================
        canvas_frame = tk.Frame(self, bg="#2a2a2a")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        
        # Koordinaten standardmäßig AUS bei Performance-Mode
        default_coords = not self.performance_mode
        self.show_coordinates = tk.BooleanVar(value=default_coords)
        
        # =================== RIGHT PANEL - SETTINGS ===================
        right_frame = tk.Frame(self, bg="#1a1a1a", width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="⚙️ Einstellungen", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Map Info
        info_frame = tk.LabelFrame(right_frame, text="📊 Karten-Info", bg="#1a1a1a", 
                                   fg="white", font=("Arial", 9, "bold"))
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(info_frame, text=f"Größe: {self.width}×{self.height}", 
                bg="#1a1a1a", fg="#aaa", font=("Arial", 9)).pack(pady=2)
        tk.Label(info_frame, text=f"Tiles: {self.total_tiles}", 
                bg="#1a1a1a", fg="#aaa", font=("Arial", 9)).pack(pady=2)
        tk.Label(info_frame, text=f"Tile-Größe: {self.tile_size}px", 
                bg="#1a1a1a", fg="#aaa", font=("Arial", 9)).pack(pady=2)
        
        if self.performance_mode:
            tk.Label(info_frame, text="⚡ Performance-Mode", 
                    bg="#1a1a1a", fg="#ff8800", font=("Arial", 9, "bold")).pack(pady=2)
        
        # Display Options
        display_frame = tk.LabelFrame(right_frame, text="👁️ Anzeige", bg="#1a1a1a", 
                                      fg="white", font=("Arial", 9, "bold"))
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Checkbutton(display_frame, text="Koordinaten", variable=self.show_coordinates,
                      bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 9), command=self.draw_grid).pack(anchor=tk.W, padx=5, pady=2)
        
        # River Direction
        river_frame = tk.LabelFrame(right_frame, text="🌊 Fluss-Richtung", bg="#1a1a1a",
                                    fg="white", font=("Arial", 9, "bold"))
        river_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Radiobutton(river_frame, text="Aus", variable=self.river_direction_mode, value="disabled",
                      bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 8), command=self.draw_grid).pack(anchor=tk.W, padx=5)
        
        for direction in ["↑ Norden", "→ Osten", "↓ Süden", "← Westen"]:
            dir_val = direction.split()[1].lower()
            tk.Radiobutton(river_frame, text=direction, 
                          variable=self.river_direction_mode, value=dir_val,
                          bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                          font=("Arial", 8), command=self.draw_grid).pack(anchor=tk.W, padx=5)
        
        # Tools
        tools_frame = tk.LabelFrame(right_frame, text="🛠️ Werkzeuge", bg="#1a1a1a",
                                    fg="white", font=("Arial", 9, "bold"))
        tools_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(tools_frame, text="🎨 Material-Manager", bg="#5d2a7d", fg="white",
                 font=("Arial", 9), width=18,
                 command=self.open_material_manager).pack(pady=3, padx=5)
        
        tk.Button(tools_frame, text="🖼️ Vorschau", bg="#2a5d8d", fg="white",
                 font=("Arial", 9), width=18,
                 command=self.show_preview).pack(pady=3, padx=5)
        
        self.draw_grid()
        
        # Info bei Performance-Mode
        if self.performance_mode:
            info_msg = (
                f"⚡ Performance-Mode aktiviert!\n\n"
                f"Diese Map ist groß ({self.width}×{self.height} = {self.total_tiles} Tiles).\n\n"
                f"Optimierungen:\n"
                f"• Tile-Größe reduziert auf {self.tile_size}px\n"
                f"• Koordinaten standardmäßig aus\n"
                f"• Rendering optimiert\n\n"
                f"Tipp: Zoome im Canvas für Details!"
            )
        
        # Zoom-Level initialisieren
        self.zoom_level = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        
        # Pan (Verschieben) Variablen
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.is_panning = False
        
        # Maus-Events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Pan mit mittlerer Maustaste oder Shift+Linksklick
        self.canvas.bind("<Button-2>", self.start_pan)  # Mittlere Maustaste
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-2>", self.stop_pan)
        
        self.canvas.bind("<Shift-Button-1>", self.start_pan)  # Shift+Linksklick
        self.canvas.bind("<Shift-B1-Motion>", self.do_pan)
        self.canvas.bind("<Shift-ButtonRelease-1>", self.stop_pan)
        
        # Zoom mit Mausrad (Strg+Scroll)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)
    
    def start_pan(self, event):
        """Startet Pan-Modus"""
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")  # Verschiebe-Cursor
    
    def do_pan(self, event):
        """Verschiebt das Canvas"""
        if not self.is_panning:
            return
        
        # Delta berechnen
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        
        # Canvas scrollen
        self.canvas.xview_scroll(int(-dx / 10), "units")
        self.canvas.yview_scroll(int(-dy / 10), "units")
        
        # Position aktualisieren
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def stop_pan(self, event):
        """Beendet Pan-Modus"""
        self.is_panning = False
        self.canvas.config(cursor="")  # Zurück zum Standard-Cursor
    
    def on_zoom(self, event):
        """Zoom mit Strg+Mausrad"""
        # Zoom-Faktor berechnen
        if event.delta > 0:
            scale = 1.1  # Zoom in
        else:
            scale = 0.9  # Zoom out
        
        new_zoom = self.zoom_level * scale
        
        # Limitierung prüfen
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return
        
        self.zoom_level = new_zoom
        
        # Tile-Größe anpassen
        self.tile_size = int(self.tile_size * scale)
        
        # Grid neu zeichnen
        self.draw_grid()
        
        # Canvas scrollregion aktualisieren
        canvas_width = self.width * self.tile_size
        canvas_height = self.height * self.tile_size
        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
    
    def on_canvas_release(self, event):
        """Maus losgelassen"""
        self.is_drawing = False
    
    def populate_material_list(self):
        """Füllt die Material-Liste links - gruppiert nach Bundles"""
        # Clear existing
        for widget in self.material_list_inner.winfo_children():
            widget.destroy()
        
        # Get all bundles (sorted)
        bundles = self.bundle_manager.get_bundle_list()
        
        for bundle_id, bundle_data in bundles:
            self.create_bundle_section(bundle_id, bundle_data)
    
    def create_bundle_section(self, bundle_id, bundle_data):
        """Erstellt eine ein-/ausklappbare Bundle-Sektion"""
        is_active = self.bundle_manager.is_bundle_active(bundle_id)
        materials = bundle_data.get("materials", [])
        icon = bundle_data.get("icon", "📦")
        name = bundle_data.get("name", bundle_id)
        is_base = bundle_id == "base"
        
        # Bundle Header Frame
        header_frame = tk.Frame(self.material_list_inner, bg="#1a1a1a", cursor="hand2")
        header_frame.pack(fill=tk.X, pady=(8, 0), padx=5)
        
        # Toggle-Status speichern
        if not hasattr(self, 'bundle_collapsed'):
            self.bundle_collapsed = {}
        
        is_collapsed = self.bundle_collapsed.get(bundle_id, not is_active)  # Aktive Bundles ausgeklappt
        
        # Arrow + Icon + Name + Count
        arrow = "▼" if not is_collapsed else "▶"
        header_text = f"{arrow} {icon} {name} ({len(materials)})"
        
        header_btn = tk.Button(
            header_frame,
            text=header_text,
            bg="#2a5d8d" if is_active else "#3a3a3a",
            fg="white",
            font=("Arial", 10, "bold"),
            anchor=tk.W,
            padx=10,
            pady=5,
            relief=tk.RAISED if is_active else tk.FLAT,
            command=lambda: self.toggle_bundle_section(bundle_id)
        )
        header_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Activate/Deactivate Button (außer für Base)
        if not is_base:
            toggle_text = "✓" if is_active else "○"
            toggle_btn = tk.Button(
                header_frame,
                text=toggle_text,
                bg="#2a7d2a" if is_active else "#7d2a2a",
                fg="white",
                font=("Arial", 10, "bold"),
                width=3,
                command=lambda: self.toggle_bundle(bundle_id)
            )
            toggle_btn.pack(side=tk.RIGHT, padx=2)
        
        # Materials Grid (nur wenn aktiv und nicht collapsed)
        if is_active and not is_collapsed:
            materials_grid = tk.Frame(self.material_list_inner, bg="#2a2a2a")
            materials_grid.pack(fill=tk.BOTH, padx=3, pady=5)
            
            # Grid mit 3 kompakten Spalten
            col = 0
            row = 0
            for material_id in sorted(materials):
                # Prüfe ob Material existiert
                try:
                    texture = self.texture_renderer.get_texture(material_id, 48, 0)
                    if not texture:
                        continue
                except:
                    continue
                
                # Material Button Frame - 2x größer
                mat_frame = tk.Frame(materials_grid, bg="#3a3a3a", 
                                    relief=tk.RAISED if material_id == self.selected_terrain else tk.FLAT,
                                    bd=2, cursor="hand2", width=130, height=140)
                mat_frame.grid(row=row, column=col, padx=2, pady=2)
                mat_frame.grid_propagate(False)  # Feste Größe
                
                # Click handler
                def select_material(m=material_id, f=mat_frame):
                    self.select_terrain(m)
                    # Highlight
                    for child in materials_grid.winfo_children():
                        child.configure(relief=tk.FLAT, bd=1)
                    f.configure(relief=tk.RAISED, bd=3)
                
                mat_frame.bind("<Button-1>", lambda e, m=material_id, f=mat_frame: select_material(m, f))
                
                # Preview Image - 2x größer
                texture_small = texture.resize((100, 100), Image.LANCZOS)
                photo = ImageTk.PhotoImage(texture_small)
                img_label = tk.Label(mat_frame, image=photo, bg="#3a3a3a")
                img_label.image = photo  # Keep reference
                img_label.pack(pady=(2, 0))
                img_label.bind("<Button-1>", lambda e, m=material_id, f=mat_frame: select_material(m, f))
                
                # Name Label - größer
                name_text = material_id.replace('_', ' ').title()
                
                # Intelligentes Kürzen
                if len(name_text) > 14:
                    words = name_text.split()
                    if len(words) >= 2:
                        # Erste 2 Wörter, je max 8 Zeichen
                        line1 = words[0][:8]
                        line2 = words[1][:8]
                        name_text = f"{line1}\n{line2}"
                    else:
                        # Ein langes Wort in 2 Zeilen
                        mid = len(name_text) // 2
                        name_text = f"{name_text[:mid]}\n{name_text[mid:]}"
                
                name_label = tk.Label(mat_frame, text=name_text,
                                     bg="#3a3a3a", fg="white",
                                     font=("Arial", 9), justify=tk.CENTER,
                                     wraplength=120)
                name_label.pack(pady=(2, 1))
                name_label.bind("<Button-1>", lambda e, m=material_id, f=mat_frame: select_material(m, f))
                
                # Grid positioning
                col += 1
                if col >= 2:  # 2 Spalten (wegen größeren Karten)
                    col = 0
                    row += 1
    
    def toggle_bundle_section(self, bundle_id):
        """Klappt Bundle-Sektion ein/aus"""
        if not hasattr(self, 'bundle_collapsed'):
            self.bundle_collapsed = {}
        
        self.bundle_collapsed[bundle_id] = not self.bundle_collapsed.get(bundle_id, False)
        self.populate_material_list()  # Neu zeichnen
    
    def get_active_materials(self):
        """Gibt Liste der aktiven Materialien zurück (gefiltert nach Bundles)"""
        # Direkt vom Bundle-Manager holen
        active_materials = self.bundle_manager.get_active_materials()
        
        # Debug: Zeige was geladen ist
        if len(active_materials) == 0:
            print("⚠️ Keine aktiven Materialien! Lade Base-Materials als Fallback...")
            # Fallback zu Base-Materials
            active_materials = set(["grass", "water", "forest", "mountain", "sand", 
                                   "stone", "snow", "village", "empty", "dirt", "road"])
        
        return active_materials
    
    def filter_material_bar(self):
        """Filtert Material-Bar nach aktiven Bundles (für Kompatibilität)"""
        # Update material list instead
        if hasattr(self, 'material_list_inner'):
            self.populate_material_list()
    
    def open_material_manager(self):
        """Öffnet den Material-Manager"""
        MaterialManagerWindow(self, self.texture_renderer)
    
    def show_preview(self):
        """Zeigt eine Vorschau der Karte"""
        messagebox.showinfo("Vorschau", "Vorschau-Funktion noch nicht implementiert")
    
    def select_terrain(self, terrain):
        """Terrain auswählen"""
        self.selected_terrain = terrain
        # Update ohne komplettes Neuladen
        print(f"✓ Material '{terrain}' ausgewählt")
    
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
        # Nicht zeichnen wenn gerade Pan-Modus aktiv ist
        if self.is_panning:
            return
        
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if 0 <= x < self.width and 0 <= y < self.height:
            self.set_tile(x, y, self.selected_terrain)
            self.update_tile(x, y)
    
    def on_canvas_drag(self, event):
        """Drag"""
        # Nicht zeichnen wenn gerade Pan-Modus aktiv ist
        if self.is_panning:
            return
        
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
    
    def export_as_svg(self):
        """Map als SVG exportieren mit Qualitäts-Dialog"""
        # WARNUNG bei großen Maps
        total_tiles = self.width * self.height
        non_empty_tiles = sum(1 for row in self.map for tile in row if tile and tile != "empty")
        
        if total_tiles > 2000 or non_empty_tiles > 1500:
            warning_msg = (
                f"⚠️ GROSSE MAP ERKANNT!\n\n"
                f"Map-Größe: {self.width}×{self.height} = {total_tiles} Tiles\n"
                f"Befüllte Tiles: {non_empty_tiles}\n\n"
                f"SVG-Export kann sehr lange dauern und große Dateien erzeugen!\n\n"
                f"Empfehlungen:\n"
                f"• Nutze 'Low' Qualität für schnelleren Export\n"
                f"• Datei kann 50-500 MB groß werden\n"
                f"• Projektor-Rendering kann langsam sein\n\n"
                f"Trotzdem fortfahren?"
            )
            
            if not messagebox.askyesno("Warnung - Große Map", warning_msg):
                return
        
        # Dialog für Qualität
        quality_dialog = tk.Toplevel(self)
        quality_dialog.title("SVG Export")
        quality_dialog.geometry("450x380")
        quality_dialog.configure(bg="#1a1a1a")
        quality_dialog.transient(self)
        quality_dialog.grab_set()
        
        tk.Label(quality_dialog, text="📤 Map als SVG exportieren",
                font=("Arial", 14, "bold"),
                bg="#1a1a1a", fg="#d4af37").pack(pady=20)
        
        # Info über Map-Größe
        tk.Label(quality_dialog, text=f"Map: {self.width}×{self.height} ({non_empty_tiles} Tiles)",
                bg="#1a1a1a", fg="#888",
                font=("Arial", 9)).pack(pady=5)
        
        tk.Label(quality_dialog, text="Wähle die Export-Qualität:",
                bg="#1a1a1a", fg="white",
                font=("Arial", 10)).pack(pady=10)
        
        quality_var = tk.StringVar(value="low" if non_empty_tiles > 1000 else "high")
        
        qualities = [
            ("Low (256px) - Klein, schnell ⚡", "low"),
            ("High (512px) - Empfohlen ⭐", "high"),
            ("Ultra (1024px) - Maximale Qualität 🐌", "ultra")
        ]
        
        for text, value in qualities:
            tk.Radiobutton(quality_dialog, text=text,
                          variable=quality_var, value=value,
                          bg="#1a1a1a", fg="white",
                          selectcolor="#2a2a2a",
                          font=("Arial", 9)).pack(anchor=tk.W, padx=40, pady=5)
        
        # Geschätzte Dateigröße
        estimated_mb = (non_empty_tiles * 2) / 1000  # Grobe Schätzung
        tk.Label(quality_dialog, 
                text=f"Geschätzte Dateigröße: ~{estimated_mb:.0f}-{estimated_mb*2:.0f} MB",
                bg="#1a1a1a", fg="#ff8800",
                font=("Arial", 8, "italic")).pack(pady=10)
        
        def do_export():
            quality = quality_var.get()
            quality_dialog.destroy()
            
            # Datei-Dialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".svg",
                filetypes=[("SVG Dateien", "*.svg"), ("Alle Dateien", "*.*")],
                initialdir="."
            )
            
            if filename:
                try:
                    from svg_map_exporter import SVGMapExporter
                    
                    # 1. Map-Daten von 2D-Array in {(x,y): material} Dictionary konvertieren
                    map_dict = {}
                    for y in range(self.height):
                        for x in range(self.width):
                            material = self.map[y][x]
                            if material and material != "empty":
                                map_dict[(x, y)] = material
                    
                    # 2. Materials Dictionary vorbereiten
                    # Alle Materialien aus dem Renderer sammeln
                    materials = {}
                    
                    # Standard-Materialien
                    if hasattr(self.texture_renderer, 'material_definitions'):
                        materials.update(self.texture_renderer.material_definitions)
                    
                    # Custom-Materials hinzufügen
                    if hasattr(self.texture_renderer, 'custom_textures'):
                        for mat_name, mat_info in self.texture_renderer.custom_textures.items():
                            # mat_info ist ein Dictionary mit 'texture_path', 'name', etc.
                            if isinstance(mat_info, dict) and 'texture_path' in mat_info:
                                materials[mat_name] = {
                                    'type': 'custom',
                                    'path': mat_info['texture_path']  # Extrahiere den echten Pfad!
                                }
                            elif isinstance(mat_info, str):
                                # Fallback: mat_info ist direkt der Pfad (alte Struktur)
                                materials[mat_name] = {
                                    'type': 'custom',
                                    'path': mat_info
                                }
                    
                    # 3. SVG Exporter mit korrekter tile_size erstellen
                    tile_sizes = {
                        "low": 256,
                        "high": 512,
                        "ultra": 1024
                    }
                    base_tile_size = tile_sizes.get(quality, 512)
                    
                    exporter = SVGMapExporter(tile_size=base_tile_size)
                    
                    # 4. Exportiere mit korrekter API + LIMITS
                    max_dimension = 2048  # Max 2048px pro Seite
                    
                    success = exporter.export_map_to_svg(
                        map_data=map_dict,
                        materials=materials,
                        renderer=self.texture_renderer,
                        output_path=filename,
                        embed_images=True,
                        render_resolution=quality,
                        max_dimension=max_dimension,
                        use_symbols=False  # Für PIL-Kompatibilität!
                    )
                    
                    if success:
                        # Dateigröße prüfen
                        import os
                        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
                        
                        msg = (f"SVG exportiert!\n\n"
                               f"Datei: {filename}\n"
                               f"Qualität: {quality.upper()}\n"
                               f"Dateigröße: {file_size_mb:.1f} MB\n"
                               f"Base Tile-Größe: {base_tile_size}px")
                        
                        if file_size_mb > 100:
                            msg += f"\n\n⚠️ Große Datei! Projektor kann langsam sein."
                        
                        messagebox.showinfo("Erfolg", msg)
                    else:
                        messagebox.showerror("Fehler", "SVG Export fehlgeschlagen!")
                
                except Exception as e:
                    import traceback
                    messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}\n\n{traceback.format_exc()}")
        
        button_frame = tk.Frame(quality_dialog, bg="#1a1a1a")
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="✅ Exportieren",
                 bg="#2a7d2a", fg="white",
                 font=("Arial", 10, "bold"),
                 padx=20, pady=5,
                 command=do_export).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="❌ Abbrechen",
                 bg="#7d2a2a", fg="white",
                 font=("Arial", 10, "bold"),
                 padx=20, pady=5,
                 command=quality_dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    def refresh_bundle_buttons(self):
        """Aktualisiert Bundle-Buttons"""
        # Alte Buttons löschen
        for widget in self.bundle_button_frame.winfo_children():
            widget.destroy()
        
        self.bundle_buttons = {}
        
        # Bundles holen und sortieren
        bundles = self.bundle_manager.get_bundle_list()
        
        for bundle_id, bundle_data in bundles:
            icon = bundle_data.get("icon", "📦")
            name = bundle_data.get("name", bundle_id)
            is_active = self.bundle_manager.is_bundle_active(bundle_id)
            is_always = bundle_data.get("always_loaded", False)
            
            # Button-Farbe basierend auf Status
            if is_always:
                bg_color = "#2a5d2a"  # Grün (immer geladen)
                state = "disabled"
            elif is_active:
                bg_color = "#2a5d8d"  # Blau (aktiv)
                state = "normal"
            else:
                bg_color = "#3a3a3a"  # Grau (inaktiv)
                state = "normal"
            
            btn = tk.Button(
                self.bundle_button_frame,
                text=f"{icon} {name}",
                bg=bg_color,
                fg="white",
                font=("Arial", 9),
                padx=10,
                pady=3,
                relief=tk.RAISED if is_active else tk.FLAT,
                state=state,
                command=lambda bid=bundle_id: self.toggle_bundle(bid)
            )
            btn.pack(side=tk.LEFT, padx=3)
            
            self.bundle_buttons[bundle_id] = btn
    
    def toggle_bundle(self, bundle_id):
        """Bundle aktivieren/deaktivieren"""
        # Toggle im Manager
        is_now_active = self.bundle_manager.toggle_bundle(bundle_id)
        
        # Debug
        print(f"🔄 Toggle {bundle_id}: aktiv={is_now_active}")
        print(f"   Aktive Bundles: {self.bundle_manager.active_bundles}")
        
        # UI aktualisieren
        self.refresh_bundle_buttons()
        self.populate_material_list()  # WICHTIG: Material-Liste neu laden!
    
    def filter_material_bar(self):
        """Filtert Material-Bar nach aktiven Bundles"""
        if not hasattr(self, 'material_bar'):
            return
        
        # Hole aktive Materialien aus Bundles
        active_materials = self.bundle_manager.get_active_materials()
        
        # Füge alle Custom-Materials hinzu (falls vorhanden)
        if hasattr(self.texture_renderer, 'custom_textures'):
            for mat_name in self.texture_renderer.custom_textures.keys():
                # Nur hinzufügen wenn Material in aktivem Bundle ist
                bundle_id = self.bundle_manager.get_material_bundle(mat_name)
                if bundle_id and self.bundle_manager.is_bundle_active(bundle_id):
                    active_materials.add(mat_name)
        
        # Material-Bar aktualisieren
        self.material_bar.filter_materials(active_materials)
    
    def open_bundle_manager(self):
        """Öffnet Bundle-Manager-Dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("📦 Bundle-Manager")
        dialog.geometry("600x500")
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self)
        
        tk.Label(dialog, text="📦 Material Bundle Manager",
                font=("Arial", 14, "bold"),
                bg="#1a1a1a", fg="#d4af37").pack(pady=20)
        
        # Info
        total_bundles = len(self.bundle_manager.bundles)
        active_count = len(self.bundle_manager.active_bundles)
        tk.Label(dialog, text=f"{total_bundles} Bundles | {active_count} aktiv",
                bg="#1a1a1a", fg="#888").pack(pady=5)
        
        # Liste mit Scrollbar
        list_frame = tk.Frame(dialog, bg="#1a1a1a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        bundle_list = tk.Listbox(list_frame, 
                                bg="#2a2a2a", fg="white",
                                font=("Arial", 10),
                                selectmode=tk.SINGLE,
                                yscrollcommand=scrollbar.set)
        bundle_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=bundle_list.yview)
        
        # Bundles anzeigen
        bundles = self.bundle_manager.get_bundle_list()
        for bundle_id, bundle_data in bundles:
            icon = bundle_data.get("icon", "📦")
            name = bundle_data.get("name", bundle_id)
            mat_count = len(bundle_data.get("materials", []))
            is_active = self.bundle_manager.is_bundle_active(bundle_id)
            status = "✅" if is_active else "⬜"
            
            display = f"{status} {icon} {name} ({mat_count} Materials)"
            bundle_list.insert(tk.END, display)
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="#1a1a1a")
        button_frame.pack(pady=10)
        
        def toggle_selected():
            sel = bundle_list.curselection()
            if sel:
                idx = sel[0]
                bundle_id = list(self.bundle_manager.bundles.keys())[idx]
                self.toggle_bundle(bundle_id)
                dialog.destroy()
                self.open_bundle_manager()  # Refresh
        
        def delete_selected():
            sel = bundle_list.curselection()
            if sel:
                idx = sel[0]
                bundle_id = list(self.bundle_manager.bundles.keys())[idx]
                bundle_info = self.bundle_manager.get_bundle_info(bundle_id)
                name = bundle_info.get("name", bundle_id)
                
                if messagebox.askyesno("Löschen?", f"Bundle '{name}' wirklich löschen?"):
                    self.bundle_manager.delete_bundle(bundle_id)
                    self.refresh_bundle_buttons()
                    dialog.destroy()
                    self.open_bundle_manager()  # Refresh
        
        tk.Button(button_frame, text="🔄 Aktivieren/Deaktivieren",
                 bg="#2a5d8d", fg="white", font=("Arial", 9),
                 padx=15, pady=5, command=toggle_selected).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🗑️ Löschen",
                 bg="#7d2a2a", fg="white", font=("Arial", 9),
                 padx=15, pady=5, command=delete_selected).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="✅ Schließen",
                 bg="#2a7d2a", fg="white", font=("Arial", 9),
                 padx=15, pady=5, command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def destroy(self):
        """Aufräumen"""
        self.is_animating = False
        if self.animation_id:
            self.after_cancel(self.animation_id)
        super().destroy()
    
    def open_map_draw(self):
        """Öffnet das MapDraw-Tool (Hand-Drawn Map Editor)"""
        try:
            # Starte hand_drawn_map_editor.py
            editor_path = os.path.join(os.path.dirname(__file__), "hand_drawn_map_editor.py")
            
            if not os.path.exists(editor_path):
                messagebox.showerror("Fehler", 
                    "hand_drawn_map_editor.py nicht gefunden!")
                return
            
            # Starte als separater Prozess
            subprocess.Popen([sys.executable, editor_path])
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Konnte MapDraw nicht starten:\n{e}")


def ask_canvas_size(parent=None):
    """Dialog zur Auswahl der Canvas-Größe vor dem Start"""
    dialog = tk.Toplevel(parent) if parent else tk.Tk()
    dialog.title("🗺️ Neue Karte erstellen")
    dialog.geometry("450x500")  # Größer: 400x350 → 450x500
    dialog.configure(bg="#1a1a1a")
    dialog.resizable(False, False)
    
    if parent:
        dialog.transient(parent)
        dialog.grab_set()
    
    result = {"width": 50, "height": 50, "confirmed": False}
    
    tk.Label(dialog, text="🗺️ Karten-Größe wählen",
            font=("Arial", 16, "bold"),
            bg="#1a1a1a", fg="#d4af37").pack(pady=20)
    
    # Vorlagen
    tk.Label(dialog, text="Vorlagen:",
            bg="#1a1a1a", fg="white",
            font=("Arial", 10, "bold")).pack(pady=(10, 5))
    
    presets_frame = tk.Frame(dialog, bg="#1a1a1a")
    presets_frame.pack(pady=5)
    
    presets = [
        ("Klein (20×20)", 20, 20),
        ("Mittel (30×30)", 30, 30),
        ("Groß (50×50)", 50, 50),
        ("Riesig (100×100)", 100, 100)
    ]
    
    width_var = tk.IntVar(value=50)
    height_var = tk.IntVar(value=50)
    
    # Tile-Count Anzeige (MUSS VOR set_preset definiert werden!)
    tile_count_label = tk.Label(dialog, text="",
                               bg="#1a1a1a", fg="#888",
                               font=("Arial", 9, "italic"))
    
    def update_tile_count():
        try:
            w = width_var.get()
            h = height_var.get()
            total = w * h
            tile_count_label.config(text=f"Gesamt: {w}×{h} = {total:,} Tiles".replace(",", "."))
            
            # Warnung bei großen Maps
            if total > 5000:
                tile_count_label.config(fg="#ff8800")
            else:
                tile_count_label.config(fg="#888")
        except:
            pass
    
    def set_preset(w, h):
        width_var.set(w)
        height_var.set(h)
        update_tile_count()
    
    for i, (name, w, h) in enumerate(presets):
        row = i // 2
        col = i % 2
        tk.Button(presets_frame, text=name,
                 bg="#2a5d8d", fg="white",
                 font=("Arial", 9),
                 width=15, pady=5,
                 command=lambda w=w, h=h: set_preset(w, h)).grid(row=row, column=col, padx=5, pady=3)
    
    # Benutzerdefiniert
    tk.Label(dialog, text="Benutzerdefiniert:",
            bg="#1a1a1a", fg="white",
            font=("Arial", 10, "bold")).pack(pady=(15, 5))
    
    custom_frame = tk.Frame(dialog, bg="#1a1a1a")
    custom_frame.pack(pady=5)
    
    tk.Label(custom_frame, text="Breite:",
            bg="#1a1a1a", fg="white",
            font=("Arial", 9)).grid(row=0, column=0, padx=5)
    
    width_spinbox = tk.Spinbox(custom_frame, from_=5, to=200,
                              textvariable=width_var,
                              width=8, font=("Arial", 10),
                              command=update_tile_count)
    width_spinbox.grid(row=0, column=1, padx=5)
    width_spinbox.bind("<KeyRelease>", lambda e: update_tile_count())
    
    tk.Label(custom_frame, text="Höhe:",
            bg="#1a1a1a", fg="white",
            font=("Arial", 9)).grid(row=1, column=0, padx=5, pady=5)
    
    height_spinbox = tk.Spinbox(custom_frame, from_=5, to=200,
                               textvariable=height_var,
                               width=8, font=("Arial", 10),
                               command=update_tile_count)
    height_spinbox.grid(row=1, column=1, padx=5, pady=5)
    height_spinbox.bind("<KeyRelease>", lambda e: update_tile_count())
    
    # Label wird oberhalb bereits erstellt und angezeigt
    tile_count_label.pack(pady=10)
    
    # update_tile_count bereits oben definiert
    update_tile_count()  # Initial aufrufen
    
    # Buttons
    button_frame = tk.Frame(dialog, bg="#1a1a1a")
    button_frame.pack(pady=20)
    
    def confirm():
        result["width"] = width_var.get()
        result["height"] = height_var.get()
        result["confirmed"] = True
        if parent:
            dialog.grab_release()  # WICHTIG: Grab freigeben!
        dialog.destroy()
    
    def cancel():
        result["confirmed"] = False
        if parent:
            dialog.grab_release()  # WICHTIG: Grab freigeben!
        dialog.destroy()
    
    tk.Button(button_frame, text="✅ Erstellen",
             bg="#2a7d2a", fg="white",
             font=("Arial", 10, "bold"),
             padx=20, pady=5,
             command=confirm).pack(side=tk.LEFT, padx=10)
    
    tk.Button(button_frame, text="❌ Abbrechen",
             bg="#7d2a2a", fg="white",
             font=("Arial", 10, "bold"),
             padx=20, pady=5,
             command=cancel).pack(side=tk.LEFT, padx=10)
    
    # Auch beim X-Button Grab freigeben
    def on_closing():
        result["confirmed"] = False
        if parent:
            dialog.grab_release()
        dialog.destroy()
    
    dialog.protocol("WM_DELETE_WINDOW", on_closing)
    
    dialog.wait_window()
    return result
