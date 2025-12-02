"""
Partikel-System für realistische Effekte (Regen, Schnee, Feuer, etc.)
Inspiriert von Blender's Partikel-System mit Emitter und Canvas

Features:
- Verschiedene Partikel-Typen (Regen, Schnee, Funken, Rauch, Feuer, Nebel)
- Physik-Simulation (Gravitation, Wind, Kollision, Turbulenz)
- Realistische Texturen und Effekte
- Export als MP4, GIF, WebM
"""

import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Callable, Any
from enum import Enum, auto
import colorsys
import time


class ParticleType(Enum):
    """Verfügbare Partikel-Typen"""
    RAIN = auto()           # Regen
    SNOW = auto()           # Schnee
    SPARK = auto()          # Funken
    SMOKE = auto()          # Rauch
    FIRE = auto()           # Feuer
    FOG = auto()            # Nebel
    DUST = auto()           # Staub
    EMBER = auto()          # Glut
    MAGIC = auto()          # Magische Partikel
    LEAVES = auto()         # Fallende Blätter
    WATER_SPLASH = auto()   # Wasser-Spritzer
    BUBBLE = auto()         # Blasen
    CUSTOM = auto()         # Benutzerdefiniert


class BlendMode(Enum):
    """Blend-Modi für Partikel-Rendering"""
    NORMAL = auto()
    ADD = auto()            # Additiv (gut für Feuer, Funken)
    MULTIPLY = auto()
    SCREEN = auto()
    SOFT_LIGHT = auto()


@dataclass
class Vector3:
    """3D-Vektor für Position, Geschwindigkeit, etc."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __truediv__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)
    
    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self) -> 'Vector3':
        l = self.length()
        if l > 0:
            return self / l
        return Vector3()
    
    def dot(self, other: 'Vector3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: 'Vector3') -> 'Vector3':
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)
    
    def to_2d(self) -> Tuple[float, float]:
        """Projektion auf 2D (ignoriert z)"""
        return (self.x, self.y)


@dataclass
class Color:
    """RGBA Farbe"""
    r: float = 1.0  # 0-1
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0
    
    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.r, self.g, self.b, self.a)
    
    def to_int_tuple(self) -> Tuple[int, int, int, int]:
        return (int(self.r * 255), int(self.g * 255), 
                int(self.b * 255), int(self.a * 255))
    
    def lerp(self, other: 'Color', t: float) -> 'Color':
        """Lineare Interpolation zwischen zwei Farben"""
        return Color(
            self.r + (other.r - self.r) * t,
            self.g + (other.g - self.g) * t,
            self.b + (other.b - self.b) * t,
            self.a + (other.a - self.a) * t
        )
    
    @staticmethod
    def from_hsv(h: float, s: float, v: float, a: float = 1.0) -> 'Color':
        """Erstelle Farbe aus HSV"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return Color(r, g, b, a)


@dataclass
class Particle:
    """Einzelnes Partikel mit allen Eigenschaften"""
    position: Vector3 = field(default_factory=Vector3)
    velocity: Vector3 = field(default_factory=Vector3)
    acceleration: Vector3 = field(default_factory=Vector3)
    
    color: Color = field(default_factory=Color)
    start_color: Color = field(default_factory=Color)
    end_color: Color = field(default_factory=Color)
    
    size: float = 1.0
    start_size: float = 1.0
    end_size: float = 0.0
    
    rotation: float = 0.0
    rotation_speed: float = 0.0
    
    age: float = 0.0
    lifetime: float = 1.0
    
    # Für spezielle Effekte
    trail_positions: List[Vector3] = field(default_factory=list)
    trail_length: int = 0
    
    # Für Kollisionserkennung
    bounces: int = 0
    max_bounces: int = 0
    
    # Benutzerdefinierte Daten
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def alive(self) -> bool:
        return self.age < self.lifetime
    
    @property
    def life_progress(self) -> float:
        """0.0 = gerade geboren, 1.0 = am Ende"""
        return min(1.0, self.age / self.lifetime) if self.lifetime > 0 else 1.0
    
    def update_color_by_life(self):
        """Aktualisiere Farbe basierend auf Lebensfortschritt"""
        self.color = self.start_color.lerp(self.end_color, self.life_progress)
    
    def update_size_by_life(self):
        """Aktualisiere Größe basierend auf Lebensfortschritt"""
        self.size = self.start_size + (self.end_size - self.start_size) * self.life_progress


@dataclass
class EmitterShape:
    """Basis-Klasse für Emitter-Formen"""
    pass


@dataclass
class PointEmitter(EmitterShape):
    """Punkt-Emitter"""
    position: Vector3 = field(default_factory=Vector3)


@dataclass
class LineEmitter(EmitterShape):
    """Linien-Emitter"""
    start: Vector3 = field(default_factory=Vector3)
    end: Vector3 = field(default_factory=Vector3)


@dataclass
class RectEmitter(EmitterShape):
    """Rechteck-Emitter"""
    position: Vector3 = field(default_factory=Vector3)
    width: float = 100.0
    height: float = 100.0


@dataclass
class CircleEmitter(EmitterShape):
    """Kreis-Emitter"""
    position: Vector3 = field(default_factory=Vector3)
    radius: float = 50.0
    inner_radius: float = 0.0  # Für Ring-Form


@dataclass
class SphereEmitter(EmitterShape):
    """Kugel-Emitter (3D)"""
    position: Vector3 = field(default_factory=Vector3)
    radius: float = 50.0
    inner_radius: float = 0.0


@dataclass
class ForceField:
    """Kraftfeld für Partikel-Beeinflussung"""
    position: Vector3 = field(default_factory=Vector3)
    strength: float = 1.0
    radius: float = 100.0
    falloff: float = 1.0  # Exponent für Abnahme
    
    def apply(self, particle: Particle, direction: Vector3) -> Vector3:
        """Berechne Kraft auf Partikel"""
        dist = (particle.position - self.position).length()
        if dist > self.radius or dist == 0:
            return Vector3()
        
        factor = 1.0 - (dist / self.radius) ** self.falloff
        return direction * (self.strength * factor)


@dataclass
class WindForce(ForceField):
    """Wind-Kraft"""
    direction: Vector3 = field(default_factory=lambda: Vector3(1.0, 0.0, 0.0))
    turbulence: float = 0.0
    
    def apply(self, particle: Particle, _=None) -> Vector3:
        base = super().apply(particle, self.direction.normalize())
        if self.turbulence > 0:
            noise = Vector3(
                random.uniform(-1, 1) * self.turbulence,
                random.uniform(-1, 1) * self.turbulence,
                random.uniform(-1, 1) * self.turbulence
            )
            base = base + noise
        return base


@dataclass
class GravityForce(ForceField):
    """Schwerkraft"""
    direction: Vector3 = field(default_factory=lambda: Vector3(0.0, 1.0, 0.0))
    
    def apply(self, particle: Particle, _=None) -> Vector3:
        return self.direction * self.strength


@dataclass
class VortexForce(ForceField):
    """Wirbel-Kraft"""
    axis: Vector3 = field(default_factory=lambda: Vector3(0.0, 0.0, 1.0))
    inward_strength: float = 0.0
    
    def apply(self, particle: Particle, _=None) -> Vector3:
        to_center = self.position - particle.position
        dist = to_center.length()
        
        if dist > self.radius or dist == 0:
            return Vector3()
        
        factor = 1.0 - (dist / self.radius) ** self.falloff
        
        # Tangentiale Kraft (Rotation)
        tangent = self.axis.cross(to_center.normalize())
        rotation_force = tangent * (self.strength * factor)
        
        # Radiale Kraft (nach innen/außen)
        radial_force = to_center.normalize() * (self.inward_strength * factor)
        
        return rotation_force + radial_force


@dataclass 
class CollisionPlane:
    """Kollisionsebene"""
    position: Vector3 = field(default_factory=Vector3)
    normal: Vector3 = field(default_factory=lambda: Vector3(0.0, -1.0, 0.0))
    bounce: float = 0.5
    friction: float = 0.1
    
    def check_collision(self, particle: Particle) -> bool:
        """Prüfe ob Partikel die Ebene durchquert hat"""
        d = (particle.position - self.position).dot(self.normal)
        return d < 0
    
    def resolve(self, particle: Particle):
        """Löse Kollision auf"""
        # Reflektiere Geschwindigkeit
        dot = particle.velocity.dot(self.normal)
        reflection = particle.velocity - self.normal * (2 * dot)
        
        # Bounce und Friction anwenden
        particle.velocity = reflection * self.bounce
        
        # Partikel zurück auf die Ebene setzen
        d = (particle.position - self.position).dot(self.normal)
        particle.position = particle.position - self.normal * d


class ParticleEmitter:
    """
    Partikel-Emitter - erzeugt und verwaltet Partikel
    Ähnlich wie Blender's Emitter-System
    """
    
    def __init__(self, particle_type: ParticleType = ParticleType.RAIN):
        self.particle_type = particle_type
        self.particles: List[Particle] = []
        
        # Emitter-Einstellungen
        self.shape: EmitterShape = RectEmitter()
        self.emission_rate: float = 100.0  # Partikel pro Sekunde
        self.max_particles: int = 10000
        self.burst_count: int = 0  # Für einmalige Bursts
        
        # Partikel-Eigenschaften (mit Variation)
        self.lifetime: float = 2.0
        self.lifetime_variation: float = 0.5
        
        self.start_speed: float = 100.0
        self.speed_variation: float = 20.0
        self.direction: Vector3 = Vector3(0, 1, 0)
        self.spread: float = 0.1  # Streuung (0 = keine, 1 = volle Kugel)
        
        self.start_size: float = 5.0
        self.size_variation: float = 2.0
        self.end_size: float = 0.0
        
        self.start_color: Color = Color(1.0, 1.0, 1.0, 1.0)
        self.end_color: Color = Color(1.0, 1.0, 1.0, 0.0)
        self.color_variation: float = 0.0
        
        self.rotation_speed: float = 0.0
        self.rotation_variation: float = 0.0
        
        # Trail-Einstellungen
        self.trail_length: int = 0
        
        # Physik
        self.forces: List[ForceField] = []
        self.collision_planes: List[CollisionPlane] = []
        self.max_bounces: int = 0
        
        # Rendering
        self.blend_mode: BlendMode = BlendMode.NORMAL
        self.texture_id: Optional[str] = None
        
        # Interne Variablen
        self._emission_accumulator: float = 0.0
        self._time: float = 0.0
        
        # Standard-Presets anwenden
        self._apply_preset(particle_type)
    
    def _apply_preset(self, particle_type: ParticleType):
        """Wende Voreinstellungen für Partikeltyp an"""
        presets = {
            ParticleType.RAIN: self._preset_rain,
            ParticleType.SNOW: self._preset_snow,
            ParticleType.SPARK: self._preset_spark,
            ParticleType.SMOKE: self._preset_smoke,
            ParticleType.FIRE: self._preset_fire,
            ParticleType.FOG: self._preset_fog,
            ParticleType.DUST: self._preset_dust,
            ParticleType.EMBER: self._preset_ember,
            ParticleType.MAGIC: self._preset_magic,
            ParticleType.LEAVES: self._preset_leaves,
            ParticleType.WATER_SPLASH: self._preset_water_splash,
            ParticleType.BUBBLE: self._preset_bubble,
        }
        
        if particle_type in presets:
            presets[particle_type]()
    
    def _preset_rain(self):
        """Regen-Einstellungen"""
        self.emission_rate = 500
        self.lifetime = 1.0
        self.lifetime_variation = 0.2
        self.start_speed = 800
        self.speed_variation = 100
        self.direction = Vector3(0, 1, 0)
        self.spread = 0.02
        self.start_size = 2.0
        self.size_variation = 1.0
        self.end_size = 2.0
        self.start_color = Color(0.7, 0.8, 1.0, 0.6)
        self.end_color = Color(0.7, 0.8, 1.0, 0.3)
        self.trail_length = 5
        self.blend_mode = BlendMode.ADD
        
        # Leichte Schwerkraft
        self.forces = [GravityForce(strength=200)]
        
        # Boden-Kollision
        self.collision_planes = [
            CollisionPlane(position=Vector3(0, 600, 0), bounce=0.0)
        ]
    
    def _preset_snow(self):
        """Schnee-Einstellungen"""
        self.emission_rate = 100
        self.lifetime = 5.0
        self.lifetime_variation = 1.0
        self.start_speed = 50
        self.speed_variation = 20
        self.direction = Vector3(0, 1, 0)
        self.spread = 0.3
        self.start_size = 4.0
        self.size_variation = 2.0
        self.end_size = 4.0
        self.start_color = Color(1.0, 1.0, 1.0, 0.9)
        self.end_color = Color(1.0, 1.0, 1.0, 0.5)
        self.rotation_speed = 2.0
        self.rotation_variation = 1.0
        self.blend_mode = BlendMode.NORMAL
        
        # Leichte Schwerkraft und Wind
        self.forces = [
            GravityForce(strength=30),
            WindForce(direction=Vector3(1, 0, 0), strength=20, turbulence=10, radius=10000)
        ]
    
    def _preset_spark(self):
        """Funken-Einstellungen"""
        self.emission_rate = 50
        self.lifetime = 0.8
        self.lifetime_variation = 0.3
        self.start_speed = 300
        self.speed_variation = 100
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.5
        self.start_size = 3.0
        self.size_variation = 1.5
        self.end_size = 0.5
        self.start_color = Color(1.0, 0.8, 0.3, 1.0)
        self.end_color = Color(1.0, 0.3, 0.0, 0.0)
        self.trail_length = 8
        self.blend_mode = BlendMode.ADD
        
        self.forces = [GravityForce(strength=300)]
    
    def _preset_smoke(self):
        """Rauch-Einstellungen"""
        self.emission_rate = 30
        self.lifetime = 4.0
        self.lifetime_variation = 1.0
        self.start_speed = 50
        self.speed_variation = 20
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.2
        self.start_size = 20.0
        self.size_variation = 5.0
        self.end_size = 80.0
        self.start_color = Color(0.3, 0.3, 0.3, 0.5)
        self.end_color = Color(0.5, 0.5, 0.5, 0.0)
        self.rotation_speed = 0.5
        self.rotation_variation = 0.3
        self.blend_mode = BlendMode.NORMAL
        
        self.forces = [
            GravityForce(direction=Vector3(0, -1, 0), strength=20),
            WindForce(direction=Vector3(1, 0, 0), strength=30, turbulence=15, radius=10000)
        ]
    
    def _preset_fire(self):
        """Feuer-Einstellungen"""
        self.emission_rate = 100
        self.lifetime = 1.5
        self.lifetime_variation = 0.5
        self.start_speed = 100
        self.speed_variation = 30
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.15
        self.start_size = 15.0
        self.size_variation = 5.0
        self.end_size = 5.0
        self.start_color = Color(1.0, 0.9, 0.3, 0.9)
        self.end_color = Color(1.0, 0.2, 0.0, 0.0)
        self.color_variation = 0.1
        self.blend_mode = BlendMode.ADD
        
        self.forces = [
            GravityForce(direction=Vector3(0, -1, 0), strength=80),
            WindForce(direction=Vector3(1, 0, 0), strength=10, turbulence=20, radius=10000)
        ]
    
    def _preset_fog(self):
        """Nebel-Einstellungen"""
        self.emission_rate = 10
        self.lifetime = 10.0
        self.lifetime_variation = 2.0
        self.start_speed = 10
        self.speed_variation = 5
        self.direction = Vector3(1, 0, 0)
        self.spread = 0.5
        self.start_size = 100.0
        self.size_variation = 30.0
        self.end_size = 150.0
        self.start_color = Color(0.8, 0.8, 0.85, 0.2)
        self.end_color = Color(0.8, 0.8, 0.85, 0.0)
        self.blend_mode = BlendMode.NORMAL
        
        self.forces = [
            WindForce(direction=Vector3(1, 0, 0), strength=5, turbulence=3, radius=10000)
        ]
    
    def _preset_dust(self):
        """Staub-Einstellungen"""
        self.emission_rate = 20
        self.lifetime = 3.0
        self.lifetime_variation = 1.0
        self.start_speed = 20
        self.speed_variation = 10
        self.direction = Vector3(0, 0, 0)
        self.spread = 1.0
        self.start_size = 2.0
        self.size_variation = 1.0
        self.end_size = 1.0
        self.start_color = Color(0.8, 0.7, 0.5, 0.4)
        self.end_color = Color(0.8, 0.7, 0.5, 0.0)
        self.blend_mode = BlendMode.NORMAL
        
        self.forces = [
            GravityForce(strength=5),
            WindForce(direction=Vector3(1, 0, 0), strength=10, turbulence=8, radius=10000)
        ]
    
    def _preset_ember(self):
        """Glut-Einstellungen"""
        self.emission_rate = 15
        self.lifetime = 3.0
        self.lifetime_variation = 1.0
        self.start_speed = 80
        self.speed_variation = 30
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.3
        self.start_size = 4.0
        self.size_variation = 2.0
        self.end_size = 1.0
        self.start_color = Color(1.0, 0.6, 0.1, 1.0)
        self.end_color = Color(0.8, 0.2, 0.0, 0.0)
        self.trail_length = 3
        self.blend_mode = BlendMode.ADD
        
        self.forces = [
            GravityForce(direction=Vector3(0, -1, 0), strength=30),
            WindForce(direction=Vector3(1, 0.5, 0), strength=40, turbulence=20, radius=10000)
        ]
    
    def _preset_magic(self):
        """Magische Partikel-Einstellungen"""
        self.emission_rate = 40
        self.lifetime = 2.0
        self.lifetime_variation = 0.5
        self.start_speed = 60
        self.speed_variation = 30
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.4
        self.start_size = 8.0
        self.size_variation = 3.0
        self.end_size = 2.0
        self.start_color = Color(0.5, 0.3, 1.0, 1.0)
        self.end_color = Color(0.8, 0.5, 1.0, 0.0)
        self.color_variation = 0.2
        self.trail_length = 10
        self.blend_mode = BlendMode.ADD
        
        self.forces = [
            VortexForce(strength=50, radius=200, inward_strength=10)
        ]
    
    def _preset_leaves(self):
        """Fallende Blätter-Einstellungen"""
        self.emission_rate = 10
        self.lifetime = 6.0
        self.lifetime_variation = 2.0
        self.start_speed = 30
        self.speed_variation = 15
        self.direction = Vector3(0, 1, 0)
        self.spread = 0.4
        self.start_size = 12.0
        self.size_variation = 4.0
        self.end_size = 12.0
        self.start_color = Color(0.8, 0.6, 0.2, 0.9)
        self.end_color = Color(0.6, 0.4, 0.1, 0.7)
        self.color_variation = 0.2
        self.rotation_speed = 3.0
        self.rotation_variation = 2.0
        self.blend_mode = BlendMode.NORMAL
        
        self.forces = [
            GravityForce(strength=40),
            WindForce(direction=Vector3(1, 0, 0), strength=30, turbulence=25, radius=10000)
        ]
    
    def _preset_water_splash(self):
        """Wasser-Spritzer-Einstellungen"""
        self.emission_rate = 0
        self.burst_count = 50
        self.lifetime = 0.8
        self.lifetime_variation = 0.2
        self.start_speed = 250
        self.speed_variation = 100
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.4
        self.start_size = 4.0
        self.size_variation = 2.0
        self.end_size = 2.0
        self.start_color = Color(0.6, 0.8, 1.0, 0.8)
        self.end_color = Color(0.7, 0.9, 1.0, 0.0)
        self.trail_length = 3
        self.blend_mode = BlendMode.ADD
        
        self.forces = [GravityForce(strength=500)]
    
    def _preset_bubble(self):
        """Blasen-Einstellungen"""
        self.emission_rate = 15
        self.lifetime = 4.0
        self.lifetime_variation = 1.5
        self.start_speed = 40
        self.speed_variation = 15
        self.direction = Vector3(0, -1, 0)
        self.spread = 0.2
        self.start_size = 8.0
        self.size_variation = 4.0
        self.end_size = 12.0
        self.start_color = Color(0.8, 0.9, 1.0, 0.4)
        self.end_color = Color(0.9, 0.95, 1.0, 0.0)
        self.blend_mode = BlendMode.ADD
        
        self.forces = [
            GravityForce(direction=Vector3(0, -1, 0), strength=20),
            WindForce(direction=Vector3(1, 0, 0), strength=10, turbulence=8, radius=10000)
        ]
    
    def _get_spawn_position(self) -> Vector3:
        """Berechne Spawn-Position basierend auf Emitter-Form"""
        if isinstance(self.shape, PointEmitter):
            return Vector3(self.shape.position.x, self.shape.position.y, self.shape.position.z)
        
        elif isinstance(self.shape, LineEmitter):
            t = random.random()
            return Vector3(
                self.shape.start.x + (self.shape.end.x - self.shape.start.x) * t,
                self.shape.start.y + (self.shape.end.y - self.shape.start.y) * t,
                self.shape.start.z + (self.shape.end.z - self.shape.start.z) * t
            )
        
        elif isinstance(self.shape, RectEmitter):
            return Vector3(
                self.shape.position.x + random.uniform(-self.shape.width/2, self.shape.width/2),
                self.shape.position.y + random.uniform(-self.shape.height/2, self.shape.height/2),
                self.shape.position.z
            )
        
        elif isinstance(self.shape, CircleEmitter):
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(self.shape.inner_radius, self.shape.radius)
            return Vector3(
                self.shape.position.x + math.cos(angle) * r,
                self.shape.position.y + math.sin(angle) * r,
                self.shape.position.z
            )
        
        elif isinstance(self.shape, SphereEmitter):
            # Gleichmäßige Verteilung auf Kugel
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            r = random.uniform(self.shape.inner_radius, self.shape.radius)
            return Vector3(
                self.shape.position.x + r * math.sin(phi) * math.cos(theta),
                self.shape.position.y + r * math.sin(phi) * math.sin(theta),
                self.shape.position.z + r * math.cos(phi)
            )
        
        return Vector3()
    
    def _get_spawn_velocity(self) -> Vector3:
        """Berechne initiale Geschwindigkeit mit Streuung"""
        speed = self.start_speed + random.uniform(-1, 1) * self.speed_variation
        
        # Basis-Richtung
        dir_vec = self.direction.normalize()
        
        # Streuung hinzufügen
        if self.spread > 0:
            # Zufällige Abweichung
            spread_angle = self.spread * math.pi
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, spread_angle)
            
            # Zufällige Richtung im Kegel
            rand_dir = Vector3(
                math.sin(phi) * math.cos(theta),
                math.cos(phi),
                math.sin(phi) * math.sin(theta)
            )
            
            # Rotiere zur Basis-Richtung (vereinfacht)
            if abs(dir_vec.y) < 0.999:
                # Berechne Rotation
                up = Vector3(0, 1, 0)
                axis = up.cross(dir_vec)
                angle = math.acos(up.dot(dir_vec))
                
                # Rodrigues' Rotation (vereinfacht)
                c = math.cos(angle)
                s = math.sin(angle)
                k = axis.normalize()
                
                v_rot = rand_dir * c + k.cross(rand_dir) * s + k * (k.dot(rand_dir)) * (1 - c)
                dir_vec = v_rot.normalize()
            else:
                dir_vec = rand_dir if dir_vec.y > 0 else Vector3(rand_dir.x, -rand_dir.y, rand_dir.z)
        
        return dir_vec * speed
    
    def _create_particle(self) -> Particle:
        """Erstelle ein neues Partikel"""
        lifetime = max(0.1, self.lifetime + random.uniform(-1, 1) * self.lifetime_variation)
        
        size = max(0.1, self.start_size + random.uniform(-1, 1) * self.size_variation)
        
        # Farbvariation
        start_color = Color(
            max(0, min(1, self.start_color.r + random.uniform(-1, 1) * self.color_variation)),
            max(0, min(1, self.start_color.g + random.uniform(-1, 1) * self.color_variation)),
            max(0, min(1, self.start_color.b + random.uniform(-1, 1) * self.color_variation)),
            self.start_color.a
        )
        end_color = Color(
            max(0, min(1, self.end_color.r + random.uniform(-1, 1) * self.color_variation)),
            max(0, min(1, self.end_color.g + random.uniform(-1, 1) * self.color_variation)),
            max(0, min(1, self.end_color.b + random.uniform(-1, 1) * self.color_variation)),
            self.end_color.a
        )
        
        rotation = random.uniform(0, 2 * math.pi)
        rot_speed = self.rotation_speed + random.uniform(-1, 1) * self.rotation_variation
        
        return Particle(
            position=self._get_spawn_position(),
            velocity=self._get_spawn_velocity(),
            start_color=start_color,
            end_color=end_color,
            color=start_color,
            start_size=size,
            end_size=self.end_size,
            size=size,
            lifetime=lifetime,
            rotation=rotation,
            rotation_speed=rot_speed,
            trail_length=self.trail_length,
            max_bounces=self.max_bounces
        )
    
    def emit(self, count: int = 1):
        """Emittiere eine bestimmte Anzahl Partikel"""
        for _ in range(count):
            if len(self.particles) < self.max_particles:
                self.particles.append(self._create_particle())
    
    def burst(self, count: Optional[int] = None):
        """Einmaliger Burst von Partikeln"""
        self.emit(count or self.burst_count)
    
    def update(self, dt: float):
        """Aktualisiere alle Partikel"""
        self._time += dt
        
        # Kontinuierliche Emission
        if self.emission_rate > 0:
            self._emission_accumulator += self.emission_rate * dt
            while self._emission_accumulator >= 1.0:
                self.emit(1)
                self._emission_accumulator -= 1.0
        
        # Partikel aktualisieren
        alive_particles = []
        
        for particle in self.particles:
            # Alter erhöhen
            particle.age += dt
            
            if not particle.alive:
                continue
            
            # Trail aktualisieren
            if particle.trail_length > 0:
                particle.trail_positions.insert(0, Vector3(
                    particle.position.x, 
                    particle.position.y, 
                    particle.position.z
                ))
                while len(particle.trail_positions) > particle.trail_length:
                    particle.trail_positions.pop()
            
            # Kräfte anwenden
            total_force = Vector3()
            for force in self.forces:
                total_force = total_force + force.apply(particle)
            
            particle.acceleration = total_force
            
            # Physik-Integration (Verlet-ähnlich)
            particle.velocity = particle.velocity + particle.acceleration * dt
            particle.position = particle.position + particle.velocity * dt
            
            # Kollisionen
            for plane in self.collision_planes:
                if plane.check_collision(particle):
                    if particle.bounces < particle.max_bounces or particle.max_bounces == 0:
                        plane.resolve(particle)
                        particle.bounces += 1
                    else:
                        particle.age = particle.lifetime  # Partikel "töten"
            
            # Rotation
            particle.rotation += particle.rotation_speed * dt
            
            # Farbe und Größe interpolieren
            particle.update_color_by_life()
            particle.update_size_by_life()
            
            alive_particles.append(particle)
        
        self.particles = alive_particles
    
    def clear(self):
        """Entferne alle Partikel"""
        self.particles.clear()
        self._emission_accumulator = 0.0


class ParticleCanvas:
    """
    Canvas zum Rendern von Partikeln
    Unterstützt mehrere Emitter und verschiedene Render-Modi
    """
    
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self.emitters: List[ParticleEmitter] = []
        self.background_color: Color = Color(0, 0, 0, 0)  # Transparent
        
        # Render-Einstellungen
        self.motion_blur: float = 0.0  # 0-1
        self.glow_strength: float = 0.0
        self.glow_radius: int = 10
        
        # Frame-Buffer für Motion-Blur
        self._previous_frame: Optional[np.ndarray] = None
    
    def add_emitter(self, emitter: ParticleEmitter) -> ParticleEmitter:
        """Füge Emitter hinzu"""
        self.emitters.append(emitter)
        return emitter
    
    def remove_emitter(self, emitter: ParticleEmitter):
        """Entferne Emitter"""
        if emitter in self.emitters:
            self.emitters.remove(emitter)
    
    def update(self, dt: float):
        """Aktualisiere alle Emitter"""
        for emitter in self.emitters:
            emitter.update(dt)
    
    def render_frame(self) -> np.ndarray:
        """
        Rendere aktuellen Frame als NumPy-Array (RGBA)
        Gibt ein (height, width, 4) Array zurück
        """
        # Erstelle leeren Frame
        frame = np.zeros((self.height, self.width, 4), dtype=np.float32)
        
        # Hintergrundfarbe
        frame[:, :, 0] = self.background_color.r
        frame[:, :, 1] = self.background_color.g
        frame[:, :, 2] = self.background_color.b
        frame[:, :, 3] = self.background_color.a
        
        # Alle Partikel rendern
        for emitter in self.emitters:
            self._render_emitter(frame, emitter)
        
        # Motion Blur
        if self.motion_blur > 0 and self._previous_frame is not None:
            frame = frame * (1 - self.motion_blur) + self._previous_frame * self.motion_blur
        
        self._previous_frame = frame.copy()
        
        # Glow-Effekt
        if self.glow_strength > 0:
            frame = self._apply_glow(frame)
        
        # Clip auf 0-1
        frame = np.clip(frame, 0, 1)
        
        return frame
    
    def _render_emitter(self, frame: np.ndarray, emitter: ParticleEmitter):
        """Rendere alle Partikel eines Emitters"""
        for particle in emitter.particles:
            self._render_particle(frame, particle, emitter.blend_mode)
    
    def _render_particle(self, frame: np.ndarray, particle: Particle, blend_mode: BlendMode):
        """Rendere ein einzelnes Partikel"""
        x, y = int(particle.position.x), int(particle.position.y)
        size = max(1, int(particle.size))
        half_size = size // 2
        
        # Bounding Box
        x1 = max(0, x - half_size)
        y1 = max(0, y - half_size)
        x2 = min(self.width, x + half_size + 1)
        y2 = min(self.height, y + half_size + 1)
        
        if x1 >= x2 or y1 >= y2:
            return
        
        # Partikel-Farbe
        color = particle.color
        
        # Trail rendern
        if particle.trail_length > 0 and len(particle.trail_positions) > 0:
            self._render_trail(frame, particle, blend_mode)
        
        # Einfaches Kreis-Rendering mit Soft-Edge
        for py in range(y1, y2):
            for px in range(x1, x2):
                dx = px - x
                dy = py - y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist <= half_size:
                    # Soft edge
                    alpha = 1.0 - (dist / half_size) ** 2 if half_size > 0 else 1.0
                    alpha *= color.a
                    
                    self._blend_pixel(frame, px, py, color, alpha, blend_mode)
    
    def _render_trail(self, frame: np.ndarray, particle: Particle, blend_mode: BlendMode):
        """Rendere Partikel-Trail"""
        if len(particle.trail_positions) < 2:
            return
        
        for i, pos in enumerate(particle.trail_positions):
            # Trail wird schwächer
            trail_alpha = (1.0 - i / len(particle.trail_positions)) * 0.5
            trail_size = max(1, int(particle.size * (1.0 - i / len(particle.trail_positions) * 0.5)))
            
            x, y = int(pos.x), int(pos.y)
            half_size = trail_size // 2
            
            # Überspringe wenn half_size 0 ist
            if half_size <= 0:
                continue
            
            x1 = max(0, x - half_size)
            y1 = max(0, y - half_size)
            x2 = min(self.width, x + half_size + 1)
            y2 = min(self.height, y + half_size + 1)
            
            if x1 >= x2 or y1 >= y2:
                continue
            
            for py in range(y1, y2):
                for px in range(x1, x2):
                    dx = px - x
                    dy = py - y
                    dist = math.sqrt(dx*dx + dy*dy)
                    
                    if dist <= half_size:
                        alpha = (1.0 - dist / half_size) * trail_alpha * particle.color.a
                        self._blend_pixel(frame, px, py, particle.color, alpha, blend_mode)
    
    def _blend_pixel(self, frame: np.ndarray, x: int, y: int, 
                     color: Color, alpha: float, blend_mode: BlendMode):
        """Blende Pixel mit verschiedenen Modi"""
        if alpha <= 0:
            return
        
        dst = frame[y, x]
        src = np.array([color.r, color.g, color.b, alpha])
        
        if blend_mode == BlendMode.NORMAL:
            # Standard Alpha-Blending
            frame[y, x, :3] = dst[:3] * (1 - alpha) + src[:3] * alpha
            frame[y, x, 3] = min(1.0, dst[3] + alpha * (1 - dst[3]))
        
        elif blend_mode == BlendMode.ADD:
            # Additives Blending
            frame[y, x, :3] = np.minimum(1.0, dst[:3] + src[:3] * alpha)
            frame[y, x, 3] = min(1.0, dst[3] + alpha)
        
        elif blend_mode == BlendMode.MULTIPLY:
            frame[y, x, :3] = dst[:3] * (src[:3] * alpha + (1 - alpha))
            frame[y, x, 3] = min(1.0, dst[3] + alpha * (1 - dst[3]))
        
        elif blend_mode == BlendMode.SCREEN:
            frame[y, x, :3] = 1 - (1 - dst[:3]) * (1 - src[:3] * alpha)
            frame[y, x, 3] = min(1.0, dst[3] + alpha * (1 - dst[3]))
    
    def _apply_glow(self, frame: np.ndarray) -> np.ndarray:
        """Wende Glow-Effekt an"""
        try:
            from scipy.ndimage import gaussian_filter
            
            # Nur helle Bereiche extrahieren
            bright = frame.copy()
            bright[:, :, :3] = np.maximum(0, bright[:, :, :3] - 0.5) * 2
            
            # Blur anwenden
            for i in range(3):
                bright[:, :, i] = gaussian_filter(bright[:, :, i], sigma=self.glow_radius)
            
            # Mit Original kombinieren
            result = frame + bright * self.glow_strength
            return np.clip(result, 0, 1)
        except ImportError:
            return frame
    
    def get_total_particles(self) -> int:
        """Zähle alle aktiven Partikel"""
        return sum(len(e.particles) for e in self.emitters)


# Preset-Funktionen für schnellen Zugriff
def create_rain_effect(width: int = 1920, height: int = 1080) -> Tuple[ParticleCanvas, ParticleEmitter]:
    """Erstelle Regen-Effekt"""
    canvas = ParticleCanvas(width, height)
    emitter = ParticleEmitter(ParticleType.RAIN)
    emitter.shape = RectEmitter(position=Vector3(width/2, -50, 0), width=width + 200, height=10)
    emitter.collision_planes = [CollisionPlane(position=Vector3(0, height, 0))]
    canvas.add_emitter(emitter)
    return canvas, emitter


def create_snow_effect(width: int = 1920, height: int = 1080) -> Tuple[ParticleCanvas, ParticleEmitter]:
    """Erstelle Schnee-Effekt"""
    canvas = ParticleCanvas(width, height)
    emitter = ParticleEmitter(ParticleType.SNOW)
    emitter.shape = RectEmitter(position=Vector3(width/2, -50, 0), width=width + 200, height=10)
    canvas.add_emitter(emitter)
    return canvas, emitter


def create_fire_effect(x: float, y: float) -> Tuple[ParticleCanvas, ParticleEmitter]:
    """Erstelle Feuer-Effekt an Position"""
    canvas = ParticleCanvas(400, 400)
    emitter = ParticleEmitter(ParticleType.FIRE)
    emitter.shape = CircleEmitter(position=Vector3(x, y, 0), radius=20)
    canvas.add_emitter(emitter)
    canvas.glow_strength = 0.5
    canvas.glow_radius = 15
    return canvas, emitter


def create_magic_effect(x: float, y: float) -> Tuple[ParticleCanvas, ParticleEmitter]:
    """Erstelle magischen Effekt an Position"""
    canvas = ParticleCanvas(400, 400)
    emitter = ParticleEmitter(ParticleType.MAGIC)
    emitter.shape = CircleEmitter(position=Vector3(x, y, 0), radius=30)
    # Vortex um das Zentrum
    emitter.forces.append(VortexForce(position=Vector3(x, y, 0), strength=100, radius=150))
    canvas.add_emitter(emitter)
    canvas.glow_strength = 0.7
    canvas.glow_radius = 20
    return canvas, emitter


if __name__ == "__main__":
    # Test
    canvas, emitter = create_rain_effect(800, 600)
    
    # Simulation
    for i in range(60):
        canvas.update(1/60)
        frame = canvas.render_frame()
        print(f"Frame {i}: {canvas.get_total_particles()} Partikel")
