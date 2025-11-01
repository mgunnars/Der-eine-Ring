# Der Eine Ring - Interaktiver Tabletop-Kartenprojektor

<<<<<<< HEAD
Ein interaktives Kartenprojektionssystem für Herr-der-Ringe-Tabletop-Spiele mit handgezeichneten Aquarell-Texturen.

## Features

- 🎨 Handgezeichnete Aquarell-Texturen
- 🌊 Animierte Gewässer mit Fließeffekten
- 🏰 Automatischer Wechsel zwischen Weltkarte und Innenräumen
- 🎭 Split-View für geteilte Gruppen
- 📹 Webcam-Integration für Bewegungserkennung
- 🗺️ Vorgefertigte Mittelerde-Karte

## Installation

```bash
# Repository klonen
git clone https://github.com/mgunnars/Der-eine-Ring.git
cd Der-eine-Ring

# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python enhanced_main.py
```

## Systemanforderungen

- Python 3.8+
- Webcam (optional, für Bewegungserkennung)
- Beamer/zweiter Bildschirm (empfohlen für Projektion)

## Verwendung

1. **Karteneditor**: Erstelle deine eigene Mittelerde-Karte
2. **Projektionsmodus**: Projiziere die Karte auf den Spieltisch
3. **Orte betreten**: Spielfiguren wechseln automatisch zu Innenansichten
4. **Nebel des Krieges**: Verstecke Bereiche vor Spielern

## Lizenz

Für persönliche und nicht-kommerzielle Nutzung
=======
Ein professioneller Kartenprojektionssystem für Herr-der-Ringe-Tabletop-Spiele mit hochwertigen Texturen.

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)

## ✨ Features

- 🎨 **Karteneditor** - Erstelle eigene Karten mit verschiedenen Terrains
- 📺 **Projektor-Modus** - Vollbild-Anzeige für zweiten Monitor/Beamer
- 🖼️ **Hochwertige Texturen** - Prozedural generierte Texturen für alle Terrains
- 💾 **Speichern/Laden** - Karten als JSON speichern und wiederverwenden
- 🔍 **Zoom & Pan** - Kamera-Steuerung im Projektor-Modus
- 🗺️ **Multi-Terrain** - Gras, Wasser, Wald, Berg, Sand, Schnee, Dorf, etc.

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
>>>>>>> 1b8b352 (Initial commit: Der Eine Ring VTT System)
