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
            # ════════════════════════════════════════════════════════════
            # TAGESMODUS: Physikalisch korrekte Schatten & Beleuchtung
            # ════════════════════════════════════════════════════════════
            # Die Map-Texturen bleiben IMMER sichtbar!
            # Dunkelheit = multiplikative Verdunkelung (wie echte Schatten)
            # Licht = additive Aufhellung der dunklen Bereiche
            
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
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 1: Erstelle Shadow-Mask (Schatten-Intensität pro Pixel)
            # ════════════════════════════════════════════════════════════
            # Diese Maske definiert wo es dunkel ist (0=hell, 255=dunkel)
            shadow_mask = Image.new('L', (img_width, img_height), 0)  # 0 = keine Schatten
            draw = ImageDraw.Draw(shadow_mask)
            
            # Zeichne Dunkelheits-Polygone als Schatten-Bereiche
            for polygon in self.darkness_polygons:
                # Konvertiere Tile-Koordinaten zu Pixel-Koordinaten
                pixel_poly = [(int(x * tile_size), int(y * tile_size)) for x, y in polygon]
                # Basis-Schatten-Intensität (nie 100% schwarz wegen Ambient)
                # darkness_opacity = 0.85 → 85% dunkel → Pixel-Wert 217 (von 255)
                shadow_intensity = int(self.darkness_opacity * 255)
                draw.polygon(pixel_poly, fill=shadow_intensity)
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 2: Licht reduziert Schatten (physikalisch korrekt)
            # ════════════════════════════════════════════════════════════
            # Konvertiere Licht zu Helligkeit (Grayscale)
            light_brightness = light_layer.convert('L')
            
            # Licht subtrahiert von Schatten: Wo Licht ist, weniger Schatten
            # ImageChops.subtract(a, b) = max(0, a - b)
            final_shadow_mask = ImageChops.subtract(shadow_mask, light_brightness)
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 3: Erstelle MULTIPLICATIVE Darkening Layer
            # ════════════════════════════════════════════════════════════
            # Dieser Layer wird MULTIPLIZIERT mit der Map (nicht darübergelegt!)
            # Wert 255 = 100% hell (keine Veränderung)
            # Wert 128 = 50% dunkel
            # Wert 0 = 100% dunkel (schwarz)
            
            # Invertiere Schatten-Maske: 0→255 (dunkel→hell), 255→0 (hell→dunkel)
            # Dann skalieren mit Ambient-Minimum (nie komplett schwarz)
            import numpy as np
            shadow_array = np.array(final_shadow_mask, dtype=np.float32)
            
            # Invertiere und normalisiere
            # shadow_mask: 0=kein Schatten, 255=maximaler Schatten
            # multiply_mask: 255=keine Verdunkelung, 0=maximale Verdunkelung
            # ABER: minimum = ambient_intensity (z.B. 0.2 = 20% Helligkeit minimum)
            ambient_min = int(self.ambient_intensity * 255)  # Minimale Helligkeit (Streulicht)
            
            # Formel: multiply = (255 - shadow) * (1 - ambient) + ambient * 255
            # Oder einfacher: multiply = 255 - (shadow * (1 - ambient))
            multiply_array = 255 - (shadow_array * (1.0 - self.ambient_intensity))
            multiply_array = np.clip(multiply_array, ambient_min, 255).astype(np.uint8)
            
            multiply_mask = Image.fromarray(multiply_array)
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 4: Erstelle RGBA Multiply-Layer
            # ════════════════════════════════════════════════════════════
            # Wir brauchen einen Layer der die Map MULTIPLIZIERT (verdunkelt)
            # Dies wird über den Blend-Modus "multiply" erreicht
            
            # PROBLEM: PIL alpha_composite unterstützt kein "multiply" direkt
            # LÖSUNG: Wir nutzen einen Trick mit ImageChops.multiply
            # Aber wir returnen einen Layer den der Projector anders verarbeiten muss!
            
            # Erstelle RGB Layer für Multiplikation (wird außerhalb angewandt)
            # Format: RGB-Werte = Multiplikations-Faktor (0=schwarz, 255=keine Änderung)
            multiply_layer = Image.merge('RGB', [multiply_mask, multiply_mask, multiply_mask])
            
            # ════════════════════════════════════════════════════════════
            # SCHRITT 5: Füge farbiges Licht additiv hinzu
            # ════════════════════════════════════════════════════════════
            # Das Licht wird NACH der Multiplikation additiv aufgehellt
            # Nur im Polygon-Bereich sichtbar (sonst würde es die ganze Map aufhellen)
            
            # Erstelle Polygon-Maske (wo sind die Darkness-Bereiche?)
            polygon_mask = Image.new('L', (img_width, img_height), 0)
            draw_poly = ImageDraw.Draw(polygon_mask)
            for polygon in self.darkness_polygons:
                pixel_poly = [(int(x * tile_size), int(y * tile_size)) for x, y in polygon]
                draw_poly.polygon(pixel_poly, fill=255)
            
            # Clamp Licht auf Polygon-Bereich
            light_rgba = light_layer.convert('RGBA')
            light_alpha_original = light_rgba.split()[3]
            
            # Kombiniere Original-Licht-Alpha mit Polygon-Maske
            light_alpha_clamped = ImageChops.multiply(
                light_alpha_original.convert('RGB'),
                Image.merge('RGB', [polygon_mask]*3)
            ).convert('L')
            
            light_rgba.putalpha(light_alpha_clamped)
            
            # ════════════════════════════════════════════════════════════
            # RETURN: Spezielles Format für Projector
            # ════════════════════════════════════════════════════════════
            # Wir returnen ein Dict mit beiden Layern:
            # - "multiply": RGB Layer zum Multiplizieren (Schatten)
            # - "add": RGBA Layer zum Addieren (Licht)
            # 
            # ABER: render_lighting() muss Image returnen, nicht Dict!
            # LÖSUNG: Wir encoden beide Infos in einem speziellen RGBA Image
            # 
            # ALTERNATIVE: Wir passen den Projector an um multiply korrekt zu handlen
            # Für jetzt: Return RGBA mit custom Handling im Projector
            
            # Erstelle finales RGBA Image:
            # - RGB Channels: Multiply-Faktor (wird für Multiplikation genutzt)
            # - Alpha Channel: Kodiert dass dies ein Multiply-Layer ist (255=multiply mode)
            
            # ABER das ist zu komplex. Bessere Lösung:
            # Return ein Layer der im Projector mit MULTIPLY statt ALPHA_COMPOSITE verarbeitet wird
            
            # EINFACHSTE LÖSUNG: Store Flag in LightingEngine und ändere Projector
            # Für jetzt: Composite multiply + light direkt hier
            
            # ════════════════════════════════════════════════════════════
            # FINALE COMPOSITING mit echtem MULTIPLY-BLEND
            # ════════════════════════════════════════════════════════════
            # PROBLEM: PIL alpha_composite kann kein Multiply!
            # LÖSUNG: Wir returnen ein spezielles Format, das der Projector
            #         mit ImageChops.multiply() verarbeiten kann
            
            # Erstelle einen RGBA Layer mit spezieller Bedeutung:
            # - RGB: Multiply-Faktoren (255 = keine Änderung, 0 = schwarz)
            # - Alpha: Wo der Effekt angewandt wird (Polygon-Bereiche)
            
            # SCHRITT 1: Erstelle Multiply-RGB Layer
            # multiply_mask enthält bereits die richtigen Werte (0-255)
            multiply_rgb = Image.merge('RGB', [multiply_mask, multiply_mask, multiply_mask])
            
            # SCHRITT 2: Erstelle Alpha-Maske (wo sind die Polygone?)
            polygon_alpha = Image.new('L', (img_width, img_height), 0)
            draw_alpha = ImageDraw.Draw(polygon_alpha)
            for polygon in self.darkness_polygons:
                pixel_poly = [(int(x * tile_size), int(y * tile_size)) for x, y in polygon]
                draw_alpha.polygon(pixel_poly, fill=255)
            
            # SCHRITT 3: Kombiniere zu RGBA
            # Dieser Layer enthält die Multiply-Faktoren und wird vom Projector
            # mit ImageChops.multiply() auf die Map angewandt
            multiply_layer = multiply_rgb.convert('RGBA')
            multiply_layer.putalpha(polygon_alpha)
            
            # SCHRITT 4: Addiere farbiges Licht
            # Das Licht wird NACH dem Multiply als normaler Alpha-Composite angewandt
            result = Image.alpha_composite(multiply_layer, light_rgba)
            
            # WICHTIGER HINWEIS für Projector:
            # Dieser Layer muss mit ImageChops.multiply() angewandt werden,
            # NICHT mit alpha_composite!
            # Projector muss prüfen: if lighting_mode == "day": multiply statt composite
            
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
