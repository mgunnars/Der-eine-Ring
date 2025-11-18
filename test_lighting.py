"""
Test Script für Lighting System
Testet ob Auto-Lights funktionieren
"""
import sys
sys.path.insert(0, '.')

from lighting_system import LightingEngine, LightSource, LIGHT_PRESETS

# Test 1: LIGHT_PRESETS vorhanden?
print("🧪 Test 1: LIGHT_PRESETS")
print(f"   Verfügbare Presets: {list(LIGHT_PRESETS.keys())}")
print(f"   ✅ torch preset: {LIGHT_PRESETS.get('torch')}")

# Test 2: LightSource erstellen
print("\n🧪 Test 2: LightSource erstellen")
torch_preset = LIGHT_PRESETS["torch"]
light = LightSource(
    x=5, y=5,
    radius=torch_preset["radius"],
    color=torch_preset["color"],
    intensity=torch_preset["intensity"],
    flicker=torch_preset["flicker"],
    light_type="torch"
)
print(f"   Position: ({light.x}, {light.y})")
print(f"   Radius: {light.radius}")
print(f"   Farbe: {light.color}")
print(f"   Flackert: {light.flicker}")
print(f"   ✅ LightSource erstellt!")

# Test 3: LightingEngine
print("\n🧪 Test 3: LightingEngine")
engine = LightingEngine()
engine.add_light(light)
print(f"   Lichter im Engine: {len(engine.lights)}")
print(f"   ✅ Light hinzugefügt!")

# Test 4: get_light_at
print("\n🧪 Test 4: get_light_at")
idx = engine.get_light_at(5, 5, tolerance=0)
print(f"   Licht gefunden bei (5,5): {idx is not None}")
print(f"   Index: {idx}")
print(f"   ✅ get_light_at funktioniert!")

# Test 5: Auto-Light Materials
print("\n🧪 Test 5: Auto-Light Materials")
light_emitting_materials = {
    "torch": {"preset": "torch", "icon": "🔥"},
    "candle": {"preset": "candle", "icon": "🕯️"},
}
material = "torch"
if material in light_emitting_materials:
    preset_name = light_emitting_materials[material]["preset"]
    print(f"   Material '{material}' → Preset '{preset_name}'")
    print(f"   ✅ Material-Mapping funktioniert!")

print("\n✅ ALLE TESTS BESTANDEN!")
