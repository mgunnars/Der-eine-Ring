"""
Time & Weather System für "Der Eine Ring" VTT
==============================================

Verwaltet:
- Tag/Nacht-Zyklus (automatisch oder manuell)
- Wetter-System mit Regionen und Jahreszeiten
- Lichtverhältnisse basierend auf Tageszeit
- Integration mit Lighting-System

Autor: VTT Development Team
Version: 1.0.0
"""

import random
import time
import math
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json


class TimeOfDay(Enum):
    """Tageszeit"""
    DAWN = "dawn"           # Morgendämmerung (5-7)
    MORNING = "morning"     # Morgen (7-10)
    NOON = "noon"           # Mittag (10-14)
    AFTERNOON = "afternoon" # Nachmittag (14-17)
    DUSK = "dusk"           # Abenddämmerung (17-19)
    EVENING = "evening"     # Abend (19-22)
    NIGHT = "night"         # Nacht (22-5)


class Season(Enum):
    """Jahreszeit"""
    SPRING = "spring"       # Frühling
    SUMMER = "summer"       # Sommer
    AUTUMN = "autumn"       # Herbst
    WINTER = "winter"       # Winter


class WeatherType(Enum):
    """Wetter-Typ"""
    CLEAR = "clear"                 # Klar
    PARTLY_CLOUDY = "partly_cloudy" # Leicht bewölkt
    CLOUDY = "cloudy"               # Bewölkt
    OVERCAST = "overcast"           # Bedeckt
    FOG = "fog"                     # Nebel
    MIST = "mist"                   # Dunst
    RAIN_LIGHT = "rain_light"       # Leichter Regen
    RAIN = "rain"                   # Regen
    RAIN_HEAVY = "rain_heavy"       # Starkregen
    THUNDERSTORM = "thunderstorm"   # Gewitter
    SNOW_LIGHT = "snow_light"       # Leichter Schneefall
    SNOW = "snow"                   # Schnee
    SNOW_HEAVY = "snow_heavy"       # Schneesturm
    BLIZZARD = "blizzard"           # Blizzard
    HAIL = "hail"                   # Hagel
    SANDSTORM = "sandstorm"         # Sandsturm
    WIND = "wind"                   # Wind
    STORM = "storm"                 # Sturm


class ClimateZone(Enum):
    """Klimazone"""
    TEMPERATE = "temperate"     # Gemäßigt (Standard)
    TROPICAL = "tropical"       # Tropisch
    ARCTIC = "arctic"           # Arktisch
    DESERT = "desert"           # Wüste
    MOUNTAIN = "mountain"       # Gebirge
    COASTAL = "coastal"         # Küste
    FOREST = "forest"           # Wald
    SWAMP = "swamp"             # Sumpf


@dataclass
class Region:
    """Eine geografische Region mit Klima-Eigenschaften"""
    id: str
    name: str
    climate_zone: ClimateZone = ClimateZone.TEMPERATE
    
    # Höhe (beeinflusst Temperatur und Wetter)
    altitude: int = 0           # Meter über Meeresspiegel
    
    # Wetter-Wahrscheinlichkeiten (überschreiben Defaults)
    weather_weights: Dict[str, float] = field(default_factory=dict)
    
    # Erlaubte/verbotene Wetter
    allowed_weather: List[str] = field(default_factory=list)  # Leer = alle
    forbidden_weather: List[str] = field(default_factory=list)
    
    # Modifikatoren
    temperature_modifier: int = 0   # Grad-Änderung
    precipitation_modifier: float = 1.0  # Niederschlags-Faktor
    
    # Besondere Eigenschaften
    always_snow_above_altitude: int = 3000  # Schnee ab dieser Höhe
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "climate_zone": self.climate_zone.value,
            "altitude": self.altitude,
            "weather_weights": self.weather_weights,
            "allowed_weather": self.allowed_weather,
            "forbidden_weather": self.forbidden_weather,
            "temperature_modifier": self.temperature_modifier,
            "precipitation_modifier": self.precipitation_modifier,
            "always_snow_above_altitude": self.always_snow_above_altitude
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Region':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            climate_zone=ClimateZone(data.get("climate_zone", "temperate")),
            altitude=data.get("altitude", 0),
            weather_weights=data.get("weather_weights", {}),
            allowed_weather=data.get("allowed_weather", []),
            forbidden_weather=data.get("forbidden_weather", []),
            temperature_modifier=data.get("temperature_modifier", 0),
            precipitation_modifier=data.get("precipitation_modifier", 1.0),
            always_snow_above_altitude=data.get("always_snow_above_altitude", 3000)
        )


@dataclass
class WeatherState:
    """Aktueller Wetter-Zustand"""
    weather_type: WeatherType = WeatherType.CLEAR
    temperature: int = 20       # Grad Celsius
    wind_speed: int = 0         # km/h
    humidity: int = 50          # Prozent
    visibility: float = 1.0     # 0-1 (1 = klar, 0 = keine Sicht)
    precipitation: float = 0.0  # 0-1 (Niederschlags-Intensität)
    
    # Für Overlay-Steuerung
    overlay_intensity: float = 0.0  # Wie stark das Wetter-Overlay sein soll
    
    def to_dict(self) -> dict:
        return {
            "weather_type": self.weather_type.value,
            "temperature": self.temperature,
            "wind_speed": self.wind_speed,
            "humidity": self.humidity,
            "visibility": self.visibility,
            "precipitation": self.precipitation,
            "overlay_intensity": self.overlay_intensity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WeatherState':
        return cls(
            weather_type=WeatherType(data.get("weather_type", "clear")),
            temperature=data.get("temperature", 20),
            wind_speed=data.get("wind_speed", 0),
            humidity=data.get("humidity", 50),
            visibility=data.get("visibility", 1.0),
            precipitation=data.get("precipitation", 0.0),
            overlay_intensity=data.get("overlay_intensity", 0.0)
        )


class GameTime:
    """
    Verwaltet die Spielzeit (In-Game-Zeit)
    """
    
    def __init__(self, 
                 hour: int = 12, 
                 minute: int = 0,
                 day: int = 1,
                 month: int = 1,
                 year: int = 1):
        
        self.hour = hour
        self.minute = minute
        self.day = day
        self.month = month  # 1-12
        self.year = year
        
        # Zeit-Skalierung: Wie viele Echtzeit-Sekunden = 1 Spielzeit-Minute
        self.time_scale = 60.0  # 60 Sekunden real = 1 Minute Spielzeit
        
        # Auto-Update
        self._auto_advance = True
        self._last_update = time.time()
        
        # Callbacks
        self.on_hour_change: Optional[Callable[[int], None]] = None
        self.on_time_of_day_change: Optional[Callable[[TimeOfDay], None]] = None
        self.on_day_change: Optional[Callable[[int], None]] = None
        
        self._last_hour = hour
        self._last_time_of_day = self.get_time_of_day()
    
    def update(self, delta_seconds: float = 0):
        """Update der Spielzeit"""
        if not self._auto_advance:
            return
        
        # Zeit seit letztem Update
        if delta_seconds <= 0:
            current_time = time.time()
            delta_seconds = current_time - self._last_update
            self._last_update = current_time
        
        # In Spielminuten umrechnen
        game_minutes = delta_seconds / self.time_scale
        
        self.add_minutes(game_minutes)
    
    def add_minutes(self, minutes: float):
        """Fügt Minuten zur Zeit hinzu"""
        self.minute += minutes
        
        # Überlauf zu Stunden
        while self.minute >= 60:
            self.minute -= 60
            self.add_hours(1)
        
        while self.minute < 0:
            self.minute += 60
            self.add_hours(-1)
    
    def add_hours(self, hours: int):
        """Fügt Stunden zur Zeit hinzu"""
        old_hour = self.hour
        self.hour += hours
        
        # Überlauf zu Tagen
        while self.hour >= 24:
            self.hour -= 24
            self.add_days(1)
        
        while self.hour < 0:
            self.hour += 24
            self.add_days(-1)
        
        # Callback für Stundenwechsel
        if self.hour != old_hour and self.on_hour_change:
            self.on_hour_change(self.hour)
        
        # Callback für Tageszeit-Wechsel
        new_time_of_day = self.get_time_of_day()
        if new_time_of_day != self._last_time_of_day:
            self._last_time_of_day = new_time_of_day
            if self.on_time_of_day_change:
                self.on_time_of_day_change(new_time_of_day)
    
    def add_days(self, days: int):
        """Fügt Tage zur Zeit hinzu"""
        old_day = self.day
        self.day += days
        
        # Einfacher Kalender (30 Tage pro Monat)
        days_per_month = 30
        
        while self.day > days_per_month:
            self.day -= days_per_month
            self.month += 1
            if self.month > 12:
                self.month = 1
                self.year += 1
        
        while self.day < 1:
            self.day += days_per_month
            self.month -= 1
            if self.month < 1:
                self.month = 12
                self.year -= 1
        
        # Callback für Tageswechsel
        if self.day != old_day and self.on_day_change:
            self.on_day_change(self.day)
    
    def set_time(self, hour: int, minute: int = 0):
        """Setzt die Uhrzeit direkt"""
        self.hour = hour % 24
        self.minute = minute % 60
        
        # Callbacks auslösen
        if self.on_hour_change:
            self.on_hour_change(self.hour)
        
        new_tod = self.get_time_of_day()
        if new_tod != self._last_time_of_day:
            self._last_time_of_day = new_tod
            if self.on_time_of_day_change:
                self.on_time_of_day_change(new_tod)
    
    def set_time_of_day(self, time_of_day: str):
        """Setzt die Tageszeit (springt zur passenden Stunde)"""
        time_mapping = {
            "dawn": 6,
            "morning": 8,
            "noon": 12,
            "afternoon": 15,
            "dusk": 18,
            "evening": 20,
            "night": 0
        }
        
        if time_of_day in time_mapping:
            self.set_time(time_mapping[time_of_day], 0)
    
    def get_time_of_day(self) -> TimeOfDay:
        """Gibt die aktuelle Tageszeit zurück"""
        h = self.hour
        
        if 5 <= h < 7:
            return TimeOfDay.DAWN
        elif 7 <= h < 10:
            return TimeOfDay.MORNING
        elif 10 <= h < 14:
            return TimeOfDay.NOON
        elif 14 <= h < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= h < 19:
            return TimeOfDay.DUSK
        elif 19 <= h < 22:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    def get_season(self) -> Season:
        """Gibt die aktuelle Jahreszeit zurück"""
        if self.month in [3, 4, 5]:
            return Season.SPRING
        elif self.month in [6, 7, 8]:
            return Season.SUMMER
        elif self.month in [9, 10, 11]:
            return Season.AUTUMN
        else:
            return Season.WINTER
    
    def is_day(self) -> bool:
        """Ist es Tag?"""
        return 6 <= self.hour < 20
    
    def is_night(self) -> bool:
        """Ist es Nacht?"""
        return not self.is_day()
    
    def get_hour(self) -> int:
        """Gibt die aktuelle Stunde zurück"""
        return self.hour
    
    def get_formatted_time(self) -> str:
        """Gibt formatierte Zeitangabe zurück"""
        return f"{self.hour:02d}:{int(self.minute):02d}"
    
    def get_formatted_date(self) -> str:
        """Gibt formatiertes Datum zurück"""
        season_names = {
            Season.SPRING: "Frühling",
            Season.SUMMER: "Sommer",
            Season.AUTUMN: "Herbst",
            Season.WINTER: "Winter"
        }
        season = season_names[self.get_season()]
        return f"Tag {self.day}, {season} {self.year}"
    
    def get_sun_intensity(self) -> float:
        """
        Berechnet Sonnenintensität (0-1)
        Für Lighting-System
        """
        h = self.hour + self.minute / 60.0
        
        if h < 5 or h >= 21:
            return 0.0  # Nacht
        elif 5 <= h < 7:
            # Morgendämmerung (0 -> 0.5)
            return ((h - 5) / 2) * 0.5
        elif 7 <= h < 9:
            # Morgen (0.5 -> 1.0)
            return 0.5 + ((h - 7) / 2) * 0.5
        elif 9 <= h < 17:
            return 1.0  # Voller Tag
        elif 17 <= h < 19:
            # Nachmittag -> Dämmerung (1.0 -> 0.5)
            return 1.0 - ((h - 17) / 2) * 0.5
        elif 19 <= h < 21:
            # Abenddämmerung (0.5 -> 0)
            return 0.5 - ((h - 19) / 2) * 0.5
        
        return 0.0
    
    def get_ambient_color(self) -> Tuple[int, int, int]:
        """
        Berechnet Ambient-Farbe basierend auf Tageszeit
        Für Lighting-System
        """
        tod = self.get_time_of_day()
        
        colors = {
            TimeOfDay.DAWN: (255, 200, 150),      # Warmes Orange
            TimeOfDay.MORNING: (255, 245, 230),   # Warmes Weiß
            TimeOfDay.NOON: (255, 255, 255),      # Reines Weiß
            TimeOfDay.AFTERNOON: (255, 250, 240), # Leicht warm
            TimeOfDay.DUSK: (255, 180, 120),      # Orange
            TimeOfDay.EVENING: (100, 120, 180),   # Bläulich
            TimeOfDay.NIGHT: (30, 40, 80)         # Tiefblau
        }
        
        return colors.get(tod, (255, 255, 255))
    
    def set_auto_advance(self, enabled: bool):
        """Aktiviert/deaktiviert automatischen Zeitfortschritt"""
        self._auto_advance = enabled
        if enabled:
            self._last_update = time.time()
    
    def set_time_scale(self, scale: float):
        """Setzt Zeit-Skalierung (Sekunden real pro Minute Spielzeit)"""
        self.time_scale = max(1.0, scale)
    
    def to_dict(self) -> dict:
        return {
            "hour": self.hour,
            "minute": self.minute,
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "time_scale": self.time_scale,
            "auto_advance": self._auto_advance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameTime':
        gt = cls(
            hour=data.get("hour", 12),
            minute=data.get("minute", 0),
            day=data.get("day", 1),
            month=data.get("month", 1),
            year=data.get("year", 1)
        )
        gt.time_scale = data.get("time_scale", 60.0)
        gt._auto_advance = data.get("auto_advance", True)
        return gt


class WeatherSystem:
    """
    Wetter-System mit Regionen und Jahreszeiten
    """
    
    # Standard-Wetter-Wahrscheinlichkeiten pro Jahreszeit
    SEASONAL_WEATHER = {
        Season.SPRING: {
            WeatherType.CLEAR: 0.25,
            WeatherType.PARTLY_CLOUDY: 0.25,
            WeatherType.CLOUDY: 0.15,
            WeatherType.RAIN_LIGHT: 0.15,
            WeatherType.RAIN: 0.10,
            WeatherType.FOG: 0.05,
            WeatherType.THUNDERSTORM: 0.05
        },
        Season.SUMMER: {
            WeatherType.CLEAR: 0.40,
            WeatherType.PARTLY_CLOUDY: 0.25,
            WeatherType.CLOUDY: 0.10,
            WeatherType.RAIN_LIGHT: 0.05,
            WeatherType.RAIN: 0.05,
            WeatherType.THUNDERSTORM: 0.10,
            WeatherType.RAIN_HEAVY: 0.05
        },
        Season.AUTUMN: {
            WeatherType.CLEAR: 0.15,
            WeatherType.PARTLY_CLOUDY: 0.20,
            WeatherType.CLOUDY: 0.20,
            WeatherType.OVERCAST: 0.10,
            WeatherType.RAIN_LIGHT: 0.10,
            WeatherType.RAIN: 0.10,
            WeatherType.FOG: 0.10,
            WeatherType.MIST: 0.05
        },
        Season.WINTER: {
            WeatherType.CLEAR: 0.20,
            WeatherType.PARTLY_CLOUDY: 0.15,
            WeatherType.CLOUDY: 0.15,
            WeatherType.OVERCAST: 0.15,
            WeatherType.SNOW_LIGHT: 0.15,
            WeatherType.SNOW: 0.10,
            WeatherType.SNOW_HEAVY: 0.05,
            WeatherType.BLIZZARD: 0.02,
            WeatherType.FOG: 0.03
        }
    }
    
    # Klimazonen-Modifikatoren
    CLIMATE_MODIFIERS = {
        ClimateZone.TEMPERATE: {},  # Standard
        ClimateZone.TROPICAL: {
            WeatherType.RAIN: 0.20,
            WeatherType.RAIN_HEAVY: 0.15,
            WeatherType.THUNDERSTORM: 0.15,
            WeatherType.SNOW: -1,  # Kein Schnee
            WeatherType.SNOW_LIGHT: -1,
            WeatherType.SNOW_HEAVY: -1,
            WeatherType.BLIZZARD: -1
        },
        ClimateZone.ARCTIC: {
            WeatherType.SNOW: 0.25,
            WeatherType.SNOW_LIGHT: 0.20,
            WeatherType.SNOW_HEAVY: 0.15,
            WeatherType.BLIZZARD: 0.10,
            WeatherType.RAIN: -1,  # Kein Regen
            WeatherType.RAIN_LIGHT: -1,
            WeatherType.RAIN_HEAVY: -1,
            WeatherType.THUNDERSTORM: -1
        },
        ClimateZone.DESERT: {
            WeatherType.CLEAR: 0.50,
            WeatherType.SANDSTORM: 0.15,
            WeatherType.RAIN: -1,
            WeatherType.RAIN_LIGHT: -1,
            WeatherType.RAIN_HEAVY: -1,
            WeatherType.SNOW: -1,
            WeatherType.FOG: -1
        },
        ClimateZone.MOUNTAIN: {
            WeatherType.WIND: 0.15,
            WeatherType.STORM: 0.10,
            WeatherType.SNOW: 0.15,
            WeatherType.FOG: 0.10
        },
        ClimateZone.COASTAL: {
            WeatherType.MIST: 0.15,
            WeatherType.FOG: 0.10,
            WeatherType.WIND: 0.10,
            WeatherType.STORM: 0.08
        },
        ClimateZone.SWAMP: {
            WeatherType.FOG: 0.20,
            WeatherType.MIST: 0.20,
            WeatherType.RAIN_LIGHT: 0.15,
            WeatherType.OVERCAST: 0.15
        }
    }
    
    def __init__(self, game_time: GameTime):
        self.game_time = game_time
        
        # Aktuelle Werte
        self.current_weather = WeatherState()
        self.current_region: Optional[Region] = None
        
        # Registrierte Regionen
        self.regions: Dict[str, Region] = {}
        
        # Zufalls-Modus
        self.random_weather = True
        self.weather_change_interval = 3600  # Sekunden (Spielzeit) bis Wetter-Check
        self._time_since_last_change = 0.0
        
        # Transition (sanfter Übergang zwischen Wetter)
        self._target_weather: Optional[WeatherState] = None
        self._transition_progress = 0.0
        self._transition_duration = 300.0  # Sekunden für Übergang
        
        # Callbacks
        self.on_weather_change: Optional[Callable[[WeatherState], None]] = None
        self.on_weather_transition: Optional[Callable[[float], None]] = None
        
        # Standard-Region erstellen
        self.register_region(Region(
            id="default",
            name="Standard-Region",
            climate_zone=ClimateZone.TEMPERATE
        ))
        self.set_region("default")
    
    def register_region(self, region: Region):
        """Registriert eine neue Region"""
        self.regions[region.id] = region
        print(f"🌍 Region registriert: {region.name} ({region.climate_zone.value})")
    
    def set_region(self, region_id: str):
        """Wechselt zur angegebenen Region"""
        if region_id in self.regions:
            self.current_region = self.regions[region_id]
            print(f"📍 Region gewechselt: {self.current_region.name}")
            
            # Wetter neu berechnen
            if self.random_weather:
                self._generate_weather()
    
    def set_weather(self, weather_type: str, immediate: bool = False):
        """Setzt das Wetter manuell"""
        try:
            wtype = WeatherType(weather_type)
        except ValueError:
            print(f"⚠️ Unbekannter Wetter-Typ: {weather_type}")
            return
        
        new_state = self._create_weather_state(wtype)
        
        if immediate:
            self.current_weather = new_state
            if self.on_weather_change:
                self.on_weather_change(self.current_weather)
        else:
            # Sanfter Übergang
            self._target_weather = new_state
            self._transition_progress = 0.0
    
    def update(self, delta_seconds: float):
        """Update-Tick"""
        # Zufalls-Wetter prüfen
        if self.random_weather:
            self._time_since_last_change += delta_seconds
            
            if self._time_since_last_change >= self.weather_change_interval:
                self._time_since_last_change = 0
                
                # Zufällig neues Wetter?
                if random.random() < 0.3:  # 30% Chance auf Änderung
                    self._generate_weather()
        
        # Wetter-Transition
        if self._target_weather:
            self._transition_progress += delta_seconds / self._transition_duration
            
            if self._transition_progress >= 1.0:
                self.current_weather = self._target_weather
                self._target_weather = None
                self._transition_progress = 0.0
                
                if self.on_weather_change:
                    self.on_weather_change(self.current_weather)
            else:
                # Interpolieren
                self._interpolate_weather()
                
                if self.on_weather_transition:
                    self.on_weather_transition(self._transition_progress)
    
    def _generate_weather(self):
        """Generiert zufälliges Wetter basierend auf Region und Jahreszeit"""
        season = self.game_time.get_season()
        region = self.current_region
        
        # Basis-Wahrscheinlichkeiten
        weights = dict(self.SEASONAL_WEATHER.get(season, {}))
        
        # Klimazonen-Modifikator
        if region:
            climate_mods = self.CLIMATE_MODIFIERS.get(region.climate_zone, {})
            for wtype, mod in climate_mods.items():
                if mod < 0:
                    # Entfernen
                    weights.pop(wtype, None)
                else:
                    # Addieren
                    weights[wtype] = weights.get(wtype, 0) + mod
            
            # Regionen-spezifische Gewichte
            for wtype_str, weight in region.weather_weights.items():
                try:
                    wtype = WeatherType(wtype_str)
                    weights[wtype] = weight
                except ValueError:
                    pass
            
            # Höhe beachten (Schnee in hohen Lagen)
            if region.altitude >= region.always_snow_above_altitude:
                if season == Season.WINTER:
                    weights[WeatherType.SNOW] = weights.get(WeatherType.SNOW, 0) + 0.3
                    weights[WeatherType.SNOW_HEAVY] = weights.get(WeatherType.SNOW_HEAVY, 0) + 0.2
                else:
                    weights[WeatherType.SNOW_LIGHT] = weights.get(WeatherType.SNOW_LIGHT, 0) + 0.15
            
            # Verbotene Wetter entfernen
            for forbidden in region.forbidden_weather:
                try:
                    wtype = WeatherType(forbidden)
                    weights.pop(wtype, None)
                except ValueError:
                    pass
        
        # Normalisieren
        total = sum(weights.values())
        if total <= 0:
            weather_type = WeatherType.CLEAR
        else:
            weights = {k: v/total for k, v in weights.items()}
            
            # Zufällige Auswahl
            r = random.random()
            cumulative = 0.0
            weather_type = WeatherType.CLEAR
            
            for wtype, weight in weights.items():
                cumulative += weight
                if r <= cumulative:
                    weather_type = wtype
                    break
        
        # Neuen Zustand erstellen
        new_state = self._create_weather_state(weather_type)
        
        # Sanfter Übergang
        self._target_weather = new_state
        self._transition_progress = 0.0
        
        print(f"🌤️ Wetter ändert sich zu: {weather_type.value}")
    
    def _create_weather_state(self, weather_type: WeatherType) -> WeatherState:
        """Erstellt einen Weather-State für einen Typ"""
        season = self.game_time.get_season()
        region = self.current_region
        
        # Basis-Temperatur nach Jahreszeit
        base_temps = {
            Season.SPRING: 15,
            Season.SUMMER: 25,
            Season.AUTUMN: 12,
            Season.WINTER: 2
        }
        temp = base_temps.get(season, 15)
        
        # Region-Modifikator
        if region:
            temp += region.temperature_modifier
            
            # Höhen-Korrektur (ca. 6°C pro 1000m)
            temp -= (region.altitude // 1000) * 6
        
        # Wetter-spezifische Anpassungen
        weather_configs = {
            WeatherType.CLEAR: {
                "wind": 5, "humidity": 40, "visibility": 1.0, "precipitation": 0, "overlay": 0
            },
            WeatherType.PARTLY_CLOUDY: {
                "wind": 10, "humidity": 50, "visibility": 0.95, "precipitation": 0, "overlay": 0.1
            },
            WeatherType.CLOUDY: {
                "wind": 15, "humidity": 60, "visibility": 0.85, "precipitation": 0, "overlay": 0.2
            },
            WeatherType.OVERCAST: {
                "wind": 10, "humidity": 70, "visibility": 0.7, "precipitation": 0, "overlay": 0.3
            },
            WeatherType.FOG: {
                "wind": 0, "humidity": 95, "visibility": 0.2, "precipitation": 0, "overlay": 0.6,
                "temp_mod": -5
            },
            WeatherType.MIST: {
                "wind": 5, "humidity": 85, "visibility": 0.5, "precipitation": 0, "overlay": 0.4
            },
            WeatherType.RAIN_LIGHT: {
                "wind": 10, "humidity": 80, "visibility": 0.7, "precipitation": 0.3, "overlay": 0.4,
                "temp_mod": -3
            },
            WeatherType.RAIN: {
                "wind": 20, "humidity": 90, "visibility": 0.5, "precipitation": 0.6, "overlay": 0.6,
                "temp_mod": -5
            },
            WeatherType.RAIN_HEAVY: {
                "wind": 30, "humidity": 95, "visibility": 0.3, "precipitation": 0.9, "overlay": 0.8,
                "temp_mod": -7
            },
            WeatherType.THUNDERSTORM: {
                "wind": 40, "humidity": 95, "visibility": 0.2, "precipitation": 0.8, "overlay": 0.9,
                "temp_mod": -8
            },
            WeatherType.SNOW_LIGHT: {
                "wind": 5, "humidity": 70, "visibility": 0.7, "precipitation": 0.3, "overlay": 0.4,
                "temp_mod": -10
            },
            WeatherType.SNOW: {
                "wind": 15, "humidity": 80, "visibility": 0.4, "precipitation": 0.6, "overlay": 0.6,
                "temp_mod": -12
            },
            WeatherType.SNOW_HEAVY: {
                "wind": 30, "humidity": 90, "visibility": 0.2, "precipitation": 0.9, "overlay": 0.8,
                "temp_mod": -15
            },
            WeatherType.BLIZZARD: {
                "wind": 60, "humidity": 95, "visibility": 0.05, "precipitation": 1.0, "overlay": 1.0,
                "temp_mod": -20
            },
            WeatherType.SANDSTORM: {
                "wind": 50, "humidity": 10, "visibility": 0.1, "precipitation": 0, "overlay": 0.9,
                "temp_mod": 5
            },
            WeatherType.WIND: {
                "wind": 40, "humidity": 40, "visibility": 0.9, "precipitation": 0, "overlay": 0.2
            },
            WeatherType.STORM: {
                "wind": 60, "humidity": 80, "visibility": 0.4, "precipitation": 0.5, "overlay": 0.7,
                "temp_mod": -5
            }
        }
        
        config = weather_configs.get(weather_type, weather_configs[WeatherType.CLEAR])
        
        # Temperatur anpassen
        temp += config.get("temp_mod", 0)
        
        # Etwas Varianz hinzufügen
        temp += random.randint(-3, 3)
        wind = config["wind"] + random.randint(-5, 5)
        
        return WeatherState(
            weather_type=weather_type,
            temperature=temp,
            wind_speed=max(0, wind),
            humidity=config["humidity"],
            visibility=config["visibility"],
            precipitation=config["precipitation"],
            overlay_intensity=config["overlay"]
        )
    
    def _interpolate_weather(self):
        """Interpoliert zwischen aktuellem und Ziel-Wetter"""
        if not self._target_weather:
            return
        
        t = self._transition_progress
        
        # Lineare Interpolation für numerische Werte
        self.current_weather.temperature = int(
            self.current_weather.temperature * (1-t) + 
            self._target_weather.temperature * t
        )
        self.current_weather.wind_speed = int(
            self.current_weather.wind_speed * (1-t) + 
            self._target_weather.wind_speed * t
        )
        self.current_weather.humidity = int(
            self.current_weather.humidity * (1-t) + 
            self._target_weather.humidity * t
        )
        self.current_weather.visibility = (
            self.current_weather.visibility * (1-t) + 
            self._target_weather.visibility * t
        )
        self.current_weather.precipitation = (
            self.current_weather.precipitation * (1-t) + 
            self._target_weather.precipitation * t
        )
        self.current_weather.overlay_intensity = (
            self.current_weather.overlay_intensity * (1-t) + 
            self._target_weather.overlay_intensity * t
        )
    
    def get_weather_overlay_name(self) -> str:
        """Gibt den Namen des passenden Wetter-Overlays zurück"""
        wtype = self.current_weather.weather_type
        
        overlay_mapping = {
            WeatherType.RAIN_LIGHT: "rain_light",
            WeatherType.RAIN: "rain",
            WeatherType.RAIN_HEAVY: "rain_heavy",
            WeatherType.THUNDERSTORM: "thunderstorm",
            WeatherType.SNOW_LIGHT: "snow_light",
            WeatherType.SNOW: "snow",
            WeatherType.SNOW_HEAVY: "snow_heavy",
            WeatherType.BLIZZARD: "blizzard",
            WeatherType.FOG: "fog",
            WeatherType.MIST: "mist",
            WeatherType.SANDSTORM: "sandstorm"
        }
        
        return overlay_mapping.get(wtype, "")
    
    def set_random_weather(self, enabled: bool):
        """Aktiviert/deaktiviert zufälliges Wetter"""
        self.random_weather = enabled
    
    def to_dict(self) -> dict:
        return {
            "current_weather": self.current_weather.to_dict(),
            "current_region_id": self.current_region.id if self.current_region else "",
            "random_weather": self.random_weather,
            "weather_change_interval": self.weather_change_interval,
            "regions": {rid: r.to_dict() for rid, r in self.regions.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict, game_time: GameTime) -> 'WeatherSystem':
        ws = cls(game_time)
        
        # Regionen laden
        for rid, rdata in data.get("regions", {}).items():
            ws.register_region(Region.from_dict(rdata))
        
        # Aktuelle Werte
        ws.current_weather = WeatherState.from_dict(data.get("current_weather", {}))
        ws.random_weather = data.get("random_weather", True)
        ws.weather_change_interval = data.get("weather_change_interval", 3600)
        
        # Region setzen
        region_id = data.get("current_region_id", "default")
        if region_id in ws.regions:
            ws.set_region(region_id)
        
        return ws


class TimeWeatherManager:
    """
    Kombinierter Manager für Zeit und Wetter
    Integriert sich mit dem Lighting-System
    """
    
    def __init__(self):
        self.game_time = GameTime()
        self.weather_system = WeatherSystem(self.game_time)
        
        # Lighting-Integration
        self.lighting_engine = None  # Wird von außen gesetzt
        
        # GM-Controls
        self.gm_override_time = False
        self.gm_override_weather = False
        
        # Callbacks für externe Systeme
        self.on_time_change: Optional[Callable[[GameTime], None]] = None
        self.on_weather_change: Optional[Callable[[WeatherState], None]] = None
        self.on_lighting_update: Optional[Callable[[float, Tuple[int,int,int]], None]] = None
        
        # Setup interner Callbacks
        self.game_time.on_time_of_day_change = self._on_time_of_day_changed
        self.weather_system.on_weather_change = self._on_weather_changed
        
        # Update-Timer
        self._last_update = time.time()
    
    def update(self, delta_seconds: float = 0):
        """Update-Tick für Zeit und Wetter"""
        if delta_seconds <= 0:
            current = time.time()
            delta_seconds = current - self._last_update
            self._last_update = current
        
        # Zeit updaten
        if not self.gm_override_time:
            self.game_time.update(delta_seconds)
        
        # Wetter updaten
        if not self.gm_override_weather:
            self.weather_system.update(delta_seconds)
        
        # Lighting updaten
        self._update_lighting()
    
    def _update_lighting(self):
        """Aktualisiert das Lighting basierend auf Zeit und Wetter"""
        sun = self.game_time.get_sun_intensity()
        ambient = self.game_time.get_ambient_color()
        
        # Wetter-Modifikation
        weather = self.weather_system.current_weather
        
        # Bewölkung reduziert Sonnenlicht
        sun *= weather.visibility
        
        # Regen/Schnee verdunkelt
        sun *= (1.0 - weather.precipitation * 0.3)
        
        if self.on_lighting_update:
            self.on_lighting_update(sun, ambient)
        
        if self.lighting_engine:
            # Hier würde Integration mit LightingEngine stattfinden
            pass
    
    def _on_time_of_day_changed(self, time_of_day: TimeOfDay):
        """Callback wenn Tageszeit wechselt"""
        print(f"🕐 Tageszeit: {time_of_day.value}")
        if self.on_time_change:
            self.on_time_change(self.game_time)
    
    def _on_weather_changed(self, weather: WeatherState):
        """Callback wenn Wetter wechselt"""
        print(f"🌤️ Wetter: {weather.weather_type.value}, {weather.temperature}°C")
        if self.on_weather_change:
            self.on_weather_change(weather)
    
    # GM Controls
    def gm_set_time(self, hour: int, minute: int = 0):
        """GM setzt die Zeit manuell"""
        self.gm_override_time = True
        self.game_time.set_time(hour, minute)
    
    def gm_set_weather(self, weather_type: str):
        """GM setzt das Wetter manuell"""
        self.gm_override_weather = True
        self.weather_system.set_weather(weather_type, immediate=True)
    
    def gm_resume_auto(self):
        """GM gibt Kontrolle zurück an automatische Systeme"""
        self.gm_override_time = False
        self.gm_override_weather = False
    
    def gm_advance_time(self, hours: int):
        """GM lässt Zeit vorspulen"""
        self.game_time.add_hours(hours)
    
    # Zustandsspeicherung
    def to_dict(self) -> dict:
        return {
            "game_time": self.game_time.to_dict(),
            "weather_system": self.weather_system.to_dict(),
            "gm_override_time": self.gm_override_time,
            "gm_override_weather": self.gm_override_weather
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeWeatherManager':
        manager = cls()
        
        manager.game_time = GameTime.from_dict(data.get("game_time", {}))
        manager.weather_system = WeatherSystem.from_dict(
            data.get("weather_system", {}),
            manager.game_time
        )
        manager.gm_override_time = data.get("gm_override_time", False)
        manager.gm_override_weather = data.get("gm_override_weather", False)
        
        return manager


# ============================================================
# PRESET REGIONS
# ============================================================

PRESET_REGIONS = {
    "shire": Region(
        id="shire",
        name="Das Auenland",
        climate_zone=ClimateZone.TEMPERATE,
        altitude=100,
        temperature_modifier=2,
        weather_weights={
            "clear": 0.35,
            "partly_cloudy": 0.30,
            "rain_light": 0.15
        }
    ),
    "mordor": Region(
        id="mordor",
        name="Mordor",
        climate_zone=ClimateZone.DESERT,
        altitude=500,
        temperature_modifier=10,
        forbidden_weather=["snow", "snow_light", "snow_heavy", "blizzard"],
        weather_weights={
            "overcast": 0.40,
            "fog": 0.20,
            "sandstorm": 0.10
        }
    ),
    "moria": Region(
        id="moria",
        name="Moria",
        climate_zone=ClimateZone.MOUNTAIN,
        altitude=0,  # Unterirdisch
        temperature_modifier=-5,
        forbidden_weather=["rain", "rain_light", "rain_heavy", "snow", "thunderstorm"],
        weather_weights={
            "clear": 0.5,  # Kein Wetter in Höhlen
            "fog": 0.3,
            "mist": 0.2
        }
    ),
    "rivendell": Region(
        id="rivendell",
        name="Bruchtal",
        climate_zone=ClimateZone.FOREST,
        altitude=800,
        temperature_modifier=0,
        weather_weights={
            "clear": 0.40,
            "partly_cloudy": 0.25,
            "mist": 0.15,
            "rain_light": 0.10
        }
    ),
    "misty_mountains": Region(
        id="misty_mountains",
        name="Nebelgebirge",
        climate_zone=ClimateZone.MOUNTAIN,
        altitude=2500,
        temperature_modifier=-15,
        always_snow_above_altitude=2000,
        weather_weights={
            "snow": 0.25,
            "snow_light": 0.20,
            "fog": 0.15,
            "wind": 0.15,
            "storm": 0.10
        }
    ),
    "fangorn": Region(
        id="fangorn",
        name="Fangorn-Wald",
        climate_zone=ClimateZone.FOREST,
        altitude=400,
        temperature_modifier=-3,
        weather_weights={
            "fog": 0.25,
            "mist": 0.25,
            "overcast": 0.20,
            "rain_light": 0.15
        }
    ),
    "dead_marshes": Region(
        id="dead_marshes",
        name="Totensümpfe",
        climate_zone=ClimateZone.SWAMP,
        altitude=50,
        temperature_modifier=-2,
        weather_weights={
            "fog": 0.35,
            "mist": 0.30,
            "overcast": 0.20,
            "rain_light": 0.10
        }
    ),
    "gondor_coast": Region(
        id="gondor_coast",
        name="Küste Gondors",
        climate_zone=ClimateZone.COASTAL,
        altitude=10,
        temperature_modifier=5,
        weather_weights={
            "clear": 0.30,
            "partly_cloudy": 0.25,
            "mist": 0.15,
            "wind": 0.15,
            "storm": 0.08
        }
    )
}


def register_preset_regions(weather_system: WeatherSystem):
    """Registriert alle vordefinierten Regionen"""
    for region in PRESET_REGIONS.values():
        weather_system.register_region(region)
