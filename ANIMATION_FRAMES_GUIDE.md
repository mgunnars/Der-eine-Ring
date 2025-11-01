# Animation Frames - Benutzerhandbuch

## Überblick
Der Texture Editor unterstützt jetzt **Multi-Frame Animationen**! Du kannst eigene animierte Materialien erstellen, indem du mehrere Frames zeichnest, die im Projektor automatisch durchlaufen werden.

---

## So erstellst du animierte Materialien

### 1. Texture Editor öffnen
- Klicke auf **"✏️ Material-Manager"** im Editor
- Dann **"➕ Neu"** oder **"✏️ Bearbeiten"** für ein bestehendes Material

### 2. Frame-Controls verwenden

Im Editor siehst du jetzt einen neuen Bereich: **"🎬 Animation Frames"**

#### Navigation zwischen Frames:
- **◄ Zurück** - Vorheriger Frame
- **Weiter ►** - Nächster Frame
- Anzeige: `Frame X / Y` (aktueller Frame / Gesamt)

#### Frame-Aktionen:
- **➕ Neuer Frame** - Leeren Frame hinzufügen
- **📋 Frame Kopieren** - Aktuellen Frame duplizieren (zum Anpassen)
- **🗑️ Frame Löschen** - Aktuellen Frame entfernen

### 3. Animation erstellen

**Methode 1: Von Grund auf neu**
1. Zeichne Frame 1
2. Klicke **"➕ Neuer Frame"**
3. Zeichne Frame 2 (komplett neu)
4. Wiederhole für weitere Frames

**Methode 2: Frame kopieren und anpassen** (EMPFOHLEN!)
1. Zeichne Frame 1
2. Klicke **"📋 Frame Kopieren"**
3. Passe die Kopie leicht an (z.B. Welle verschieben, Baum bewegen)
4. Wiederhole für flüssige Animation

### 4. Material speichern
- Material wird automatisch als **animiert** markiert, wenn >1 Frame
- Klicke **"💾 Speichern"**
- Alle Frames werden gespeichert als:
  - `material_name_frame_0.png`
  - `material_name_frame_1.png`
  - `material_name_frame_2.png`
  - usw.

---

## Tipps für gute Animationen

### Flüssigkeit
- **Mehr Frames = smoothere Animation**
- Minimum: 4-6 Frames
- Optimal: 8-12 Frames
- Sehr smooth: 15-20 Frames

### Frame-Kopieren Workflow
1. Zeichne Basis-Frame
2. Kopiere ihn
3. Mache KLEINE Änderungen (1-2 Pixel Verschiebung)
4. Kopiere wieder
5. Noch eine kleine Änderung
6. → Ergibt flüssige Bewegung!

### Was animieren?
- **Wasser**: Wellen verschieben, Glanzlichter bewegen
- **Feuer**: Flammen flackern, Farbe ändern
- **Gras**: Leicht hin und her wackeln
- **Flaggen**: Wind-Bewegung
- **Sterne**: Funkeln (Alpha wechseln)

---

## Beispiel: Animiertes Wasser

**Frame 1:**
```
Welle: ~~~~
```

**Frame 2** (kopiert + angepasst):
```
Welle:  ~~~~
```

**Frame 3** (kopiert + angepasst):
```
Welle:   ~~~~
```

**Frame 4** (kopiert + angepasst):
```
Welle:    ~~~~
```

→ Welle bewegt sich nach rechts! 🌊

---

## Technische Details

### Speicherformat
- Frames: `textures/{material_id}_frame_{0-59}.png`
- Basis: `textures/{material_id}.png` (Frame 0)
- Auflösung: 256x256px (optimiert)

### Animation im Projektor
- Frame-Rate: ~12.5 FPS (80ms pro Frame)
- Loop: Frames 0 → N → 0 (endlos)
- Smooth: 120 Frames total möglich

### Performance
- Frames werden einzeln geladen (kein Memory-Overflow)
- Nur sichtbare Tiles werden animiert
- Cache-System für schnelles Laden

---

## Troubleshooting

**Problem**: Animation ruckelt
- **Lösung**: Mehr Zwischenframes erstellen (Frame kopieren!)

**Problem**: Animation zu schnell
- **Lösung**: Mehr Frames mit kleineren Änderungen

**Problem**: Material nicht animiert im Projektor
- **Lösung**: Prüfe ob >1 Frame gespeichert wurde

**Problem**: Frames gehen verloren
- **Lösung**: Vor Wechsel wird automatisch gespeichert, aber teste vorher!

---

## Keyboard Shortcuts (geplant)

- `←` / `→` - Frame Navigation
- `Ctrl+D` - Frame duplizieren
- `Delete` - Frame löschen
- `Ctrl+N` - Neuer Frame

---

Viel Spaß beim Animieren! 🎨🎬
