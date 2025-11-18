"""
ERWEITERTE LIGHTING-EFFEKTE v2.0
Realistische Animationen für Feuer, Fackeln, Kerzen, Magie

NEUE FEATURES:
✨ Verschiedene Flicker-Patterns (Fackel ≠ Kerze ≠ Feuer)
🔥 Dynamischer Farb-Shift (Orange → Gelb → Rot)
💫 Sanfte Gradienten mit mehr Details
🌊 Basis für Wasser-Animation (kommt in v2.1)
"""

# ========== FLICKER-PATTERNS ==========

# 1. TORCH (Fackel) - Starkes, chaotisches Flackern
"""
Kombination aus:
- Langsamer Basis-Welle (0.8 Hz)
- Schnellen Zuckungen (5 Hz)
- Zufälligem Chaos (±10%)
- Gelegentlichen "Aussetzern" (5% Chance auf -20%)

Ergebnis: Lebhaftes, unvorhersehbares Flackern wie echte Fackel
"""

# 2. CANDLE (Kerze) - Sanftes, elegantes Flackern
"""
Kombination aus:
- Langsamer Basis-Welle (1.2 Hz)
- Sanfte Oberwelle (3 Hz)
- Minimales Chaos (±3%)

Ergebnis: Ruhiges, gleichmäßiges Tanzen wie Kerzenflamme
"""

# 3. FIRE/CAMPFIRE (Feuer) - Wie Fackel aber extremer
"""
Gleich wie Torch, aber:
- Mehr Chaos
- Größere Amplituden
- Häufigere Aussetzer

Ergebnis: Wildes, gefährliches Flackern
"""

# 4. MAGIC (Magie) - Langsames Pulsieren
"""
Kombination aus:
- Sehr langsame Welle (0.6 Hz) = "Atmen"
- Schnelles Schimmern (4 Hz)
- Kein Chaos (mystisch stabil)

Ergebnis: Übernatürliches, gleichmäßiges Glühen
"""

# ========== FARB-SHIFTS ==========

# FEUER-GRADIENT (Torch/Fire/Campfire):
"""
Kern (0-30% Radius): Helles Gelb-Weiß
  RGB: (255, 240, 180) - Heißeste Stelle
  
Mitte (30-60%): Orange
  RGB: (255, 180, 100) - Standard-Flammenfarbe
  
Außen (60-100%): Dunkles Rot
  RGB: (230, 90, 50) - Glühende Ränder

+ Zufällige Funken (1% Chance): +50 R, +30 G
"""

# KERZEN-GRADIENT:
"""
Warmth-Pulsieren:
- Sin-Wave auf Gelb-Kanal
- Sanfter Übergang Weiß ↔ Gelb
- Kein Rot-Shift (zu stabil)
"""

# MAGIE-GRADIENT:
"""
Regenbogen-Shift:
- Alle Kanäle pulsieren
- Violett ↔ Cyan ↔ Pink
- Übernatürlicher Look
"""

# ========== PERFORMANCE ==========
"""
OPTIMIERT:
- Gradienten: 20-40 Steps (statt 5)
- Smoothere Übergänge
- Besseres Blending

FPS-TARGET:
- 30 FPS für Flicker (statt 60)
- Nur neu rendern wenn Flicker aktiv
- Smart Caching möglich
"""

# ========== NÄCHSTE FEATURES (v2.1) ==========
"""
🌊 WASSER-ANIMATION:
- Ähnliches System wie Lighting
- Fließ-Richtung gespeichert in Tiles
- Sinus-Wellen für Bewegung
- Reflexionen von Licht

🎆 PARTIKEL-SYSTEM:
- Funken von Fackeln
- Rauch aufsteigend
- Magische Glitzer-Effekte

☁️ FOG-OF-WAR MIT LIGHTING:
- Dunkle Bereiche = Unexplored
- Licht enthüllt Karte
- Dynamische Sichtweite
"""

print("📖 Lighting Effects Documentation loaded!")
