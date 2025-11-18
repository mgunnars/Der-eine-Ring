# 🌊 WASSER-ANIMATION - Planung v2.1

## 💡 Konzept

Ähnlich wie Lighting-System, aber für Wasser-Bewegung:
- **Fließrichtung** gespeichert in Tiles
- **Sinus-Wellen** für Wellen-Bewegung
- **Reflexionen** von Lichtquellen
- **Real-time Animation** mit 30 FPS

---

## 🎯 Wie es funktionieren würde:

### 1. **Wasser-Tiles erweitern**
```python
# In map_data speichern:
"water_flow": {
    "(x, y)": {
        "direction": "east",  # north/south/east/west
        "speed": 1.0,         # 0.5 = langsam, 2.0 = schnell
        "wave_offset": 0.0    # Für Animation
    }
}
```

### 2. **WaterAnimationEngine** (wie LightingEngine)
```python
class WaterAnimationEngine:
    def __init__(self):
        self.water_tiles = {}
        self.time_offset = 0.0
    
    def update_animation(self, dt: float):
        self.time_offset += dt
        
        for tile, data in self.water_tiles.items():
            # Berechne Wellen-Offset
            wave = math.sin(self.time_offset * data["speed"]) * 2.0
            data["wave_offset"] = wave
    
    def render_water(self, canvas, tile_size):
        for (x, y), data in self.water_tiles.items():
            # Zeichne Wasser mit Offset
            offset_x = 0
            offset_y = 0
            
            if data["direction"] == "east":
                offset_x = int(data["wave_offset"])
            elif data["direction"] == "south":
                offset_y = int(data["wave_offset"])
            
            # Texture mit Offset zeichnen
            self.draw_water_tile(x, y, offset_x, offset_y)
```

### 3. **Reflexionen von Licht**
```python
# Wenn Lichtquelle über Wasser:
if tile_type == "water":
    # Spiegele Licht nach unten
    mirror_light = LightSource(
        x=light.x,
        y=light.y + 1,  # Etwas versetzt
        color=(light.color[0] * 0.7, 
               light.color[1] * 0.7,
               light.color[2] * 1.2),  # Mehr Blau
        intensity=light.intensity * 0.5  # Schwächer
    )
```

### 4. **Wellen-Effekt**
```python
def generate_water_texture_animated(self, size, time_offset):
    """Animierte Wasser-Textur"""
    img = Image.new('RGB', (size, size), (93, 173, 226))
    draw = ImageDraw.Draw(img)
    
    # Sinus-Wellen zeichnen
    for y in range(0, size, 2):
        wave = math.sin(y * 0.3 + time_offset * 2.0) * 3
        
        for x in range(0, size, 4):
            offset_x = x + int(wave)
            
            # Hellere Wellen-Kämme
            brightness = 120 + int(wave * 10)
            color = (brightness, 190, 255)
            
            draw.line([(offset_x, y), (offset_x + 2, y)], 
                     fill=color, width=1)
    
    return img
```

---

## 🎨 Features die möglich wären:

### ✅ Basic:
- **Fließrichtung:** Pfeile im Editor setzen
- **Wellen-Animation:** Sinus-basiert
- **Speed-Control:** Langsam (See) vs. Schnell (Fluss)

### ✨ Advanced:
- **Licht-Reflexionen:** Fackeln spiegeln sich im Wasser
- **Strömungs-Linien:** Animierte Streifen zeigen Richtung
- **Schaumkronen:** Bei schnellem Wasser

### 🔥 Expert:
- **Partikel:** Tropfen spritzen
- **Nebel:** Über kaltem Wasser
- **Schatten:** Objekte werfen Schatten auf Wasser

---

## 🛠️ Integration in Editor:

### Neue UI-Elemente:
```
🌊 WATER TOOLS
[ ] Fließrichtung setzen (↑↓←→)
[Slider] Speed: ━━●━━━ (1.0)
[✓] Wave Animation
[✓] Light Reflections
```

### Shortcuts:
- **`W`** = Water Flow Tool
- **`Arrow Keys`** = Set direction
- **`+/-`** = Speed ändern

---

## 📋 Implementierungs-Reihenfolge:

1. ✅ **Lighting System** (DONE!)
2. 🔄 **Wasser-Richtungen** speichern (nächstes)
3. 🌊 **Basic Animation** (Sinus-Wellen)
4. 💡 **Licht-Reflexionen**
5. ✨ **Advanced Effects** (Schaum, Nebel)

---

## 🎮 Wie es aussehen würde:

```
🏞️ BEISPIEL: Fluss-Szene
═════════════════════════════════════

         🌲    🌲
         
   🔥 ← Fackel
   
   ≈≈≈≈≈≈≈≈  ← Wasser fließt →→→
   ≈≈≈≈≈≈≈≈     (mit Wellen)
   ≈≈≈≈≈≈≈≈     (Fackel spiegelt!)
   
         🌲    🌲
```

---

## 💾 Map-Format erweitert:

```json
{
  "tiles": [...],
  "lighting": {...},
  "water_animation": {
    "enabled": true,
    "tiles": [
      {
        "x": 10,
        "y": 15,
        "direction": "east",
        "speed": 1.5,
        "type": "river"
      }
    ],
    "reflections_enabled": true
  }
}
```

---

## 🚀 Performance:

- **Animation:** 30 FPS (wie Lighting)
- **Nur bei sichtbaren Tiles:** Culling außerhalb Screen
- **Cached Textures:** Wellen-Frames vorbereiten
- **Smart Update:** Nur wenn Wasser sichtbar

---

**Status:** 📋 Geplant für v2.1  
**Komplexität:** ⭐⭐⭐ (Medium - ähnlich wie Lighting)  
**Voraussetzung:** ✅ Lighting System (bereits fertig!)

**Willst du dass ich das jetzt implementiere?** 🌊
