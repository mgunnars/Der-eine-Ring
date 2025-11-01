"""
Der Eine Ring PRO - Erweiterte Hauptanwendung
<<<<<<< HEAD
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
=======
Mit Editor-Modus, Projektor-Modus und VTT-Features
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
>>>>>>> 1b8b352 (Initial commit: Der Eine Ring VTT System)

class DerEineRingProApp(tk.Tk):
    def __init__(self):
        super().__init__()
<<<<<<< HEAD
        self.title("Der Eine Ring PRO")
        self.geometry("1600x900")
        self.configure(bg="#1a1a1a")
        
        ttk.Label(self, text="🗺️ Der Eine Ring", font=("Arial", 24, "bold")).pack(pady=30)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)
        ttk.Button(btn_frame, text="🎨 Editor", command=self.start_editor).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="📁 Laden", command=self.load_map).pack(side=tk.LEFT, padx=10)
    
    def start_editor(self):
        try:
            from main import MapEditor
            editor_win = tk.Toplevel(self)
            editor_win.title("Editor")
            editor_win.geometry("1400x900")
            MapEditor(editor_win).pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))
    
    def load_map(self):
        filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
=======
        self.title("Der Eine Ring PRO VTT")
        self.geometry("1920x1080")
        self.configure(bg="#1a1a1a")
        
        # Aktuell geladene Karte
        self.current_map_data = None
        self.current_editor = None
        self.projector_window = None
        self.gm_panel = None
        
        # Webcam-Tracker initialisieren
        from webcam_tracker import WebcamTracker
        self.webcam_tracker = WebcamTracker(camera_index=0)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Hauptmenü erstellen"""
        # Header
        header = tk.Frame(self, bg="#1a1a1a")
        header.pack(fill=tk.X, pady=20)
        
        title_label = tk.Label(header, text="🗺️ Der Eine Ring", 
                              font=("Arial", 32, "bold"),
                              bg="#1a1a1a", fg="#d4af37")
        title_label.pack()
        
        subtitle_label = tk.Label(header, text="Interaktiver Tabletop Kartenprojektor",
                                 font=("Arial", 12),
                                 bg="#1a1a1a", fg="#888888")
        subtitle_label.pack(pady=5)
        
        # Hauptbuttons
        button_frame = tk.Frame(self, bg="#1a1a1a")
        button_frame.pack(expand=True)
        
        buttons = [
            ("🎨 Karten-Editor", self.start_editor, "#2a7d2a"),
            ("📺 Projektor-Modus", self.start_projector, "#2a5d8d"),
            ("🎮 Gamemaster Panel", self.start_gm_panel, "#8b4513"),
            ("📁 Karte laden", self.load_map, "#7d5d2a"),
            ("📋 Karten-Liste", self.show_map_list, "#5d2a7d"),
            ("❓ Hilfe", self.show_help, "#555555"),
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(button_frame, text=text, 
                          font=("Arial", 14, "bold"),
                          bg=color, fg="white",
                          width=25, height=2,
                          cursor="hand2",
                          command=command)
            btn.pack(pady=10, padx=20)
        
        # Footer
        footer = tk.Frame(self, bg="#1a1a1a")
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        tk.Label(footer, text="Version 1.0 | Für Mittelerde-Tabletop-Spiele",
                font=("Arial", 9),
                bg="#1a1a1a", fg="#666666").pack()
    
    def start_editor(self):
        """Editor-Fenster öffnen"""
        try:
            from main import MapEditor
            
            editor_win = tk.Toplevel(self)
            editor_win.title("Map Editor - Der Eine Ring")
            editor_win.geometry("1400x900")
            editor_win.configure(bg="#1a1a1a")
            
            # MapEditor mit aktuellen Daten oder neu
            editor = MapEditor(editor_win, width=50, height=50, map_data=self.current_map_data)
            editor.pack(fill=tk.BOTH, expand=True)
            
            self.current_editor = editor
            
            # Beim Schließen Map-Daten speichern
            def on_close():
                self.current_map_data = editor.get_map_data()
                editor_win.destroy()
            
            editor_win.protocol("WM_DELETE_WINDOW", on_close)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Editor konnte nicht gestartet werden:\n{e}")
    
    def start_projector(self):
        """Projektor-Fenster öffnen"""
        try:
            from projector_window import ProjectorWindow
            
            # Wenn kein Editor läuft, aktuelle Map-Daten nutzen
            map_data = self.current_map_data
            
            # Wenn Editor läuft, dessen Daten nutzen
            if self.current_editor:
                map_data = self.current_editor.get_map_data()
            
            # Wenn keine Daten vorhanden, Standardkarte laden
            if not map_data:
                from map_system import MapSystem
                ms = MapSystem()
                map_data = ms.create_default_map()
                messagebox.showinfo("Info", "Keine Karte geladen - Zeige Beispielkarte")
            
            # Webcam-Tracker vorbereiten
            if self.webcam_tracker:
                map_width = map_data.get("width", 50)
                map_height = map_data.get("height", 50)
                self.webcam_tracker.map_size = (map_width, map_height)
            
            # Projektor öffnen
            if self.projector_window and self.projector_window.winfo_exists():
                self.projector_window.update_map(map_data)
                self.projector_window.lift()
            else:
                self.projector_window = ProjectorWindow(self, map_data, self.webcam_tracker)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Projektor konnte nicht gestartet werden:\n{e}")
    
    def start_gm_panel(self):
        """Gamemaster-Kontrollpanel öffnen"""
        try:
            from gm_controls import GamemasterControlPanel
            
            # Wenn GM-Panel schon offen, in Vordergrund holen
            if self.gm_panel and self.gm_panel.winfo_exists():
                self.gm_panel.lift()
                return
            
            # Neues Panel erstellen
            self.gm_panel = GamemasterControlPanel(self, self.projector_window, self.webcam_tracker)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"GM-Panel konnte nicht gestartet werden:\n{e}")
    
    def load_map(self):
        """Karte laden"""
        filename = filedialog.askopenfilename(
            title="Karte laden",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")],
            initialdir="maps"
        )
        
        if filename:
            try:
                from map_system import MapSystem
                ms = MapSystem()
                map_data = ms.load_map(filename)
                
                if map_data:
                    self.current_map_data = map_data
                    messagebox.showinfo("Erfolg", f"Karte geladen:\n{os.path.basename(filename)}")
                else:
                    messagebox.showerror("Fehler", "Karte konnte nicht geladen werden")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
    
    def show_map_list(self):
        """Liste aller gespeicherten Karten anzeigen"""
        try:
            from map_system import MapSystem
            ms = MapSystem()
            maps = ms.list_maps()
            
            if not maps:
                messagebox.showinfo("Keine Karten", "Noch keine Karten gespeichert.\nErstelle zuerst eine Karte im Editor!")
                return
            
            # Listenfenster erstellen
            list_win = tk.Toplevel(self)
            list_win.title("Gespeicherte Karten")
            list_win.geometry("600x400")
            list_win.configure(bg="#1a1a1a")
            
            tk.Label(list_win, text="📋 Gespeicherte Karten", 
                    font=("Arial", 16, "bold"),
                    bg="#1a1a1a", fg="white").pack(pady=10)
            
            # Listbox mit Scrollbar
            frame = tk.Frame(list_win, bg="#1a1a1a")
            frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            scrollbar = tk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                               bg="#2a2a2a", fg="white",
                               font=("Courier", 10),
                               selectmode=tk.SINGLE)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Karten einfügen
            for filename, created, size in maps:
                listbox.insert(tk.END, f"{filename:30} | {size:8} | {created[:19]}")
            
            # Buttons
            btn_frame = tk.Frame(list_win, bg="#1a1a1a")
            btn_frame.pack(pady=10)
            
            def load_selected():
                selection = listbox.curselection()
                if selection:
                    idx = selection[0]
                    filename = maps[idx][0]
                    map_data = ms.load_map(filename)
                    if map_data:
                        self.current_map_data = map_data
                        messagebox.showinfo("Erfolg", f"Karte geladen: {filename}")
                        list_win.destroy()
            
            tk.Button(btn_frame, text="📂 Laden", bg="#2a7d2a", fg="white",
                     padx=20, command=load_selected).pack(side=tk.LEFT, padx=5)
            
            tk.Button(btn_frame, text="❌ Schließen", bg="#7d2a2a", fg="white",
                     padx=20, command=list_win.destroy).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Liste:\n{e}")
    
    def show_help(self):
        """Hilfe anzeigen"""
        help_text = """
🗺️ Der Eine Ring VTT - Anleitung

📝 EDITOR-MODUS:
• Klicke auf ein Terrain (Gras, Wasser, etc.)
• Klicke oder ziehe auf der Karte zum Zeichnen
• Speichere deine Karte mit dem 💾 Button

📺 PROJEKTOR-MODUS:
• Zeigt die Karte im Vollbild
• Perfekt für einen zweiten Monitor/Beamer
• Fog-of-War System für verborgene Bereiche
• Klicke und ziehe zum Bewegen
• Mausrad zum Zoomen
• ESC zum Beenden
• F11 für Vollbild an/aus

🎮 GAMEMASTER PANEL:
• Webcam-Tracking aktivieren
• Fog-of-War manuell steuern
• Zoom und Kamera kontrollieren
• Live-Vorschau der Webcam
• Spieltisch kalibrieren

📹 WEBCAM-TRACKING:
• Webcam über dem Spieltisch montieren
• Im GM-Panel "Start Tracking" klicken
• Spieltisch kalibrieren (4 Ecken markieren)
• Hand oder Figuren bewegen - Fog lichtet sich automatisch
• Sichtweite im GM-Panel anpassen

🌫️ FOG-OF-WAR:
• Anfangs ist gesamte Karte verborgen
• Fog lichtet sich automatisch durch Spielerbewegung
• Gamemaster kann manuell Bereiche auf/zudecken
• Sichtweite anpassbar (1-10 Tiles)

💡 TIPPS:
• Erstelle Karten im Editor
• Starte Projektor für Spieler (2. Monitor/Beamer)
• Öffne GM-Panel für Kontrolle
• Aktiviere Webcam-Tracking
• Nutze manuelle Fog-Steuerung für besondere Szenen

⌨️ TASTENKÜRZEL:
• ESC - Projektor beenden
• F11 - Vollbild umschalten
"""
        
        help_win = tk.Toplevel(self)
        help_win.title("Hilfe")
        help_win.geometry("650x700")
        help_win.configure(bg="#1a1a1a")
        
        text = tk.Text(help_win, wrap=tk.WORD, 
                      bg="#2a2a2a", fg="white",
                      font=("Courier", 10),
                      padx=20, pady=20)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert("1.0", help_text)
        text.config(state=tk.DISABLED)
        
        tk.Button(help_win, text="OK", bg="#2a7d2a", fg="white",
                 padx=30, command=help_win.destroy).pack(pady=10)
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        # Webcam stoppen
        if self.webcam_tracker:
            self.webcam_tracker.stop()
        super().destroy()
>>>>>>> 1b8b352 (Initial commit: Der Eine Ring VTT System)

if __name__ == "__main__":
    DerEineRingProApp().mainloop()