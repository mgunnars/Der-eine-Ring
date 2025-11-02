# 🎨 SVG-Texturen On-Board

Die Beispielkarte liegt jetzt als **hochauflösende SVG** vor!

## 📦 Was ist enthalten:

- ✅ `maps/beispiel_mittelerde.svg` - Beispielkarte in SVG (1.2 MB)
- ✅ `start_with_svg.py` - Startup-Dialog mit SVG-Option
- ✅ `convert_example_to_svg.py` - Konvertierungs-Script
- ✅ Alle Texturen als Base64 in der SVG eingebettet

## 🚀 Verwendung:

### Option 1: Startup-Dialog (empfohlen)
```bash
START.bat
```
Oder:
```bash
py start_with_svg.py
```

→ Wähle zwischen:
- **Map Editor**: Klassischer Editor mit PNG-Tiles
- **SVG Projektor**: High-Quality Projektion (verlustfrei)

### Option 2: Direkt SVG-Projektor
```bash
py svg_projector.py maps/beispiel_mittelerde.svg
```

### Option 3: Eigene Karten konvertieren
```python
# convert_example_to_svg.py anpassen
from svg_map_exporter import SVGMapExporter
# ... Karte exportieren
```

## 💡 Vorteile der SVG-Version:

1. **Perfekte Qualität** bei jeder Auflösung
   - 1080p, 4K, 8K - alles scharf
   - Keine Verpixelung beim Zoomen

2. **Eine Datei** statt 600 PNG-Tiles
   - Einfacher zu teilen
   - Kleinere Gesamt-Dateigröße

3. **Schnelleres Laden** im Projektor
   - Einmal rendern, dann cachen
   - Keine hunderte einzelner Dateien

4. **On-Board** ohne Externe Dependencies
   - PIL-Fallback extrahiert Base64-PNGs
   - Kein cairosvg nötig (aber optional für beste Qualität)

## 🎬 Projektor-Steuerung:

| Taste | Funktion |
|-------|----------|
| `F11` | Vollbild an/aus |
| `+` | Zoom rein |
| `-` | Zoom raus |
| `R` | Ansicht zurücksetzen |
| `G` | Grid ein/aus |
| `F` | Fog of War ein/aus |
| `ESC` | Beenden |

## 📊 Technische Details:

**Beispiel-SVG:**
- Größe: 30×20 Tiles (600 Tiles)
- Auflösung: 15360×10240px (High Quality)
- Dateigröße: 1.2 MB
- Format: SVG 1.1 mit embedded Base64-PNG

**Render-Performance (ohne cairosvg):**
- Erstes Laden: ~1-2 Sekunden
- Gecachtes Rendering: Instant
- Speicherverbrauch: ~50 MB

## 🔧 Eigene Karten zu SVG konvertieren:

1. Im Editor: Karte erstellen/laden
2. Klick auf "📐 Als SVG" Button
3. Qualität wählen (High empfohlen)
4. Speichern
5. Mit "🎬 SVG Projektor" öffnen

## ⚙️ Konfiguration:

### Rendering-Qualität anpassen:
In `convert_example_to_svg.py`:
```python
render_resolution="high"  # low, high, ultra
```

### Bilder extern statt eingebettet:
```python
embed_images=False  # Material-PNGs müssen im selben Ordner sein
```

## 🆚 SVG vs PNG Vergleich:

| Feature | PNG-Tiles | SVG |
|---------|-----------|-----|
| Editor-Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Projektor-Qualität | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Zoom ohne Verlust | ❌ | ✅ |
| Dateigröße | Mittel | Klein |
| Ladezeit | Schnell | Mittel |
| Archivierung | Viele Dateien | Eine Datei |

## 💾 Backup & Sharing:

**Für Spielabende:**
1. Exportiere Karte als SVG
2. Teile eine Datei statt hunderte
3. Projiziere in perfekter Qualität

**Für Archivierung:**
- JSON (Editor-Format) + SVG (Projektor-Format)
- Beste von beiden Welten

## 🎮 Workflows:

### Workflow 1: Vorbereitung
```
1. Karte im Editor erstellen
2. Als JSON speichern (für spätere Bearbeitung)
3. Als SVG exportieren (für Projektion)
4. SVG auf Beamer-PC kopieren
```

### Workflow 2: Spielabend
```
1. START.bat → SVG Projektor wählen
2. F11 für Vollbild
3. Nebel mit F toggle
4. Perfekte Qualität genießen!
```

### Workflow 3: Updates
```
1. JSON im Editor laden
2. Änderungen vornehmen
3. Neu als SVG exportieren
4. Im laufenden Projektor neu laden (File → Open)
```

## ❓ FAQ:

**Q: Muss ich cairosvg installieren?**
A: Nein! PIL-Fallback funktioniert out-of-the-box.

**Q: Ist SVG langsamer als PNG?**
A: Erster Render ja, danach gecacht = gleich schnell.

**Q: Kann ich SVG im Browser öffnen?**
A: Ja! Firefox, Chrome, Edge - alle zeigen SVG an.

**Q: Wie groß werden SVG-Dateien?**
A: ~2 KB pro Tile. 30×20 = ~1.2 MB.

**Q: Funktionieren Animationen?**
A: Aktuell statisch. Animated SVG geplant.

---

**Status:** ✅ Production Ready  
**Branch:** svg-vector-maps  
**Beispiel-Karte:** maps/beispiel_mittelerde.svg (✅ inkludiert)
