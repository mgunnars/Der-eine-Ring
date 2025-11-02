"""
Test-Script für SVG-Projektor mit Menu
"""
import tkinter as tk
from svg_projector import SVGProjectorWindow
import os

def test_projector():
    """Testet den SVG-Projektor mit Menu"""
    
    # Hauptfenster (muss existieren für Toplevel)
    root = tk.Tk()
    root.title("SVG Projektor Test")
    root.geometry("300x200")
    
    # Info-Label
    tk.Label(root, text="SVG-Projektor Tester", 
            font=("Arial", 14, "bold")).pack(pady=20)
    
    def open_projector():
        """Öffnet SVG-Projektor"""
        svg_path = "maps/beispiel_mittelerde.svg"
        
        if not os.path.exists(svg_path):
            tk.messagebox.showerror("Fehler", f"SVG nicht gefunden:\n{svg_path}")
            return
        
        try:
            projector = SVGProjectorWindow(svg_path, fullscreen=False)
            print("✅ Projektor geöffnet")
            print("📋 Menu sollte oben im Projektor-Fenster erscheinen:")
            print("   Datei → 📂 SVG öffnen...")
            print("   Datei → ❌ Schließen")
        except Exception as e:
            print(f"❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
    
    # Button
    tk.Button(root, text="🎬 SVG Projektor öffnen",
             font=("Arial", 12, "bold"),
             bg="#2a7d7d", fg="white",
             padx=20, pady=10,
             command=open_projector).pack(pady=20)
    
    tk.Label(root, text="Nach dem Öffnen:\n"
                       "Schaue oben im Projektor-Fenster\n"
                       "nach der Menu-Leiste 'Datei'",
            font=("Arial", 9),
            fg="gray").pack(pady=10)
    
    print("=" * 60)
    print("SVG-PROJEKTOR TEST")
    print("=" * 60)
    print("\n1. Klicke auf 'SVG Projektor öffnen'")
    print("2. Schaue im PROJEKTOR-Fenster oben nach 'Datei' Menu")
    print("3. Klicke auf 'Datei' → '📂 SVG öffnen...'")
    print("\nFalls kein Menu sichtbar ist:")
    print("- Drücke Alt (manchmal versteckt Windows das Menu)")
    print("- Oder nutze diese Tastenkombinationen im Projektor:")
    print("  • F11 = Vollbild")
    print("  • +/- = Zoom")
    print("  • R = Reset")
    print("  • ESC = Schließen")
    print("=" * 60)
    
    root.mainloop()

if __name__ == "__main__":
    test_projector()
