# 🚀 Verbessertes Lichtsystem - Schnellstart

## Sofort loslegen

### 1. Demo starten
```bash
python test_improved_lighting.py
```

Die Demo zeigt alle 10+ Lichtquellen-Typen mit realistischem Flackern in Echtzeit.

### 2. Im VTT-Editor verwenden

**Lichtquelle hinzufügen:**
1. Öffne den Map-Editor
2. Wähle "Lighting" Tool
3. Klicke auf die Karte
4. Wähle Lichttyp aus Dropdown:
   - 🔥 Fackel/Torch (starkes Flackern)
   - 🔥 Feuer/Fire (sehr intensiv)
   - 🕯️ Kerze/Candle (sanft)
   - ✨ Magie/Magic (pulsierend)
   - 🌙 Mondlicht/Moonlight (konstant)
   - und mehr...

**Das war's! Die Animation läuft automatisch.**

## Unterschiede zum alten System

### Was ist neu?

✅ **Flackern ist jetzt sichtbar!**
- Vorher: 0.8 Hz (fast unsichtbar)
- Jetzt: 15 Hz bei Feuer (deutlich sichtbar)

✅ **Physikalisch korrekte Lichtverteilung**
- Vorher: Linearer Radius
- Jetzt: Inverse-Square-Law (wie echtes Licht)

✅ **Unterschiedliche Intensitäten**
- Feuer ist heller als Kerzen
- Mondlicht ist sehr sanft
- Fackeln sind intensiv

✅ **Realistische Farben**
- Feuer: Weiß (Kern) → Gelb → Orange → Rot (Rand)
- Kerzen: Warmes Gelb
- Magie: Farbwechsel

## Lichtquellen-Typen auf einen Blick

| Typ | Flackern | Radius | Farbe | Verwendung |
|-----|----------|--------|-------|------------|
| 🔥 **Fackel** | Stark | Mittel | Orange | Dungeon, Korridor |
| 🔥 **Feuer** | Sehr stark | Groß | Orange-Rot | Lagerfeuer, Kampf |
| 🕯️ **Kerze** | Sanft | Klein | Gelb | Taverne, Raum |
| 🏮 **Laterne** | Mittel | Mittel | Gelb | Tragen, Outdoor |
| ✨ **Magie** | Pulsierend | Groß | Lila | Zauber, Artefakte |
| 💎 **Kristall** | Sanft | Mittel | Blau | Höhle, Magie |
| 🔥 **Feuerschale** | Stark | Groß | Orange | Tempel, Halle |
| 🪟 **Fenster** | Minimal | Groß | Blau-Weiß | Tag, Indoor |
| 🌙 **Mondlicht** | Keine | Sehr groß | Blau-Weiß | Nacht, Outdoor |

## Tipps für beste Ergebnisse

### Kombination von Lichtquellen

**Taverne-Szene:**
```
- 2-3 Kerzen (candle) auf Tischen
- 1 Feuer (fire) im Kamin
- 1-2 Laternen (lantern) an Wänden
```

**Dungeon:**
```
- Fackeln (torch) an Wänden (Abstand: 5-7 Tiles)
- Kerze (candle) beim Spieler (tragbar)
```

**Magie-Ritual:**
```
- 4 Kerzen (candle) in Kreis
- 1 Magie-Licht (magic) in Mitte (pulsierend)
```

**Outdoor Nacht:**
```
- 1 Mondlicht (moonlight) zentral (großer Radius)
- Lagerfeuer (campfire) beim Camp
```

### Performance-Tipps

1. **Große Karten (>50x50 Tiles):**
   - Max 10-15 Lichtquellen
   - Nutze größere Radien statt vieler kleiner Lichter

2. **Viele Lichtquellen:**
   - Frame-Skipping aktiviert sich automatisch
   - Bei Lag: Weniger flackernde Lichter nutzen

3. **Optimale Radien:**
   - Kerze: 3-4 Tiles
   - Fackel: 6-7 Tiles
   - Feuer: 8-10 Tiles
   - Mondlicht: 12-15 Tiles

## Häufige Fragen

**Q: Warum flackert meine Fackel nicht?**
A: Stelle sicher, dass `flicker=True` gesetzt ist und der Lichttyp "torch" oder "fire" ist.

**Q: Kann ich eigene Farben verwenden?**
A: Ja! Setze einfach `color=(R, G, B)` beim Erstellen der Lichtquelle.

**Q: Wie mache ich Licht heller?**
A: Erhöhe `intensity` (Standard: 1.0, Maximum: 1.5 empfohlen).

**Q: Performance-Probleme?**
A: Reduziere Anzahl der Lichtquellen oder nutze weniger flackernde Lichter.

**Q: Licht zu groß/klein?**
A: Ändere `radius` Parameter (3-15 Tiles empfohlen).

## Code-Beispiele

### Einfache Fackel
```python
from lighting_system import LightSource, LIGHT_PRESETS

light = LightSource(x=10, y=15, **LIGHT_PRESETS["torch"])
lighting_engine.add_light(light)
```

### Eigene Farbe
```python
light = LightSource(
    x=10, y=15,
    radius=8,
    color=(100, 255, 100),  # Grün!
    intensity=1.0,
    flicker=True,
    light_type="magic"
)
```

### Licht ohne Flackern
```python
light = LightSource(
    x=10, y=15,
    radius=10,
    color=(255, 255, 255),  # Weiß
    intensity=0.8,
    flicker=False,  # Konstant
    light_type="window"
)
```

## Probleme?

Siehe **IMPROVED_LIGHTING_SYSTEM.md** für Details.

---

**Viel Erfolg beim Beleuchten deiner Dungeons! 🔦✨**
