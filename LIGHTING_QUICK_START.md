# 🔥 Lighting Objects - Quick Start

## ✨ Wie platziere ich Fackeln/Kerzen?

### 🎯 **Methode 1: Material-basiert (EMPFOHLEN)**

1. **Starte Editor:** `python enhanced_main.py` → Map Editor
2. **Rechte Sidebar** → Scrolle zu **"🔥 Lighting Objects"**
3. **Wähle Material:**
   - **🔥 torch** - Fackel (stark flackernd)
   - **🕯️ candle** - Kerze (sanft flackernd)
   - **🏮 lantern** - Laterne
   - **🔥 fire** - Feuer
   - **🔥 campfire** - Lagerfeuer
   - **🪟 window** - Fenster-Licht
   - **✨ magic_circle** - Magischer Kreis
   - **💎 crystal** - Kristall

4. **Brush-Tool aktiv?** (Pinsel-Icon oder `B` drücken)
5. **Click & Drag** auf Map
6. **Aktiviere Lighting:** Checkbox "💡 Dynamic Lighting" ✓
7. **FERTIG!** Fackeln leuchten und flackern automatisch! 🔥✨

---

### 💡 **Methode 2: Light-Tool (Manuell)**

Wenn du nur Licht ohne Objekt willst:

1. **Drücke `G`** (für "Glow") oder klicke **💡 Light Button**
2. **Wähle Preset** (Torch/Candle/Fire/etc.)
3. **Klicke auf Map**
4. **Aktiviere Lighting**

---

## 🎨 Beispiel: Taverne beleuchten

```
1. Material "candle" wählen
2. Auf alle Tische klicken (Brush-Tool)
3. Material "fire" wählen
4. Im Kamin platzieren
5. Material "torch" wählen
6. An Wänden platzieren (2-3 Stück)
7. Checkbox "💡 Dynamic Lighting" ✓
8. BOOM! Gemütliche Taverne mit flackerndem Licht! 🍺🔥
```

---

## 🔥 Material-Übersicht

| Material | Icon | Licht | Flackern | Radius |
|----------|------|-------|----------|--------|
| torch | 🔥 | Warm Orange | ✅ Stark | 6 Tiles |
| candle | 🕯️ | Gelb | ✅ Sanft | 3 Tiles |
| lantern | 🏮 | Gelb | ✅ Sanft | 3 Tiles |
| fire | 🔥 | Helles Orange | ✅ Sehr stark | 5 Tiles |
| campfire | 🔥 | Orange | ✅ Sehr stark | 5 Tiles |
| window | 🪟 | Tageslicht Blau | ❌ Nein | 8 Tiles |
| magic_circle | ✨ | Violett | ✅ Pulsierend | 7 Tiles |
| crystal | 💎 | Violett | ✅ Pulsierend | 7 Tiles |

---

## ⌨️ Shortcuts

- **`B`** = Brush Tool (zum Platzieren)
- **`G`** = Light Tool (manuell)
- **`E`** = Eraser (Löschen)
- **Checkbox** = Lighting an/aus

---

## 🐛 Troubleshooting

**"Ich sehe keine Lighting Objects!"**
→ Scrolle in der rechten Sidebar nach unten
→ Suche nach "🔥 Lighting Objects" Bundle

**"Fackeln leuchten nicht!"**
→ Checkbox "💡 Dynamic Lighting" aktivieren
→ Warte 1 Sekunde (Animation startet)

**"Material nicht gefunden!"**
→ Bundle ist always_loaded, sollte automatisch da sein
→ Neustart: `python enhanced_main.py`

**"Licht verschwindet!"**
→ Material übermalen entfernt automatisch das Licht
→ Das ist korrekt so! 😊

---

## 💡 Profi-Tipps

1. **Brush Size:** Pinselgröße = 1 für einzelne Fackeln
2. **Layer nutzen:** "Objects" Layer für Fackeln
3. **Symmetrie:** Fackeln symmetrisch platzieren sieht gut aus
4. **Mix & Match:** Kerzen + Fackeln + Feuer kombinieren
5. **Nicht zu viel:** 5-8 Lichtquellen pro Raum reichen
6. **Save & Load:** Speichern vergessen nicht - Lichter werden mit gespeichert!

---

**Version:** Lighting Objects v1.0  
**Datum:** November 2025  
**Status:** ✅ Voll funktionsfähig!

**Viel Spaß beim Beleuchten!** 🔥✨
