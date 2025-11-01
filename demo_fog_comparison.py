"""
Visueller Vergleich: Alt vs. Neu Fog-System
Zeigt Memory-Verbrauch und Performance
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk, ImageFilter
import time
import random
from fog_texture_generator import FogTextureGenerator


class FogComparisonDemo(tk.Tk):
    """Vergleicht altes und neues Fog-System"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Fog-System Vergleich - Alt vs. Neu")
        self.geometry("1000x700")
        self.configure(bg="#1a1a1a")
        
        # Neuer Generator
        self.fog_gen = FogTextureGenerator()
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI erstellen"""
        # Header
        header = tk.Frame(self, bg="#0a0a0a")
        header.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(
            header,
            text="🌫️ Fog-System Vergleich",
            font=("Arial", 18, "bold"),
            bg="#0a0a0a",
            fg="#d4af37"
        ).pack(pady=10)
        
        tk.Label(
            header,
            text="Links: ALT (Memory-Problem) | Rechts: NEU (Optimiert)",
            font=("Arial", 10),
            bg="#0a0a0a",
            fg="#888888"
        ).pack(pady=(0, 10))
        
        # Main Content
        content = tk.Frame(self, bg="#1a1a1a")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Links: Alt
        left_frame = tk.Frame(content, bg="#2a2a2a", relief=tk.SUNKEN, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(
            left_frame,
            text="❌ ALTES SYSTEM",
            bg="#7d2a2a",
            fg="white",
            font=("Arial", 12, "bold"),
            pady=5
        ).pack(fill=tk.X)
        
        self.old_canvas = tk.Canvas(left_frame, width=400, height=400, bg="#1a1a1a")
        self.old_canvas.pack(padx=10, pady=10)
        
        self.old_stats = tk.Text(left_frame, height=8, bg="#1a1a1a", fg="white",
                                font=("Courier", 9), relief=tk.FLAT)
        self.old_stats.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Rechts: Neu
        right_frame = tk.Frame(content, bg="#2a2a2a", relief=tk.SUNKEN, bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(
            right_frame,
            text="✅ NEUES SYSTEM",
            bg="#2a7d2a",
            fg="white",
            font=("Arial", 12, "bold"),
            pady=5
        ).pack(fill=tk.X)
        
        self.new_canvas = tk.Canvas(right_frame, width=400, height=400, bg="#1a1a1a")
        self.new_canvas.pack(padx=10, pady=10)
        
        self.new_stats = tk.Text(right_frame, height=8, bg="#1a1a1a", fg="white",
                                font=("Courier", 9), relief=tk.FLAT)
        self.new_stats.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Bottom: Controls
        control_frame = tk.Frame(self, bg="#0a0a0a")
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        tk.Button(
            control_frame,
            text="🔄 Test starten (100 Tiles)",
            bg="#2a7d2a",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=10,
            command=self.run_test
        ).pack(side=tk.LEFT, padx=20)
        
        tk.Button(
            control_frame,
            text="❌ Beenden",
            bg="#555555",
            fg="white",
            font=("Arial", 11),
            padx=20,
            pady=10,
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=20)
        
        # Info
        info_text = "💡 Tipp: Das alte System erstellt für JEDES Tile eine neue Textur.\nDas neue System wiederverwendet eine einzige Textur!"
        tk.Label(
            control_frame,
            text=info_text,
            bg="#0a0a0a",
            fg="#888888",
            font=("Arial", 9),
            justify=tk.CENTER
        ).pack(side=tk.LEFT, expand=True)
    
    def generate_old_fog(self, size):
        """Simuliert ALTES System - neue Textur für jedes Tile"""
        # Einfache graue Textur (wie vorher)
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        base_fog_color = (200, 200, 200, 240)
        draw.rectangle([(0, 0), (size, size)], fill=base_fog_color)
        
        # Minimale Wolken (Performance-Problem!)
        for _ in range(2):
            x = random.randint(-5, size - 5)
            y = random.randint(-5, size - 5)
            s = random.randint(size // 2, size)
            draw.ellipse([(x, y), (x + s, y + s)], fill=(180, 180, 180, 200))
        
        img = img.filter(ImageFilter.GaussianBlur(2))
        
        return img
    
    def run_test(self):
        """Führt Vergleichstest durch"""
        self.old_canvas.delete("all")
        self.new_canvas.delete("all")
        
        tile_size = 40
        tiles_per_row = 10
        total_tiles = tiles_per_row * tiles_per_row
        
        # === ALTES SYSTEM ===
        self.old_stats.delete("1.0", tk.END)
        self.old_stats.insert("1.0", "⏳ Teste altes System...\n")
        self.update()
        
        old_photos = []
        old_start = time.time()
        
        for row in range(tiles_per_row):
            for col in range(tiles_per_row):
                x = col * tile_size
                y = row * tile_size
                
                # NEUE Textur für JEDES Tile (Problem!)
                fog_img = self.generate_old_fog(tile_size)
                photo = ImageTk.PhotoImage(fog_img)
                old_photos.append(photo)  # Muss alle referenzieren!
                
                self.old_canvas.create_image(x, y, image=photo, anchor=tk.NW)
        
        old_time = (time.time() - old_start) * 1000
        old_memory = len(old_photos) * tile_size * tile_size * 4 / 1024  # KB
        
        stats_text = f"""
❌ ALTES SYSTEM:
━━━━━━━━━━━━━━━━━━━━━━━━━
Tiles gezeichnet: {total_tiles}
Texturen erstellt: {len(old_photos)} ⚠️
Zeit: {old_time:.1f} ms
Geschätzter RAM: ~{old_memory:.1f} KB
        
⚠️ Problem: JEDES Tile = NEUE Textur!
Bei großen Karten → Memory-Overflow
→ "Fail to allocate bitmap"
        """.strip()
        
        self.old_stats.delete("1.0", tk.END)
        self.old_stats.insert("1.0", stats_text)
        
        # === NEUES SYSTEM ===
        self.new_stats.delete("1.0", tk.END)
        self.new_stats.insert("1.0", "⏳ Teste neues System...\n")
        self.update()
        
        new_start = time.time()
        
        # EINE Textur für ALLE Tiles (Lösung!)
        fog_texture = self.fog_gen.get_fog_texture(tile_size, "normal")
        new_photo = ImageTk.PhotoImage(fog_texture)
        
        for row in range(tiles_per_row):
            for col in range(tiles_per_row):
                x = col * tile_size
                y = row * tile_size
                
                # DIESELBE Textur wiederverwendet!
                self.new_canvas.create_image(x, y, image=new_photo, anchor=tk.NW)
        
        new_time = (time.time() - new_start) * 1000
        new_memory = 1 * tile_size * tile_size * 4 / 1024  # KB (nur 1 Textur!)
        
        # Vergleichswerte
        time_improvement = old_time / new_time if new_time > 0 else 0
        memory_improvement = old_memory / new_memory if new_memory > 0 else 0
        
        stats_text = f"""
✅ NEUES SYSTEM:
━━━━━━━━━━━━━━━━━━━━━━━━━
Tiles gezeichnet: {total_tiles}
Texturen erstellt: 1 ✨
Zeit: {new_time:.1f} ms
Geschätzter RAM: ~{new_memory:.1f} KB

✅ Lösung: Cache & Wiederverwendung!
→ {time_improvement:.1f}x schneller
→ {memory_improvement:.1f}x weniger Speicher
→ Kein Memory-Overflow mehr!
        """.strip()
        
        self.new_stats.delete("1.0", tk.END)
        self.new_stats.insert("1.0", stats_text)
        
        print("\n" + "="*50)
        print("  TEST ABGESCHLOSSEN")
        print("="*50)
        print(f"\n📊 VERGLEICH:")
        print(f"  Altes System: {old_time:.1f}ms, {old_memory:.0f}KB, {len(old_photos)} Texturen")
        print(f"  Neues System: {new_time:.1f}ms, {new_memory:.0f}KB, 1 Textur")
        print(f"\n✨ VERBESSERUNG:")
        print(f"  {time_improvement:.1f}x schneller")
        print(f"  {memory_improvement:.1f}x weniger Speicher")
        print(f"  {len(old_photos)}x weniger Texturen")
        print()


if __name__ == "__main__":
    print("\n" + "="*50)
    print("  FOG-SYSTEM VERGLEICH")
    print("="*50)
    print("\n💡 Dieser Demo zeigt:")
    print("  - Wie das alte System Memory verschwendete")
    print("  - Wie das neue System optimiert ist")
    print("  - Warum 'Fail to allocate bitmap' behoben ist")
    print("\n▶️ Starte Vergleichs-Demo...\n")
    
    app = FogComparisonDemo()
    app.mainloop()
