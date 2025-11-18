# 🎨 Drawing Tools - Visual Reference

## Tool-Palette Layout

```
┌─────────────────────────────────────────────────────┐
│  🗺️ Map Editor                                      │
├─────────────────────────────────────────────────────┤
│  📁 Datei  │  ✏️ Bearbeiten  │  🛠️ Werkzeuge       │
│  💾 📁 📤  │    ↶   ↷      │                       │
└─────────────────────────────────────────────────────┘

      🛠️ Werkzeuge
┌──────────────────────────┐
│  🖌️  🪣  💧  🧹         │  ← Reihe 1
│  ⬜  ⭕  📏  ✂️         │  ← Reihe 2
│                          │
│  Größe: [=====>    ] 5   │  ← Pinselgröße
│  ↔️ Sym.                │  ← Symmetrie
└──────────────────────────┘
```

---

## Tool-Symbole & Funktionen

### Reihe 1: Grundlegende Mal-Tools

```
🖌️  PINSEL (B)
    ├─ Funktion: Freies Zeichnen
    ├─ Pinselgröße: 1-15 Tiles
    ├─ Drag: Kontinuierliches Malen
    └─ Shortcuts: []/[] für Größe

🪣  FÜLLEN (F)
    ├─ Funktion: Flood Fill
    ├─ Modus: Nur verbundene Tiles
    ├─ Algorithmus: 4-Richtungen
    └─ Tipp: Gut für große Flächen

💧  PIPETTE (I)
    ├─ Funktion: Material aufnehmen
    ├─ Click: Pick Material
    ├─ Auto-Switch: Zurück zu Pinsel
    └─ Tipp: Schneller Material-Wechsel

🧹  RADIERER (E)
    ├─ Funktion: Tiles löschen
    ├─ Pinselgröße: Wie Pinsel
    ├─ Setzt auf: "empty"
    └─ Drag: Wie Pinsel
```

### Reihe 2: Form-Tools

```
⬜  RECHTECK (R)
    ├─ Funktion: Gefülltes Rechteck
    ├─ Workflow: Click → Drag → Click
    ├─ Preview: Gelbe Umrandung
    └─ Perfekt für: Gebäude, Räume

⭕  KREIS (C)
    ├─ Funktion: Kreis-Umriss
    ├─ Radius: Start → End Distanz
    ├─ Workflow: Wie Rechteck
    └─ Perfekt für: Plätze, Arenen

📏  LINIE (L)
    ├─ Funktion: Gerade Linie
    ├─ Algorithmus: Bresenham
    ├─ Workflow: Start → End
    └─ Perfekt für: Straßen, Mauern

✂️  AUSWAHL (S)
    ├─ Funktion: Bereich auswählen
    ├─ Workflow: Drag für Rechteck
    ├─ Status: 🔜 In Entwicklung
    └─ Geplant: Copy/Paste/Move
```

---

## Pinselgröße Visualisierung

```
Größe 1:   ■                (1×1 Tile)
Größe 3:   ■■■              (3×3 Bereich)
           ■■■
           ■■■

Größe 5:   ■■■■■            (5×5 Bereich)
           ■■■■■
           ■■■■■
           ■■■■■
           ■■■■■

Größe 10:  ■■■■■■■■■■       (10×10 Bereich)
           ■■■■■■■■■■
           [...]
           ■■■■■■■■■■
```

**Formel**: Kreisförmiger Pinsel mit Radius = Größe/2

---

## Symmetrie-Modus Beispiel

### Ohne Symmetrie:
```
┌──────────┐
│          │
│  ■■      │  ← Nur hier gemalt
│  ■■      │
│          │
└──────────┘
```

### Mit Symmetrie (Vertikal):
```
┌──────────┐
│          │
│  ■■  ■■  │  ← Automatisch gespiegelt!
│  ■■  ■■  │
│          │
└──────────┘
```

### Mit Symmetrie (Beide Achsen):
```
┌──────────┐
│  ■■  ■■  │
│  ■■  ■■  │  ← 4-fach gespiegelt!
│  ■■  ■■  │
│  ■■  ■■  │
└──────────┘
```

---

## Form-Tool Workflows

### Rechteck zeichnen:

```
Schritt 1:  Click (Start)
┌──────────┐
│  ●       │
│          │
└──────────┘

Schritt 2:  Drag (Preview)
┌──────────┐
│  ▓▓▓▓▓   │  ← Gelbe Preview
│  ▓▓▓▓▓   │
└──────────┘

Schritt 3:  Click (Finish)
┌──────────┐
│  ■■■■■   │  ← Fertig!
│  ■■■■■   │
└──────────┘
```

### Linie zeichnen:

```
Start         →         End
  ●──────────────────────●

Ergebnis:
  ■──────────────────────■
```

### Kreis zeichnen:

```
Center: ●
Radius: →      ●  (End-Punkt)

Ergebnis:
       ■■■
     ■     ■
    ■   ●   ■   ← Ring
     ■     ■
       ■■■
```

---

## Undo/Redo Stack

```
           Stack (max 50)
┌────────────────────────┐
│  [50] Neueste Aktion   │ ← Aktuell
│  [49] ...              │
│  [48] ...              │
│  [...]                 │
│  [2]  Zweitletzte      │
│  [1]  Erste Aktion     │
└────────────────────────┘

Strg+Z: Zurück in Stack
Strg+Y: Vorwärts in Stack
```

**Wichtig**: Bei neuer Aktion wird Redo-Stack geleert!

---

## Tastatur-Layout (QWERTZ)

```
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬─────────┐
│   │   │   │   │   │   │   │   │ I │   │   │   │ [ │    ⌫    │
│   │   │   │   │   │   │   │   │💧 │   │   │   │-  │         │
├───┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬───────┤
│     │   │   │ E │ R │   │   │   │   │   │   │   │ ] │       │
│     │   │   │🧹 │⬜ │   │   │   │   │   │   │   │+  │       │
├─────┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┬──┴┐      │
│      │   │ S │   │ F │   │   │   │   │ L │   │   │   │      │
│      │   │✂️ │   │🪣 │   │   │   │   │📏 │   │   │   │      │
├────┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴─┬─┴───┴──────┤
│    │   │   │   │ C │   │ B │   │   │   │   │   │            │
│    │   │   │   │⭕ │   │🖌️ │   │   │   │   │   │            │
└────┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴────────────┘

             Strg + Z = Undo ↶
             Strg + Y = Redo ↷
             [ = Pinsel kleiner
             ] = Pinsel größer
```

---

## Workflow-Diagramm

```
START
  │
  ├─► Material wählen (Palette links)
  │
  ├─► Tool wählen (Shortcuts oder Toolbar)
  │     │
  │     ├─► Pinsel/Radierer → Drag zum Malen
  │     ├─► Füllen → Click auf Bereich
  │     ├─► Pipette → Click zum Aufnehmen
  │     └─► Form-Tools → Click-Drag-Click
  │
  ├─► (Optional) Symmetrie aktivieren
  │
  ├─► Zeichnen/Malen
  │
  ├─► Fehler? → Strg+Z (Undo)
  │
  ├─► Fertig? → 💾 Speichern
  │
END
```

---

## Best Practices

### ✅ Do's
```
✓ Pinselgröße an Aufgabe anpassen
✓ Symmetrie für symmetrische Strukturen nutzen
✓ Pipette für schnellen Material-Wechsel
✓ Undo/Redo statt neu zeichnen
✓ Shortcuts lernen für Geschwindigkeit
```

### ❌ Don'ts
```
✗ Maximale Pinselgröße für Details
✗ Füllen ohne vorher zu prüfen
✗ Vergessen Material auszuwählen
✗ Pan-Modus mit Drawing verwechseln
✗ Zu viele Tools gleichzeitig lernen
```

---

## Performance-Tipps

### Bei großen Maps (>5000 Tiles):

```
🐌 Langsam:
   └─ Pinsel Größe 15 + Drag über ganze Map

⚡ Schnell:
   └─ Füllen-Tool für große Flächen
   └─ Formen-Tools für Strukturen
   └─ Kleiner Pinsel nur für Details
```

---

## Farb-Codes der UI

```
Tool aktiv:     #2a5d8d (Blau)
Tool inaktiv:   #3a3a3a (Grau)
Tool gedrückt:  SUNKEN  (Eingedellt)

Preview:        Gelb/Orange (Forms)
Auswahl:        Cyan gestrichelt

Erfolg:         #2a7d2a (Grün)
Fehler:         #7d2a2a (Rot)
Info:           #888888 (Grau)
```

---

**Tipp**: Drucke diese Referenz aus für schnellen Zugriff am Spieltisch! 🖨️
