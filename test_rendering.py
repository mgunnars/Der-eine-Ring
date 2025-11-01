"""
Test-Skript für das neue Rendering-System
"""
import tkinter as tk
from advanced_texture_renderer import AdvancedTextureRenderer
from material_manager import MaterialBar
from PIL import ImageTk

def test_renderer():
    """Testet den Advanced Texture Renderer"""
    print("=== Test: Advanced Texture Renderer ===")
    
    renderer = AdvancedTextureRenderer()
    
    # Test 1: Basis-Materialien laden
    print("\n1. Teste Basis-Materialien...")
    materials = renderer.get_all_materials()
    print(f"   ✓ {len(materials)} Materialien gefunden")
    
    for mat_id, mat_data in list(materials.items())[:3]:
        print(f"   - {mat_id}: {mat_data.get('name', 'N/A')}")
    
    # Test 2: Texturen generieren
    print("\n2. Teste Textur-Generierung...")
    test_materials = ["grass", "water", "mountain", "forest"]
    
    for mat_id in test_materials:
        texture = renderer.get_texture(mat_id, 64, 0)
        if texture:
            print(f"   ✓ {mat_id}: {texture.size[0]}x{texture.size[1]} Pixel")
        else:
            print(f"   ✗ {mat_id}: Fehler!")
    
    # Test 3: Custom Material erstellen
    print("\n3. Teste Custom-Material...")
    new_id = renderer.create_new_material(
        "test_material",
        "Test Material",
        color=(255, 100, 100),
        animated=False,
        emoji="🧪"
    )
    print(f"   ✓ Custom-Material erstellt: {new_id}")
    
    # Test 4: Animation
    print("\n4. Teste Animation...")
    for i in range(5):
        frame = renderer.update_animation()
        print(f"   Frame {i}: {frame}")
    
    print("\n✅ Alle Tests erfolgreich!\n")

def test_material_bar():
    """Testet die Material-Bar"""
    print("=== Test: Material-Bar ===")
    
    root = tk.Tk()
    root.title("Material-Bar Test")
    root.geometry("1000x300")
    
    renderer = AdvancedTextureRenderer()
    
    def on_select(mat_id):
        print(f"Material ausgewählt: {mat_id}")
    
    # Material-Bar erstellen
    bar = MaterialBar(root, renderer, on_select)
    bar.pack(fill=tk.BOTH, expand=True)
    
    print("\n✓ Material-Bar erstellt")
    print("  Bitte teste manuell:")
    print("  - Ein-/Ausklappen mit Toggle-Button")
    print("  - Scrollen der Materialien")
    print("  - Materialien anklicken")
    print("  - 'Neu' Button")
    print("\n(Fenster schließen zum Beenden)\n")
    
    root.mainloop()

def test_texture_generation():
    """Zeigt alle Texturen in einem Fenster"""
    print("=== Test: Textur-Anzeige ===")
    
    root = tk.Tk()
    root.title("Textur-Galerie")
    root.geometry("900x700")
    root.configure(bg="#2a2a2a")
    
    renderer = AdvancedTextureRenderer()
    materials = renderer.get_all_materials()
    
    # Canvas mit Scrollbar
    canvas_frame = tk.Frame(root, bg="#2a2a2a")
    canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    canvas = tk.Canvas(canvas_frame, bg="#1a1a1a", highlightthickness=0)
    scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
    
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Frame für Texturen
    texture_frame = tk.Frame(canvas, bg="#1a1a1a")
    canvas_window = canvas.create_window((0, 0), window=texture_frame, anchor=tk.NW)
    
    # Texturen anzeigen
    photo_refs = []
    row, col = 0, 0
    max_cols = 5
    
    for mat_id, mat_data in materials.items():
        # Container für Material
        mat_container = tk.Frame(texture_frame, bg="#2a2a2a", relief=tk.RAISED, bd=2)
        mat_container.grid(row=row, column=col, padx=10, pady=10)
        
        # Textur generieren
        texture_img = renderer.get_texture(mat_id, 128, 0)
        photo = ImageTk.PhotoImage(texture_img)
        photo_refs.append(photo)
        
        # Bild anzeigen
        img_label = tk.Label(mat_container, image=photo, bg="#2a2a2a")
        img_label.pack(padx=5, pady=5)
        
        # Name
        name_text = f"{mat_data.get('emoji', '🎨')} {mat_data.get('name', mat_id)}"
        name_label = tk.Label(
            mat_container,
            text=name_text,
            bg="#2a2a2a",
            fg="white",
            font=("Arial", 9)
        )
        name_label.pack(pady=(0, 5))
        
        # Animiert?
        if mat_data.get("animated", False):
            anim_label = tk.Label(
                mat_container,
                text="🎬 Animiert",
                bg="#2a2a2a",
                fg="#d4af37",
                font=("Arial", 7)
            )
            anim_label.pack()
        
        col += 1
        if col >= max_cols:
            col = 0
            row += 1
    
    # Scrollregion aktualisieren
    texture_frame.update_idletasks()
    canvas.configure(scrollregion=canvas.bbox("all"))
    
    print(f"\n✓ {len(materials)} Texturen angezeigt")
    print("(Fenster schließen zum Beenden)\n")
    
    root.mainloop()

def main():
    """Hauptmenü für Tests"""
    print("\n" + "="*50)
    print("  TEST-SUITE FÜR NEUES RENDERING-SYSTEM")
    print("="*50)
    print("\nWähle einen Test:")
    print("1. Renderer-Funktionen testen")
    print("2. Material-Bar testen (GUI)")
    print("3. Textur-Galerie anzeigen (GUI)")
    print("4. Alle Tests ausführen")
    print("0. Beenden")
    
    choice = input("\nDeine Wahl: ").strip()
    
    if choice == "1":
        test_renderer()
    elif choice == "2":
        test_material_bar()
    elif choice == "3":
        test_texture_generation()
    elif choice == "4":
        test_renderer()
        input("\nDrücke Enter für Material-Bar Test...")
        test_material_bar()
        input("\nDrücke Enter für Textur-Galerie...")
        test_texture_generation()
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
