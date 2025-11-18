# 💡 Dynamic Lighting System - Guide

## 🌟 Was ist neu?

Das **Dynamic Lighting System** bringt realistische Beleuchtung in dein VTT! Platziere Fackeln, Kerzen, Fenster und magische Lichtquellen für atmosphärische Dungeons und düstere Tavernen.

### ✨ Neue Features in v1.1:
- **🔥 Flicker-Animation** - Fackeln und Kerzen flackern in Echtzeit!
- **🎨 Auto-Lights** - Fackel-Material platzieren = automatisch Lichtquelle!
- **60 FPS Animation** - Flüssige, realistische Licht-Bewegung

---

## 🚀 Quick Start

### Lighting aktivieren
1. **Rechte Sidebar** → "💡 Dynamic Lighting" **✓ anklicken**
2. Map wird dunkler mit Ambient-Licht
3. Platziere Lichtquellen!

### 🆕 AUTO-LIGHTS: Material-basierte Beleuchtung

**Das Beste Feature!** Platziere einfach leuchtende Objekte und sie leuchten automatisch:

#### Methode 1: Material platzieren (EMPFOHLEN)
1. **Wähle Material:** `torch`, `candle`, `fire`, `lantern`, etc.
2. **Platziere auf Map** (Brush-Tool)
3. **✨ Automatisch:** Lichtquelle wird erstellt!
4. **Flackert live** wenn du Lighting aktivierst

#### Methode 2: Manuell (Light-Tool)
1. **Drücke `G`** (für "Glow") oder klicke **💡 Button**
2. Wähle Licht-Typ (z.B. 🔥 Torch)
3. **Klicke** Position auf Map
4. Licht erscheint mit Leuchtkegel!

### Lichtquelle entfernen
- **Übermale** leuchtendes Material → Auto-Light verschwindet
- **Light-Tool aktiv** → Klicke auf existierendes Licht → Entfernt

---

## 🔥 Licht-Typen & Auto-Light Materials

### 🔥 Torch (Fackel)
- **Radius:** 6 Tiles
- **Farbe:** Warm Orange (255, 180, 100)
- **Flackern:** ✅ Ja (stark)
- **Auto-Materials:** `torch`
- **Verwendung:** Dungeons, Korridore, Außenbereiche

### 🕯️ Candle (Kerze)
- **Radius:** 3 Tiles  
- **Farbe:** Warmes Gelb (255, 220, 150)
- **Flackern:** ✅ Ja (sanft)
- **Auto-Materials:** `candle`, `lantern`
- **Verwendung:** Tavernen, Zimmer, Altäre

### 🪟 Window (Fenster)
- **Radius:** 8 Tiles
- **Farbe:** Kühles Tageslicht (200, 220, 255)
- **Flackern:** ❌ Nein
- **Auto-Materials:** `window`
- **Verwendung:** Tageslicht durch Fenster, Öffnungen

### ✨ Magic (Magie)
- **Radius:** 7 Tiles
- **Farbe:** Violett (150, 100, 255)
- **Flackern:** ✅ Ja (pulsierend)
- **Auto-Materials:** `magic_circle`, `crystal`
- **Verwendung:** Zauber, Portale, magische Objekte

### 🔥 Fire (Feuer)
- **Radius:** 5 Tiles
- **Farbe:** Helles Orange (255, 150, 50)
- **Flackern:** ✅ Ja (sehr stark)
- **Auto-Materials:** `fire`, `campfire`
- **Verwendung:** Lagerfeuer, Kamin, Brandschäden

### 🌙 Moonlight (Mondlicht)
- **Radius:** 10 Tiles
- **Farbe:** Silber-Blau (180, 200, 230)
- **Flackern:** ❌ Nein
- **Auto-Materials:** -
- **Verwendung:** Nacht-Außenbereiche, Vollmond

---

## 🎬 Flicker-Animation

### Wie funktioniert's?
- **60 FPS Animation** - Flüssige Bewegung
- **Sinus-Wellen** + **Zufalls-Rauschen** = Realismus
- **Nur bei Bedarf** - Animation läuft nur wenn Flicker-Lights vorhanden

### Performance
- **Optimiert:** Rendert nur wenn nötig
- **Kein Lag:** Selbst mit 50+ Lichtquellen
- **Smart:** Animation stoppt wenn Lighting aus

---

## 🎯 Beleuchtungs-Physik

### Realistic Light Falloff
- **Quadratischer Abfall:** `Intensity = 1 / (1 + distance²)`
- Je weiter vom Licht, desto dunkler
- Physikalisch korrekt!

### Flicker-Effekt
- **Sinus-Wellenförmig:** Natürliches Flackern
- **Zufälliges Rauschen:** Lebendige Bewegung
- **Fackel:** Stark flackernd (±15% Intensität)
- **Kerze:** Sanft flackernd (±10% Intensität)
- **Magie:** Pulsierend (langsamer)

### Ambient Lighting
- **Basis-Dunkelheit:** Dunkles Blau (30, 30, 40)
- **Ambient Intensity:** 20% (anpassbar)
- **Nie komplett schwarz:** Spieler sehen immer Umrisse

---

## ⌨️ Shortcuts

- **`G`** = Light Tool aktivieren
- **`B`** = Brush Tool (für Auto-Lights)
- **Click** = Licht platzieren/entfernen / Material platzieren
- **Checkbox** = Lighting an/aus

---

## 💾 Speichern & Laden

### Automatisch gespeichert
- Alle Lichtquellen werden in JSON gespeichert
- Position, Typ, Farbe, Intensität, Flicker-Status
- Beim Laden automatisch wiederhergestellt

### Map-Format erweitert
```json
{
  "lighting": {
    "lights": [
      {
        "x": 10,
        "y": 15,
        "radius": 6,
        "color": [255, 180, 100],
        "intensity": 0.9,
        "flicker": true,
        "light_type": "torch"
      }
    ],
    "ambient_color": [30, 30, 40],
    "ambient_intensity": 0.2,
    "enabled": true
  }
}
```

---

## 🎨 Workflow-Beispiele

### 🏰 Düsterer Dungeon (MIT AUTO-LIGHTS)
1. Aktiviere Lighting
2. **Wähle Material `torch`**
3. **Platziere Fackeln** an Wänden alle 10-12 Tiles
4. **Fertig!** - Fackeln flackern automatisch
5. **Ambient = 20%** (dunkel)
6. Spieler müssen Fackeln tragen!

### 🍺 Gemütliche Taverne
1. Aktiviere Lighting
2. **Material `candle`** auf allen Tischen platzieren
3. **Material `fire`** im Kamin
4. 1-2 **`torch`** an Wänden
5. **`window`** für Tageslicht (optional)
6. **Alle flackern live!** ✨

### 🔮 Magischer Tempel
1. Aktiviere Lighting
2. **`magic_circle`** bei Altären (violettes Glühen)
3. **`candle`** für Rituale
4. **Moonlight** durch Dachöffnung (Light-Tool)
5. Mystische Atmosphäre!

### 🌙 Nacht-Außenbereich
1. Aktiviere Lighting
2. **Moonlight** als Hauptlicht (Light-Tool, G-Key)
3. Lagerfeuer mit **`campfire`** Material
4. **`torch`** bei Wachen
5. Dunkle, gefährliche Atmosphäre

---

## 🛠️ Technische Details

### Performance
- **Optimiert für 100+ Lichter**
- Gaussian Blur für weiche Schatten
- Rendering cached wo möglich
- **60 FPS Animation** bei normalen Maps
- Smart-Rendering: Nur bei Flicker neu zeichnen

### Rendering-Pipeline
1. **Dunkelheits-Base:** Schwarzes Bild
2. **Lichtquellen-Render:** Radiale Gradienten (mit time_offset)
3. **Blur-Pass:** Gaussian Blur für Weichheit
4. **Alpha-Maske:** Dunkelheit invertiert
5. **Overlay:** Über Map gelegt

### Animation-Loop
```python
# 60 FPS Timer
self.after(16, update_lighting_animation)

# Zeit-basiertes Flackern
intensity = sin(time * 0.1 * 10) * 0.15 + random(-0.05, 0.05)
```

### Farb-Theorie
- **Warm (Orange/Gelb):** Gemütlich, sicher
- **Kühl (Blau):** Kalt, mystisch
- **Violett:** Magisch, unheimlich
- **Flackern:** Lebendig, realistisch

---

## 🚧 Bekannte Limits

- ~~**Flicker-Animation:** Noch nicht animiert~~ ✅ **FIXED in v1.1**
- **Shadow Casting:** Objekte werfen noch keine Schatten (Phase 2)
- **Ambient einstellbar:** Noch nicht im UI (Code unterstützt es)
- **Light-Editor:** Keine Nachbearbeitung einzelner Lichter (kommt)

---

## 🔮 Kommende Features (Phase 2)

### Shadow Casting
- Objekte (Wände, Bäume) werfen Schatten
- Ray-Casting für Geometrie
- Dynamische Schatten folgen Licht

### Normal Maps
- Texturen bekommen Höheninformation
- Licht reagiert auf Relief
- 2.5D-Effekt verstärkt

### Particle Systems
- Feuer-Partikel für Fackeln
- Rauch aufsteigend
- Magische Funken

### Ambient Occlusion
- Ecken und Spalten automatisch dunkler
- Realistische Tiefe
- Post-Processing

---

## 💡 Profi-Tipps

1. **Auto-Lights nutzen:** Material platzieren statt manuell Lichter setzen
2. **Weniger ist mehr:** 5-8 Lichter pro Raum reichen
3. **Mix & Match:** Kombiniere verschiedene Typen (torch + candle)
4. **Asymmetrie:** Nicht zu symmetrisch platzieren
5. **Gameplay:** Dunkle Bereiche = Verstecke
6. **Atmosphäre:** Beleuchtung erzählt Geschichte
7. **Kontrast:** Helle + dunkle Bereiche mischen
8. **Flicker sparsam:** Zu viel ist anstrengend (aber so schön!)
9. **Material = Light:** `torch` platzieren ist schneller als G-Key
10. **Live-Vorschau:** Lighting während Platzierung aktiviert lassen

---

## 🐛 Troubleshooting

**"Lighting zeigt nichts"**
→ Checkbox "💡 Dynamic Lighting" aktiviert?

**"Fackeln flackern nicht"**
→ Sind Fackeln mit Auto-Light platziert? (Material `torch`)
→ Lighting aktiviert?

**"Zu dunkel / zu hell"**
→ Ambient Intensity im Code anpassen (0.0-1.0)

**"Performance-Probleme"**
→ Weniger Lichter verwenden (<50)
→ Kleinerer Blur-Radius
→ Flicker-Lichter reduzieren

**"Licht verschwindet"**
→ Speichern nicht vergessen!
→ Lighting-Daten in JSON prüfen

**"Auto-Light funktioniert nicht"**
→ Brush-Tool aktiv? (nicht Light-Tool)
→ Material ist `torch`, `candle`, `fire`, etc.?

---

## 📋 Auto-Light Material-Liste

Folgende Materials erzeugen automatisch Lichtquellen:

| Material | Licht-Typ | Flackern | Icon |
|----------|-----------|----------|------|
| `torch` | Torch | ✅ Stark | 🔥 |
| `candle` | Candle | ✅ Sanft | 🕯️ |
| `lantern` | Candle | ✅ Sanft | 🏮 |
| `fire` | Fire | ✅ Sehr stark | 🔥 |
| `campfire` | Fire | ✅ Sehr stark | 🔥 |
| `window` | Window | ❌ Nein | 🪟 |
| `magic_circle` | Magic | ✅ Pulsierend | ✨ |
| `crystal` | Magic | ✅ Pulsierend | 💎 |

**Tipp:** Eigene Materials erweitern in `map_editor.py`:
```python
self.light_emitting_materials = {
    "dein_material": {"preset": "torch", "icon": "🔥"}
}
```

---

**Version:** 2.5D Lighting v1.1  
**Datum:** November 2025  
**Status:** ✅ Komplett funktionsfähig mit Flicker & Auto-Lights!

**Next:** Particle Systems & Shadow Casting 🚀
