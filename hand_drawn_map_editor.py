"""
Hand-Drawn Map Editor für "Der Eine Ring"
Zeichne Karten im Vintage/Tolkien-Stil oder importiere Bilder
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from PIL import Image, ImageDraw, ImageTk, ImageFilter, ImageEnhance
import os
import math

class HandDrawnMapEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("🎨 MapDraw - Hand-Drawn Map Editor")
        self.geometry("1400x900")
        self.configure(bg="#2a2a2a")
        
        # Canvas Einstellungen
        self.canvas_width = 2048
        self.canvas_height = 2048
        self.view_width = 1024
        self.view_height = 768
        
        # Zeichnungs-Daten
        self.image = Image.new('RGBA', (self.canvas_width, self.canvas_height), (240, 230, 210, 255))
        self.draw = ImageDraw.Draw(self.image)
        
        # Tool-Einstellungen
        self.current_tool = "brush"
        self.brush_size = 5
        self.current_color = (60, 40, 20)  # Dunkelbraun
        self.last_x = None
        self.last_y = None
        
        # Undo/Redo
        self.history = [self.image.copy()]
        self.history_index = 0
        self.max_history = 20
        
        # Zoom & Pan
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.setup_ui()
        self.update_canvas()
        
    def setup_ui(self):
        """Erstelle die Benutzeroberfläche"""
        
        # =================== TOP TOOLBAR ===================
        top_frame = tk.Frame(self, bg="#1a1a1a", height=60)
        top_frame.pack(side=tk.TOP, fill=tk.X)
        top_frame.pack_propagate(False)
        
        # File Operations
        file_frame = tk.LabelFrame(top_frame, text="📁 Datei", bg="#1a1a1a", fg="white", font=("Arial", 9))
        file_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)
        
        tk.Button(file_frame, text="📂 Laden", bg="#2a5d8d", fg="white",
                 command=self.load_image).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="💾 Speichern", bg="#2a7d2a", fg="white",
                 command=self.save_image).pack(side=tk.LEFT, padx=2)
        tk.Button(file_frame, text="🆕 Neu", bg="#5d2a8d", fg="white",
                 command=self.new_image).pack(side=tk.LEFT, padx=2)
        
        # Edit Operations
        edit_frame = tk.LabelFrame(top_frame, text="✏️ Bearbeiten", bg="#1a1a1a", fg="white", font=("Arial", 9))
        edit_frame.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.Y)
        
        tk.Button(edit_frame, text="↶ Undo", bg="#5d5d5d", fg="white",
                 command=self.undo).pack(side=tk.LEFT, padx=2)
        tk.Button(edit_frame, text="↷ Redo", bg="#5d5d5d", fg="white",
                 command=self.redo).pack(side=tk.LEFT, padx=2)
        tk.Button(edit_frame, text="🗑️ Löschen", bg="#7d2a2a", fg="white",
                 command=self.clear_canvas).pack(side=tk.LEFT, padx=2)
        
        # =================== LEFT TOOLBAR - TOOLS ===================
        left_frame = tk.Frame(self, bg="#1a1a1a", width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        tk.Label(left_frame, text="🛠️ Werkzeuge", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Tool Buttons
        tools = [
            ("🖌️ Pinsel", "brush", "#2a5d8d"),
            ("✏️ Stift", "pen", "#2a7d8d"),
            ("🧽 Radierer", "eraser", "#7d5d2a"),
            ("📏 Linie", "line", "#5d2a8d"),
            ("▭ Rechteck", "rect", "#8d2a5d"),
            ("⭕ Kreis", "circle", "#2a8d5d"),
            ("🪣 Füllen", "fill", "#8d5d2a"),
            ("💧 Pipette", "eyedropper", "#2a8d8d"),
        ]
        
        for name, tool, color in tools:
            btn = tk.Button(left_frame, text=name, bg=color, fg="white",
                          font=("Arial", 10), width=18,
                          command=lambda t=tool: self.select_tool(t))
            btn.pack(pady=3, padx=10)
            if tool == self.current_tool:
                btn.configure(relief=tk.SUNKEN, bg="#5d8d2a")
        
        # Pinselgröße
        tk.Label(left_frame, text="📏 Pinselgröße", bg="#1a1a1a", fg="white",
                font=("Arial", 10)).pack(pady=(20, 5))
        
        self.size_label = tk.Label(left_frame, text=f"{self.brush_size}px", 
                                   bg="#1a1a1a", fg="white", font=("Arial", 9))
        self.size_label.pack()
        
        self.size_slider = tk.Scale(left_frame, from_=1, to=50, orient=tk.HORIZONTAL,
                                    bg="#2a2a2a", fg="white", highlightthickness=0,
                                    command=self.update_brush_size)
        self.size_slider.set(self.brush_size)
        self.size_slider.pack(pady=5, padx=10, fill=tk.X)
        
        # Farbe
        tk.Label(left_frame, text="🎨 Farbe", bg="#1a1a1a", fg="white",
                font=("Arial", 10)).pack(pady=(20, 5))
        
        self.color_display = tk.Canvas(left_frame, width=160, height=40,
                                       bg=self.rgb_to_hex(self.current_color),
                                       highlightthickness=2, highlightbackground="white")
        self.color_display.pack(pady=5)
        
        tk.Button(left_frame, text="🎨 Farbe wählen", bg="#5d2a8d", fg="white",
                 command=self.choose_color).pack(pady=5)
        
        # Vordefinierte Farben
        tk.Label(left_frame, text="Schnellfarben:", bg="#1a1a1a", fg="white",
                font=("Arial", 9)).pack(pady=(10, 5))
        
        quick_colors_frame = tk.Frame(left_frame, bg="#1a1a1a")
        quick_colors_frame.pack()
        
        quick_colors = [
            (60, 40, 20),    # Dunkelbraun
            (120, 80, 40),   # Braun
            (40, 80, 40),    # Grün
            (40, 60, 120),   # Blau
            (180, 180, 180), # Grau
            (0, 0, 0),       # Schwarz
        ]
        
        for i, color in enumerate(quick_colors):
            btn = tk.Button(quick_colors_frame, bg=self.rgb_to_hex(color),
                          width=3, height=1,
                          command=lambda c=color: self.set_color(c))
            btn.grid(row=i//3, column=i%3, padx=2, pady=2)
        
        # =================== CANVAS ===================
        canvas_frame = tk.Frame(self, bg="#2a2a2a")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, width=self.view_width, height=self.view_height,
                               bg="#3a3a3a", highlightthickness=0)
        self.canvas.pack()
        
        # Canvas Bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        
        # Info Label
        self.info_label = tk.Label(canvas_frame, text="Bereit zum Zeichnen", 
                                   bg="#2a2a2a", fg="white", font=("Arial", 9))
        self.info_label.pack(pady=5)
        
        # =================== RIGHT PANEL - FILTERS ===================
        right_frame = tk.Frame(self, bg="#1a1a1a", width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="✨ Effekte", bg="#1a1a1a", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        effects = [
            ("🎨 Aquarell", self.apply_watercolor),
            ("📜 Pergament", self.apply_parchment),
            ("✏️ Kupferstich", self.apply_engraving),
            ("🌫️ Weichzeichnen", self.apply_blur),
            ("🔆 Aufhellen", self.apply_brighten),
            ("🔅 Abdunkeln", self.apply_darken),
            ("📸 Kontrast", self.apply_contrast),
        ]
        
        for name, func in effects:
            tk.Button(right_frame, text=name, bg="#2a5d8d", fg="white",
                     font=("Arial", 9), width=18,
                     command=func).pack(pady=3, padx=10)
    
    def select_tool(self, tool):
        """Wähle ein Werkzeug"""
        self.current_tool = tool
        self.info_label.config(text=f"Werkzeug: {tool}")
        # Update button appearances (simplified)
        
    def update_brush_size(self, value):
        """Update Pinselgröße"""
        self.brush_size = int(float(value))
        self.size_label.config(text=f"{self.brush_size}px")
    
    def choose_color(self):
        """Farbe wählen"""
        color = colorchooser.askcolor(color=self.rgb_to_hex(self.current_color))
        if color[0]:
            self.current_color = tuple(int(c) for c in color[0])
            self.color_display.config(bg=self.rgb_to_hex(self.current_color))
    
    def set_color(self, color):
        """Setze Farbe direkt"""
        self.current_color = color
        self.color_display.config(bg=self.rgb_to_hex(color))
    
    def rgb_to_hex(self, rgb):
        """RGB zu Hex"""
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def canvas_to_image_coords(self, canvas_x, canvas_y):
        """Konvertiere Canvas-Koordinaten zu Bild-Koordinaten"""
        img_x = int((canvas_x - self.pan_x) / self.zoom_level)
        img_y = int((canvas_y - self.pan_y) / self.zoom_level)
        return img_x, img_y
    
    def on_mouse_down(self, event):
        """Maus gedrückt"""
        x, y = self.canvas_to_image_coords(event.x, event.y)
        
        if self.current_tool == "eyedropper":
            self.pick_color(x, y)
        elif self.current_tool == "fill":
            self.flood_fill(x, y)
        else:
            self.last_x = x
            self.last_y = y
            if self.current_tool in ["brush", "pen", "eraser"]:
                self.draw_point(x, y)
    
    def on_mouse_drag(self, event):
        """Maus gezogen"""
        x, y = self.canvas_to_image_coords(event.x, event.y)
        
        if self.current_tool in ["brush", "pen", "eraser"]:
            if self.last_x is not None:
                self.draw_line(self.last_x, self.last_y, x, y)
            self.last_x = x
            self.last_y = y
            self.update_canvas()
    
    def on_mouse_up(self, event):
        """Maus losgelassen"""
        if self.last_x is not None and self.current_tool in ["line", "rect", "circle"]:
            x, y = self.canvas_to_image_coords(event.x, event.y)
            
            if self.current_tool == "line":
                self.draw.line([self.last_x, self.last_y, x, y], 
                              fill=self.current_color, width=self.brush_size)
            elif self.current_tool == "rect":
                self.draw.rectangle([self.last_x, self.last_y, x, y],
                                   outline=self.current_color, width=self.brush_size)
            elif self.current_tool == "circle":
                self.draw.ellipse([self.last_x, self.last_y, x, y],
                                 outline=self.current_color, width=self.brush_size)
            
            self.update_canvas()
        
        self.last_x = None
        self.last_y = None
        self.save_to_history()
    
    def draw_point(self, x, y):
        """Zeichne einen Punkt"""
        if 0 <= x < self.canvas_width and 0 <= y < self.canvas_height:
            r = self.brush_size // 2
            
            if self.current_tool == "eraser":
                color = (240, 230, 210, 255)
            else:
                color = self.current_color
            
            if self.current_tool == "pen":
                self.draw.ellipse([x-r, y-r, x+r, y+r], fill=color)
            else:  # brush
                for dy in range(-r, r+1):
                    for dx in range(-r, r+1):
                        if dx*dx + dy*dy <= r*r:
                            px, py = x+dx, y+dy
                            if 0 <= px < self.canvas_width and 0 <= py < self.canvas_height:
                                self.image.putpixel((px, py), color)
    
    def draw_line(self, x1, y1, x2, y2):
        """Zeichne eine Linie"""
        dx = x2 - x1
        dy = y2 - y1
        steps = max(abs(dx), abs(dy))
        
        if steps == 0:
            self.draw_point(x1, y1)
            return
        
        for i in range(steps + 1):
            t = i / steps
            x = int(x1 + t * dx)
            y = int(y1 + t * dy)
            self.draw_point(x, y)
    
    def pick_color(self, x, y):
        """Pipette - Farbe aufnehmen"""
        if 0 <= x < self.canvas_width and 0 <= y < self.canvas_height:
            pixel = self.image.getpixel((x, y))
            self.current_color = pixel[:3]
            self.color_display.config(bg=self.rgb_to_hex(self.current_color))
            self.info_label.config(text=f"Farbe aufgenommen: {self.current_color}")
    
    def flood_fill(self, x, y):
        """Füll-Werkzeug (vereinfacht)"""
        if not (0 <= x < self.canvas_width and 0 <= y < self.canvas_height):
            return
        
        target_color = self.image.getpixel((x, y))
        if target_color[:3] == self.current_color:
            return
        
        # Einfache Flood-Fill mit ImageDraw
        ImageDraw.floodfill(self.image, (x, y), self.current_color)
        self.update_canvas()
        self.save_to_history()
    
    def update_canvas(self):
        """Aktualisiere Canvas-Anzeige"""
        # Erstelle Ansicht mit Zoom
        view = self.image.copy()
        
        if self.zoom_level != 1.0:
            new_size = (int(self.canvas_width * self.zoom_level),
                       int(self.canvas_height * self.zoom_level))
            view = view.resize(new_size, Image.LANCZOS)
        
        # Crop für Ansicht
        view_crop = view.crop((
            -self.pan_x,
            -self.pan_y,
            -self.pan_x + self.view_width,
            -self.pan_y + self.view_height
        ))
        
        self.photo = ImageTk.PhotoImage(view_crop)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
    
    def start_pan(self, event):
        """Start Panning"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
    
    def do_pan(self, event):
        """Panning durchführen"""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.pan_x += dx
        self.pan_y += dy
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.update_canvas()
    
    def on_zoom(self, event):
        """Zoom mit Mausrad"""
        if event.delta > 0:
            self.zoom_level *= 1.1
        else:
            self.zoom_level /= 1.1
        
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        self.update_canvas()
        self.info_label.config(text=f"Zoom: {self.zoom_level:.1f}x")
    
    def save_to_history(self):
        """Speichere in History"""
        # Remove future history if we're not at the end
        self.history = self.history[:self.history_index + 1]
        
        # Add new state
        self.history.append(self.image.copy())
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.history_index += 1
    
    def undo(self):
        """Rückgängig"""
        if self.history_index > 0:
            self.history_index -= 1
            self.image = self.history[self.history_index].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.info_label.config(text="Rückgängig")
    
    def redo(self):
        """Wiederherstellen"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.image = self.history[self.history_index].copy()
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.info_label.config(text="Wiederhergestellt")
    
    def clear_canvas(self):
        """Canvas löschen"""
        if messagebox.askyesno("Löschen", "Canvas wirklich löschen?"):
            self.image = Image.new('RGBA', (self.canvas_width, self.canvas_height), 
                                  (240, 230, 210, 255))
            self.draw = ImageDraw.Draw(self.image)
            self.update_canvas()
            self.save_to_history()
    
    def new_image(self):
        """Neues Bild"""
        if messagebox.askyesno("Neues Bild", "Aktuelles Bild verwerfen?"):
            self.image = Image.new('RGBA', (self.canvas_width, self.canvas_height),
                                  (240, 230, 210, 255))
            self.draw = ImageDraw.Draw(self.image)
            self.history = [self.image.copy()]
            self.history_index = 0
            self.update_canvas()
    
    def load_image(self):
        """Bild laden"""
        path = filedialog.askopenfilename(
            title="Bild laden",
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg"), ("Alle", "*.*")]
        )
        
        if path:
            try:
                loaded = Image.open(path).convert('RGBA')
                # Resize to canvas size if needed
                if loaded.size != (self.canvas_width, self.canvas_height):
                    loaded = loaded.resize((self.canvas_width, self.canvas_height), Image.LANCZOS)
                
                self.image = loaded
                self.draw = ImageDraw.Draw(self.image)
                self.update_canvas()
                self.save_to_history()
                self.info_label.config(text=f"Geladen: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Bild nicht laden:\n{e}")
    
    def save_image(self):
        """Bild speichern"""
        path = filedialog.asksaveasfilename(
            title="Bild speichern",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPG", "*.jpg")]
        )
        
        if path:
            try:
                self.image.save(path)
                self.info_label.config(text=f"Gespeichert: {os.path.basename(path)}")
                messagebox.showinfo("Erfolg", f"Bild gespeichert:\n{path}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Bild nicht speichern:\n{e}")
    
    # =================== EFFECTS ===================
    
    def apply_watercolor(self):
        """Aquarell-Effekt"""
        self.image = self.image.filter(ImageFilter.SMOOTH_MORE)
        self.image = self.image.filter(ImageFilter.EDGE_ENHANCE_MORE)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Aquarell-Effekt angewendet")
    
    def apply_parchment(self):
        """Pergament-Effekt"""
        enhancer = ImageEnhance.Color(self.image)
        self.image = enhancer.enhance(0.7)
        enhancer = ImageEnhance.Brightness(self.image)
        self.image = enhancer.enhance(1.1)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Pergament-Effekt angewendet")
    
    def apply_engraving(self):
        """Kupferstich-Effekt"""
        self.image = self.image.filter(ImageFilter.FIND_EDGES)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Kupferstich-Effekt angewendet")
    
    def apply_blur(self):
        """Weichzeichnen"""
        self.image = self.image.filter(ImageFilter.BLUR)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Weichzeichner angewendet")
    
    def apply_brighten(self):
        """Aufhellen"""
        enhancer = ImageEnhance.Brightness(self.image)
        self.image = enhancer.enhance(1.2)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Aufgehellt")
    
    def apply_darken(self):
        """Abdunkeln"""
        enhancer = ImageEnhance.Brightness(self.image)
        self.image = enhancer.enhance(0.8)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Abgedunkelt")
    
    def apply_contrast(self):
        """Kontrast erhöhen"""
        enhancer = ImageEnhance.Contrast(self.image)
        self.image = enhancer.enhance(1.3)
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()
        self.save_to_history()
        self.info_label.config(text="Kontrast erhöht")

if __name__ == "__main__":
    app = HandDrawnMapEditor()
    app.mainloop()
