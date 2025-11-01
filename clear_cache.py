"""
Cache Cleaner - Löscht alle Texture-Caches
Verwende dies nach Änderungen an den Texture-Generatoren
"""

import os
import sys

# Füge das Projekt-Verzeichnis zum Python-Path hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def clear_all_caches():
    """Löscht alle Texture- und Fog-Caches"""
    
    print("🧹 Lösche alle Texture-Caches...")
    
    try:
        # TextureManager Cache leeren
        from texture_manager import TextureManager
        tm = TextureManager()
        tm.clear_cache()
        print("✅ TextureManager Cache gelöscht")
    except Exception as e:
        print(f"⚠️ TextureManager Cache: {e}")
    
    try:
        # AdvancedTextureRenderer Cache leeren
        from advanced_texture_renderer import AdvancedTextureRenderer
        atr = AdvancedTextureRenderer()
        atr.texture_cache.clear()
        print("✅ AdvancedTextureRenderer Cache gelöscht")
    except Exception as e:
        print(f"⚠️ AdvancedTextureRenderer Cache: {e}")
    
    try:
        # FogTextureGenerator Cache leeren
        from fog_texture_generator import FogTextureGenerator
        ftg = FogTextureGenerator()
        ftg.clear_cache()
        print("✅ FogTextureGenerator Cache gelöscht")
    except Exception as e:
        print(f"⚠️ FogTextureGenerator Cache: {e}")
    
    print("\n✨ Alle Caches wurden geleert!")
    print("   Beim nächsten Start werden alle Texturen neu generiert.")
    print("   Das Wasser sollte jetzt BLAU sein! 💙")

if __name__ == "__main__":
    clear_all_caches()
    print("\n✅ Fertig! Starte die Anwendung neu für blaues Wasser.")
