# Partikel-System - Blender-ähnlicher Effekt-Generator

Ein leistungsstarkes Partikel-System zum Erstellen von Regen, Schnee, Feuer und anderen Effekten als Video-Overlays.

## 🆕 NEU: 2D/2.5D Regen-Editor

Spezieller Editor für realistische Regen-Overlays mit:
- **Kamera-Winkel**: 0° (direkt von oben) bis 75° (fast seitlich)
- **Glas-Effekt**: Realistische Regentropfen mit Refraktion und Glanz
- **Wasseroberfläche**: Empfänger-Canvas mit Ripple- und Splash-Effekten

### Starten
```bash
python particle_editor_2d.py
```

### 2D Editor Features
- Einstellbarer Blickwinkel (isometrisch 30°, von oben 0°, dramatisch 45°, etc.)
- Tropfen mit Glas-Optik (Lichtbrechung, Spiegelung, Bewegungsunschärfe)
- Wasseroberfläche mit realistischen Wellenkreisen beim Aufprall
- Splash-Partikel beim Einschlag
- Quick-Presets: Leichter Regen, Starkregen, Platzregen + Sturm
- Export als WebM (mit Alpha!), MP4, GIF, APNG oder PNG-Sequenz

---

## Features

### 🎨 Partikel-Typen
- **Regen** - Realistische Regentropfen mit Kollision
- **Schnee** - Langsam fallende Schneeflocken mit Wind
- **Feuer** - Flammen mit Funken und Rauch
- **Rauch** - Aufsteigender Rauch mit Turbulenz
- **Funken** - Sprühende Funken mit Trails
- **Nebel** - Atmosphärischer Nebel
- **Magie** - Magische Partikel mit Wirbel-Effekt
- **Blätter** - Fallende Herbstblätter
- **Blasen** - Aufsteigende Blasen
- **Staub** - Schwebende Staubpartikel

### ⚙️ Physik-Simulation
- Schwerkraft
- Wind mit Turbulenz
- Wirbel/Vortex-Kräfte
- Kollisionserkennung mit Bounce
- Partikel-Trails

### 🎥 Export-Formate
- **MP4** - Komprimiertes Video (benötigt ffmpeg)
- **WebM** - Video mit Alpha-Kanal (Transparenz!)
- **GIF** - Animiertes GIF
- **APNG** - Animiertes PNG mit voller Transparenz
- **PNG-Sequenz** - Einzelbilder für weitere Bearbeitung

## Installation

### Voraussetzungen
```bash
pip install numpy pillow PyQt5
```

### Optional für besseres Rendering
```bash
pip install pycairo scipy
```

### Optional für Video-Export (MP4/WebM)
Installiere ffmpeg:
- **Windows**: https://ffmpeg.org/download.html oder `winget install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`

## Verwendung

### GUI-Editor starten
```bash
python particle_editor.py
```

### Programmatisch verwenden

```python
from particle_system import ParticleCanvas, ParticleEmitter, ParticleType
from particle_exporter import ParticleExporter, ExportSettings, ExportFormat

# Canvas erstellen
canvas = ParticleCanvas(1920, 1080)

# Regen-Emitter hinzufügen
from particle_system import RectEmitter, Vector3
emitter = ParticleEmitter(ParticleType.RAIN)
emitter.shape = RectEmitter(
    position=Vector3(960, -50, 0),
    width=2000,
    height=20
)
canvas.add_emitter(emitter)

# Exportieren
exporter = ParticleExporter()
settings = ExportSettings(
    format=ExportFormat.WEBM,
    width=1920,
    height=1080,
    fps=30,
    duration=5.0,
    transparent_background=True
)
exporter.export(canvas, "regen_overlay.webm", settings)
```

### Schnell-Funktionen

```python
from particle_exporter import (
    create_rain_overlay,
    create_snow_overlay,
    create_fire_overlay,
    create_magic_overlay,
    ExportFormat
)

# Regen-Overlay erstellen
create_rain_overlay("regen.webm", 
    width=1920, height=1080,
    duration=10.0,
    intensity=1.5,
    format=ExportFormat.WEBM
)

# Schnee-Overlay
create_snow_overlay("schnee.webm",
    width=1920, height=1080,
    duration=15.0,
    intensity=0.8
)

# Feuer-Effekt
create_fire_overlay("feuer.webm",
    width=400, height=400,
    duration=5.0
)

# Magische Partikel
create_magic_overlay("magie.webm",
    width=400, height=400,
    color=(0.8, 0.3, 1.0)  # Lila
)
```

## Editor-Bedienung

### Hauptbereiche
1. **Links**: Emitter-Liste und Eigenschaften
2. **Mitte**: Live-Vorschau
3. **Rechts**: Canvas-Einstellungen und Export

### Emitter-Eigenschaften
- **Typ**: Wähle aus 12 Partikel-Typen
- **Emission**: Rate und Maximum
- **Lebensdauer**: Wie lange Partikel leben
- **Geschwindigkeit**: Start-Speed und Streuung
- **Größe**: Start- und Endgröße
- **Farbe**: Start- und Endfarbe mit Alpha
- **Trail**: Partikel-Schweif
- **Physik**: Gravitation, Wind, Turbulenz

### Tastenkürzel
- `Ctrl+N` - Neues Projekt
- `Ctrl+E` - Exportieren
- `Ctrl+Q` - Beenden

## Emitter-Formen

### PointEmitter
Einzelner Punkt als Quelle.

### LineEmitter
Linie zwischen zwei Punkten.

### RectEmitter
Rechteckiger Bereich (ideal für Regen/Schnee).

### CircleEmitter
Kreisförmiger Bereich (ideal für Feuer/Explosionen).

### SphereEmitter
3D-Kugelförmig (mit perspektivischer Projektion).

## Kräfte

### GravityForce
```python
from particle_system import GravityForce, Vector3
force = GravityForce(
    direction=Vector3(0, 1, 0),  # Nach unten
    strength=200
)
emitter.forces.append(force)
```

### WindForce
```python
from particle_system import WindForce
force = WindForce(
    direction=Vector3(1, 0, 0),  # Nach rechts
    strength=50,
    turbulence=20,
    radius=10000
)
emitter.forces.append(force)
```

### VortexForce
```python
from particle_system import VortexForce
force = VortexForce(
    position=Vector3(400, 300, 0),
    strength=100,
    radius=200,
    inward_strength=30
)
emitter.forces.append(force)
```

## Tipps für realistische Effekte

### Regen
- Hohe Emission-Rate (300-500)
- Schnelle Geschwindigkeit (600-1000)
- Kleine Partikel (2-4)
- Trail-Länge 3-5
- Blend-Mode: ADD

### Schnee
- Niedrige Emission-Rate (50-100)
- Langsame Geschwindigkeit (30-80)
- Mittlere Partikel (4-8)
- Rotation für Taumeln
- Wind mit Turbulenz

### Feuer
- Mehrere Emitter kombinieren:
  1. Flammen (orange/gelb)
  2. Funken (helle Punkte)
  3. Rauch (grau, aufsteigend)
- Blend-Mode: ADD für Flammen
- Glow-Effekt aktivieren

### Nebel
- Sehr große Partikel (50-150)
- Lange Lebensdauer (8-15s)
- Niedrige Alpha-Werte (0.1-0.3)
- Minimale Geschwindigkeit
- Leichter Wind

## Performance-Tipps

1. **Max Particles begrenzen**: 5000-10000 für flüssige Vorschau
2. **Export-FPS**: 30 reicht meist aus
3. **Größe optimieren**: Kleinere Canvas = schnellerer Export
4. **GIF vermeiden**: Bei vielen Farben besser APNG/WebM

## Dateien

- `particle_system.py` - Kern-System (Partikel, Emitter, Physik)
- `particle_renderer.py` - Fortgeschrittenes Rendering
- `particle_exporter.py` - Video-Export
- `particle_editor.py` - GUI-Editor

## Lizenz

Teil des Der-eine-Ring Projekts.
