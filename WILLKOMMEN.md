# 🎉 Willkommen bei Der Eine Ring VTT!

## 🚀 Schnellstart (30 Sekunden)

### Windows:
```bash
START.bat
```

Das war's! Die App installiert automatisch alle Dependencies beim ersten Start.

---

## 📦 Was passiert beim ersten Start?

### Automatische Installation:
1. ✅ Prüft Python-Version
2. ✅ Installiert alle Python-Pakete (Pillow, NumPy, OpenCV, etc.)
3. ✅ Prüft Cairo SVG-Renderer
4. ✅ Führt System-Check durch
5. ✅ Startet die Anwendung

**Dauer:** 1-2 Minuten beim ersten Mal  
**Danach:** Sofortiger Start (Dependencies gecacht)

---

## 🎨 Cairo SVG-Renderer (Optional)

Beim ersten Start wirst du gefragt ob du Cairo installieren möchtest.

### Mit Cairo (EMPFOHLEN):
- ✅ Vektorkarten in voller Farbpracht
- ✅ Verlustfreies Zooming
- ✅ 5x schnelleres Rendering
- ✅ Perfekte Qualität

### Ohne Cairo:
- ⚠️ PIL-Fallback (funktioniert, aber nur PNGs werden gerendert)
- ⚠️ Vektoren erscheinen grau/schwarz
- ⚠️ Langsameres Rendering

**Installation:** Dauert 5 Minuten, wird beim Start angeboten.

---

## 📋 System-Anforderungen

### Minimum:
- **OS:** Windows 10/11, Linux, macOS
- **Python:** 3.10 oder neuer
- **RAM:** 4 GB
- **Speicher:** 500 MB

### Empfohlen:
- **OS:** Windows 11
- **Python:** 3.11+
- **RAM:** 8 GB
- **Speicher:** 1 GB
- **Display:** 1920×1080 oder größer
- **Cairo:** Installiert (für SVG-Vektoren)

---

## 🎮 Features

### Karten-System:
- 📍 PNG/JPG Import mit Auto-Tiling
- 🎨 SVG-Export mit echten Vektoren
- 🗺️ Grid-System (Square/Hex)
- 🔍 Zoom und Pan

### Fog-of-War:
- 🌫️ Dynamischer Nebel
- 👁️ Line-of-Sight
- 🎭 GM-Controls
- 💾 Speichern/Laden

### Projektor-Modus:
- 🖥️ Zweiter Monitor Support
- 🎨 High-Quality SVG-Rendering
- ⚡ Hardware-beschleunigt
- 🔄 Live-Updates

### Material-System:
- 🎨 9 vordefinierte Materialien (Gras, Wasser, Wald, etc.)
- 📦 Material-Bundles
- 🖼️ Custom Textures
- 🎭 Animated Textures

### Webcam-Tracking:
- 📷 Automatische Token-Erkennung
- 🎯 Farbbasiertes Tracking
- 🔄 Live-Positionierung
- ⚙️ Kalibrierung

---

## 📚 Dokumentation

- **Quick Start:** `QUICK_START.md`
- **VTT Dokumentation:** `VTT_DOCUMENTATION.md`
- **SVG-Vektoren:** `SVG_VECTOR_MAPS.md`
- **Cairo Setup:** `CAIRO_QUICKSTART.md`
- **Material-Bundles:** `MATERIAL_BUNDLES.md`
- **Fog-of-War:** `FOG_UPDATE.md`

---

## 🆘 Hilfe & Troubleshooting

### App startet nicht?
```bash
# Manuell Dependencies installieren:
py -m pip install -r requirements.txt

# Python-Version prüfen:
py --version
```

### Cairo-Probleme?
```bash
# Cairo-Installer ausführen:
INSTALL_CAIRO.bat

# Oder Dokumentation lesen:
CAIRO_QUICKSTART.md
```

### Webcam funktioniert nicht?
- Prüfe ob Webcam von anderer App benutzt wird
- Starte System neu
- Prüfe Berechtigungen (Windows Settings → Privacy → Camera)

---

## 🎯 Erste Schritte

### 1. App starten:
```bash
START.bat
```

### 2. Karte importieren:
- Klicke "PNG Import"
- Wähle deine Karten-PNG (oder JPG)
- Tiles werden automatisch extrahiert

### 3. Als SVG exportieren:
- Klicke "Als SVG exportieren"
- Wähle Qualität (high/medium/low)
- Warte auf Vektorisierung

### 4. Im Projektor anzeigen:
- Klicke "Projektor-Modus"
- Wähle deine SVG-Karte
- Bewege mit Maus, Zoome mit Mausrad

### 5. Fog-of-War aktivieren:
- Klicke "GM Controls"
- Male mit Linksklick um Nebel zu entfernen
- Male mit Rechtsklick um Nebel zu setzen

---

## 🎨 Beispiel-Workflow

```
1. START.bat ausführen
   ↓
2. PNG-Karte importieren (z.B. 5000×3000px)
   ↓
3. Warte auf Auto-Tiling (21×15 Tiles @ 256px)
   ↓
4. Als SVG exportieren (Vektorisierung läuft)
   ↓
5. Projektor-Modus öffnen
   ↓
6. SVG-Karte laden (mit Cairo: Farbig & schnell!)
   ↓
7. Fog-of-War aktivieren
   ↓
8. Spielen! 🎲
```

---

## 🔧 Erweiterte Einstellungen

### Performance:
- Tile-Größe: 256px (Standard), 128px (schnell), 512px (Qualität)
- SVG-Qualität: high (16 MB), medium (8 MB), low (4 MB)
- Cache: Automatisch aktiviert

### Cairo:
- DPI: 96 (Standard)
- Rendering: Hardware-beschleunigt
- Cache: 5 Zoom-Stufen

### Fog:
- Pinselgröße: 1-10 Tiles
- Farbe: Anpassbar
- Transparenz: 0-100%

---

## 🌟 Tipps & Tricks

1. **Große Karten:** Nutze "medium" oder "low" Qualität für schnelleren Export
2. **Cairo:** Unbedingt installieren für beste Qualität!
3. **Material-Bundles:** Werden automatisch erstellt und gecacht
4. **Fog speichern:** Fog-Status wird in `.fog` Dateien gespeichert
5. **Zoom-Cache:** Arbeitet automatisch, speichert letzte 5 Zoom-Stufen

---

## 📞 Support

- **GitHub Issues:** https://github.com/mgunnars/Der-eine-Ring
- **Dokumentation:** Siehe MD-Dateien im Projekt-Ordner
- **Logs:** Prüfe Terminal-Ausgabe bei Problemen

---

## 🎉 Viel Spaß beim Spielen!

**Der Eine Ring VTT** - Professional Virtual Tabletop System  
Version 2.0 - SVG Vector Maps Edition

---

*"Not all those who wander are lost."* - J.R.R. Tolkien
