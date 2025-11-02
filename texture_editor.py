"""
Texture Editor für "Der Eine Ring"
Ermöglicht das Erstellen und Bearbeiten eigener Texturen mit erweiterten Tools
"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from PIL import Image, ImageDraw, ImageTk, ImageFilter, ImageChops
import os
import math
import random


class TextureEditor(tk.Toplevel):
    """
    Editor zum Erstellen und Bearbeiten von Texturen
    Mit Pinsel, Radierer, Verwisch-Tool, Farbauswahl und Multi-Frame Animation
    """
    
    def __init__(self, parent, material_id=None, material_name=None, 
                 base_color=(128, 128, 128), renderer=None, on_save_callback=None, tile_size=None):
        super().__init__(parent)
        
        self.renderer = renderer
        self.on_save_callback = on_save_callback
        
        # Editor-Eigenschaften
        self.material_id = material_id
        self.material_name = material_name or "Neues Material"
        self.is_new_material = material_id is None
        
        # Canvas-Größe BASIEREND AUF TILE SIZE
        # Wenn tile_size übergeben wird, nutze das (z.B. 32px, 50px)
        # Für Zeichnen vergrößern wir auf 512px für bessere Bearbeitbarkeit
        self.actual_tile_size = tile_size or 32  # Echte Tile-Größe
        self.canvas_size = 512  # Immer 512px für Editor (wird runterskaliert)
        self.scale_factor = self.canvas_size / self.actual_tile_size  # z.B. 512/32 = 16x
        
        # ANIMATION FRAMES System
        self.frames = []  # Liste von PIL Images (ein Image pro Frame)
        self.current_frame_index = 0
        self.is_animated = False
        
        # ANIMATION FRAMES System
        self.frames = []  # Liste von PIL Images (ein Image pro Frame)
        self.current_frame_index = 0
        self.is_animated = False
        
        # Initialer Frame - Lade existierendes Material wenn vorhanden
        initial_frame = self.load_existing_material() or Image.new('RGBA', (self.canvas_size, self.canvas_size), base_color + (255,))
        self.frames.append(initial_frame)
        
        # Zeichenfläche (zeigt aktuellen Frame)
        self.texture_image = self.frames[0].copy()
        self.texture_draw = ImageDraw.Draw(self.texture_image)
        
        # Zeichnen-State
        self.current_color = base_color
        self.is_drawing = False
        self.last_x = None
        self.last_y = None
        
        # PROFESSIONELLE TOOLS
        self.tool = "brush"  # brush, pencil, eraser, fill, eyedropper, blur, spray, line, curve, rectangle, circle, select, move
        self.brush_size = 3  # 1-50 für brush/blur/spray
        self.brush_opacity = 255  # 0-255
        
        # MAL-MODI (Material-Systeme)
        self.paint_mode = "acryl"  # acryl, oil, watercolor
        self.paint_mode_settings = {
            "acryl": {"mix": 0.2, "flow": 1.0, "texture": 0.1},  # Deckend, wenig Mischung
            "oil": {"mix": 0.6, "flow": 0.7, "texture": 0.3},    # Stark mischbar, dickflüssig
            "watercolor": {"mix": 0.8, "flow": 1.5, "texture": 0.05}  # Sehr transparent, fließend
        }
        
        # SPRAY CAN
        self.spray_density = 50  # 1-100 Partikel pro Spray
        self.spray_randomness = 0.8  # 0-1 Streuung
        
        # FORM-TOOLS
        self.shape_fill = True  # Formen gefüllt oder nur Umriss
        self.shape_outline_width = 2
        self.shape_start_pos = None  # Für Formen und Linien
        
        # KURVEN (Bezier)
        self.curve_points = []  # Kontrollpunkte für Bezier-Kurven
        
        # SELECTION & TRANSFORM
        self.selection_rect = None  # (x1, y1, x2, y2)
        self.selected_image = None  # Ausgewählter Bereich als Image
        self.transform_mode = None  # None, "move", "scale", "rotate"
        
        # GRAFIKTABLETT-SUPPORT
        self.tablet_pressure = 1.0  # 0-1, wird von Tablet-Events gesetzt
        self.use_pressure = True  # Drucksensitivität aktivieren
        
        # KEYBOARD SHORTCUTS
        self.setup_keyboard_shortcuts()
        
        # Undo/Redo (pro Frame)
        self.history = [self.texture_image.copy()]
        self.history_index = 0
        self.max_history = 50
        
        self.setup_ui()
    
    def setup_keyboard_shortcuts(self):
        """Richtet Tastaturkürzel ein"""
        # Werkzeug-Shortcuts
        self.bind('b', lambda e: self.select_tool('brush'))
        self.bind('B', lambda e: self.select_tool('brush'))
        self.bind('e', lambda e: self.select_tool('eraser'))
        self.bind('E', lambda e: self.select_tool('eraser'))
        self.bind('k', lambda e: self.select_tool('eyedropper'))
        self.bind('K', lambda e: self.select_tool('eyedropper'))
        self.bind('i', lambda e: self.select_tool('eyedropper'))  # Pipette = I
        self.bind('I', lambda e: self.select_tool('eyedropper'))
        self.bind('f', lambda e: self.select_tool('fill'))
        self.bind('F', lambda e: self.select_tool('fill'))
        self.bind('g', lambda e: self.select_tool('fill'))  # G wie "Gießen"
        self.bind('G', lambda e: self.select_tool('fill'))
        self.bind('s', lambda e: self.select_tool('spray'))
        self.bind('S', lambda e: self.select_tool('spray'))
        self.bind('l', lambda e: self.select_tool('line'))
        self.bind('L', lambda e: self.select_tool('line'))
        self.bind('u', lambda e: self.select_tool('curve'))  # U wie "kUrve"
        self.bind('U', lambda e: self.select_tool('curve'))
        self.bind('r', lambda e: self.select_tool('rectangle'))
        self.bind('R', lambda e: self.select_tool('rectangle'))
        self.bind('c', lambda e: self.select_tool('circle'))
        self.bind('C', lambda e: self.select_tool('circle'))
        self.bind('m', lambda e: self.select_tool('move'))
        self.bind('M', lambda e: self.select_tool('move'))
        self.bind('v', lambda e: self.select_tool('select'))  # V wie auswählen
        self.bind('V', lambda e: self.select_tool('select'))
        
        # Undo/Redo
        self.bind('<Control-z>', lambda e: self.undo())
        self.bind('<Control-y>', lambda e: self.redo())
        self.bind('<Control-Shift-Z>', lambda e: self.redo())
        
        # Pinselgröße
        self.bind('[', lambda e: self.change_brush_size(-2))
        self.bind(']', lambda e: self.change_brush_size(2))
        
        # Deckkraft
        self.bind('<', lambda e: self.change_opacity(-10))
        self.bind('>', lambda e: self.change_opacity(10))
        
        # Transform (nur wenn Selektion aktiv)
        self.bind('t', lambda e: self.toggle_transform_mode())
        self.bind('T', lambda e: self.toggle_transform_mode())
        self.bind('<Delete>', lambda e: self.delete_selection())
        self.bind('<Escape>', lambda e: self.cancel_selection())
        
        # Selektion kopieren/ausschneiden/einfügen
        self.bind('<Control-c>', lambda e: self.copy_selection())
        self.bind('<Control-x>', lambda e: self.cut_selection())
        self.bind('<Control-v>', lambda e: self.paste_selection())
        
        # Hilfe
        self.bind('h', lambda e: self.show_help())
        self.bind('H', lambda e: self.show_help())
        self.bind('<F1>', lambda e: self.show_help())
    
    def change_brush_size(self, delta):
        """Ändert Pinselgröße via Shortcut"""
        if hasattr(self, 'brush_size_var'):
            new_size = max(1, min(50, self.brush_size + delta))
            self.brush_size_var.set(new_size)
            self.update_brush_size(new_size)
    
    def change_opacity(self, delta):
        """Ändert Deckkraft via Shortcut"""
        if hasattr(self, 'opacity_var'):
            new_opacity = max(10, min(255, self.brush_opacity + delta))
            self.opacity_var.set(new_opacity)
            self.update_opacity(new_opacity)
    
    def load_existing_material(self):
        """Lädt existierendes Material als Vorlage"""
        if not self.material_id or not self.renderer:
            return None
        
        try:
            # Versuche Material zu laden (frame 0 für statische, oder erstes Frame für animiert)
            texture_path = os.path.join("textures", f"{self.material_id}_frame_0.png")
            if not os.path.exists(texture_path):
                texture_path = os.path.join("textures", f"{self.material_id}.png")
            
            if os.path.exists(texture_path):
                img = Image.open(texture_path).convert('RGBA')
                # Auf canvas_size skalieren
                img = img.resize((self.canvas_size, self.canvas_size), Image.LANCZOS)
                return img
        except Exception as e:
            print(f"Fehler beim Laden des Materials: {e}")
        
        return None
    
    def setup_ui(self):
        """UI erstellen"""
        self.title(f"Textur-Editor - {self.material_name}")
        
        # Größeres Fenster damit alles sichtbar ist
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = min(1200, int(screen_width * 0.9))
        window_height = min(900, int(screen_height * 0.9))
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Fenster im Vordergrund halten
        self.lift()
        self.focus_force()
        
        self.configure(bg="#2a2a2a")
        
        # Haupt-Container
        main_container = tk.Frame(self, bg="#2a2a2a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Linke Seite: Werkzeuge (erstmal nur Frame, Tools später)
        tools_frame = tk.Frame(main_container, bg="#1a1a1a", width=150)
        tools_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        tools_frame.pack_propagate(False)
        
        # Rechte Seite: Canvas und Optionen
        right_frame = tk.Frame(main_container, bg="#2a2a2a")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Top: Name und Speichern
        top_frame = tk.Frame(right_frame, bg="#2a2a2a")
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        tk.Label(top_frame, text="Material-Name:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.name_entry = tk.Entry(top_frame, font=("Arial", 10), width=25)
        self.name_entry.insert(0, self.material_name)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(top_frame, text="💾 Speichern", bg="#2a7d2a", fg="white",
                 font=("Arial", 10, "bold"), padx=15, pady=5,
                 command=self.save_texture).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(top_frame, text="📂 Importieren", bg="#2a5d8d", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.import_image).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(top_frame, text="📤 Exportieren", bg="#5d2a7d", fg="white",
                 font=("Arial", 10), padx=10, pady=5,
                 command=self.export_image).pack(side=tk.RIGHT, padx=5)
        
        # Canvas für Zeichnen (MUSS VOR setup_tools() kommen!)
        canvas_container = tk.Frame(right_frame, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
        canvas_container.pack(side=tk.TOP, pady=5)
        
        self.canvas = tk.Canvas(canvas_container, 
                               width=self.canvas_size, 
                               height=self.canvas_size,
                               bg="#ffffff", 
                               cursor="crosshair",
                               highlightthickness=0)
        self.canvas.pack(padx=2, pady=2)
        
        # Canvas Events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.pick_color)  # Rechtsklick = Farbpipette
        
        # FRAME CONTROLS (für Animation)
        frame_control_container = tk.Frame(right_frame, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
        frame_control_container.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        tk.Label(frame_control_container, text="🎬 Animation Frames", 
                bg="#1a1a1a", fg="#d4af37", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Frame Navigation
        nav_frame = tk.Frame(frame_control_container, bg="#1a1a1a")
        nav_frame.pack(pady=5)
        
        tk.Button(nav_frame, text="◄ Zurück", bg="#3a3a3a", fg="white",
                 font=("Arial", 9), padx=10, pady=3,
                 command=self.previous_frame).pack(side=tk.LEFT, padx=2)
        
        self.frame_label = tk.Label(nav_frame, text="Frame 1 / 1",
                                    bg="#1a1a1a", fg="white",
                                    font=("Arial", 10, "bold"), width=12)
        self.frame_label.pack(side=tk.LEFT, padx=5)
        
        tk.Button(nav_frame, text="Weiter ►", bg="#3a3a3a", fg="white",
                 font=("Arial", 9), padx=10, pady=3,
                 command=self.next_frame).pack(side=tk.LEFT, padx=2)
        
        # Frame Actions
        action_frame = tk.Frame(frame_control_container, bg="#1a1a1a")
        action_frame.pack(pady=5)
        
        tk.Button(action_frame, text="➕ Neuer Frame", bg="#2a7d2a", fg="white",
                 font=("Arial", 9), padx=8, pady=3,
                 command=self.add_new_frame).pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="📋 Frame Kopieren", bg="#2a5d8d", fg="white",
                 font=("Arial", 9), padx=8, pady=3,
                 command=self.duplicate_frame).pack(side=tk.LEFT, padx=2)
        
        tk.Button(action_frame, text="🗑️ Frame Löschen", bg="#8d2a2a", fg="white",
                 font=("Arial", 9), padx=8, pady=3,
                 command=self.delete_frame).pack(side=tk.LEFT, padx=2)
        
        # STATUSLEISTE
        self.status_bar = tk.Frame(right_frame, bg="#1a1a1a", height=30)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, before=frame_control_container)
        
        self.status_label = tk.Label(self.status_bar, text="Bereit | Werkzeug: Pinsel | Drücke H für Hilfe",
                                     bg="#1a1a1a", fg="#888", font=("Arial", 8), anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        tk.Button(self.status_bar, text="❓ Hilfe (H)", bg="#3a3a3a", fg="white",
                 font=("Arial", 8), padx=8, pady=2,
                 command=self.show_help).pack(side=tk.RIGHT, padx=5)
        
        # Bottom: Vorschau und Einstellungen
        bottom_frame = tk.Frame(right_frame, bg="#2a2a2a")
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        # Vorschau (klein)
        preview_frame = tk.Frame(bottom_frame, bg="#1a1a1a", relief=tk.SUNKEN, bd=2)
        preview_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Label(preview_frame, text="Vorschau (64x64)", bg="#1a1a1a", fg="white",
                font=("Arial", 8)).pack()
        
        self.preview_canvas = tk.Canvas(preview_frame, width=64, height=64,
                                        bg="#ffffff", highlightthickness=0)
        self.preview_canvas.pack(padx=5, pady=5)
        
        # Animation-Option
        self.is_animated_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bottom_frame, text="🎬 Animiert", variable=self.is_animated_var,
                      bg="#2a2a2a", fg="white", selectcolor="#3a3a3a",
                      font=("Arial", 10)).pack(side=tk.LEFT, padx=20)
        
        # Emoji-Auswahl
        tk.Label(bottom_frame, text="Symbol:", bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        self.emoji_entry = tk.Entry(bottom_frame, font=("Arial", 12), width=3)
        self.emoji_entry.insert(0, "🎨")
        self.emoji_entry.pack(side=tk.LEFT, padx=5)
        
        # JETZT Tools initialisieren (nachdem self.canvas existiert!)
        self.setup_tools(tools_frame)
        
        # Initial zeichnen
        self.update_canvas()
        self.update_preview()
    
    def setup_tools(self, parent):
        """Werkzeug-Panel erstellen - VOLLSTÄNDIG ERWEITERT"""
        tk.Label(parent, text="🛠️ Werkzeuge", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # ALLE Werkzeuge mit Shortcuts angezeigt
        tools = [
            ("🖌️ Pinsel (B)", "brush"),
            ("✏️ Bleistift (P)", "pencil"),
            ("🧹 Radierer (E)", "eraser"),
            ("🌫️ Verwischen", "blur"),
            ("💧 Füller (F)", "fill"),
            ("💉 Pipette (K)", "eyedropper"),
            ("🎨 Spray (S)", "spray"),
            ("📏 Linie (L)", "line"),
            ("〰️ Kurve (U)", "curve"),
            ("▭ Rechteck (R)", "rectangle"),
            ("⭕ Kreis (C)", "circle"),
            ("🔲 Auswahl (V)", "select"),
            ("✋ Bewegen (M)", "move")
        ]
        
        self.tool_buttons = {}
        for text, tool in tools:
            btn = tk.Button(parent, text=text, bg="#3a3a3a", fg="white",
                          font=("Arial", 8), width=14, pady=3,
                          command=lambda t=tool: self.select_tool(t))
            btn.pack(pady=1, padx=5)
            self.tool_buttons[tool] = btn
        
        self.select_tool("brush")
        
        # Separator
        tk.Frame(parent, bg="#555555", height=2).pack(fill=tk.X, pady=10, padx=10)
        
        # MAL-MODI
        tk.Label(parent, text="🎨 Mal-Modus", bg="#1a1a1a", fg="white",
                font=("Arial", 9, "bold")).pack(pady=(5, 2))
        
        self.paint_mode_var = tk.StringVar(value="acryl")
        
        mode_frame = tk.Frame(parent, bg="#1a1a1a")
        mode_frame.pack(fill=tk.X, padx=5)
        
        tk.Radiobutton(mode_frame, text="Acryl", variable=self.paint_mode_var,
                      value="acryl", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_paint_mode).pack(anchor=tk.W)
        
        tk.Radiobutton(mode_frame, text="Öl", variable=self.paint_mode_var,
                      value="oil", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_paint_mode).pack(anchor=tk.W)
        
        tk.Radiobutton(mode_frame, text="Wasserfarbe", variable=self.paint_mode_var,
                      value="watercolor", bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=self.update_paint_mode).pack(anchor=tk.W)
        
        # Separator
        tk.Frame(parent, bg="#555555", height=2).pack(fill=tk.X, pady=10, padx=10)
        
        # Pinselgröße
        tk.Label(parent, text="Pinselgröße [ ]", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.brush_size_var = tk.IntVar(value=3)
        brush_scale = tk.Scale(parent, from_=1, to=50, orient=tk.HORIZONTAL,
                              variable=self.brush_size_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0,
                              command=self.update_brush_size)
        brush_scale.pack(fill=tk.X, padx=10)
        
        # Deckkraft/Opacity
        tk.Label(parent, text="Deckkraft < >", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.opacity_var = tk.IntVar(value=255)
        opacity_scale = tk.Scale(parent, from_=10, to=255, orient=tk.HORIZONTAL,
                              variable=self.opacity_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0,
                              command=self.update_opacity)
        opacity_scale.pack(fill=tk.X, padx=10)
        
        # SPRAY-EINSTELLUNGEN (nur sichtbar bei Spray-Tool)
        self.spray_frame = tk.Frame(parent, bg="#1a1a1a")
        # Wird später ein/ausgeblendet
        
        tk.Label(self.spray_frame, text="Spray-Dichte", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.spray_density_var = tk.IntVar(value=50)
        spray_scale = tk.Scale(self.spray_frame, from_=10, to=100, orient=tk.HORIZONTAL,
                              variable=self.spray_density_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0,
                              command=lambda v: setattr(self, 'spray_density', int(v)))
        spray_scale.pack(fill=tk.X, padx=10)
        
        # FORM-TOOL OPTIONEN (nur sichtbar bei Formen)
        self.shape_frame = tk.Frame(parent, bg="#1a1a1a")
        # Wird später ein/ausgeblendet
        
        self.shape_fill_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.shape_frame, text="Gefüllt", variable=self.shape_fill_var,
                      bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=lambda: setattr(self, 'shape_fill', self.shape_fill_var.get())).pack(anchor=tk.W)
        
        tk.Label(self.shape_frame, text="Umrissstärke", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.outline_width_var = tk.IntVar(value=2)
        outline_scale = tk.Scale(self.shape_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                              variable=self.outline_width_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0,
                              command=lambda v: setattr(self, 'shape_outline_width', int(v)))
        outline_scale.pack(fill=tk.X, padx=10)
        
        # TABLET PRESSURE
        tk.Label(parent, text="🖊️ Tablet-Druck", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(10, 2))
        
        self.use_pressure_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="Drucksensitivität", variable=self.use_pressure_var,
                      bg="#1a1a1a", fg="white", selectcolor="#333",
                      command=lambda: setattr(self, 'use_pressure', self.use_pressure_var.get())).pack(anchor=tk.W, padx=10)
        
        # FÜLL-TOLERANZ (nur sichtbar bei Fill-Tool)
        self.fill_frame = tk.Frame(parent, bg="#1a1a1a")
        
        tk.Label(self.fill_frame, text="Füll-Toleranz", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.fill_tolerance_var = tk.IntVar(value=30)
        tolerance_scale = tk.Scale(self.fill_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                              variable=self.fill_tolerance_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0)
        tolerance_scale.pack(fill=tk.X, padx=10)
        
        tk.Label(self.fill_frame, text="(ähnliche Farben)", bg="#1a1a1a", fg="#888",
                font=("Arial", 7)).pack()
        
        # Separator
        tk.Frame(parent, bg="#555555", height=2).pack(fill=tk.X, pady=10, padx=10)
        
        # Farbwähler mit Vorschau
        tk.Label(parent, text="Farbe", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.color_display = tk.Canvas(parent, width=100, height=50,
                                       bg=self.rgb_to_hex(self.current_color),
                                       highlightthickness=2,
                                       highlightbackground="#d4af37")
        self.color_display.pack(pady=5)
        
        tk.Button(parent, text="🎨 Farbe wählen", bg="#3a3a3a", fg="white",
                 font=("Arial", 9), width=12,
                 command=self.choose_color).pack(pady=5, padx=5)
        
        # Schnell-Farben
        quick_colors = [
            ("Weiß", (255, 255, 255)),
            ("Schwarz", (0, 0, 0)),
            ("Rot", (200, 50, 50)),
            ("Grün", (50, 200, 50)),
            ("Blau", (50, 50, 200)),
            ("Gelb", (200, 200, 50))
        ]
        
        quick_frame = tk.Frame(parent, bg="#1a1a1a")
        quick_frame.pack(fill=tk.X, padx=5)
        
        for i, (name, color) in enumerate(quick_colors):
            if i % 3 == 0:
                row_frame = tk.Frame(quick_frame, bg="#1a1a1a")
                row_frame.pack(fill=tk.X)
            
            btn = tk.Button(row_frame, bg=self.rgb_to_hex(color), width=3, height=1,
                           command=lambda c=color: self.set_quick_color(c))
            btn.pack(side=tk.LEFT, padx=1, pady=1)
        
        # Separator
        tk.Frame(parent, bg="#555555", height=2).pack(fill=tk.X, pady=10, padx=10)
        
        # Aktionen
        tk.Label(parent, text="Aktionen", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        tk.Button(parent, text="↶ Rückgängig", bg="#3a3a3a", fg="white",
                 font=("Arial", 9), width=12,
                 command=self.undo).pack(pady=2, padx=5)
        
        tk.Button(parent, text="↷ Wiederholen", bg="#3a3a3a", fg="white",
                 font=("Arial", 9), width=12,
                 command=self.redo).pack(pady=2, padx=5)
        
        tk.Button(parent, text="🗑️ Löschen", bg="#7d2a2a", fg="white",
                 font=("Arial", 9), width=12,
                 command=self.clear_canvas).pack(pady=2, padx=5)
    
    def select_tool(self, tool):
        """Werkzeug auswählen"""
        self.tool = tool
        
        # Alle Buttons zurücksetzen
        for btn in self.tool_buttons.values():
            btn.config(relief=tk.RAISED, bg="#3a3a3a")
        
        # Ausgewählten Button hervorheben
        self.tool_buttons[tool].config(relief=tk.SUNKEN, bg="#2a5d8d")
        
        # Tool-spezifische Optionen ein/ausblenden
        if tool == "spray":
            self.spray_frame.pack(fill=tk.X, padx=5, before=self.shape_frame)
        else:
            self.spray_frame.pack_forget()
        
        if tool in ["rectangle", "circle"]:
            self.shape_frame.pack(fill=tk.X, padx=5, before=self.color_display if hasattr(self, 'color_display') else None)
        else:
            self.shape_frame.pack_forget()
        
        if tool == "fill":
            self.fill_frame.pack(fill=tk.X, padx=5, before=self.color_display if hasattr(self, 'color_display') else None)
        else:
            self.fill_frame.pack_forget()
        
        # Cursor ändern
        cursors = {
            "brush": "crosshair",
            "pencil": "pencil",
            "eraser": "circle",
            "blur": "crosshair",
            "fill": "spraycan",
            "eyedropper": "target",
            "spray": "crosshair",
            "line": "crosshair",
            "curve": "crosshair",
            "rectangle": "crosshair",
            "circle": "crosshair",
            "select": "cross",
            "move": "fleur"
        }
        self.canvas.config(cursor=cursors.get(tool, "crosshair"))
        
        # Reset temporäre Tool-States
        if tool not in ["line", "curve", "rectangle", "circle", "select"]:
            self.shape_start_pos = None
            self.curve_points = []
        
        # Statusleiste aktualisieren
        self.update_status("Bereit")
    
    def update_paint_mode(self):
        """Aktualisiert den Mal-Modus"""
        self.paint_mode = self.paint_mode_var.get()
    
    def update_brush_size(self, value):
        """Pinselgröße aktualisieren"""
        self.brush_size = int(value)
    
    def update_opacity(self, value):
        """Deckkraft aktualisieren"""
        self.brush_opacity = int(value)
    
    def set_quick_color(self, color):
        """Schnell-Farbe setzen"""
        self.current_color = color
        self.color_display.config(bg=self.rgb_to_hex(color))
    
    def choose_color(self):
        """Farbe mit Farbwähler auswählen"""
        color = colorchooser.askcolor(
            initialcolor=self.rgb_to_hex(self.current_color),
            title="Farbe wählen",
            parent=self  # Dialog an dieses Fenster binden
        )
        
        if color[0]:  # RGB
            self.current_color = tuple(int(c) for c in color[0])
            self.color_display.config(bg=self.rgb_to_hex(self.current_color))
        
        # Fokus zurückholen
        self.lift()
        self.focus_force()
    
    def rgb_to_hex(self, rgb):
        """RGB zu Hex konvertieren"""
        return '#%02x%02x%02x' % rgb
    
    def on_canvas_click(self, event):
        """Klick auf Canvas - ERWEITERT für alle Tools"""
        # Tablet-Druck erkennen (falls verfügbar)
        if hasattr(event, 'pressure'):
            self.tablet_pressure = event.pressure
        else:
            self.tablet_pressure = 1.0
        
        if self.tool == "fill":
            self.flood_fill(event.x, event.y)
        elif self.tool == "eyedropper":
            self.pick_color(event)
        elif self.tool in ["line", "rectangle", "circle"]:
            # Form-Tools: Startpunkt setzen
            if self.shape_start_pos is None:
                self.shape_start_pos = (event.x, event.y)
            else:
                # Form fertigstellen
                self.finish_shape(event.x, event.y)
        elif self.tool == "curve":
            # Kurven-Kontrollpunkte sammeln
            self.curve_points.append((event.x, event.y))
            if len(self.curve_points) >= 4:
                # Bezier-Kurve mit 4 Punkten zeichnen
                self.draw_bezier_curve()
                self.curve_points = []
        elif self.tool == "select":
            # Selektion starten
            self.shape_start_pos = (event.x, event.y)
            self.is_drawing = True
        elif self.tool == "move":
            # Bewegen: Wenn Selektion existiert, verschieben starten
            if self.selection_rect:
                self.transform_mode = "move"
                self.last_x = event.x
                self.last_y = event.y
        else:
            # Standard Zeichen-Tools
            self.is_drawing = True
            self.last_x = event.x
            self.last_y = event.y
            self.draw_at(event.x, event.y)
    
    def on_canvas_drag(self, event):
        """Ziehen auf Canvas - ERWEITERT"""
        # Tablet-Druck aktualisieren
        if hasattr(event, 'pressure'):
            self.tablet_pressure = event.pressure
        
        if self.tool in ["brush", "pencil", "eraser", "blur", "spray"] and self.is_drawing:
            # Linie von letzter Position zur aktuellen zeichnen (smooth)
            if self.last_x is not None and self.last_y is not None:
                self.draw_line(self.last_x, self.last_y, event.x, event.y)
            else:
                self.draw_at(event.x, event.y)
            
            self.last_x = event.x
            self.last_y = event.y
            
            # Canvas während Drag updaten (für Live-Feedback)
            self.update_canvas()
        
        elif self.tool in ["line", "rectangle", "circle"] and self.shape_start_pos:
            # Form-Vorschau während Drag
            self.update_canvas()
            self.draw_shape_preview(event.x, event.y)
        
        elif self.tool == "select" and self.is_drawing:
            # Selektions-Rechteck Vorschau
            self.update_canvas()
            self.draw_selection_preview(event.x, event.y)
        
        elif self.tool == "move" and self.transform_mode == "move":
            # Selektion bewegen
            dx = event.x - self.last_x
            dy = event.y - self.last_y
            self.move_selection(dx, dy)
            self.last_x = event.x
            self.last_y = event.y
    
    def on_canvas_release(self, event):
        """Maus losgelassen - ERWEITERT"""
        if self.tool == "select" and self.is_drawing and self.shape_start_pos:
            # Selektion finalisieren
            x1, y1 = self.shape_start_pos
            x2, y2 = event.x, event.y
            self.selection_rect = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            self.extract_selection()
            self.shape_start_pos = None
        
        if self.is_drawing:
            self.is_drawing = False
            self.last_x = None
            self.last_y = None
            self.transform_mode = None
            
            # Final update
            self.update_canvas()
            self.update_preview()
            self.save_to_history()
    
    def draw_line(self, x1, y1, x2, y2):
        """Zeichnet eine Linie von (x1,y1) zu (x2,y2) für smoothes Zeichnen"""
        # Bresenham's Line Algorithm für gleichmäßige Striche
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            self.draw_at(x1, y1)
            
            if x1 == x2 and y1 == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
    
    def draw_at(self, x, y):
        """Zeichnet an Position x, y mit dem aktuellen Werkzeug - ERWEITERT"""
        if self.tool == "brush":
            self.draw_brush(x, y)
        elif self.tool == "pencil":
            self.draw_pencil(x, y)
        elif self.tool == "eraser":
            self.draw_eraser(x, y)
        elif self.tool == "blur":
            self.apply_blur(x, y)
        elif self.tool == "spray":
            self.draw_spray(x, y)
    
    def draw_pencil(self, x, y):
        """Bleistift - präzises 1-Pixel-Zeichnen"""
        if 0 <= x < self.canvas_size and 0 <= y < self.canvas_size:
            # Exakt 1 Pixel setzen
            self.texture_image.putpixel((x, y), self.current_color + (255,))
    
    def draw_brush(self, x, y):
        """Zeichnet mit Pinsel - MIT MAL-MODI und TABLET-DRUCK"""
        draw = ImageDraw.Draw(self.texture_image, 'RGBA')
        
        # Tablet-Druck berücksichtigen
        pressure = self.tablet_pressure if self.use_pressure else 1.0
        effective_size = int(self.brush_size * pressure)
        effective_opacity = int(self.brush_opacity * pressure)
        
        # Mal-Modus Einstellungen holen
        mode_settings = self.paint_mode_settings[self.paint_mode]
        mix_factor = mode_settings["mix"]
        flow = mode_settings["flow"]
        
        # Kreis mit Deckkraft zeichnen
        for i in range(-effective_size, effective_size + 1):
            for j in range(-effective_size, effective_size + 1):
                if i*i + j*j <= effective_size*effective_size:
                    px, py = x + i, y + j
                    if 0 <= px < self.canvas_size and 0 <= py < self.canvas_size:
                        try:
                            old_color = self.texture_image.getpixel((px, py))
                            if len(old_color) == 3:
                                old_color = old_color + (255,)
                            
                            # MAL-MODI: Verschiedene Mischverhalten
                            if self.paint_mode == "oil":
                                # Öl: Starke Mischung mit Untergrund
                                alpha = (effective_opacity / 255.0) * flow
                                mixed_alpha = alpha * (1 - mix_factor) + mix_factor
                                new_r = int(old_color[0] * (1 - mixed_alpha) + self.current_color[0] * mixed_alpha)
                                new_g = int(old_color[1] * (1 - mixed_alpha) + self.current_color[1] * mixed_alpha)
                                new_b = int(old_color[2] * (1 - mixed_alpha) + self.current_color[2] * mixed_alpha)
                            
                            elif self.paint_mode == "watercolor":
                                # Wasserfarben: Transparent, fließend
                                alpha = (effective_opacity / 255.0) * 0.3 * flow  # Sehr transparent
                                new_r = int(old_color[0] * (1 - alpha) + self.current_color[0] * alpha)
                                new_g = int(old_color[1] * (1 - alpha) + self.current_color[1] * alpha)
                                new_b = int(old_color[2] * (1 - alpha) + self.current_color[2] * alpha)
                            
                            else:  # acryl
                                # Acryl: Deckend, wenig Mischung
                                alpha = (effective_opacity / 255.0) * flow
                                new_r = int(old_color[0] * (1 - alpha) + self.current_color[0] * alpha)
                                new_g = int(old_color[1] * (1 - alpha) + self.current_color[1] * alpha)
                                new_b = int(old_color[2] * (1 - alpha) + self.current_color[2] * alpha)
                            
                            self.texture_image.putpixel((px, py), (new_r, new_g, new_b, 255))
                        except:
                            pass
    
    def draw_spray(self, x, y):
        """Spray Can Tool - sprüht Partikel"""
        import random
        
        # Tablet-Druck berücksichtigt Dichte
        pressure = self.tablet_pressure if self.use_pressure else 1.0
        num_particles = int(self.spray_density * pressure)
        
        # Spray-Radius
        spray_radius = self.brush_size * 2
        
        for _ in range(num_particles):
            # Zufällige Position im Spray-Radius
            angle = random.random() * 2 * 3.14159
            distance = random.random() * spray_radius * self.spray_randomness
            
            px = int(x + distance * math.cos(angle))
            py = int(y + distance * math.sin(angle))
            
            if 0 <= px < self.canvas_size and 0 <= py < self.canvas_size:
                # Einzelnes Partikel mit leichter Transparenz
                try:
                    old_color = self.texture_image.getpixel((px, py))
                    if len(old_color) == 3:
                        old_color = old_color + (255,)
                    
                    # Spray ist immer leicht transparent
                    alpha = 0.1 * (self.brush_opacity / 255.0)
                    new_r = int(old_color[0] * (1 - alpha) + self.current_color[0] * alpha)
                    new_g = int(old_color[1] * (1 - alpha) + self.current_color[1] * alpha)
                    new_b = int(old_color[2] * (1 - alpha) + self.current_color[2] * alpha)
                    
                    self.texture_image.putpixel((px, py), (new_r, new_g, new_b, 255))
                except:
                    pass
    
    def draw_eraser(self, x, y):
        """Radiert (setzt auf Weiß)"""
        draw = ImageDraw.Draw(self.texture_image)
        
        # Kreis radieren
        for i in range(-self.brush_size, self.brush_size + 1):
            for j in range(-self.brush_size, self.brush_size + 1):
                if i*i + j*j <= self.brush_size*self.brush_size:
                    px, py = x + i, y + j
                    if 0 <= px < self.canvas_size and 0 <= py < self.canvas_size:
                        self.texture_image.putpixel((px, py), (255, 255, 255, 255))
    
    def apply_blur(self, x, y):
        """Verwischt Bereich (Blur-Tool)"""
        # Kleine Region extrahieren
        radius = self.brush_size
        x1 = max(0, x - radius)
        y1 = max(0, y - radius)
        x2 = min(self.canvas_size, x + radius)
        y2 = min(self.canvas_size, y + radius)
        
        if x2 <= x1 or y2 <= y1:
            return
        
        # Region extrahieren, blurren, zurückschreiben
        region = self.texture_image.crop((x1, y1, x2, y2))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=1))
        self.texture_image.paste(blurred, (x1, y1))
    
    def flood_fill(self, x, y):
        """Füllwerkzeug (Flood Fill) - MIT TOLERANZ für ähnliche Farben"""
        if not (0 <= x < self.canvas_size and 0 <= y < self.canvas_size):
            return
        
        # Farbe an dieser Position
        target_color = self.texture_image.getpixel((x, y))
        target_rgb = target_color[:3] if len(target_color) == 4 else target_color
        
        if target_rgb == self.current_color:
            return  # Gleiche Farbe
        
        # Toleranz holen
        tolerance = self.fill_tolerance_var.get() if hasattr(self, 'fill_tolerance_var') else 30
        
        # Flood-Fill Algorithmus mit Toleranz
        self._flood_fill_iterative_tolerance(x, y, target_rgb, tolerance)
        
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
    
    def color_distance(self, c1, c2):
        """Berechnet Farbdistanz (Euklidische Distanz im RGB-Raum)"""
        return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2 + (c1[2] - c2[2])**2)
    
    def _flood_fill_iterative_tolerance(self, start_x, start_y, target_color, tolerance):
        """Stack-basierter Flood-Fill mit Toleranz"""
        stack = [(start_x, start_y)]
        visited = set()
        
        # Maximale erlaubte Distanz
        max_distance = tolerance * 4.41  # 255*sqrt(3) = 441, normalisiert auf 0-100
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
            
            if not (0 <= x < self.canvas_size and 0 <= y < self.canvas_size):
                continue
            
            # Aktuelle Farbe prüfen
            try:
                current_pixel = self.texture_image.getpixel((x, y))
                current_rgb = current_pixel[:3] if len(current_pixel) == 4 else current_pixel
            except:
                continue
            
            # Prüfe ob Farbe innerhalb Toleranz
            if self.color_distance(current_rgb, target_color) > max_distance:
                continue
            
            # Pixel füllen
            self.texture_image.putpixel((x, y), self.current_color + (255,))
            visited.add((x, y))
            
            # Nachbarn hinzufügen
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))
    
    def pick_color(self, event):
        """Farbpipette - Farbe von Position aufnehmen"""
        x, y = event.x, event.y
        
        if 0 <= x < self.canvas_size and 0 <= y < self.canvas_size:
            try:
                pixel = self.texture_image.getpixel((x, y))
                color = pixel[:3] if len(pixel) == 4 else pixel
                self.current_color = color
                self.color_display.config(bg=self.rgb_to_hex(color))
                
                # Zurück zum Pinsel wechseln
                self.select_tool("brush")
            except:
                pass
            if self.tool == "eyedropper":
                self.select_tool("brush")
    
    def finish_shape(self, x2, y2):
        """Beendet eine Form (Linie, Rechteck, Kreis)"""
        if not self.shape_start_pos:
            return
        
        x1, y1 = self.shape_start_pos
        draw = ImageDraw.Draw(self.texture_image)
        
        if self.tool == "line":
            # Gerade Linie zeichnen
            draw.line([(x1, y1), (x2, y2)], 
                     fill=self.current_color, 
                     width=self.shape_outline_width)
        
        elif self.tool == "rectangle":
            # Rechteck
            if self.shape_fill:
                draw.rectangle([(x1, y1), (x2, y2)], 
                              fill=self.current_color)
            else:
                draw.rectangle([(x1, y1), (x2, y2)], 
                              outline=self.current_color, 
                              width=self.shape_outline_width)
        
        elif self.tool == "circle":
            # Kreis (Ellipse)
            if self.shape_fill:
                draw.ellipse([(x1, y1), (x2, y2)], 
                            fill=self.current_color)
            else:
                draw.ellipse([(x1, y1), (x2, y2)], 
                            outline=self.current_color, 
                            width=self.shape_outline_width)
        
        self.shape_start_pos = None
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
    
    def draw_shape_preview(self, x2, y2):
        """Zeichnet Vorschau der Form während Drag"""
        if not self.shape_start_pos:
            return
        
        x1, y1 = self.shape_start_pos
        
        # Temporäre Linie auf Canvas (als Canvas-Element, nicht auf Image)
        self.canvas.delete("preview")
        
        if self.tool == "line":
            self.canvas.create_line(x1, y1, x2, y2, 
                                   fill=self.rgb_to_hex(self.current_color),
                                   width=self.shape_outline_width,
                                   tags="preview")
        elif self.tool == "rectangle":
            if self.shape_fill:
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                            fill=self.rgb_to_hex(self.current_color),
                                            tags="preview")
            else:
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                            outline=self.rgb_to_hex(self.current_color),
                                            width=self.shape_outline_width,
                                            tags="preview")
        elif self.tool == "circle":
            if self.shape_fill:
                self.canvas.create_oval(x1, y1, x2, y2,
                                       fill=self.rgb_to_hex(self.current_color),
                                       tags="preview")
            else:
                self.canvas.create_oval(x1, y1, x2, y2,
                                       outline=self.rgb_to_hex(self.current_color),
                                       width=self.shape_outline_width,
                                       tags="preview")
    
    def draw_bezier_curve(self):
        """Zeichnet Bezier-Kurve mit 4 Kontrollpunkten"""
        if len(self.curve_points) < 4:
            return
        
        draw = ImageDraw.Draw(self.texture_image)
        p0, p1, p2, p3 = self.curve_points[:4]
        
        # Bezier-Kurve berechnen
        points = []
        steps = 50
        for i in range(steps + 1):
            t = i / steps
            # Kubische Bezier-Formel
            x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
            y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
            points.append((int(x), int(y)))
        
        # Kurve zeichnen
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], 
                     fill=self.current_color, 
                     width=self.shape_outline_width)
        
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
    
    def draw_selection_preview(self, x2, y2):
        """Zeichnet Selektions-Rechteck Vorschau"""
        if not self.shape_start_pos:
            return
        
        x1, y1 = self.shape_start_pos
        self.canvas.delete("selection_preview")
        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     outline="blue",
                                     width=2,
                                     dash=(5, 5),
                                     tags="selection_preview")
    
    def extract_selection(self):
        """Extrahiert ausgewählten Bereich als separates Image"""
        if not self.selection_rect:
            return
        
        x1, y1, x2, y2 = self.selection_rect
        self.selected_image = self.texture_image.crop((x1, y1, x2, y2))
    
    def move_selection(self, dx, dy):
        """Bewegt die aktuelle Selektion"""
        if not self.selection_rect or not self.selected_image:
            return
        
        x1, y1, x2, y2 = self.selection_rect
        
        # Lösche alten Bereich (mit Weiß)
        draw = ImageDraw.Draw(self.texture_image)
        draw.rectangle([(x1, y1), (x2, y2)], fill=(255, 255, 255))
        
        # Neue Position
        new_x1 = x1 + dx
        new_y1 = y1 + dy
        new_x2 = x2 + dx
        new_y2 = y2 + dy
        
        # Paste an neuer Position
        self.texture_image.paste(self.selected_image, (new_x1, new_y1))
        
        # Update selection rect
        self.selection_rect = (new_x1, new_y1, new_x2, new_y2)
        
        self.update_canvas()
    
    def toggle_transform_mode(self):
        """Wechselt Transform-Modus für Selektion"""
        if not self.selection_rect or not self.selected_image:
            messagebox.showinfo("Keine Selektion", "Bitte wählen Sie zuerst einen Bereich aus!")
            return
        
        # Dialog für Transform-Optionen
        transform_dialog = tk.Toplevel(self)
        transform_dialog.title("Transform")
        transform_dialog.geometry("300x200")
        transform_dialog.configure(bg="#2a2a2a")
        
        tk.Label(transform_dialog, text="Transform Selektion", 
                bg="#2a2a2a", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Scale
        scale_frame = tk.Frame(transform_dialog, bg="#2a2a2a")
        scale_frame.pack(pady=10, padx=20, fill=tk.X)
        
        tk.Label(scale_frame, text="Skalierung (%):", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        scale_var = tk.IntVar(value=100)
        scale_entry = tk.Entry(scale_frame, textvariable=scale_var, width=8)
        scale_entry.pack(side=tk.LEFT, padx=10)
        
        # Rotate
        rotate_frame = tk.Frame(transform_dialog, bg="#2a2a2a")
        rotate_frame.pack(pady=10, padx=20, fill=tk.X)
        
        tk.Label(rotate_frame, text="Rotation (°):", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        rotate_var = tk.IntVar(value=0)
        rotate_entry = tk.Entry(rotate_frame, textvariable=rotate_var, width=8)
        rotate_entry.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        btn_frame = tk.Frame(transform_dialog, bg="#2a2a2a")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Anwenden", bg="#2a7d2a", fg="white",
                 command=lambda: self.apply_transform(scale_var.get(), rotate_var.get(), transform_dialog)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Abbrechen", bg="#7d2a2a", fg="white",
                 command=transform_dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def apply_transform(self, scale_percent, rotate_degrees, dialog):
        """Wendet Transform auf Selektion an"""
        if not self.selected_image:
            return
        
        transformed = self.selected_image.copy()
        
        # Skalieren
        if scale_percent != 100:
            new_width = int(transformed.width * scale_percent / 100)
            new_height = int(transformed.height * scale_percent / 100)
            transformed = transformed.resize((new_width, new_height), Image.LANCZOS)
        
        # Rotieren
        if rotate_degrees != 0:
            transformed = transformed.rotate(rotate_degrees, expand=True, fillcolor=(255, 255, 255))
        
        # An Selektion zurückschreiben
        x1, y1, x2, y2 = self.selection_rect
        
        # Lösche alten Bereich
        draw = ImageDraw.Draw(self.texture_image)
        draw.rectangle([(x1, y1), (x2, y2)], fill=(255, 255, 255))
        
        # Paste transformiertes Bild
        self.texture_image.paste(transformed, (x1, y1))
        self.selected_image = transformed
        
        # Update Selektion Größe
        self.selection_rect = (x1, y1, x1 + transformed.width, y1 + transformed.height)
        
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
        
        dialog.destroy()
    
    def cancel_selection(self):
        """Bricht Selektion ab"""
        self.selection_rect = None
        self.selected_image = None
        self.update_canvas()
    
    def delete_selection(self):
        """Löscht den selektierten Bereich"""
        if not self.selection_rect:
            return
        
        x1, y1, x2, y2 = self.selection_rect
        draw = ImageDraw.Draw(self.texture_image)
        draw.rectangle([(x1, y1), (x2, y2)], fill=(255, 255, 255))
        
        self.selection_rect = None
        self.selected_image = None
        
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
    
    def copy_selection(self):
        """Kopiert Selektion in Zwischenablage (intern)"""
        if self.selected_image:
            self.clipboard_image = self.selected_image.copy()
            messagebox.showinfo("Kopiert", "Selektion wurde kopiert!")
    
    def cut_selection(self):
        """Schneidet Selektion aus"""
        if not self.selection_rect:
            return
        
        self.copy_selection()
        self.delete_selection()
    
    def paste_selection(self):
        """Fügt Zwischenablage ein"""
        if not hasattr(self, 'clipboard_image') or self.clipboard_image is None:
            messagebox.showwarning("Keine Daten", "Zwischenablage ist leer!")
            return
        
        # Füge in Mitte des Canvas ein
        paste_x = (self.canvas_size - self.clipboard_image.width) // 2
        paste_y = (self.canvas_size - self.clipboard_image.height) // 2
        
        self.texture_image.paste(self.clipboard_image, (paste_x, paste_y))
        
        # Neue Selektion erstellen
        self.selection_rect = (paste_x, paste_y, 
                              paste_x + self.clipboard_image.width, 
                              paste_y + self.clipboard_image.height)
        self.selected_image = self.clipboard_image.copy()
        
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
    
    def clear_canvas(self):
        """Canvas löschen"""
        if messagebox.askyesno("Löschen", "Möchten Sie die gesamte Zeichnung löschen?"):
            self.texture_image = Image.new('RGB', (self.canvas_size, self.canvas_size), (255, 255, 255))
            self.texture_draw = ImageDraw.Draw(self.texture_image)
            self.save_to_history()
            self.update_canvas()
            self.update_preview()
    
    def save_to_history(self):
        """Speichert aktuellen Zustand in History"""
        # Entferne alles nach aktuellem Index
        self.history = self.history[:self.history_index + 1]
        
        # Füge neuen Zustand hinzu
        self.history.append(self.texture_image.copy())
        
        # Begrenze History
        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.history_index += 1
    
    def undo(self):
        """Rückgängig"""
        if self.history_index > 0:
            self.history_index -= 1
            self.texture_image = self.history[self.history_index].copy()
            self.texture_draw = ImageDraw.Draw(self.texture_image)
            self.update_canvas()
            self.update_preview()
    
    def redo(self):
        """Wiederholen"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.texture_image = self.history[self.history_index].copy()
            self.texture_draw = ImageDraw.Draw(self.texture_image)
            self.update_canvas()
            self.update_preview()
    
    def update_canvas(self, clear_preview=True):
        """Aktualisiert die Canvas-Anzeige"""
        # Photo für Tkinter
        self.photo = ImageTk.PhotoImage(self.texture_image)
        if clear_preview:
            self.canvas.delete("all")
        else:
            # Nur Image updaten, Preview-Elemente behalten
            self.canvas.delete("image")
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW, tags="image")
        
        # Selektion anzeigen wenn vorhanden
        if self.selection_rect:
            x1, y1, x2, y2 = self.selection_rect
            self.canvas.create_rectangle(x1, y1, x2, y2,
                                        outline="blue",
                                        width=2,
                                        dash=(5, 5),
                                        tags="selection")
        
        # Kurven-Kontrollpunkte anzeigen
        if self.curve_points and self.tool == "curve":
            for i, (px, py) in enumerate(self.curve_points):
                self.canvas.create_oval(px-3, py-3, px+3, py+3,
                                       fill="red",
                                       outline="white",
                                       tags="curve_point")
                self.canvas.create_text(px, py-10,
                                       text=f"P{i+1}",
                                       fill="white",
                                       tags="curve_point")
    
    def update_preview(self):
        """Aktualisiert die Vorschau"""
        # Skaliere auf 64x64
        preview_img = self.texture_image.resize((64, 64), Image.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview_img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, image=self.preview_photo, anchor=tk.NW)
    
    def import_image(self):
        """Importiert ein Bild"""
        filename = filedialog.askopenfilename(
            title="Bild importieren",
            filetypes=[
                ("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("Alle Dateien", "*.*")
            ]
        )
        
        if filename:
            try:
                img = Image.open(filename).convert('RGB')
                img = img.resize((self.canvas_size, self.canvas_size), Image.LANCZOS)
                
                self.texture_image = img
                self.texture_draw = ImageDraw.Draw(self.texture_image)
                
                self.save_to_history()
                self.update_canvas()
                self.update_preview()
                
                messagebox.showinfo("Erfolg", "Bild erfolgreich importiert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Importieren:\n{e}")
    
    def export_image(self):
        """Exportiert das Bild"""
        filename = filedialog.asksaveasfilename(
            title="Textur exportieren",
            defaultextension=".png",
            filetypes=[
                ("PNG Dateien", "*.png"),
                ("JPEG Dateien", "*.jpg"),
                ("Alle Dateien", "*.*")
            ]
        )
        
        if filename:
            try:
                # In höherer Auflösung speichern (256x256)
                export_img = self.texture_image.resize((256, 256), Image.LANCZOS)
                export_img.save(filename)
                messagebox.showinfo("Erfolg", f"Textur exportiert:\n{filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Exportieren:\n{e}")
    
    def update_frame_label(self):
        """Aktualisiert das Frame-Label"""
        total = len(self.frames)
        current = self.current_frame_index + 1
        self.frame_label.config(text=f"Frame {current} / {total}")
    
    def save_current_frame(self):
        """Speichert den aktuellen Canvas-Inhalt in die Frame-Liste"""
        self.frames[self.current_frame_index] = self.texture_image.copy()
    
    def load_frame(self, index):
        """Lädt einen Frame zum Bearbeiten"""
        if 0 <= index < len(self.frames):
            self.current_frame_index = index
            self.texture_image = self.frames[index].copy()
            self.texture_draw = ImageDraw.Draw(self.texture_image)
            
            # Undo-History für diesen Frame zurücksetzen
            self.history = [self.texture_image.copy()]
            self.history_index = 0
            
            self.update_canvas()
            self.update_preview()
            self.update_frame_label()
    
    def previous_frame(self):
        """Geht zum vorherigen Frame"""
        self.save_current_frame()
        new_index = (self.current_frame_index - 1) % len(self.frames)
        self.load_frame(new_index)
    
    def next_frame(self):
        """Geht zum nächsten Frame"""
        self.save_current_frame()
        new_index = (self.current_frame_index + 1) % len(self.frames)
        self.load_frame(new_index)
    
    def add_new_frame(self):
        """Fügt einen neuen leeren Frame hinzu"""
        self.save_current_frame()
        
        # Neuer leerer Frame mit aktueller Hintergrundfarbe
        new_frame = Image.new('RGB', (self.canvas_size, self.canvas_size), (200, 200, 200))
        self.frames.insert(self.current_frame_index + 1, new_frame)
        
        # Zum neuen Frame wechseln
        self.load_frame(self.current_frame_index + 1)
        
        # Material automatisch als animiert markieren
        if len(self.frames) > 1:
            self.is_animated_var.set(True)
    
    def duplicate_frame(self):
        """Kopiert den aktuellen Frame"""
        self.save_current_frame()
        
        # Frame duplizieren
        duplicated_frame = self.texture_image.copy()
        self.frames.insert(self.current_frame_index + 1, duplicated_frame)
        
        # Zum duplizierten Frame wechseln
        self.load_frame(self.current_frame_index + 1)
        
        # Material automatisch als animiert markieren
        if len(self.frames) > 1:
            self.is_animated_var.set(True)
    
    def delete_frame(self):
        """Löscht den aktuellen Frame"""
        if len(self.frames) <= 1:
            messagebox.showwarning("Warnung", "Der letzte Frame kann nicht gelöscht werden!")
            return
        
        response = messagebox.askyesno("Frame löschen", 
                                      f"Frame {self.current_frame_index + 1} wirklich löschen?")
        if response:
            del self.frames[self.current_frame_index]
            
            # Zum vorherigen Frame wechseln (oder ersten)
            new_index = min(self.current_frame_index, len(self.frames) - 1)
            self.load_frame(new_index)
            
            # Wenn nur noch 1 Frame übrig, Animation deaktivieren
            if len(self.frames) == 1:
                self.is_animated_var.set(False)
    
    def save_texture(self):
        """Speichert die Textur im Renderer"""
        name = self.name_entry.get().strip()
        
        if not name:
            messagebox.showerror("Fehler", "Bitte geben Sie einen Namen ein!")
            return
        
        # Aktuellen Frame vor dem Speichern sichern
        self.save_current_frame()
        
        # Material-ID erstellen (falls neu)
        if self.is_new_material:
            material_id = name.lower().replace(" ", "_").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
            # Sicherstellen dass ID einzigartig ist
            base_id = material_id
            counter = 1
            while material_id in self.renderer.get_all_materials():
                material_id = f"{base_id}_{counter}"
                counter += 1
            
            self.material_id = material_id
        
        # Textur-Verzeichnis erstellen
        texture_dir = "textures"
        os.makedirs(texture_dir, exist_ok=True)
        
        is_animated = self.is_animated_var.get() and len(self.frames) > 1
        
        if is_animated:
            # ANIMIERT: Alle Frames speichern
            for frame_idx, frame in enumerate(self.frames):
                frame_path = os.path.join(texture_dir, f"{self.material_id}_frame_{frame_idx}.png")
                save_img = frame.resize((256, 256), Image.LANCZOS)
                save_img.save(frame_path, "PNG")
            
            # Ersten Frame auch als Standard speichern
            texture_path = os.path.join(texture_dir, f"{self.material_id}.png")
            save_img = self.frames[0].resize((256, 256), Image.LANCZOS)
            save_img.save(texture_path, "PNG")
        else:
            # STATISCH: Nur ersten Frame speichern
            texture_path = os.path.join(texture_dir, f"{self.material_id}.png")
            save_img = self.frames[0].resize((256, 256), Image.LANCZOS)
            save_img.save(texture_path, "PNG")
        
        # Im Renderer registrieren
        if self.renderer:
            emoji = self.emoji_entry.get().strip() or "🎨"
            
            # Durchschnittsfarbe vom ersten Frame berechnen
            avg_color = self.calculate_average_color()
            
            self.renderer.create_new_material(
                self.material_id,
                name,
                color=avg_color,
                animated=is_animated,
                emoji=emoji
            )
            
            # Textur importieren
            self.renderer.import_texture(self.material_id, texture_path)
        
        # Callback aufrufen
        if self.on_save_callback:
            self.on_save_callback(self.material_id)
        
        messagebox.showinfo("Erfolg", f"Material '{name}' wurde gespeichert!")
        self.destroy()
    
    def show_help(self):
        """Zeigt Hilfe-Dialog mit allen Shortcuts"""
        help_window = tk.Toplevel(self)
        help_window.title("Tastaturkürzel & Hilfe")
        help_window.geometry("600x700")
        help_window.configure(bg="#2a2a2a")
        
        # Scrollbarer Text
        text_frame = tk.Frame(help_window, bg="#2a2a2a")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        help_text = tk.Text(text_frame, bg="#1a1a1a", fg="white",
                           font=("Courier", 10), wrap=tk.WORD,
                           yscrollcommand=scrollbar.set)
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=help_text.yview)
        
        help_content = """
╔══════════════════════════════════════════════════════╗
║     PROFESSIONELLER TEXTURE EDITOR - HILFE          ║
╚══════════════════════════════════════════════════════╝

🎨 WERKZEUGE (Shortcuts):
  B  - Pinsel          E  - Radierer
  K/I- Pipette         F/G- Füller
  S  - Spray Can       L  - Linie
  U  - Kurve           R  - Rechteck
  C  - Kreis           V  - Auswahl
  M  - Bewegen

📐 PINSEL & EINSTELLUNGEN:
  [  - Pinsel kleiner  ]  - Pinsel größer
  <  - Deckkraft -     >  - Deckkraft +

🎨 MAL-MODI:
  • Acryl: Deckend, präzise
  • Öl: Mischbar, dickflüssig
  • Wasserfarbe: Transparent, fließend

✏️ ZEICHNEN:
  • Pinsel: Drucksensitiv (Tablet)
  • Spray: Organische Partikel-Streuung
  • Kurve: 4 Punkte für Bezier-Kurve

🖊️ GRAFIKTABLETT:
  Automatische Druckerkennung
  Beeinflusst Größe & Deckkraft

🔲 SELEKTION & TRANSFORM:
  V      - Selektion erstellen
  M      - Selektion bewegen
  T      - Transform (Scale/Rotate)
  Del    - Selektion löschen
  Esc    - Selektion abbrechen
  Ctrl+C - Kopieren
  Ctrl+X - Ausschneiden
  Ctrl+V - Einfügen

⏪ UNDO/REDO:
  Ctrl+Z - Rückgängig
  Ctrl+Y - Wiederholen

💾 SPEICHERN:
  Speichert als PNG (256x256)
  Unterstützt Animation (Multi-Frame)

🎬 ANIMATION:
  ◄► - Frame Navigation
  ➕  - Neuer Frame
  📋  - Frame duplizieren

❓ TIPPS:
  • Rechtsklick = Schnell-Pipette
  • Füll-Toleranz: Ähnliche Farben
  • Mal-Modi für realistische Effekte
  • Tablet-Druck für natürliches Zeichnen
        """
        
        help_text.insert('1.0', help_content)
        help_text.config(state=tk.DISABLED)
        
        tk.Button(help_window, text="Schließen", bg="#2a5d8d", fg="white",
                 font=("Arial", 10), padx=20, pady=5,
                 command=help_window.destroy).pack(pady=10)
    
    def update_status(self, message):
        """Aktualisiert Statusleiste"""
        if hasattr(self, 'status_label'):
            tool_names = {
                "brush": "Pinsel", "pencil": "Bleistift", "eraser": "Radierer",
                "blur": "Verwischen", "fill": "Füller", "eyedropper": "Pipette",
                "spray": "Spray", "line": "Linie", "curve": "Kurve",
                "rectangle": "Rechteck", "circle": "Kreis",
                "select": "Auswahl", "move": "Bewegen"
            }
            tool_name = tool_names.get(self.tool, self.tool)
            self.status_label.config(text=f"{message} | Werkzeug: {tool_name} | Drücke H für Hilfe")
    
    def calculate_average_color(self):
        """Berechnet die Durchschnittsfarbe des Bildes"""
        # Verkleinern für schnellere Berechnung
        small = self.texture_image.resize((32, 32), Image.LANCZOS)
        pixels = list(small.getdata())
        
        r_total = sum(p[0] for p in pixels)
        g_total = sum(p[1] for p in pixels)
        b_total = sum(p[2] for p in pixels)
        
        count = len(pixels)
        
        return (
            r_total // count,
            g_total // count,
            b_total // count
        )
