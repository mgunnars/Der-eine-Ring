"""
Generiert Wetter-Overlay GIFs für den Projektor
Führe dieses Script aus um rain.gif, snow.gif, etc. zu erstellen
"""

import os
import sys

# Füge Projektordner zu Path hinzu
sys.path.insert(0, os.path.dirname(__file__))

from particle_system_2d import ParticleSystem2D, Renderer2D
from PIL import Image

def generate_weather_gif(output_path: str, weather_type: str = "rain", 
                         width: int = 400, height: int = 400,
                         duration: float = 3.0, fps: int = 15):
    """Generiere ein Wetter-Overlay GIF"""
    
    print(f"🌧️ Generiere {weather_type} GIF...")
    
    system = ParticleSystem2D(width, height)
    renderer = Renderer2D(width, height)
    
    # Kein Wasser-Surface für Overlay (nur Partikel!)
    system.water_surface = None
    
    # Wetter-Typ konfigurieren
    if weather_type == "rain":
        system.set_camera_angle(70)  # Fast seitlich für vertikale Striche
        emitter = system.add_rain_emitter(intensity=0.8)
        emitter.start_color.a = 0.4
        emitter.end_color.a = 0.2
        
    elif weather_type == "snow":
        system.set_camera_angle(30)
        system.add_snow_emitter(intensity=0.6, wind_strength=30)
        
    elif weather_type == "storm":
        system.set_camera_angle(60)
        emitter = system.add_rain_emitter(intensity=1.5)
        emitter.start_color.a = 0.5
        system.set_global_wind(250, 80)  # Starker Wind
        
    elif weather_type == "leaves":
        system.set_camera_angle(30)
        system.add_leaves_emitter(intensity=0.5, wind_strength=50)
        
    elif weather_type == "dust":
        system.set_camera_angle(30)
        system.add_dust_emitter(intensity=0.6, wind_strength=40)
    
    else:
        print(f"⚠️ Unbekannter Wetter-Typ: {weather_type}")
        return
    
    # Warmup - lass Partikel sich verteilen
    for _ in range(60):
        system.update(1/30)
    
    # Frames generieren
    frames = []
    total_frames = int(duration * fps)
    dt = 1.0 / fps
    
    for i in range(total_frames):
        system.update(dt)
        frame = renderer.render(system)
        img = Image.fromarray(frame, 'RGBA')
        frames.append(img)
        
        if (i + 1) % 10 == 0:
            print(f"  Frame {i+1}/{total_frames}")
    
    # Als GIF speichern
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / fps),
        loop=0,
        disposal=2
    )
    
    print(f"✅ Gespeichert: {output_path} ({total_frames} Frames)")


def main():
    output_folder = os.path.join(os.path.dirname(__file__), "weather_overlays")
    os.makedirs(output_folder, exist_ok=True)
    
    print("=" * 50)
    print("🌤️ Wetter-Overlay Generator")
    print("=" * 50)
    
    # Generiere alle Standard-Wetter
    weather_types = ["rain", "snow", "storm", "leaves", "dust"]
    
    for weather in weather_types:
        output_path = os.path.join(output_folder, f"{weather}.gif")
        generate_weather_gif(output_path, weather)
        print()
    
    print("=" * 50)
    print("✅ Alle Wetter-Overlays generiert!")
    print(f"📁 Ordner: {output_folder}")
    print()
    print("Nutze im Projektor:")
    print("  - Taste 'W' oder Button 🌧️ für Wetter-Dialog")
    print("  - Wähle ein Wetter oder aktiviere Zufalls-Modus")
    print("=" * 50)


if __name__ == "__main__":
    main()
