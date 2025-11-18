"""
Test-Script für physikalisch korrektes Lighting System
Testet Tag-Modus mit Dunkelheitspolygonen und realistischer Beleuchtung
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
from lighting_system import LightingEngine, LightSource, LIGHT_PRESETS
import random

class PhysicalLightingDemo(tk.Tk):
    """Demo für das neue physikalische Lighting System"""
    
    def __init__(self):
        super().__init__()
        
        self.title("🔦 Physikalisch korrektes Lighting - Test")
        self.geometry("1400x900")
        self.configure(bg="#1a1a1a")
        
        # Map-Daten (einfache Textur-Map)
        self.map_width = 40
        self.map_height = 30
        self.tile_size = 20
        
        # Lighting Engine
        self.lighting_engine = LightingEngine()
        self.lighting_engine.lighting_mode = "day"  # TAG-MODUS!
        self.lighting_engine.ambient_intensity = 0.25  # 25% Minimum-Helligkeit (Streulicht)
        self.lighting_engine.darkness_opacity = 0.80  # 80% Verdunkelung in Innenräumen
        
        # Definiere Innenräume (Dunkelheitspolygone)
        # Raum 1: Großer rechteckiger Raum (mit Fenster und 2 Lichtquellen)
        room1 = [
            (5, 5),   # Oben links
            (25, 5),  # Oben rechts
            (25, 20), # Unten rechts
            (5, 20)   # Unten links
        ]
        self.lighting_engine.darkness_polygons.append(room1)
        
        # Raum 2: Kleinerer L-förmiger Raum
        room2 = [
            (28, 8),
            (35, 8),
            (35, 25),
            (30, 25),
            (30, 15),
            (28, 15)
        ]
        self.lighting_engine.darkness_polygons.append(room2)
        
        # Fenster (window light = Tageslicht von außen)
        window_preset = LIGHT_PRESETS["window"]
        self.lighting_engine.add_light(LightSource(
            x=10, y=5,  # An der Wand
            radius=window_preset["radius"],
            color=window_preset["color"],
            intensity=window_preset["intensity"],
            flicker=window_preset["flicker"],
            light_type=window_preset["light_type"]
        ))
        
        # Fackel 1 (warmes Flackerlicht)
        torch_preset = LIGHT_PRESETS["torch"]
        self.lighting_engine.add_light(LightSource(
            x=15, y=12,
            radius=torch_preset["radius"],
            color=torch_preset["color"],
            intensity=torch_preset["intensity"],
            flicker=torch_preset["flicker"],
            light_type=torch_preset["light_type"]
        ))
        
        # Kerze (sanftes Flackern)
        candle_preset = LIGHT_PRESETS["candle"]
        self.lighting_engine.add_light(LightSource(
            x=20, y=15,
            radius=candle_preset["radius"],
            color=candle_preset["color"],
            intensity=candle_preset["intensity"],
            flicker=candle_preset["flicker"],
            light_type=candle_preset["light_type"]
        ))
        
        # Magisches Licht im zweiten Raum
        magic_preset = LIGHT_PRESETS["magic"]
        self.lighting_engine.add_light(LightSource(
            x=32, y=16,
            radius=magic_preset["radius"],
            color=magic_preset["color"],
            intensity=magic_preset["intensity"],
            flicker=magic_preset["flicker"],
            light_type=magic_preset["light_type"]
        ))
        
        self.lighting_time = 0.0
        
        # UI Setup
        self.setup_ui()
        
        # Start Animation
        self.animate()
    
    def setup_ui(self):
        """Erstelle UI"""
        # Canvas für Rendering
        self.canvas = tk.Canvas(self, bg="#0a0a0a", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Control Panel
        control_frame = tk.Frame(self, bg="#1a1a1a", width=300)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        tk.Label(control_frame, text="⚙️ Physikalisches Lighting", 
                bg="#1a1a1a", fg="white", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Info-Text
        info = ("✨ NEUE FEATURES:\n\n"
                "• Texturen bleiben IMMER sichtbar\n"
                "• Schatten verdunkeln multiplikativ\n"
                "• Licht hellt physikalisch auf\n"
                "• Nie 100% dunkel (Streulicht)\n"
                "• Realistische Farbtemperaturen\n\n"
                "🔥 Fackel: Weiß→Gelb→Orange→Rot\n"
                "🕯️ Kerze: Warmes sanftes Gelb\n"
                "🪟 Fenster: Kühles Tageslicht\n"
                "✨ Magie: Pulsierendes Violett")
        
        tk.Label(control_frame, text=info, bg="#1a1a1a", fg="#aaaaaa",
                font=("Arial", 9), justify=tk.LEFT).pack(pady=10, padx=10)
        
        # Controls
        tk.Label(control_frame, text="Dunkelheit (Innenräume):", 
                bg="#1a1a1a", fg="white", font=("Arial", 10)).pack(pady=(20, 5))
        
        self.darkness_var = tk.DoubleVar(value=self.lighting_engine.darkness_opacity)
        tk.Scale(control_frame, from_=0.0, to=1.0, resolution=0.05,
                orient=tk.HORIZONTAL, variable=self.darkness_var,
                command=self.update_darkness,
                bg="#2a2a2a", fg="white", highlightthickness=0).pack(fill=tk.X, padx=10)
        
        tk.Label(control_frame, text="Ambient (Streulicht):", 
                bg="#1a1a1a", fg="white", font=("Arial", 10)).pack(pady=(20, 5))
        
        self.ambient_var = tk.DoubleVar(value=self.lighting_engine.ambient_intensity)
        tk.Scale(control_frame, from_=0.0, to=0.5, resolution=0.05,
                orient=tk.HORIZONTAL, variable=self.ambient_var,
                command=self.update_ambient,
                bg="#2a2a2a", fg="white", highlightthickness=0).pack(fill=tk.X, padx=10)
        
        # FPS Counter
        self.fps_label = tk.Label(control_frame, text="FPS: 0", 
                                 bg="#1a1a1a", fg="#4a4", font=("Courier", 12))
        self.fps_label.pack(pady=20)
        
        self.frame_times = []
        self.last_frame_time = 0
    
    def update_darkness(self, value):
        """Update Darkness-Opacity"""
        self.lighting_engine.darkness_opacity = float(value)
    
    def update_ambient(self, value):
        """Update Ambient-Intensity"""
        self.lighting_engine.ambient_intensity = float(value)
    
    def create_base_map(self):
        """Erstelle Basis-Map mit Texturen"""
        img_width = self.map_width * self.tile_size
        img_height = self.map_height * self.tile_size
        
        # Erstelle bunte Test-Map (simuliert Terrain-Texturen)
        base_map = Image.new('RGB', (img_width, img_height))
        draw = ImageDraw.Draw(base_map)
        
        # Zeichne buntes Muster (simuliert verschiedene Terrains)
        for y in range(self.map_height):
            for x in range(self.map_width):
                # Verschiedene Farben je nach Position
                if (x + y) % 3 == 0:
                    color = (90, 150, 90)  # Grünes Gras
                elif (x + y) % 3 == 1:
                    color = (120, 100, 70)  # Brauner Boden
                else:
                    color = (140, 140, 100)  # Sandstein
                
                # Leichte Variation für Textur-Effekt
                variation = random.randint(-10, 10)
                color = tuple(max(0, min(255, c + variation)) for c in color)
                
                x1 = x * self.tile_size
                y1 = y * self.tile_size
                x2 = x1 + self.tile_size
                y2 = y1 + self.tile_size
                
                draw.rectangle([x1, y1, x2, y2], fill=color)
        
        # Zeichne Raum-Umrisse (nur zur Visualisierung)
        for polygon in self.lighting_engine.darkness_polygons:
            pixel_poly = [(int(x * self.tile_size), int(y * self.tile_size)) for x, y in polygon]
            draw.polygon(pixel_poly, outline=(200, 200, 200), width=3)
        
        return base_map
    
    def animate(self):
        """Animation-Loop"""
        import time
        start_time = time.time()
        
        # Update Lighting-Animation
        self.lighting_engine.update_animation(0.033)  # ~30 FPS
        self.lighting_time += 0.033
        
        # Erstelle Base-Map
        base_map = self.create_base_map()
        
        # Konvertiere zu RGBA für Compositing
        base_map = base_map.convert('RGBA')
        
        # Rendere Lighting-Overlay
        lighting_overlay = self.lighting_engine.render_lighting(
            width=self.map_width,
            height=self.map_height,
            tile_size=self.tile_size,
            time_offset=self.lighting_time,
            radius_scale=1.0
        )
        
        # ═══════════════════════════════════════════════════════════
        # TAG-MODUS: MULTIPLY-BLEND für physikalisch korrekte Schatten
        # ═══════════════════════════════════════════════════════════
        if self.lighting_engine.lighting_mode == "day" and self.lighting_engine.darkness_polygons:
            from PIL import ImageChops
            
            # Separiere RGB und Alpha
            lighting_rgb = lighting_overlay.convert('RGB')
            lighting_alpha = lighting_overlay.split()[3]
            
            # Konvertiere Base-Map zu RGB
            base_rgb = base_map.convert('RGB')
            
            # MULTIPLY: Verdunkelt die Map (wie echte Schatten)
            darkened_map = ImageChops.multiply(base_rgb, lighting_rgb)
            darkened_map = darkened_map.convert('RGBA')
            
            # Wende Multiply nur in Polygon-Bereichen an
            result = Image.composite(darkened_map, base_map, lighting_alpha)
        else:
            # Normales Alpha-Composite
            result = Image.alpha_composite(base_map, lighting_overlay)
        
        # Zu RGB konvertieren und anzeigen
        result = result.convert('RGB')
        
        # Auf Canvas anzeigen
        photo = ImageTk.PhotoImage(result)
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Zentrieren
        x = (canvas_width - result.width) // 2
        y = (canvas_height - result.height) // 2
        
        self.canvas.delete("all")
        self.canvas.create_image(x, y, image=photo, anchor=tk.NW)
        self.canvas.image = photo  # Referenz behalten!
        
        # FPS berechnen
        frame_time = time.time() - start_time
        self.frame_times.append(frame_time)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        self.fps_label.config(text=f"FPS: {fps:.1f}")
        
        # Nächster Frame
        self.after(33, self.animate)  # ~30 FPS

if __name__ == "__main__":
    app = PhysicalLightingDemo()
    app.mainloop()
