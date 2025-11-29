# Der Eine Ring - Interaktiver Tabletop-Kartenprojektor

Ein professioneller Kartenprojektionssystem für Herr-der-Ringe-Tabletop-Spiele mit hochwertigen Texturen.

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)

## ✨ Features

### 🚀 GPU Acceleration
**Neu in dieser Version:** Vollständige GPU-Beschleunigung für maximale Performance!

- **AMD GPUs:** OpenCL-Unterstützung für Radeon-Grafikkarten
- **NVIDIA GPUs:** CUDA-Unterstützung (zukünftig)
- **Fallback:** CPU-Rendering wenn GPU nicht verfügbar
- **10-50x schnelleres Lighting** bei mehreren Lichtquellen
- **Hardware-beschleunigte Filter** für flüssigeres Gameplay

### 🎨 Professioneller Karten-Editor
- **Drawing Tools** wie Foundry VTT & Dynamic Dungeons:
  - 🖌️ Pinsel mit variabler Größe (1-15 Tiles)
  - 🪣 Füllen-Tool (Flood Fill)
  - 💧 Pipette (Material-Picker)
  - 🧹 Radierer mit Pinselgröße
  - ⬜ Rechteck-Tool für Gebäude
  - ⭕ Kreis-Tool für Plätze
  - 📏 Linien-Tool für Straßen
  - ✂️ Auswahl-Tool (in Entwicklung)
- **Advanced Features**:
  - ↔️ Symmetrie-Modus (vertikal/horizontal)
  - 🔄 Undo/Redo (bis zu 50 Schritte)
  - ⌨️ Tastatur-Shortcuts (B/F/I/E/R/C/L/S)
  - 🔍 Zoom & Pan während der Bearbeitung
- **Material-System**:
  - 📦 Bundle-Manager für organisierte Material-Bibliothek
  - 🎨 Custom Materials importieren
  - 🖼️ Hochwertige prozedurale Texturen

### 📺 Projektor-System
- 📺 **Projektor-Modus** - Vollbild-Anzeige für zweiten Monitor/Beamer
- 🌫️ **Fog-of-War** - Dynamisches Aufdecken von Bereichen
- 🎥 **Kamera-Steuerung** - Zoom & Pan im Projektor
- 🗺️ **SVG-Support** - Vektor-basierte Maps für höchste Qualität
- 🎮 **GM-Controls** - Separates Kontrollpanel für Spielleiter

### 🗺️ Map-System
- 💾 **Speichern/Laden** - Karten als JSON
- 📤 **SVG-Export** - Vektorbasierte Karten exportieren
- 📥 **PNG-Import** - Bestehende Maps importieren
- 🏘️ **Detail-Maps** - Automatischer Wechsel bei Dörfern/Gebäuden
- 🗺️ **Multi-Terrain** - Gras, Wasser, Wald, Berg, Sand, Schnee, Dorf, etc.

📖 **Neue Guides**: 
- [Professional Drawing Tools Guide](EDITOR_TOOLS_GUIDE.md)
- [Quick Start für Tools](EDITOR_QUICKSTART.md)

## � Installation

### Voraussetzungen
- Python 3.8 oder höher
- pip (Python Package Manager)

### Schritt 1: Dependencies installieren

```bash
pip install -r requirements.txt
```

### Schritt 2: Anwendung starten

**Windows:**
```bash
START.bat
```

**Oder manuell:**
```bash
python enhanced_main.py
```

## 🎮 Verwendung

### 1️⃣ Karten-Editor
- Klicke auf **"🎨 Karten-Editor"** im Hauptmenü
- Wähle ein Terrain aus der Toolbar (Gras, Wasser, Berg, etc.)
- Klicke oder ziehe auf der Karte zum Zeichnen
- Speichere deine Karte mit **"💾 Speichern"**

### 2️⃣ Projektor-Modus
- Erstelle oder lade eine Karte
- Klicke auf **"📺 Projektor-Modus"**
- Das Fenster öffnet sich im Vollbild
- **Steuerung:**
  - Maus ziehen = Karte bewegen
  - Mausrad = Zoom
  - ESC = Beenden
  - F11 = Vollbild an/aus

### 3️⃣ Karten verwalten
- **📁 Karte laden** - Bestehende Karte öffnen
- **📋 Karten-Liste** - Alle gespeicherten Karten anzeigen
- Karten werden im `maps/` Ordner gespeichert

## 🎨 Verfügbare Terrains

| Terrain | Icon | Beschreibung |
|---------|------|--------------|
| Gras | 🌿 | Grüne Wiesen und Felder |
| Wasser | 💧 | Flüsse, Seen, Meer |
| Berg | 🏔️ | Felsige Berge |
| Wald | 🌲 | Dichter Wald |
| Sand | 🏖️ | Strände und Wüsten |
| Schnee | ❄️ | Schneebedeckte Gebiete |
| Dorf | 🏘️ | Siedlungen und Gebäude |

## 🖥️ Zwei-Monitor-Setup

Für die beste Erfahrung mit einem Projektor oder zweiten Monitor:

1. Verbinde deinen zweiten Monitor/Beamer
2. Windows-Einstellungen: **"Anzeige duplizieren"** oder **"Anzeige erweitern"**
3. Starte den Projektor-Modus
4. Ziehe das Fenster auf den zweiten Monitor
5. Drücke F11 für Vollbild

## 📁 Projektstruktur

```
Der-eine-Ring-main/
├── enhanced_main.py          # Hauptanwendung
├── main.py                   # Map Editor
├── projector_window.py       # Projektor-Fenster
├── texture_manager.py        # Textur-Generierung
├── map_system.py             # Karten-Verwaltung
├── maps/                     # Gespeicherte Karten
├── requirements.txt          # Python-Dependencies
├── START.bat                 # Windows-Starter
└── README.md                 # Diese Datei
```

## 🛠️ Technische Details

- **GUI Framework:** Tkinter
- **Bildverarbeitung:** PIL/Pillow
- **Texturen:** Prozedural generiert mit PIL
- **Kartenformat:** JSON

## 🐛 Fehlerbehebung

### "ModuleNotFoundError: No module named 'PIL'"
```bash
pip install Pillow
```

### Editor-Fenster bleibt weiß
- Überprüfe, ob alle Dependencies installiert sind
- Starte die Anwendung neu

### Projektor zeigt nichts an
- Lade zuerst eine Karte im Editor oder über "Karte laden"
- Bei erster Nutzung wird eine Beispielkarte angezeigt

## 📝 Lizenz

Für persönliche und nicht-kommerzielle Nutzung.

## 🤝 Beitragen

Verbesserungsvorschläge und Bug-Reports sind willkommen!

---

**Viel Spaß beim Spielen! 🗺️⚔️🧙‍♂️**
