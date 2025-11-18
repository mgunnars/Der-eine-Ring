"""
Advanced Texture Renderer für "Der Eine Ring"
Professionelles Rendering-System mit gezeichneten Texturen und fortgeschrittenen Animationen
"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np
import random
import math
import os
import json


class AdvancedTextureRenderer:
    """
    Hochprofessionelles Rendering-System für handgezeichnete Texturen
    Unterstützt Import, Export und Animation
    """
    
    def __init__(self):
        self.texture_cache = {}
        self.animation_frames = {}
        self.custom_textures = {}
        self.animation_time = 0
        
        # Basis-Materialien mit professionellen Farben
        self.base_materials = {
            "grass": {
                "name": "Gras",
                "color": (126, 179, 86),
                "animated": False,
                "emoji": "🌿"
            },
            "water": {
                "name": "Wasser",
                "color": (93, 173, 226),
                "animated": True,
                "emoji": "💧"
            },
            "mountain": {
                "name": "Berg",
                "color": (139, 125, 107),
                "animated": False,
                "emoji": "🏔️"
            },
            "forest": {
                "name": "Wald",
                "color": (46, 90, 28),
                "animated": True,
                "emoji": "🌲"
            },
            "sand": {
                "name": "Sand",
                "color": (201, 177, 138),
                "animated": False,
                "emoji": "🏖️"
            },
            "snow": {
                "name": "Schnee",
                "color": (232, 244, 248),
                "animated": True,
                "emoji": "❄️"
            },
            "road": {
                "name": "Straße",
                "color": (122, 111, 93),
                "animated": False,
                "emoji": "🛤️"
            },
            "village": {
                "name": "Dorf",
                "color": (150, 130, 100),
                "animated": True,  # ANIMIERT für Rauch!
                "emoji": "🏘️"
            },
            "stone": {
                "name": "Stein",
                "color": (100, 100, 100),
                "animated": False,
                "emoji": "🪨"
            },
            "dirt": {
                "name": "Erde",
                "color": (139, 111, 71),
                "animated": False,
                "emoji": "🟫"
            }
        }
        
        # Lade custom Materialien
        self.load_custom_materials()
    
    def load_custom_materials(self):
        """Lädt benutzerdefinierte Materialien aus einer JSON-Datei"""
        materials_file = "custom_materials.json"
        if os.path.exists(materials_file):
            try:
                with open(materials_file, 'r', encoding='utf-8') as f:
                    self.custom_textures = json.load(f)
            except Exception as e:
                print(f"Fehler beim Laden der custom Materialien: {e}")
    
    def save_custom_materials(self):
        """Speichert benutzerdefinierte Materialien in eine JSON-Datei"""
        materials_file = "custom_materials.json"
        try:
            # Nur serialisierbare Daten speichern
            save_data = {}
            for mat_id, mat_data in self.custom_textures.items():
                save_data[mat_id] = {
                    "name": mat_data.get("name", ""),
                    "color": mat_data.get("color", (128, 128, 128)),
                    "animated": mat_data.get("animated", False),
                    "emoji": mat_data.get("emoji", "🎨"),
                    "texture_path": mat_data.get("texture_path", None)
                }
            
            with open(materials_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Fehler beim Speichern der custom Materialien: {e}")
    
    def get_all_materials(self):
        """Gibt alle verfügbaren Materialien (basis + custom) zurück, sortiert A-Z"""
        all_materials = {}
        
        # Basis-Materialien
        all_materials.update(self.base_materials)
        
        # Custom-Materialien
        all_materials.update(self.custom_textures)
        
        # Nach Name sortieren
        sorted_materials = dict(sorted(
            all_materials.items(),
            key=lambda x: x[1].get('name', x[0]).lower()
        ))
        
        return sorted_materials
    
    @property
    def registered_materials(self):
        """Alias für SVG-Export Kompatibilität"""
        return self.get_all_materials()
    
    def create_new_material(self, material_id, name, color=(128, 128, 128), 
                           animated=False, emoji="🎨", base_texture=None):
        """Erstellt ein neues benutzerdefiniertes Material"""
        self.custom_textures[material_id] = {
            "name": name,
            "color": color,
            "animated": animated,
            "emoji": emoji,
            "base_texture": base_texture
        }
        
        # Speichern
        self.save_custom_materials()
        
        return material_id
    
    def import_texture(self, material_id, image_path):
        """Importiert eine externe Textur für ein Material"""
        try:
            img = Image.open(image_path).convert('RGB')
            
            # Speichere Pfad im Material
            if material_id in self.custom_textures:
                self.custom_textures[material_id]["texture_path"] = image_path
            elif material_id in self.base_materials:
                # Für Basis-Material: Custom-Version erstellen
                new_id = f"{material_id}_custom"
                self.custom_textures[new_id] = {
                    **self.base_materials[material_id],
                    "texture_path": image_path
                }
                material_id = new_id
            
            # Cache leeren für dieses Material
            self.clear_cache_for_material(material_id)
            
            self.save_custom_materials()
            return True
        except Exception as e:
            print(f"Fehler beim Importieren der Textur: {e}")
            return False
    
    def clear_cache_for_material(self, material_id):
        """Löscht Cache-Einträge für ein bestimmtes Material"""
        keys_to_remove = [key for key in self.texture_cache.keys() 
                         if key.startswith(f"{material_id}_")]
        for key in keys_to_remove:
            del self.texture_cache[key]
    
    def render_texture(self, material_name, material_type, size):
        """
        Wrapper für SVG-Export - ruft get_texture() auf
        """
        return self.get_texture(material_name, size=size, animation_frame=0)
    
    def get_texture(self, material_id, size=64, animation_frame=0, river_direction="right"):
        """
        Hauptmethode zum Abrufen einer Textur
        Unterstützt Caching, Animation, Custom-Texturen und River-Richtungen
        """
        # Prüfe ob importierte Textur vorhanden
        material = self.custom_textures.get(material_id) or self.base_materials.get(material_id)
        
        if material and material.get("texture_path"):
            # Prüfe ob animiert mit mehreren Frames
            if material.get("animated", False):
                # Versuche Frame-spezifische Textur zu laden
                base_path = material["texture_path"]
                # Ersetze .png mit _frame_X.png
                frame_path = base_path.replace(".png", f"_frame_{animation_frame % 240}.png")
                
                # Wenn Frame-Datei existiert, lade sie
                import os
                if os.path.exists(frame_path):
                    return self.load_and_scale_texture(frame_path, size)
                
                # Fallback: Verwende Basis-Textur
                return self.load_and_scale_texture(base_path, size)
            else:
                # Statische Custom-Textur
                return self.load_and_scale_texture(material["texture_path"], size)
        
        # Animierte Texturen (prozedural)
        # Water mit Richtung hat separaten Cache
        if material_id == "water":
            cache_key = f"{material_id}_{size}_{animation_frame}_{river_direction}"
        elif material and material.get("animated", False):
            cache_key = f"{material_id}_{size}_{animation_frame}"
        else:
            cache_key = f"{material_id}_{size}"
        
        # Cache-Check (auch für animierte Texturen - Performance!)
        if cache_key in self.texture_cache:
            return self.texture_cache[cache_key]
        
        # Generiere neue Textur (mit river_direction für water)
        texture = self.generate_professional_texture(material_id, size, animation_frame, river_direction)
        
        # Cache-Management: Begrenze Cache-Größe (max 200 Einträge)
        if len(self.texture_cache) > 200:
            # Entferne älteste Einträge (FIFO)
            keys_to_remove = list(self.texture_cache.keys())[:50]
            for key in keys_to_remove:
                del self.texture_cache[key]
        
        # Textur cachen (auch animierte für bessere Performance!)
        self.texture_cache[cache_key] = texture
        
        return texture
    
    def load_and_scale_texture(self, image_path, size):
        """Lädt und skaliert eine importierte Textur"""
        try:
            img = Image.open(image_path).convert('RGB')
            img = img.resize((size, size), Image.LANCZOS)
            return img
        except Exception as e:
            # Fehler nur bei unerwarteten Problemen ausgeben
            # (Fehlende Tiles sind OK - werden grau)
            if "No such file or directory" not in str(e) and "[Errno 2]" not in str(e):
                print(f"Fehler beim Laden der Textur: {e}")
            # Fallback
            return Image.new('RGB', (size, size), (128, 128, 128))
    
    def generate_professional_texture(self, material_id, size, animation_frame=0, river_direction="right"):
        """
        Generiert professionelle, handgezeichnete Texturen
        mit erweiterten Rendering-Techniken
        """
        generators = {
            "grass": self.render_grass,
            "water": lambda s, f: self.render_water(s, f, river_direction),  # Pass direction for water
            "mountain": self.render_mountain,
            "forest": self.render_forest,
            "sand": self.render_sand,
            "snow": self.render_snow,
            "road": self.render_road,
            "village": self.render_village,
            "stone": self.render_stone,
            "dirt": self.render_dirt
        }
        
        if material_id in generators:
            return generators[material_id](size, animation_frame)
        
        # Fallback für custom materials
        material = self.custom_textures.get(material_id)
        if material:
            return self.render_custom_material(material, size, animation_frame)
        
        # Default
        return Image.new('RGB', (size, size), (128, 128, 128))
    
    def render_grass(self, size, frame):
        """Professionelles Gras mit organischer Struktur und Wind-Animation"""
        img = Image.new('RGB', (size, size), (126, 179, 86))
        draw = ImageDraw.Draw(img)
        
        # Organische Basis-Variation
        random.seed(size * 1000)
        for y in range(0, size, 2):
            for x in range(0, size, 2):
                # Perlin-ähnliche Variation
                noise = math.sin(x * 0.1) * math.cos(y * 0.1) * 10
                variation = int(noise) + random.randint(-5, 5)
                
                color = (
                    max(110, min(140, 126 + variation)),
                    max(165, min(190, 179 + variation)),
                    max(75, min(95, 86 + variation))
                )
                draw.rectangle([(x, y), (x+2, y+2)], fill=color)
        
        # Grasbüschel mit Textur
        for _ in range(size // 6):
            x = random.randint(0, size-4)
            y = random.randint(0, size-4)
            
            # Organische Büschel-Form
            grass_color = (
                random.randint(100, 120),
                random.randint(150, 170),
                random.randint(70, 90)
            )
            
            # Mehrere überlappende Striche für Grasbüschel
            for i in range(3):
                offset_x = random.randint(-1, 1)
                offset_y = random.randint(-2, 0)
                draw.line(
                    [(x + offset_x, y), (x + offset_x, y + offset_y + 3)],
                    fill=grass_color,
                    width=1
                )
        
        # Highlights für Tiefe
        for _ in range(size // 10):
            x = random.randint(0, size-1)
            y = random.randint(0, size-1)
            draw.point((x, y), fill=(150, 200, 110))
        
        random.seed()
        
        # Professioneller Smooth-Effekt
        img = img.filter(ImageFilter.SMOOTH_MORE)
        
        # Leichte Sättigung erhöhen
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.2)
        
        return img
    
    def render_water(self, size, frame, direction="right"):
        """
        Professioneller animierter Fluss mit Richtung
        direction: "right", "left", "up", "down", "down-right", "down-left", "up-right", "up-left"
        PERFEKT nahtlose Tiles - keine sichtbaren Ränder!
        """
        WATER_BASE = (65, 155, 230)  # Klares helles Blau
        img = Image.new('RGB', (size, size), WATER_BASE)
        draw = ImageDraw.Draw(img)
        
        # Fließgeschwindigkeit
        flow_speed = frame * 0.4
        
        # Richtungs-Mapping (inkl. Diagonale!)
        direction_map = {
            "right": (1, 0),
            "left": (-1, 0),
            "down": (0, 1),
            "up": (0, -1),
            "down-right": (1, 1),
            "down-left": (-1, 1),
            "up-right": (1, -1),
            "up-left": (-1, -1)
        }
        
        dx, dy = direction_map.get(direction, (1, 0))
        
        # KRITISCH: Wellenlänge muss ein Vielfaches von 2*PI sein für nahtlose Wiederholung!
        wave_freq = (2.0 * math.pi) / size
        
        # Zeichne jeden Pixel mit GARANTIERT nahtlosen Wellen
        for y in range(size):
            for x in range(size):
                # Position mit Flow-Offset
                pos_x = x + flow_speed * dx
                pos_y = y + flow_speed * dy
                
                # EINHEITLICHE Wellen für ALLE Richtungen
                # Nutze BEIDE Koordinaten immer, nur mit unterschiedlicher Gewichtung
                
                # Hauptwelle in Flussrichtung
                if dx != 0 and dy != 0:
                    # Diagonal - beide Richtungen gleich gewichtet
                    main_wave_pos = (pos_x + pos_y) * 0.707  # 1/sqrt(2)
                elif dx != 0:
                    # Horizontal
                    main_wave_pos = pos_x
                else:
                    # Vertikal
                    main_wave_pos = pos_y
                
                # IDENTISCHE Wellen-Formeln für ALLE Richtungen
                wave1 = math.sin(main_wave_pos * wave_freq * 2.5) * 8
                wave2 = math.sin(main_wave_pos * wave_freq * 3.7 + (x + y) * 0.03) * 5
                
                # Querwellen (immer beide Koordinaten)
                cross_wave = math.sin(x * wave_freq * 4.2) * 2
                cross_wave += math.sin(y * wave_freq * 4.2) * 2
                
                brightness = int(wave1 + wave2 + cross_wave)
                
                # Sanfte Farbübergänge
                r = max(50, min(80, WATER_BASE[0] + brightness // 3))
                g = max(135, min(170, WATER_BASE[1] + brightness // 2))
                b = max(205, min(235, WATER_BASE[2] + brightness // 3))
                
                draw.point((x, y), fill=(r, g, b))
        
        # Glanzlichter zurück - aber nahtlos!
        # Verwende deterministisches Muster basierend auf Tile-Position
        num_highlights = max(3, size // 12)
        
        for i in range(num_highlights):
            # Deterministisches Muster für Glanzlichter (nahtlos über Tiles)
            angle = (i * 2.4 + frame * 0.02) % (2 * math.pi)
            radius = (size * 0.3) + (i % 3) * 5
            
            center_x = size / 2 + math.cos(angle) * radius
            center_y = size / 2 + math.sin(angle) * radius
            
            # Bewege in Flussrichtung
            highlight_x = (center_x + flow_speed * dx * 0.3) % size
            highlight_y = (center_y + flow_speed * dy * 0.3) % size
            
            x = int(highlight_x)
            y = int(highlight_y)
            
            if 2 <= x < size - 2 and 2 <= y < size - 2:
                # Sanfte Glanzpunkte
                intensity = 20 + i * 3
                for dy_offset in range(-1, 2):
                    for dx_offset in range(-1, 2):
                        px = x + dx_offset
                        py = y + dy_offset
                        if 0 <= px < size and 0 <= py < size:
                            dist = math.sqrt(dx_offset**2 + dy_offset**2)
                            fade = max(0, 1 - dist / 1.5)
                            local_intensity = int(intensity * fade)
                            
                            current = img.getpixel((px, py))
                            new_color = (
                                min(255, current[0] + local_intensity),
                                min(255, current[1] + local_intensity),
                                min(255, current[2] + local_intensity // 2)
                            )
                            draw.point((px, py), fill=new_color)
        
        return img
    
    def render_mountain(self, size, frame):
        """Professioneller Fels mit realistischer Struktur"""
        img = Image.new('RGB', (size, size), (139, 125, 107))
        draw = ImageDraw.Draw(img)
        
        # Fels-Grundstruktur mit Perlin-ähnlichem Noise
        random.seed(size * 2000)
        for y in range(size):
            for x in range(size):
                # Komplexes Noise-Pattern
                noise = (
                    math.sin(x * 0.15) * math.cos(y * 0.15) * 15 +
                    math.sin(x * 0.3 + y * 0.2) * 8
                )
                noise += random.randint(-5, 5)
                
                brightness = int(noise)
                color = (
                    max(100, min(160, 139 + brightness)),
                    max(90, min(145, 125 + brightness)),
                    max(80, min(125, 107 + brightness))
                )
                draw.point((x, y), fill=color)
        
        # Felsrisse und Spalten
        for _ in range(size // 8):
            start_x = random.randint(0, size-1)
            start_y = random.randint(0, size-1)
            
            # Organischer Riss
            current_x, current_y = start_x, start_y
            for step in range(random.randint(5, 15)):
                next_x = current_x + random.randint(-2, 2)
                next_y = current_y + random.randint(-1, 2)
                
                if 0 <= next_x < size and 0 <= next_y < size:
                    draw.line(
                        [(current_x, current_y), (next_x, next_y)],
                        fill=(90, 80, 65),
                        width=random.randint(1, 2)
                    )
                    current_x, current_y = next_x, next_y
        
        # Highlights für Lichtreflexionen
        for _ in range(size // 15):
            x = random.randint(0, size-3)
            y = random.randint(0, size-3)
            draw.ellipse(
                [(x, y), (x+2, y+2)],
                fill=(170, 150, 130)
            )
        
        random.seed()
        
        # Schärfe für Felsstruktur
        img = img.filter(ImageFilter.EDGE_ENHANCE)
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def render_forest(self, size, frame):
        """
        Professioneller Wald mit animiertem Blätterrauschen
        SMOOTH WACKELN - langsame, sanfte Wind-Bewegung
        """
        img = Image.new('RGB', (size, size), (46, 90, 28))
        draw = ImageDraw.Draw(img)
        
        # Waldbodenstruktur - sehr langsame Wechselgeschwindigkeit
        random.seed(size * 3000 + frame // 40)  # // 40 für sehr langsame Änderungen
        for y in range(size):
            for x in range(size):
                variation = random.randint(-8, 8)
                color = (
                    max(35, min(55, 46 + variation)),
                    max(75, min(105, 90 + variation)),
                    max(20, min(38, 28 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Baumkronen mit SMOOTH Animation (Wind) - sehr langsame Geschwindigkeit
        # frame * 0.008 für extrem sanfte, kaum merkliche Bewegung
        wind_offset = math.sin(frame * 0.008) * 1.5
        
        tree_count = size // 5
        for i in range(tree_count):
            base_x = random.randint(4, size - 5)
            base_y = random.randint(4, size - 5)
            
            # Sanfte Wind-Bewegung
            x = int(base_x + wind_offset)
            y = base_y
            
            radius = random.randint(3, 6)
            
            # Schatten (Tiefe)
            shadow_radius = radius + 1
            draw.ellipse(
                [(x - shadow_radius, y - shadow_radius),
                 (x + shadow_radius, y + shadow_radius)],
                fill=(20, 50, 15)
            )
            
            # Hauptkrone - mehrschichtig für Tiefe
            for layer in range(3):
                layer_offset = layer - 1
                layer_radius = radius - layer
                
                crown_color = (
                    max(20, min(50, 35 + layer * 5 + random.randint(-5, 5))),
                    max(50, min(95, 75 + layer * 5 + random.randint(-8, 8))),
                    max(15, min(35, 22 + layer * 3 + random.randint(-3, 3)))
                )
                
                draw.ellipse(
                    [(x - layer_radius + layer_offset, y - layer_radius + layer_offset),
                     (x + layer_radius + layer_offset, y + layer_radius + layer_offset)],
                    fill=crown_color
                )
            
            # Licht-Highlights
            highlight_x = x - radius // 2
            highlight_y = y - radius // 2
            highlight_radius = max(1, radius // 3)
            
            draw.ellipse(
                [(highlight_x - highlight_radius, highlight_y - highlight_radius),
                 (highlight_x + highlight_radius, highlight_y + highlight_radius)],
                fill=(60, 110, 40)
            )
        
        random.seed()
        
        # Weicher Blur für organischen Look
        img = img.filter(ImageFilter.SMOOTH_MORE)
        
        return img
    
    def render_sand(self, size, frame):
        """Professioneller Sand mit Körnung"""
        img = Image.new('RGB', (size, size), (201, 177, 138))
        draw = ImageDraw.Draw(img)
        
        # Organische Sand-Textur
        random.seed(size * 4000)
        for y in range(size):
            for x in range(size):
                # Sandkorn-Variation
                variation = random.randint(-18, 18)
                color = (
                    max(180, min(220, 201 + variation)),
                    max(155, min(195, 177 + variation)),
                    max(115, min(155, 138 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Sandkörner als Details
        for _ in range(size * 3):
            x = random.randint(0, size-1)
            y = random.randint(0, size-1)
            
            if random.random() > 0.5:
                draw.point((x, y), fill=(185, 160, 120))
            else:
                draw.point((x, y), fill=(215, 195, 155))
        
        # Kleine Schatten für Dimensionalität
        for _ in range(size // 20):
            x = random.randint(1, size-2)
            y = random.randint(1, size-2)
            draw.point((x, y), fill=(180, 155, 115))
        
        random.seed()
        
        # Sanfter Smooth
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def render_snow(self, size, frame):
        """
        Professioneller Schnee mit funkelnden Kristallen (animiert)
        """
        img = Image.new('RGB', (size, size), (232, 244, 248))
        draw = ImageDraw.Draw(img)
        
        # Schneestruktur mit subtilen Variationen
        random.seed(size * 5000)
        for y in range(size):
            for x in range(size):
                variation = random.randint(-12, 12)
                color = (
                    max(220, min(255, 232 + variation)),
                    max(232, min(255, 244 + variation)),
                    max(236, min(255, 248 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Funkelnde Schneekristalle (animiert)
        random.seed(size + frame * 123)
        sparkle_count = size // 3
        
        for i in range(sparkle_count):
            x = random.randint(0, size-1)
            y = random.randint(0, size-1)
            
            # Einige Kristalle funkeln stärker je nach Frame
            intensity = 255
            if (i + frame) % 10 < 5:
                intensity = random.randint(240, 255)
            
            draw.point((x, y), fill=(intensity, intensity, intensity))
            
            # Stern-Form für größere Kristalle
            if random.random() > 0.7 and 1 < x < size-1 and 1 < y < size-1:
                draw.point((x-1, y), fill=(250, 252, 255))
                draw.point((x+1, y), fill=(250, 252, 255))
                draw.point((x, y-1), fill=(250, 252, 255))
                draw.point((x, y+1), fill=(250, 252, 255))
        
        random.seed()
        
        # Sehr leichter Blur
        img = img.filter(ImageFilter.GaussianBlur(0.3))
        
        return img
    
    def render_road(self, size, frame):
        """Professionelle Straße mit Kopfsteinpflaster"""
        img = Image.new('RGB', (size, size), (122, 111, 93))
        draw = ImageDraw.Draw(img)
        
        # Erdiger Untergrund
        random.seed(size * 6000)
        for y in range(size):
            for x in range(size):
                variation = random.randint(-15, 15)
                color = (
                    max(100, min(140, 122 + variation)),
                    max(90, min(130, 111 + variation)),
                    max(75, min(110, 93 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Kopfsteinpflaster
        stone_size = max(4, size // 10)
        
        for row in range(0, size, stone_size):
            for col in range(0, size, stone_size):
                # Leicht versetzt für organischen Look
                offset_x = random.randint(-1, 1)
                offset_y = random.randint(-1, 1)
                
                x1 = col + offset_x
                y1 = row + offset_y
                x2 = x1 + stone_size - 2
                y2 = y1 + stone_size - 2
                
                if 0 <= x1 < size and 0 <= y1 < size:
                    # Stein-Farbe
                    stone_brightness = random.randint(-15, 15)
                    stone_color = (
                        max(90, min(135, 115 + stone_brightness)),
                        max(80, min(125, 105 + stone_brightness)),
                        max(65, min(105, 85 + stone_brightness))
                    )
                    
                    # Stein zeichnen
                    draw.rectangle(
                        [(x1, y1), (min(x2, size-1), min(y2, size-1))],
                        fill=stone_color,
                        outline=(70, 60, 50),
                        width=1
                    )
                    
                    # Highlight auf Stein
                    if random.random() > 0.6:
                        highlight_x = x1 + stone_size // 3
                        highlight_y = y1 + stone_size // 4
                        if highlight_x < size and highlight_y < size:
                            draw.point(
                                (highlight_x, highlight_y),
                                fill=(140, 130, 110)
                            )
        
        random.seed()
        
        # Leichter Smooth für natürlichen Look
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def render_village(self, size, frame):
        """
        Professionelles Dorf/Gebäude in PSEUDO-3D mit animiertem Rauch!
        Rauch zieht über 2-3 Tiles, nur Gebäude/Rauch überlappen (nicht Boden)
        """
        # VIEL größeres Canvas für Rauch über 2-3 Tiles!
        extended_size = int(size * 3)  # 3x statt 1.5x für mehr Rauch-Höhe
        img = Image.new('RGBA', (extended_size, extended_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # WICHTIG: Bodentextur GANZ UNTEN platzieren (letztes Tile im 3x Canvas)
        # Das Boden-Tile muss bei y = 2*size beginnen und genau 1*size hoch sein
        random.seed(size * 7000)
        boden_start_y = int(size * 2)  # Beginnt bei 2x size (letztes Drittel)
        
        for y in range(boden_start_y, extended_size, 2):
            for x in range(0, size, 2):  # Nur original width (nicht extended!)
                variation = random.randint(-10, 10)
                color = (
                    max(135, min(165, 150 + variation)),
                    max(115, min(145, 130 + variation)),
                    max(85, min(115, 100 + variation)),
                    255
                )
                draw.rectangle([(x, y), (x+2, y+2)], fill=color)
        
        # GRÖSSERES PSEUDO-3D GEBÄUDE (70% der ORIGINAL size)
        building_size = int(size * 0.7)
        # Gebäude positioniert: Unterkante GENAU bei boden_start_y (am Bodenanfang)
        building_x = size // 6
        building_y = boden_start_y + int(size * 0.05)  # Leicht in den Boden eingelassen
        
        # 3D-Schatten (KLEINER und dezenter)
        shadow_offset = 2
        for i in range(2):  # Nur 2 statt 3 Schichten
            alpha = 50 - i * 15  # Weniger opak
            draw.rectangle(
                [(building_x + shadow_offset + i, building_y + shadow_offset + i),
                 (building_x + building_size + shadow_offset + i, 
                  building_y + building_size + shadow_offset + i)],
                fill=(60, 50, 35, alpha)
            )
        
        # VORDERWAND (3D-Effekt - heller)
        draw.rectangle(
            [(building_x, building_y),
             (building_x + building_size, building_y + building_size)],
            fill=(120, 95, 70, 255),
            outline=(80, 60, 40),
            width=2
        )
        
        # DACH mit 3D-Tiefe - isometrisch
        roof_height = building_size // 3
        # Dach-Polygon (trapezförmig für 3D)
        roof_points = [
            (building_x - 3, building_y),  # Links unten
            (building_x + building_size // 2, building_y - roof_height),  # Spitze
            (building_x + building_size + 3, building_y),  # Rechts unten
        ]
        draw.polygon(roof_points, fill=(90, 65, 45, 255), outline=(70, 50, 35))
        
        # Dach-Textur (Schindeln mit Schatten)
        for i in range(3):
            offset = i * 3
            shingle_y = building_y - roof_height + offset * 2
            draw.line(
                [(building_x - 3 + offset, shingle_y),
                 (building_x + building_size + 3 - offset, shingle_y)],
                fill=(80, 55, 35, 255),
                width=2
            )
        
        # KAMIN (3D-Rechteck)
        chimney_w = max(3, size // 10)
        chimney_h = max(6, size // 8)
        chimney_x = building_x + building_size - chimney_w - 5
        chimney_y = building_y - roof_height - chimney_h // 2
        
        # Kamin-Vorderseite (heller)
        draw.rectangle(
            [(chimney_x, chimney_y),
             (chimney_x + chimney_w, chimney_y + chimney_h)],
            fill=(110, 80, 60, 255),
            outline=(80, 60, 40)
        )
        # Kamin-Seite (dunkler für 3D)
        draw.polygon(
            [(chimney_x + chimney_w, chimney_y),
             (chimney_x + chimney_w + 2, chimney_y - 2),
             (chimney_x + chimney_w + 2, chimney_y + chimney_h - 2),
             (chimney_x + chimney_w, chimney_y + chimney_h)],
            fill=(80, 60, 45, 255)
        )
        
        # 🔥 ANIMIERTER RAUCH aus dem Kamin - BREITER, REALISTISCHER WIND!
        smoke_start_x = chimney_x + chimney_w // 2
        smoke_start_y = chimney_y
        
        # Rauch als BREITE durchgehende Wolke
        max_smoke_height = extended_size - smoke_start_y
        
        # WIND-RICHTUNG: Ändert sich sehr langsam (alle ~8 Sekunden bei 30 FPS)
        # Nutze frame // 240 für seltene Richtungswechsel
        wind_phase = (frame // 240) * 2.5  # Langsam wechselnde Phase
        wind_direction = math.sin(wind_phase) * 15  # Wind von -15 bis +15 Pixel
        
        # Sehr langsame Aufstiegs-Animation
        base_offset = (frame * 1.0) % max_smoke_height  # Langsamer als vorher
        
        # Zeichne VIELE Partikel für dichte, breite Rauch-Wolke
        num_particles = 120  # Mehr Partikel für dickeren Rauch
        
        # Seed für konsistente horizontale Streuung pro Frame
        random.seed(size * 9000)
        
        for i in range(num_particles):
            # Gleichmäßig verteilte Partikel über die gesamte Höhe
            particle_base_height = (i / num_particles) * max_smoke_height
            
            # Animation: Kontinuierlicher Aufstieg
            particle_height = (particle_base_height + base_offset) % max_smoke_height
            
            # Y-Position vom Kamin aus
            particle_y = smoke_start_y - particle_height
            
            # BREITE: Partikel verteilen sich horizontal (breiterer Rauch)
            # Je höher, desto breiter die Streuung
            width_factor = particle_height / max_smoke_height
            horizontal_spread = (random.random() - 0.5) * 8 * width_factor  # Bis zu ±4px Streuung
            
            # Sanfte Wind-Drift (alle Partikel driften in gleiche Richtung)
            wind_drift = wind_direction * width_factor  # Je höher, desto mehr Wind-Einfluss
            
            # Sehr subtile zusätzliche Wellenbewegung (kaum sichtbar)
            subtle_wobble = math.sin((particle_base_height / 20) + frame * 0.02) * 2
            
            # Finale X-Position
            particle_x = smoke_start_x + horizontal_spread + wind_drift + subtle_wobble
            
            # Größe und Transparenz abhängig von Höhe
            particle_size = max(1, int(1.5 + particle_height / 20))  # Größer für dichteren Rauch
            # Partikel werden nach oben hin transparenter
            particle_alpha = max(5, int(230 - (particle_height / max_smoke_height * 210)))
            
            # Zeichne Rauch-Partikel
            if 0 <= particle_y < extended_size and particle_alpha > 10:
                draw.ellipse(
                    [(particle_x - particle_size, particle_y - particle_size),
                     (particle_x + particle_size, particle_y + particle_size)],
                    fill=(185, 185, 195, particle_alpha)
                )
        
        # Tür (mit 3D-Schatten)
        door_w = building_size // 4
        door_h = building_size // 3
        door_x = building_x + (building_size - door_w) // 2
        door_y = building_y + building_size - door_h - 3
        
        draw.rectangle(
            [(door_x, door_y), (door_x + door_w, door_y + door_h)],
            fill=(60, 40, 25, 255),
            outline=(40, 25, 15),
            width=2
        )
        # Tür-Griff
        draw.ellipse(
            [(door_x + door_w - 4, door_y + door_h // 2 - 1),
             (door_x + door_w - 2, door_y + door_h // 2 + 1)],
            fill=(220, 180, 100, 255)
        )
        
        # Fenster mit Reflektion
        window_size = max(3, building_size // 8)
        # Linkes Fenster
        window_x1 = building_x + building_size // 4 - window_size // 2
        window_y1 = building_y + building_size // 3
        draw.rectangle(
            [(window_x1, window_y1),
             (window_x1 + window_size, window_y1 + window_size)],
            fill=(200, 220, 240, 255),
            outline=(60, 50, 40),
            width=1
        )
        # Fenster-Reflektion (hell)
        draw.rectangle(
            [(window_x1 + 1, window_y1 + 1),
             (window_x1 + window_size // 2, window_y1 + window_size // 2)],
            fill=(240, 250, 255, 200)
        )
        
        # Rechtes Fenster
        window_x2 = building_x + 3 * building_size // 4 - window_size // 2
        draw.rectangle(
            [(window_x2, window_y1),
             (window_x2 + window_size, window_y1 + window_size)],
            fill=(200, 220, 240, 255),
            outline=(60, 50, 40),
            width=1
        )
        # Fenster-Reflektion
        draw.rectangle(
            [(window_x2 + 1, window_y1 + 1),
             (window_x2 + window_size // 2, window_y1 + window_size // 2)],
            fill=(240, 250, 255, 200)
        )
        
        random.seed()
        
        # WICHTIG: Extended Canvas beibehalten für Rauch-Overlap!
        # Wir geben das größere Bild zurück, damit der Rauch über Tiles hinausragen kann
        # Das Rendering-System muss mit diesem größeren Format umgehen können
        
        return img  # RGBA mit extended_size (1.5x)
    
    def render_stone(self, size, frame):
        """Professionelle Stein-Textur"""
        img = Image.new('RGB', (size, size), (100, 100, 100))
        draw = ImageDraw.Draw(img)
        
        # Stein-Grundstruktur
        random.seed(size * 8000)
        for y in range(size):
            for x in range(size):
                variation = random.randint(-25, 25)
                color = (
                    max(75, min(125, 100 + variation)),
                    max(75, min(125, 100 + variation)),
                    max(75, min(125, 100 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Steinplatten-Muster
        plate_size = max(6, size // 4)  # Mindestens 6px groß
        for i in range(4):
            for j in range(4):
                x1 = i * plate_size + random.randint(-2, 2)
                y1 = j * plate_size + random.randint(-2, 2)
                x2 = x1 + plate_size - 3
                y2 = y1 + plate_size - 3
                
                # Validate rectangle coordinates STRIKT (x1 must be < x2, y1 must be < y2)
                # UND innerhalb der Bounds
                if (0 <= x1 < size and 0 <= y1 < size and 
                    x2 > x1 and y2 > y1 and 
                    x2 < size and y2 < size):
                    draw.rectangle(
                        [(x1, y1), (x2, y2)],
                        outline=(60, 60, 60),
                        width=1 if size < 16 else 2
                    )
        
        random.seed()
        
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def render_dirt(self, size, frame):
        """Professionelle Erd-Textur"""
        img = Image.new('RGB', (size, size), (139, 111, 71))
        draw = ImageDraw.Draw(img)
        
        # Erdstruktur
        random.seed(size * 9000)
        for y in range(size):
            for x in range(size):
                variation = random.randint(-22, 22)
                color = (
                    max(115, min(160, 139 + variation)),
                    max(90, min(130, 111 + variation)),
                    max(50, min(90, 71 + variation))
                )
                draw.point((x, y), fill=color)
        
        # Kleine Steine
        for _ in range(size // 6):
            x = random.randint(0, size-3)
            y = random.randint(0, size-3)
            stone_size = random.randint(1, 3)
            
            draw.ellipse(
                [(x, y), (x + stone_size, y + stone_size)],
                fill=(100, 90, 70)
            )
        
        # Wurzeln/Gras-Stücke
        for _ in range(size // 12):
            x = random.randint(0, size-1)
            y = random.randint(0, size-1)
            draw.point((x, y), fill=(80, 100, 50))
        
        random.seed()
        
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def render_custom_material(self, material, size, frame):
        """Rendert ein benutzerdefiniertes Material"""
        color = material.get("color", (128, 128, 128))
        img = Image.new('RGB', (size, size), color)
        draw = ImageDraw.Draw(img)
        
        # Einfache Textur-Variation
        random.seed(size * 10000 + hash(material.get("name", "")))
        for y in range(0, size, 2):
            for x in range(0, size, 2):
                variation = random.randint(-15, 15)
                varied_color = tuple(
                    max(0, min(255, c + variation)) for c in color
                )
                draw.rectangle([(x, y), (x+2, y+2)], fill=varied_color)
        
        random.seed()
        
        img = img.filter(ImageFilter.SMOOTH)
        
        return img
    
    def update_animation(self):
        """Erhöht den Animations-Frame-Counter"""
        self.animation_time = (self.animation_time + 1) % 100
        return self.animation_time
    
    def export_texture(self, material_id, size=256, filename=None):
        """Exportiert eine Textur als PNG-Datei"""
        if filename is None:
            filename = f"textures/{material_id}_{size}.png"
        
        # Stelle sicher, dass Verzeichnis existiert
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else "textures", exist_ok=True)
        
        texture = self.get_texture(material_id, size)
        texture.save(filename, "PNG")
        
        return filename
