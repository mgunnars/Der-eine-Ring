"""
Animierte Texturen und professionelle VTT-Assets für Der Eine Ring
Inspiriert von professionellen VTT-Systemen wie Foundry VTT, Roll20, und Arkenforge
"""

import time
from PIL import Image, ImageDraw, ImageFilter
import math
import random
from dataclasses import dataclass
from typing import List
from enum import Enum, auto

try:
    import noise
except ImportError:
    print("Warning: noise module not installed. Install with: pip install noise")
    noise = None

class AnimationType(Enum):
    """Animationstypen für verschiedene Texturen"""
    STATIC = auto()
    WATER_FLOW = auto()
    LAVA_FLOW = auto()
    FIRE = auto()
    SMOKE = auto()
    WIND_GRASS = auto()
    TORCH_FLICKER = auto()
    MAGIC_PULSE = auto()
    FOG_DRIFT = auto()

@dataclass
class AnimatedTexture:
    """Container für animierte Texturen"""
    frames: List[Image.Image]
    frame_duration: int  # Millisekunden pro Frame
    loop: bool = True
    current_frame: int = 0
    last_update: float = 0
    animation_type: AnimationType = AnimationType.STATIC
    
    def get_current_frame(self) -> Image.Image:
        """Gibt den aktuellen Frame zurück"""
        if not self.frames:
            return None
        return self.frames[self.current_frame]
    
    def update(self, current_time: float):
        """Aktualisiert die Animation"""
        if len(self.frames) <= 1:
            return
        
        if current_time - self.last_update >= self.frame_duration / 1000.0:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.last_update = current_time
            
            if not self.loop and self.current_frame == 0:
                self.current_frame = len(self.frames) - 1

class ProfessionalTextureGenerator:
    """Professionelle Texturgenerierung mit Animationen im VTT-Stil"""
    
    def __init__(self, tile_size=64, quality='high'):
        self.tile_size = tile_size
        self.quality = quality
        self.animation_cache = {}
        self.perlin_scale = 100.0
        
        if quality == 'high':
            self.water_frames = 60
            self.animation_fps = 30
        elif quality == 'medium':
            self.water_frames = 30
            self.animation_fps = 20
        else:
            self.water_frames = 15
            self.animation_fps = 15
    
    def generate_animated_water(self, water_type='river') -> AnimatedTexture:
        """Generiert animiertes Wasser mit fließender Bewegung"""
        frames = []
        
        for frame_num in range(self.water_frames):
            img = Image.new('RGBA', (self.tile_size, self.tile_size))
            draw = ImageDraw.Draw(img)
            
            base_colors = [
                (15, 94, 156, 255),
                (35, 137, 218, 245),
                (64, 164, 223, 235),
                (119, 190, 230, 225)
            ]
            
            for layer_idx, color in enumerate(base_colors):
                layer = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
                layer_draw = ImageDraw.Draw(layer)
                
                for x in range(self.tile_size):
                    for y in range(self.tile_size):
                        time_offset = frame_num * 0.1
                        
                        if noise:
                            if water_type == 'river':
                                flow_offset = (frame_num * 2) % self.tile_size
                                noise_val = noise.pnoise3(
                                    (x + flow_offset) / self.perlin_scale,
                                    y / self.perlin_scale,
                                    time_offset,
                                    octaves=3
                                )
                            else:
                                noise_val = noise.pnoise3(
                                    x / self.perlin_scale,
                                    y / self.perlin_scale,
                                    time_offset,
                                    octaves=4
                                )
                        else:
                            # Fallback ohne noise
                            noise_val = math.sin(x * 0.1 + frame_num * 0.1) * math.cos(y * 0.1)
                        
                        alpha = int((noise_val + 1) * 127.5)
                        alpha = max(0, min(255, alpha + 50 * (3 - layer_idx)))
                        
                        if alpha > 100:
                            layer_draw.point((x, y), fill=color[:3] + (alpha,))
                
                img = Image.alpha_composite(img, layer)
            
            # Wellen-Highlights
            for wave in range(3):
                wave_y = int((self.tile_size / 4) * (wave + 1))
                wave_offset = math.sin(frame_num * 0.2 + wave) * 5
                
                for x in range(self.tile_size):
                    y = wave_y + int(math.sin((x + frame_num * 2) * 0.3) * 3 + wave_offset)
                    if 0 <= y < self.tile_size:
                        for dy in range(-1, 2):
                            if 0 <= y + dy < self.tile_size:
                                alpha = 200 - abs(dy) * 50
                                draw.point((x, y + dy), fill=(255, 255, 255, alpha))
            
            frames.append(img)
        
        return AnimatedTexture(
            frames=frames,
            frame_duration=1000 // self.animation_fps,
            animation_type=AnimationType.WATER_FLOW
        )
    
    def generate_animated_fire(self) -> AnimatedTexture:
        """Generiert animierte Feuer-Textur"""
        frames = []
        
        for frame_num in range(20):
            img = Image.new('RGBA', (self.tile_size, self.tile_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            num_particles = 30
            
            for particle in range(num_particles):
                base_x = self.tile_size // 2 + random.randint(-10, 10)
                base_y = self.tile_size - 10
                
                rise = (frame_num * 2 + particle * 3) % self.tile_size
                x = base_x + int(math.sin(rise * 0.1) * 5)
                y = base_y - rise
                
                if y < 0:
                    continue
                
                height_ratio = rise / self.tile_size
                
                if height_ratio < 0.3:
                    color = (255, 255, 200)
                elif height_ratio < 0.6:
                    color = (255, 150, 0)
                else:
                    color = (200, 50, 0)
                
                alpha = int(255 * (1 - height_ratio))
                size = int(5 * (1 - height_ratio * 0.7))
                
                if size > 0:
                    draw.ellipse([(x - size, y - size), (x + size, y + size)],
                               fill=color + (alpha,))
            
            img = img.filter(ImageFilter.GaussianBlur(1))
            frames.append(img)
        
        return AnimatedTexture(
            frames=frames,
            frame_duration=50,
            animation_type=AnimationType.FIRE
        )