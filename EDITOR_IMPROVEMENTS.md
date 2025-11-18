# 🎨 Map-Editor Verbesserungen - Implementierungsplan

## ✅ SOFORT UMSETZBAR (Quick Fixes)

### 1. **Fullscreen-Start**
- Map-Editor: `self.master.state('zoomed')` in `__init__`
- GM-Controls: `self.state('zoomed')` in `__init__`

### 2. **Select-Tool für Lichtquellen**
- Neues Tool: `active_tool = "select"`
- Bei Klick: Prüfe ob Lichtquelle in Nähe (tolerance 1-2 tiles)
- Zeige Auswahl-Marker (gelber Ring)
- Öffne Kontext-Panel für Radius-Anpassung

### 3. **Lights in eigenem Layer**
```python
self.layer_manager.add_layer("lights", "💡 Lichtquellen", visible=True, locked=False)
```

### 4. **Darkness-Polygone in eigenem Layer**
```python
self.layer_manager.add_layer("darkness", "🌑 Dunkelzonen", visible=True, locked=False)
```

### 5. **Kontextabhängiges GUI**
- Erstelle `self.context_panel = tk.Frame()` (rechts)
- Nur sichtbar wenn Objekt ausgewählt
- Zeigt: Typ, Position, Properties
- Für Lights: Radius-Slider

---

## 🔧 MITTELFRISTIG (Refactoring nötig)

### 6. **Polygon-Zeichnung verbessern**

#### **Modus A: Manuell (Ruckelfrei)**
```python
# Nutze Canvas-Coordinates statt Tile-Snapping während Zeichnen
# Erst beim Abschluss zu Tiles konvertieren
```

#### **Modus B: Geometrien**
```python
# Rectangle-Tool: 2 Klicks für Ecken
# Circle-Tool: Zentrum + Radius
# Ellipse-Tool: Zentrum + 2 Radien
```

#### **Modus C: Kantenerkennung**
```python
# Nutze OpenCV für Edge Detection
# cv2.Canny() auf Map-Tiles
# Threshold-Slider für User
```

### 7. **Polygon-Bearbeitung**
```python
# Select-Modus für Polygone
# Zeige Kontrollpunkte (kleine Kreise)
# Drag-to-Move für Punkte
# Rechtsklick: Punkt löschen
# Strg+Klick: Punkt hinzufügen
```

---

## 🚀 LANGFRISTIG (Neue Architektur)

### 8. **Objekt-System**
```python
class MapObject:
    def __init__(self, type, x, y, properties):
        self.type = type  # "light", "polygon", "marker"
        self.x = x
        self.y = y
        self.properties = properties
    
    def is_clicked(self, mx, my, tolerance=1):
        return abs(self.x - mx) <= tolerance and abs(self.y - my) <= tolerance
    
    def render(self, canvas, tile_size):
        pass
```

### 9. **GUI-Layout neu**
```python
# Accordion-Style für Tools
# Tabs für: Draw | Objects | Lighting | Layers
# Property-Panel: Floating oder rechts angedockt
# Toolbar: Icons statt Text
```

### 10. **Undo/Redo für alles**
```python
# Command-Pattern
# Auch für Objekt-Bewegung, Deletion
```

---

## 📊 PRIORITÄTEN

**P0 (KRITISCH):**
1. Fullscreen-Start ✓
2. Select-Tool für Lights ✓
3. Layers für Lights & Darkness ✓

**P1 (WICHTIG):**
4. Kontextabhängiges GUI
5. Polygon smooth drawing
6. Polygon-Bearbeitung

**P2 (NICE-TO-HAVE):**
7. Geometrie-Tools
8. Kantenerkennung
9. GUI-Redesign
10. Erweiterte Object-Verwaltung

---

## 🔨 IMPLEMENTATION STATUS

- [ ] Fullscreen-Start
- [ ] Select-Tool
- [ ] Light-Layer
- [ ] Darkness-Layer
- [ ] Context-Panel
- [ ] Polygon smooth drawing
- [ ] Polygon edit mode
- [ ] Geometry tools
- [ ] Edge detection
- [ ] GUI redesign

