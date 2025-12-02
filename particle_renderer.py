"""
Fortgeschrittenes Partikel-Rendering mit Cairo und OpenGL-ähnlichen Effekten
Unterstützt realistische Texturen, Blur, Glow und verschiedene Blend-Modi
"""

import math
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import colorsys

try:
    import cairo
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False
    print("Warnung: Cairo nicht verfügbar. Verwende Fallback-Renderer.")

try:
    from PIL import Image, ImageFilter, ImageDraw, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warnung: PIL nicht verfügbar.")

from particle_system import (
    Particle, ParticleEmitter, ParticleCanvas, ParticleType,
    BlendMode, Vector3, Color
)


class TextureType(Enum):
    """Verschiedene Partikel-Textur-Typen"""
    CIRCLE_SOFT = "circle_soft"
    CIRCLE_HARD = "circle_hard"
    RAINDROP = "raindrop"
    SNOWFLAKE = "snowflake"
    SPARK = "spark"
    SMOKE = "smoke"
    FIRE = "fire"
    GLOW = "glow"
    STAR = "star"
    LEAF = "leaf"
    BUBBLE = "bubble"
    CUSTOM = "custom"


@dataclass
class ParticleTexture:
    """Partikel-Textur mit Alpha-Kanal"""
    data: np.ndarray  # RGBA als (size, size, 4)
    size: int
    
    @staticmethod
    def generate(texture_type: TextureType, size: int = 64) -> 'ParticleTexture':
        """Generiere Textur basierend auf Typ"""
        generators = {
            TextureType.CIRCLE_SOFT: ParticleTexture._gen_circle_soft,
            TextureType.CIRCLE_HARD: ParticleTexture._gen_circle_hard,
            TextureType.RAINDROP: ParticleTexture._gen_raindrop,
            TextureType.SNOWFLAKE: ParticleTexture._gen_snowflake,
            TextureType.SPARK: ParticleTexture._gen_spark,
            TextureType.SMOKE: ParticleTexture._gen_smoke,
            TextureType.FIRE: ParticleTexture._gen_fire,
            TextureType.GLOW: ParticleTexture._gen_glow,
            TextureType.STAR: ParticleTexture._gen_star,
            TextureType.LEAF: ParticleTexture._gen_leaf,
            TextureType.BUBBLE: ParticleTexture._gen_bubble,
        }
        
        if texture_type in generators:
            data = generators[texture_type](size)
        else:
            data = ParticleTexture._gen_circle_soft(size)
        
        return ParticleTexture(data=data, size=size)
    
    @staticmethod
    def _gen_circle_soft(size: int) -> np.ndarray:
        """Weicher Kreis mit Gradient"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                
                if dist <= 1.0:
                    alpha = 1.0 - dist ** 2
                    data[y, x] = [1.0, 1.0, 1.0, alpha]
        
        return data
    
    @staticmethod
    def _gen_circle_hard(size: int) -> np.ndarray:
        """Harter Kreis"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                
                if dist <= 0.9:
                    data[y, x] = [1.0, 1.0, 1.0, 1.0]
                elif dist <= 1.0:
                    alpha = (1.0 - dist) / 0.1
                    data[y, x] = [1.0, 1.0, 1.0, alpha]
        
        return data
    
    @staticmethod
    def _gen_raindrop(size: int) -> np.ndarray:
        """Regentropfen-Form (länglich)"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center_x = size / 2
        
        for y in range(size):
            # Tropfen-Form: oben spitz, unten rund
            progress = y / size
            width = math.sin(progress * math.pi) * 0.3 + 0.1
            
            for x in range(size):
                dx = abs(x - center_x + 0.5) / size
                
                if dx < width:
                    # Weicher Rand
                    edge_dist = 1.0 - dx / width
                    alpha = edge_dist ** 0.5 * 0.8
                    
                    # Hellerer Kern (Reflektion)
                    if dx < width * 0.3:
                        brightness = 1.0
                    else:
                        brightness = 0.7 + 0.3 * (1 - dx / width)
                    
                    data[y, x] = [brightness, brightness, 1.0, alpha]
        
        return data
    
    @staticmethod
    def _gen_snowflake(size: int) -> np.ndarray:
        """Schneeflocken-Form"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        # 6-strahlige Schneeflocke
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                angle = math.atan2(dy, dx)
                
                if dist <= 1.0:
                    # Basis-Kreis
                    base_alpha = (1.0 - dist ** 2) * 0.3
                    
                    # Strahlen (6 Stück)
                    ray_alpha = 0
                    for i in range(6):
                        ray_angle = i * math.pi / 3
                        angle_diff = abs(math.sin((angle - ray_angle) * 3))
                        
                        if angle_diff < 0.2:
                            ray_factor = (1.0 - angle_diff / 0.2) * (1.0 - dist)
                            ray_alpha = max(ray_alpha, ray_factor * 0.8)
                    
                    alpha = min(1.0, base_alpha + ray_alpha)
                    data[y, x] = [1.0, 1.0, 1.0, alpha]
        
        return data
    
    @staticmethod
    def _gen_spark(size: int) -> np.ndarray:
        """Funken-Textur (hell im Zentrum)"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                
                if dist <= 1.0:
                    # Exponentieller Falloff für intensives Zentrum
                    intensity = math.exp(-dist * 3)
                    alpha = intensity
                    
                    # Farbverlauf: Weiß -> Gelb -> Orange
                    if dist < 0.3:
                        color = [1.0, 1.0, 0.9]
                    elif dist < 0.6:
                        t = (dist - 0.3) / 0.3
                        color = [1.0, 1.0 - t * 0.2, 0.9 - t * 0.5]
                    else:
                        t = (dist - 0.6) / 0.4
                        color = [1.0, 0.8 - t * 0.3, 0.4 - t * 0.3]
                    
                    data[y, x] = [color[0], color[1], color[2], alpha]
        
        return data
    
    @staticmethod
    def _gen_smoke(size: int) -> np.ndarray:
        """Rauch-Textur mit Perlin-ähnlichem Noise"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        # Einfacher Noise
        noise = np.random.rand(size // 4, size // 4)
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                
                if dist <= 1.0:
                    # Basis-Alpha mit weichem Rand
                    base_alpha = (1.0 - dist ** 2) ** 0.5
                    
                    # Noise hinzufügen
                    nx, ny = int(x * (size // 4 - 1) / size), int(y * (size // 4 - 1) / size)
                    noise_val = noise[ny, nx]
                    
                    alpha = base_alpha * (0.5 + noise_val * 0.5)
                    gray = 0.3 + noise_val * 0.2
                    
                    data[y, x] = [gray, gray, gray, alpha * 0.7]
        
        return data
    
    @staticmethod
    def _gen_fire(size: int) -> np.ndarray:
        """Feuer-Textur"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center_x = size / 2
        
        for y in range(size):
            progress = y / size  # 0 = oben (Spitze), 1 = unten (Basis)
            
            # Flammenform: unten breit, oben spitz
            width = (1.0 - progress ** 0.5) * 0.5
            
            for x in range(size):
                dx = abs(x - center_x + 0.5) / size
                
                if dx < width:
                    edge_factor = 1.0 - dx / width
                    
                    # Farbverlauf basierend auf Position
                    if progress < 0.3:
                        # Spitze: Orange/Rot, schwächer
                        t = progress / 0.3
                        color = [1.0, 0.3 + t * 0.2, 0.0]
                        alpha = edge_factor * t * 0.8
                    elif progress < 0.6:
                        # Mitte: Gelb/Orange
                        t = (progress - 0.3) / 0.3
                        color = [1.0, 0.5 + t * 0.4, t * 0.2]
                        alpha = edge_factor * 0.9
                    else:
                        # Basis: Weiß/Gelb
                        t = (progress - 0.6) / 0.4
                        color = [1.0, 0.9 + t * 0.1, 0.2 + t * 0.6]
                        alpha = edge_factor * (1.0 - t * 0.3)
                    
                    data[y, x] = [color[0], color[1], color[2], alpha]
        
        return data
    
    @staticmethod
    def _gen_glow(size: int) -> np.ndarray:
        """Glow-Textur (sehr weich)"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                
                if dist <= 1.0:
                    # Sehr weicher Falloff
                    alpha = math.exp(-dist * 2) * 0.8
                    data[y, x] = [1.0, 1.0, 1.0, alpha]
        
        return data
    
    @staticmethod
    def _gen_star(size: int) -> np.ndarray:
        """Stern-Textur"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                angle = math.atan2(dy, dx)
                
                if dist <= 1.0:
                    # 4-zackiger Stern
                    star_factor = abs(math.cos(angle * 2)) ** 4
                    effective_dist = dist / (0.3 + star_factor * 0.7)
                    
                    if effective_dist <= 1.0:
                        alpha = (1.0 - effective_dist ** 2) ** 0.5
                        data[y, x] = [1.0, 1.0, 1.0, alpha]
        
        return data
    
    @staticmethod
    def _gen_leaf(size: int) -> np.ndarray:
        """Blatt-Textur"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center_x = size / 2
        center_y = size / 2
        
        for y in range(size):
            for x in range(size):
                # Blattform: Ellipse mit Spitze
                dx = (x - center_x + 0.5) / (size * 0.3)
                dy = (y - center_y + 0.5) / (size * 0.45)
                
                # Asymmetrische Form
                dist = dx*dx + dy*dy
                
                if dist <= 1.0:
                    alpha = (1.0 - dist) ** 0.5
                    
                    # Blattader (Mittelader)
                    if abs(dx) < 0.1:
                        green = 0.4
                    else:
                        green = 0.6 + abs(dx) * 0.2
                    
                    data[y, x] = [0.3, green, 0.1, alpha * 0.9]
        
        return data
    
    @staticmethod
    def _gen_bubble(size: int) -> np.ndarray:
        """Blasen-Textur mit Reflektion"""
        data = np.zeros((size, size, 4), dtype=np.float32)
        center = size / 2
        
        for y in range(size):
            for x in range(size):
                dx = x - center + 0.5
                dy = y - center + 0.5
                dist = math.sqrt(dx*dx + dy*dy) / center
                
                if dist <= 1.0:
                    # Rand stärker als Mitte
                    if dist > 0.85:
                        alpha = (1.0 - dist) / 0.15 * 0.5
                    else:
                        alpha = 0.1
                    
                    # Reflektion (oben links)
                    ref_x = center * 0.6
                    ref_y = center * 0.4
                    ref_dist = math.sqrt((x - ref_x)**2 + (y - ref_y)**2) / (size * 0.15)
                    
                    if ref_dist < 1.0:
                        ref_alpha = (1.0 - ref_dist ** 2) * 0.8
                        alpha = max(alpha, ref_alpha)
                    
                    data[y, x] = [0.9, 0.95, 1.0, alpha]
        
        return data


class AdvancedParticleRenderer:
    """
    Fortgeschrittener Renderer mit Cairo-Unterstützung
    """
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Texture Cache
        self.texture_cache: Dict[Tuple[TextureType, int], ParticleTexture] = {}
        
        # Texture-Zuordnung für Partikeltypen
        self.particle_textures: Dict[ParticleType, TextureType] = {
            ParticleType.RAIN: TextureType.RAINDROP,
            ParticleType.SNOW: TextureType.SNOWFLAKE,
            ParticleType.SPARK: TextureType.SPARK,
            ParticleType.SMOKE: TextureType.SMOKE,
            ParticleType.FIRE: TextureType.FIRE,
            ParticleType.FOG: TextureType.SMOKE,
            ParticleType.DUST: TextureType.CIRCLE_SOFT,
            ParticleType.EMBER: TextureType.SPARK,
            ParticleType.MAGIC: TextureType.GLOW,
            ParticleType.LEAVES: TextureType.LEAF,
            ParticleType.WATER_SPLASH: TextureType.CIRCLE_SOFT,
            ParticleType.BUBBLE: TextureType.BUBBLE,
        }
        
        # Cairo-Surface
        if CAIRO_AVAILABLE:
            self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            self.ctx = cairo.Context(self.surface)
        else:
            self.surface = None
            self.ctx = None
    
    def get_texture(self, texture_type: TextureType, size: int = 64) -> ParticleTexture:
        """Hole oder erstelle Textur (cached)"""
        key = (texture_type, size)
        if key not in self.texture_cache:
            self.texture_cache[key] = ParticleTexture.generate(texture_type, size)
        return self.texture_cache[key]
    
    def render(self, canvas: ParticleCanvas, 
               background_alpha: float = 0.0) -> np.ndarray:
        """
        Rendere Canvas mit fortgeschrittenen Effekten
        Returns: RGBA numpy array (height, width, 4) with values 0-255
        """
        if CAIRO_AVAILABLE:
            return self._render_cairo(canvas, background_alpha)
        else:
            return self._render_fallback(canvas, background_alpha)
    
    def _render_cairo(self, canvas: ParticleCanvas, 
                      background_alpha: float) -> np.ndarray:
        """Render mit Cairo"""
        # Clear
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)
        
        # Background
        if background_alpha > 0:
            self.ctx.set_source_rgba(
                canvas.background_color.r,
                canvas.background_color.g,
                canvas.background_color.b,
                background_alpha
            )
            self.ctx.paint()
        
        # Partikel rendern
        for emitter in canvas.emitters:
            self._render_emitter_cairo(emitter)
        
        # Surface zu numpy array
        buf = self.surface.get_data()
        data = np.ndarray(shape=(self.height, self.width, 4), 
                         dtype=np.uint8, buffer=buf)
        
        # BGRA zu RGBA konvertieren
        result = np.zeros_like(data)
        result[:, :, 0] = data[:, :, 2]  # R
        result[:, :, 1] = data[:, :, 1]  # G
        result[:, :, 2] = data[:, :, 0]  # B
        result[:, :, 3] = data[:, :, 3]  # A
        
        return result
    
    def _render_emitter_cairo(self, emitter: ParticleEmitter):
        """Rendere Emitter mit Cairo"""
        # Blend-Modus setzen
        if emitter.blend_mode == BlendMode.ADD:
            self.ctx.set_operator(cairo.OPERATOR_ADD)
        elif emitter.blend_mode == BlendMode.MULTIPLY:
            self.ctx.set_operator(cairo.OPERATOR_MULTIPLY)
        elif emitter.blend_mode == BlendMode.SCREEN:
            self.ctx.set_operator(cairo.OPERATOR_SCREEN)
        else:
            self.ctx.set_operator(cairo.OPERATOR_OVER)
        
        # Textur für diesen Partikeltyp
        texture_type = self.particle_textures.get(
            emitter.particle_type, TextureType.CIRCLE_SOFT
        )
        
        for particle in emitter.particles:
            self._render_particle_cairo(particle, texture_type)
        
        # Reset operator
        self.ctx.set_operator(cairo.OPERATOR_OVER)
    
    def _render_particle_cairo(self, particle: Particle, texture_type: TextureType):
        """Rendere einzelnes Partikel mit Cairo"""
        x, y = particle.position.x, particle.position.y
        size = max(2, particle.size)
        color = particle.color
        
        # Trail zuerst rendern
        if particle.trail_length > 0 and len(particle.trail_positions) > 1:
            self._render_trail_cairo(particle)
        
        # Partikel mit Textur rendern
        self.ctx.save()
        self.ctx.translate(x, y)
        self.ctx.rotate(particle.rotation)
        self.ctx.scale(size / 64, size / 64)
        
        # Textur als Gradient simulieren
        if texture_type in [TextureType.CIRCLE_SOFT, TextureType.GLOW]:
            # Radialer Gradient
            pattern = cairo.RadialGradient(0, 0, 0, 0, 0, 32)
            pattern.add_color_stop_rgba(0, color.r, color.g, color.b, color.a)
            pattern.add_color_stop_rgba(1, color.r, color.g, color.b, 0)
            self.ctx.set_source(pattern)
            self.ctx.arc(0, 0, 32, 0, 2 * math.pi)
            self.ctx.fill()
        
        elif texture_type == TextureType.RAINDROP:
            # Längliche Form für Regen
            self.ctx.scale(0.3, 1.0)
            pattern = cairo.LinearGradient(0, -32, 0, 32)
            pattern.add_color_stop_rgba(0, color.r, color.g, color.b, 0)
            pattern.add_color_stop_rgba(0.3, color.r, color.g, color.b, color.a)
            pattern.add_color_stop_rgba(1, color.r, color.g, color.b, color.a * 0.5)
            self.ctx.set_source(pattern)
            self.ctx.arc(0, 0, 32, 0, 2 * math.pi)
            self.ctx.fill()
        
        elif texture_type == TextureType.SPARK:
            # Heller Kern
            pattern = cairo.RadialGradient(0, 0, 0, 0, 0, 32)
            pattern.add_color_stop_rgba(0, 1, 1, 0.9, color.a)
            pattern.add_color_stop_rgba(0.3, color.r, color.g, color.b, color.a * 0.8)
            pattern.add_color_stop_rgba(1, color.r * 0.5, 0, 0, 0)
            self.ctx.set_source(pattern)
            self.ctx.arc(0, 0, 32, 0, 2 * math.pi)
            self.ctx.fill()
        
        elif texture_type == TextureType.SNOWFLAKE:
            # Sternform
            self.ctx.set_source_rgba(color.r, color.g, color.b, color.a)
            for i in range(6):
                angle = i * math.pi / 3
                self.ctx.move_to(0, 0)
                self.ctx.line_to(math.cos(angle) * 30, math.sin(angle) * 30)
            self.ctx.set_line_width(3)
            self.ctx.stroke()
            
            # Zentrum
            self.ctx.arc(0, 0, 8, 0, 2 * math.pi)
            self.ctx.fill()
        
        elif texture_type == TextureType.FIRE:
            # Flammenform
            pattern = cairo.RadialGradient(0, 10, 0, 0, 0, 32)
            pattern.add_color_stop_rgba(0, 1, 1, 0.8, color.a)
            pattern.add_color_stop_rgba(0.4, 1, 0.6, 0.1, color.a * 0.8)
            pattern.add_color_stop_rgba(1, 1, 0.2, 0, 0)
            self.ctx.set_source(pattern)
            
            # Flammenform zeichnen
            self.ctx.move_to(0, -30)
            self.ctx.curve_to(-15, -10, -20, 10, -15, 30)
            self.ctx.curve_to(-5, 20, 5, 20, 15, 30)
            self.ctx.curve_to(20, 10, 15, -10, 0, -30)
            self.ctx.fill()
        
        elif texture_type == TextureType.SMOKE:
            # Weicher Kreis mit Noise-Effekt (vereinfacht)
            pattern = cairo.RadialGradient(0, 0, 0, 0, 0, 32)
            pattern.add_color_stop_rgba(0, color.r, color.g, color.b, color.a * 0.6)
            pattern.add_color_stop_rgba(0.7, color.r, color.g, color.b, color.a * 0.3)
            pattern.add_color_stop_rgba(1, color.r, color.g, color.b, 0)
            self.ctx.set_source(pattern)
            self.ctx.arc(0, 0, 32, 0, 2 * math.pi)
            self.ctx.fill()
        
        elif texture_type == TextureType.LEAF:
            # Blattform
            self.ctx.set_source_rgba(color.r, color.g, color.b, color.a)
            self.ctx.scale(0.6, 1.0)
            self.ctx.arc(0, 0, 25, 0, 2 * math.pi)
            self.ctx.fill()
            
            # Blattader
            self.ctx.set_source_rgba(color.r * 0.7, color.g * 0.8, color.b * 0.7, color.a)
            self.ctx.move_to(0, -25)
            self.ctx.line_to(0, 25)
            self.ctx.set_line_width(2)
            self.ctx.stroke()
        
        elif texture_type == TextureType.BUBBLE:
            # Blase mit Reflektion
            self.ctx.set_source_rgba(color.r, color.g, color.b, color.a * 0.3)
            self.ctx.arc(0, 0, 30, 0, 2 * math.pi)
            self.ctx.set_line_width(2)
            self.ctx.stroke()
            
            # Reflektion
            self.ctx.set_source_rgba(1, 1, 1, color.a * 0.6)
            self.ctx.arc(-10, -10, 8, 0, 2 * math.pi)
            self.ctx.fill()
        
        else:
            # Fallback: einfacher Kreis
            self.ctx.set_source_rgba(color.r, color.g, color.b, color.a)
            self.ctx.arc(0, 0, 30, 0, 2 * math.pi)
            self.ctx.fill()
        
        self.ctx.restore()
    
    def _render_trail_cairo(self, particle: Particle):
        """Rendere Partikel-Trail mit Cairo"""
        if len(particle.trail_positions) < 2:
            return
        
        color = particle.color
        
        # Trail als Linie mit abnehmender Dicke
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        
        for i in range(len(particle.trail_positions) - 1):
            p1 = particle.trail_positions[i]
            p2 = particle.trail_positions[i + 1]
            
            alpha = (1.0 - i / len(particle.trail_positions)) * color.a * 0.5
            width = particle.size * (1.0 - i / len(particle.trail_positions)) * 0.5
            
            self.ctx.set_source_rgba(color.r, color.g, color.b, alpha)
            self.ctx.set_line_width(max(1, width))
            self.ctx.move_to(p1.x, p1.y)
            self.ctx.line_to(p2.x, p2.y)
            self.ctx.stroke()
    
    def _render_fallback(self, canvas: ParticleCanvas, 
                         background_alpha: float) -> np.ndarray:
        """Fallback-Renderer ohne Cairo - verwendet PIL"""
        if PIL_AVAILABLE:
            return self._render_with_pil(canvas, background_alpha)
        else:
            # Verwende das eingebaute Rendering
            frame = canvas.render_frame()
            # Konvertiere zu uint8
            return (frame * 255).astype(np.uint8)
    
    def _render_with_pil(self, canvas: ParticleCanvas,
                         background_alpha: float) -> np.ndarray:
        """Rendere mit PIL/Pillow"""
        # Erstelle transparentes Bild
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Alle Partikel rendern
        for emitter in canvas.emitters:
            texture_type = self.particle_textures.get(
                emitter.particle_type, TextureType.CIRCLE_SOFT
            )
            
            # Trails zuerst (damit sie hinter den Partikeln sind)
            for particle in emitter.particles:
                if particle.trail_length > 0 and len(particle.trail_positions) > 1:
                    self._draw_trail_pil(draw, particle, emitter.blend_mode)
            
            # Dann die Partikel selbst
            for particle in emitter.particles:
                self._draw_particle_pil(draw, img, particle, texture_type, emitter.blend_mode)
        
        return np.array(img)
    
    def _draw_particle_pil(self, draw: ImageDraw.Draw, img: Image.Image,
                           particle, texture_type: TextureType, blend_mode):
        """Zeichne einzelnes Partikel mit PIL"""
        x, y = particle.position.x, particle.position.y
        size = max(2, particle.size)
        color = particle.color
        
        # RGBA Farbe
        r = int(color.r * 255)
        g = int(color.g * 255)
        b = int(color.b * 255)
        a = int(color.a * 255)
        
        half = size / 2
        
        # Für additive Blending: Hellere Farbe
        if blend_mode == BlendMode.ADD:
            # Bei ADD wird die Farbe heller dargestellt
            r = min(255, int(r * 1.5))
            g = min(255, int(g * 1.5))
            b = min(255, int(b * 1.5))
        
        if texture_type in [TextureType.CIRCLE_SOFT, TextureType.GLOW]:
            # Weicher Kreis mit mehreren Ringen
            for i in range(3, 0, -1):
                ring_size = half * i / 3
                ring_alpha = int(a * (1 - (i-1) / 3) * 0.7)
                if ring_alpha > 0:
                    draw.ellipse(
                        [x - ring_size, y - ring_size, x + ring_size, y + ring_size],
                        fill=(r, g, b, ring_alpha)
                    )
        
        elif texture_type == TextureType.RAINDROP:
            # Länglicher Tropfen
            draw.ellipse(
                [x - half * 0.3, y - half, x + half * 0.3, y + half],
                fill=(r, g, b, a)
            )
        
        elif texture_type == TextureType.SPARK:
            # Heller Kern mit Glühen
            for i in range(4, 0, -1):
                ring_size = half * i / 4
                ring_alpha = int(a * (1 - (i-1) / 4))
                bright_r = min(255, r + (255 - r) * (4 - i) // 4)
                bright_g = min(255, g + (255 - g) * (4 - i) // 4)
                bright_b = min(255, b + (255 - b) * (4 - i) // 4)
                if ring_alpha > 0:
                    draw.ellipse(
                        [x - ring_size, y - ring_size, x + ring_size, y + ring_size],
                        fill=(bright_r, bright_g, bright_b, ring_alpha)
                    )
        
        elif texture_type == TextureType.SNOWFLAKE:
            # Einfache Schneeflocke (Stern)
            draw.ellipse(
                [x - half * 0.3, y - half * 0.3, x + half * 0.3, y + half * 0.3],
                fill=(r, g, b, a)
            )
            # Strahlen
            for angle in range(0, 360, 60):
                rad = angle * 3.14159 / 180
                ex = x + half * 0.8 * np.cos(rad)
                ey = y + half * 0.8 * np.sin(rad)
                draw.line([(x, y), (ex, ey)], fill=(r, g, b, a), width=max(1, int(half * 0.2)))
        
        elif texture_type in [TextureType.SMOKE, TextureType.FIRE]:
            # Größerer weicher Kreis für Rauch/Feuer
            for i in range(5, 0, -1):
                ring_size = half * i / 5
                ring_alpha = int(a * (1 - (i-1) / 5) * 0.5)
                if ring_alpha > 0:
                    draw.ellipse(
                        [x - ring_size, y - ring_size, x + ring_size, y + ring_size],
                        fill=(r, g, b, ring_alpha)
                    )
        
        elif texture_type == TextureType.LEAF:
            # Ellipse für Blatt
            import math
            rot = particle.rotation
            # Vereinfachtes rotiertes Blatt als Ellipse
            draw.ellipse(
                [x - half * 0.4, y - half * 0.8, x + half * 0.4, y + half * 0.8],
                fill=(r, g, b, a)
            )
        
        elif texture_type == TextureType.BUBBLE:
            # Kreis mit hellerem Rand
            draw.ellipse(
                [x - half, y - half, x + half, y + half],
                outline=(r, g, b, a),
                width=max(1, int(half * 0.15))
            )
            # Reflexion
            ref_x = x - half * 0.3
            ref_y = y - half * 0.3
            ref_size = half * 0.25
            draw.ellipse(
                [ref_x - ref_size, ref_y - ref_size, ref_x + ref_size, ref_y + ref_size],
                fill=(255, 255, 255, int(a * 0.6))
            )
        
        else:
            # Standard: Einfacher Kreis
            draw.ellipse(
                [x - half, y - half, x + half, y + half],
                fill=(r, g, b, a)
            )
    
    def _draw_trail_pil(self, draw: ImageDraw.Draw, particle, blend_mode):
        """Zeichne Partikel-Trail mit PIL"""
        if len(particle.trail_positions) < 2:
            return
        
        color = particle.color
        r = int(color.r * 255)
        g = int(color.g * 255)
        b = int(color.b * 255)
        
        # Trail als Linien
        positions = [(particle.position.x, particle.position.y)] + \
                    [(p.x, p.y) for p in particle.trail_positions]
        
        for i in range(len(positions) - 1):
            p1 = positions[i]
            p2 = positions[i + 1]
            
            # Alpha nimmt ab
            alpha = int(color.a * 255 * (1 - i / len(positions)) * 0.5)
            width = max(1, int(particle.size * (1 - i / len(positions)) * 0.5))
            
            if alpha > 0:
                draw.line([p1, p2], fill=(r, g, b, alpha), width=width)
    
    def apply_post_effects(self, frame: np.ndarray, 
                           glow_strength: float = 0.0,
                           glow_radius: int = 10,
                           motion_blur: float = 0.0,
                           previous_frame: Optional[np.ndarray] = None) -> np.ndarray:
        """Wende Post-Processing-Effekte an"""
        if not PIL_AVAILABLE:
            return frame
        
        # Zu PIL Image konvertieren
        image = Image.fromarray(frame, 'RGBA')
        
        # Glow
        if glow_strength > 0:
            # Helle Bereiche extrahieren
            r, g, b, a = image.split()
            bright = Image.merge('RGB', (r, g, b))
            bright = ImageEnhance.Brightness(bright).enhance(1.5)
            
            # Blur
            glow = bright.filter(ImageFilter.GaussianBlur(glow_radius))
            
            # Mit Original kombinieren
            glow_rgba = Image.merge('RGBA', (*glow.split(), a))
            image = Image.blend(image, glow_rgba, glow_strength)
        
        # Motion Blur
        if motion_blur > 0 and previous_frame is not None:
            prev_image = Image.fromarray(previous_frame, 'RGBA')
            image = Image.blend(prev_image, image, 1.0 - motion_blur)
        
        return np.array(image)


def create_particle_preview(particle_type: ParticleType, 
                           width: int = 400, height: int = 300,
                           duration: float = 3.0, fps: int = 30) -> List[np.ndarray]:
    """
    Erstelle Vorschau-Frames für einen Partikeltyp
    Returns: Liste von RGBA numpy arrays
    """
    from particle_system import (
        ParticleCanvas, ParticleEmitter, RectEmitter, CircleEmitter, Vector3
    )
    
    canvas = ParticleCanvas(width, height)
    emitter = ParticleEmitter(particle_type)
    
    # Emitter-Form basierend auf Typ
    if particle_type in [ParticleType.RAIN, ParticleType.SNOW, ParticleType.LEAVES]:
        emitter.shape = RectEmitter(
            position=Vector3(width/2, -20, 0),
            width=width + 100,
            height=10
        )
    elif particle_type in [ParticleType.FIRE, ParticleType.SMOKE, ParticleType.EMBER]:
        emitter.shape = CircleEmitter(
            position=Vector3(width/2, height - 50, 0),
            radius=30
        )
    elif particle_type in [ParticleType.SPARK, ParticleType.MAGIC]:
        emitter.shape = CircleEmitter(
            position=Vector3(width/2, height/2, 0),
            radius=20
        )
    else:
        emitter.shape = CircleEmitter(
            position=Vector3(width/2, height/2, 0),
            radius=50
        )
    
    canvas.add_emitter(emitter)
    
    renderer = AdvancedParticleRenderer(width, height)
    renderer.particle_textures[particle_type] = renderer.particle_textures.get(
        particle_type, TextureType.CIRCLE_SOFT
    )
    
    frames = []
    num_frames = int(duration * fps)
    dt = 1.0 / fps
    
    for _ in range(num_frames):
        canvas.update(dt)
        frame = renderer.render(canvas)
        frames.append(frame)
    
    return frames


if __name__ == "__main__":
    # Test Texturen
    print("Generiere Texturen...")
    for tex_type in TextureType:
        if tex_type != TextureType.CUSTOM:
            texture = ParticleTexture.generate(tex_type, 64)
            print(f"  {tex_type.value}: {texture.size}x{texture.size}")
    
    print("\nRenderer-Test...")
    renderer = AdvancedParticleRenderer(800, 600)
    
    from particle_system import ParticleCanvas, ParticleEmitter, CircleEmitter, Vector3
    
    canvas = ParticleCanvas(800, 600)
    emitter = ParticleEmitter(ParticleType.FIRE)
    emitter.shape = CircleEmitter(position=Vector3(400, 500, 0), radius=30)
    canvas.add_emitter(emitter)
    
    # Simuliere einige Frames
    for i in range(60):
        canvas.update(1/60)
    
    frame = renderer.render(canvas)
    print(f"Frame shape: {frame.shape}, dtype: {frame.dtype}")
    print(f"Partikel: {canvas.get_total_particles()}")
