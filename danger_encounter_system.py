"""
Danger & Encounter System für "Der Eine Ring" VTT
==================================================

Verwaltet Gefahrenstufen und zufällige Begegnungen basierend auf:
- Tageszeit (nachts gefährlicher)
- Wetter (Sturm erhöht Gefahr)
- Region (Mordor gefährlicher als Auenland)
- Story-Flags (Quest-abhängige Begegnungen)

Autor: VTT Development Team
Version: 1.0.0
"""

import random
import json
from typing import Dict, List, Optional, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid


class EncounterType(Enum):
    """Art der Begegnung"""
    COMBAT = "combat"               # Kampf
    SOCIAL = "social"               # Soziale Interaktion
    ENVIRONMENTAL = "environmental" # Umweltgefahr
    DISCOVERY = "discovery"         # Entdeckung
    TRAP = "trap"                   # Falle
    MYSTERY = "mystery"             # Mysterium
    MERCHANT = "merchant"           # Händler
    REST = "rest"                   # Rastplatz/Zuflucht


class DangerLevel(Enum):
    """Gefahrenstufe"""
    SAFE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    EXTREME = 4
    DEADLY = 5


class CreatureCategory(Enum):
    """Kreatur-Kategorie"""
    BEAST = "beast"             # Wilde Tiere
    HUMANOID = "humanoid"       # Menschen, Elfen, Zwerge etc.
    ORC = "orc"                 # Orks und Goblins
    UNDEAD = "undead"           # Untote
    MONSTER = "monster"         # Monster (Trolle, Drachen etc.)
    SPIRIT = "spirit"           # Geister und übernatürliche Wesen
    SPIDER = "spider"           # Spinnen
    WOLF = "wolf"               # Wölfe und Warge


@dataclass
class Creature:
    """Eine Kreatur für Begegnungen"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Unbekannte Kreatur"
    category: CreatureCategory = CreatureCategory.BEAST
    
    # Kampfwerte (vereinfacht)
    health: int = 10
    attack: int = 3
    defense: int = 2
    
    # Verhalten
    aggression: float = 0.5     # 0 = friedlich, 1 = immer aggressiv
    group_size_min: int = 1
    group_size_max: int = 1
    
    # Beute/Belohnung
    loot: List[str] = field(default_factory=list)
    experience: int = 10
    
    # Bedingungen
    time_restriction: str = ""  # "night", "day", "" = immer
    weather_restriction: str = "" # "fog", "storm", "" = immer
    
    # Beschreibung für GM
    description: str = ""
    tactics: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "health": self.health,
            "attack": self.attack,
            "defense": self.defense,
            "aggression": self.aggression,
            "group_size_min": self.group_size_min,
            "group_size_max": self.group_size_max,
            "loot": self.loot,
            "experience": self.experience,
            "time_restriction": self.time_restriction,
            "weather_restriction": self.weather_restriction,
            "description": self.description,
            "tactics": self.tactics
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Creature':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Unbekannte Kreatur"),
            category=CreatureCategory(data.get("category", "beast")),
            health=data.get("health", 10),
            attack=data.get("attack", 3),
            defense=data.get("defense", 2),
            aggression=data.get("aggression", 0.5),
            group_size_min=data.get("group_size_min", 1),
            group_size_max=data.get("group_size_max", 1),
            loot=data.get("loot", []),
            experience=data.get("experience", 10),
            time_restriction=data.get("time_restriction", ""),
            weather_restriction=data.get("weather_restriction", ""),
            description=data.get("description", ""),
            tactics=data.get("tactics", "")
        )


@dataclass
class Encounter:
    """Eine mögliche Begegnung"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Unbekannte Begegnung"
    encounter_type: EncounterType = EncounterType.COMBAT
    
    # Inhalt
    creatures: List[Creature] = field(default_factory=list)
    description: str = ""
    
    # Gewichtung
    weight: float = 1.0         # Basis-Wahrscheinlichkeit
    min_danger_level: int = 0   # Minimum Gefahrenstufe
    max_danger_level: int = 5   # Maximum Gefahrenstufe
    
    # Bedingungen
    required_flags: List[str] = field(default_factory=list)
    forbidden_flags: List[str] = field(default_factory=list)
    region_ids: List[str] = field(default_factory=list)  # Leer = überall
    
    # Zeit/Wetter
    time_of_day: str = ""       # "day", "night", "dusk", "" = immer
    weather_types: List[str] = field(default_factory=list)  # Leer = alle
    
    # Skalierung
    scale_with_party_size: bool = True
    
    # Belohnungen
    rewards: Dict[str, any] = field(default_factory=dict)
    
    # Einmalig oder wiederholbar
    unique: bool = False
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "encounter_type": self.encounter_type.value,
            "creatures": [c.to_dict() for c in self.creatures],
            "description": self.description,
            "weight": self.weight,
            "min_danger_level": self.min_danger_level,
            "max_danger_level": self.max_danger_level,
            "required_flags": self.required_flags,
            "forbidden_flags": self.forbidden_flags,
            "region_ids": self.region_ids,
            "time_of_day": self.time_of_day,
            "weather_types": self.weather_types,
            "scale_with_party_size": self.scale_with_party_size,
            "rewards": self.rewards,
            "unique": self.unique
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Encounter':
        enc = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Unbekannte Begegnung"),
            encounter_type=EncounterType(data.get("encounter_type", "combat")),
            description=data.get("description", ""),
            weight=data.get("weight", 1.0),
            min_danger_level=data.get("min_danger_level", 0),
            max_danger_level=data.get("max_danger_level", 5),
            required_flags=data.get("required_flags", []),
            forbidden_flags=data.get("forbidden_flags", []),
            region_ids=data.get("region_ids", []),
            time_of_day=data.get("time_of_day", ""),
            weather_types=data.get("weather_types", []),
            scale_with_party_size=data.get("scale_with_party_size", True),
            rewards=data.get("rewards", {}),
            unique=data.get("unique", False)
        )
        enc.creatures = [Creature.from_dict(c) for c in data.get("creatures", [])]
        return enc


@dataclass
class EncounterPool:
    """Eine Sammlung von möglichen Begegnungen"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Standard-Pool"
    
    encounters: List[Encounter] = field(default_factory=list)
    
    # Pool-weite Einstellungen
    base_chance: float = 0.1    # Basis-Chance pro Check
    check_interval: float = 300 # Sekunden zwischen Checks (Spielzeit)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "encounters": [e.to_dict() for e in self.encounters],
            "base_chance": self.base_chance,
            "check_interval": self.check_interval
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EncounterPool':
        pool = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Standard-Pool"),
            base_chance=data.get("base_chance", 0.1),
            check_interval=data.get("check_interval", 300)
        )
        pool.encounters = [Encounter.from_dict(e) for e in data.get("encounters", [])]
        return pool


class DangerSystem:
    """
    Haupt-System für Gefahrenstufen und Begegnungen
    """
    
    # Gefahren-Modifikatoren
    TIME_MODIFIERS = {
        "dawn": 0.8,
        "morning": 0.6,
        "noon": 0.5,
        "afternoon": 0.6,
        "dusk": 0.9,
        "evening": 1.2,
        "night": 1.5
    }
    
    WEATHER_MODIFIERS = {
        "clear": 0.8,
        "partly_cloudy": 0.9,
        "cloudy": 1.0,
        "overcast": 1.1,
        "fog": 1.3,
        "mist": 1.2,
        "rain_light": 1.0,
        "rain": 1.1,
        "rain_heavy": 1.2,
        "thunderstorm": 1.4,
        "snow_light": 1.1,
        "snow": 1.2,
        "snow_heavy": 1.4,
        "blizzard": 1.6,
        "sandstorm": 1.5
    }
    
    REGION_BASE_DANGER = {
        "shire": DangerLevel.SAFE,
        "rivendell": DangerLevel.SAFE,
        "gondor_coast": DangerLevel.LOW,
        "fangorn": DangerLevel.MODERATE,
        "misty_mountains": DangerLevel.HIGH,
        "dead_marshes": DangerLevel.HIGH,
        "moria": DangerLevel.EXTREME,
        "mordor": DangerLevel.DEADLY
    }
    
    def __init__(self):
        # Aktuelle Werte
        self.danger_level = DangerLevel.SAFE
        self.danger_value = 0.0  # Numerischer Wert (0-10)
        
        # Begegnungs-Pools
        self.encounter_pools: Dict[str, EncounterPool] = {}
        self.active_pool_id: str = ""
        
        # Tracking
        self.triggered_unique_encounters: Set[str] = set()
        self._time_since_last_check = 0.0
        
        # Externe Referenzen
        self.time_system = None
        self.weather_system = None
        self.game_state = None  # Für Flags
        
        # Aktueller Kontext
        self.current_region_id: str = "default"
        self.party_size: int = 4
        
        # Callbacks
        self.on_danger_change: Optional[Callable[[DangerLevel, float], None]] = None
        self.on_encounter: Optional[Callable[[Encounter], None]] = None
        
        # Standard-Pool laden
        self._create_default_pool()
    
    def _create_default_pool(self):
        """Erstellt den Standard-Begegnungspool"""
        default_pool = EncounterPool(
            id="default",
            name="Standard-Begegnungen"
        )
        
        # Beispiel-Begegnungen hinzufügen
        default_pool.encounters = [
            # Wilde Tiere
            Encounter(
                name="Wolfsrudel",
                encounter_type=EncounterType.COMBAT,
                creatures=[
                    Creature(
                        name="Wolf",
                        category=CreatureCategory.WOLF,
                        health=15,
                        attack=4,
                        defense=2,
                        aggression=0.7,
                        group_size_min=3,
                        group_size_max=6,
                        time_restriction="night"
                    )
                ],
                weight=1.5,
                min_danger_level=1,
                max_danger_level=3,
                time_of_day="night",
                description="Ein Rudel hungriger Wölfe hat eure Spur aufgenommen."
            ),
            
            # Orks
            Encounter(
                name="Ork-Patrouille",
                encounter_type=EncounterType.COMBAT,
                creatures=[
                    Creature(
                        name="Ork-Krieger",
                        category=CreatureCategory.ORC,
                        health=20,
                        attack=5,
                        defense=3,
                        aggression=0.9,
                        group_size_min=4,
                        group_size_max=8
                    )
                ],
                weight=1.0,
                min_danger_level=2,
                max_danger_level=4,
                description="Eine Gruppe Orks streift durch das Gebiet."
            ),
            
            # Händler
            Encounter(
                name="Wandernder Händler",
                encounter_type=EncounterType.MERCHANT,
                creatures=[],
                weight=0.8,
                min_danger_level=0,
                max_danger_level=2,
                time_of_day="day",
                description="Ein freundlicher Händler mit einem beladenen Pony kreuzt euren Weg."
            ),
            
            # Umweltgefahr
            Encounter(
                name="Steinschlag",
                encounter_type=EncounterType.ENVIRONMENTAL,
                creatures=[],
                weight=0.5,
                min_danger_level=2,
                max_danger_level=4,
                region_ids=["misty_mountains", "moria"],
                description="Steine lösen sich von der Felswand über euch!"
            ),
            
            # Entdeckung
            Encounter(
                name="Verlassenes Lager",
                encounter_type=EncounterType.DISCOVERY,
                creatures=[],
                weight=0.6,
                min_danger_level=0,
                max_danger_level=3,
                description="Ihr entdeckt ein kürzlich verlassenes Lager.",
                rewards={"gold": 50, "items": ["healing_potion"]}
            ),
            
            # Spinnen (nachts im Wald)
            Encounter(
                name="Riesenspinne",
                encounter_type=EncounterType.COMBAT,
                creatures=[
                    Creature(
                        name="Riesenspinne",
                        category=CreatureCategory.SPIDER,
                        health=30,
                        attack=6,
                        defense=4,
                        aggression=0.8,
                        group_size_min=1,
                        group_size_max=2,
                        time_restriction="night"
                    )
                ],
                weight=0.8,
                min_danger_level=3,
                max_danger_level=5,
                time_of_day="night",
                region_ids=["fangorn", "moria"],
                description="Große, glänzende Augen starren euch aus der Dunkelheit an..."
            ),
            
            # Untote (nur nachts, Nebel)
            Encounter(
                name="Wandernde Geister",
                encounter_type=EncounterType.COMBAT,
                creatures=[
                    Creature(
                        name="Schattenwanderer",
                        category=CreatureCategory.UNDEAD,
                        health=25,
                        attack=5,
                        defense=2,
                        aggression=1.0,
                        group_size_min=2,
                        group_size_max=4,
                        weather_restriction="fog"
                    )
                ],
                weight=0.6,
                min_danger_level=4,
                max_danger_level=5,
                time_of_day="night",
                weather_types=["fog", "mist"],
                region_ids=["dead_marshes"],
                description="Blasse Gestalten erheben sich aus dem Nebel..."
            )
        ]
        
        self.encounter_pools["default"] = default_pool
        self.active_pool_id = "default"
    
    def set_region(self, region_id: str):
        """Setzt die aktuelle Region"""
        self.current_region_id = region_id
        self._recalculate_danger()
    
    def update(self, delta_seconds: float):
        """Update-Tick"""
        self._recalculate_danger()
        
        # Begegnungs-Check
        pool = self.encounter_pools.get(self.active_pool_id)
        if pool:
            self._time_since_last_check += delta_seconds
            
            if self._time_since_last_check >= pool.check_interval:
                self._time_since_last_check = 0
                self._check_for_encounter()
    
    def _recalculate_danger(self):
        """Berechnet die aktuelle Gefahrenstufe neu"""
        # Basis aus Region
        base = self.REGION_BASE_DANGER.get(
            self.current_region_id, 
            DangerLevel.LOW
        ).value
        
        # Zeit-Modifikator
        time_mod = 1.0
        if self.time_system:
            tod = self.time_system.get_time_of_day().value
            time_mod = self.TIME_MODIFIERS.get(tod, 1.0)
        
        # Wetter-Modifikator
        weather_mod = 1.0
        if self.weather_system:
            weather = self.weather_system.current_weather.weather_type.value
            weather_mod = self.WEATHER_MODIFIERS.get(weather, 1.0)
        
        # Berechnung
        self.danger_value = base * time_mod * weather_mod
        
        # Auf Stufe mappen
        if self.danger_value < 0.5:
            new_level = DangerLevel.SAFE
        elif self.danger_value < 1.5:
            new_level = DangerLevel.LOW
        elif self.danger_value < 2.5:
            new_level = DangerLevel.MODERATE
        elif self.danger_value < 3.5:
            new_level = DangerLevel.HIGH
        elif self.danger_value < 4.5:
            new_level = DangerLevel.EXTREME
        else:
            new_level = DangerLevel.DEADLY
        
        # Callback bei Änderung
        if new_level != self.danger_level:
            self.danger_level = new_level
            if self.on_danger_change:
                self.on_danger_change(self.danger_level, self.danger_value)
    
    def _check_for_encounter(self):
        """Prüft ob eine zufällige Begegnung stattfindet"""
        pool = self.encounter_pools.get(self.active_pool_id)
        if not pool:
            return
        
        # Basis-Chance modifiziert durch Gefahr
        chance = pool.base_chance * (1 + self.danger_value * 0.2)
        
        if random.random() > chance:
            return
        
        # Passende Begegnung auswählen
        encounter = self._select_encounter(pool)
        
        if encounter:
            print(f"⚔️ Begegnung! {encounter.name}")
            
            # Als ausgelöst markieren
            if encounter.unique:
                self.triggered_unique_encounters.add(encounter.id)
            
            if self.on_encounter:
                self.on_encounter(encounter)
    
    def _select_encounter(self, pool: EncounterPool) -> Optional[Encounter]:
        """Wählt eine passende Begegnung aus dem Pool"""
        valid_encounters = []
        
        for enc in pool.encounters:
            # Gefahrenstufe prüfen
            if not (enc.min_danger_level <= self.danger_level.value <= enc.max_danger_level):
                continue
            
            # Unique bereits ausgelöst?
            if enc.unique and enc.id in self.triggered_unique_encounters:
                continue
            
            # Region prüfen
            if enc.region_ids and self.current_region_id not in enc.region_ids:
                continue
            
            # Tageszeit prüfen
            if enc.time_of_day and self.time_system:
                current_tod = self.time_system.get_time_of_day().value
                if enc.time_of_day == "day" and current_tod in ["night", "evening", "dusk"]:
                    continue
                if enc.time_of_day == "night" and current_tod not in ["night", "evening"]:
                    continue
                if enc.time_of_day not in ["day", "night", ""] and enc.time_of_day != current_tod:
                    continue
            
            # Wetter prüfen
            if enc.weather_types and self.weather_system:
                current_weather = self.weather_system.current_weather.weather_type.value
                if current_weather not in enc.weather_types:
                    continue
            
            # Flags prüfen
            if self.game_state:
                # Required Flags
                if enc.required_flags:
                    if not all(self.game_state.get_flag(f) for f in enc.required_flags):
                        continue
                
                # Forbidden Flags
                if enc.forbidden_flags:
                    if any(self.game_state.get_flag(f) for f in enc.forbidden_flags):
                        continue
            
            valid_encounters.append(enc)
        
        if not valid_encounters:
            return None
        
        # Gewichtete Auswahl
        total_weight = sum(e.weight for e in valid_encounters)
        r = random.random() * total_weight
        
        cumulative = 0.0
        for enc in valid_encounters:
            cumulative += enc.weight
            if r <= cumulative:
                return enc
        
        return valid_encounters[-1]
    
    def spawn_encounter(self, encounter_id: str, **kwargs):
        """Spawnt eine spezifische Begegnung (für Story-Events)"""
        # In allen Pools suchen
        for pool in self.encounter_pools.values():
            for enc in pool.encounters:
                if enc.id == encounter_id:
                    print(f"⚔️ Story-Begegnung: {enc.name}")
                    if self.on_encounter:
                        self.on_encounter(enc)
                    return
        
        print(f"⚠️ Begegnung nicht gefunden: {encounter_id}")
    
    def force_encounter_check(self):
        """Erzwingt einen Begegnungs-Check"""
        self._check_for_encounter()
    
    def get_danger_description(self) -> str:
        """Gibt eine textuelle Beschreibung der Gefahr zurück"""
        descriptions = {
            DangerLevel.SAFE: "Die Gegend wirkt friedlich und sicher.",
            DangerLevel.LOW: "Ihr seid auf der Hut, aber die Gefahr scheint gering.",
            DangerLevel.MODERATE: "Etwas stimmt nicht... haltet eure Waffen bereit.",
            DangerLevel.HIGH: "Gefahr lauert an jeder Ecke. Seid sehr vorsichtig!",
            DangerLevel.EXTREME: "Die Bedrohung ist allgegenwärtig. Jeder Schritt könnte euer letzter sein.",
            DangerLevel.DEADLY: "Nur die Mutigsten - oder Dümmsten - wagen sich hierher."
        }
        return descriptions.get(self.danger_level, "")
    
    def get_danger_icon(self) -> str:
        """Gibt ein Icon für die Gefahrenstufe zurück"""
        icons = {
            DangerLevel.SAFE: "🟢",
            DangerLevel.LOW: "🟡",
            DangerLevel.MODERATE: "🟠",
            DangerLevel.HIGH: "🔴",
            DangerLevel.EXTREME: "💀",
            DangerLevel.DEADLY: "☠️"
        }
        return icons.get(self.danger_level, "❓")
    
    def add_encounter_pool(self, pool: EncounterPool):
        """Fügt einen Begegnungs-Pool hinzu"""
        self.encounter_pools[pool.id] = pool
    
    def set_active_pool(self, pool_id: str):
        """Aktiviert einen Begegnungs-Pool"""
        if pool_id in self.encounter_pools:
            self.active_pool_id = pool_id
    
    def to_dict(self) -> dict:
        return {
            "danger_level": self.danger_level.value,
            "danger_value": self.danger_value,
            "current_region_id": self.current_region_id,
            "active_pool_id": self.active_pool_id,
            "triggered_unique_encounters": list(self.triggered_unique_encounters),
            "encounter_pools": {pid: p.to_dict() for pid, p in self.encounter_pools.items()},
            "party_size": self.party_size
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DangerSystem':
        system = cls()
        
        system.danger_level = DangerLevel(data.get("danger_level", 0))
        system.danger_value = data.get("danger_value", 0.0)
        system.current_region_id = data.get("current_region_id", "default")
        system.active_pool_id = data.get("active_pool_id", "default")
        system.triggered_unique_encounters = set(data.get("triggered_unique_encounters", []))
        system.party_size = data.get("party_size", 4)
        
        # Pools laden
        for pid, pdata in data.get("encounter_pools", {}).items():
            system.encounter_pools[pid] = EncounterPool.from_dict(pdata)
        
        return system


# ============================================================
# PRESET CREATURES
# ============================================================

PRESET_CREATURES = {
    "wolf": Creature(
        id="wolf",
        name="Wolf",
        category=CreatureCategory.WOLF,
        health=15,
        attack=4,
        defense=2,
        aggression=0.6,
        group_size_min=3,
        group_size_max=6,
        time_restriction="night",
        description="Ein grauer Wolf mit hungrigem Blick.",
        tactics="Wolfs umkreisen ihre Beute und greifen koordiniert an."
    ),
    "warg": Creature(
        id="warg",
        name="Warg",
        category=CreatureCategory.WOLF,
        health=35,
        attack=7,
        defense=4,
        aggression=0.8,
        group_size_min=2,
        group_size_max=4,
        description="Ein riesiger, dämonischer Wolf mit glühenden Augen.",
        tactics="Warge sind intelligent und attackieren Schwächere zuerst."
    ),
    "orc_warrior": Creature(
        id="orc_warrior",
        name="Ork-Krieger",
        category=CreatureCategory.ORC,
        health=20,
        attack=5,
        defense=3,
        aggression=0.9,
        group_size_min=4,
        group_size_max=10,
        loot=["orcish_blade", "crude_armor"],
        description="Ein kräftiger Ork in rostiger Rüstung."
    ),
    "orc_archer": Creature(
        id="orc_archer",
        name="Ork-Bogenschütze",
        category=CreatureCategory.ORC,
        health=12,
        attack=4,
        defense=2,
        aggression=0.8,
        group_size_min=2,
        group_size_max=4,
        loot=["crude_bow", "arrows"],
        description="Ein Ork mit einem primitiven Bogen."
    ),
    "uruk_hai": Creature(
        id="uruk_hai",
        name="Uruk-hai",
        category=CreatureCategory.ORC,
        health=40,
        attack=8,
        defense=5,
        aggression=1.0,
        group_size_min=3,
        group_size_max=8,
        loot=["uruk_scimitar", "uruk_armor"],
        description="Ein mächtiger Uruk-hai mit der weißen Hand Sarumans."
    ),
    "giant_spider": Creature(
        id="giant_spider",
        name="Riesenspinne",
        category=CreatureCategory.SPIDER,
        health=30,
        attack=6,
        defense=4,
        aggression=0.7,
        group_size_min=1,
        group_size_max=2,
        time_restriction="night",
        loot=["spider_silk", "venom_sac"],
        description="Eine Spinne so groß wie ein Pferd, mit giftigen Fängen."
    ),
    "troll": Creature(
        id="troll",
        name="Höhlentroll",
        category=CreatureCategory.MONSTER,
        health=80,
        attack=10,
        defense=6,
        aggression=0.5,
        group_size_min=1,
        group_size_max=1,
        time_restriction="night",
        loot=["troll_hide", "gold_pouch"],
        description="Ein gewaltiger Troll mit dicker, steinartiger Haut.",
        tactics="Langsam aber mächtig. Versteinert bei Sonnenlicht!"
    ),
    "nazgul": Creature(
        id="nazgul",
        name="Ringgeist",
        category=CreatureCategory.UNDEAD,
        health=100,
        attack=12,
        defense=8,
        aggression=1.0,
        group_size_min=1,
        group_size_max=1,
        description="Ein Schatten in schwarzer Robe, Diener des Dunklen Herrschers.",
        tactics="Der Ringgeist verbreitet Furcht. Nur Feuer schadet ihm wirklich."
    ),
    "barrow_wight": Creature(
        id="barrow_wight",
        name="Hügelgrab-Geist",
        category=CreatureCategory.UNDEAD,
        health=45,
        attack=7,
        defense=4,
        aggression=0.9,
        group_size_min=1,
        group_size_max=1,
        time_restriction="night",
        weather_restriction="fog",
        description="Ein blasser Geist, gehüllt in uralte Grabtücher.",
        tactics="Zieht Opfer in sein Grab und lähmt sie mit Kälte."
    )
}


def get_preset_creature(creature_id: str) -> Optional[Creature]:
    """Gibt eine vordefinierte Kreatur zurück (Kopie)"""
    if creature_id in PRESET_CREATURES:
        import copy
        return copy.deepcopy(PRESET_CREATURES[creature_id])
    return None
