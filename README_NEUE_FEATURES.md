# Der Eine Ring - VTT System
## Professionelles Virtual Tabletop mit erweiterten Rendering-Features

---

## 🎨 NEUE FEATURES - Professionelles Rendering-System

### ✨ Komplett überarbeitetes Rendering
- **Handgezeichnete Texturen**: Alle Terrain-Typen mit professionellem, organischem Look
- **Erweiterte Animationen**: Wasser mit Welleneffekten, Wind in Wäldern, funkelnder Schnee
- **Hochwertige Details**: Schatten, Highlights, Lichtreflexionen für mehr Tiefe

### 🎨 Material-Editor
Erstelle und bearbeite eigene Texturen direkt in der Anwendung!

**Features:**
- 🖌️ **Pinsel-Werkzeug**: Zeichne Pixel für Pixel mit einstellbarer Größe
- 🧹 **Radierer**: Entferne ungewollte Bereiche
- 💧 **Füll-Werkzeug**: Flächen schnell einfärben
- 💉 **Pipette**: Farben aus der Textur aufnehmen
- ↶↷ **Undo/Redo**: Bis zu 50 Schritte rückgängig machen
- 🎨 **Farbwähler**: Unbegrenzte Farbauswahl
- 📤📂 **Import/Export**: PNG, JPG, BMP Bilder importieren und exportieren

**So funktioniert's:**
1. Material-Manager öffnen (Button im Editor)
2. "Neues Material" oder bestehendes Material bearbeiten
3. Im Editor zeichnen und gestalten
4. Material speichern - erscheint automatisch in der Leiste!

### 📦 Material-Management-System

**Ein-/ausklappbare Material-Leiste:**
- ▼▶ **Toggle-Button**: Leiste ein- und ausklappen für mehr Platz
- 🔤 **A-Z Sortierung**: Alle Materialien alphabetisch sortiert
- 📜 **Scrollbar**: Horizontale Scrollleiste für viele Materialien
- 🖼️ **Live-Vorschau**: Jedes Material mit Preview-Bild
- 🎬 **Animations-Indikator**: Zeigt animierte Materialien an
- ➕ **Schnell-Buttons**: Neu, Bearbeiten, Aktualisieren direkt in der Leiste

**Material-Manager Fenster:**
- Übersichtliche Liste aller Materialien (Basis + Custom)
- Details zu jedem Material (Name, Typ, Animation, etc.)
- Erstellen, Bearbeiten, Löschen von Custom-Materialien
- Export-Funktion für einzelne Texturen
- Basis-Materialien können kopiert und angepasst werden

### 📥 Textur-Import
Importiere eigene Bilder als Materialien!

**Unterstützte Formate:**
- PNG (empfohlen für Transparenz)
- JPG/JPEG
- BMP
- GIF

**So funktioniert's:**
1. Material auswählen oder neu erstellen
2. "Importieren" Button im Editor klicken
3. Bild auswählen
4. Automatische Anpassung auf optimale Größe
5. Sofort einsatzbereit in der Map!

### 🎭 Basis-Materialien

**10 professionell gestaltete Terrain-Typen:**
- 🌿 **Gras**: Saftiges Grün mit organischer Struktur
- 💧 **Wasser**: Animiert mit Wellen und Glanzlichtern
- 🏔️ **Berg**: Realistische Felsstruktur mit Rissen
- 🌲 **Wald**: Baumkronen von oben, animiert (Wind)
- 🏖️ **Sand**: Detaillierte Körnung und Struktur
- ❄️ **Schnee**: Funkelnde Kristalle (animiert)
- 🛤️ **Straße**: Kopfsteinpflaster mit Details
- 🏘️ **Dorf**: Gebäude-Draufsicht mit Dach und Tür
- 🪨 **Stein**: Steinplatten-Muster
- 🟫 **Erde**: Erdiger Boden mit Steinen

---

## 🚀 Schnellstart

### Installation
```bash
pip install -r requirements.txt
```

### Starten
```bash
python enhanced_main.py
```

---

## 📖 Verwendung

### 1. Map erstellen
1. **"Karten-Editor"** starten
2. Material aus der Material-Leiste wählen
3. Auf Karte klicken oder ziehen zum Zeichnen
4. Mit **💾 Speichern** sichern

### 2. Eigenes Material erstellen
1. Im Editor: **"🎨 Material-Manager"** öffnen
2. **"➕ Neues Material"** klicken
3. Name eingeben und Symbol wählen
4. Im Editor zeichnen oder Bild importieren
5. **"💾 Speichern"** - Material erscheint in Leiste!

### 3. Material bearbeiten
**Methode 1:** In Material-Leiste doppelklicken
**Methode 2:** Material auswählen → "✏️ Bearbeiten"
**Methode 3:** Im Material-Manager Fenster

### 4. Projektor-Modus
1. **"📺 Projektor-Modus"** starten
2. Fenster auf zweiten Monitor/Beamer ziehen
3. F11 für Vollbild
4. Spieler sehen die Karte!

### 5. Gamemaster-Panel
1. **"🎮 Gamemaster Panel"** öffnen
2. Fog-of-War steuern
3. Webcam-Tracking aktivieren
4. Zoom und Kamera kontrollieren

---

## 🎨 Textur-Editor Shortcuts

| Taste | Funktion |
|-------|----------|
| **Linksklick** | Zeichnen/Werkzeug anwenden |
| **Rechtsklick** | Farbpipette (Farbe aufnehmen) |
| **Maus ziehen** | Kontinuierlich zeichnen |
| **1-10** | Pinselgröße (optional) |

---

## 💾 Datei-Struktur

```
Der-eine-Ring-main/
├── advanced_texture_renderer.py   # Neues Rendering-System
├── texture_editor.py              # Textur-Editor mit Zeichenwerkzeugen
├── material_manager.py            # Material-Verwaltung und Leiste
├── texture_manager.py             # Kompatibilitäts-Layer
├── main.py                        # Map-Editor (aktualisiert)
├── enhanced_main.py               # Haupt-Anwendung
├── projector_window.py            # Projektor für Spieler
├── gm_controls.py                 # Gamemaster-Panel
├── custom_materials.json          # Gespeicherte Custom-Materialien
├── textures/                      # Exportierte/Importierte Texturen
│   └── *.png
├── maps/                          # Gespeicherte Karten
│   └── *.json
└── README_NEUE_FEATURES.md        # Diese Datei
```

---

## 🔧 Technische Details

### Advanced Texture Renderer
- **Rendering**: PIL-basiert mit erweiterten Filtern
- **Caching**: Intelligentes Caching für Performance
- **Animation**: Frame-basiertes System (60+ FPS)
- **Skalierung**: Automatische Anpassung an Tile-Größe
- **Export**: PNG-Export in hoher Auflösung (256x256+)

### Material-System
- **JSON-Storage**: Materialien in `custom_materials.json`
- **Texture-Storage**: Bilder in `textures/` Ordner
- **Auto-Backup**: Automatisches Speichern
- **Versionierung**: Kompatibilität mit älteren Versionen

### Textur-Editor
- **Canvas-Größe**: 512x512 Pixel (64x64 Grid)
- **Export-Größe**: 256x256 Pixel (optimiert)
- **History**: 50 Undo-Schritte
- **Formate**: PNG, JPG, BMP Import/Export

---

## 🎓 Tipps & Tricks

### Für Map-Ersteller
1. **Materialien organisieren**: Nutze klare Namen und Symbole
2. **Animationen sparsam**: Zu viele animierte Tiles beeinflussen Performance
3. **Kontraste**: Helle und dunkle Bereiche für bessere Sichtbarkeit
4. **Custom-Materialien**: Erstelle Variationen (z.B. "Gras Hell", "Gras Dunkel")

### Für Textur-Designer
1. **Nahtlose Kacheln**: Teste ob Textur nahtlos kachelt (wichtig!)
2. **Farbpalette**: Halte dich an eine einheitliche Farbpalette
3. **Details**: Nicht übertreiben - Texturen werden klein angezeigt
4. **Import**: PNG für beste Qualität, JPG für große Bilder

### Performance-Optimierung
1. **Material-Leiste**: Eingeklappt für mehr Editor-Platz
2. **Koordinaten**: Ausschalten bei großen Karten
3. **Animation**: Deaktiviere Animation wenn nicht benötigt
4. **Tile-Größe**: Kleinere Tiles = bessere Performance

---

## 🐛 Bekannte Probleme & Lösungen

### Problem: Material erscheint nicht in Leiste
**Lösung**: "🔄 Aktualisieren" Button klicken

### Problem: Import funktioniert nicht
**Lösung**: Prüfe ob Bild-Format unterstützt wird (PNG, JPG, BMP)

### Problem: Animation ruckelt
**Lösung**: Weniger animierte Materialien verwenden oder Animation deaktivieren

### Problem: Textur zu klein/groß
**Lösung**: Automatische Skalierung - Editor passt an Tile-Größe an

---

## 📝 Changelog

### Version 2.0 (Aktuell)
- ✅ Komplett neues Rendering-System
- ✅ Textur-Editor mit Zeichenwerkzeugen
- ✅ Material-Management-System
- ✅ Ein-/ausklappbare Material-Leiste (scrollbar, A-Z)
- ✅ Import/Export von Texturen
- ✅ Custom-Material-System
- ✅ Erweiterte Animationen
- ✅ Professionelle handgezeichnete Texturen

### Version 1.0
- Basis Map-Editor
- Projektor-Modus
- Fog-of-War
- Webcam-Tracking
- Basis-Texturen

---

## 🆘 Support & Feedback

Bei Fragen oder Problemen:
1. Prüfe diese Dokumentation
2. Schaue in `VTT_DOCUMENTATION.md` für Details
3. Teste mit Standard-Materialien ob Fehler reproduzierbar

---

## 📜 Lizenz

Dieses Projekt ist für private und nicht-kommerzielle Nutzung gedacht.

---

**Viel Spaß beim Erstellen epischer Mittelerde-Karten! 🗺️✨**
