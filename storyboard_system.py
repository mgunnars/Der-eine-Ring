"""
Storyboard System für "Der Eine Ring" VTT
=========================================

Ein komplettes Storyboard-System für interaktive Geschichten mit:
- Szenen/Kapitel-Management
- Video- und Map-Integration
- Event/Trigger-System (Point-and-Click Logik)
- Zustandsmaschine für Story-Progression

Autor: VTT Development Team
Version: 1.0.0
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import copy


class SceneType(Enum):
    """Typ einer Szene"""
    VIDEO = "video"           # MP4 Video aus Unity/Blender
    MAP_JSON = "map_json"     # JSON-basierte Tile-Map
    MAP_SVG = "map_svg"       # SVG Vektor-Map
    IMAGE = "image"           # Statisches Bild
    CUTSCENE = "cutscene"     # Video ohne Interaktion


class TriggerType(Enum):
    """Auslöser-Typ für Events"""
    CLICK = "click"                   # Spieler klickt auf Bereich
    ENTER_ZONE = "enter_zone"         # Spieler betritt Zone
    LEAVE_ZONE = "leave_zone"         # Spieler verlässt Zone
    TIME_ELAPSED = "time_elapsed"     # Zeit vergangen
    CONDITION_MET = "condition_met"   # Bedingung erfüllt
    ITEM_USED = "item_used"           # Gegenstand benutzt
    DIALOGUE_END = "dialogue_end"     # Dialog beendet
    COMBAT_END = "combat_end"         # Kampf beendet
    CUSTOM = "custom"                 # Benutzerdefiniert


class ActionType(Enum):
    """Aktions-Typ für Events"""
    CHANGE_SCENE = "change_scene"         # Szene wechseln
    PLAY_VIDEO = "play_video"             # Video abspielen
    SHOW_DIALOGUE = "show_dialogue"       # Dialog anzeigen
    ADD_ITEM = "add_item"                 # Gegenstand geben
    REMOVE_ITEM = "remove_item"           # Gegenstand entfernen
    SET_FLAG = "set_flag"                 # Flag setzen
    SPAWN_ENCOUNTER = "spawn_encounter"   # Begegnung erstellen
    PLAY_SOUND = "play_sound"             # Sound abspielen
    SET_WEATHER = "set_weather"           # Wetter ändern
    SET_TIME = "set_time"                 # Tageszeit setzen
    SHOW_OVERLAY = "show_overlay"         # Overlay anzeigen
    HIDE_OVERLAY = "hide_overlay"         # Overlay verstecken
    TELEPORT = "teleport"                 # Spieler teleportieren
    CUSTOM = "custom"                     # Benutzerdefinierte Aktion


class ConditionOperator(Enum):
    """Operatoren für Bedingungen"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    AND = "and"
    OR = "or"


@dataclass
class Condition:
    """Eine Bedingung für Events oder Aktionen"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    variable: str = ""              # z.B. "flags.door_unlocked", "time.hour", "weather.type"
    operator: ConditionOperator = ConditionOperator.EQUALS
    value: Any = None               # Vergleichswert
    sub_conditions: List['Condition'] = field(default_factory=list)  # Für AND/OR
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "variable": self.variable,
            "operator": self.operator.value,
            "value": self.value,
            "sub_conditions": [c.to_dict() for c in self.sub_conditions]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Condition':
        cond = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            variable=data.get("variable", ""),
            operator=ConditionOperator(data.get("operator", "equals")),
            value=data.get("value")
        )
        cond.sub_conditions = [cls.from_dict(c) for c in data.get("sub_conditions", [])]
        return cond


@dataclass
class Action:
    """Eine Aktion die ausgeführt werden kann"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action_type: ActionType = ActionType.SET_FLAG
    target: str = ""                # Ziel der Aktion (z.B. Szene-ID, Sound-Datei)
    parameters: Dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0              # Verzögerung in Sekunden
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "delay": self.delay
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Action':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            action_type=ActionType(data.get("action_type", "set_flag")),
            target=data.get("target", ""),
            parameters=data.get("parameters", {}),
            delay=data.get("delay", 0.0)
        )


@dataclass
class Trigger:
    """Ein Auslöser für Events"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trigger_type: TriggerType = TriggerType.CLICK
    zone: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2) für Klick/Zone
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    cooldown: float = 0.0           # Abklingzeit in Sekunden
    max_triggers: int = -1          # -1 = unbegrenzt
    _trigger_count: int = 0
    _last_triggered: float = 0.0
    
    # UI-Darstellung
    name: str = ""
    icon: str = "⚡"
    color: str = "#ffaa00"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trigger_type": self.trigger_type.value,
            "zone": self.zone,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "cooldown": self.cooldown,
            "max_triggers": self.max_triggers,
            "name": self.name,
            "icon": self.icon,
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Trigger':
        trigger = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            trigger_type=TriggerType(data.get("trigger_type", "click")),
            zone=tuple(data["zone"]) if data.get("zone") else None,
            cooldown=data.get("cooldown", 0.0),
            max_triggers=data.get("max_triggers", -1),
            name=data.get("name", ""),
            icon=data.get("icon", "⚡"),
            color=data.get("color", "#ffaa00")
        )
        trigger.conditions = [Condition.from_dict(c) for c in data.get("conditions", [])]
        trigger.actions = [Action.from_dict(a) for a in data.get("actions", [])]
        return trigger


@dataclass
class Overlay:
    """Ein Video/Bild-Overlay für Wetter, Effekte etc."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    file_path: str = ""             # MP4, GIF oder PNG
    opacity: float = 1.0
    blend_mode: str = "normal"      # normal, multiply, screen, overlay
    z_index: int = 100              # Höher = weiter vorne
    position: Tuple[int, int] = (0, 0)  # Offset
    scale: float = 1.0
    loop: bool = True
    visible: bool = True
    
    # Für animierte Overlays
    animation_speed: float = 1.0
    
    # Kategorien für einfache Verwaltung
    category: str = "effect"        # weather, effect, ui, ambient
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "file_path": self.file_path,
            "opacity": self.opacity,
            "blend_mode": self.blend_mode,
            "z_index": self.z_index,
            "position": self.position,
            "scale": self.scale,
            "loop": self.loop,
            "visible": self.visible,
            "animation_speed": self.animation_speed,
            "category": self.category
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Overlay':
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            file_path=data.get("file_path", ""),
            opacity=data.get("opacity", 1.0),
            blend_mode=data.get("blend_mode", "normal"),
            z_index=data.get("z_index", 100),
            position=tuple(data.get("position", (0, 0))),
            scale=data.get("scale", 1.0),
            loop=data.get("loop", True),
            visible=data.get("visible", True),
            animation_speed=data.get("animation_speed", 1.0),
            category=data.get("category", "effect")
        )


@dataclass
class Scene:
    """Eine Szene im Storyboard"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Neue Szene"
    description: str = ""
    scene_type: SceneType = SceneType.MAP_JSON
    
    # Content (je nach Typ)
    content_path: str = ""          # Pfad zu Video/Map/Bild
    background_source: str = ""     # Alias für content_path (UI-Kompatibilität)
    map_data: Optional[dict] = None # Embedded Map-Daten (JSON)
    
    # Audio-Einstellungen
    ambient_audio: str = ""         # Hintergrund-Audio Datei
    ambient_volume: float = 0.7     # Audio-Lautstärke (0.0 - 1.0)
    
    # Overlays für diese Szene
    overlays: List[Overlay] = field(default_factory=list)
    
    # Trigger/Events für diese Szene
    triggers: List[Trigger] = field(default_factory=list)
    
    # Verbindungen zu anderen Szenen
    connections: Dict[str, str] = field(default_factory=dict)  # trigger_id -> scene_id
    
    # Szenen-Einstellungen
    ambient_sound: str = ""         # Hintergrund-Sound (Legacy)
    music_track: str = ""           # Musik-Track
    default_weather: str = "clear"  # Standard-Wetter
    time_of_day: str = "auto"       # auto, morning, noon, evening, night
    loop_background: bool = True    # Hintergrund loopen (für Videos)
    interactive: bool = True        # Szene ist interaktiv
    
    # Startpunkt für Spieler
    spawn_point: Tuple[int, int] = (0, 0)
    
    # Region-Daten (für Wetter-System)
    region_id: str = ""
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "scene_type": self.scene_type.value,
            "content_path": self.content_path,
            "background_source": self.background_source,
            "map_data": self.map_data,
            "ambient_audio": self.ambient_audio,
            "ambient_volume": self.ambient_volume,
            "overlays": [o.to_dict() for o in self.overlays],
            "triggers": [t.to_dict() for t in self.triggers],
            "connections": self.connections,
            "ambient_sound": self.ambient_sound,
            "music_track": self.music_track,
            "default_weather": self.default_weather,
            "time_of_day": self.time_of_day,
            "loop_background": self.loop_background,
            "interactive": self.interactive,
            "spawn_point": self.spawn_point,
            "region_id": self.region_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Scene':
        scene = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Neue Szene"),
            description=data.get("description", ""),
            scene_type=SceneType(data.get("scene_type", "map_json")),
            content_path=data.get("content_path", ""),
            background_source=data.get("background_source", ""),
            map_data=data.get("map_data"),
            ambient_audio=data.get("ambient_audio", ""),
            ambient_volume=data.get("ambient_volume", 0.7),
            connections=data.get("connections", {}),
            ambient_sound=data.get("ambient_sound", ""),
            music_track=data.get("music_track", ""),
            default_weather=data.get("default_weather", "clear"),
            time_of_day=data.get("time_of_day", "auto"),
            loop_background=data.get("loop_background", True),
            interactive=data.get("interactive", True),
            spawn_point=tuple(data.get("spawn_point", (0, 0))),
            region_id=data.get("region_id", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            modified_at=data.get("modified_at", datetime.now().isoformat()),
            tags=data.get("tags", [])
        )
        scene.overlays = [Overlay.from_dict(o) for o in data.get("overlays", [])]
        scene.triggers = [Trigger.from_dict(t) for t in data.get("triggers", [])]
        return scene


@dataclass
class Chapter:
    """Ein Kapitel/Abschnitt der Geschichte"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Neues Kapitel"
    description: str = ""
    order: int = 0
    locked: bool = False            # Kapitel gesperrt bis Voraussetzungen erfüllt
    
    # Szenen in diesem Kapitel
    scenes: List[Scene] = field(default_factory=list)
    start_scene_id: str = ""        # Start-Szene des Kapitels
    
    # Kapitel-weite Einstellungen
    required_flags: List[str] = field(default_factory=list)  # Flags die gesetzt sein müssen
    
    # Metadaten
    icon: str = "📖"
    color: str = "#4a90d9"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "locked": self.locked,
            "scenes": [s.to_dict() for s in self.scenes],
            "start_scene_id": self.start_scene_id,
            "required_flags": self.required_flags,
            "icon": self.icon,
            "color": self.color
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Chapter':
        chapter = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Neues Kapitel"),
            description=data.get("description", ""),
            order=data.get("order", 0),
            locked=data.get("locked", False),
            start_scene_id=data.get("start_scene_id", ""),
            required_flags=data.get("required_flags", []),
            icon=data.get("icon", "📖"),
            color=data.get("color", "#4a90d9")
        )
        chapter.scenes = [Scene.from_dict(s) for s in data.get("scenes", [])]
        return chapter


@dataclass
class Storyboard:
    """Das Haupt-Storyboard einer Kampagne"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Neue Kampagne"
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    
    # Kapitel
    chapters: List[Chapter] = field(default_factory=list)
    
    # Globale Einstellungen
    start_chapter_id: str = ""
    
    # Asset-Pfade
    assets_path: str = "assets/"
    videos_path: str = "videos/"
    audio_path: str = "audio/"
    
    # Metadaten
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "chapters": [c.to_dict() for c in self.chapters],
            "start_chapter_id": self.start_chapter_id,
            "assets_path": self.assets_path,
            "videos_path": self.videos_path,
            "audio_path": self.audio_path,
            "created_at": self.created_at,
            "modified_at": self.modified_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Storyboard':
        sb = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Neue Kampagne"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            start_chapter_id=data.get("start_chapter_id", ""),
            assets_path=data.get("assets_path", "assets/"),
            videos_path=data.get("videos_path", "videos/"),
            audio_path=data.get("audio_path", "audio/"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            modified_at=data.get("modified_at", datetime.now().isoformat())
        )
        sb.chapters = [Chapter.from_dict(c) for c in data.get("chapters", [])]
        return sb
    
    def save(self, filepath: str):
        """Speichert das Storyboard als JSON"""
        self.modified_at = datetime.now().isoformat()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: str) -> 'Storyboard':
        """Lädt ein Storyboard aus einer JSON-Datei"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class GameState:
    """
    Spielzustand-Manager
    Speichert Flags, Inventar, Fortschritt etc.
    """
    
    def __init__(self):
        self.flags: Dict[str, Any] = {}           # Globale Flags
        self.inventory: List[str] = []             # Spieler-Inventar
        self.visited_scenes: Set[str] = set()      # Besuchte Szenen
        self.current_chapter_id: str = ""
        self.current_scene_id: str = ""
        self.play_time: float = 0.0                # Spielzeit in Sekunden
        
        # Event-History für Debugging/Achievements
        self.event_history: List[Dict] = []
    
    def set_flag(self, key: str, value: Any = True):
        """Setzt ein Flag"""
        self.flags[key] = value
        self.event_history.append({
            "type": "flag_set",
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_flag(self, key: str, default: Any = None) -> Any:
        """Liest ein Flag"""
        return self.flags.get(key, default)
    
    def add_item(self, item_id: str):
        """Fügt einen Gegenstand hinzu"""
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            self.event_history.append({
                "type": "item_added",
                "item": item_id,
                "timestamp": datetime.now().isoformat()
            })
    
    def remove_item(self, item_id: str):
        """Entfernt einen Gegenstand"""
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            self.event_history.append({
                "type": "item_removed",
                "item": item_id,
                "timestamp": datetime.now().isoformat()
            })
    
    def has_item(self, item_id: str) -> bool:
        """Prüft ob Spieler einen Gegenstand hat"""
        return item_id in self.inventory
    
    def mark_scene_visited(self, scene_id: str):
        """Markiert eine Szene als besucht"""
        self.visited_scenes.add(scene_id)
    
    def to_dict(self) -> dict:
        return {
            "flags": self.flags,
            "inventory": self.inventory,
            "visited_scenes": list(self.visited_scenes),
            "current_chapter_id": self.current_chapter_id,
            "current_scene_id": self.current_scene_id,
            "play_time": self.play_time,
            "event_history": self.event_history
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GameState':
        state = cls()
        state.flags = data.get("flags", {})
        state.inventory = data.get("inventory", [])
        state.visited_scenes = set(data.get("visited_scenes", []))
        state.current_chapter_id = data.get("current_chapter_id", "")
        state.current_scene_id = data.get("current_scene_id", "")
        state.play_time = data.get("play_time", 0.0)
        state.event_history = data.get("event_history", [])
        return state
    
    def save(self, filepath: str):
        """Speichert den Spielstand"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, filepath: str) -> 'GameState':
        """Lädt einen Spielstand"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class StoryboardEngine:
    """
    Haupt-Engine für das Storyboard-System
    Verwaltet den Ablauf der Geschichte
    """
    
    def __init__(self, storyboard: Optional[Storyboard] = None):
        self.storyboard = storyboard or Storyboard()
        self.game_state = GameState()
        
        # Aktuelle Szene
        self.current_scene: Optional[Scene] = None
        
        # Event-Callbacks
        self.on_scene_change: Optional[Callable[[Scene], None]] = None
        self.on_trigger_activated: Optional[Callable[[Trigger], None]] = None
        self.on_action_executed: Optional[Callable[[Action], None]] = None
        self.on_overlay_change: Optional[Callable[[Overlay, bool], None]] = None
        
        # Externe System-Referenzen (werden von außen gesetzt)
        self.weather_system = None
        self.time_system = None
        self.danger_system = None
        self.video_manager = None
        
        # Pending Actions (verzögerte Aktionen)
        self._pending_actions: List[Tuple[float, Action]] = []
        self._time_accumulator: float = 0.0
    
    def start(self):
        """Startet die Geschichte"""
        if not self.storyboard.chapters:
            print("⚠️ Keine Kapitel im Storyboard!")
            return
        
        # Erstes Kapitel finden
        start_chapter = None
        if self.storyboard.start_chapter_id:
            for chapter in self.storyboard.chapters:
                if chapter.id == self.storyboard.start_chapter_id:
                    start_chapter = chapter
                    break
        
        if not start_chapter:
            start_chapter = self.storyboard.chapters[0]
        
        # In erstes Kapitel/Szene wechseln
        self.go_to_chapter(start_chapter.id)
    
    def go_to_chapter(self, chapter_id: str) -> bool:
        """Wechselt zu einem Kapitel"""
        chapter = self.get_chapter(chapter_id)
        if not chapter:
            print(f"⚠️ Kapitel '{chapter_id}' nicht gefunden!")
            return False
        
        # Prüfe Required Flags
        for flag in chapter.required_flags:
            if not self.game_state.get_flag(flag):
                print(f"⚠️ Kapitel benötigt Flag '{flag}'!")
                return False
        
        self.game_state.current_chapter_id = chapter_id
        
        # Zur Start-Szene des Kapitels
        start_scene_id = chapter.start_scene_id or (chapter.scenes[0].id if chapter.scenes else "")
        if start_scene_id:
            return self.go_to_scene(start_scene_id)
        
        return True
    
    def go_to_scene(self, scene_id: str) -> bool:
        """Wechselt zu einer Szene"""
        scene = self.get_scene(scene_id)
        if not scene:
            print(f"⚠️ Szene '{scene_id}' nicht gefunden!")
            return False
        
        # Alte Szene verlassen
        if self.current_scene:
            self._on_leave_scene(self.current_scene)
        
        # Neue Szene betreten
        self.current_scene = scene
        self.game_state.current_scene_id = scene_id
        self.game_state.mark_scene_visited(scene_id)
        
        self._on_enter_scene(scene)
        
        # Callback
        if self.on_scene_change:
            self.on_scene_change(scene)
        
        print(f"🎬 Szene gewechselt: {scene.name}")
        return True
    
    def _on_enter_scene(self, scene: Scene):
        """Wird beim Betreten einer Szene aufgerufen"""
        # Wetter setzen
        if scene.default_weather != "clear" and self.weather_system:
            self.weather_system.set_weather(scene.default_weather)
        
        # Tageszeit setzen
        if scene.time_of_day != "auto" and self.time_system:
            self.time_system.set_time_of_day(scene.time_of_day)
        
        # Overlays aktivieren
        for overlay in scene.overlays:
            if overlay.visible and self.on_overlay_change:
                self.on_overlay_change(overlay, True)
    
    def _on_leave_scene(self, scene: Scene):
        """Wird beim Verlassen einer Szene aufgerufen"""
        # Overlays deaktivieren
        for overlay in scene.overlays:
            if self.on_overlay_change:
                self.on_overlay_change(overlay, False)
    
    def process_click(self, x: int, y: int):
        """Verarbeitet einen Klick auf der aktuellen Szene"""
        if not self.current_scene:
            return
        
        for trigger in self.current_scene.triggers:
            if trigger.trigger_type != TriggerType.CLICK:
                continue
            
            # Prüfe Zone
            if trigger.zone:
                x1, y1, x2, y2 = trigger.zone
                if not (x1 <= x <= x2 and y1 <= y <= y2):
                    continue
            
            # Prüfe Bedingungen
            if not self._evaluate_conditions(trigger.conditions):
                continue
            
            # Prüfe Cooldown und Max-Triggers
            if not self._can_trigger(trigger):
                continue
            
            # Trigger aktivieren
            self._activate_trigger(trigger)
    
    def process_zone_enter(self, x: int, y: int):
        """Verarbeitet das Betreten einer Zone"""
        if not self.current_scene:
            return
        
        for trigger in self.current_scene.triggers:
            if trigger.trigger_type != TriggerType.ENTER_ZONE:
                continue
            
            if trigger.zone:
                x1, y1, x2, y2 = trigger.zone
                if not (x1 <= x <= x2 and y1 <= y <= y2):
                    continue
            
            if not self._evaluate_conditions(trigger.conditions):
                continue
            
            if not self._can_trigger(trigger):
                continue
            
            self._activate_trigger(trigger)
    
    def _can_trigger(self, trigger: Trigger) -> bool:
        """Prüft ob ein Trigger aktiviert werden kann"""
        import time
        current_time = time.time()
        
        # Cooldown prüfen
        if trigger.cooldown > 0:
            if current_time - trigger._last_triggered < trigger.cooldown:
                return False
        
        # Max-Triggers prüfen
        if trigger.max_triggers >= 0:
            if trigger._trigger_count >= trigger.max_triggers:
                return False
        
        return True
    
    def _activate_trigger(self, trigger: Trigger):
        """Aktiviert einen Trigger und führt dessen Aktionen aus"""
        import time
        
        trigger._trigger_count += 1
        trigger._last_triggered = time.time()
        
        print(f"⚡ Trigger aktiviert: {trigger.name or trigger.id}")
        
        if self.on_trigger_activated:
            self.on_trigger_activated(trigger)
        
        # Aktionen ausführen
        for action in trigger.actions:
            if action.delay > 0:
                # Verzögerte Aktion
                self._pending_actions.append((action.delay, action))
            else:
                self._execute_action(action)
    
    def _execute_action(self, action: Action):
        """Führt eine Aktion aus"""
        print(f"🎯 Aktion: {action.action_type.value} -> {action.target}")
        
        if action.action_type == ActionType.CHANGE_SCENE:
            self.go_to_scene(action.target)
        
        elif action.action_type == ActionType.SET_FLAG:
            value = action.parameters.get("value", True)
            self.game_state.set_flag(action.target, value)
        
        elif action.action_type == ActionType.ADD_ITEM:
            self.game_state.add_item(action.target)
        
        elif action.action_type == ActionType.REMOVE_ITEM:
            self.game_state.remove_item(action.target)
        
        elif action.action_type == ActionType.SET_WEATHER:
            if self.weather_system:
                self.weather_system.set_weather(action.target)
        
        elif action.action_type == ActionType.SET_TIME:
            if self.time_system:
                self.time_system.set_time_of_day(action.target)
        
        elif action.action_type == ActionType.SHOW_OVERLAY:
            overlay = self._get_overlay(action.target)
            if overlay and self.on_overlay_change:
                overlay.visible = True
                self.on_overlay_change(overlay, True)
        
        elif action.action_type == ActionType.HIDE_OVERLAY:
            overlay = self._get_overlay(action.target)
            if overlay and self.on_overlay_change:
                overlay.visible = False
                self.on_overlay_change(overlay, False)
        
        elif action.action_type == ActionType.SPAWN_ENCOUNTER:
            if self.danger_system:
                self.danger_system.spawn_encounter(action.target, **action.parameters)
        
        elif action.action_type == ActionType.PLAY_VIDEO:
            if self.video_manager:
                self.video_manager.play_video(action.target, **action.parameters)
        
        if self.on_action_executed:
            self.on_action_executed(action)
    
    def _get_overlay(self, overlay_id: str) -> Optional[Overlay]:
        """Findet ein Overlay anhand der ID"""
        if not self.current_scene:
            return None
        
        for overlay in self.current_scene.overlays:
            if overlay.id == overlay_id or overlay.name == overlay_id:
                return overlay
        return None
    
    def _evaluate_conditions(self, conditions: List[Condition]) -> bool:
        """Evaluiert eine Liste von Bedingungen (AND-verknüpft)"""
        if not conditions:
            return True
        
        for condition in conditions:
            if not self._evaluate_condition(condition):
                return False
        return True
    
    def _evaluate_condition(self, condition: Condition) -> bool:
        """Evaluiert eine einzelne Bedingung"""
        # AND/OR für Sub-Conditions
        if condition.operator == ConditionOperator.AND:
            return all(self._evaluate_condition(c) for c in condition.sub_conditions)
        elif condition.operator == ConditionOperator.OR:
            return any(self._evaluate_condition(c) for c in condition.sub_conditions)
        
        # Variable auslesen
        value = self._get_variable_value(condition.variable)
        target = condition.value
        
        # Vergleichen
        if condition.operator == ConditionOperator.EQUALS:
            return value == target
        elif condition.operator == ConditionOperator.NOT_EQUALS:
            return value != target
        elif condition.operator == ConditionOperator.GREATER_THAN:
            return value > target if value is not None else False
        elif condition.operator == ConditionOperator.LESS_THAN:
            return value < target if value is not None else False
        elif condition.operator == ConditionOperator.CONTAINS:
            return target in value if value else False
        elif condition.operator == ConditionOperator.NOT_CONTAINS:
            return target not in value if value else True
        
        return False
    
    def _get_variable_value(self, variable: str) -> Any:
        """Liest den Wert einer Variable"""
        parts = variable.split(".")
        
        if parts[0] == "flags":
            return self.game_state.get_flag(".".join(parts[1:]))
        elif parts[0] == "inventory":
            if len(parts) > 1:
                return parts[1] in self.game_state.inventory
            return self.game_state.inventory
        elif parts[0] == "time":
            if self.time_system:
                if parts[1] == "hour":
                    return self.time_system.get_hour()
                elif parts[1] == "is_day":
                    return self.time_system.is_day()
                elif parts[1] == "is_night":
                    return self.time_system.is_night()
        elif parts[0] == "weather":
            if self.weather_system:
                if parts[1] == "type":
                    return self.weather_system.current_weather
        elif parts[0] == "danger":
            if self.danger_system:
                if parts[1] == "level":
                    return self.danger_system.danger_level
        
        return None
    
    def update(self, delta_time: float):
        """Update-Loop für verzögerte Aktionen"""
        self._time_accumulator += delta_time
        self.game_state.play_time += delta_time
        
        # Pending Actions verarbeiten
        ready_actions = []
        remaining_actions = []
        
        for delay, action in self._pending_actions:
            new_delay = delay - delta_time
            if new_delay <= 0:
                ready_actions.append(action)
            else:
                remaining_actions.append((new_delay, action))
        
        self._pending_actions = remaining_actions
        
        for action in ready_actions:
            self._execute_action(action)
    
    def get_chapter(self, chapter_id: str) -> Optional[Chapter]:
        """Findet ein Kapitel anhand der ID"""
        for chapter in self.storyboard.chapters:
            if chapter.id == chapter_id:
                return chapter
        return None
    
    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Findet eine Szene anhand der ID (sucht in allen Kapiteln)"""
        for chapter in self.storyboard.chapters:
            for scene in chapter.scenes:
                if scene.id == scene_id:
                    return scene
        return None
    
    def create_scene(self, name: str, scene_type: SceneType = SceneType.MAP_JSON,
                    chapter_id: Optional[str] = None) -> Scene:
        """Erstellt eine neue Szene"""
        scene = Scene(name=name, scene_type=scene_type)
        
        # Zu Kapitel hinzufügen
        if chapter_id:
            chapter = self.get_chapter(chapter_id)
            if chapter:
                chapter.scenes.append(scene)
        elif self.storyboard.chapters:
            self.storyboard.chapters[0].scenes.append(scene)
        
        return scene
    
    def create_trigger(self, scene_id: str, trigger_type: TriggerType,
                      zone: Optional[Tuple[int, int, int, int]] = None,
                      name: str = "") -> Optional[Trigger]:
        """Erstellt einen neuen Trigger für eine Szene"""
        scene = self.get_scene(scene_id)
        if not scene:
            return None
        
        trigger = Trigger(
            trigger_type=trigger_type,
            zone=zone,
            name=name
        )
        scene.triggers.append(trigger)
        return trigger
    
    def create_chapter(self, name: str, order: int = -1) -> Chapter:
        """Erstellt ein neues Kapitel"""
        if order < 0:
            order = len(self.storyboard.chapters)
        
        chapter = Chapter(name=name, order=order)
        self.storyboard.chapters.append(chapter)
        
        # Sortieren nach Order
        self.storyboard.chapters.sort(key=lambda c: c.order)
        
        return chapter


# ============================================================
# FACTORY-FUNKTIONEN für einfache Erstellung
# ============================================================

def create_click_trigger(zone: Tuple[int, int, int, int], 
                        target_scene: str,
                        name: str = "") -> Trigger:
    """Erstellt einen einfachen Klick-Trigger der zu einer anderen Szene wechselt"""
    return Trigger(
        trigger_type=TriggerType.CLICK,
        zone=zone,
        name=name,
        actions=[
            Action(
                action_type=ActionType.CHANGE_SCENE,
                target=target_scene
            )
        ]
    )


def create_conditional_trigger(zone: Tuple[int, int, int, int],
                               flag_name: str,
                               target_scene_true: str,
                               target_scene_false: str,
                               name: str = "") -> Trigger:
    """Erstellt einen Trigger der je nach Flag zu verschiedenen Szenen führt"""
    return Trigger(
        trigger_type=TriggerType.CLICK,
        zone=zone,
        name=name,
        conditions=[
            Condition(variable=f"flags.{flag_name}", operator=ConditionOperator.EQUALS, value=True)
        ],
        actions=[
            Action(action_type=ActionType.CHANGE_SCENE, target=target_scene_true)
        ]
    )


def create_weather_overlay(weather_type: str, video_path: str) -> Overlay:
    """Erstellt ein Wetter-Overlay"""
    return Overlay(
        name=f"Weather: {weather_type}",
        file_path=video_path,
        category="weather",
        opacity=0.7,
        blend_mode="screen",
        z_index=200,
        loop=True
    )


def create_effect_overlay(name: str, video_path: str, opacity: float = 1.0) -> Overlay:
    """Erstellt ein Effekt-Overlay"""
    return Overlay(
        name=name,
        file_path=video_path,
        category="effect",
        opacity=opacity,
        blend_mode="normal",
        z_index=150,
        loop=True
    )
