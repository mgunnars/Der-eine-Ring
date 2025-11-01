"""
Fog/Cloud Texture Generator für "Der Eine Ring"
Erstellt professionelle Nebel-/Wolkentexturen wie handgezeichnet
Verwendet optional ein Cloud-Referenzbild als Basis
"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import random
import math
import os


class FogTextureGenerator:
    """
    Generiert professionelle Fog/Cloud-Texturen
    Inspiriert von handgezeichneten Wolken
    Kann ein Referenzbild als Basis verwenden
    """
    
    def __init__(self):
        self.texture_cache = {}
        self.cloud_reference = None
        
        # Versuche das Cloud-Referenzbild zu finden
        possible_paths = [
            "cloud_reference.png",
            "cloud_reference.jpg",
            "maps/cloud_reference.png",
            "maps/cloud_reference.jpg",
            "textures/cloud_reference.png"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    self.cloud_reference = Image.open(path).convert('RGBA')
                    print(f"✓ Cloud-Referenzbild geladen: {path}")
                    break
                except Exception as e:
                    print(f"Warnung: Konnte {path} nicht laden: {e}")
    
    def generate_cloud_fog_texture(self, size=64):
        """
        Generiert eine wolkenartige Fog-Textur
        Verwendet das Referenzbild falls verfügbar, sonst prozedural
        WICHTIG: Hohe Deckkraft damit Texturen darunter komplett verdeckt werden!
        """
        
        # Wenn Referenzbild vorhanden, nutze es als Basis
        if self.cloud_reference:
            # Skaliere Referenzbild auf gewünschte Größe
            img = self.cloud_reference.copy()
            img = img.resize((size, size), Image.LANCZOS)
            
            # Stelle sicher dass es vollständig deckend ist (Alpha=255)
            pixels = img.load()
            for y in range(size):
                for x in range(size):
                    r, g, b, a = pixels[x, y]
                    pixels[x, y] = (r, g, b, 255)  # Volle Deckkraft!
            
            return img
        
        # Fallback: Prozedural generieren (wie vorher)
        # Erstelle RGBA-Image für Transparenz
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Basis: Helles Grau-Beige wie im Referenzbild mit HOHER Deckkraft
        base_color = (210, 200, 190)  # Warmes Grau-Beige
        
        # Fülle Basis mit VOLLER Deckkraft (255) damit nichts durchscheint
        draw.rectangle([(0, 0), (size, size)], fill=base_color + (255,))
        
        # Hauptwolken-Formen (große, weiche Ellipsen)
        random.seed(size * 42)  # Konsistent für gleiche Größe
        
        num_main_clouds = 3
        for i in range(num_main_clouds):
            # Position und Größe
            x = random.randint(-size//4, size - size//4)
            y = random.randint(-size//4, size - size//4)
            width = random.randint(size//2, size)
            height = random.randint(size//3, size//2)
            
            # Wolkenkern - etwas dunkler, VOLLDECKEND
            cloud_color = (
                random.randint(185, 205),
                random.randint(175, 195),
                random.randint(165, 185),
                255  # VOLLE Deckkraft!
            )
            
            draw.ellipse([(x, y), (x + width, y + height)], fill=cloud_color)
        
        # Kleinere Wolken-Details für organischen Look
        num_small_clouds = random.randint(4, 7)
        for _ in range(num_small_clouds):
            x = random.randint(-10, size)
            y = random.randint(-10, size)
            width = random.randint(size//6, size//3)
            height = random.randint(size//6, size//3)
            
            cloud_color = (
                random.randint(190, 210),
                random.randint(180, 200),
                random.randint(170, 190),
                255  # VOLLE Deckkraft!
            )
            
            draw.ellipse([(x, y), (x + width, y + height)], fill=cloud_color)
        
        random.seed()  # Reset
        
        # Mehrfacher Blur für weiche, organische Wolken (wie Referenzbild)
        img = img.filter(ImageFilter.GaussianBlur(8))
        img = img.filter(ImageFilter.SMOOTH_MORE)
        img = img.filter(ImageFilter.GaussianBlur(4))
        
        # Leichte Punktierung für organische Textur - NACH dem Blur
        draw = ImageDraw.Draw(img, 'RGBA')
        num_dots = size * 2  # Reduzierte Dichte für subtilere Textur
        
        for _ in range(num_dots):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            
            # Nur subtile dunkle Punkte für Tiefenwirkung
            if random.random() < 0.6:
                dot_color = (
                    random.randint(150, 170),
                    random.randint(140, 160),
                    random.randint(130, 150),
                    255
                )
                draw.point((x, y), fill=dot_color)
        
        # Final Blur für Weichheit
        img = img.filter(ImageFilter.GaussianBlur(2))
        
        # Leicht aufhellen für bessere Sichtbarkeit
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        
        return img
    
    def generate_dense_fog_texture(self, size=64):
        """
        Generiert dichten Nebel (für stark verdeckte Bereiche)
        """
        img = Image.new('RGBA', (size, size), (200, 195, 190, 230))
        draw = ImageDraw.Draw(img)
        
        # Sehr dichte Wolkenstruktur
        random.seed(size * 123)
        
        for _ in range(size * 3):
            x = random.randint(0, size-1)
            y = random.randint(0, size-1)
            
            gray = random.randint(180, 210)
            alpha = random.randint(200, 240)
            
            draw.point((x, y), fill=(gray, gray-10, gray-20, alpha))
        
        random.seed()
        
        # Starker Blur
        img = img.filter(ImageFilter.GaussianBlur(4))
        
        return img
    
    def generate_light_fog_texture(self, size=64):
        """
        Generiert leichten Nebel (für Rand-Bereiche)
        """
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Leichte Wolken
        random.seed(size * 456)
        
        num_clouds = 2
        for _ in range(num_clouds):
            x = random.randint(-size//2, size)
            y = random.randint(-size//2, size)
            width = random.randint(size//2, size)
            height = random.randint(size//2, size)
            
            cloud_color = (
                random.randint(210, 230),
                random.randint(200, 220),
                random.randint(190, 210),
                random.randint(80, 120)
            )
            
            draw.ellipse([(x, y), (x + width, y + height)], fill=cloud_color)
        
        # Wenige Punkte
        for _ in range(size * 2):
            x = random.randint(0, size-1)
            y = random.randint(0, size-1)
            
            gray = random.randint(200, 220)
            alpha = random.randint(60, 100)
            
            draw.point((x, y), fill=(gray, gray-5, gray-10, alpha))
        
        random.seed()
        
        img = img.filter(ImageFilter.GaussianBlur(3))
        
        return img
    
    def get_fog_texture(self, size=64, fog_type="normal"):
        """
        Gibt eine gecachte Fog-Textur zurück
        
        fog_type: "normal", "dense", "light"
        """
        cache_key = f"{fog_type}_{size}"
        
        if cache_key not in self.texture_cache:
            if fog_type == "dense":
                self.texture_cache[cache_key] = self.generate_dense_fog_texture(size)
            elif fog_type == "light":
                self.texture_cache[cache_key] = self.generate_light_fog_texture(size)
            else:
                self.texture_cache[cache_key] = self.generate_cloud_fog_texture(size)
        
        return self.texture_cache[cache_key]
    
    def generate_animated_fog_frame(self, size=64, frame=0):
        """
        Generiert animierte Fog-Textur (leicht bewegte Wolken)
        """
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Bewegung basierend auf Frame
        offset_x = int(math.sin(frame * 0.05) * 5)
        offset_y = int(math.cos(frame * 0.03) * 3)
        
        # Basis
        base_color = (210, 200, 190)
        draw.rectangle([(0, 0), (size, size)], fill=base_color + (200,))
        
        # Bewegte Wolken
        random.seed(size * 42 + frame // 10)
        
        num_clouds = 3
        for i in range(num_clouds):
            x = random.randint(-size//4, size - size//4) + offset_x
            y = random.randint(-size//4, size - size//4) + offset_y
            width = random.randint(size//2, size)
            height = random.randint(size//3, size//2)
            
            cloud_color = (
                random.randint(190, 210),
                random.randint(180, 200),
                random.randint(170, 190),
                random.randint(180, 220)
            )
            
            draw.ellipse([(x, y), (x + width, y + height)], fill=cloud_color)
        
        # Punkte
        for _ in range(size * 5):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            
            dot_color = (
                random.randint(160, 190),
                random.randint(150, 180),
                random.randint(140, 170),
                random.randint(150, 200)
            )
            draw.point((x, y), fill=dot_color)
        
        random.seed()
        
        img = img.filter(ImageFilter.GaussianBlur(3))
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def clear_cache(self):
        """Leert den Texture-Cache"""
        self.texture_cache.clear()
