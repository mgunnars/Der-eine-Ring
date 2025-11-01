"""
Test und Demo für Fog/Cloud-Texturen
"""
import tkinter as tk
from PIL import ImageTk
from fog_texture_generator import FogTextureGenerator


def test_fog_textures():
    """Zeigt verschiedene Fog-Texturen in einem Fenster"""
    root = tk.Tk()
    root.title("Fog/Cloud Texture Demo")
    root.geometry("900x600")
    root.configure(bg="#1a1a1a")
    
    # Generator
    fog_gen = FogTextureGenerator()
    
    # Header
    header_frame = tk.Frame(root, bg="#0a0a0a")
    header_frame.pack(fill=tk.X, pady=(0, 20))
    
    tk.Label(
        header_frame,
        text="🌫️ Fog/Cloud Texture Generator",
        font=("Arial", 16, "bold"),
        bg="#0a0a0a",
        fg="#d4af37"
    ).pack(pady=10)
    
    tk.Label(
        header_frame,
        text="Professionelle, handgezeichnete Wolken-Texturen",
        font=("Arial", 10),
        bg="#0a0a0a",
        fg="#888888"
    ).pack()
    
    # Container für Texturen
    texture_frame = tk.Frame(root, bg="#1a1a1a")
    texture_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    # Verschiedene Größen und Typen testen
    test_configs = [
        ("Normal - 64px", 64, "normal"),
        ("Normal - 128px", 128, "normal"),
        ("Normal - 256px", 256, "normal"),
        ("Dense - 128px", 128, "dense"),
        ("Light - 128px", 128, "light"),
    ]
    
    photo_refs = []
    
    for idx, (label, size, fog_type) in enumerate(test_configs):
        # Container für diese Textur
        container = tk.Frame(texture_frame, bg="#2a2a2a", relief=tk.RAISED, bd=2)
        container.grid(row=idx // 3, column=idx % 3, padx=10, pady=10, sticky=tk.NSEW)
        
        # Label
        tk.Label(
            container,
            text=label,
            bg="#2a2a2a",
            fg="white",
            font=("Arial", 10, "bold")
        ).pack(pady=5)
        
        # Textur generieren
        fog_texture = fog_gen.get_fog_texture(size, fog_type)
        
        # Als PhotoImage
        photo = ImageTk.PhotoImage(fog_texture)
        photo_refs.append(photo)
        
        # Anzeigen
        img_label = tk.Label(container, image=photo, bg="#2a2a2a")
        img_label.pack(padx=5, pady=5)
        
        # Info
        info_text = f"{fog_texture.size[0]}×{fog_texture.size[1]} px"
        tk.Label(
            container,
            text=info_text,
            bg="#2a2a2a",
            fg="#888888",
            font=("Arial", 8)
        ).pack(pady=(0, 5))
    
    # Info-Text unten
    info_frame = tk.Frame(root, bg="#0a0a0a")
    info_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
    
    info_text = """
    ✅ Fog-Texturen werden gecached (wiederverwendet)
    ✅ Verhindert "Fail to allocate bitmap" Fehler
    ✅ Organische Wolkenstruktur mit Punktierung
    ✅ Handgezeichneter Look wie im Referenzbild
    """
    
    tk.Label(
        info_frame,
        text=info_text,
        bg="#0a0a0a",
        fg="#888888",
        font=("Arial", 9),
        justify=tk.LEFT
    ).pack(padx=20, pady=10)
    
    # Grid konfigurieren
    for i in range(3):
        texture_frame.columnconfigure(i, weight=1)
    for i in range(2):
        texture_frame.rowconfigure(i, weight=1)
    
    print("\n" + "="*50)
    print("  FOG TEXTURE DEMO")
    print("="*50)
    print(f"\n✓ {len(test_configs)} Texturen generiert")
    print("✓ Alle Texturen gecached")
    print("✓ Memory-effizient durch Wiederverwendung")
    print("\nFenster schließen zum Beenden\n")
    
    root.mainloop()


def test_animated_fog():
    """Zeigt animierte Fog-Textur"""
    root = tk.Tk()
    root.title("Animated Fog Demo")
    root.geometry("400x450")
    root.configure(bg="#1a1a1a")
    
    # Generator
    fog_gen = FogTextureGenerator()
    
    # Header
    tk.Label(
        root,
        text="🌫️ Animierte Fog-Textur",
        font=("Arial", 14, "bold"),
        bg="#1a1a1a",
        fg="#d4af37"
    ).pack(pady=10)
    
    # Canvas für Animation
    canvas_size = 256
    canvas_frame = tk.Frame(root, bg="#2a2a2a", relief=tk.SUNKEN, bd=2)
    canvas_frame.pack(padx=20, pady=10)
    
    canvas = tk.Canvas(canvas_frame, width=canvas_size, height=canvas_size, 
                      bg="#000000", highlightthickness=0)
    canvas.pack(padx=2, pady=2)
    
    # Frame-Counter
    frame_var = tk.StringVar(value="Frame: 0")
    tk.Label(root, textvariable=frame_var, bg="#1a1a1a", fg="white",
            font=("Arial", 10)).pack(pady=5)
    
    # Animation-State
    frame_counter = [0]
    photo_ref = [None]
    is_running = [True]
    
    def animate():
        if not is_running[0]:
            return
        
        # Generiere Frame
        fog_texture = fog_gen.generate_animated_fog_frame(canvas_size, frame_counter[0])
        photo = ImageTk.PhotoImage(fog_texture)
        photo_ref[0] = photo
        
        # Zeichne
        canvas.delete("all")
        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
        
        # Update Frame-Counter
        frame_counter[0] = (frame_counter[0] + 1) % 100
        frame_var.set(f"Frame: {frame_counter[0]}")
        
        # Nächster Frame nach 50ms (20 FPS)
        root.after(50, animate)
    
    # Start/Stop Button
    def toggle_animation():
        is_running[0] = not is_running[0]
        btn_text = "⏸️ Pause" if is_running[0] else "▶️ Start"
        toggle_btn.config(text=btn_text)
        if is_running[0]:
            animate()
    
    toggle_btn = tk.Button(
        root,
        text="⏸️ Pause",
        bg="#2a7d2a",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=20,
        pady=5,
        command=toggle_animation
    )
    toggle_btn.pack(pady=10)
    
    # Info
    tk.Label(
        root,
        text="Nebel bewegt sich sanft wie echte Wolken",
        bg="#1a1a1a",
        fg="#888888",
        font=("Arial", 9)
    ).pack(pady=5)
    
    # Animation starten
    animate()
    
    print("\n✓ Animierte Fog-Textur gestartet")
    print("  Wolken bewegen sich organisch")
    print("\nFenster schließen zum Beenden\n")
    
    root.mainloop()


def main():
    """Hauptmenü"""
    print("\n" + "="*50)
    print("  FOG/CLOUD TEXTURE TEST")
    print("="*50)
    print("\nWähle einen Test:")
    print("1. Verschiedene Fog-Texturen anzeigen")
    print("2. Animierte Fog-Textur")
    print("0. Beenden")
    
    choice = input("\nDeine Wahl: ").strip()
    
    if choice == "1":
        test_fog_textures()
    elif choice == "2":
        test_animated_fog()
    elif choice == "0":
        print("\nTschüss! 👋\n")
    else:
        print("\n❌ Ungültige Wahl!\n")
        main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest abgebrochen! 👋\n")
    except Exception as e:
        print(f"\n❌ FEHLER: {e}\n")
        import traceback
        traceback.print_exc()
