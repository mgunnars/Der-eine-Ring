# 🎨 Erweiterte Zeichentools - Quick Guide

## Neue Features implementiert! ✨

### 🎨 Layer-System
**Rechte Sidebar → Layer Panel**
- **4 Standard-Layer**: 
  - 🗺️ Base Terrain (Basis-Karte)
  - 🏰 Objects (Gebäude, Objekte)
  - 🎭 Tokens (Spielfiguren)
  - 📝 Annotations (Notizen, Markierungen)
- **+ / −** Buttons: Layer hinzufügen/entfernen
- **👁 Visible**: Layer ein/ausblenden
- **🔒 Locked**: Layer vor Bearbeitung schützen
- **Aktiver Layer** ist blau markiert

---

## 🛠️ Neue Zeichentools

### 1. 🌊 Curve Tool (Bezier-Kurven)
**Taste: V**
- Organische Linien für Flüsse, Pfade, Straßen
- **Verwendung:**
  1. Drücke `V` oder klicke 🌊 Button
  2. Klicke Punkte für Kurve
  3. **ENTER** = Kurve zeichnen
  4. **ESC** = Abbrechen
- **Gelbe Punkte** = Kontrollpunkte
- **Orange gestrichelte Linien** = Verbindungen
- **Cyan-Kurve** = Vorschau

### 2. ⬟ Polygon Tool
**Taste: P**
- Komplexe Formen für Räume, Gebäude, Bereiche
- **Verwendung:**
  1. Drücke `P` oder klicke ⬟ Button
  2. Klicke Eckpunkte
  3. **ENTER** = Polygon füllen & schließen
  4. **ESC** = Abbrechen
- **Grüner Punkt** = Startpunkt
- **Gelbe Punkte** = Eckpunkte
- **Füllt alle Tiles** innerhalb automatisch

### 3. 📝 Text Tool
**Taste: T**
- Beschriftungen für Orte, Hinweise, Namen
- **Verwendung:**
  1. Drücke `T` oder klicke 📝 Button
  2. Klicke Position
  3. Gib Text ein
  4. Text erscheint mit Schatten
- Text bleibt beim Speichern erhalten

### 4. 🔄 Transform Tool (Vorbereitet)
**Taste: X**
- Rotation, Skalierung, Spiegelung (in Entwicklung)

---

## ⌨️ Erweiterte Shortcuts

### Neue Tool-Shortcuts
- `V` = Curve (Kurve)
- `P` = Polygon
- `T` = Text
- `X` = Transform

### Curve/Polygon Steuerung
- `ENTER` = Fertigstellen
- `ESC` = Abbrechen

### Bestehende Shortcuts (unverändert)
- `B` = Brush (Pinsel)
- `F` = Fill (Füllen)
- `I` = Eyedropper (Pipette)
- `E` = Eraser (Radierer)
- `R` = Rectangle (Rechteck)
- `C` = Circle (Kreis)
- `L` = Line (Linie)
- `S` = Select (Auswahl)
- `Ctrl+Z` = Undo
- `Ctrl+Y` = Redo
- `[` / `]` = Pinselgröße

---

## 🎯 Workflow-Beispiele

### Fluss zeichnen mit Curve Tool
1. Wähle "water" Material
2. Drücke `V` für Curve
3. Klicke Flussverlauf: Start → Kurven → Ende
4. `ENTER` zum Zeichnen
5. Fertiger Fluss mit natürlichen Kurven!

### Raum erstellen mit Polygon
1. Wähle "stone" für Wände
2. Drücke `P` für Polygon
3. Klicke Raumecken (im Uhrzeigersinn)
4. `ENTER` zum Füllen
5. Raum ist fertig!

### Karte beschriften
1. Drücke `T` für Text
2. Klicke Position (z.B. Taverne)
3. Tippe "Die Goldene Eiche"
4. Beschriftung erscheint!

---

## 💾 Layer-Workflow

### Professioneller Map-Aufbau
1. **Base Terrain Layer**:
   - Gras, Wasser, Berge zeichnen
   - Grundlage der Karte

2. **Objects Layer**:
   - Gebäude, Bäume, Steine platzieren
   - Kann ausgeblendet werden für "nur Terrain" Ansicht

3. **Tokens Layer**:
   - Spielfiguren positionieren
   - Kann separat für Spieler/GM angezeigt werden

4. **Annotations Layer**:
   - Text-Markierungen
   - Temporäre Notizen
   - Einfach löschbar ohne Map zu ändern

### Layer-Tricks
- **Lock Base Layer** → Verhindert versehentliches Übermalen
- **Hide Tokens** → Zeigt Map ohne Figuren
- **Annotations nur für GM** → Verstecke vor Spielern

---

## 🚀 Nächste Features (in Entwicklung)

### Transform Tool
- Auswahl rotieren
- Skalieren (größer/kleiner)
- Horizontal/Vertikal spiegeln

### Erweiterte Farbpalette
- Color Picker Dialog
- Gespeicherte Paletten
- Hex-Code Eingabe

### 2.5D Features (Phase 2)
- Dynamic Lighting (Fackeln, Fenster)
- Normal Maps für Tiefe
- Particle Systems (Feuer, Regen)
- Shadow Casting

---

## 🐛 Bekannte Limits
- Text kann noch nicht nachträglich bearbeitet werden (kommt)
- Transform Tool noch nicht aktiv
- Layer können noch nicht umbenannt werden (kommt)

---

## 💡 Tipps & Tricks

1. **Curve Tool**: Mind. 2 Punkte für einfache Linie, 3-4 für schöne Kurven
2. **Polygon Tool**: Immer im Uhrzeigersinn klicken für beste Resultate
3. **Layer Lock**: Lock Base Layer bevor du Details zeichnest
4. **Undo**: Funktioniert auch für Curve/Polygon (vor ENTER!)
5. **ESC ist dein Freund**: Bricht alles ab ohne zu speichern

---

**Version:** 2.5D Update v1.0
**Datum:** November 2025
**Status:** ✅ Layer-System, ✅ Curve, ✅ Polygon, ✅ Text
