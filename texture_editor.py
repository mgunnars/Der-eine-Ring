"""
Texture Editor für "Der Eine Ring"
Ermöglicht das Erstellen und Bearbeiten eigener Texturen mit erweiterten Tools
"""
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
from PIL import Image, ImageDraw, ImageTk, ImageFilter
import os


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
        
        # ERWEITERTE TOOLS
        self.tool = "brush"  # brush, pencil, eraser, fill, eyedropper, blur (verwischen)
        self.brush_size = 3  # 1-20 für brush/blur
        self.brush_opacity = 255  # 0-255
        
        # Undo/Redo (pro Frame)
        self.history = [self.texture_image.copy()]
        self.history_index = 0
        self.max_history = 50
        
        self.setup_ui()
    
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
        """Werkzeug-Panel erstellen - ERWEITERT"""
        tk.Label(parent, text="🛠️ Werkzeuge", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Werkzeuge - MIT BLUR/VERWISCHEN UND BLEISTIFT
        tools = [
            ("🖌️ Pinsel", "brush"),
            ("✏️ Bleistift", "pencil"),
            ("🧹 Radierer", "eraser"),
            ("🌫️ Verwischen", "blur"),
            ("💧 Füller", "fill"),
            ("💉 Pipette", "eyedropper")
        ]
        
        self.tool_buttons = {}
        for text, tool in tools:
            btn = tk.Button(parent, text=text, bg="#3a3a3a", fg="white",
                          font=("Arial", 9), width=12, pady=5,
                          command=lambda t=tool: self.select_tool(t))
            btn.pack(pady=2, padx=5)
            self.tool_buttons[tool] = btn
        
        self.select_tool("brush")
        
        # Separator
        tk.Frame(parent, bg="#555555", height=2).pack(fill=tk.X, pady=10, padx=10)
        
        # Pinselgröße
        tk.Label(parent, text="Pinselgröße", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.brush_size_var = tk.IntVar(value=3)
        brush_scale = tk.Scale(parent, from_=1, to=20, orient=tk.HORIZONTAL,
                              variable=self.brush_size_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0,
                              command=self.update_brush_size)
        brush_scale.pack(fill=tk.X, padx=10)
        
        # Deckkraft/Opacity
        tk.Label(parent, text="Deckkraft", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(5, 2))
        
        self.opacity_var = tk.IntVar(value=255)
        opacity_scale = tk.Scale(parent, from_=10, to=255, orient=tk.HORIZONTAL,
                              variable=self.opacity_var,
                              bg="#3a3a3a", fg="white", 
                              highlightthickness=0,
                              command=self.update_opacity)
        opacity_scale.pack(fill=tk.X, padx=10)
        
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
        
        # Cursor ändern
        cursors = {
            "brush": "crosshair",
            "pencil": "pencil",
            "eraser": "circle",
            "blur": "crosshair",
            "fill": "spraycan",
            "eyedropper": "target"
        }
        self.canvas.config(cursor=cursors.get(tool, "crosshair"))
    
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
        """Klick auf Canvas"""
        if self.tool == "fill":
            self.flood_fill(event.x, event.y)
        elif self.tool == "eyedropper":
            self.pick_color(event)
        else:
            self.is_drawing = True
            self.last_x = event.x
            self.last_y = event.y
            self.draw_at(event.x, event.y)
    
    def on_canvas_drag(self, event):
        """Ziehen auf Canvas"""
        if self.is_drawing and self.tool in ["brush", "pencil", "eraser", "blur"]:
            # Linie von letzter Position zur aktuellen zeichnen (smooth)
            if self.last_x is not None and self.last_y is not None:
                self.draw_line(self.last_x, self.last_y, event.x, event.y)
            else:
                self.draw_at(event.x, event.y)
            
            self.last_x = event.x
            self.last_y = event.y
            
            # Canvas während Drag updaten (für Live-Feedback)
            self.update_canvas()
    
    def on_canvas_release(self, event):
        """Maus losgelassen"""
        if self.is_drawing:
            self.is_drawing = False
            self.last_x = None
            self.last_y = None
            
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
        """Zeichnet an Position x, y mit dem aktuellen Werkzeug"""
        if self.tool == "brush":
            self.draw_brush(x, y)
        elif self.tool == "pencil":
            self.draw_pencil(x, y)
        elif self.tool == "eraser":
            self.draw_eraser(x, y)
        elif self.tool == "blur":
            self.apply_blur(x, y)
        
        # Update nur noch wenn nicht am Zeichnen (Performance)
        # Beim Drag wird nur am Ende updated
    
    def draw_pencil(self, x, y):
        """Bleistift - präzises 1-Pixel-Zeichnen"""
        if 0 <= x < self.canvas_size and 0 <= y < self.canvas_size:
            # Exakt 1 Pixel setzen
            self.texture_image.putpixel((x, y), self.current_color + (255,))
    
    def draw_brush(self, x, y):
        """Zeichnet mit Pinsel"""
        draw = ImageDraw.Draw(self.texture_image, 'RGBA')
        
        # Kreis mit Deckkraft zeichnen
        for i in range(-self.brush_size, self.brush_size + 1):
            for j in range(-self.brush_size, self.brush_size + 1):
                if i*i + j*j <= self.brush_size*self.brush_size:
                    px, py = x + i, y + j
                    if 0 <= px < self.canvas_size and 0 <= py < self.canvas_size:
                        # Aktuelle Pixel-Farbe holen
                        try:
                            old_color = self.texture_image.getpixel((px, py))
                            if len(old_color) == 3:
                                old_color = old_color + (255,)
                            
                            # Alpha-Blending
                            alpha = self.brush_opacity / 255.0
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
        """Füllwerkzeug (Flood Fill) - MODERNISIERT"""
        if not (0 <= x < self.canvas_size and 0 <= y < self.canvas_size):
            return
        
        # Farbe an dieser Position
        target_color = self.texture_image.getpixel((x, y))
        target_rgb = target_color[:3] if len(target_color) == 4 else target_color
        
        if target_rgb == self.current_color:
            return  # Gleiche Farbe
        
        # Flood-Fill Algorithmus
        self._flood_fill_iterative(x, y, target_rgb)
        
        self.save_to_history()
        self.update_canvas()
        self.update_preview()
    
    def _flood_fill_iterative(self, start_x, start_y, target_color):
        """Stack-basierter Flood-Fill (effizienter als rekursiv)"""
        stack = [(start_x, start_y)]
        visited = set()
        
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
            
            if current_rgb != target_color:
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
    
    def update_canvas(self):
        """Aktualisiert die Canvas-Anzeige"""
        # Photo für Tkinter
        self.photo = ImageTk.PhotoImage(self.texture_image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
    
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
