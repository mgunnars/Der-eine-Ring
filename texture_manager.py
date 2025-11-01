"""
Professioneller Texture Manager für "Der Eine Ring"
Generiert hochwertige Texturen mit PIL
HINWEIS: Dieser Manager wird für Kompatibilität beibehalten.
Für neue Features bitte AdvancedTextureRenderer verwenden.
"""
from PIL import Image, ImageDraw, ImageFilter
import random
import math

# Import für Kompatibilität mit neuem System
try:
    from advanced_texture_renderer import AdvancedTextureRenderer
    _advanced_renderer = AdvancedTextureRenderer()
except ImportError:
    _advanced_renderer = None

class TextureManager:
    """Verwaltet und generiert Texturen für verschiedene Terrain-Typen"""
    
    def __init__(self):
        self.texture_cache = {}
        
        # Nutze Advanced Renderer wenn verfügbar
        if _advanced_renderer:
            self.advanced_renderer = _advanced_renderer
        else:
            self.advanced_renderer = None
        
        # Farben EXAKT aus den Referenzbildern entnommen
        self.colors = {
            "empty": "#1a1a1a",
            "grass": "#7eb356",      # Saftiges Gras-Grün (aus Referenzbild)
            "water": "#5dade2",      # Klares Türkis-Blau (aus Referenzbild)
            "water_h": "#5dade2",
            "water_v": "#5dade2",
            "mountain": "#8b7d6b",   # Braun-Grauer Fels
            "forest": "#2e5a1c",     # Dunkles Wald-Grün
            "sand": "#c9b18a",       # Warmer Sand
            "snow": "#e8f4f8",       # Bläuliches Weiß
            "stone": "#9e8b7c",      # Stein-Pfad
            "dirt": "#a08567",       # Erdweg
            "road": "#8a7560",       # Gepflasterter Weg
            "village": "#c4a574"     # Gebäude-Farbe
        }
    
    def get_color(self, terrain_type):
        """Gibt die Grundfarbe für einen Terrain-Typ zurück"""
        return self.colors.get(terrain_type, "#1a1a1a")
    
    def get_texture(self, terrain_type, size=64):
        """
        Gibt die Textur für einen Terrain-Typ zurück
        Nutzt Advanced Renderer wenn verfügbar
        """
        # Nutze Advanced Renderer für bessere Qualität
        if self.advanced_renderer:
            try:
                return self.advanced_renderer.get_texture(terrain_type, size, 0)
            except Exception as e:
                print(f"Fehler im Advanced Renderer für {terrain_type}: {e}")
                # Fallback zu alter Methode
        
        # Fallback: Alte Methode
        cache_key = f"{terrain_type}_{size}"
        
        if cache_key not in self.texture_cache:
            self.texture_cache[cache_key] = self.generate_texture(terrain_type, size)
        
        return self.texture_cache[cache_key]
    
    def generate_texture(self, terrain_type, size=64):
        """Generiert eine neue Textur für einen Terrain-Typ"""
        generators = {
            "grass": self.generate_grass_texture,
            "water": lambda s: self.generate_water_texture(s, "horizontal"),
            "water_h": lambda s: self.generate_water_texture(s, "horizontal"),
            "water_v": lambda s: self.generate_water_texture(s, "vertical"),
            "mountain": self.generate_mountain_texture,
            "forest": self.generate_forest_texture,
            "sand": self.generate_sand_texture,
            "snow": self.generate_snow_texture,
            "stone": self.generate_stone_texture,
            "dirt": self.generate_dirt_texture,
            "road": self.generate_road_texture,
            "village": self.generate_village_texture,
            "empty": self.generate_empty_texture
        }
        
        generator = generators.get(terrain_type, self.generate_empty_texture)
        return generator(size)
    
    def generate_grass_texture(self, size):
        """Gras-Textur wie in Referenzbild - saftiges Grün"""
        # Basis: Saftiges Grün aus Referenzbild
        img = Image.new('RGB', (size, size), (126, 179, 86))
        draw = ImageDraw.Draw(img)
        
        # Organisches Pattern ohne Animation
        random.seed(size)  # Konsistent
        for y in range(0, size, 2):
            for x in range(0, size, 2):
                # Leichte Variation für natürlichen Look
                variation = random.randint(-6, 6)
                color = (
                    max(110, min(140, 126 + variation)),
                    max(165, min(190, 179 + variation)),
                    max(75, min(95, 86 + variation))
                )
                draw.rectangle([(x, y), (x+2, y+2)], fill=color)
        
        # Gras-Details: Dunklere Büschel
        for _ in range(size // 8):
            x = random.randint(0, size-3)
            y = random.randint(0, size-3)
            # Dunklere Gras-Büschel
            draw.ellipse([(x, y), (x+3, y+3)], fill=(100, 150, 70))
        
        # Hellere Highlights
        for _ in range(size // 12):
            x = random.randint(0, size-2)
            y = random.randint(0, size-2)
            draw.point((x, y), fill=(140, 195, 100))
        
        random.seed()  # Reset
        
        # Leichter Smooth für natürlichen Look
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def generate_water_texture(self, size, direction="horizontal"):
        """Professionelle Wasser-Textur - KLARES BLAU"""
        # WICHTIG: Klares helles Blau (nicht graubraun!)
        WATER_COLOR = (65, 155, 230)  # Helles Blau
        
        # Basis: Einheitliche blaue Farbe
        img = Image.new('RGB', (size, size), WATER_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Subtile Wellen-Textur durch Helligkeits-Gradient
        random.seed(size)  # Konsistent
        
        if direction == "horizontal":
            # Horizontale Wellen
            for y in range(size):
                # Sanfte Wellung
                wave = math.sin(y * 0.3) * 6
                for x in range(size):
                    # Helligkeit anpassen - BLAU MUSS DOMINIEREN
                    brightness = int(wave + math.cos(x * 0.2) * 2)
                    
                    r = max(40, min(100, WATER_COLOR[0] + brightness // 2))
                    g = max(130, min(200, WATER_COLOR[1] + brightness))
                    b = max(200, min(255, WATER_COLOR[2] + brightness))
                    
                    draw.point((x, y), fill=(r, g, b))
        else:
            # Vertikale Wellen
            for x in range(size):
                wave = math.sin(x * 0.3) * 6
                for y in range(size):
                    brightness = int(wave + math.cos(y * 0.2) * 2)
                    
                    r = max(40, min(100, WATER_COLOR[0] + brightness // 2))
                    g = max(130, min(200, WATER_COLOR[1] + brightness))
                    b = max(200, min(255, WATER_COLOR[2] + brightness))
                    
                    draw.point((x, y), fill=(r, g, b))
        
        # Glanz-Highlights
        for _ in range(size // 16):
            x = random.randint(1, size - 2)
            y = random.randint(1, size - 2)
            # Heller Glanzpunkt
            draw.ellipse([(x, y), (x + 2, y + 2)], 
                        fill=(min(255, WATER_COLOR[0] + 60),
                              min(255, WATER_COLOR[1] + 60),
                              min(255, WATER_COLOR[2] + 25)))
        
        random.seed()  # Reset
        
        # Leichter Blur für weichen Look
        img = img.filter(ImageFilter.GaussianBlur(0.5))
        
        return img
    
    def generate_mountain_texture(self, size):
        """Fels/Berg wie in Referenzbild - braun-grauer Fels"""
        # Braun-grauer Fels als Basis
        img = Image.new('RGB', (size, size), (139, 125, 107))
        draw = ImageDraw.Draw(img)
        
        # Fels-Struktur mit Pattern
        random.seed(size)
        for y in range(size):
            for x in range(size):
                # Rocky pattern
                noise = ((x * 3 + y * 2) % 15) + random.randint(-3, 3)
                
                if noise < 5:
                    color = (120, 106, 88)   # Dunkler
                elif noise < 10:
                    color = (139, 125, 107)  # Basis
                else:
                    color = (150, 136, 118)  # Heller
                
                draw.point((x, y), fill=color)
        
        # Fels-Kanten und Risse
        for _ in range(size // 10):
            x = random.randint(0, size - 6)
            y = random.randint(0, size - 1)
            length = random.randint(3, 8)
            draw.line([(x, y), (x + length, y)], fill=(100, 90, 75), width=1)
        
        # Vertikale Risse
        for _ in range(size // 15):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 6)
            length = random.randint(3, 8)
            draw.line([(x, y), (x, y + length)], fill=(95, 85, 70), width=1)
        
        random.seed()  # Reset
        
        # Edge enhance für scharfe Kanten
        img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def generate_forest_texture(self, size):
        """Wald wie in Referenzbild - dunkle Baumkronen von oben"""
        # Sehr dunkles Grün als Basis (Waldboden)
        img = Image.new('RGB', (size, size), (46, 90, 28))
        draw = ImageDraw.Draw(img)
        
        # Dunkler Untergrund mit Variation
        random.seed(size)
        for y in range(size):
            for x in range(size):
                variation = random.randint(-5, 5)
                color = (
                    max(40, min(55, 46 + variation)),
                    max(80, min(100, 90 + variation)),
                    max(23, min(35, 28 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Baumkronen-Pattern (überlappend)
        tree_count = size // 6
        
        for i in range(tree_count):
            x = random.randint(3, size - 4)
            y = random.randint(3, size - 4)
            radius = random.randint(3, 6)
            
            # Schatten unter Baum (zuerst, ganz dunkel)
            shadow_color = (15, 45, 10)
            draw.ellipse([(x - radius - 1, y - radius - 1), 
                         (x + radius + 2, y + radius + 2)],
                        fill=shadow_color)
            
            # Baumkrone - dunkles Waldgrün
            crown_variation = random.randint(-8, 8)
            crown_color = (
                max(25, min(45, 30 + crown_variation)),
                max(60, min(90, 75 + crown_variation)),
                max(15, min(30, 20 + crown_variation))
            )
            
            draw.ellipse([(x - radius, y - radius), 
                         (x + radius, y + radius)],
                        fill=crown_color)
            
            # Minimales Highlight (sehr subtil)
            highlight_x = x - radius // 3
            highlight_y = y - radius // 3
            highlight_radius = max(1, radius // 3)
            
            highlight_color = (
                min(255, crown_color[0] + 15),
                min(255, crown_color[1] + 20),
                min(255, crown_color[2] + 10)
            )
            
            draw.ellipse([(highlight_x - highlight_radius, highlight_y - highlight_radius),
                         (highlight_x + highlight_radius, highlight_y + highlight_radius)],
                        fill=highlight_color)
        
        random.seed()  # Reset
        
        # Leichter Blur für natürlichen Look
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def generate_sand_texture(self, size):
        """Generiert eine Sand-Textur"""
        img = Image.new('RGB', (size, size))
        draw = ImageDraw.Draw(img)
        
        base_color = (212, 196, 160)
        
        for y in range(size):
            for x in range(size):
                variation = random.randint(-15, 15)
                final_color = tuple(max(0, min(255, c + variation)) for c in base_color)
                draw.point((x, y), fill=final_color)
        
        # Sand-Körner
        for _ in range(size * 2):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            draw.point((x, y), fill=(200, 180, 140))
        
        img = img.filter(ImageFilter.SMOOTH)
        return img
    
    def generate_snow_texture(self, size):
        """Generiert eine Schnee-Textur"""
        img = Image.new('RGB', (size, size))
        draw = ImageDraw.Draw(img)
        
        base_color = (232, 244, 248)
        
        for y in range(size):
            for x in range(size):
                variation = random.randint(-10, 10)
                final_color = tuple(max(0, min(255, c + variation)) for c in base_color)
                draw.point((x, y), fill=final_color)
        
        # Funkelnde Schneekristalle
        for _ in range(size // 4):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            draw.point((x, y), fill=(255, 255, 255))
        
        img = img.filter(ImageFilter.GaussianBlur(0.5))
        return img
    
    def generate_road_texture(self, size):
        """Generiert eine Straßen-Textur (Kopfsteinpflaster oder Erdweg)"""
        img = Image.new('RGB', (size, size))
        draw = ImageDraw.Draw(img)
        
        # Erdiger Grundton
        base_color = (122, 111, 93)
        
        # Basis mit Variationen
        for y in range(size):
            for x in range(size):
                variation = random.randint(-20, 20)
                final_color = tuple(max(0, min(255, c + variation)) for c in base_color)
                draw.point((x, y), fill=final_color)
        
        # Steinplatten/Kopfsteinpflaster
        stone_size = size // 8
        for i in range(0, size, stone_size):
            for j in range(0, size, stone_size):
                # Leicht versetzte Steine für natürlichen Look
                offset_x = random.randint(-2, 2)
                offset_y = random.randint(-2, 2)
                x1 = i + offset_x
                y1 = j + offset_y
                x2 = x1 + stone_size - 2
                y2 = y1 + stone_size - 2
                
                # Steinfarbe mit Variation
                stone_color = (
                    base_color[0] + random.randint(-15, 15),
                    base_color[1] + random.randint(-15, 15),
                    base_color[2] + random.randint(-15, 15)
                )
                
                if 0 <= x1 < size and 0 <= y1 < size and x2 < size and y2 < size:
                    draw.rectangle([(x1, y1), (x2, y2)], 
                                 fill=stone_color, 
                                 outline=(80, 70, 60))
        
        # Fugen zwischen Steinen dunkler
        for i in range(0, size, stone_size):
            draw.line([(i, 0), (i, size)], fill=(70, 60, 50), width=1)
            draw.line([(0, i), (size, i)], fill=(70, 60, 50), width=1)
        
        # Leichter Blur für natürlicheren Look
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def generate_stone_texture(self, size):
        """Generiert eine Stein-Textur (für Straßen etc.)"""
        img = Image.new('RGB', (size, size))
        draw = ImageDraw.Draw(img)
        
        base_color = (100, 100, 100)
        
        for y in range(size):
            for x in range(size):
                variation = random.randint(-20, 20)
                final_color = tuple(max(0, min(255, c + variation)) for c in base_color)
                draw.point((x, y), fill=final_color)
        
        # Steinplatten-Muster
        for i in range(4):
            for j in range(4):
                x1 = i * size // 4
                y1 = j * size // 4
                x2 = x1 + size // 4 - 2
                y2 = y1 + size // 4 - 2
                draw.rectangle([(x1, y1), (x2, y2)], outline=(60, 60, 60))
        
        return img
    
    def generate_dirt_texture(self, size):
        """Generiert eine Erd-Textur"""
        img = Image.new('RGB', (size, size))
        draw = ImageDraw.Draw(img)
        
        base_color = (139, 111, 71)
        
        for y in range(size):
            for x in range(size):
                variation = random.randint(-20, 20)
                final_color = tuple(max(0, min(255, c + variation)) for c in base_color)
                draw.point((x, y), fill=final_color)
        
        # Kleine Steine
        for _ in range(size // 8):
            x = random.randint(0, size - 1)
            y = random.randint(0, size - 1)
            stone_size = random.randint(1, 2)
            draw.ellipse([(x, y), (x + stone_size, y + stone_size)], 
                        fill=(100, 90, 70))
        
        img = img.filter(ImageFilter.SMOOTH)
        return img
    
    def generate_village_texture(self, size):
        """Dorf/Gebäude wie in Referenzbild - Draufsicht"""
        # Basis: Steinboden/Erde
        img = Image.new('RGB', (size, size), (150, 130, 100))
        draw = ImageDraw.Draw(img)
        
        # Boden-Variation
        random.seed(size)
        for y in range(0, size, 2):
            for x in range(0, size, 2):
                variation = random.randint(-8, 8)
                color = (
                    max(140, min(160, 150 + variation)),
                    max(120, min(140, 130 + variation)),
                    max(90, min(110, 100 + variation))
                )
                draw.rectangle([(x, y), (x+2, y+2)], fill=color)
        
        # Einfaches Gebäude-Symbol (Draufsicht)
        building_size = size // 2
        building_x = size // 4
        building_y = size // 4
        
        # Hauswände (dunkleres Braun)
        draw.rectangle([(building_x, building_y), 
                       (building_x + building_size, building_y + building_size)],
                      fill=(110, 85, 60), outline=(80, 60, 40), width=1)
        
        # Dach-Andeutung (Striche für Textur)
        for i in range(building_x + 2, building_x + building_size - 2, 3):
            draw.line([(i, building_y + 2), (i, building_y + building_size - 2)],
                     fill=(90, 65, 45), width=1)
        
        # Tür (kleines Rechteck)
        door_w = building_size // 4
        door_h = building_size // 3
        door_x = building_x + (building_size - door_w) // 2
        door_y = building_y + building_size - door_h - 2
        draw.rectangle([(door_x, door_y), (door_x + door_w, door_y + door_h)],
                      fill=(60, 40, 25))
        
        random.seed()  # Reset
        
        return img
    
    def generate_empty_texture(self, size):
        """Generiert eine leere/schwarze Textur"""
        img = Image.new('RGB', (size, size), (26, 26, 26))
        return img
    
    def clear_cache(self):
        """Leert den Texture-Cache"""
        self.texture_cache.clear()
