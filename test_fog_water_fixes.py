"""
Test-Script: Fog & Water Fixes Demonstration
Zeigt die verbesserten Fog- und Water-Texturen an
"""

from fog_texture_generator import FogTextureGenerator
from advanced_texture_renderer import AdvancedTextureRenderer
import tkinter as tk
from PIL import ImageTk

def show_textures():
    """Zeigt Fog und Water Texturen in einem Fenster"""
    root = tk.Tk()
    root.title("Fog & Water Fixes - Test")
    root.geometry("900x400")
    
    # Generator initialisieren
    fog_gen = FogTextureGenerator()
    texture_gen = AdvancedTextureRenderer()
    
    # Frame für Textur-Anzeige
    frame = tk.Frame(root, bg='#2b2b2b')
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Water Texture
    water_label = tk.Label(frame, text="Water Texture\n(sollte BLAU sein)", 
                          bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
    water_label.grid(row=0, column=0, padx=10, pady=5)
    
    water_img = texture_gen.get_texture("water", size=256, animation_frame=0)
    water_photo = ImageTk.PhotoImage(water_img)
    water_canvas = tk.Label(frame, image=water_photo, bg='#2b2b2b')
    water_canvas.image = water_photo  # Referenz halten
    water_canvas.grid(row=1, column=0, padx=10, pady=5)
    
    # Fog Texture (Normal)
    fog_label = tk.Label(frame, text="Fog Texture\n(vollständig deckend, Alpha=255)", 
                        bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
    fog_label.grid(row=0, column=1, padx=10, pady=5)
    
    fog_img = fog_gen.get_fog_texture(size=256, fog_type='normal')
    fog_photo = ImageTk.PhotoImage(fog_img)
    fog_canvas = tk.Label(frame, image=fog_photo, bg='#2b2b2b')
    fog_canvas.image = fog_photo
    fog_canvas.grid(row=1, column=1, padx=10, pady=5)
    
    # Fog über Water (Test für Deckkraft)
    overlay_label = tk.Label(frame, text="Fog über Water\n(keine Transparenz!)", 
                            bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
    overlay_label.grid(row=0, column=2, padx=10, pady=5)
    
    # Overlay erstellen
    from PIL import Image
    overlay_img = water_img.copy()
    fog_rgba = fog_img.convert('RGBA')
    overlay_img.paste(fog_rgba, (0, 0), fog_rgba)
    
    overlay_photo = ImageTk.PhotoImage(overlay_img)
    overlay_canvas = tk.Label(frame, image=overlay_photo, bg='#2b2b2b')
    overlay_canvas.image = overlay_photo
    overlay_canvas.grid(row=1, column=2, padx=10, pady=5)
    
    # Info-Text
    info_text = """
    ✅ Water ist jetzt BLAU (nicht braun)
    ✅ Fog ist vollständig deckend (Alpha = 255)
    ✅ Fog hat weniger Punkte, mehr Blur (wolkiger)
    
    Rechtes Bild zeigt: Fog VERDECKT Water komplett
    """
    
    info_label = tk.Label(root, text=info_text, bg='#2b2b2b', fg='#90EE90', 
                         font=('Arial', 9), justify=tk.LEFT)
    info_label.pack(pady=10)
    
    # Schließen-Button
    close_btn = tk.Button(root, text="Test beenden", command=root.destroy,
                         bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                         padx=20, pady=10)
    close_btn.pack(pady=10)
    
    root.configure(bg='#2b2b2b')
    root.mainloop()

if __name__ == "__main__":
    print("Starte Fog & Water Fix Test...")
    print("Erwartete Ergebnisse:")
    print("  - Water: Klar BLAU")
    print("  - Fog: Wolkig, weich, vollständig deckend")
    print("  - Overlay: Fog verdeckt Water komplett")
    print()
    
    try:
        show_textures()
        print("\n✅ Test erfolgreich abgeschlossen!")
    except Exception as e:
        print(f"\n❌ Fehler beim Test: {e}")
        import traceback
        traceback.print_exc()
