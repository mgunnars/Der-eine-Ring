"""
Map Editor für "Der Eine Ring"
Vollständiger Karten-Editor mit Material-Manager, River-Direktions-System und Layer-System
Extrahiert aus main.py für modulare Nutzung
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk, ImageDraw
import subprocess
import sys
import os
from texture_manager import TextureManager
from map_system import MapSystem
from advanced_texture_renderer import AdvancedTextureRenderer
from material_manager import MaterialBar, MaterialManagerWindow
from material_bundle_manager import MaterialBundleManager
from layer_manager import LayerManager, LayerPanel
from advanced_drawing_tools import BezierCurveTool, PolygonTool, TextTool, TransformTool
from lighting_system import LightingEngine, LightSource, LIGHT_PRESETS
from map_editor_extensions import SelectTool, ContextPanel, SmoothPolygonDrawer, GeometryTools

class MapEditor(tk.Frame):
    def __init__(self, parent, width=50, height=50, map_data=None):
        super().__init__(parent, bg="#2a2a2a")
        
        # DEBUG: Zeige was übergeben wurde
        print(f"\n🔍 MapEditor.__init__ aufgerufen:")
        print(f"   width={width}, height={height}")
        print(f"   map_data={'vorhanden' if map_data else 'None'}")
        if map_data:
            print(f"   map_data.keys() = {list(map_data.keys())}")
            print(f"   tiles vorhanden: {'tiles' in map_data}")
        
        self.width = width
        self.height = height
        
        # Map System
        self.map_system = MapSystem()
        
        # Bundle Manager initialisieren
        self.bundle_manager = MaterialBundleManager()
        
        # SVG-Mode Support
        self.is_svg_mode = False
        self.svg_source_path = None
        
        # Wenn Map-Daten übergeben wurden, diese laden
        if map_data:
            # Prüfe ob SVG-Mode
            if map_data.get("is_svg_mode"):
                self.is_svg_mode = True
                self.svg_source_path = map_data.get("svg_path")
                print(f"📐 SVG-Mode aktiviert: {self.svg_source_path}")
            
            self.width = map_data.get("width", width)
            self.height = map_data.get("height", height)
            self.map = map_data.get("tiles", self.create_empty_map())
            self.river_directions = map_data.get("river_directions", {})
            print(f"✅ Map-Daten geladen: {self.width}×{self.height}, {len(self.map)} Zeilen")
        else:
            self.map = self.create_empty_map()
            self.river_directions = {}
            print(f"🆕 Neue leere Map erstellt: {self.width}×{self.height}")
        
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
        
        # === PROFESSIONAL DRAWING TOOLS ===
        self.active_tool = tk.StringVar(value="brush")  # brush, fill, eyedropper, eraser, rectangle, circle, line, select, curve, polygon, text, light
        self.shape_tool = tk.StringVar(value="rectangle")  # rectangle, circle, line
        
        # === OBJECT SELECTION ===
        self.selected_light = None  # Index der ausgewählten Lichtquelle
        self.selected_polygon = None  # Index des ausgewählten Polygons
        self.fill_connected_only = tk.BooleanVar(value=True)  # Nur verbundene Tiles füllen
        self.symmetry_mode = tk.BooleanVar(value=False)  # Symmetrisches Zeichnen
        self.symmetry_axis = tk.StringVar(value="vertical")  # vertical, horizontal, both
        
        # Shape drawing state
        self.shape_start = None
        self.shape_preview = []  # Liste der Preview-Tiles
        
        # Selection state
        self.selection_area = None  # (x1, y1, x2, y2)
        self.selection_content = None  # Kopierte Tiles
        
        # Undo/Redo
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 50
        
        # Layer-System initialisieren
        self.layer_manager = LayerManager()
        
        # Erweiterte Zeichentools
        self.bezier_tool = BezierCurveTool()
        self.polygon_tool = PolygonTool()
        self.text_tool = TextTool()
        self.transform_tool = TransformTool()
        
        # NEUE EDITOR-ERWEITERUNGEN
        self.select_tool = SelectTool(self)
        self.smooth_polygon_drawer = SmoothPolygonDrawer()
        self.geometry_tools = GeometryTools()
        self.context_panel = None  # Wird im UI setup erstellt
        
        # Lighting System
        self.lighting_engine = LightingEngine()
        self.show_lighting = tk.BooleanVar(value=False)
        self.selected_light_preset = "torch"
        self.selected_light_index = None  # Aktuell ausgewählte Lichtquelle
        self.lighting_update_id = None  # Timer für Animation
        self.lighting_time = 0.0  # Zeit für Flicker-Animation
        
        # Lade Lighting-Daten falls vorhanden
        if map_data and "lighting" in map_data:
            self.lighting_engine.from_dict(map_data["lighting"])
            print(f"   ✅ Always-loaded: lighting_objects")
            print(f"💡 {len(self.lighting_engine.lights)} Lichtquellen geladen")
            print(f"☀️ Lighting-Mode: {self.lighting_engine.lighting_mode}")
            print(f"🏠 Darkness-Polygone: {len(self.lighting_engine.darkness_polygons)}")
        
        # Darkness Polygon Drawing
        self.drawing_darkness_polygon = False
        self.current_darkness_polygon = []
        
        # Material → Light Mapping (welche Materials erzeugen Lichtquellen)
        self.light_emitting_materials = {
            "torch": {"preset": "torch", "icon": "🔥"},
            "candle": {"preset": "candle", "icon": "🕯️"},
            "lantern": {"preset": "candle", "icon": "🏮"},
            "fire": {"preset": "fire", "icon": "🔥"},
            "campfire": {"preset": "fire", "icon": "🔥"},
            "window": {"preset": "window", "icon": "🪟"},
            "magic_circle": {"preset": "magic", "icon": "✨"},
            "crystal": {"preset": "magic", "icon": "💎"}
        }
        
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
        
        # Im SVG-Mode: Größere Tiles erlauben für bessere Darstellung
        if self.is_svg_mode:
            self.tile_size = min(self.tile_size, 128)  # Bis zu 128px für SVG
            print(f"   SVG-Mode: Tile-Größe = {self.tile_size}px")
        else:
            self.tile_size = min(self.tile_size, 64)
        
        # Performance-Mode bei großen Maps (>1000 Tiles)
        self.total_tiles = self.width * self.height
        self.performance_mode = self.total_tiles > 1000
        
        if self.performance_mode and not self.is_svg_mode:  # Nicht im SVG-Mode!
            print(f"⚡ Performance-Mode aktiviert ({self.total_tiles} Tiles)")
            print(f"   - Kleinere Tile-Größe (max 32px)")
            print(f"   - Koordinaten standardmäßig aus")
            self.tile_size = min(self.tile_size, 32)  # Noch kleiner bei großen Maps
        
        self.setup_ui()
        
        # Synchronisiere UI mit geladenen Lighting-Daten (falls vorhanden)
        if map_data and "lighting" in map_data:
            self.lighting_mode_var.set(self.lighting_engine.lighting_mode)
            self.darkness_opacity_var.set(int(self.lighting_engine.darkness_opacity * 100))
            print(f"🎚️ UI mit Lighting-Daten synchronisiert")
        
        # Starte Lighting-Animation
        self.start_lighting_animation()

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
        
        # Edit Operations
        edit_frame = tk.LabelFrame(top_frame, text="✏️ Bearbeiten", bg="#1a1a1a", fg="white", font=("Arial", 9))
        edit_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)
        
        tk.Button(edit_frame, text="↶", bg="#3a3a3a", fg="white",
                 font=("Arial", 12, "bold"), width=3,
                 command=self.undo).pack(side=tk.LEFT, padx=2)
        tk.Button(edit_frame, text="↷", bg="#3a3a3a", fg="white",
                 font=("Arial", 12, "bold"), width=3,
                 command=self.redo).pack(side=tk.LEFT, padx=2)
        
        # === TOOL PALETTE - Professional VTT Style ===
        tool_frame = tk.LabelFrame(top_frame, text="🛠️ Werkzeuge", bg="#1a1a1a", fg="white", font=("Arial", 9, "bold"))
        tool_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)
        
        # Tool-Buttons (2 Reihen)
        tool_row1 = tk.Frame(tool_frame, bg="#1a1a1a")
        tool_row1.pack(padx=3, pady=2)
        
        tools_top = [
            ("🖌️", "brush", "Pinsel (B)"),
            ("🪣", "fill", "Füllen (F)"),
            ("💧", "eyedropper", "Pipette (I)"),
            ("🧹", "eraser", "Radierer (E)")
        ]
        
        for icon, tool, tooltip in tools_top:
            self._create_tool_button(tool_row1, icon, tool, tooltip)
        
        tool_row2 = tk.Frame(tool_frame, bg="#1a1a1a")
        tool_row2.pack(padx=3, pady=2)
        
        tools_bottom = [
            ("⬜", "rectangle", "Rechteck (R)"),
            ("⭕", "circle", "Kreis (C)"),
            ("📏", "line", "Linie (L)"),
            ("✂️", "select", "Auswahl (S)")
        ]
        
        for icon, tool, tooltip in tools_bottom:
            self._create_tool_button(tool_row2, icon, tool, tooltip)
        
        # Tool Row 3 - NEUE ERWEITERTE TOOLS
        tool_row3 = tk.Frame(tool_frame, bg="#1a1a1a")
        tool_row3.pack(padx=3, pady=2)
        
        tools_advanced = [
            ("🌊", "curve", "Kurve (V)"),
            ("⬟", "polygon", "Polygon (P)"),
            ("📝", "text", "Text (T)"),
            ("💡", "light", "Licht (G)")
        ]
        
        for icon, tool, tooltip in tools_advanced:
            self._create_tool_button(tool_row3, icon, tool, tooltip)
        
        # Brush Size (nur für Pinsel/Radierer)
        size_frame = tk.Frame(tool_frame, bg="#1a1a1a")
        size_frame.pack(padx=5, pady=3)
        
        self.brush_size_var = tk.IntVar(value=1)
        tk.Label(size_frame, text="Größe:", bg="#1a1a1a", fg="white",
                font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
        self.brush_scale = tk.Scale(size_frame, from_=1, to=15, orient=tk.HORIZONTAL,
                              variable=self.brush_size_var, 
                              command=lambda v: setattr(self, 'brush_size', int(v)),
                              bg="#2a2a2a", fg="white", troughcolor="#1a1a1a",
                              highlightthickness=0, length=100, width=10)
        self.brush_scale.pack(side=tk.LEFT, padx=2)
        
        # Symmetrie Toggle
        sym_frame = tk.Frame(tool_frame, bg="#1a1a1a")
        sym_frame.pack(padx=5, pady=2)
        
        tk.Checkbutton(sym_frame, text="↔️", variable=self.symmetry_mode,
                      bg="#1a1a1a", fg="white", selectcolor="#2a5d8d",
                      font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Label(sym_frame, text="Sym.", bg="#1a1a1a", fg="#888",
                font=("Arial", 7)).pack(side=tk.LEFT, padx=2)
        
        # MapDraw Button
        tk.Button(top_frame, text="🎨 MapDraw", bg="#8d5a2a", fg="white",
                 font=("Arial", 10, "bold"), padx=15, pady=5,
                 command=self.open_map_draw).pack(side=tk.RIGHT, padx=20)
        
        # =================== LEFT PANEL - MATERIALS ===================
        left_frame = tk.Frame(self, bg="#1a1a1a", width=320)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        # Header mit Suche
        header_frame = tk.Frame(left_frame, bg="#1a1a1a")
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header_frame, text="🎨 Materialien", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # Suchfeld
        search_frame = tk.Frame(left_frame, bg="#1a1a1a")
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.material_search_var = tk.StringVar()
        self.material_search_var.trace('w', lambda *args: self.filter_materials())
        
        search_entry = tk.Entry(search_frame, textvariable=self.material_search_var,
                               bg="#2a2a2a", fg="white", insertbackground="white",
                               font=("Arial", 10), relief=tk.FLAT)
        search_entry.pack(fill=tk.X, ipady=5)
        
        tk.Label(search_frame, text="🔍 Suchen...", bg="#1a1a1a", fg="#666",
                font=("Arial", 8)).pack(anchor=tk.W, pady=2)
        
        # Bundle Selector (kompakter)
        bundle_selector_frame = tk.Frame(left_frame, bg="#1a1a1a")
        bundle_selector_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        tk.Label(bundle_selector_frame, text="📦", bg="#1a1a1a", fg="#888",
                font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        
        tk.Button(bundle_selector_frame, text="⚙️ Bundles", bg="#3a3a3a", fg="white",
                 font=("Arial", 8), command=self.open_bundle_manager).pack(side=tk.RIGHT)
        
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
        
        # =================== CONTEXT PANEL (dynamisch) ===================
        # Wird rechts neben right_panel eingeblendet wenn Objekt ausgewählt
        self.context_panel = ContextPanel(self)
        # Panel-Callbacks werden in show_light_context/show_polygon_context gesetzt
        
        # =================== RIGHT PANEL - SETTINGS ===================
        right_outer = tk.Frame(self, bg="#1a1a1a", width=280)
        right_outer.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        right_outer.pack_propagate(False)
        
        # Tabs für bessere Organisation
        tab_header = tk.Frame(right_outer, bg="#1a1a1a", height=40)
        tab_header.pack(side=tk.TOP, fill=tk.X)
        tab_header.pack_propagate(False)
        
        self.active_tab = tk.StringVar(value="info")
        self.tab_buttons = {}
        
        tab_defs = [
            ("📊", "info", "Info"),
            ("🎨", "layers", "Layers"),
            ("💡", "lighting", "Licht"),
            ("⚙️", "settings", "Settings")
        ]
        
        for icon, tab_id, label in tab_defs:
            btn = tk.Button(tab_header, text=f"{icon}", bg="#2a2a2a", fg="white",
                          font=("Arial", 10), relief=tk.FLAT, width=4,
                          command=lambda t=tab_id: self.switch_tab(t))
            btn.pack(side=tk.LEFT, padx=2, pady=5, fill=tk.BOTH, expand=True)
            self.tab_buttons[tab_id] = btn
        
        # Scrollbarer Bereich für Tab-Inhalte
        right_canvas = tk.Canvas(right_outer, bg="#1a1a1a", highlightthickness=0)
        right_scrollbar = tk.Scrollbar(right_outer, orient=tk.VERTICAL, command=right_canvas.yview)
        right_frame = tk.Frame(right_canvas, bg="#1a1a1a")
        
        right_frame.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.create_window((0, 0), window=right_frame, anchor=tk.NW)
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Speichere Referenzen
        self.right_canvas = right_canvas
        self.right_frame_container = right_frame
        
        # Tab-Container erstellen (werden per switch_tab() ein/ausgeblendet)
        self.tab_frames = {}
        
        # INFO TAB
        info_tab = tk.Frame(right_frame, bg="#1a1a1a")
        self.tab_frames["info"] = info_tab
        
        tk.Label(info_tab, text="📊 Karten-Info", bg="#1a1a1a", fg="white",
                font=("Arial", 11, "bold")).pack(pady=(10, 5), anchor=tk.W, padx=10)
        
        info_grid = tk.Frame(info_tab, bg="#1a1a1a")
        info_grid.pack(fill=tk.X, padx=10, pady=5)
        
        info_items = [
            ("Größe:", f"{self.width}×{self.height}"),
            ("Tiles:", f"{self.total_tiles}"),
            ("Tile-Größe:", f"{self.tile_size}px"),
        ]
        
        for i, (label, value) in enumerate(info_items):
            tk.Label(info_grid, text=label, bg="#1a1a1a", fg="#888",
                    font=("Arial", 9)).grid(row=i, column=0, sticky=tk.W, pady=2)
            tk.Label(info_grid, text=value, bg="#1a1a1a", fg="white",
                    font=("Arial", 9, "bold")).grid(row=i, column=1, sticky=tk.W, padx=10, pady=2)
        
        if self.performance_mode:
            tk.Label(info_tab, text="⚡ Performance-Mode aktiv", 
                    bg="#1a1a1a", fg="#ff8800", font=("Arial", 9, "bold")).pack(pady=5, padx=10, anchor=tk.W)
        
        # LAYERS TAB
        layers_tab = tk.Frame(right_frame, bg="#1a1a1a")
        self.tab_frames["layers"] = layers_tab
        
        tk.Label(layers_tab, text="🎨 Layers", bg="#1a1a1a", fg="white",
                font=("Arial", 11, "bold")).pack(pady=(10, 5), anchor=tk.W, padx=10)
        
        self.layer_panel = LayerPanel(layers_tab, self.layer_manager, 
                                      on_layer_change=self.on_layer_change)
        self.layer_panel.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # LIGHTING TAB
        lighting_tab = tk.Frame(right_frame, bg="#1a1a1a")
        self.tab_frames["lighting"] = lighting_tab
        
        tk.Label(lighting_tab, text="💡 Beleuchtung", bg="#1a1a1a", fg="white",
                font=("Arial", 11, "bold")).pack(pady=(10, 5), anchor=tk.W, padx=10)
        
        # Licht-Typen
        tk.Label(lighting_tab, text="Licht-Typ:", bg="#1a1a1a", fg="#888",
                font=("Arial", 8)).pack(anchor=tk.W, padx=10, pady=(5, 2))
        
        light_presets = ["torch", "candle", "window", "magic", "fire", "moonlight"]
        icons = {"torch": "🔥", "candle": "🕯️", "window": "🪟", 
                "magic": "✨", "fire": "🔥", "moonlight": "🌙"}
        
        for preset in light_presets:
            tk.Radiobutton(lighting_tab, text=f"{icons.get(preset, '💡')} {preset.title()}",
                          variable=tk.StringVar(value=self.selected_light_preset),
                          value=preset, bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                          font=("Arial", 8),
                          command=lambda p=preset: setattr(self, 'selected_light_preset', p)
                          ).pack(anchor=tk.W, padx=15)
        
        # Separator
        tk.Frame(lighting_tab, bg="#333", height=1).pack(fill=tk.X, padx=10, pady=10)
        
        # Szenen-Modus
        tk.Label(lighting_tab, text="Szenen-Modus:", bg="#1a1a1a", fg="white",
                font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=10, pady=(5, 2))
        
        self.lighting_mode_var = tk.StringVar(value="night")
        
        tk.Radiobutton(lighting_tab, text="☀️ Tag (Innenräume dunkel)", variable=self.lighting_mode_var, 
                      value="day", bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 8), command=self.update_lighting_mode).pack(anchor=tk.W, padx=15)
        tk.Radiobutton(lighting_tab, text="🌙 Nacht (komplett dunkel)", variable=self.lighting_mode_var,
                      value="night", bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 8), command=self.update_lighting_mode).pack(anchor=tk.W, padx=15)
        
        # Dunkelheit-Slider
        tk.Label(lighting_tab, text="Dunkelheit:", bg="#1a1a1a", fg="#888",
                font=("Arial", 8)).pack(anchor=tk.W, padx=10, pady=(10, 2))
        
        darkness_frame = tk.Frame(lighting_tab, bg="#1a1a1a")
        darkness_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.darkness_opacity_var = tk.DoubleVar(value=0.85)
        tk.Scale(darkness_frame, from_=0.0, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                variable=self.darkness_opacity_var, command=self.update_darkness_opacity,
                bg="#2a2a2a", fg="white", highlightthickness=0, showvalue=False,
                troughcolor="#404040", activebackground="#3a3a3a").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.darkness_label = tk.Label(darkness_frame, text="85%", bg="#1a1a1a", fg="white",
                                      font=("Arial", 9, "bold"), width=5)
        self.darkness_label.pack(side=tk.LEFT, padx=5)
        
        # Separator
        tk.Frame(lighting_tab, bg="#333", height=1).pack(fill=tk.X, padx=10, pady=10)
        
        # Dunkel-Bereiche
        tk.Label(lighting_tab, text="🏚️ Dunkel-Bereiche:", bg="#1a1a1a", fg="white",
                font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=10, pady=(5, 2))
        
        self.drawing_darkness_polygon = False
        self.current_darkness_polygon = []
        
        polygon_controls = tk.Frame(lighting_tab, bg="#1a1a1a")
        polygon_controls.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(polygon_controls, text="✏️ Zeichnen", bg="#2a4a2a", fg="white",
                 font=("Arial", 8), width=10, command=self.start_darkness_polygon).grid(row=0, column=0, padx=2)
        tk.Button(polygon_controls, text="❌ Abbrechen", bg="#4a2a2a", fg="white",
                 font=("Arial", 8), width=10, command=self.cancel_darkness_polygon).grid(row=0, column=1, padx=2)
        tk.Button(polygon_controls, text="🗑️ Alle löschen", bg="#7d2a2a", fg="white",
                 font=("Arial", 8), width=22, command=self.clear_darkness_polygons).grid(row=1, column=0, columnspan=2, padx=2, pady=2)
        
        self.polygon_info_label = tk.Label(lighting_tab, text="0 Polygone | 0 Punkte", 
                                          bg="#1a1a1a", fg="#888888", font=("Arial", 8))
        self.polygon_info_label.pack(anchor=tk.W, padx=10, pady=2)
        
        # Separator
        tk.Frame(lighting_tab, bg="#333", height=1).pack(fill=tk.X, padx=10, pady=10)
        
        # Buttons
        btn_frame = tk.Frame(lighting_tab, bg="#1a1a1a")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="🗑️ Alle Lichter löschen", bg="#7d2a2a", fg="white",
                 font=("Arial", 9), command=self.clear_all_lights).pack(fill=tk.X)
        
        # SETTINGS TAB
        settings_tab = tk.Frame(right_frame, bg="#1a1a1a")
        self.tab_frames["settings"] = settings_tab
        
        tk.Label(settings_tab, text="⚙️ Einstellungen", bg="#1a1a1a", fg="white",
                font=("Arial", 11, "bold")).pack(pady=(10, 5), anchor=tk.W, padx=10)
        
        # Display Options
        tk.Label(settings_tab, text="👁️ Anzeige:", bg="#1a1a1a", fg="white",
                font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=10, pady=(5, 2))
        
        tk.Checkbutton(settings_tab, text="Koordinaten anzeigen", variable=self.show_coordinates,
                      bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 9), command=self.draw_grid).pack(anchor=tk.W, padx=15, pady=2)
        
        tk.Checkbutton(settings_tab, text="💡 Dynamic Lighting", variable=self.show_lighting,
                      bg="#1a1a1a", fg="white", selectcolor="#2a2a2a",
                      font=("Arial", 9), command=self.toggle_lighting).pack(anchor=tk.W, padx=15, pady=2)
        
        # Aktiviere Info-Tab als Standard
        self.switch_tab("info")
        
        # River Direction - ins Settings Tab verschieben (später)
        # Tools - in eigene Toolbar verschieben (später)
        
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
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)  # Rechtsklick
        
        # Pan mit mittlerer Maustaste oder Shift+Linksklick
        self.canvas.bind("<Button-2>", self.start_pan)  # Mittlere Maustaste
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-2>", self.stop_pan)
        
        self.canvas.bind("<Shift-Button-1>", self.start_pan)  # Shift+Linksklick
        self.canvas.bind("<Shift-B1-Motion>", self.do_pan)
        self.canvas.bind("<Shift-ButtonRelease-1>", self.stop_pan)
        
        # Zoom mit Mausrad (Strg+Scroll)
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)
        
        # === KEYBOARD SHORTCUTS ===
        self.bind_all("<KeyPress-b>", lambda e: self.select_tool("brush"))
        self.bind_all("<KeyPress-f>", lambda e: self.select_tool("fill"))
        self.bind_all("<KeyPress-i>", lambda e: self.select_tool("eyedropper"))
        self.bind_all("<KeyPress-e>", lambda e: self.select_tool("eraser"))
        self.bind_all("<KeyPress-r>", lambda e: self.select_tool("rectangle"))
        self.bind_all("<KeyPress-c>", lambda e: self.select_tool("circle"))
        self.bind_all("<KeyPress-l>", lambda e: self.select_tool("line"))
        self.bind_all("<KeyPress-s>", lambda e: self.select_tool("select"))
        
        # Neue erweiterte Tools
        self.bind_all("<KeyPress-v>", lambda e: self.select_tool("curve"))
        self.bind_all("<KeyPress-p>", lambda e: self.select_tool("polygon"))
        self.bind_all("<KeyPress-t>", lambda e: self.select_tool("text"))
        self.bind_all("<KeyPress-g>", lambda e: self.select_tool("light"))  # G für "Glow"
        
        # Delete-Taste für ausgewählte Lichtquelle
        self.bind_all("<Delete>", self.delete_selected_light)
        
        # Curve/Polygon Finalisierung
        self.bind_all("<Return>", lambda e: self.finalize_advanced_tool())
        self.bind_all("<Escape>", lambda e: self.cancel_advanced_tool())
        
        # Undo/Redo
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())
        
        # Brush Size
        self.bind_all("<KeyPress-bracketleft>", lambda e: self.adjust_brush_size(-1))  # [
        self.bind_all("<KeyPress-bracketright>", lambda e: self.adjust_brush_size(1))  # ]
    
    def adjust_brush_size(self, delta):
        """Ändert Pinselgröße mit Tastatur"""
        new_size = max(1, min(15, self.brush_size + delta))
        self.brush_size_var.set(new_size)
        self.brush_size = new_size
        print(f"🖌️ Pinselgröße: {new_size}")
    
    def _create_tool_button(self, parent, icon, tool, tooltip):
        """Erstellt einen Tool-Button mit Highlight"""
        is_active = self.active_tool.get() == tool
        
        btn = tk.Button(
            parent,
            text=icon,
            bg="#2a5d8d" if is_active else "#3a3a3a",
            fg="white",
            font=("Arial", 14),
            width=3,
            height=1,
            relief=tk.SUNKEN if is_active else tk.RAISED,
            command=lambda: self.select_tool(tool)
        )
        btn.pack(side=tk.LEFT, padx=2)
        
        # Tooltip (einfache Variante)
        btn.bind("<Enter>", lambda e: btn.config(cursor="hand2"))
        btn.bind("<Leave>", lambda e: btn.config(cursor=""))
        
        return btn
    
    def switch_tab(self, tab_id):
        """Wechselt zwischen Tabs im Right Panel"""
        self.active_tab.set(tab_id)
        
        # Verstecke alle Tabs
        for tid, frame in self.tab_frames.items():
            frame.pack_forget()
        
        # Zeige aktiven Tab
        if tab_id in self.tab_frames:
            self.tab_frames[tab_id].pack(fill=tk.BOTH, expand=True)
        
        # Update Button-Farben
        for tid, btn in self.tab_buttons.items():
            if tid == tab_id:
                btn.config(bg="#2a5d8d", relief=tk.SUNKEN)
            else:
                btn.config(bg="#2a2a2a", relief=tk.FLAT)
    
    def filter_materials(self):
        """Filtert Material-Liste nach Suchbegriff"""
        search_term = self.material_search_var.get().lower()
        
        # Refresh der Material-Liste mit Filter
        self.populate_material_list(filter_text=search_term)
    
    def select_tool(self, tool):
        """Wählt ein Zeichentool aus"""
        self.active_tool.set(tool)
        print(f"🛠️ Tool gewählt: {tool}")
        
        # UI-Update: Alle Tool-Buttons neu färben
        # (wird beim nächsten setup_ui automatisch gemacht)
        
        # Cursor ändern
        cursor_map = {
            "brush": "pencil",
            "fill": "spraycan",
            "eyedropper": "target",
            "eraser": "X_cursor",
            "rectangle": "crosshair",
            "circle": "crosshair",
            "line": "crosshair",
            "select": "cross"
        }
        self.canvas.config(cursor=cursor_map.get(tool, ""))
    
    def save_undo_state(self):
        """Speichert den aktuellen Map-Zustand für Undo"""
        # Deep copy der Map
        import copy
        state = copy.deepcopy(self.map)
        
        self.undo_stack.append(state)
        
        # Limit undo stack
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        
        # Redo stack leeren bei neuer Aktion
        self.redo_stack.clear()
    
    def finalize_advanced_tool(self):
        """Schließt Curve oder Polygon ab (Enter)"""
        tool = self.active_tool.get()
        
        if tool == "curve" and len(self.bezier_tool.points) >= 2:
            # Zeichne Kurve auf Map
            self.save_undo_state()
            curve_points = self.bezier_tool.get_curve_points()
            for x, y in curve_points:
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.map[y][x] = self.selected_terrain
            
            # Lösche Vorschau und reset Tool
            self.canvas.delete("curve_preview")
            self.bezier_tool.clear()
            self.draw_grid()
            print(f"✅ Kurve gezeichnet mit {len(curve_points)} Punkten")
            
        elif tool == "polygon" and len(self.polygon_tool.points) >= 3:
            # Schließe Polygon
            self.polygon_tool.close_polygon()
            
            # Fülle Polygon auf Map
            self.save_undo_state()
            tiles = self.polygon_tool.get_tiles_inside(self.width, self.height)
            for x, y in tiles:
                self.map[y][x] = self.selected_terrain
            
            # Lösche Vorschau und reset Tool
            self.canvas.delete("polygon_preview")
            self.polygon_tool.clear()
            self.draw_grid()
            print(f"✅ Polygon gezeichnet mit {len(tiles)} Tiles gefüllt")
    
    def cancel_advanced_tool(self):
        """Bricht Curve/Polygon ab (Escape)"""
        tool = self.active_tool.get()
        
        if tool == "curve":
            self.canvas.delete("curve_preview")
            self.bezier_tool.clear()
            print("❌ Kurve abgebrochen")
            
        elif tool == "polygon":
            self.canvas.delete("polygon_preview")
            self.polygon_tool.clear()
            print("❌ Polygon abgebrochen")
    
    def undo(self):
        """Macht die letzte Aktion rückgängig"""
        if not self.undo_stack:
            print("⚠️ Nichts zum Rückgängig machen")
            return
        
        # Aktuellen Zustand in Redo speichern
        import copy
        self.redo_stack.append(copy.deepcopy(self.map))
        
        # Letzten Zustand wiederherstellen
        self.map = self.undo_stack.pop()
        self.draw_grid()
        print("↶ Rückgängig")
    
    def redo(self):
        """Stellt rückgängig gemachte Aktion wieder her"""
        if not self.redo_stack:
            print("⚠️ Nichts zum Wiederherstellen")
            return
        
        # Aktuellen Zustand in Undo speichern
        import copy
        self.undo_stack.append(copy.deepcopy(self.map))
        
        # Redo-Zustand wiederherstellen
        self.map = self.redo_stack.pop()
        self.draw_grid()
        print("↷ Wiederhergestellt")
    
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
    
    def on_canvas_right_click(self, event):
        """Rechtsklick - Polygon abschließen"""
        if self.drawing_darkness_polygon:
            self.finish_darkness_polygon()
    
    def populate_material_list(self, filter_text=""):
        """Füllt die Material-Liste links - gruppiert nach Bundles"""
        # Clear existing
        for widget in self.material_list_inner.winfo_children():
            widget.destroy()
        
        # Get all bundles (sorted)
        bundles = self.bundle_manager.get_bundle_list()
        
        for bundle_id, bundle_data in bundles:
            self.create_bundle_section(bundle_id, bundle_data, filter_text)
    
    def create_bundle_section(self, bundle_id, bundle_data, filter_text=""):
        """Erstellt eine ein-/ausklappbare Bundle-Sektion"""
        is_active = self.bundle_manager.is_bundle_active(bundle_id)
        materials = bundle_data.get("materials", [])
        
        # Filter materials wenn Suchbegriff vorhanden
        if filter_text:
            materials = [m for m in materials if filter_text in m.lower()]
            if not materials:  # Überspringe Bundle wenn kein Material matched
                return
        
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
        
        # SVG als Hintergrundbild anzeigen (falls SVG-Mode)
        if self.is_svg_mode and self.svg_source_path and os.path.exists(self.svg_source_path):
            try:
                from cairosvg import svg2png
                import io
                
                # SVG zu PNG konvertieren (in passender Größe)
                target_width = self.width * self.tile_size
                target_height = self.height * self.tile_size
                
                png_data = svg2png(url=self.svg_source_path, 
                                  output_width=target_width,
                                  output_height=target_height)
                
                bg_img = Image.open(io.BytesIO(png_data))
                bg_photo = ImageTk.PhotoImage(bg_img)
                
                # Hintergrundbild zeichnen
                self.canvas.create_image(0, 0, image=bg_photo, anchor=tk.NW, tags="svg_background")
                self.canvas.image_refs.append(bg_photo)
                
                print(f"✅ SVG als Hintergrund geladen: {target_width}×{target_height}px")
            except ImportError:
                print("⚠️ cairosvg nicht installiert - SVG-Hintergrund nicht verfügbar")
                print("   Installiere mit: pip install cairosvg")
            except Exception as e:
                print(f"⚠️ SVG-Hintergrund-Fehler: {e}")
        
        for y in range(self.height):
            for x in range(self.width):
                x1 = x * self.tile_size
                y1 = y * self.tile_size
                
                terrain = self.map[y][x]
                
                # Im SVG-Mode: Optional sehr dünne Grid-Linien (transparent!)
                if self.is_svg_mode:
                    # NUR Outline, KEIN Fill (damit SVG sichtbar bleibt)
                    # Grid-Linien nur bei Bedarf (z.B. beim Zeichnen)
                    if self.show_coordinates.get():  # Zeige Grid nur wenn Koordinaten aktiv
                        self.canvas.create_rectangle(x1, y1, x1 + self.tile_size, y1 + self.tile_size,
                                                    outline="#dddddd", width=1, fill="",
                                                    tags=f"tile_{x}_{y}")
                else:
                    # Normal-Mode: Texturen rendern
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
        
        # === LIGHTING OVERLAY ===
        if self.show_lighting.get() and self.lighting_engine.enabled:
            # Rendere Lighting (mit time_offset für Flicker)
            lighting_overlay = self.lighting_engine.render_lighting(
                self.width, self.height, self.tile_size, time_offset=self.lighting_time
            )
            
            # Konvertiere zu PhotoImage
            lighting_photo = ImageTk.PhotoImage(lighting_overlay)
            self.canvas.create_image(0, 0, image=lighting_photo, anchor=tk.NW, tags="lighting_overlay")
            self.canvas.image_refs.append(lighting_photo)  # Referenz behalten
            
            # Zeichne Licht-Icons mit Interaktions-Bereich
            for i, light in enumerate(self.lighting_engine.lights):
                lx = light.x * self.tile_size + self.tile_size // 2
                ly = light.y * self.tile_size + self.tile_size // 2
                
                # Icon basierend auf Typ
                icons = {"torch": "🔥", "candle": "🕯️", "window": "🪟", 
                        "magic": "✨", "fire": "🔥", "moonlight": "🌙", "point": "💡"}
                icon = icons.get(light.light_type, "💡")
                
                # Highlight ausgewählte Lichtquelle mit mehreren Ringen
                if i == self.selected_light_index:
                    # Doppelter Ring für bessere Sichtbarkeit
                    self.canvas.create_oval(lx-18, ly-18, lx+18, ly+18, 
                                          outline="#ffff00", width=3, tags="light_source")
                    self.canvas.create_oval(lx-14, ly-14, lx+14, ly+14, 
                                          outline="#ffaa00", width=2, tags="light_source")
                else:
                    # Subtiler Umriss für nicht-ausgewählte Lichter
                    self.canvas.create_oval(lx-12, ly-12, lx+12, ly+12, 
                                          outline="#cccccc", width=1, tags="light_source")
                
                # Icon mit Shadow für bessere Lesbarkeit
                self.canvas.create_text(lx+1, ly+1, text=icon, font=("Arial", 14),
                                       fill="black", tags="light_source")
                self.canvas.create_text(lx, ly, text=icon, font=("Arial", 14),
                                       tags="light_source")
        
        # Zeichne Darkness-Polygone (gespeichert)
        for polygon in self.lighting_engine.darkness_polygons:
            if len(polygon) >= 3:
                coords = []
                for px, py in polygon:
                    coords.extend([px * self.tile_size, py * self.tile_size])
                self.canvas.create_polygon(coords, outline="#ff00ff", width=2, 
                                          fill="", dash=(5, 5), tags="darkness_polygon")
        
        # Zeichne aktuelles Polygon (wird gerade gezeichnet)
        if self.drawing_darkness_polygon and len(self.current_darkness_polygon) > 0:
            # Zeichne Punkte
            for px, py in self.current_darkness_polygon:
                cx = px * self.tile_size + self.tile_size // 2
                cy = py * self.tile_size + self.tile_size // 2
                self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, 
                                       fill="#ff00ff", outline="white", tags="darkness_polygon")
            
            # Zeichne Linien zwischen Punkten
            if len(self.current_darkness_polygon) >= 2:
                coords = []
                for px, py in self.current_darkness_polygon:
                    coords.extend([px * self.tile_size + self.tile_size // 2, 
                                  py * self.tile_size + self.tile_size // 2])
                self.canvas.create_line(coords, fill="#ff00ff", width=2, tags="darkness_polygon")
        
        # === SELECTION MARKERS ===
        # Zeichne Auswahl-Marker für ausgewählte Objekte
        self.select_tool.draw_selection_markers(self.canvas, self.tile_size)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_click(self, event):
        """Mausklick - Tool-basiert"""
        # Nicht zeichnen wenn gerade Pan-Modus aktiv ist
        if self.is_panning:
            return
        
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        
        # === DARKNESS POLYGON DRAWING ===
        if self.drawing_darkness_polygon:
            self.current_darkness_polygon.append((x, y))
            self.update_polygon_info()
            self.draw_grid()
            print(f"📍 Punkt hinzugefügt: ({x}, {y}) - {len(self.current_darkness_polygon)} Punkte")
            return
        
        tool = self.active_tool.get()
        
        # === CURVE TOOL (Bezier) ===
        if tool == "curve":
            self.bezier_tool.add_point(x, y)
            self.canvas.delete("curve_preview")
            self.bezier_tool.draw_preview(self.canvas, self.tile_size)
            print(f"🌊 Kurven-Punkt hinzugefügt: ({x}, {y}) - {len(self.bezier_tool.points)} Punkte")
            return
        
        # === POLYGON TOOL ===
        if tool == "polygon":
            self.polygon_tool.add_point(x, y)
            self.canvas.delete("polygon_preview")
            self.polygon_tool.draw_preview(self.canvas, self.tile_size)
            print(f"⬟ Polygon-Punkt hinzugefügt: ({x}, {y}) - {len(self.polygon_tool.points)} Punkte")
            return
        
        # === TEXT TOOL ===
        if tool == "text":
            text = tk.simpledialog.askstring("Text eingeben", "Text für Annotation:")
            if text:
                self.text_tool.add_text(x, y, text)
                self.canvas.delete("text_annotation")
                self.text_tool.draw_texts(self.canvas, self.tile_size)
                print(f"📝 Text hinzugefügt: '{text}' bei ({x}, {y})")
            return
        
        # === LIGHT TOOL ===
        if tool == "light":
            # Prüfe ob Licht bereits existiert
            existing = self.lighting_engine.get_light_at(x, y, tolerance=0)
            if existing is not None:
                # Lichtquelle auswählen
                self.select_light(existing)
                print(f"💡 Lichtquelle #{existing} ausgewählt")
            else:
                # Neues Licht hinzufügen
                preset = LIGHT_PRESETS.get(self.selected_light_preset, LIGHT_PRESETS["torch"])
                light = LightSource(x, y, **preset)
                self.lighting_engine.add_light(light)
                print(f"💡 {self.selected_light_preset.title()} platziert bei ({x}, {y})")
            
            # Redraw wenn Lighting aktiv
            if self.show_lighting.get():
                self.draw_grid()
            return
        
        # === EYEDROPPER (Pipette) ===
        if tool == "eyedropper":
            picked_terrain = self.map[y][x]
            if picked_terrain and picked_terrain != "empty":
                self.selected_terrain = picked_terrain
                print(f"💧 Material aufgenommen: {picked_terrain}")
                # Automatisch zu Pinsel wechseln
                self.select_tool("brush")
            return
        
        # === FILL (Füllen) ===
        if tool == "fill":
            self.flood_fill(x, y, self.selected_terrain)
            return
        
        # === SHAPE TOOLS (Rechteck, Kreis, Linie) ===
        if tool in ["rectangle", "circle", "line"]:
            if not self.shape_start:
                # Startpunkt setzen
                self.shape_start = (x, y)
                self.is_drawing = True
            else:
                # Endpunkt → Form zeichnen
                self.draw_shape(self.shape_start, (x, y), tool)
                self.shape_start = None
                self.is_drawing = False
                self.clear_shape_preview()
            return
        
        # === SELECT TOOL ===
        if tool == "select":
            # NEUE IMPLEMENTIERUNG: Objekt-Auswahl (Lichter, Polygone)
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Versuche Objekt auszuwählen
            if self.select_tool.handle_click(x, y):
                # Objekt wurde ausgewählt
                return
            
            # Fallback: Flächen-Auswahl für Tiles
            if not self.selection_area:
                self.selection_area = [x, y, x, y]
                self.is_drawing = True
            else:
                # Auswahl abgeschlossen
                self.finalize_selection()
            return
        
        # === ERASER (Radierer) ===
        if tool == "eraser":
            self.save_undo_state()
            self.paint_area(x, y, "empty")
            return
        
        # === BRUSH (Standard) ===
        if tool == "brush":
            self.save_undo_state()
            self.paint_area(x, y, self.selected_terrain)
            self.is_drawing = True
    
    def on_canvas_drag(self, event):
        """Drag - Tool-basiert"""
        # Nicht zeichnen wenn gerade Pan-Modus aktiv ist
        if self.is_panning:
            return
        
        x = int(self.canvas.canvasx(event.x) // self.tile_size)
        y = int(self.canvas.canvasy(event.y) // self.tile_size)
        
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        
        tool = self.active_tool.get()
        
        # === SHAPE PREVIEW ===
        if tool in ["rectangle", "circle", "line"] and self.shape_start:
            self.update_shape_preview(self.shape_start, (x, y), tool)
            return
        
        # === SELECT DRAGGING ===
        if tool == "select" and self.selection_area:
            self.selection_area[2] = x
            self.selection_area[3] = y
            self.draw_selection_preview()
            return
        
        # === BRUSH/ERASER DRAGGING ===
        if tool == "brush" and self.is_drawing:
            self.paint_area(x, y, self.selected_terrain)
        elif tool == "eraser" and self.is_drawing:
            self.paint_area(x, y, "empty")
    
    def paint_area(self, cx, cy, terrain):
        """Malt einen Bereich mit Pinsel-Größe (mit Symmetrie + Auto-Lights)"""
        brush_radius = self.brush_size // 2
        
        positions = []
        
        # Normale Position
        for dy in range(-brush_radius, brush_radius + 1):
            for dx in range(-brush_radius, brush_radius + 1):
                # Kreisförmiger Pinsel
                if dx*dx + dy*dy <= brush_radius*brush_radius + brush_radius:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        positions.append((nx, ny))
        
        # Symmetrie
        if self.symmetry_mode.get():
            sym_positions = []
            axis = self.symmetry_axis.get()
            
            for x, y in positions:
                if axis in ["vertical", "both"]:
                    # Spiegeln an vertikaler Achse (Mitte)
                    mirror_x = self.width - 1 - x
                    if 0 <= mirror_x < self.width:
                        sym_positions.append((mirror_x, y))
                
                if axis in ["horizontal", "both"]:
                    # Spiegeln an horizontaler Achse
                    mirror_y = self.height - 1 - y
                    if 0 <= mirror_y < self.height:
                        sym_positions.append((x, mirror_y))
                
                if axis == "both":
                    # Diagonal gespiegelt
                    mirror_x = self.width - 1 - x
                    mirror_y = self.height - 1 - y
                    if 0 <= mirror_x < self.width and 0 <= mirror_y < self.height:
                        sym_positions.append((mirror_x, mirror_y))
            
            positions.extend(sym_positions)
        
        # Tiles setzen (mit Auto-Light-Logik)
        for x, y in positions:
            if self.map[y][x] != terrain:
                old_material = self.map[y][x]
                self.set_tile(x, y, terrain)
                self.update_tile(x, y)
                
                # Auto-Light: Wenn neues Material Licht emittiert
                if terrain in self.light_emitting_materials:
                    # Prüfe ob bereits Licht an Position
                    light_idx = self.lighting_engine.get_light_at(x, y, tolerance=0)
                    if light_idx is None:
                        preset_name = self.light_emitting_materials[terrain]["preset"]
                        preset = LIGHT_PRESETS[preset_name]
                        light = LightSource(
                            x=x, y=y,
                            radius=preset["radius"],
                            color=preset["color"],
                            intensity=preset["intensity"],
                            flicker=preset["flicker"],
                            light_type=preset_name
                        )
                        self.lighting_engine.add_light(light)
                
                # Auto-Light entfernen: IMMER prüfen ob Lichtquelle existiert (auch beim Eraser!)
                else:
                    light_idx = self.lighting_engine.get_light_at(x, y, tolerance=0)
                    if light_idx is not None:
                        self.lighting_engine.remove_light(light_idx)
                        print(f"💡 Lichtquelle bei ({x},{y}) entfernt")
    
    def flood_fill(self, start_x, start_y, new_terrain):
        """Füllt verbundene Tiles mit neuem Terrain (Flood Fill)"""
        old_terrain = self.map[start_y][start_x]
        
        if old_terrain == new_terrain:
            return
        
        self.save_undo_state()
        
        # Stack-basierter Flood Fill
        stack = [(start_x, start_y)]
        visited = set()
        changed_tiles = []
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
            
            if not (0 <= x < self.width and 0 <= y < self.height):
                continue
            
            if self.map[y][x] != old_terrain:
                continue
            
            visited.add((x, y))
            changed_tiles.append((x, y))
            self.set_tile(x, y, new_terrain)
            
            # 4-Richtungen (NSWE)
            stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        
        # Batch-Update: Nur einmal komplett neu zeichnen statt für jeden Tile
        print(f"🪣 {len(visited)} Tiles gefüllt - Aktualisiere Ansicht...")
        
        if len(changed_tiles) > 100:
            # Bei vielen Tiles: Komplettes Neuzeichnen ist schneller
            self.draw_grid()
        else:
            # Bei wenigen Tiles: Einzeln updaten
            for x, y in changed_tiles:
                self.update_tile(x, y)
        
        print(f"✅ Fertig!")
    
    def draw_shape(self, start, end, shape_type):
        """Zeichnet eine geometrische Form"""
        self.save_undo_state()
        
        x1, y1 = start
        x2, y2 = end
        
        tiles = []
        
        if shape_type == "rectangle":
            # Rechteck
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    tiles.append((x, y))
        
        elif shape_type == "line":
            # Bresenham's Line Algorithm
            tiles = self.bresenham_line(x1, y1, x2, y2)
        
        elif shape_type == "circle":
            # Kreis um Startpunkt mit Radius = Distanz
            radius = int(((x2-x1)**2 + (y2-y1)**2)**0.5)
            
            for y in range(max(0, y1-radius), min(self.height, y1+radius+1)):
                for x in range(max(0, x1-radius), min(self.width, x1+radius+1)):
                    dist = ((x-x1)**2 + (y-y1)**2)**0.5
                    if abs(dist - radius) < 1.5:  # Ring
                        tiles.append((x, y))
        
        # Tiles setzen (batch)
        for x, y in tiles:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.set_tile(x, y, self.selected_terrain)
        
        # Batch-Update: Bei vielen Tiles komplettes Neuzeichnen
        if len(tiles) > 50:
            self.draw_grid()
        else:
            for x, y in tiles:
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.update_tile(x, y)
        
        print(f"📐 {shape_type.title()} mit {len(tiles)} Tiles gezeichnet")
    
    def bresenham_line(self, x1, y1, x2, y2):
        """Bresenham's Line Algorithm für Linie zwischen zwei Punkten"""
        points = []
        
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        while True:
            points.append((x, y))
            
            if x == x2 and y == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return points
    
    def update_shape_preview(self, start, end, shape_type):
        """Zeigt Shape-Preview während des Zeichnens"""
        # Clear old preview
        self.clear_shape_preview()
        
        x1, y1 = start
        x2, y2 = end
        
        # Berechne Preview-Tiles (gleiche Logik wie draw_shape)
        tiles = []
        
        if shape_type == "rectangle":
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    tiles.append((x, y))
        elif shape_type == "line":
            tiles = self.bresenham_line(x1, y1, x2, y2)
        elif shape_type == "circle":
            radius = int(((x2-x1)**2 + (y2-y1)**2)**0.5)
            for y in range(max(0, y1-radius), min(self.height, y1+radius+1)):
                for x in range(max(0, x1-radius), min(self.width, x1+radius+1)):
                    dist = ((x-x1)**2 + (y-y1)**2)**0.5
                    if abs(dist - radius) < 1.5:
                        tiles.append((x, y))
        
        # Preview als halbtransparentes Overlay
        for x, y in tiles:
            if 0 <= x < self.width and 0 <= y < self.height:
                x1 = x * self.tile_size
                y1 = y * self.tile_size
                
                preview_id = self.canvas.create_rectangle(
                    x1, y1, x1 + self.tile_size, y1 + self.tile_size,
                    fill="yellow", outline="orange", width=2,
                    stipple="gray50",  # Halbtransparent-Effekt
                    tags="shape_preview"
                )
                self.shape_preview.append(preview_id)
    
    def clear_shape_preview(self):
        """Löscht Shape-Preview"""
        for preview_id in self.shape_preview:
            self.canvas.delete(preview_id)
        self.shape_preview.clear()
    
    def draw_selection_preview(self):
        """Zeigt Auswahl-Bereich als Preview"""
        self.canvas.delete("selection_preview")
        
        if not self.selection_area:
            return
        
        x1, y1, x2, y2 = self.selection_area
        
        # Sortieren
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Rahmen zeichnen
        px1 = x1 * self.tile_size
        py1 = y1 * self.tile_size
        px2 = (x2 + 1) * self.tile_size
        py2 = (y2 + 1) * self.tile_size
        
        self.canvas.create_rectangle(
            px1, py1, px2, py2,
            outline="cyan", width=3,
            dash=(5, 5),
            tags="selection_preview"
        )
    
    def finalize_selection(self):
        """Schließt Auswahl ab und kopiert Inhalt"""
        if not self.selection_area:
            return
        
        x1, y1, x2, y2 = self.selection_area
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Inhalt kopieren
        self.selection_content = []
        for y in range(y1, y2 + 1):
            row = []
            for x in range(x1, x2 + 1):
                row.append(self.map[y][x])
            self.selection_content.append(row)
        
        count = (x2 - x1 + 1) * (y2 - y1 + 1)
        print(f"✂️ Auswahl: {x2-x1+1}×{y2-y1+1} ({count} Tiles)")
        
        # Zurücksetzen
        self.selection_area = None
        self.is_drawing = False
        self.canvas.delete("selection_preview")
    
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
    
    def on_layer_change(self):
        """Callback wenn Layer geändert wird"""
        # Aktualisiere Canvas
        self.draw_grid()
        print(f"🎨 Layer gewechselt: {self.layer_manager.get_active_layer().name}")
    
    def start_lighting_animation(self):
        """Starte Lighting-Animation-Loop"""
        if self.lighting_update_id is None:
            self.update_lighting_animation()
    
    def update_lighting_animation(self):
        """Update Lighting (für Flicker-Animation)"""
        # Zeit hochzählen
        self.lighting_time += 0.1
        
        # Nur neu rendern wenn Lighting aktiv und Lichtquellen vorhanden
        if self.show_lighting.get() and self.lighting_engine.enabled and len(self.lighting_engine.lights) > 0:
            # Prüfe ob irgendein Licht flackert
            has_flicker = any(light.flicker for light in self.lighting_engine.lights)
            if has_flicker:
                self.draw_grid()  # Neu rendern für Animation
        
        # Timer für nächstes Update (30 FPS für Flicker)
        self.lighting_update_id = self.after(33, self.update_lighting_animation)
    
    def toggle_lighting(self):
        """Toggle Lighting System"""
        self.lighting_engine.enabled = self.show_lighting.get()
        self.draw_grid()
        status = "aktiviert" if self.show_lighting.get() else "deaktiviert"
        print(f"💡 Dynamic Lighting {status}")
    
    def clear_all_lights(self):
        """Entferne alle Lichtquellen"""
        if messagebox.askyesno("Bestätigen", "Alle Lichtquellen löschen?"):
            self.lighting_engine.clear_lights()
            self.draw_grid()
            print("💡 Alle Lichtquellen entfernt")
    
    def update_radius_scale(self, value):
        """Update globaler Radius-Skalierungsfaktor"""
        scale = float(value)
        self.lighting_engine.global_radius_scale = scale
        self.radius_label.config(text=f"{scale:.1f}x")
        self.draw_grid()
    
    def update_lighting_mode(self):
        """Update Lighting Mode (Day/Night)"""
        mode = self.lighting_mode_var.get()
        self.lighting_engine.lighting_mode = mode
        self.draw_grid()
        mode_names = {"day": "Tag (Innenräume dunkel)", "night": "Nacht (komplett dunkel)"}
        print(f"☀️ Lighting-Mode: {mode_names.get(mode, mode)}")
    
    def update_darkness_opacity(self, value):
        """Update Darkness Opacity (für Tag-Modus)"""
        opacity = float(value)
        self.lighting_engine.darkness_opacity = opacity
        self.darkness_label.config(text=f"{int(opacity*100)}%")
        self.draw_grid()
    
    def select_light(self, index):
        """Wähle eine Lichtquelle aus"""
        if 0 <= index < len(self.lighting_engine.lights):
            self.selected_light_index = index
            light = self.lighting_engine.lights[index]
            
            # Update UI
            self.selected_light_info.config(text=f"🔥 {light.light_type.title()} @ ({light.x},{light.y})", fg="#4a4")
            self.individual_radius_var.set(light.radius)
            self.individual_radius_slider.config(state=tk.NORMAL)
            self.individual_radius_label.config(text=f"{light.radius:.1f}")
            
            self.draw_grid()
    
    def deselect_light(self):
        """Hebe Lichtquellen-Auswahl auf"""
        self.selected_light_index = None
        self.selected_light_info.config(text="Keine ausgewählt", fg="#888")
        self.individual_radius_slider.config(state=tk.DISABLED)
        self.draw_grid()
    
    def update_individual_radius(self, value):
        """Update Radius der ausgewählten Lichtquelle"""
        if self.selected_light_index is not None and 0 <= self.selected_light_index < len(self.lighting_engine.lights):
            radius = float(value)
            light = self.lighting_engine.lights[self.selected_light_index]
            light.radius = int(radius)
            self.individual_radius_label.config(text=f"{radius:.1f}")
            self.draw_grid()
    
    def delete_selected_light(self, event=None):
        """Lösche die ausgewählte Lichtquelle (Entf-Taste)"""
        if self.selected_light_index is not None:
            light = self.lighting_engine.lights[self.selected_light_index]
            self.lighting_engine.remove_light(self.selected_light_index)
            print(f"💡 Lichtquelle {light.light_type} bei ({light.x},{light.y}) gelöscht")
            self.deselect_light()
    
    def start_darkness_polygon(self):
        """Starte Zeichnen eines Dunkelheits-Polygons"""
        self.drawing_darkness_polygon = True
        self.current_darkness_polygon = []
        self.update_polygon_info()
        print("🖊️ Polygon-Modus: Klicke Punkte auf der Map (Rechtsklick = fertig)")
    
    def cancel_darkness_polygon(self):
        """Abbrechen des aktuellen Polygons"""
        self.drawing_darkness_polygon = False
        self.current_darkness_polygon = []
        self.update_polygon_info()
        self.draw_grid()
        print("❌ Polygon-Zeichnung abgebrochen")
    
    def clear_darkness_polygons(self):
        """Lösche alle Darkness-Polygone"""
        if messagebox.askyesno("Bestätigen", "Alle Dunkel-Bereiche löschen?"):
            self.lighting_engine.darkness_polygons.clear()
            self.update_polygon_info()
            self.draw_grid()
            print("🗑️ Alle Dunkel-Polygone gelöscht")
    
    def finish_darkness_polygon(self):
        """Schließe das aktuelle Polygon ab"""
        if len(self.current_darkness_polygon) >= 3:
            self.lighting_engine.darkness_polygons.append(self.current_darkness_polygon.copy())
            print(f"✅ Polygon gespeichert: {len(self.current_darkness_polygon)} Punkte")
        self.drawing_darkness_polygon = False
        self.current_darkness_polygon = []
        self.update_polygon_info()
        self.draw_grid()
    
    def update_polygon_info(self):
        """Update Polygon-Info-Label"""
        num_polygons = len(self.lighting_engine.darkness_polygons)
        num_points = len(self.current_darkness_polygon)
        if self.drawing_darkness_polygon:
            self.polygon_info_label.config(text=f"{num_polygons} Polygone | Aktuell: {num_points} Punkte", fg="#4a4")
        else:
            self.polygon_info_label.config(text=f"{num_polygons} Polygone gespeichert", fg="#888")
    
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
                "river_directions": self.river_directions,
                "layers": self.layer_manager.to_dict(),  # Layer-Daten speichern
                "lighting": self.lighting_engine.to_dict()  # Lighting speichern
            }
            
            # SVG-Metadata behalten wenn vorhanden
            if self.is_svg_mode and self.svg_source_path:
                map_data["is_svg_mode"] = True
                map_data["svg_path"] = self.svg_source_path
                # Original SVG-Größe falls verfügbar
                if hasattr(self, 'original_svg_size'):
                    map_data["original_svg_size"] = self.original_svg_size
            
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
                    
                    # Layer-Daten laden
                    if "layers" in map_data:
                        self.layer_manager.from_dict(map_data["layers"])
                    
                    # Lighting-Daten laden
                    if "lighting" in map_data:
                        self.lighting_engine.from_dict(map_data["lighting"])
                        self.lighting_enabled = map_data["lighting"].get("enabled", False)
                        
                        # Synchronisiere UI mit geladenen Daten
                        self.lighting_mode_var.set(self.lighting_engine.lighting_mode)
                        self.darkness_opacity_var.set(int(self.lighting_engine.darkness_opacity * 100))
                        
                        print(f"💡 {len(self.lighting_engine.lights)} Lichtquellen geladen")
                        print(f"☀️ Lighting-Mode: {self.lighting_engine.lighting_mode}")
                        print(f"🏠 Darkness-Polygone: {len(self.lighting_engine.darkness_polygons)}")
                    
                    # SVG-Metadata laden
                    if map_data.get("is_svg_mode"):
                        self.is_svg_mode = True
                        self.svg_source_path = map_data.get("svg_path")
                        if "original_svg_size" in map_data:
                            self.original_svg_size = map_data["original_svg_size"]
                    
                    # Reset tool states
                    self.shape_start = None
                    self.is_drawing = False
                    self.shape_preview = []
                    self.selection_area = None
                    self.clear_shape_preview()
                    
                    # Update canvas scroll region for new map size
                    canvas_width = self.width * self.tile_size
                    canvas_height = self.height * self.tile_size
                    self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
                    
                    # Redraw map
                    self.draw_grid()
                    
                    # Update performance mode if needed
                    self.total_tiles = self.width * self.height
                    self.performance_mode = self.total_tiles > 1000
                    
                    messagebox.showinfo("Erfolg", f"Karte geladen:\n{filename}\nGröße: {self.width}×{self.height}")
                else:
                    messagebox.showerror("Fehler", "Karte konnte nicht geladen werden")
            except Exception as e:
                import traceback
                messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}\n\n{traceback.format_exc()}")
    
    def get_map_data(self):
        """Gibt vollständige Map-Daten zurück (für Projektor, etc.)"""
        map_data = {
            "width": self.width,
            "height": self.height,
            "tiles": self.map,
            "river_directions": self.river_directions,
            "layers": self.layer_manager.to_dict(),
            "lighting": self.lighting_engine.to_dict()
        }
        
        # SVG-Metadata falls vorhanden
        if self.is_svg_mode and self.svg_source_path:
            map_data["is_svg_mode"] = True
            map_data["svg_path"] = self.svg_source_path
            if hasattr(self, 'original_svg_size'):
                map_data["original_svg_size"] = self.original_svg_size
        
        return map_data
    
    def export_as_svg(self):
        """Map als SVG exportieren mit Qualitäts-Dialog"""
        # WARNUNG: SVG kann keine Lighting-Daten speichern!
        if self.lighting_engine.lights:
            warning = (
                f"⚠️ ACHTUNG: LIGHTING-DATEN GEHEN VERLOREN!\n\n"
                f"Diese Map hat {len(self.lighting_engine.lights)} Lichtquelle(n).\n\n"
                f"SVG kann keine Lighting-Daten speichern!\n"
                f"Die Lichter werden beim Export entfernt.\n\n"
                f"Um Lighting zu behalten:\n"
                f"1. Speichere VORHER als JSON (Datei → Speichern)\n"
                f"2. JSON behält alle Lichtquellen und Flacker-Animationen\n"
                f"3. JSON kann im Projektor verwendet werden\n\n"
                f"Trotzdem SVG exportieren (Lighting geht verloren)?"
            )
            if not messagebox.askyesno("Lighting geht verloren", warning):
                return
        
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

    # ===========================
    # NEUE CONTEXT-PANEL METHODEN
    # ===========================
    
    def show_light_context(self, light_index):
        """Zeige Context-Panel für ausgewählte Lichtquelle"""
        if light_index >= len(self.lighting_engine.lights):
            return
        
        light = self.lighting_engine.lights[light_index]
        
        # Context-Panel erstellen falls noch nicht vorhanden
        if not self.context_panel:
            self.context_panel = ContextPanel(self)
            
            # Callbacks setzen
            self.context_panel.on_radius_change = self._on_light_radius_change
            self.context_panel.on_intensity_change = self._on_light_intensity_change
            self.context_panel.on_delete_light = self._on_delete_light
            self.context_panel.on_duplicate_light = self._on_duplicate_light
        
        self.context_panel.show_light_context(light)
        self.selected_light_index = light_index
    
    def show_polygon_context(self, polygon_index):
        """Zeige Context-Panel für ausgewähltes Polygon"""
        if polygon_index >= len(self.lighting_engine.darkness_polygons):
            return
        
        polygon = self.lighting_engine.darkness_polygons[polygon_index]
        
        # Context-Panel erstellen falls noch nicht vorhanden
        if not self.context_panel:
            self.context_panel = ContextPanel(self)
            
            # Callbacks setzen
            self.context_panel.on_edit_polygon = self._on_edit_polygon
            self.context_panel.on_delete_polygon = self._on_delete_polygon
        
        self.context_panel.show_polygon_context(polygon)
    
    def hide_context_panel(self):
        """Verstecke Context-Panel"""
        if self.context_panel:
            self.context_panel.hide()
        self.selected_light_index = None
    
    def _on_light_radius_change(self, new_radius):
        """Callback: Radius der ausgewählten Lichtquelle ändern"""
        if self.selected_light_index is not None and self.selected_light_index < len(self.lighting_engine.lights):
            light = self.lighting_engine.lights[self.selected_light_index]
            light.radius = new_radius
            print(f"💡 Radius geändert: {new_radius}")
            if self.show_lighting.get():
                self.draw_grid()
    
    def _on_light_intensity_change(self, new_intensity):
        """Callback: Intensität der ausgewählten Lichtquelle ändern"""
        if self.selected_light_index is not None and self.selected_light_index < len(self.lighting_engine.lights):
            light = self.lighting_engine.lights[self.selected_light_index]
            light.intensity = new_intensity
            print(f"💡 Intensität geändert: {new_intensity}")
            if self.show_lighting.get():
                self.draw_grid()
    
    def _on_delete_light(self):
        """Callback: Lichtquelle löschen"""
        if self.selected_light_index is not None and self.selected_light_index < len(self.lighting_engine.lights):
            self.lighting_engine.lights.pop(self.selected_light_index)
            print(f"🗑️ Lichtquelle gelöscht")
            self.hide_context_panel()
            self.select_tool.deselect_all()
            if self.show_lighting.get():
                self.draw_grid()
    
    def _on_duplicate_light(self):
        """Callback: Lichtquelle duplizieren"""
        if self.selected_light_index is not None and self.selected_light_index < len(self.lighting_engine.lights):
            original = self.lighting_engine.lights[self.selected_light_index]
            # Erstelle Kopie mit leichtem Offset
            duplicate = LightSource(
                x=original.x + 1,
                y=original.y + 1,
                radius=original.radius,
                color=original.color,
                intensity=original.intensity,
                light_type=original.light_type,
                flicker=original.flicker
            )
            self.lighting_engine.lights.append(duplicate)
            print(f"📋 Lichtquelle dupliziert")
            if self.show_lighting.get():
                self.draw_grid()
    
    def _on_edit_polygon(self):
        """Callback: Polygon bearbeiten"""
        # TODO: Implementierung für Polygon-Edit-Modus
        print("✏️ Polygon-Bearbeitung (noch nicht implementiert)")
    
    def _on_delete_polygon(self):
        """Callback: Polygon löschen"""
        if self.select_tool.selected_polygon is not None:
            index = self.select_tool.selected_polygon
            if index < len(self.lighting_engine.darkness_polygons):
                self.lighting_engine.darkness_polygons.pop(index)
                print(f"🗑️ Polygon gelöscht")
                self.hide_context_panel()
                self.select_tool.deselect_all()
                if self.show_lighting.get():
                    self.draw_grid()

