# 🚀 Quick-Start Guide - Neues Rendering-System

## Sofort loslegen!

### 1️⃣ Editor mit neuen Features starten

```bash
python enhanced_main.py
```

Dann: **"🎨 Karten-Editor"** klicken

---

## 2️⃣ Die neue Material-Leiste

### Oben im Editor siehst du jetzt:

```
▼ Materialien  [➕ Neu] [✏️ Bearbeiten] [🔄 Aktualisieren]
┌────────────────────────────────────────────────┐
│ [🌿 Gras] [💧 Wasser] [🏔️ Berg] [🌲 Wald] ... │  ← Scrollbar!
└────────────────────────────────────────────────┘
```

**Was du tun kannst:**
- ▼ **Klicke auf "▼ Materialien"** → Leiste klappt ein/aus
- 🖱️ **Klicke auf ein Material** → Es wird ausgewählt
- 🖱️🖱️ **Doppelklick auf Material** → Editor öffnet sich
- ⬅️➡️ **Scrolle horizontal** → Mehr Materialien sehen

---

## 3️⃣ Eigene Textur erstellen - IN 5 SCHRITTEN!

### Schritt 1: Neues Material erstellen
Klicke auf **"➕ Neu"** in der Material-Leiste

### Schritt 2: Name eingeben
Gib deinem Material einen Namen, z.B. "Lavafeld"

### Schritt 3: Zeichnen!
```
🖌️ Pinsel    - Zeichnen
🧹 Radierer  - Löschen
💧 Füller    - Fläche füllen
💉 Pipette   - Farbe aufnehmen
```

**Tipp:** Rechtsklick = Pipette (Farbe schnell aufnehmen!)

### Schritt 4: Farbe wählen
Klicke **"🎨 Farbe wählen"** → Wähle eine Farbe

### Schritt 5: Speichern
Klicke **"💾 Speichern"** → Fertig! ✅

**→ Dein Material erscheint automatisch in der Leiste!**

---

## 4️⃣ Bild importieren - SUPER EINFACH!

### Option A: Im Material-Editor
1. Klicke **"📂 Importieren"**
2. Wähle ein Bild (PNG, JPG, BMP)
3. **Fertig!** Wird automatisch angepasst

### Option B: Für existierendes Material
1. Material doppelklicken
2. **"📂 Importieren"**
3. Bild wählen
4. **"💾 Speichern"**

---

## 5️⃣ Material bearbeiten

### Methode 1: Doppelklick
→ Einfach auf Material in der Leiste **doppelklicken**

### Methode 2: Bearbeiten-Button
1. Material anklicken
2. **"✏️ Bearbeiten"** klicken

### Methode 3: Material-Manager
1. **"🎨 Material-Manager"** öffnen
2. Material auswählen
3. **"✏️ Bearbeiten"**

---

## 6️⃣ Material-Manager

**Öffnen:** Button im Editor: **"🎨 Material-Manager"**

### Was du hier siehst:
```
┌─────────────────────────────────────────┐
│ ID          │ Name    │ Typ    │ Anim  │
├─────────────────────────────────────────┤
│ grass       │ Gras    │ Basis  │ Nein  │
│ lavafeld    │ Lavafeld│ Custom │ Ja    │
│ ...         │ ...     │ ...    │ ...   │
└─────────────────────────────────────────┘

[➕ Neues Material] [✏️ Bearbeiten] [🗑️ Löschen] [📤 Exportieren]
```

**Funktionen:**
- ➕ Neues Material erstellen
- ✏️ Ausgewähltes Material bearbeiten
- 🗑️ Custom-Material löschen (Basis-Materialien nicht!)
- 📤 Textur exportieren (PNG-Datei)

---

## 7️⃣ Animations-Checkbox

**Im Material-Editor:**
```
☑️ 🎬 Animiert
```

**Aktiviert?** → Material wird animiert (wie Wasser mit Wellen)  
**Deaktiviert?** → Material ist statisch

**Tipp:** Zu viele Animationen = Performance-Einbußen!

---

## 8️⃣ Praktische Shortcuts

### Im Material-Editor:
- **Linksklick** → Zeichnen
- **Rechtsklick** → Pipette (Farbe aufnehmen)
- **Linksklick + Ziehen** → Kontinuierlich zeichnen
- **Strg+Z** → Rückgängig (50 Schritte!)
- **Strg+Y** → Wiederholen

---

## 🎯 Beispiel-Workflow: "Lavafluss" erstellen

### 1. Material erstellen
```
➕ Neu → Name: "Lavafluss" → Symbol: "🌋"
```

### 2. Basis-Farbe
```
🎨 Farbe: Orange (#FF6600)
💧 Füller: Gesamte Fläche füllen
```

### 3. Lava-Details
```
🖌️ Pinsel: Größe 3
🎨 Farbe: Rot (#FF0000)
→ Lava-Adern zeichnen
```

### 4. Glühen
```
🎨 Farbe: Gelb (#FFFF00)
🖌️ Pinsel: Größe 1
→ Highlights setzen
```

### 5. Animation?
```
☑️ 🎬 Animiert (aktivieren)
```

### 6. Speichern
```
💾 Speichern → Fertig! ✅
```

**→ Verwende "Lavafluss" jetzt in deiner Map!**

---

## 🔥 Pro-Tipps

### Für Schnelligkeit:
1. **Rechtsklick = Pipette** (schneller als Tool wechseln!)
2. **Füller nutzen** für große Flächen
3. **Pinselgröße anpassen** für Details vs. Flächen

### Für schöne Texturen:
1. **Teste nahtlose Kacheln** → Zeichne über Rand hinaus
2. **Nutze mehrere Farbtöne** → Mehr Tiefe
3. **Shadows & Highlights** → Realismus

### Für Organisation:
1. **Klare Namen** → "Gras Hell", "Gras Dunkel"
2. **Symbole nutzen** → Schnell erkennbar
3. **Material-Leiste einklappen** → Mehr Platz zum Arbeiten

---

## ⚡ Performance-Tipps

### Animation:
- ❌ **Nicht:** Gesamte Karte animiert
- ✅ **Besser:** Nur Akzente (Wasser, Feuer)

### Material-Anzahl:
- 💡 **~20-30 Materialien** = Optimal
- ⚠️ **>50 Materialien** = Scrolling wird länger

### Textur-Größe:
- Standard: **64x64** Pixel (Editor)
- Export: **256x256** Pixel (hochwertig)

---

## 🆘 Häufige Fragen

### "Material erscheint nicht in Leiste"
→ Klicke **"🔄 Aktualisieren"**

### "Import funktioniert nicht"
→ Nur PNG, JPG, BMP unterstützt! GIF-Animationen → als PNG speichern

### "Editor ist zu langsam"
→ **▶ Materialien** (einklappen) oder Koordinaten ausschalten

### "Wie lösche ich ein Material?"
→ **Material-Manager** → Material auswählen → **"🗑️ Löschen"**  
(Nur Custom-Materialien!)

### "Textur ist verpixelt"
→ Normal bei kleinen Tiles! Größere Kacheln = schärfer

---

## 🎉 Das war's!

**Du bist jetzt bereit, epische Custom-Materialien zu erstellen!**

### Nächste Schritte:
1. 🎨 Erstelle 2-3 eigene Materialien zum Üben
2. 🗺️ Baue eine Map mit deinen Materials
3. 📺 Zeige sie deinen Spielern im Projektor!

---

**Viel Erfolg! 🚀✨**
