# 🔥 Verbessertes Lichtsystem - Dokumentation

## Übersicht der Änderungen

Das Lichtsystem wurde komplett überarbeitet, um **physikalisch korrekte Lichtverteilung** und **realistisches Flackern** zu implementieren.

## ✨ Neue Features

### 1. Physikalisch korrekte Lichtabnahme

**Inverse-Square-Law Implementation:**
- Licht folgt jetzt der Formel: `I = I₀ / (1 + (d/r)ⁿ)`
- `n` ist der **Falloff-Exponent** (variiert je nach Lichttyp)
- Standard: `n = 2.0` (echtes Inverse-Square-Law)
- Feuer/Fackeln: `n = 2.5` (stärkerer Abfall)
- Mondlicht: `n = 1.2` (sehr sanfter Abfall)

**Kern-Überhellung (Bloom-Effekt):**
- Innerste 10% des Radius haben erhöhte Helligkeit
- `core_brightness` Parameter (1.2-1.6 je nach Typ)
- Simuliert Überbelichtung im hellen Kern

### 2. Unterschiedliche Lichtintensitäten

Jeder Lichttyp hat nun **eigene physikalische Eigenschaften**:

| Lichttyp | Radius | Intensität | Falloff | Core Brightness |
|----------|--------|------------|---------|-----------------|
| **Fackel (torch)** | 7 | 1.0 | 2.5 | 1.5 |
| **Feuer (fire)** | 8 | 1.2 | 2.5 | 1.5 |
| **Kerze (candle)** | 4 | 0.8 | 2.2 | 1.3 |
| **Laterne (lantern)** | 6 | 0.85 | 2.5 | 1.5 |
| **Magie (magic)** | 8 | 1.1 | 1.8 | 1.6 |
| **Fenster (window)** | 10 | 0.7 | 1.5 | 1.0 |
| **Mondlicht (moonlight)** | 12 | 0.5 | 1.2 | 0.8 |

### 3. Realistisches Flackern

**Neue Flacker-Physik mit Harmonischen:**

```python
# Basis-Welle (Hauptfrequenz)
main_wave = sin(time * frequency * 2π)

# Harmonische (Details)
harmonic1 = sin(time * frequency * 2.3 * 2π) * 0.3
harmonic2 = sin(time * frequency * 3.7 * 2π) * 0.15

# Langsame Drift
slow_drift = sin(time * 0.5 * 2π) * 0.1

# Chaos (Zufälligkeit)
chaos = random(-1, 1) * chaos_factor

# Kombiniert
flicker = (main_wave * 0.5 + harmonic1 * 0.3 + harmonic2 * 0.15 + slow_drift * 0.05 + chaos)
```

**Frequenzen pro Lichttyp:**
- **Fackel/Feuer:** 15 Hz (sehr schnell, stark sichtbar)
- **Kerze:** 8 Hz (sanft)
- **Magie:** 4 Hz (langsames Pulsieren)
- **Fenster:** 1 Hz (minimal, Wind-Effekt)
- **Mondlicht:** 0 Hz (konstant)

**Spezial-Effekte:**
- **Feuer:** Zufällige "Aussetzer" (3% Chance, Intensität sinkt kurz)
- **Feuer:** "Funken" (2% Chance, kurze helle Spitzen)

### 4. Dynamische Farbtemperatur

**Feuer-Gradient (physikalisch korrekt):**
- **Kern (0-15% Radius):** Weißglühend (255, 245, 220)
- **Innen (15-40%):** Helles Gelb-Orange (255, 200, 80)
- **Mitte (40-70%):** Orange (255, 140, 40)
- **Außen (70-100%):** Dunkelrot (180, 60, 20)

**Zeit-basierter Farbshift:**
- Farben "flackern" mit der Zeit
- Simuliert Bewegung der Flamme
- Kombination aus Sinus-Wellen und Distanz

**Kerzen:**
- Sanftes warmes Gelb
- Subtile Variationen

**Magie:**
- Pulsierender Regenbogen-Effekt
- 3 unabhängige Sinus-Wellen für RGB

### 5. Performance-Optimierungen

**Intelligentes Frame-Skipping:**
- Ohne Flackern: Jeder 2. Frame (15 FPS)
- Mit Flackern: Jeder Frame (30 FPS)
- Automatische Erkennung ob flackernde Lichter vorhanden

**Kontinuierliche Animation:**
- `update_animation()` wird in `animate_tiles()` aufgerufen
- Delta-Time: 0.033s (33ms, 30 FPS)
- `time_offset` wird an `render_lighting()` übergeben

## 🎮 Verwendung im Editor

### Lichtquelle hinzufügen:

```python
from lighting_system import LightSource, LIGHT_PRESETS

# Mit Preset
light = LightSource(x=10, y=15, **LIGHT_PRESETS["torch"])
lighting_engine.add_light(light)

# Manuell
light = LightSource(
    x=10, 
    y=15, 
    radius=7,
    color=(255, 180, 80),
    intensity=1.0,
    flicker=True,
    light_type="torch"
)
```

### Verfügbare Presets:

- `torch` - Fackel (warmes Orange, starkes Flackern)
- `fire` - Großes Feuer (intensiv)
- `campfire` - Lagerfeuer (mittel)
- `candle` - Kerze (sanft)
- `lantern` - Laterne (stabil)
- `magic` - Magie (pulsierend, lila)
- `crystal` - Kristall (kühl, blau)
- `brazier` - Feuerschale (groß)
- `window` - Fenster/Tageslicht (blau-weiß)
- `moonlight` - Mondlicht (groß, konstant)

### Animation aktivieren:

Die Animation läuft automatisch im `animate_tiles()` Loop des Projektors:

```python
# In projector_window.py (bereits implementiert):
def animate_tiles(self):
    # ...
    if self.lighting_enabled:
        self.lighting_time += 0.033
        self.lighting_engine.update_animation(0.033)
    # ...
```

## 🧪 Testen

**Test-Demo ausführen:**
```bash
python test_improved_lighting.py
```

Die Demo zeigt:
- 12 verschiedene Lichtquellen-Typen
- Echtzeit-Flackern bei 60 FPS
- Vergleich der Lichtintensitäten
- Einstellbare Umgebungshelligkeit
- Animation-Speed-Control

## 📊 Technische Details

### Klassen-Struktur:

**`LightSource`:**
- `_setup_light_physics()` - Konfiguriert physikalische Parameter
- `get_current_intensity()` - Berechnet Flacker-Intensität
- `get_light_at_position()` - Berechnet Licht an Pixel-Position

**Neue Attribute:**
- `falloff_exponent` - Stärke der Lichtabnahme (1.2-2.5)
- `core_brightness` - Kern-Überhellung (0.8-1.6)
- `flicker_frequency` - Hz (0-15)
- `flicker_amplitude` - Stärke (0.0-0.25)
- `flicker_chaos` - Zufälligkeit (0.0-0.35)

**`LightingEngine`:**
- `update_animation(delta_time)` - Update Timer
- `render_lighting()` - Rendert Licht mit time_offset

### Formeln:

**Lichtabnahme:**
```
falloff = 1.0 / (1.0 + (distance / radius)^falloff_exponent)
```

**Flackern:**
```
intensity = base_intensity + (
    sin(t * f * 2π) * 0.5 +
    sin(t * f * 2.3 * 2π) * 0.3 +
    sin(t * f * 3.7 * 2π) * 0.15 +
    sin(t * 0.5 * 2π) * 0.05 +
    random(-1, 1) * chaos
) * amplitude
```

## 🔧 Anpassung

### Eigenen Lichttyp erstellen:

```python
custom_preset = {
    "radius": 8,
    "color": (255, 100, 200),  # Pink
    "intensity": 1.0,
    "flicker": True,
    "light_type": "custom_fire"  # Verwendet fire-Physik
}

LIGHT_PRESETS["custom_fire"] = custom_preset
```

### Flacker-Parameter anpassen:

In `_setup_light_physics()`:
```python
elif self.light_type == "my_type":
    self.falloff_exponent = 2.0
    self.core_brightness = 1.4
    self.flicker_frequency = 10.0  # 10 Hz
    self.flicker_amplitude = 0.20   # 20% Schwankung
    self.flicker_chaos = 0.25       # Mittleres Chaos
```

## 🎯 Ergebnisse

### Vorher vs. Nachher:

**Vorher:**
- ❌ Flackern nicht sichtbar (zu langsame Frequenz)
- ❌ Linearer Radius (unrealistisch)
- ❌ Alle Lichter gleich intensiv
- ❌ Keine Farbdynamik

**Nachher:**
- ✅ Flackern deutlich sichtbar (15 Hz bei Feuer)
- ✅ Inverse-Square-Law (physikalisch korrekt)
- ✅ 10 verschiedene Lichttypen mit eigenen Eigenschaften
- ✅ Dynamische Farbtemperatur (Feuer: weiß→gelb→orange→rot)
- ✅ Spezialeffekte (Funken, Aussetzer)
- ✅ 30-60 FPS Animation

## 🐛 Bekannte Probleme

Keine bekannten Probleme. System läuft stabil.

## 📝 Changelog

**Version 2.0 (2025-11-18):**
- ✅ Komplett überarbeitete Flacker-Physik mit Harmonischen
- ✅ Inverse-Square-Law Implementation
- ✅ 10+ Lichtquellen-Presets mit eigenen Eigenschaften
- ✅ Dynamische Farbtemperatur
- ✅ Kontinuierliche Animation (30 FPS)
- ✅ Performance-Optimierungen (Frame-Skipping)
- ✅ Test-Demo erstellt

## 👨‍💻 Entwickler-Notizen

**Wichtig bei Änderungen:**
- `time_offset` muss kontinuierlich aktualisiert werden (in `animate_tiles()`)
- `render_lighting()` muss `time_offset` Parameter erhalten
- Bei neuen Lichttypen: `_setup_light_physics()` erweitern
- Flicker-Frequenzen sollten zwischen 1-20 Hz bleiben (sichtbar)

**Performance:**
- Rendering ist CPU-intensiv (PIL/Pillow)
- Frame-Skipping hilft (skip_frames=2 ohne Flackern)
- Cache für Fog-Texturen nutzen
- Große Maps (>50x50) können langsam werden

---

**Viel Spaß mit dem verbesserten Lichtsystem! 🔥✨**
