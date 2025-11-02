"""
Start-Script mit SVG-Projektor Option
"""

import tkinter as tk
from tkinter import messagebox
import os
import sys


def show_startup_dialog():
    """Zeigt Startup-Dialog mit SVG-Option"""
    root = tk.Tk()
    root.withdraw()
    
    # Prüfe ob SVG existiert
    svg_exists = os.path.exists('maps/beispiel_mittelerde.svg')
    
    if svg_exists:
        # Dialog mit Option
        dialog = tk.Toplevel()
        dialog.title("Der Eine Ring - VTT")
        dialog.geometry("500x350")
        dialog.configure(bg="#1a1a1a")
        
        # Zentrieren
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"500x350+{x}+{y}")
        
        # Header
        tk.Label(dialog, text="🗺️ Der Eine Ring", 
                bg="#1a1a1a", fg="#d4af37",
                font=("Arial", 24, "bold")).pack(pady=20)
        
        tk.Label(dialog, text="Virtual Tabletop System", 
                bg="#1a1a1a", fg="white",
                font=("Arial", 12)).pack(pady=5)
        
        tk.Label(dialog, text="─" * 50, 
                bg="#1a1a1a", fg="#444").pack(pady=10)
        
        # Beschreibung
        info_frame = tk.Frame(dialog, bg="#1a1a1a")
        info_frame.pack(pady=20)
        
        tk.Label(info_frame, text="SVG-Karte verfügbar!", 
                bg="#1a1a1a", fg="#4a4",
                font=("Arial", 11, "bold")).pack()
        
        tk.Label(info_frame, text="Die Beispielkarte liegt als hochauflösende SVG vor.", 
                bg="#1a1a1a", fg="#888",
                font=("Arial", 9)).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="#1a1a1a")
        button_frame.pack(pady=20)
        
        def start_editor():
            dialog.destroy()
            root.destroy()
            # Editor starten
            import enhanced_main
            enhanced_main.DerEineRingProApp().mainloop()
        
        def start_svg_projector():
            dialog.destroy()
            root.destroy()
            # SVG Projektor starten
            from svg_projector import SVGProjectorWindow
            temp_root = tk.Tk()
            temp_root.withdraw()
            projector = SVGProjectorWindow('maps/beispiel_mittelerde.svg', fullscreen=False)
            
            # Info
            messagebox.showinfo("SVG Projektor", 
                "🎬 SVG Projektor gestartet!\n\n"
                "Steuerung:\n"
                "• F11: Vollbild\n"
                "• +/-: Zoom\n"
                "• R: Reset\n"
                "• G: Grid\n"
                "• ESC: Beenden")
            
            temp_root.mainloop()
        
        tk.Button(button_frame, text="🎨 Map Editor starten", 
                 bg="#2a5d8d", fg="white",
                 font=("Arial", 12, "bold"),
                 padx=20, pady=10,
                 command=start_editor).pack(pady=5)
        
        tk.Button(button_frame, text="🎬 SVG Projektor starten (High Quality)", 
                 bg="#2a7d7d", fg="white",
                 font=("Arial", 12, "bold"),
                 padx=20, pady=10,
                 command=start_svg_projector).pack(pady=5)
        
        tk.Label(dialog, text="💡 Tipp: SVG Projektor bietet verlustfreie Qualität!", 
                bg="#1a1a1a", fg="#888",
                font=("Arial", 8, "italic")).pack(side=tk.BOTTOM, pady=10)
        
        dialog.protocol("WM_DELETE_WINDOW", lambda: (dialog.destroy(), root.destroy()))
        dialog.mainloop()
        
    else:
        # Keine SVG - direkt Editor starten
        root.destroy()
        import enhanced_main
        enhanced_main.DerEineRingProApp().mainloop()


if __name__ == "__main__":
    show_startup_dialog()
