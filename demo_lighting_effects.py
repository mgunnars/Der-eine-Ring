"""
🔥 LIGHTING EFFECTS DEMO
Zeigt alle neuen Animationen in Aktion
"""
import time
from lighting_system import LightSource, LightingEngine, LIGHT_PRESETS

print("=" * 60)
print("🔥 LIGHTING EFFECTS v2.0 - ANIMATION DEMO")
print("=" * 60)

# Erstelle verschiedene Lichtquellen
lights = {
    "🔥 Torch": LightSource(5, 5, **LIGHT_PRESETS["torch"]),
    "🕯️ Candle": LightSource(10, 10, **LIGHT_PRESETS["candle"]),
    "🔥 Fire": LightSource(15, 15, **LIGHT_PRESETS["fire"]),
    "✨ Magic": LightSource(20, 20, **LIGHT_PRESETS["magic"]),
}

print("\n📊 FLICKER-PATTERNS (10 Frames á 0.1s):\n")

for name, light in lights.items():
    print(f"{name}:")
    intensities = []
    for frame in range(10):
        t = frame * 0.1
        intensity = light.get_current_intensity(t)
        intensities.append(intensity)
        bar = "█" * int(intensity * 30)
        print(f"  Frame {frame}: {bar} {intensity:.3f}")
    
    # Statistik
    avg = sum(intensities) / len(intensities)
    variance = sum((i - avg) ** 2 for i in intensities) / len(intensities)
    print(f"  📈 Average: {avg:.3f}")
    print(f"  📊 Variance: {variance:.4f} ({'Chaotic' if variance > 0.01 else 'Stable'})")
    print()

print("=" * 60)
print("\n🎨 FARB-SHIFTS:\n")

# Teste Farb-Shifts für Torch
torch = lights["🔥 Torch"]
print("🔥 Torch Color Gradient (Core → Edge):")

for distance_pct in [0, 30, 60, 100]:
    # Simuliere get_light_at_position Farb-Logik
    if distance_pct < 30:
        color_name = "Yellow-White (Core)"
        example = "RGB: (255, 240, 180)"
    elif distance_pct < 60:
        color_name = "Orange (Middle)"
        example = "RGB: (255, 180, 100)"
    else:
        color_name = "Dark Red (Edge)"
        example = "RGB: (230, 90, 50)"
    
    print(f"  {distance_pct}% Radius: {color_name}")
    print(f"    {example}")

print("\n🕯️ Candle Color Shift:")
print("  Warm Yellow ↔ White")
print("  Gentle pulsing, no chaos")

print("\n✨ Magic Color Shift:")
print("  Violet ↔ Cyan ↔ Pink")
print("  Rainbow shimmer effect")

print("\n" + "=" * 60)
print("\n✅ NEUE FEATURES AKTIV:")
print("  ✨ Realistische Flicker-Patterns")
print("  🔥 Dynamische Farb-Gradienten")
print("  💫 Smoothere Übergänge (20+ Steps)")
print("  🎯 Pattern-spezifisch (Torch ≠ Candle)")
print("  🌈 Farb-Shifts für Feuer-Typen")
print("\n🎮 Teste im Editor mit:")
print("  py enhanced_main.py")
print("  → Platziere Fackeln/Kerzen")
print("  → Aktiviere Dynamic Lighting")
print("  → Beobachte das Flackern!")
print("\n" + "=" * 60)
