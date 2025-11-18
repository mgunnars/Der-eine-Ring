# 🎨 Map Editor - Professional Drawing Tools

## Übersicht

Der Map Editor wurde mit professionellen VTT-Drawing-Tools erweitert, ähnlich wie bei **Foundry VTT**, **Dynamic Dungeons VTT** und anderen modernen Virtual Tabletop Systemen.

---

## 🛠️ Werkzeuge

### 🖌️ Pinsel (B)
- **Funktion**: Malt mit ausgewähltem Material
- **Pinselgröße**: 1-15 Tiles (einstellbar)
- **Tastatur**: `B` oder `[` / `]` für Größenänderung
- **Tipp**: Ziehe mit der Maus für freies Zeichnen

### 🪣 Füllen (F)
- **Funktion**: Füllt verbundene Bereiche mit gleichem Terrain
- **Algorithmus**: Flood Fill (4-Richtungen)
- **Tastatur**: `F`
- **Tipp**: Klicke auf einen Bereich um alle verbundenen Tiles zu füllen

### 💧 Pipette (I)
- **Funktion**: Material von einem Tile aufnehmen
- **Tastatur**: `I` (wie Inkscape)
- **Workflow**: 
  1. Pipette wählen
  2. Auf Tile klicken
  3. Automatisch zurück zum Pinsel mit neuem Material

### 🧹 Radierer (E)
- **Funktion**: Löscht Tiles (setzt auf "empty")
- **Pinselgröße**: Wie Pinsel einstellbar
- **Tastatur**: `E`
- **Tipp**: Ziehe für größere Bereiche

### ⬜ Rechteck (R)
- **Funktion**: Zeichnet gefülltes Rechteck
- **Workflow**:
  1. Klick auf Startpunkt
  2. Ziehe zur Ecke (zeigt Preview)
  3. Klick zum Abschließen
- **Tastatur**: `R`

### ⭕ Kreis (C)
- **Funktion**: Zeichnet Kreis-Umriss
- **Radius**: Distanz vom Startpunkt zum Endpunkt
- **Workflow**: Wie Rechteck
- **Tastatur**: `C`

### 📏 Linie (L)
- **Funktion**: Zeichnet gerade Linie
- **Algorithmus**: Bresenham's Line
- **Tastatur**: `L`
- **Tipp**: Perfekt für Straßen und Pfade

### ✂️ Auswahl (S)
- **Funktion**: Wählt Bereich aus (noch in Entwicklung)
- **Geplant**: Kopieren, Einfügen, Verschieben
- **Tastatur**: `S`

---

## ⚙️ Erweiterte Features

### 🔄 Undo/Redo
- **Undo**: `Strg + Z` oder Toolbar-Button ↶
- **Redo**: `Strg + Y` oder Toolbar-Button ↷
- **Speicher**: Bis zu 50 Aktionen

### ↔️ Symmetrie-Modus
- **Toggle**: Checkbox in Tool-Palette
- **Achsen**: Vertikal, Horizontal, oder Beide
- **Anwendung**: Alle Mal-Operationen werden gespiegelt
- **Perfekt für**: Symmetrische Dungeons, Tempel, Burgen

### 📐 Grid-Snapping
- **Automatisch**: Alle Tools rasten am Grid ein
- **Tile-basiert**: Keine Pixel-Manipulation nötig

### 🔍 Zoom & Pan
- **Zoom**: `Strg + Mausrad`
- **Pan**: `Mittlere Maustaste` oder `Shift + Linksklick + Ziehen`
- **Zurücksetzen**: Doppelklick auf leeren Bereich

---

## ⌨️ Tastatur-Shortcuts

### Tools
| Taste | Werkzeug |
|-------|----------|
| `B` | Pinsel |
| `F` | Füllen |
| `I` | Pipette |
| `E` | Radierer |
| `R` | Rechteck |
| `C` | Kreis |
| `L` | Linie |
| `S` | Auswahl |

### Bearbeitung
| Shortcut | Aktion |
|----------|--------|
| `Strg + Z` | Rückgängig |
| `Strg + Y` | Wiederherstellen |
| `[` | Pinsel kleiner |
| `]` | Pinsel größer |

### Navigation
| Shortcut | Aktion |
|----------|--------|
| `Strg + Mausrad` | Zoom |
| `Shift + Ziehen` | Pan (Verschieben) |
| `Mittlere Maustaste` | Pan |

---

## 🎯 Workflow-Tipps

### Schnelles Terrain-Painting
1. Material aus Palette wählen
2. `B` für Pinsel
3. `]` mehrmals für größeren Pinsel
4. Ziehe über Canvas für großflächiges Malen

### Präzise Strukturen
1. `R` für Rechteck
2. Klick-Zieh-Klick für Gebäude
3. `L` für Linie
4. Zeichne Straßen und Wege

### Material-Wechsel
1. `I` für Pipette
2. Klick auf gewünschtes Terrain
3. Automatisch zurück zum Pinsel
4. Sofort weitermalen

### Symmetrische Dungeons
1. Aktiviere Symmetrie-Modus ↔️
2. Wähle Achse (vertikal für Ost-West-Symmetrie)
3. Male auf einer Seite - andere Seite wird gespiegelt
4. Perfekt für symmetrische Tempel und Festungen

---

## 🆕 Geplante Features

### 🗂️ Layer-System
- **Basis-Layer**: Terrain
- **Objekt-Layer**: Möbel, Dekorationen
- **Token-Layer**: Charaktere, NPCs
- **Sichtbarkeit**: Ein/Aus pro Layer
- **Opacity**: Transparenz-Einstellung

### 🎨 Erweiterte Pinsel
- **Textur-Pinsel**: Male mit Mustern
- **Weiche Kanten**: Sanfte Übergänge
- **Spray-Tool**: Zufälliges Platzieren

### 📋 Clipboard
- **Kopieren**: `Strg + C`
- **Einfügen**: `Strg + V`
- **Ausschneiden**: `Strg + X`

### 🔄 Transformationen
- **Rotation**: 90°, 180°, 270°
- **Spiegeln**: Horizontal/Vertikal
- **Skalieren**: Bereich vergrößern/verkleinern

---

## 💡 Vergleich mit anderen VTTs

| Feature | Foundry VTT | Roll20 | Dieser Editor |
|---------|-------------|--------|---------------|
| Pinsel-Tool | ✅ | ✅ | ✅ |
| Füllen | ✅ | ❌ | ✅ |
| Formen | ✅ | ⚠️ | ✅ |
| Symmetrie | ❌ | ❌ | ✅ |
| Undo/Redo | ✅ | ⚠️ | ✅ |
| Pipette | ✅ | ❌ | ✅ |
| Layer | ✅ | ✅ | 🔜 |

**Legende**: ✅ Vorhanden | ⚠️ Eingeschränkt | ❌ Nicht vorhanden | 🔜 Geplant

---

## 🐛 Bekannte Limitierungen

1. **Layer-System**: Noch nicht implementiert - alle Tiles auf einem Layer
2. **Auswahl-Tool**: Kopieren/Einfügen noch in Entwicklung
3. **Performance**: Bei sehr großen Maps (>10.000 Tiles) kann Rendering langsam werden
4. **Textur-Pinsel**: Nur einfarbiges Malen, keine Muster

---

## 📞 Support & Feedback

Fragen oder Verbesserungsvorschläge? Öffne ein Issue auf GitHub oder kontaktiere den Entwickler!

**Happy Mapping! 🗺️✨**
