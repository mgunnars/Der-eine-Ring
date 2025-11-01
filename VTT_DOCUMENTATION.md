# Der Eine Ring - VTT System - Dokumentation

## 🎮 Vollständiges Virtual Tabletop System

### ✅ Implementierte Features

#### 1. **Webcam-Tracking System** (`webcam_tracker.py`)
- OpenCV-basierte Hand- und Figurenerkennung
- Echtzeit-Bewegungsverfolgung über dem Spieltisch
- Kalibrierung für Spieltisch-Ecken (perspektivische Transformation)
- Bewegungsvektoren und Position-Tracking
- Geglättete Position-Daten für stabile Erkennung

#### 2. **Fog-of-War System** (`fog_of_war.py`)
- Dynamisches Nebelsystem für verborgene Kartenbereiche
- Boolean-Array für revealed/hidden Status
- Kreisförmiges Aufdecken mit einstellbarer Sichtweite (1-10 Tiles)
- Manuelle Steuerung: Bereiche auf-/zudecken, alles zeigen/verbergen
- Halbtransparentes schwarzes Overlay für verborgene Bereiche

#### 3. **Gamemaster Control Panel** (`gm_controls.py`)
- **Webcam Tab**: Live-Vorschau, Start/Stop, Kalibrierung
- **Fog-of-War Tab**: Aktivierung, Sichtweite, manuelle Bereichs-Steuerung
- **Kamera Tab**: Zoom-Slider, Auto-Zoom Toggle, Kamera zurücksetzen
- **Einstellungen Tab**: Webcam-Auswahl, Tracking-Empfindlichkeit
- **Detail-Maps Tab**: Erstellen, Verwalten, Löschen von Detail-Karten

#### 4. **Dynamischer Kamera-Controller** (`camera_controller.py`)
- Automatischer Zoom auf relevante Spielbereiche
- Bounding-Box Berechnung um Spieler-Positionen
- Sanfte Zoom- und Pan-Transitions
- Tracking von aufgedeckten Tiles und Spieler-Aktivität
- Konfigurierbare Zoom-Grenzen (0.5x - 3.0x)

#### 5. **Detail-Maps System** (`detail_map_system.py`)
- Automatischer Wechsel zu Detail-Ansichten bei Dörfern/Gebäuden
- JSON-basierte Speicherung in `detail_maps/` Ordner
- Standard-Generatoren für Dorf- und Gebäude-Innenkarten
- Trigger-System für automatisches Laden
- Rechtsklick zum manuellen Wechsel zwischen Base/Detail

#### 6. **Integrierter Projektor** (`projector_window.py`)
- Vollbild-Modus für zweiten Monitor/Beamer (1920x1080)
- Integration aller Systeme: Webcam, Fog, Auto-Zoom, Detail-Maps
- Wasser-Animation (200ms Refresh)
- Dynamische Tile-Größen (8-64px basierend auf Kartengröße)
- Zentrierte Kartendarstellung ohne schwarze Ränder

### 🎯 Workflow

1. **Karte erstellen**: Im Editor Terrain malen und speichern
2. **Projektor starten**: Karte auf zweitem Monitor anzeigen
3. **GM-Panel öffnen**: Kontrollpanel für alle Funktionen
4. **Webcam aktivieren**: "Start Tracking" im Webcam-Tab
5. **Kalibrieren**: 4 Ecken des Spieltisches markieren
6. **Spielen**: 
   - Hand/Figuren bewegen → Fog lichtet sich automatisch
   - Auto-Zoom folgt Spieler-Aktivität
   - Detail-Maps laden automatisch bei Dörfern
   - Manuelle Fog-Steuerung für besondere Szenen

### 📁 Dateistruktur

```
Der-eine-Ring-main/
├── enhanced_main.py          # Hauptmenü mit VTT-Integration
├── main.py                   # Karten-Editor
├── projector_window.py       # Vollbild-Projektor mit allen Features
├── texture_manager.py        # Prozedurale Terrain-Texturen
├── map_system.py             # JSON Map-Verwaltung
├── webcam_tracker.py         # Webcam Hand-Tracking
├── fog_of_war.py            # Fog-of-War Logik
├── gm_controls.py           # Gamemaster Kontrollpanel
├── camera_controller.py     # Auto-Zoom & Kamera
├── detail_map_system.py     # Detail-Karten System
├── requirements.txt         # Dependencies
├── maps/                    # Gespeicherte Karten
└── detail_maps/             # Detail-Ansichten
```

### 🔧 Installation

```powershell
py -m pip install -r requirements.txt
```

**Dependencies:**
- Pillow >= 10.0.0
- opencv-python >= 4.8.0
- numpy >= 1.24.0

### 🚀 Start

```powershell
py enhanced_main.py
```

### ⌨️ Tastenkombinationen

**Projektor:**
- `ESC` - Beenden
- `F11` - Vollbild an/aus
- `Rechtsklick` - Detail-Ansicht Toggle
- `Mausrad` - Zoom
- `Linke Maustaste + Ziehen` - Karte verschieben

**Editor:**
- Terrain auswählen + Klicken/Ziehen zum Malen
- `💾` - Karte speichern
- `📂` - Karte laden
- `📍` - Koordinaten anzeigen

### 🎮 GM-Panel Features

**Webcam-Tracking:**
- Live-Vorschau der Kamera
- Status-Anzeige (Gestoppt/Läuft)
- Kalibrierungs-Tool
- Empfindlichkeits-Einstellung

**Fog-of-War:**
- Ein/Aus Toggle
- Sichtweite 1-10 Tiles
- Alles aufdecken/verbergen
- Bereichs-Auswahl (X1,Y1 bis X2,Y2)

**Kamera:**
- Zoom 0.5x - 3.0x
- Auto-Zoom auf Spieler-Bereiche
- Kamera zurücksetzen

**Detail-Maps:**
- Neue Detail-Maps erstellen (Dorf/Gebäude)
- Position angeben (X, Y)
- Liste aller Detail-Maps
- Löschen-Funktion

### 🌟 Besondere Features

1. **Intelligentes Tracking**: Webcam erkennt Handbewegungen UND Spielfiguren
2. **Perspektiv-Kalibrierung**: Spieltisch-Verzerrung wird ausgeglichen
3. **Smooth Transitions**: Alle Kamera-Bewegungen sind sanft animiert
4. **Performance-Optimiert**: 
   - Wasser-Animation nur für sichtbare Tiles
   - Begrenzte Tile-Größen (8-64px)
   - Referenz-Caching für Bilder
5. **Automatisierung**: Fog und Detail-Maps reagieren automatisch auf Spieler

### 🎨 Terrain-Typen

- `grass` - Grasland
- `water_h/water_v` - Wasser (horizontal/vertikal animiert)
- `mountain` - Berge
- `forest` - Wald
- `sand` - Sand/Strand
- `snow` - Schnee
- `road` - Straßen
- `village` - Dörfer (Trigger für Detail-Maps)
- `stone` - Stein
- `dirt` - Erde

### 📝 Hinweise für Gamemaster

1. **Webcam-Position**: Direkt über Spieltisch, möglichst zentral
2. **Beleuchtung**: Gleichmäßig, nicht zu dunkel
3. **Kalibrierung**: Wichtig für genaues Tracking!
4. **Fog-Strategie**: 
   - Start: Alles verborgen
   - Sichtweite 3-5 Tiles für Dungeon-Crawls
   - Größere Sichtweite (7-10) für Außenbereiche
5. **Detail-Maps**: Vorher erstellen für wichtige Orte
6. **Auto-Zoom**: Gut für fokussierte Szenen, deaktivieren für Übersicht

### 🐛 Troubleshooting

**Webcam startet nicht:**
- Webcam-Index im Einstellungen-Tab anpassen (0, 1, 2...)
- Andere Programme schließen, die Webcam nutzen

**Tracking ungenau:**
- Kalibrierung wiederholen
- Beleuchtung verbessern
- Empfindlichkeit anpassen (100-2000)

**Performance-Probleme:**
- Kartengröße reduzieren (max 50x50)
- Wasser-Tiles minimieren
- Auto-Zoom deaktivieren

**Fog zeigt nicht korrekt:**
- Projektor-Fenster neu laden
- "Alles verbergen" + manuell aufdecken

---

**Viel Spaß in Mittelerde! 🧙‍♂️🗡️🏔️**
