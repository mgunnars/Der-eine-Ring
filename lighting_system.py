"""
Dynamic Lighting System für 2.5D VTT
Echtzeit-Beleuchtung mit Lichtquellen, Farbeffekten und Falloff
"""
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
import math
from typing import List, Tuple, Dict, Optional
import json
import numpy as np

class LightSource:
    """Einzelne Lichtquelle mit physikalischen Eigenschaften"""
    def __init__(self, x: int, y: int, radius: int = 5, 
                 color: Tuple[int, int, int] = (255, 255, 200),
                 intensity: float = 1.0,
                 flicker: bool = False,
                 light_type: str = "point"):
        """
        Args:
            x, y: Position in Tiles
            radius: Leuchtradius in Tiles
            color: RGB Farbe des Lichts (255,255,200 = warmes Licht)
            intensity: Helligkeit 0.0-1.0
            flicker: Ob Licht flackert (Fackel-Effekt)
            light_type: "point", "torch", "candle", "window", "magic", "fire", "campfire"
        """
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity
        self.flicker = flicker
        self.light_type = light_type
        self.flicker_offset = 0.0
        
        # Physikalische Parameter basierend auf Lichtquelle-Typ
        self._setup_light_physics()
    
    def _setup_light_physics(self):
        """Konfiguriere physikalische Parameter basierend auf Lichttyp"""
        # Standard-Werte
        self.falloff_exponent = 2.0  # Inverse-square-law
        self.core_brightness = 1.2   # Kern-Helligkeit (kann >1 sein für bloom)
        self.flicker_frequency = 0.0
        self.flicker_amplitude = 0.0
        self.flicker_chaos = 0.0     # Zufälligkeit
        
        # Typ-spezifische Parameter
        if self.light_type in ["torch", "fire", "campfire"]:
            # Fackel/Feuer: Stark flackernd, sehr intensiv im Kern
            self.falloff_exponent = 2.5  # Stärker abfallend
            self.core_brightness = 1.5
            self.flicker_frequency = 15.0  # Sehr schnelles Flackern (Hz)
            self.flicker_amplitude = 0.25  # Große Schwankungen
            self.flicker_chaos = 0.35
            
        elif self.light_type == "candle":
            # Kerze: Sanftes Flackern, weicher Kern
            self.falloff_exponent = 2.2
            self.core_brightness = 1.3
            self.flicker_frequency = 8.0   # Mittleres Flackern
            self.flicker_amplitude = 0.15
            self.flicker_chaos = 0.12
            
        elif self.light_type == "magic":
            # Magie: Pulsierend, konstante Wellen
            self.falloff_exponent = 1.8  # Sanfter Falloff
            self.core_brightness = 1.6   # Sehr hell
            self.flicker_frequency = 4.0   # Langsames Pulsieren
            self.flicker_amplitude = 0.20
            self.flicker_chaos = 0.05    # Wenig Chaos
            
        elif self.light_type == "window":
            # Fenster/Tageslicht: Fast konstant
            self.falloff_exponent = 1.5  # Sehr sanft
            self.core_brightness = 1.0
            self.flicker_frequency = 1.0   # Minimales Flackern (Wind)
            self.flicker_amplitude = 0.05
            self.flicker_chaos = 0.02
            
        elif self.light_type == "moonlight":
            # Mondlicht: Komplett konstant
            self.falloff_exponent = 1.2  # Sehr weich
            self.core_brightness = 0.8
            self.flicker_frequency = 0.0
            self.flicker_amplitude = 0.0
            self.flicker_chaos = 0.0
            
        else:  # "point" oder andere
            # Standard Lichtquelle
            self.falloff_exponent = 2.0
            self.core_brightness = 1.2
            self.flicker_frequency = 0.0
            self.flicker_amplitude = 0.0
            self.flicker_chaos = 0.0
        
    def get_current_intensity(self, time_offset: float = 0.0) -> float:
        """Berechne aktuelle Intensität mit physikalisch korrektem Flackern"""
        if not self.flicker or self.flicker_frequency == 0.0:
            return self.intensity
        
        import random
        
        # Basis-Welle (Hauptfrequenz)
        # time_offset ist in Sekunden, flicker_frequency in Hz
        main_wave = math.sin(time_offset * self.flicker_frequency * math.pi * 2)
        
        # Harmonische (höhere Frequenzen für Detailreichtum)
        harmonic1 = math.sin(time_offset * self.flicker_frequency * 2.3 * math.pi * 2) * 0.3
        harmonic2 = math.sin(time_offset * self.flicker_frequency * 3.7 * math.pi * 2) * 0.15
        
        # Perlin-artiges Chaos (langsame Drift)
        slow_drift = math.sin(time_offset * 0.5 * math.pi * 2) * 0.1
        
        # Zufälliges Rauschen (Chaos)
        chaos = random.uniform(-1, 1) * self.flicker_chaos
        
        # Kombiniere alle Komponenten
        combined_flicker = (
            main_wave * 0.5 +
            harmonic1 * 0.3 +
            harmonic2 * 0.15 +
            slow_drift * 0.05 +
            chaos
        )
        
        # Skaliere mit Amplitude
        flicker_amount = combined_flicker * self.flicker_amplitude
        
        # Spezielle Effekte für bestimmte Lichttypen
        if self.light_type in ["torch", "fire", "campfire"]:
            # Gelegentliche "Aussetzer" (Feuer sackt kurz ab)
            if random.random() < 0.03:  # 3% Chance pro Frame
                flicker_amount -= random.uniform(0.2, 0.4)
            
            # Extra "Funken" (kurze helle Spitzen)
            if random.random() < 0.02:  # 2% Chance
                flicker_amount += random.uniform(0.3, 0.5)
        
        # Finale Intensität berechnen
        final_intensity = self.intensity + flicker_amount
        
        # Clamp auf sinnvolle Werte (verschiedene Minima je nach Typ)
        if self.light_type in ["torch", "fire", "campfire"]:
            min_intensity = 0.25  # Feuer kann sehr dunkel werden
        elif self.light_type == "candle":
            min_intensity = 0.60  # Kerzen bleiben relativ stabil
        else:
            min_intensity = 0.40
        
        return max(min_intensity, min(1.5, final_intensity))  # Erlaubt kurze Überhellung
        
    def get_light_at_position(self, px: int, py: int, time_offset: float = 0.0) -> Tuple[int, int, int, int]:
        """
        Berechne Lichtfarbe an Position mit physikalisch korrektem Falloff
        Returns: (R, G, B, A) mit Alpha als Intensität
        """
        import random
        
        # Distanz zur Lichtquelle (in Tiles)
        dx = px - self.x
        dy = py - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Hard Cutoff am Radius (Performance)
        if distance > self.radius:
            return (0, 0, 0, 0)
        
        # Physikalisch korrekter Falloff: I = I₀ / (1 + (d/r)ⁿ)
        # n = falloff_exponent (Standard 2.0 für Inverse-Square-Law)
        normalized_distance = distance / self.radius
        falloff = 1.0 / (1.0 + normalized_distance ** self.falloff_exponent)
        
        # Kern-Bereich (innerste 10%) ist überhell für Bloom-Effekt
        if distance < self.radius * 0.1:
            falloff = min(1.0, falloff * self.core_brightness)
        
        # Aktuelle Intensität (mit Flackern)
        current_intensity = self.get_current_intensity(time_offset)
        
        # Finale Intensität
        final_intensity = falloff * current_intensity
        
        # DYNAMISCHER FARB-SHIFT basierend auf Lichttyp und Distanz
        base_color = self.color
        
        if self.light_type in ["torch", "fire", "campfire"]:
            # Feuer: Realistischer Farbverlauf (Weiß→Gelb→Orange→Rot)
            # Physik: Heißer Kern (weiß), kühlere Außenbereiche (rot)
            
            # Zeit-basierter Farbshift (Flackern der Farbe)
            color_wave = math.sin(time_offset * 4.0 + distance * 1.2) * 0.08
            
            # Distanz-basierte Farbtemperatur
            dist_factor = normalized_distance
            
            if dist_factor < 0.15:  # Kern: Weißglühend
                r = int(min(255, 255 * (1.0 + color_wave)))
                g = int(min(255, 245 * (1.0 + color_wave)))
                b = int(min(255, 220 * (1.0 + color_wave * 0.5)))
            elif dist_factor < 0.40:  # Innen: Helles Gelb-Orange
                r = int(min(255, 255 * (1.0 + color_wave * 0.5)))
                g = int(min(255, 200 * (1.0 + color_wave * 0.3)))
                b = int(min(255, 80 * (1.0 - color_wave * 0.5)))
            elif dist_factor < 0.70:  # Mitte: Orange
                r = int(min(255, 255 * (0.95 + color_wave * 0.2)))
                g = int(min(255, 140 * (1.0 + color_wave * 0.2)))
                b = int(40)
            else:  # Außen: Dunkelrot
                r = int(180 * (1.0 + color_wave * 0.2))
                g = int(60 * (1.0 - dist_factor * 0.3))
                b = int(20)
            
            # Zufällige Funken (nur im inneren Bereich)
            if random.random() < 0.015 and dist_factor < 0.5:
                spark_boost = random.uniform(50, 120)
                r = min(255, r + int(spark_boost))
                g = min(255, g + int(spark_boost * 0.6))
        
        elif self.light_type == "candle":
            # Kerze: Sanftes warmes Gelb mit subtilen Variationen
            warmth_wave = math.sin(time_offset * 2.5) * 0.06
            r = int(min(255, base_color[0] * (1.0 + warmth_wave)))
            g = int(min(255, base_color[1] * (1.0 + warmth_wave * 0.8)))
            b = int(min(255, base_color[2] * (1.0 - warmth_wave * 0.2)))
        
        elif self.light_type == "magic":
            # Magie: Pulsierender Farbshift mit Regenbogen-Effekt
            hue_time = time_offset * 2.0
            r = int(min(255, base_color[0] * (1.0 + math.sin(hue_time) * 0.3)))
            g = int(min(255, base_color[1] * (1.0 + math.sin(hue_time + 2.1) * 0.3)))
            b = int(min(255, base_color[2] * (1.0 + math.sin(hue_time + 4.2) * 0.3)))
        
        elif self.light_type == "window":
            # Tageslicht: Leicht bläulicher Shift
            r = int(base_color[0] * 0.95)
            g = int(base_color[1])
            b = int(min(255, base_color[2] * 1.05))
        
        else:
            # Standard: Direkte Farbe
            r = int(base_color[0])
            g = int(base_color[1])
            b = int(base_color[2])
        
        # Intensität anwenden
        r = int(r * final_intensity)
        g = int(g * final_intensity)
        b = int(b * final_intensity)
        
        a = int(255 * final_intensity)
        
        return (r, g, b, a)
        
    def to_dict(self) -> Dict:
        """Export als Dictionary"""
        return {
            "x": self.x,
            "y": self.y,
            "radius": self.radius,
            "color": self.color,
            "intensity": self.intensity,
            "flicker": self.flicker,
            "light_type": self.light_type
        }
        
    @staticmethod
    def from_dict(data: Dict) -> 'LightSource':
        """Import aus Dictionary"""
        return LightSource(
            x=data["x"],
            y=data["y"],
            radius=data.get("radius", 5),
            color=tuple(data.get("color", [255, 255, 200])),
            intensity=data.get("intensity", 1.0),
            flicker=data.get("flicker", False),
            light_type=data.get("light_type", "point")
        )


class LightingEngine:
    """Verwaltet alle Lichtquellen und rendert Beleuchtung"""
    def __init__(self):
        self.lights: List[LightSource] = []
        self.ambient_color = (30, 30, 40)  # Dunkles Blau für Nacht
        self.ambient_intensity = 0.2  # Basis-Helligkeit
        self.enabled = True
        self.time_offset = 0.0  # Für Animationen
        self.global_radius_scale = 1.0  # Manueller Radius-Multiplikator
        
        # Tag/Nacht-System
        self.lighting_mode = "night"  # "day", "night", "custom"
        self.darkness_opacity = 0.85  # Wie dunkel sind unbeleuchtete Bereiche (0=hell, 1=schwarz)
        
        # Darkness-Polygone (für Tag-Modus: definiere Innenräume)
        self.darkness_polygons: List[List[Tuple[int, int]]] = []  # Liste von Polygon-Punkten [(x,y), ...]
        
    def add_light(self, light: LightSource):
        """Füge Lichtquelle hinzu"""
        self.lights.append(light)
        
    def remove_light(self, index: int):
        """Entferne Lichtquelle"""
        if 0 <= index < len(self.lights):
            del self.lights[index]
            
    def get_light_at(self, x: int, y: int, tolerance: int = 1) -> Optional[int]:
        """Finde Lichtquelle an Position (gibt Index zurück)"""
        for i, light in enumerate(self.lights):
            if abs(light.x - x) <= tolerance and abs(light.y - y) <= tolerance:
                return i
        return None
        
    def clear_lights(self):
        """Entferne alle Lichtquellen"""
        self.lights.clear()
        
    def render_lighting(self, width: int, height: int, tile_size: int, time_offset: float = 0.0, radius_scale: float = 1.0) -> Image.Image:
        """
        Rendere Beleuchtungs-Overlay mit farbigem Licht und Dunkelheit
        Args:
            time_offset: Zeit für Flicker-Animation
            radius_scale: Skalierungsfaktor für Lichtradien (abhängig von Tile-Größe)
        Returns: RGBA Image mit farbigem Licht und Schatten
        """
        self.time_offset = time_offset
        
        img_width = width * tile_size
        img_height = height * tile_size
        
        if not self.enabled or not self.lights:
            # Keine Beleuchtung aktiv
            if self.lighting_mode == "day":
                # Tagesszene ohne Lichter = normal sichtbar
                return Image.new('RGBA', (img_width, img_height), (255, 255, 255, 0))
            else:
                # Nachtszene ohne Lichter = ambient darkness
                ambient = int(self.ambient_intensity * 255)
                darkness = Image.new('RGB', (img_width, img_height), (ambient, ambient, ambient))
                return darkness.convert('RGBA')
        
        # Erstelle Licht-Layer (additiv)
        light_layer = Image.new('RGB', (img_width, img_height), (0, 0, 0))
        pixels = light_layer.load()
        
        # Zeichne jede Lichtquelle mit realistischem Gradient
        for light in self.lights:
            cx = int(light.x * tile_size + tile_size / 2)
            cy = int(light.y * tile_size + tile_size / 2)
            # WICHTIG: Radius mit radius_scale UND global_radius_scale skalieren!
            final_radius_scale = radius_scale * self.global_radius_scale
            radius_px = int(light.radius * tile_size * final_radius_scale)
            
            # Aktuelle Intensität mit Flackern
            current_intensity = light.get_current_intensity(time_offset)
            
            # Zeichne Licht pixelweise für sanften, natürlichen Falloff
            for dy in range(-radius_px, radius_px + 1):
                for dx in range(-radius_px, radius_px + 1):
                    px = cx + dx
                    py = cy + dy
                    
                    if px < 0 or px >= img_width or py < 0 or py >= img_height:
                        continue
                    
                    # Distanz zum Lichtzentrum
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance > radius_px:
                        continue
                    
                    # Distanz normalisiert (0 = Zentrum, 1 = Rand)
                    dist_norm = distance / radius_px
                    
                    # Physikalischer Falloff mit extra Weichheit
                    # Kombiniere Inverse-Square mit Gaussian für natürlichen Look
                    inv_square = 1.0 / (1.0 + (dist_norm ** light.falloff_exponent) * 1.5)
                    gaussian = math.exp(-(dist_norm ** 2) * 2.0)
                    falloff = inv_square * 0.6 + gaussian * 0.4  # Mischung
                    
                    # Finale Intensität
                    intensity = falloff * current_intensity
                    
                    if intensity < 0.01:
                        continue
                    
                    # FARBIGES LICHT basierend auf Lichttyp und Distanz
                    if light.light_type in ["torch", "fire", "campfire"]:
                        # Feuer: Farbgradient von Weiß (Kern) über Gelb zu Orange/Rot (Rand)
                        if dist_norm < 0.15:
                            # Kern: Sehr hell, fast weiß mit leichtem Gelb
                            r = 255
                            g = 250
                            b = 230
                        elif dist_norm < 0.4:
                            # Innen: Helles Gelb-Orange
                            r = 255
                            g = int(220 - dist_norm * 100)
                            b = int(150 - dist_norm * 200)
                        elif dist_norm < 0.7:
                            # Mitte: Orange
                            r = int(255 - dist_norm * 50)
                            g = int(140 - dist_norm * 60)
                            b = int(50 - dist_norm * 30)
                        else:
                            # Außen: Dunkles Orange-Rot
                            r = int(200 - dist_norm * 50)
                            g = int(80 - dist_norm * 40)
                            b = 20
                    
                    elif light.light_type == "candle":
                        # Kerze: Warmes Gelb
                        r = 255
                        g = int(230 - dist_norm * 30)
                        b = int(180 - dist_norm * 80)
                    
                    elif light.light_type == "magic":
                        # Magie: Kühles Lila/Blau (pulsierend)
                        hue_shift = math.sin(time_offset * 2.0) * 0.2
                        r = int((180 + hue_shift * 40) * (1.0 - dist_norm * 0.5))
                        g = int((120 + hue_shift * 30) * (1.0 - dist_norm * 0.5))
                        b = int((255 + hue_shift * 20) * (1.0 - dist_norm * 0.3))
                    
                    elif light.light_type == "window":
                        # Tageslicht: Kühles Blau-Weiß
                        r = int(220 - dist_norm * 20)
                        g = int(235 - dist_norm * 35)
                        b = 255
                    
                    elif light.light_type == "moonlight":
                        # Mondlicht: Sehr kühles Blau
                        r = int(180 - dist_norm * 60)
                        g = int(200 - dist_norm * 50)
                        b = int(235 - dist_norm * 35)
                    
                    else:
                        # Standard: Neutral weiß
                        bright = int(255 * (1.0 - dist_norm * 0.3))
                        r = g = b = bright
                    
                    # Wende Intensität an
                    r = int(r * intensity)
                    g = int(g * intensity)
                    b = int(b * intensity)
                    
                    # Additive Blending (Licht addiert sich)
                    old_r, old_g, old_b = pixels[px, py]
                    pixels[px, py] = (
                        min(255, old_r + r),
                        min(255, old_g + g),
                        min(255, old_b + b)
                    )
        
        # EXTREM STARKER Blur für völlig verwischtes, diffuses Licht
        # 3 Blur-Pässe mit steigender Intensität um ALLE Geometrien zu entfernen
        blur_strength = max(int(tile_size * final_radius_scale * 1.2), 15)  # 3x stärker!
        
        # Pass 1: Starker Basis-Blur
        light_layer = light_layer.filter(ImageFilter.GaussianBlur(radius=blur_strength))
        
        # Pass 2: Mittlerer Blur für sanfte Übergänge
        light_layer = light_layer.filter(ImageFilter.GaussianBlur(radius=blur_strength // 2))
        
        # Pass 3: Feiner Blur für ultra-weiche Ränder
        light_layer = light_layer.filter(ImageFilter.GaussianBlur(radius=blur_strength // 4))
        
        # Addiere Ambient Light zum beleuchteten Bereich
        if self.ambient_intensity > 0:
            ambient = int(self.ambient_intensity * 255)
            ambient_layer = Image.new('RGB', (img_width, img_height), (ambient, ambient, ambient))
            # Kombiniere: max(ambient, light)
            light_layer = ImageChops.lighter(light_layer, ambient_layer)
        
        # TAG/NACHT-MODI: Unterschiedliche Rendering-Strategien
        if self.lighting_mode == "day":
            # TAGESMODUS: Dunkle Polygone (Innenräume) mit Licht-Ausschnitten
            if not self.darkness_polygons:
                # KEINE Dunkel-Bereiche definiert = NUR Lichtquellen als Highlights
                # Komplett transparent, keine Dunkelheit!
                light_rgba = light_layer.convert('RGBA')
                # Mache Lichtquellen sichtbar aber nicht zu dominant
                alpha = light_layer.convert('L')
                # Reduziere Alpha für subtileren Effekt im Tag-Modus
                alpha = alpha.point(lambda p: int(p * 0.3))  # 30% Intensität
                light_rgba.putalpha(alpha)
                return light_rgba
            
            # Erstelle Darkness-Mask nur für definierte Polygone
            darkness_mask = Image.new('L', (img_width, img_height), 0)  # 0 = transparent
            draw = ImageDraw.Draw(darkness_mask)
            
            # Zeichne Dunkelheits-Polygone (255 = opak/dunkel)
            for polygon in self.darkness_polygons:
                # Konvertiere Tile-Koordinaten zu Pixel-Koordinaten
                pixel_poly = [(int(x * tile_size), int(y * tile_size)) for x, y in polygon]
                draw.polygon(pixel_poly, fill=255)
            
            # DEBUG: Prüfe ob Polygon gezeichnet wurde
            import numpy as np
            mask_array = np.array(darkness_mask)
            nonzero_pixels = np.count_nonzero(mask_array)
            print(f"🔍 Darkness-Mask: {nonzero_pixels} pixels mit Dunkelheit (von {img_width}×{img_height})")
            
            # Licht "schneidet" Löcher in die Dunkelheit
            # light_layer ist RGB - konvertiere zu Grayscale für Helligkeit
            light_mask = light_layer.convert('L')
            
            # DEBUG: Prüfe Light-Mask
            light_array = np.array(light_mask)
            light_bright = np.count_nonzero(light_array > 10)  # Pixels mit Helligkeit > 10
            light_max = np.max(light_array)
            print(f"🔍 Light-Mask: {light_bright} helle pixels, max brightness={light_max}")
            
            # WICHTIG: Clamp light_mask auf darkness_mask!
            # Subtraction soll NUR innerhalb des Polygons wirken
            # Wo darkness_mask=0 (außerhalb Polygon) → light_mask auch 0 setzen
            light_mask_clamped = ImageChops.multiply(
                light_mask.convert('RGB'),
                Image.merge('RGB', [darkness_mask]*3)
            ).convert('L')
            
            # Jetzt subtrahieren (nur noch innerhalb Polygon)
            final_darkness_mask = ImageChops.subtract(darkness_mask, light_mask_clamped)
            
            # DEBUG: Prüfe finale Maske
            final_array = np.array(final_darkness_mask)
            final_nonzero = np.count_nonzero(final_array)
            final_max = np.max(final_array) if final_nonzero > 0 else 0
            print(f"🔍 Final-Mask nach Light-Subtract: {final_nonzero} pixels dunkel (max={final_max})")
            
            # Erstelle KOMPLETT TRANSPARENTEN Layer als Basis
            result = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            
            print(f"🔍 Result-Layer erstellt: {result.size}, Mode={result.mode}")
            
            # Erstelle dunklen Layer NUR wo die finale Maske aktiv ist
            darkness_value = int((1.0 - self.darkness_opacity) * 255)
            darkness_layer = Image.new('RGBA', (img_width, img_height), 
                                      (darkness_value, darkness_value, darkness_value, 255))
            darkness_layer.putalpha(final_darkness_mask)
            
            print(f"🔍 Darkness-Layer: RGB=({darkness_value},{darkness_value},{darkness_value}), Opacity={self.darkness_opacity}")
            
            # Composite: Dunkelheit über transparentem Hintergrund
            result = Image.alpha_composite(result, darkness_layer)
            
            # Addiere farbiges Licht darüber - ABER NUR IM POLYGON!
            # Clamp light auf darkness_mask Bereich
            light_rgba = light_layer.convert('RGBA')
            
            # Erstelle Maske für Lichter: Nur innerhalb des Polygons sichtbar
            # Erweitere darkness_mask zu RGBA für Composite
            light_region_mask = Image.new('L', (img_width, img_height), 0)
            light_region_mask.paste(darkness_mask, (0, 0))  # Kopiere Polygon-Bereich
            
            # Wende Maske auf Licht an (nur im Polygon sichtbar)
            light_clamped = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            # Composite light mit region mask
            light_alpha = light_rgba.split()[3]  # Original alpha
            combined_alpha = ImageChops.multiply(
                light_alpha.convert('RGB'),
                Image.merge('RGB', [light_region_mask]*3)
            ).convert('L')
            light_rgba.putalpha(combined_alpha)
            
            result = Image.alpha_composite(result, light_rgba)
            
            # DEBUG: Prüfe finales Result
            result_array = np.array(result)
            non_transparent = np.count_nonzero(result_array[:,:,3] > 0)  # Alpha-Kanal > 0
            print(f"🔍 Final Result: {non_transparent} nicht-transparente pixels (should be ~{nonzero_pixels})")
            
            return result
            
        else:
            # NACHTMODUS: Nur additive Lichtquellen, KEIN Darkness-Overlay
            # Die Map bleibt sichtbar, nur Lichtquellen werden hinzugefügt
            light_rgba = light_layer.convert('RGBA')
            return light_rgba
    
    def update_animation(self, delta_time: float = 0.016):
        """
        Update Animation Timer (für Flicker)
        Args:
            delta_time: Zeit seit letztem Frame in Sekunden (default: ~60 FPS)
        """
        self.time_offset += delta_time
        
        # Wrap around bei großen Werten (verhindert Float-Overflow)
        if self.time_offset > 1000.0:
            self.time_offset = self.time_offset % 1000.0
        
    def to_dict(self) -> Dict:
        """Export als Dictionary"""
        return {
            "lights": [light.to_dict() for light in self.lights],
            "ambient_color": self.ambient_color,
            "ambient_intensity": self.ambient_intensity,
            "enabled": self.enabled,
            "lighting_mode": self.lighting_mode,
            "darkness_opacity": self.darkness_opacity,
            "darkness_polygons": self.darkness_polygons
        }
        
    def from_dict(self, data: Dict):
        """Import aus Dictionary"""
        self.lights = [LightSource.from_dict(l) for l in data.get("lights", [])]
        self.ambient_color = tuple(data.get("ambient_color", [30, 30, 40]))
        self.ambient_intensity = data.get("ambient_intensity", 0.2)
        self.enabled = data.get("enabled", True)
        self.lighting_mode = data.get("lighting_mode", "night")
        self.darkness_opacity = data.get("darkness_opacity", 0.85)
        self.darkness_polygons = data.get("darkness_polygons", [])


# Preset Lichtquellen mit optimierten physikalischen Parametern
LIGHT_PRESETS = {
    "torch": {
        "radius": 7,  # Größerer Radius für Fackeln
        "color": (255, 180, 80),  # Wärmeres Orange
        "intensity": 1.0,  # Volle Intensität
        "flicker": True,
        "light_type": "torch"
    },
    "candle": {
        "radius": 4,  # Etwas größer für bessere Sichtbarkeit
        "color": (255, 230, 180),  # Weiches warmes Gelb
        "intensity": 0.8,
        "flicker": True,
        "light_type": "candle"
    },
    "fire": {
        "radius": 8,  # Großes Feuer
        "color": (255, 140, 40),  # Intensives Orange-Rot
        "intensity": 1.2,  # Sehr hell (erlaubt Überhellung)
        "flicker": True,
        "light_type": "fire"
    },
    "campfire": {
        "radius": 6,
        "color": (255, 160, 60),
        "intensity": 1.0,
        "flicker": True,
        "light_type": "campfire"
    },
    "window": {
        "radius": 10,  # Großer sanfter Bereich
        "color": (220, 235, 255),  # Tageslicht (leicht blau)
        "intensity": 0.7,
        "flicker": False,  # Kein Flackern bei Tageslicht
        "light_type": "window"
    },
    "magic": {
        "radius": 8,
        "color": (180, 120, 255),  # Lila/Violett für Magie
        "intensity": 1.1,
        "flicker": True,  # Pulsiert
        "light_type": "magic"
    },
    "moonlight": {
        "radius": 12,  # Sehr großer, sanfter Bereich
        "color": (180, 200, 235),  # Kühles Blau-Weiß
        "intensity": 0.5,
        "flicker": False,
        "light_type": "moonlight"
    },
    # Neue Presets
    "lantern": {
        "radius": 6,
        "color": (255, 200, 120),
        "intensity": 0.85,
        "flicker": True,
        "light_type": "torch"  # Verwendet Torch-Physik aber schwächer
    },
    "brazier": {
        "radius": 9,
        "color": (255, 150, 50),
        "intensity": 1.1,
        "flicker": True,
        "light_type": "fire"
    },
    "crystal": {
        "radius": 7,
        "color": (150, 200, 255),  # Kühles Blau
        "intensity": 0.9,
        "flicker": True,
        "light_type": "magic"
    }
}
