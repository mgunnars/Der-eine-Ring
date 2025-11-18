# 🔥 LIGHTING BUGFIX v1.1

## ✅ Was wurde gefixt:

### 1. **Auto-Lights funktionieren jetzt!**
- Fackeln/Kerzen erzeugen automatisch Lichtquellen beim Platzieren
- Funktioniert auch beim Brush-Drag
- Licht verschwindet automatisch wenn Material übermalt wird

### 2. **Lighting Objects Bundle wird automatisch geladen**
- `always_loaded: true` in `lighting_objects.json`
- Bundle Manager aktiviert alle `always_loaded` Bundles beim Start
- Du siehst jetzt "🔥 Lighting Objects" in der Sidebar!

### 3. **Performance verbessert**
- Flicker-Animation läuft mit 30 FPS statt 60 FPS (spart CPU)
- Duplikate in Animation-Loop entfernt

---

## 🎮 SO TESTEST DU ES:

```powershell
py .\enhanced_main.py
```

### Schritt-für-Schritt:

1. **Map Editor öffnen** (SVG-Map laden oder neue Map)

2. **Rechte Sidebar → Scrolle nach unten**
   - Du solltest jetzt sehen: **"🔥 Lighting Objects"**
   
3. **Klicke auf "torch"** 🔥
   - Material sollte ausgewählt sein

4. **Brush-Tool prüfen:**
   - Oben sollte Pinsel-Icon aktiv sein
   - Falls nicht: Drücke `B` oder klicke Pinsel-Icon

5. **Auf Map klicken:**
   - Klicke irgendwo auf Map
   - Du solltest oranges Fackel-Icon sehen

6. **Lighting aktivieren:**
   - Rechts oben: Checkbox **"💡 Dynamic Lighting"** ✓
   - Map wird dunkler
   - Fackel sollte jetzt LEUCHTEN! 🔥✨

7. **Mehr Fackeln platzieren:**
   - Klicke weitere Positionen
   - Jede Fackel leuchtet
   - Sie sollten **flackern**!

---

## 🐛 Falls es IMMER NOCH nicht geht:

### Problem 1: "Ich sehe kein Lighting Objects Bundle"

**Debug:**
```powershell
py
>>> from material_bundle_manager import MaterialBundleManager
>>> mbm = MaterialBundleManager()
>>> print(mbm.bundles.keys())
>>> print(mbm.active_bundles)
>>> exit()
```

**Sollte zeigen:**
- `'lighting_objects'` in bundles
- `'lighting_objects'` in active_bundles

**Falls nicht:**
- Prüfe ob `material_bundles/lighting_objects.json` existiert
- Inhalt prüfen: `"always_loaded": true`

---

### Problem 2: "Materials platzieren geht nicht"

**Debug in Console:**
- Schau nach Print-Messages:
  - `"💡 Auto-Light platziert: torch bei (x,y)"`
  
**Falls keine Messages:**
- Brush-Tool aktiv? (Pinsel-Icon oben)
- Material wirklich "torch"? (nicht "grass" etc.)

---

### Problem 3: "Lighting zeigt nichts"

**Debug:**
```powershell
py
>>> from lighting_system import LightingEngine
>>> engine = LightingEngine()
>>> print(len(engine.lights))  # Sollte 0 sein
>>> from lighting_system import LIGHT_PRESETS
>>> print(LIGHT_PRESETS.keys())  # Sollte ['torch', 'candle', ...] zeigen
>>> exit()
```

**Checke:**
- Checkbox "💡 Dynamic Lighting" aktiviert?
- Mindestens 1 Fackel platziert?

---

## 📋 Erwartetes Verhalten:

1. ✅ Lighting Objects Bundle in Sidebar sichtbar
2. ✅ "torch" Material auswählbar
3. ✅ Klick platziert orange Fackel-Texture
4. ✅ Console zeigt: `"💡 Auto-Light platziert: torch bei (x,y)"`
5. ✅ Lighting aktivieren → Map wird dunkel
6. ✅ Fackel leuchtet mit warmem Orange-Glow
7. ✅ Fackel flackert sanft (Animation)
8. ✅ Mehrere Fackeln = mehrere Lichtquellen

---

## 🔧 Debugging Commands:

Wenn gar nichts geht, teste einzelne Komponenten:

```powershell
# Test 1: Lighting System
py test_lighting.py

# Test 2: Bundle Manager
py
>>> from material_bundle_manager import MaterialBundleManager
>>> mbm = MaterialBundleManager()
>>> print(f"Bundles: {list(mbm.bundles.keys())}")
>>> print(f"Active: {mbm.active_bundles}")
>>> print(f"Materials: {mbm.get_active_materials()}")
>>> exit()

# Test 3: Texture Manager
py
>>> from texture_manager import TextureManager
>>> tm = TextureManager()
>>> tex = tm.get_texture("torch", 64)
>>> print(f"Texture size: {tex.size}")
>>> tex.show()  # Sollte Fackel-Bild zeigen
>>> exit()
```

---

**Version:** Lighting Bugfix v1.1  
**Datum:** November 17, 2025  
**Status:** ✅ Sollte jetzt funktionieren!
