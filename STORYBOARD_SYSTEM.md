# 🎬 Storyboard-System Dokumentation
## Der Eine Ring - Virtual Tabletop

---

## Übersicht

Das Storyboard-System erweitert das VTT um umfangreiche Features für interaktives Storytelling:

### Neue Module

| Modul | Beschreibung |
|-------|-------------|
| `storyboard_system.py` | Kern-System mit Szenen, Kapiteln, Triggern, Actions |
| `video_overlay_manager.py` | Video-Wiedergabe und Overlay-Compositing |
| `time_weather_system.py` | Tag/Nacht-Zyklus und Wettersystem |
| `danger_encounter_system.py` | Gefahrenstufen und Zufallsbegegnungen |
| `story_editor.py` | Visueller Editor für Storyboards |
| `story_editor_*.py` | Editor-Komponenten (Scenes, Graph, Properties) |

---

## 1. Storyboard-Struktur

```
Storyboard
├── Chapter (Kapitel)
│   ├── name, icon, description
│   ├── start_scene_id
│   ├── locked (erfordert Freischaltung)
│   └── Scene[] (Szenen)
│       ├── name, scene_type
│       ├── background_source (Video/Bild/Map)
│       ├── Trigger[] (Auslöser)
│       │   ├── trigger_type (CLICK, HOVER, TIMER, etc.)
│       │   ├── conditions[] (Bedingungen)
│       │   └── actions[] (Aktionen)
│       └── Overlay[] (Überlagerungen)
└── variables (Spielzustand)
```

### Szenen-Typen (`SceneType`)

| Typ | Beschreibung |
|-----|-------------|
| `VIDEO` | MP4/WebM als Hintergrund (aus Unity/Blender) |
| `MAP_JSON` | VTT-Karte im JSON-Format |
| `MAP_SVG` | Vektor-basierte SVG-Karte |
| `IMAGE` | Statisches Bild |
| `CUTSCENE` | Video-Sequenz ohne Interaktion |

### Trigger-Typen (`TriggerType`)

| Typ | Beschreibung |
|-----|-------------|
| `CLICK` | Klick auf Element |
| `HOVER` | Maus über Element |
| `TIMER` | Zeit-basiert |
| `ENTER_AREA` | Token betritt Bereich |
| `LEAVE_AREA` | Token verlässt Bereich |
| `CONDITION` | Variable erfüllt Bedingung |
| `CUSTOM` | Benutzerdefiniert |

### Action-Typen (`ActionType`)

| Typ | Beschreibung |
|-----|-------------|
| `TRANSITION` | Szenen-Übergang |
| `PLAY_SOUND` | Audio abspielen |
| `SHOW_TEXT` | Text anzeigen |
| `SET_VARIABLE` | Variable setzen |
| `ADD_OVERLAY` | Overlay hinzufügen |
| `REMOVE_OVERLAY` | Overlay entfernen |
| `CAMERA_MOVE` | Kamera bewegen/zoomen |
| `SPAWN_TOKEN` | Token erstellen |
| `TRIGGER_WEATHER` | Wetter ändern |
| `RUN_SCRIPT` | Skript ausführen |

---

## 2. Video-Overlay-System

### Features

- **Video-Maps**: MP4-Hintergründe statt dynamischer Beleuchtung
- **Wetter-Overlays**: Regen, Schnee, Nebel als Video-Layer
- **Blend-Modi**: Normal, Multiply, Screen, Overlay, Add
- **GPU-Beschleunigung**: Optional mit OpenCV

### Verwendung

```python
from video_overlay_manager import VideoOverlayManager

manager = VideoOverlayManager()

# Video-Map laden
manager.load_video_map("maps/forest.mp4")

# Wetter-Overlay hinzufügen
manager.add_overlay(
    name="rain",
    source="effects/rain.webm",
    blend_mode="screen",
    opacity=0.6
)

# Frame abrufen
frame = manager.get_composite_frame()
```

---

## 3. Zeit- und Wettersystem

### Tageszeiten

| Zeit | Stunden | Lichtstärke |
|------|---------|-------------|
| DAWN | 5-7 | 0.4-0.8 |
| MORNING | 7-12 | 0.9-1.0 |
| NOON | 12-14 | 1.0 |
| AFTERNOON | 14-18 | 0.9-1.0 |
| DUSK | 18-21 | 0.8-0.3 |
| NIGHT | 21-5 | 0.1-0.2 |

### Wetter-Typen

- `CLEAR` - Klar
- `CLOUDY` - Bewölkt
- `RAIN` - Regen
- `STORM` - Sturm
- `SNOW` - Schnee
- `FOG` - Nebel
- `WIND` - Windig

### Regionen (Presets)

- **The Shire**: Mild, wenig Regen
- **Mordor**: Heiß, trocken, Asche
- **Mirkwood**: Dunkel, neblig
- **Rivendell**: Angenehm, klar
- **Misty Mountains**: Kalt, Schnee

### Verwendung

```python
from time_weather_system import TimeWeatherManager, PRESET_REGIONS

manager = TimeWeatherManager()

# Region setzen
manager.set_region(PRESET_REGIONS["mirkwood"])

# Zeit setzen (10:30 Uhr)
manager.time_system.set_time(10, 30)

# Wetter manuell ändern
manager.weather_system.force_weather(WeatherType.FOG, intensity=0.8)

# Aktuellen Zustand abfragen
state = manager.get_current_state()
print(f"Zeit: {state['time_of_day']}")
print(f"Wetter: {state['weather']}")
print(f"Lichtstärke: {state['light_level']}")
```

---

## 4. Gefahren- und Begegnungssystem

### Gefahrenstufen

| Stufe | Beschreibung | Begegnungschance |
|-------|-------------|------------------|
| SAFE | Sicher (Städte) | 0% |
| LOW | Gering | 5% |
| MODERATE | Mittel | 15% |
| HIGH | Hoch | 25% |
| EXTREME | Extrem | 40% |

### Modifikatoren

- **Nachtzeit**: +50% Begegnungschance
- **Schlechtes Wetter**: +25% Begegnungschance

### Kreaturen (Presets)

```python
PRESET_CREATURES = {
    "wolf": Creature(name="Wolf", danger_level=DangerLevel.LOW, ...),
    "warg": Creature(name="Warg", danger_level=DangerLevel.MODERATE, ...),
    "orc_scout": Creature(name="Ork-Späher", ...),
    "uruk_hai": Creature(name="Uruk-hai", ...),
    "troll": Creature(name="Höhlentroll", ...),
    "nazgul": Creature(name="Nazgûl", danger_level=DangerLevel.EXTREME, ...)
}
```

### Verwendung

```python
from danger_encounter_system import DangerSystem, PRESET_CREATURES

danger = DangerSystem()

# Kreaturen hinzufügen
danger.add_creature(PRESET_CREATURES["wolf"], weight=10)
danger.add_creature(PRESET_CREATURES["orc_scout"], weight=5)

# Begegnung generieren
encounter = danger.generate_encounter(
    time_of_day=TimeOfDay.NIGHT,
    weather=WeatherType.STORM
)

if encounter:
    print(f"Begegnung: {encounter.creature.name}")
```

---

## 5. Story Editor

### Öffnen

```python
from story_editor import open_story_editor, Storyboard

# Neuer Story Editor
editor = open_story_editor()

# Mit bestehendem Storyboard
storyboard = Storyboard.load("my_adventure.story.json")
editor = open_story_editor(storyboard=storyboard)
```

### Layout

```
┌────────────────────────────────────────────────────────────┐
│ 📄 📂 💾  |  📖 🎬  |  ▶️ 🎮        📚 Abenteuer-Name      │
├──────────┬─────────────────────────────┬──────────────────┤
│ 📚 Kapitel│      🔗 Flow-Graph          │  ⚙️ Eigenschaften│
│           │                             │                  │
│ 📖 Prolog │   ┌─────┐    ┌─────┐       │  🎬 Szene        │
│   🎬 Intro│   │Intro├───▶│Dorf │       │  Name: ___       │
│   🎬 Dorf │   └─────┘    └──┬──┘       │                  │
│           │                 │          │  ⚡ Trigger:     │
│ 📖 Kap. 1 │            ┌────▼────┐     │  [+ Hinzufügen]  │
│   🎬 Wald │            │  Wald   │     │                  │
│   🎬 Höhle│            └─────────┘     │  🎭 Overlays:    │
│           │                             │  [+ Hinzufügen]  │
└──────────┴─────────────────────────────┴──────────────────┘
│ Bereit                              2 Kapitel | 4 Szenen   │
└────────────────────────────────────────────────────────────┘
```

### Tastenkürzel

| Taste | Aktion |
|-------|--------|
| Ctrl+N | Neues Storyboard |
| Ctrl+O | Öffnen |
| Ctrl+S | Speichern |
| Del | Löschen |
| F5 | Vorschau |

### Flow-Graph

- **Doppelklick** auf Szene: Verbindung erstellen
- **Mittlere Maustaste**: Pan
- **Mausrad**: Zoom
- **Rechtsklick**: Kontext-Menü

---

## 6. Integration ins VTT

### Main-Integration

```python
# In map_editor.py oder main.py

from story_editor import open_story_editor
from storyboard_system import StoryboardEngine

class VTTApplication:
    def __init__(self):
        self.storyboard_engine = None
        
    def open_story_editor(self):
        """Story Editor öffnen"""
        editor = open_story_editor(
            parent=self.root,
            on_scene_preview=self.preview_scene
        )
    
    def preview_scene(self, scene):
        """Szene im Projektor anzeigen"""
        if scene.scene_type == SceneType.VIDEO:
            self.projector.load_video(scene.background_source)
        elif scene.scene_type == SceneType.MAP_JSON:
            self.projector.load_map(scene.background_source)
    
    def start_adventure(self, storyboard_path):
        """Abenteuer starten"""
        storyboard = Storyboard.load(storyboard_path)
        self.storyboard_engine = StoryboardEngine(storyboard)
        
        # Erstes Kapitel, erste Szene laden
        self.storyboard_engine.start()
```

### GM-Kontrollen

```python
# Zeit/Wetter Panel für GM
from time_weather_system import TimeWeatherManager

class GMControlPanel:
    def __init__(self, parent, time_weather: TimeWeatherManager):
        self.tw = time_weather
        
        # Zeit-Slider
        self.time_slider = tk.Scale(
            parent, from_=0, to=24,
            command=self._on_time_change
        )
        
        # Wetter-Buttons
        for weather in WeatherType:
            tk.Button(
                parent, text=weather.value,
                command=lambda w=weather: self.tw.force_weather(w)
            )
    
    def _on_time_change(self, hour):
        self.tw.time_system.set_time(int(hour), 0)
```

---

## 7. Datei-Format

### Storyboard JSON

```json
{
  "id": "uuid",
  "name": "Der Eine Ring - Beispiel",
  "author": "Spielleiter",
  "version": "1.0",
  "chapters": [
    {
      "id": "uuid",
      "name": "Prolog",
      "icon": "📖",
      "description": "Die Reise beginnt...",
      "locked": false,
      "start_scene_id": "scene_uuid",
      "scenes": [
        {
          "id": "scene_uuid",
          "name": "Beutelsend",
          "scene_type": "map_json",
          "background_source": "maps/bag_end.json",
          "triggers": [
            {
              "id": "trigger_uuid",
              "name": "Tür öffnen",
              "trigger_type": "click",
              "actions": [
                {
                  "action_type": "transition",
                  "params": {
                    "target_scene_id": "other_scene_uuid",
                    "transition_type": "fade"
                  }
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  "variables": {}
}
```

---

## 8. Best Practices

### Performance

1. **Videos**: Verwende MP4 (H.264) für beste Kompatibilität
2. **Overlays**: WebM mit Alpha-Kanal für transparente Effekte
3. **Auflösung**: 1920x1080 für Projektor-Darstellung

### Storytelling

1. **Klare Szenen-Namen**: "Beutelsend - Wohnzimmer" statt "Szene 1"
2. **Trigger-Logik**: Einfach halten, komplexe Logik in Variablen
3. **Kapitel-Struktur**: Thematisch gruppieren

### Datei-Organisation

```
abenteuer/
├── adventure.story.json
├── maps/
│   ├── village.json
│   └── forest.svg
├── videos/
│   ├── intro_cutscene.mp4
│   └── forest_ambient.mp4
├── effects/
│   ├── rain.webm
│   └── fog.webm
└── audio/
    ├── ambient_forest.mp3
    └── combat_music.mp3
```

---

## 9. Changelog

### Version 1.0.0

- ✅ Storyboard Core System
- ✅ Video/Overlay Manager
- ✅ Zeit- und Wettersystem
- ✅ Gefahren- und Begegnungssystem
- ✅ Visueller Story Editor
  - Kapitel/Szenen-Verwaltung
  - Flow-Graph mit Bezier-Kurven
  - Trigger/Action Editor
  - Properties Panel

---

## 10. Nächste Schritte

- [ ] Audio-Manager Integration
- [ ] Token-Automatisierung
- [ ] Netzwerk-Synchronisation
- [ ] Import/Export für andere VTTs
- [ ] Undo/Redo im Editor
