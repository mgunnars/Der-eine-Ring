"""
2D/2.5D Partikel-System mit Perspektive von oben
Realistischer Regen mit kleinen, schnellen Tropfen
"""

import math
import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum

from particle_system import (
    Vector3, Color, Particle, ParticleEmitter, ParticleType, BlendMode,
    RectEmitter, GravityForce, WindForce, CollisionPlane
)


class ViewAngle(Enum):
    """Vordefinierte Kamera-Winkel"""
    TOP_DOWN = 0       # Direkt von oben (2D)
    SLIGHT_ANGLE = 15  # Leicht geneigt
    ISOMETRIC = 30     # Isometrisch (2.5D)
    DRAMATIC = 45      # Dramatischer Winkel
    SIDE = 75          # Fast seitlich


@dataclass
class Ripple:
    """Einzelne Welle auf der Wasseroberfläche"""
    x: float
    y: float
    radius: float = 0.0
    max_radius: float = 40.0
    strength: float = 1.0
    speed: float = 60.0
    age: float = 0.0
    lifetime: float = 1.5
    
    @property
    def alive(self) -> bool:
        return self.age < self.lifetime and self.radius < self.max_radius
    
    @property
    def alpha(self) -> float:
        return max(0, 1.0 - (self.age / self.lifetime) ** 0.5)
    
    def update(self, dt: float):
        self.age += dt
        self.radius += self.speed * dt
        self.speed *= 0.97


@dataclass
class Splash:
    """Splash-Partikel beim Aufprall"""
    x: float
    y: float
    particles: List[Dict] = field(default_factory=list)
    age: float = 0.0
    lifetime: float = 0.3
    
    def __post_init__(self):
        num_particles = random.randint(2, 5)
        for _ in range(num_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(15, 40)
            self.particles.append({
                'x': self.x,
                'y': self.y,
                'vx': math.cos(angle) * speed,
                'vy': -random.uniform(20, 50),
                'size': random.uniform(0.5, 1.5),
                'alpha': 1.0
            })
    
    @property
    def alive(self) -> bool:
        return self.age < self.lifetime
    
    def update(self, dt: float):
        self.age += dt
        gravity = 150
        for p in self.particles:
            p['vy'] += gravity * dt
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['alpha'] = max(0, 1.0 - self.age / self.lifetime)


class WaterSurface:
    """Wasseroberfläche mit Wellen-Simulation und einstellbaren Bounds"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Bounds der Wasserfläche (Rechteck)
        self.bounds_x = 0
        self.bounds_y = height * 0.85
        self.bounds_width = width
        self.bounds_height = height * 0.15
        
        self.ripples: List[Ripple] = []
        self.splashes: List[Splash] = []
        self.max_ripples = 150
        self.max_splashes = 80
        
        self.ripple_speed = 60.0
        self.ripple_max_radius = 40.0
        self.ripple_lifetime = 1.5
        self.splash_enabled = True
        
        # Aussehen
        self.water_color = Color(0.2, 0.4, 0.6, 0.4)  # Wasserfarbe mit Alpha
        self.ripple_color = Color(0.7, 0.85, 1.0, 0.5)
        
        # Glas/Reflektion Optionen
        self.glass_effect = False       # Reflektives Glas-Aussehen
        self.glass_reflection = 0.4     # Reflexionsstärke
        
        # Transparenz der Wasserfarbe (0 = unsichtbar, 1 = solid)
        self.water_opacity = 0.4
    
    def set_bounds(self, x: float, y: float, width: float, height: float):
        """Setze die Bounds der Wasserfläche"""
        self.bounds_x = x
        self.bounds_y = y
        self.bounds_width = width
        self.bounds_height = height
    
    def point_in_bounds(self, x: float, y: float) -> bool:
        """Prüfe ob Punkt innerhalb der Wasserfläche liegt"""
        return (self.bounds_x <= x <= self.bounds_x + self.bounds_width and
                self.bounds_y <= y <= self.bounds_y + self.bounds_height)
    
    def get_depth_factor(self, y: float) -> float:
        """Berechne Tiefenfaktor (0 = oben, 1 = unten)"""
        if self.bounds_height <= 0:
            return 0
        return max(0, min(1, (y - self.bounds_y) / self.bounds_height))
    
    def add_ripple(self, x: float, y: float, strength: float = 1.0):
        if len(self.ripples) < self.max_ripples:
            self.ripples.append(Ripple(
                x=x, y=y,
                max_radius=self.ripple_max_radius * (0.5 + strength * 0.5),
                strength=strength,
                speed=self.ripple_speed,
                lifetime=self.ripple_lifetime
            ))
    
    def add_splash(self, x: float, y: float):
        if self.splash_enabled and len(self.splashes) < self.max_splashes:
            self.splashes.append(Splash(x=x, y=y))
    
    def update(self, dt: float):
        for ripple in self.ripples:
            ripple.update(dt)
        self.ripples = [r for r in self.ripples if r.alive]
        
        for splash in self.splashes:
            splash.update(dt)
        self.splashes = [s for s in self.splashes if s.alive]


@dataclass
class RaindropAppearance:
    """Aussehen eines Regentropfens - minimalistisch und realistisch"""
    # Glas-Effekt (dezent)
    glass_enabled: bool = True
    refraction_strength: float = 0.2
    specular_strength: float = 0.4
    
    # Farbe - sehr transparent und subtil
    base_color: Color = field(default_factory=lambda: Color(0.7, 0.8, 0.9, 0.3))
    
    # Bewegungsunschärfe
    motion_blur: float = 0.6


class ParticleSystem2D:
    """2D/2.5D Partikel-System mit echter Perspektive"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Kamera - 0° = von oben, 90° = seitlich
        self.camera_angle = 30.0
        
        self.emitters: List[ParticleEmitter] = []
        self.water_surface: Optional[WaterSurface] = None
        self.water_level_y = height * 0.9
        
        self.raindrop_appearance = RaindropAppearance()
        self.background_color = Color(0, 0, 0, 0)
        
        self.total_particles = 0
        self.total_ripples = 0
    
    def set_camera_angle(self, angle: float):
        """Setze Kamera-Winkel (0-90 Grad)"""
        self.camera_angle = max(0, min(90, angle))
        # Bei Winkeländerung Emitter neu konfigurieren
        self._reconfigure_emitters()
    
    def _reconfigure_emitters(self):
        """Konfiguriere Emitter basierend auf Kamera-Winkel"""
        angle_rad = math.radians(self.camera_angle)
        
        for emitter in self.emitters:
            if emitter.particle_type == ParticleType.RAIN:
                # Bei 0° (von oben): Tropfen fallen "auf uns zu" - kurze Striche, fast Punkte
                # Bei 90° (seitlich): Tropfen fallen seitlich - lange vertikale Striche
                
                # Richtung anpassen
                # cos(0) = 1, sin(0) = 0 -> bei 0° fallen Tropfen auf Kamera zu (fast keine y-Bewegung im 2D)
                # cos(90) = 0, sin(90) = 1 -> bei 90° fallen Tropfen nach unten (volle y-Bewegung)
                
                vertical_component = math.sin(angle_rad)  # 0 bei 0°, 1 bei 90°
                depth_component = math.cos(angle_rad)     # 1 bei 0°, 0 bei 90°
                
                emitter.direction = Vector3(0, vertical_component * 0.8 + 0.2, 0)
                emitter.direction.normalize()  # In-place normalization
                
                # Geschwindigkeit: Langsamer für realistischeren Regen
                # Bei flachem Winkel noch langsamer (Tiefe)
                base_speed = 80 + 60 * vertical_component  # Viel langsamer!
                emitter.start_speed = base_speed
    
    def enable_water_surface(self, y_position: Optional[float] = None):
        self.water_surface = WaterSurface(self.width, self.height)
        self.water_level_y = y_position if y_position else self.height * 0.9
    
    def add_rain_emitter(self, intensity: float = 1.0, 
                         wind_angle: float = 0.0,
                         wind_strength: float = 0.0) -> ParticleEmitter:
        """Füge Regen-Emitter hinzu - realistische kleine Tropfen"""
        emitter = ParticleEmitter(ParticleType.RAIN)
        
        # Großer Emitter-Bereich über dem Bildschirm
        emitter.shape = RectEmitter(
            position=Vector3(self.width / 2, -30, 0),
            width=self.width + 100,
            height=10
        )
        
        # Viele kleine, schnelle Tropfen
        emitter.emission_rate = int(300 * intensity)
        emitter.lifetime = 2.0
        
        # KLEINE Tropfen! Das ist der Schlüssel zu Realismus
        emitter.start_size = 1.0 + 0.5 * intensity  # Sehr klein: 1-2 Pixel
        emitter.size_variation = 0.5
        emitter.end_size = emitter.start_size * 0.8
        
        # Initiale Richtung (wird durch _reconfigure_emitters angepasst)
        emitter.direction = Vector3(0, 1, 0)
        emitter.spread = 0.03  # Leichte Streuung
        emitter.start_speed = 120  # Viel langsamer!
        emitter.speed_variation = 30
        
        # Farbe: Sehr transparent
        emitter.start_color = self.raindrop_appearance.base_color
        emitter.end_color = Color(
            self.raindrop_appearance.base_color.r,
            self.raindrop_appearance.base_color.g,
            self.raindrop_appearance.base_color.b,
            0.15
        )
        
        # Trail für Bewegungsunschärfe
        emitter.trail_length = 5
        
        emitter.blend_mode = BlendMode.ADD
        
        # Physik - sanftere Gravitation
        emitter.forces.clear()
        emitter.forces.append(GravityForce(strength=100))  # Viel sanfter
        
        if wind_strength > 0:
            wind_rad = math.radians(wind_angle)
            emitter.forces.append(WindForce(
                direction=Vector3(math.cos(wind_rad), 0, 0),
                strength=wind_strength,
                turbulence=wind_strength * 0.2
            ))
        
        # KEINE Kollisionsebene mehr - Partikel werden im update() 
        # zufällig auf der Wasserfläche entfernt
        emitter.collision_planes = []
        
        self.emitters.append(emitter)
        self._reconfigure_emitters()
        return emitter
    
    def add_snow_emitter(self, intensity: float = 1.0,
                         wind_strength: float = 20.0) -> ParticleEmitter:
        """Schneeflocken - langsam, schwebend, mit Windeinfluss"""
        emitter = ParticleEmitter(ParticleType.SNOW)
        
        emitter.shape = RectEmitter(
            position=Vector3(self.width / 2, -20, 0),
            width=self.width + 150,
            height=20
        )
        
        emitter.emission_rate = int(80 * intensity)
        emitter.lifetime = 8.0  # Lange Lebenszeit
        
        # Schneeflocken: größer als Regen, aber sehr leicht
        emitter.start_size = 2.0 + 1.5 * intensity
        emitter.size_variation = 1.0
        emitter.end_size = emitter.start_size * 0.9
        
        emitter.direction = Vector3(0, 1, 0)
        emitter.spread = 0.2  # Mehr Streuung
        emitter.start_speed = 20  # Sehr langsam!
        emitter.speed_variation = 10
        
        # Weiß, leicht transparent
        emitter.start_color = Color(1.0, 1.0, 1.0, 0.8)
        emitter.end_color = Color(1.0, 1.0, 1.0, 0.3)
        
        emitter.trail_length = 0  # Kein Trail
        emitter.blend_mode = BlendMode.ADD
        
        # Sehr leichte Gravitation + Wind
        emitter.forces.clear()
        emitter.forces.append(GravityForce(strength=15))
        emitter.forces.append(WindForce(
            direction=Vector3(1, 0, 0),
            strength=wind_strength,
            turbulence=wind_strength * 0.8  # Viel Turbulenz für Wirbel
        ))
        
        self.emitters.append(emitter)
        return emitter
    
    def add_leaves_emitter(self, intensity: float = 1.0,
                           wind_strength: float = 40.0) -> ParticleEmitter:
        """Fallende Blätter - langsam, taumelnd"""
        emitter = ParticleEmitter(ParticleType.LEAVES)
        
        emitter.shape = RectEmitter(
            position=Vector3(self.width / 2, -30, 0),
            width=self.width + 200,
            height=30
        )
        
        emitter.emission_rate = int(15 * intensity)
        emitter.lifetime = 10.0
        
        # Blätter: mittelgroß
        emitter.start_size = 4.0 + 2.0 * intensity
        emitter.size_variation = 2.0
        emitter.end_size = emitter.start_size
        
        emitter.direction = Vector3(0, 1, 0)
        emitter.spread = 0.3
        emitter.start_speed = 15
        emitter.speed_variation = 8
        
        # Herbstfarben (wird im Renderer variiert)
        emitter.start_color = Color(0.8, 0.5, 0.1, 0.9)
        emitter.end_color = Color(0.6, 0.3, 0.05, 0.7)
        
        emitter.trail_length = 0
        emitter.blend_mode = BlendMode.NORMAL
        
        # Leichte Gravitation + starker Wind
        emitter.forces.clear()
        emitter.forces.append(GravityForce(strength=20))
        emitter.forces.append(WindForce(
            direction=Vector3(1, 0.2, 0),
            strength=wind_strength,
            turbulence=wind_strength * 1.2  # Sehr viel Turbulenz
        ))
        
        self.emitters.append(emitter)
        return emitter
    
    def add_dust_emitter(self, intensity: float = 1.0,
                         wind_strength: float = 30.0) -> ParticleEmitter:
        """Staubpartikel - schwebend, diffus"""
        emitter = ParticleEmitter(ParticleType.DUST)
        
        # Staub von überall
        emitter.shape = RectEmitter(
            position=Vector3(self.width / 2, self.height / 2, 0),
            width=self.width,
            height=self.height
        )
        
        emitter.emission_rate = int(50 * intensity)
        emitter.lifetime = 6.0
        
        emitter.start_size = 1.5
        emitter.size_variation = 1.0
        emitter.end_size = 0.5
        
        emitter.direction = Vector3(0.5, -0.2, 0)
        emitter.spread = 0.8
        emitter.start_speed = 10
        emitter.speed_variation = 8
        
        # Bräunlich-grau
        emitter.start_color = Color(0.6, 0.5, 0.4, 0.3)
        emitter.end_color = Color(0.5, 0.45, 0.4, 0.0)
        
        emitter.trail_length = 0
        emitter.blend_mode = BlendMode.ADD
        
        emitter.forces.clear()
        emitter.forces.append(WindForce(
            direction=Vector3(1, 0, 0),
            strength=wind_strength,
            turbulence=wind_strength * 0.5
        ))
        
        self.emitters.append(emitter)
        return emitter
    
    def add_fog_emitter(self, intensity: float = 1.0) -> ParticleEmitter:
        """Nebelschwaden - sehr langsam, groß"""
        emitter = ParticleEmitter(ParticleType.FOG)
        
        emitter.shape = RectEmitter(
            position=Vector3(self.width / 2, self.height * 0.7, 0),
            width=self.width + 100,
            height=self.height * 0.3
        )
        
        emitter.emission_rate = int(8 * intensity)
        emitter.lifetime = 12.0
        
        # Große, weiche Nebelpartikel
        emitter.start_size = 40 + 20 * intensity
        emitter.size_variation = 20
        emitter.end_size = emitter.start_size * 1.5
        
        emitter.direction = Vector3(1, 0, 0)
        emitter.spread = 0.5
        emitter.start_speed = 8
        emitter.speed_variation = 4
        
        # Weiß-grau, sehr transparent
        emitter.start_color = Color(0.8, 0.8, 0.85, 0.15)
        emitter.end_color = Color(0.7, 0.7, 0.75, 0.0)
        
        emitter.trail_length = 0
        emitter.blend_mode = BlendMode.ADD
        
        emitter.forces.clear()
        emitter.forces.append(WindForce(
            direction=Vector3(1, 0, 0),
            strength=5,
            turbulence=3
        ))
        
        self.emitters.append(emitter)
        return emitter
    
    def add_sparks_emitter(self, x: float, y: float, 
                           intensity: float = 1.0) -> ParticleEmitter:
        """Funken - schnell, kurz, hell"""
        from particle_system import CircleEmitter
        
        emitter = ParticleEmitter(ParticleType.SPARKS)
        
        emitter.shape = CircleEmitter(
            position=Vector3(x, y, 0),
            radius=10
        )
        
        emitter.emission_rate = int(100 * intensity)
        emitter.lifetime = 1.0
        
        emitter.start_size = 2.0
        emitter.size_variation = 1.0
        emitter.end_size = 0.5
        
        emitter.direction = Vector3(0, -1, 0)  # Nach oben
        emitter.spread = 0.8
        emitter.start_speed = 80
        emitter.speed_variation = 40
        
        # Orange-gelb, hell
        emitter.start_color = Color(1.0, 0.8, 0.2, 1.0)
        emitter.end_color = Color(1.0, 0.3, 0.0, 0.0)
        
        emitter.trail_length = 3
        emitter.blend_mode = BlendMode.ADD
        
        emitter.forces.clear()
        emitter.forces.append(GravityForce(strength=150))
        
        self.emitters.append(emitter)
        return emitter
    
    def add_fire_emitter(self, x: float, y: float,
                         intensity: float = 1.0) -> ParticleEmitter:
        """Feuerpartikel - aufsteigend, flackernd"""
        from particle_system import CircleEmitter
        
        emitter = ParticleEmitter(ParticleType.FIRE)
        
        emitter.shape = CircleEmitter(
            position=Vector3(x, y, 0),
            radius=20 * intensity
        )
        
        emitter.emission_rate = int(60 * intensity)
        emitter.lifetime = 1.5
        
        emitter.start_size = 8 * intensity
        emitter.size_variation = 4
        emitter.end_size = 2
        
        emitter.direction = Vector3(0, -1, 0)  # Nach oben
        emitter.spread = 0.3
        emitter.start_speed = 40
        emitter.speed_variation = 20
        
        # Feuerfarben
        emitter.start_color = Color(1.0, 0.9, 0.3, 0.9)
        emitter.end_color = Color(0.8, 0.2, 0.0, 0.0)
        
        emitter.trail_length = 2
        emitter.blend_mode = BlendMode.ADD
        
        emitter.forces.clear()
        emitter.forces.append(GravityForce(strength=-50))  # Negative = nach oben
        emitter.forces.append(WindForce(
            direction=Vector3(1, 0, 0),
            strength=10,
            turbulence=20
        ))
        
        self.emitters.append(emitter)
        return emitter
    
    def add_smoke_emitter(self, x: float, y: float,
                          intensity: float = 1.0) -> ParticleEmitter:
        """Rauch - langsam aufsteigend, expandierend"""
        from particle_system import CircleEmitter
        
        emitter = ParticleEmitter(ParticleType.SMOKE)
        
        emitter.shape = CircleEmitter(
            position=Vector3(x, y, 0),
            radius=15
        )
        
        emitter.emission_rate = int(20 * intensity)
        emitter.lifetime = 5.0
        
        emitter.start_size = 10
        emitter.size_variation = 5
        emitter.end_size = 40  # Expandiert stark
        
        emitter.direction = Vector3(0, -1, 0)
        emitter.spread = 0.4
        emitter.start_speed = 20
        emitter.speed_variation = 10
        
        # Grau
        emitter.start_color = Color(0.3, 0.3, 0.35, 0.5)
        emitter.end_color = Color(0.5, 0.5, 0.55, 0.0)
        
        emitter.trail_length = 0
        emitter.blend_mode = BlendMode.NORMAL
        
        emitter.forces.clear()
        emitter.forces.append(GravityForce(strength=-20))
        emitter.forces.append(WindForce(
            direction=Vector3(1, 0, 0),
            strength=15,
            turbulence=10
        ))
        
        self.emitters.append(emitter)
        return emitter
    
    def set_global_wind(self, angle: float, strength: float):
        """Setze globalen Wind für alle Emitter"""
        wind_rad = math.radians(angle)
        # Wind bewegt Partikel hauptsächlich horizontal
        wind_dir = Vector3(math.cos(wind_rad), math.sin(wind_rad) * 0.3, 0)
        
        for emitter in self.emitters:
            # Entferne alte WindForce
            emitter.forces = [f for f in emitter.forces if not isinstance(f, WindForce)]
            
            # Füge neue hinzu
            if strength > 0:
                # Stärke-Multiplikator basierend auf Partikeltyp
                strength_mult = {
                    ParticleType.RAIN: 3.0,      # Regen braucht mehr Wind
                    ParticleType.SNOW: 5.0,      # Schnee ist sehr leicht
                    ParticleType.LEAVES: 6.0,    # Blätter werden stark beeinflusst
                    ParticleType.DUST: 4.0,
                    ParticleType.FOG: 2.0,
                    ParticleType.SMOKE: 3.0,
                }.get(emitter.particle_type, 2.0)
                
                # Turbulenz basierend auf Partikeltyp
                turb_factor = {
                    ParticleType.RAIN: 0.2,
                    ParticleType.SNOW: 1.0,
                    ParticleType.LEAVES: 1.5,
                    ParticleType.DUST: 0.8,
                    ParticleType.FOG: 0.4,
                }.get(emitter.particle_type, 0.5)
                
                actual_strength = strength * strength_mult
                
                emitter.forces.append(WindForce(
                    position=Vector3(self.width / 2, self.height / 2, 0),
                    radius=10000,  # Sehr groß - betrifft alle Partikel!
                    direction=wind_dir,
                    strength=actual_strength,
                    turbulence=actual_strength * turb_factor
                ))
    
    def update(self, dt: float):
        for emitter in self.emitters:
            old_positions = {id(p): p.position.y for p in emitter.particles}
            emitter.update(dt)
            
            if self.water_surface and emitter.particle_type == ParticleType.RAIN:
                # Nutze die Bounds der Wasserfläche
                ws = self.water_surface
                
                particles_to_remove = []
                
                for particle in emitter.particles:
                    px, py = particle.position.x, particle.position.y
                    
                    # Ist Partikel innerhalb der Wasserflächen-Bounds (X-Koordinate)?
                    in_x_bounds = ws.bounds_x <= px <= ws.bounds_x + ws.bounds_width
                    
                    # Ist Partikel unterhalb des oberen Rands der Wasserfläche?
                    below_water_top = py >= ws.bounds_y
                    
                    if in_x_bounds and below_water_top:
                        # Berechne relative Y-Position innerhalb des Wasserbereichs
                        relative_y = py - ws.bounds_y
                        water_height = ws.bounds_height
                        
                        # Tiefenfaktor (0 = oben, 1 = unten)
                        depth_factor = min(1.0, relative_y / water_height) if water_height > 0 else 0
                        
                        # WICHTIG: Partikel die den UNTEREN Rand erreichen MÜSSEN aufprallen
                        at_bottom = py >= ws.bounds_y + ws.bounds_height - 5
                        
                        # Zufällige Chance dass Tropfen "auftrifft"
                        # Gleichmäßiger verteilt über die gesamte Fläche
                        # Basis-Chance + leicht höher weiter unten
                        hit_chance = 0.02 + depth_factor * 0.05  # 2-7% pro Frame
                        
                        # Am unteren Rand: 100% Aufprall
                        if at_bottom or random.random() < hit_chance:
                            # Ripple Position: gleichmäßig über die gesamte Wasserfläche
                            # Bei perspektivischer Ansicht: Ripples überall
                            ripple_y = py
                            
                            # Wenn nicht am Boden, erzeuge Ripple an zufälliger Y-Position
                            # damit Ripples über die gesamte Fläche verteilt sind
                            if not at_bottom and random.random() < 0.5:
                                ripple_y = ws.bounds_y + random.uniform(0, water_height)
                            
                            impact_strength = min(1.0, particle.velocity.length() / 200)
                            ws.add_ripple(
                                px, ripple_y,
                                impact_strength * (0.3 + random.uniform(0, 0.7))
                            )
                            
                            # Splash bei stärkerem Aufprall
                            if impact_strength > 0.3 and random.random() < 0.3:
                                ws.add_splash(px, ripple_y)
                            
                            # Partikel "verschwindet" im Wasser
                            particles_to_remove.append(particle)
                
                # Entferne aufgetroffene Partikel
                for p in particles_to_remove:
                    if p in emitter.particles:
                        emitter.particles.remove(p)
        
        if self.water_surface:
            self.water_surface.update(dt)
        
        self.total_particles = sum(len(e.particles) for e in self.emitters)
        self.total_ripples = len(self.water_surface.ripples) if self.water_surface else 0


class Renderer2D:
    """Renderer für realistische, kleine Regentropfen"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
    
    def render(self, system: ParticleSystem2D) -> np.ndarray:
        try:
            from PIL import Image, ImageDraw
            return self._render_pil(system)
        except ImportError:
            return self._render_numpy(system)
    
    def _render_pil(self, system: ParticleSystem2D) -> np.ndarray:
        from PIL import Image, ImageDraw
        
        img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Wasseroberfläche
        if system.water_surface:
            self._render_water_surface(draw, system)
        
        # Partikel basierend auf Typ rendern
        angle_rad = math.radians(system.camera_angle)
        
        for emitter in system.emitters:
            ptype = emitter.particle_type
            for particle in emitter.particles:
                if ptype == ParticleType.RAIN:
                    self._render_raindrop_realistic(draw, particle, system, angle_rad)
                elif ptype == ParticleType.SNOW:
                    self._render_snowflake(draw, particle)
                elif ptype == ParticleType.LEAVES:
                    self._render_leaf(draw, particle, angle_rad)
                elif ptype == ParticleType.DUST:
                    self._render_dust(draw, particle)
                elif ptype == ParticleType.FOG:
                    self._render_fog(draw, img, particle)
                elif ptype == ParticleType.FIRE:
                    self._render_fire(draw, particle)
                elif ptype == ParticleType.SMOKE:
                    self._render_smoke(draw, img, particle)
                elif ptype == ParticleType.SPARKS:
                    self._render_spark(draw, particle)
                else:
                    # Fallback: einfacher Kreis
                    self._render_simple_particle(draw, particle)
        
        # Splashes
        if system.water_surface:
            self._render_splashes(draw, system.water_surface)
        
        return np.array(img)
    
    def _render_water_surface(self, draw, system: ParticleSystem2D):
        surface = system.water_surface
        
        # Bounds der Wasserfläche
        x1 = int(surface.bounds_x)
        y1 = int(surface.bounds_y)
        x2 = int(surface.bounds_x + surface.bounds_width)
        y2 = int(surface.bounds_y + surface.bounds_height)
        
        # Wasserfarbe mit einstellbarer Transparenz
        r, g, b, _ = surface.water_color.to_int_tuple()
        
        # water_opacity steuert die Sichtbarkeit der Wasserfläche
        # 0 = komplett transparent (nur Ripples sichtbar)
        # 1 = solid gefärbt
        actual_alpha = int(255 * surface.water_opacity)
        
        if actual_alpha > 0:
            if surface.glass_effect:
                # Glas-Effekt: Reflektives Wasser mit Gradient
                self._render_glass_water(draw, surface, x1, y1, x2, y2)
            else:
                # Normale Wasserfläche mit einstellbarer Transparenz
                draw.rectangle([x1, y1, x2, y2], fill=(r, g, b, actual_alpha))
        
        # Ripples mit perspektivischer Ellipse
        angle_factor = math.sin(math.radians(system.camera_angle))
        
        for ripple in surface.ripples:
            # Nur Ripples innerhalb der Bounds zeichnen
            if surface.point_in_bounds(ripple.x, ripple.y):
                self._render_ripple(draw, ripple, surface, angle_factor)
    
    def _render_glass_water(self, draw, surface: WaterSurface, x1: int, y1: int, x2: int, y2: int):
        """Rendere Wasserfläche mit Glas/Reflexions-Effekt"""
        r, g, b, _ = surface.water_color.to_int_tuple()
        height = y2 - y1
        
        # Basis-Alpha aus water_opacity
        base_alpha = surface.water_opacity * 255
        
        # Gradient von oben (heller/reflektiver) nach unten (dunkler/tiefer)
        num_bands = min(20, max(5, height // 10))
        band_height = height / num_bands
        
        for i in range(num_bands):
            band_y1 = y1 + i * band_height
            band_y2 = y1 + (i + 1) * band_height
            
            # Reflexionsfaktor: oben mehr Reflexion
            reflection = 1.0 - (i / num_bands)
            
            # Farbe: oben heller (Himmel-Reflexion), unten dunkler (Tiefe)
            band_r = int(min(255, r + 60 * reflection * surface.glass_reflection))
            band_g = int(min(255, g + 80 * reflection * surface.glass_reflection))
            band_b = int(min(255, b + 100 * reflection * surface.glass_reflection))
            # Alpha: Basis + zusätzliche Reflexion oben
            band_a = int(base_alpha + 50 * reflection * surface.glass_reflection)
            
            draw.rectangle([x1, int(band_y1), x2, int(band_y2)], 
                          fill=(band_r, band_g, band_b, min(255, band_a)))
        
        # Highlight-Linie am oberen Rand (Oberflächen-Reflexion)
        if surface.glass_reflection > 0.2:
            highlight_alpha = int(150 * surface.glass_reflection)
            draw.line([(x1, y1), (x2, y1)], fill=(255, 255, 255, highlight_alpha), width=2)
            draw.line([(x1, y1 + 2), (x2, y1 + 2)], fill=(200, 220, 255, highlight_alpha // 2), width=1)
    
    def _render_ripple(self, draw, ripple: Ripple, surface: WaterSurface, angle_factor: float):
        color = surface.ripple_color
        alpha = int(ripple.alpha * color.a * 255)
        
        if alpha < 3:
            return
        
        r, g, b = int(color.r * 255), int(color.g * 255), int(color.b * 255)
        
        # Ellipse: Bei flachem Winkel (0°) = Kreise von oben
        # Bei steilem Winkel (90°) = stark gestreckte Ellipsen
        radius_x = ripple.radius
        radius_y = ripple.radius * (0.3 + 0.7 * angle_factor)  # Wird flacher bei top-down
        
        # Nur 1-2 Ringe für subtileren Effekt
        for i in range(2):
            r_offset = i * 2
            if ripple.radius - r_offset <= 0:
                continue
            
            rx = radius_x - r_offset
            ry = radius_y - r_offset * (0.3 + 0.7 * angle_factor)
            ring_alpha = int(alpha * (1 - i * 0.4))
            
            if ring_alpha > 3 and rx > 0 and ry > 0:
                draw.ellipse(
                    [ripple.x - rx, ripple.y - ry, ripple.x + rx, ripple.y + ry],
                    outline=(r, g, b, ring_alpha),
                    width=1
                )
    
    def _render_splashes(self, draw, surface: WaterSurface):
        for splash in surface.splashes:
            for p in splash.particles:
                alpha = int(p['alpha'] * 150)
                if alpha < 3:
                    continue
                size = max(0.5, p['size'])
                x, y = p['x'], p['y']
                draw.ellipse(
                    [x - size, y - size, x + size, y + size],
                    fill=(180, 200, 220, alpha)
                )
    
    def _render_raindrop_realistic(self, draw, particle: Particle, 
                                    system: ParticleSystem2D, angle_rad: float):
        """Rendere realistischen, kleinen Regentropfen"""
        x, y = particle.position.x, particle.position.y
        
        if x < -20 or x > self.width + 20 or y < -20 or y > self.height + 20:
            return
        
        appearance = system.raindrop_appearance
        
        # Basisgröße - KLEIN halten!
        base_size = particle.size
        
        # Bei 0° (von oben): Tropfen erscheinen als kleine Punkte/kurze Striche
        # Bei 90° (seitlich): Tropfen erscheinen als lange vertikale Striche
        
        # Länge des Tropfens basierend auf Winkel
        # cos(0°) = 1 -> kurz (Tropfen fällt auf uns zu)
        # sin(90°) = 1 -> lang (Tropfen fällt seitwärts)
        
        # Geschwindigkeitsbasierte Länge
        speed = particle.velocity.length()
        speed_factor = min(1.0, speed / 500)
        
        # Tropfenlänge: Bei 0° kurz, bei 90° lang
        drop_length = base_size * (1 + 5 * math.sin(angle_rad) * speed_factor)
        drop_width = base_size * 0.5
        
        # Sehr kleines Minimum
        drop_length = max(1, min(drop_length, 15))
        drop_width = max(0.5, min(drop_width, 2))
        
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Bewegungsrichtung für Orientierung
        if particle.velocity.length() > 1:
            vel_x = particle.velocity.x
            vel_y = particle.velocity.y
            vel_len = math.sqrt(vel_x*vel_x + vel_y*vel_y)
            dir_x = vel_x / vel_len
            dir_y = vel_y / vel_len
        else:
            dir_x, dir_y = 0, 1
        
        # Trail zuerst (Bewegungsunschärfe)
        if len(particle.trail_positions) > 0 and appearance.motion_blur > 0:
            self._render_trail_simple(draw, particle, r, g, b, a, drop_width)
        
        # Haupttropfen
        if appearance.glass_enabled and drop_length > 2:
            # Dezenter Glas-Effekt für größere Tropfen
            self._render_glass_drop_minimal(draw, x, y, dir_x, dir_y, 
                                            drop_width, drop_length, r, g, b, a, appearance)
        else:
            # Einfache Linie für kleine/schnelle Tropfen
            self._render_drop_line(draw, x, y, dir_x, dir_y, drop_length, r, g, b, a)
    
    def _render_trail_simple(self, draw, particle, r, g, b, a, width):
        """Einfacher Trail als Linie"""
        positions = [(particle.position.x, particle.position.y)]
        for p in particle.trail_positions[:3]:  # Nur wenige Trail-Punkte
            positions.append((p.x, p.y))
        
        if len(positions) < 2:
            return
        
        for i in range(len(positions) - 1):
            p1, p2 = positions[i], positions[i + 1]
            trail_alpha = int(a * 0.3 * (1 - i / len(positions)))
            if trail_alpha > 3:
                draw.line([p1, p2], fill=(r, g, b, trail_alpha), width=max(1, int(width)))
    
    def _render_drop_line(self, draw, x, y, dir_x, dir_y, length, r, g, b, a):
        """Rendere Tropfen als einfache Linie"""
        half_len = length / 2
        x1 = x - dir_x * half_len
        y1 = y - dir_y * half_len
        x2 = x + dir_x * half_len
        y2 = y + dir_y * half_len
        
        # Hauptlinie
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, a), width=1)
        
        # Optional: Dezenter Glanzpunkt am Kopf
        if a > 50:
            draw.point((x1, y1), fill=(255, 255, 255, min(a, 100)))
    
    def _render_glass_drop_minimal(self, draw, x, y, dir_x, dir_y, 
                                    width, length, r, g, b, a, appearance):
        """Minimaler Glas-Effekt - nicht zu auffällig"""
        half_len = length / 2
        
        # Endpunkte
        x1 = x - dir_x * half_len
        y1 = y - dir_y * half_len
        x2 = x + dir_x * half_len
        y2 = y + dir_y * half_len
        
        # Haupttropfen als Linie
        line_width = max(1, int(width))
        draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, a), width=line_width)
        
        # Dezenter Glanzpunkt am Kopf (oben)
        if appearance.specular_strength > 0.1:
            spec_alpha = int(min(255, a * appearance.specular_strength * 1.5))
            if spec_alpha > 10:
                spec_size = max(0.5, width * 0.3)
                draw.ellipse(
                    [x1 - spec_size, y1 - spec_size, x1 + spec_size, y1 + spec_size],
                    fill=(255, 255, 255, spec_alpha)
                )
    
    def _render_snowflake(self, draw, particle: Particle):
        """Schneeflocke - weißer, weicher Punkt"""
        x, y = particle.position.x, particle.position.y
        if x < -20 or x > self.width + 20 or y < -20 or y > self.height + 20:
            return
        
        size = particle.size
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Weicher Schneeflocken-Punkt mit Glow
        # Äußerer Glow
        glow_size = size * 1.5
        draw.ellipse(
            [x - glow_size, y - glow_size, x + glow_size, y + glow_size],
            fill=(r, g, b, int(a * 0.3))
        )
        
        # Innerer Kern
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(r, g, b, a)
        )
        
        # Optional: kleine Sternform für größere Flocken
        if size > 3:
            line_len = size * 0.6
            line_alpha = int(a * 0.5)
            for angle in [0, 60, 120]:
                rad = math.radians(angle)
                dx = math.cos(rad) * line_len
                dy = math.sin(rad) * line_len
                draw.line([(x - dx, y - dy), (x + dx, y + dy)], 
                         fill=(255, 255, 255, line_alpha), width=1)
    
    def _render_leaf(self, draw, particle: Particle, angle_rad: float):
        """Blatt - ovale Form mit Rotation"""
        x, y = particle.position.x, particle.position.y
        if x < -30 or x > self.width + 30 or y < -30 or y > self.height + 30:
            return
        
        size = particle.size
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Variation in Farbe (Herbstlaub)
        color_var = hash(id(particle)) % 3
        if color_var == 1:
            r, g = min(255, int(r * 1.2)), max(0, int(g * 0.6))  # Rötlicher
        elif color_var == 2:
            r, g = int(r * 0.9), min(255, int(g * 1.3))  # Gelblicher
        
        # Blattform als Ellipse
        # Rotation basierend auf Bewegung
        if particle.velocity.length() > 1:
            rot = math.atan2(particle.velocity.y, particle.velocity.x)
        else:
            rot = particle.age * 2  # Taumeln
        
        width = size
        height = size * 0.5
        
        # Einfache Ellipse (ohne echte Rotation - PIL limitiert)
        draw.ellipse(
            [x - width, y - height, x + width, y + height],
            fill=(r, g, b, a)
        )
        
        # Blattader (Mittellinie)
        draw.line([(x - width * 0.7, y), (x + width * 0.7, y)],
                 fill=(int(r * 0.6), int(g * 0.5), 0, a), width=1)
    
    def _render_dust(self, draw, particle: Particle):
        """Staubpartikel - kleiner, diffuser Punkt"""
        x, y = particle.position.x, particle.position.y
        if x < 0 or x > self.width or y < 0 or y > self.height:
            return
        
        size = max(0.5, particle.size)
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Sehr simple Darstellung
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(r, g, b, a)
        )
    
    def _render_fog(self, draw, img, particle: Particle):
        """Nebel - große, sehr weiche Partikel"""
        from PIL import ImageFilter
        
        x, y = particle.position.x, particle.position.y
        size = particle.size
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Große, sehr transparente Ellipse
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(r, g, b, max(1, int(a * 0.3)))
        )
    
    def _render_fire(self, draw, particle: Particle):
        """Feuerpartikel - hell, mit Farbverlauf"""
        x, y = particle.position.x, particle.position.y
        if x < -20 or x > self.width + 20 or y < -20 or y > self.height + 20:
            return
        
        size = particle.size
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Äußerer Glow (rötlich)
        glow_size = size * 1.8
        draw.ellipse(
            [x - glow_size, y - glow_size, x + glow_size, y + glow_size],
            fill=(255, int(g * 0.3), 0, int(a * 0.2))
        )
        
        # Mittlerer Ring (orange)
        mid_size = size * 1.2
        draw.ellipse(
            [x - mid_size, y - mid_size, x + mid_size, y + mid_size],
            fill=(255, int(g * 0.6), 0, int(a * 0.5))
        )
        
        # Kern (gelb-weiß)
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(r, g, b, a)
        )
    
    def _render_smoke(self, draw, img, particle: Particle):
        """Rauch - weiche, expandierende Partikel"""
        x, y = particle.position.x, particle.position.y
        size = particle.size
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Mehrere überlappende Kreise für weichen Effekt
        for i in range(3):
            offset_x = (hash(id(particle) + i) % 10 - 5) * size * 0.1
            offset_y = (hash(id(particle) + i + 100) % 10 - 5) * size * 0.1
            sub_size = size * (0.7 + i * 0.15)
            sub_alpha = max(1, int(a * (0.4 - i * 0.1)))
            
            draw.ellipse(
                [x + offset_x - sub_size, y + offset_y - sub_size,
                 x + offset_x + sub_size, y + offset_y + sub_size],
                fill=(r, g, b, sub_alpha)
            )
    
    def _render_spark(self, draw, particle: Particle):
        """Funke - kleiner, heller Punkt mit Trail"""
        x, y = particle.position.x, particle.position.y
        if x < -10 or x > self.width + 10 or y < -10 or y > self.height + 10:
            return
        
        size = particle.size
        color = particle.color
        r, g, b, a = color.to_int_tuple()
        
        # Trail zeichnen
        if len(particle.trail_positions) > 0:
            positions = [(x, y)] + [(p.x, p.y) for p in particle.trail_positions[:5]]
            for i in range(len(positions) - 1):
                p1, p2 = positions[i], positions[i + 1]
                trail_alpha = int(a * (1 - i / len(positions)) * 0.5)
                if trail_alpha > 3:
                    draw.line([p1, p2], fill=(r, g, b, trail_alpha), width=1)
        
        # Glühender Kern
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(r, g, b, a)
        )
        
        # Heller Punkt in der Mitte
        if size > 1:
            draw.ellipse(
                [x - 1, y - 1, x + 1, y + 1],
                fill=(255, 255, 255, min(255, int(a * 1.5)))
            )
    
    def _render_simple_particle(self, draw, particle: Particle):
        """Fallback für unbekannte Partikeltypen"""
        x, y = particle.position.x, particle.position.y
        if x < 0 or x > self.width or y < 0 or y > self.height:
            return
        
        size = max(1, particle.size)
        r, g, b, a = particle.color.to_int_tuple()
        
        draw.ellipse(
            [x - size, y - size, x + size, y + size],
            fill=(r, g, b, a)
        )
    
    def _render_numpy(self, system: ParticleSystem2D) -> np.ndarray:
        """Fallback-Renderer"""
        frame = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        
        for emitter in system.emitters:
            for particle in emitter.particles:
                x, y = int(particle.position.x), int(particle.position.y)
                
                if 0 <= x < self.width and 0 <= y < self.height:
                    color = particle.color.to_int_tuple()
                    frame[max(0,y-1):min(self.height,y+2), max(0,x):min(self.width,x+1)] = color
        
        return frame


def create_rain_scene_2d(width: int = 1920, height: int = 1080,
                         camera_angle: float = 30.0,
                         intensity: float = 1.0,
                         with_water: bool = True) -> ParticleSystem2D:
    """Erstelle realistische Regen-Szene"""
    system = ParticleSystem2D(width, height)
    system.set_camera_angle(camera_angle)
    
    if with_water:
        system.enable_water_surface(height * 0.85)
    
    system.add_rain_emitter(intensity=intensity)
    return system


if __name__ == "__main__":
    print("2D/2.5D Partikel-System Test")
    print("=" * 40)
    
    # Test verschiedene Winkel
    for angle in [0, 30, 60, 90]:
        print(f"\nTest mit Kamera-Winkel: {angle}°")
        system = create_rain_scene_2d(
            width=800, height=600,
            camera_angle=angle,
            intensity=1.0,
            with_water=True
        )
        
        renderer = Renderer2D(800, 600)
        
        for i in range(30):
            system.update(1/60)
        
        frame = renderer.render(system)
        print(f"  Partikel: {system.total_particles}, Ripples: {system.total_ripples}")
        
        try:
            from PIL import Image
            img = Image.fromarray(frame, 'RGBA')
            img.save(f"test_rain_2d_angle_{angle}.png")
            print(f"  Gespeichert: test_rain_2d_angle_{angle}.png")
        except Exception as e:
            print(f"  Fehler: {e}")
