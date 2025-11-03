# Der Eine Ring - Professional Virtual Tabletop

Ein professioneller Kartenprojektionssystem für Tabletop-Spiele mit **SVG-Vektor-Support** und hochwertigen Texturen.

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![Cairo](https://img.shields.io/badge/cairo-optional-orange)

## 🚀 Schnellstart

**Windows (EMPFOHLEN):**
```bash
START.bat
```

Das war's! Beim ersten Start werden automatisch alle Dependencies installiert.

---

## ✨ Features

### 🎨 Karten-System
- **PNG/JPG Import** - Automatisches Tiling großer Karten
- **SVG-Export** - Echte Vektorgrafiken mit verlustfreier Qualität
- **Material-System** - 9 vordefinierte + unbegrenzt custom Materials
- **Grid-System** - Square oder Hex-Grid

### 🌫️ Fog-of-War
- **Dynamischer Nebel** - Male Sichtbereiche für Spieler
- **Line-of-Sight** - Automatische Sichtlinien-Berechnung
- **GM-Controls** - Vollständige Kontrolle über Sichtbarkeit
- **Persistent** - Fog-Status wird gespeichert

### 📺 Projektor-Modus
- **High-Quality Rendering** - CairoSVG für perfekte Vektoren
- **Hardware-beschleunigt** - Smooth Zoom & Pan
- **Multi-Monitor Support** - Fullscreen auf zweitem Display
- **Live-Updates** - Änderungen erscheinen sofort

### 🎭 Material-System
- **Vordefiniert:** Gras, Wasser, Wald, Berg, Sand, Schnee, Stein, Erde, Straße
- **Custom Textures:** Importiere eigene PNG/JPG
- **Material-Bundles:** Automatisches Caching für Performance
- **Animiert:** Wasser-Animation Support

### 📷 Webcam-Tracking (Experimental)
- **Token-Erkennung** - Farbbasiertes Tracking
- **Live-Position** - Tokens bewegen sich auf der Karte
- **Kalibrierung** - Einfaches Setup

---

## 📦 Installation

### Automatisch (Windows):
```bash
START.bat
```
Installiert automatisch beim ersten Start:
- ✅ Python-Pakete (Pillow, NumPy, OpenCV, etc.)
- ✅ Optional: Cairo für High-Quality SVG
- ✅ System-Check und Diagnostik

### Manuell:
```bash
# Python 3.10+ erforderlich
py --version

# Dependencies installieren
py -m pip install -r requirements.txt

# App starten
py enhanced_main.py
```

### Cairo (EMPFOHLEN für SVG):
```bash
# Automatischer Installer:
INSTALL_CAIRO.bat

# Oder siehe Dokumentation:
CAIRO_QUICKSTART.md
```

---

## 🎮 Verwendung

### 1️⃣ Karte importieren
- Klicke **"PNG Import"**
- Wähle deine Karten-Datei (PNG/JPG)
- Tiles werden automatisch extrahiert
- Material-Bundle wird erstellt

### 2️⃣ Als SVG exportieren
- Klicke **"Als SVG exportieren"**
- Wähle Qualität (high/medium/low)
- Warte auf Vektorisierung
- SVG wird in `maps/` gespeichert

### 3️⃣ Projektor-Modus
- Klicke **"Projektor-Modus"**
- Wähle deine SVG-Karte
- **Steuerung:**
  - Maus ziehen = Karte bewegen
  - Mausrad = Zoom
  - ESC = Beenden

### 4️⃣ Fog-of-War
- Klicke **"GM Controls"**
- **Linksklick** = Nebel entfernen
- **Rechtsklick** = Nebel setzen
- **Mausrad** = Pinselgröße ändern

---

## 🎨 Verfügbare Materialien

| Material | Beschreibung | Typ |
|---------|--------------|-----|
| 🌿 Gras | Grüne Wiesen | Vektor |
| 💧 Wasser | Flüsse, Seen (animiert) | Vektor |
| 🌲 Wald | Dichter Wald | Vektor |
| 🏔️ Berg | Felsige Berge | Vektor |
| 🏖️ Sand | Strände, Wüsten | Vektor |
| ❄️ Schnee | Schneefelder | Vektor |
| 🪨 Stein | Steinpflaster | Vektor |
| 🟫 Erde | Erdböden | Vektor |
| 🛣️ Straße | Wege, Pfade | Vektor |
| 🖼️ Custom | Eigene PNG/JPG | Import |

---

## 📚 Dokumentation

- **[Willkommen](WILLKOMMEN.md)** - Ausführliche Einführung
- **[Quick Start](QUICK_START.md)** - 5-Minuten-Anleitung
- **[VTT Dokumentation](VTT_DOCUMENTATION.md)** - Vollständiges Handbuch
- **[SVG-Vektoren](SVG_VECTOR_MAPS.md)** - Vektor-System erklärt
- **[Cairo Setup](CAIRO_QUICKSTART.md)** - High-Quality Rendering
- **[Material-Bundles](MATERIAL_BUNDLES.md)** - Material-System
- **[Fog-of-War](FOG_UPDATE.md)** - Nebel-System

---

## 🖥️ Zwei-Monitor-Setup

Für die beste Erfahrung mit einem Projektor oder zweiten Monitor:

1. Verbinde deinen zweiten Monitor/Beamer
2. Windows-Einstellungen: **"Anzeige erweitern"**
3. Starte den Projektor-Modus
4. Ziehe das Fenster auf den zweiten Monitor
5. Drücke F11 für Vollbild

---

## 📁 Projektstruktur

```
Der-eine-Ring-main/
├── enhanced_main.py          # Hauptanwendung
├── map_editor.py             # Map Editor
├── projector_window.py       # Projektor-Fenster
├── svg_projector.py          # SVG-Renderer (Cairo/PIL)
├── svg_map_exporter.py       # SVG-Export-System
├── svg_texture_vectorizer.py # PNG→SVG Vektorisierung
├── texture_manager.py        # Textur-Generierung
├── material_manager.py       # Material-System
├── material_bundle_manager.py# Bundle-System
├── fog_of_war.py             # Fog-System
├── map_system.py             # Karten-Verwaltung
├── maps/                     # Gespeicherte Karten
├── imported_maps/            # Importierte PNG-Tiles
├── material_bundles/         # Material-Caches
├── requirements.txt          # Python-Dependencies
├── START.bat                 # Auto-Setup & Start
├── INSTALL_CAIRO.bat         # Cairo-Installer
└── *.md                      # Dokumentation
```

---

## 🛠️ Technische Details

### Core:
- **GUI Framework:** Tkinter
- **Bildverarbeitung:** PIL/Pillow 10.x
- **Numerik:** NumPy 1.24+
- **Webcam:** OpenCV 4.8+

### SVG-System:
- **Vektorisierung:** Color Quantization + Rectangular Regions
- **Rendering:** CairoSVG (empfohlen) oder PIL-Fallback
- **Format:** SVG 1.1 mit Pattern-based Textures
- **Caching:** Multi-Level Render-Cache (5 Zoom-Stufen)

### Performance:
- **Tile-Größe:** 97-256px (dynamisch)
- **Material-Bundles:** JSON-basiertes Caching
- **Vektor-Qualität:** 8-16 Farben, 2-4px Grid
- **File-Size:** 8-16 MB für 315-Tile-Map

---

## 🐛 Fehlerbehebung

### App startet nicht
```bash
# Manuell Dependencies installieren:
py -m pip install -r requirements.txt

# Python-Version prüfen (min. 3.10):
py --version
```

### Cairo-Fehler: "no library called 'cairo-2' was found"
```bash
# Cairo-Installer ausführen:
INSTALL_CAIRO.bat

# Oder GTK3 Runtime manuell installieren:
# https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
```

### SVG zeigt nur graue/schwarze Flächen
**Ursache:** CairoSVG fehlt, PIL kann nur PNGs rendern.

**Lösung:** Cairo installieren (siehe oben) oder App nutzt automatisch PIL-Fallback.

### Webcam funktioniert nicht
- Prüfe ob Webcam von anderer App benutzt wird
- Starte System neu
- Prüfe Berechtigungen (Windows Settings → Privacy → Camera)

### "ModuleNotFoundError"
```bash
# Alle Pakete neu installieren:
py -m pip install --upgrade -r requirements.txt
```

---

## 📊 System-Anforderungen

### Minimum:
- **OS:** Windows 10/11, Linux, macOS
- **Python:** 3.10 oder neuer
- **RAM:** 4 GB
- **Speicher:** 500 MB
- **Display:** 1280×720

### Empfohlen:
- **OS:** Windows 11
- **Python:** 3.11+
- **RAM:** 8 GB
- **Speicher:** 1 GB
- **Display:** 1920×1080 oder größer
- **Cairo:** Installiert (für SVG-Vektoren)
- **Webcam:** Optional für Token-Tracking

---

## 🎯 Workflow-Beispiel

```
1. START.bat ausführen (auto-install beim ersten Mal)
   ↓
2. PNG-Karte importieren (z.B. 5000×3000px Taverne)
   ↓
3. Warte auf Auto-Tiling (21×15 Tiles @ 256px)
   ↓
4. Als SVG exportieren (Vektorisierung: 8-12 Farben)
   ↓
5. Projektor-Modus öffnen
   ↓
6. SVG-Karte laden (Cairo rendert in Farbe!)
   ↓
7. Fog-of-War aktivieren (GM-Controls)
   ↓
8. Spielen! 🎲
```

---

## 🌟 Tipps & Tricks

1. **Große Karten:** Nutze "medium" Qualität für schnelleren Export (8 MB statt 16 MB)
2. **Cairo:** Unbedingt installieren für farbige Vektoren!
3. **Material-Bundles:** Werden automatisch erstellt und gecacht
4. **Fog speichern:** Fog-Status wird in `.fog` Dateien neben der Map gespeichert
5. **Zoom-Cache:** Arbeitet automatisch, speichert letzte 5 Zoom-Stufen

---

## 🆕 Was ist neu in Version 2.0?

- ✅ **SVG-Vektor-Export** - Echte Vektorgrafiken statt PNG-Embedding
- ✅ **PNG-Vektorisierung** - Importierte Karten werden zu Vektoren
- ✅ **CairoSVG-Integration** - High-Quality Rendering
- ✅ **Material-Bundle-System** - Automatisches Caching
- ✅ **Verbesserte Fog-of-War** - Mit Water-Detection
- ✅ **Auto-Setup** - Dependencies beim Start installieren
- ✅ **Multi-Level-Cache** - 5 Zoom-Stufen für smooth Performance
- ✅ **Bessere Dokumentation** - Ausführliche Guides

---

## 📝 Lizenz

Für persönliche und nicht-kommerzielle Nutzung.

---

## 🤝 Beitragen

Verbesserungsvorschläge und Bug-Reports sind willkommen!

**GitHub:** https://github.com/mgunnars/Der-eine-Ring

---

## 📞 Support

- **Issues:** GitHub Issues
- **Dokumentation:** Siehe `*.md` Dateien
- **Logs:** Terminal-Ausgabe prüfen bei Problemen

---

**Der Eine Ring VTT** - Professional Virtual Tabletop System  
Version 2.0 - SVG Vector Maps Edition

*"Not all those who wander are lost."* - J.R.R. Tolkien

---

**Viel Spaß beim Spielen! 🗺️⚔️🧙‍♂️**
