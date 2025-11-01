# Performance-Fix: Animation im Editor deaktiviert

## Problem
- Im Editor-Modus wurden alle animierten Tiles (Wasser, Bäume, etc.) kontinuierlich animiert
- Jedes Tile generierte alle 150ms eine neue Textur
- Bei vielen animierten Tiles → starkes Ruckeln
- Bei sehr vielen Tiles → "Fail to allocate bitmap" (Speicher-Overflow)

## Lösung
**Animation im Editor-Modus komplett deaktiviert!**

### Änderungen in `main.py`:

1. **`is_animating = False`** (statt True)
   - Animation ist standardmäßig aus im Editor

2. **`animation_frame = 0`** (konstant)
   - Alle Texturen verwenden Frame 0 (statisches Bild)

3. **`update_tile()` verwendet immer Frame 0**
   - Explizit `get_texture(terrain, size, 0)` statt `animation_frame`

4. **`start_animation()` und `animate_water()` deaktiviert**
   - Funktionen tun nichts mehr (`pass` bzw. `return`)

## Ergebnis
✅ **Kein Ruckeln** mehr beim Platzieren von Tiles
✅ **Kein "Fail to allocate bitmap"** mehr
✅ **Schneller Editor** - Texturen werden gecacht
✅ **Weniger CPU-Last** - keine 60 FPS-Neuberechnungen

## Wo ist Animation noch aktiv?
Animation läuft **nur im Projektor-Modus** (`projector_window.py`)!
- Dort ist es sinnvoll für die visuelle Präsentation
- Nur sichtbare Tiles werden animiert (nicht die ganze Map)

## Testen
1. Editor öffnen
2. Viele Water-Tiles platzieren
3. **Erwartet**: Kein Ruckeln, statische Texturen
4. Projektor öffnen
5. **Erwartet**: Water animiert (falls Projektor-Animation aktiviert)

---
*Datum: 17. Januar 2025*
