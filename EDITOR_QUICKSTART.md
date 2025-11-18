# 🎨 Quick Start - Neue Drawing Tools

## Erste Schritte mit den professionellen Werkzeugen

### 1️⃣ Tool auswählen

Die **Tool-Palette** befindet sich in der oberen Toolbar:

```
🖌️ Pinsel    🪣 Füllen    💧 Pipette    🧹 Radierer
⬜ Rechteck   ⭕ Kreis     📏 Linie     ✂️ Auswahl
```

**Tipp**: Nutze Tastatur-Shortcuts (B, F, I, E, R, C, L, S) für schnellen Wechsel!

---

### 2️⃣ Grundlegende Workflows

#### 🖌️ Freies Zeichnen (wie bei Paint)
```
1. Material aus Palette wählen (links)
2. Taste [B] drücken für Pinsel
3. Pinselgröße mit []/[] anpassen
4. Mit Maus ziehen = Malen!
```

#### 🪣 Große Flächen füllen
```
1. Material wählen
2. Taste [F] für Füllen
3. Auf Bereich klicken = Alles mit gleichem Terrain wird gefüllt
```

#### 📐 Gebäude & Strukturen
```
1. Material wählen (z.B. "stone" oder "wood")
2. Taste [R] für Rechteck
3. Klick auf Startpunkt
4. Ziehe zur Ecke (gelbe Preview)
5. Klick zum Abschließen
```

#### 🛣️ Straßen & Wege
```
1. Material "road" wählen
2. Taste [L] für Linie
3. Klick auf Startpunkt
4. Klick auf Endpunkt = Gerade Linie!
```

---

### 3️⃣ Erweiterte Techniken

#### ↔️ Symmetrischer Dungeon
```
1. Aktiviere Symmetrie-Checkbox (↔️ Sym.)
2. Wähle Pinsel [B]
3. Male auf einer Seite
4. → Automatisch gespiegelt auf der anderen Seite!
```

**Perfekt für**: Tempel, Burgen, symmetrische Räume

#### 💧 Material kopieren
```
1. Taste [I] für Pipette
2. Klick auf gewünschtes Tile
3. → Automatisch zurück zum Pinsel mit diesem Material
4. Sofort weitermalen!
```

#### 🔄 Fehler korrigieren
```
Strg + Z = Rückgängig
Strg + Y = Wiederherstellen
```

**Tipp**: Bis zu 50 Aktionen gespeichert!

---

### 4️⃣ Pinselgröße optimal nutzen

```
Pinselgröße 1-3:   Detailarbeit (Fenster, kleine Objekte)
Pinselgröße 4-7:   Normale Räume und Wege
Pinselgröße 8-15:  Große Flächen (Wiesen, Wasser)
```

**Schnell ändern**: `[` kleiner, `]` größer

---

### 5️⃣ Navigation bei großen Maps

#### Zoom
```
Strg + Mausrad rauf/runter = Zoom In/Out
```

#### Verschieben (Pan)
```
Option A: Shift + Linksklick + Ziehen
Option B: Mittlere Maustaste + Ziehen
```

---

## 🎯 Typische Szenarien

### Scenario: Erstelle einen Dungeon-Raum

```
1. [R] - Rechteck für Raum-Umriss mit "stone"
2. [F] - Fülle Inneres mit "dirt" 
3. [B] - Pinsel Größe 1 für Details
4. [L] - Linien für Türen mit "empty"
5. Strg+Z falls nötig
```

### Scenario: Natürliche Landschaft

```
1. [F] - Fülle Basis mit "grass"
2. [B] - Pinsel Größe 5-8
3. Male Wald-Bereiche mit "forest"
4. [I] - Pipette für "water"
5. Male Fluss mit Pinsel Größe 3-5
6. [L] - Straße als Linie mit "road"
```

### Scenario: Symmetrische Burg

```
1. Aktiviere Symmetrie ↔️
2. [R] - Rechtecke für Türme (gespiegelt!)
3. [L] - Mauer-Linien (gespiegelt!)
4. Deaktiviere Symmetrie
5. [F] - Fülle Innenhof mit "sand"
```

---

## ⚠️ Häufige Fehler

### Problem: "Tool funktioniert nicht"
✅ **Lösung**: Prüfe ob Tool aktiv ist (Button soll blau sein)

### Problem: "Pinsel malt nichts"
✅ **Lösung**: Material aus Palette wählen (links)

### Problem: "Kann nicht zoomen"
✅ **Lösung**: `Strg` gedrückt halten + Mausrad

### Problem: "Füllen füllt zu viel"
✅ **Lösung**: Normale! Flood-Fill füllt alle verbundenen Tiles

---

## 🎓 Von Anfänger zu Profi

### Woche 1: Basics
- Pinsel, Radierer, Füllen
- Material-Palette nutzen
- Undo/Redo

### Woche 2: Formen
- Rechteck für Gebäude
- Linie für Straßen
- Kreis für Plätze

### Woche 3: Advanced
- Symmetrie-Modus
- Pipette-Workflow
- Pinselgrößen optimal nutzen

### Woche 4: Power-User
- Tastatur-Shortcuts auswendig
- Zoom/Pan ohne nachzudenken
- Komplexe Dungeons in <30 Minuten

---

## 📚 Weiterführende Docs

- **Vollständige Dokumentation**: `EDITOR_TOOLS_GUIDE.md`
- **Material-System**: `MATERIAL_BUNDLES.md`
- **SVG-Export**: `SVG_VECTOR_MAPS.md`

---

**Viel Erfolg beim Kartenbau! 🗺️✨**

_Tipp: Drücke `?` im Editor für diese Anleitung (geplant)_
