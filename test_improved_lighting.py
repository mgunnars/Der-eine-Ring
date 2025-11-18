"""
Test und Demo für das verbesserte Lichtsystem
Zeigt verschiedene Lichtquellen mit physikalisch korrektem Falloff und realistischem Flackern
"""
import tkinter as tk
from PIL import Image, ImageTk
from lighting_system import LightingEngine, LightSource, LIGHT_PRESETS
import time

class LightingDemo(tk.Tk):
    """Demo-Window für verbessertes Lichtsystem"""
    
    def __init__(self):
        super().__init__()
        
        self.title("🔥 Verbessertes Lichtsystem - Demo")
        self.geometry("1400x900")
        self.configure(bg="#1a1a1a")
        
        # Lighting Engine
        self.lighting_engine = LightingEngine()
        self.lighting_engine.enabled = True
        self.lighting_engine.ambient_intensity = 0.1  # Sehr dunkel
        
        # Test-Szene erstellen
        self.setup_test_scene()
        
        # UI erstellen
        self.setup_ui()
        
        # Animation starten
        self.is_running = True
        self.last_time = time.time()
        self.animate()
        
    def setup_test_scene(self):
        """Erstelle Test-Szene mit verschiedenen Lichtquellen"""
        
        # Reihe 1: Fackeln und Feuer
        self.lighting_engine.add_light(LightSource(
            x=5, y=5, **LIGHT_PRESETS["torch"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=12, y=5, **LIGHT_PRESETS["fire"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=19, y=5, **LIGHT_PRESETS["campfire"]
        ))
        
        # Reihe 2: Kerzen und Laternen
        self.lighting_engine.add_light(LightSource(
            x=5, y=12, **LIGHT_PRESETS["candle"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=12, y=12, **LIGHT_PRESETS["lantern"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=19, y=12, **LIGHT_PRESETS["candle"]
        ))
        
        # Reihe 3: Magische Lichter
        self.lighting_engine.add_light(LightSource(
            x=5, y=19, **LIGHT_PRESETS["magic"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=12, y=19, **LIGHT_PRESETS["crystal"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=19, y=19, **LIGHT_PRESETS["brazier"]
        ))
        
        # Reihe 4: Natürliche Lichter
        self.lighting_engine.add_light(LightSource(
            x=5, y=26, **LIGHT_PRESETS["moonlight"]
        ))
        
        self.lighting_engine.add_light(LightSource(
            x=12, y=26, **LIGHT_PRESETS["window"]
        ))
        
        print(f"✅ Test-Szene erstellt mit {len(self.lighting_engine.lights)} Lichtquellen")
        
    def setup_ui(self):
        """Erstelle UI"""
        
        # Haupt-Container
        main_frame = tk.Frame(self, bg="#1a1a1a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Linke Seite: Canvas für Licht-Rendering
        left_frame = tk.Frame(main_frame, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        title = tk.Label(left_frame, text="🔥 Physikalisch korrektes Lichtsystem", 
                        font=("Arial", 18, "bold"), bg="#1a1a1a", fg="white")
        title.pack(pady=10)
        
        # Canvas
        self.canvas = tk.Canvas(left_frame, width=800, height=800, bg="black", highlightthickness=0)
        self.canvas.pack(pady=10)
        
        # FPS Anzeige
        self.fps_label = tk.Label(left_frame, text="FPS: 0", 
                                 font=("Courier", 12), bg="#1a1a1a", fg="#00ff00")
        self.fps_label.pack()
        
        # Rechte Seite: Info und Controls
        right_frame = tk.Frame(main_frame, bg="#2a2a2a", width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        # Info-Text
        info_title = tk.Label(right_frame, text="ℹ️ Lichtquellen-Typen", 
                             font=("Arial", 14, "bold"), bg="#2a2a2a", fg="white")
        info_title.pack(pady=10)
        
        info_text = """
🔥 FACKELN & FEUER
• Fackel (torch): Starkes Flackern, warmes Orange
• Feuer (fire): Sehr intensiv, große Variationen
• Lagerfeuer (campfire): Mittlere Intensität

🕯️ KERZEN & LATERNEN  
• Kerze (candle): Sanftes Flackern, weiches Gelb
• Laterne (lantern): Stabile Fackel-Physik

✨ MAGISCHE LICHTER
• Magie (magic): Pulsierend, Farbwechsel
• Kristall (crystal): Kühles Blau, sanft
• Feuerschale (brazier): Große Flamme

🌙 NATÜRLICHE LICHTER
• Mondlicht (moonlight): Konstant, großer Radius
• Fenster (window): Tageslicht, leicht blau

⚙️ PHYSIK-FEATURES:
✓ Inverse-Square-Law Lichtabnahme
✓ Typ-spezifische Falloff-Exponenten
✓ Dynamische Farbtemperatur
✓ Harmonische Flacker-Frequenzen
✓ Zufällige Funken bei Feuer
✓ Kern-Überhellung (Bloom-Effekt)
"""
        
        info_label = tk.Label(right_frame, text=info_text, 
                             font=("Courier", 9), bg="#2a2a2a", fg="#cccccc",
                             justify=tk.LEFT, anchor="w")
        info_label.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        # Controls
        control_frame = tk.LabelFrame(right_frame, text="🎛️ Einstellungen", 
                                     font=("Arial", 12, "bold"),
                                     bg="#2a2a2a", fg="white")
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Ambient Intensity
        ambient_frame = tk.Frame(control_frame, bg="#2a2a2a")
        ambient_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(ambient_frame, text="Umgebungslicht:", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        self.ambient_var = tk.DoubleVar(value=0.1)
        ambient_slider = tk.Scale(ambient_frame, from_=0.0, to=0.5, resolution=0.05,
                                 orient=tk.HORIZONTAL, variable=self.ambient_var,
                                 command=self.update_ambient,
                                 bg="#2a2a2a", fg="white", highlightthickness=0)
        ambient_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Animation Speed
        speed_frame = tk.Frame(control_frame, bg="#2a2a2a")
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(speed_frame, text="Animation Speed:", bg="#2a2a2a", fg="white").pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_slider = tk.Scale(speed_frame, from_=0.1, to=3.0, resolution=0.1,
                               orient=tk.HORIZONTAL, variable=self.speed_var,
                               bg="#2a2a2a", fg="white", highlightthickness=0)
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Buttons
        btn_frame = tk.Frame(right_frame, bg="#2a2a2a")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        pause_btn = tk.Button(btn_frame, text="⏸️ Pause/Resume",
                             command=self.toggle_pause,
                             bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        pause_btn.pack(fill=tk.X, pady=2)
        
        reset_btn = tk.Button(btn_frame, text="🔄 Zeit zurücksetzen",
                             command=self.reset_time,
                             bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
        reset_btn.pack(fill=tk.X, pady=2)
        
    def update_ambient(self, value):
        """Update Ambient Intensity"""
        self.lighting_engine.ambient_intensity = float(value)
        
    def toggle_pause(self):
        """Pause/Resume Animation"""
        self.is_running = not self.is_running
        if self.is_running:
            self.last_time = time.time()
            self.animate()
            
    def reset_time(self):
        """Reset Animation Time"""
        self.lighting_engine.time_offset = 0.0
        self.last_time = time.time()
        
    def animate(self):
        """Animation Loop"""
        if not self.is_running:
            return
        
        # Delta Time berechnen
        current_time = time.time()
        delta_time = current_time - self.last_time
        self.last_time = current_time
        
        # FPS berechnen
        fps = 1.0 / delta_time if delta_time > 0 else 0
        self.fps_label.config(text=f"FPS: {fps:.1f} | Zeit: {self.lighting_engine.time_offset:.2f}s")
        
        # Animation updaten (mit Speed-Multiplikator)
        self.lighting_engine.update_animation(delta_time * self.speed_var.get())
        
        # Render Lighting
        tile_size = 25  # 25x25 px pro Tile
        map_width = 32
        map_height = 32
        
        lighting_img = self.lighting_engine.render_lighting(
            width=map_width,
            height=map_height,
            tile_size=tile_size,
            time_offset=self.lighting_engine.time_offset
        )
        
        # Konvertiere zu PhotoImage und zeige an
        photo = ImageTk.PhotoImage(lighting_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        self.canvas.image = photo  # Referenz behalten
        
        # Zeichne Lichtquellen-Positionen
        for light in self.lighting_engine.lights:
            cx = light.x * tile_size + tile_size // 2
            cy = light.y * tile_size + tile_size // 2
            
            # Marker für Lichtquelle
            self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, 
                                   fill="white", outline="black", width=2)
            
            # Typ-Label
            self.canvas.create_text(cx, cy-15, text=light.light_type, 
                                   fill="white", font=("Arial", 8, "bold"))
        
        # Nächstes Frame nach ~16ms (60 FPS target)
        self.after(16, self.animate)
        
    def destroy(self):
        """Cleanup"""
        self.is_running = False
        super().destroy()


if __name__ == "__main__":
    print("🔥 Starte verbessertes Lichtsystem Demo...")
    print("=" * 60)
    print("FEATURES:")
    print("  ✓ Physikalisch korrekte Lichtabnahme (Inverse-Square-Law)")
    print("  ✓ Verschiedene Lichtintensitäten pro Typ")
    print("  ✓ Realistisches Flackern mit Harmonischen")
    print("  ✓ Dynamische Farbtemperatur (Feuer: weiß→gelb→orange→rot)")
    print("  ✓ Zufällige Funken und Aussetzer bei Feuer")
    print("  ✓ 60 FPS Animation")
    print("=" * 60)
    
    app = LightingDemo()
    app.mainloop()
    
    print("Demo beendet.")
