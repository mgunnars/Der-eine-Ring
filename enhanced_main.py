"""
Der Eine Ring PRO - Erweiterte Hauptanwendung
Mit Editor-Modus, Projektor-Modus und VTT-Features
Unterstützt JSON-Maps und SVG-Maps
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

class DerEineRingProApp(tk.Tk):
    def __init__(self):
        super().__init__()
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
            ("�️ PNG-Karte importieren", self.import_png_map, "#2a7d7d"),
            ("�📋 Karten-Liste", self.show_map_list, "#5d2a7d"),
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
            from map_editor import MapEditor
            
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
        """Projektor-Fenster öffnen - unterstützt JSON und SVG"""
        try:
            from projector_window import ProjectorWindow
            
            # Prüfe ob eine SVG-Datei geladen wurde
            if hasattr(self, 'loaded_svg_path') and self.loaded_svg_path:
                # SVG-Modus: Öffne Projektor mit SVG
                if self.projector_window and self.projector_window.winfo_exists():
                    self.projector_window.destroy()
                
                self.projector_window = ProjectorWindow(self, svg_path=self.loaded_svg_path, webcam_tracker=self.webcam_tracker)
                return
            
            # JSON-Modus: Normale Tile-basierte Map
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
        """Karte laden - unterstützt JSON und SVG"""
        filename = filedialog.askopenfilename(
            title="Karte laden",
            filetypes=[("Alle Dateien", "*.*"), ("JSON Dateien", "*.json"), ("SVG Dateien", "*.svg")],
            initialdir="maps"
        )
        
        if filename:
            # SVG? → Merke Pfad und öffne im Projektor
            if filename.lower().endswith('.svg'):
                self.loaded_svg_path = filename
                messagebox.showinfo("SVG geladen", 
                    f"✅ SVG-Karte geladen!\n\n"
                    f"Datei: {os.path.basename(filename)}\n\n"
                    f"Öffne nun '📺 Projektor-Modus' um die SVG anzuzeigen.\n\n"
                    f"Steuerung:\n"
                    f"• Mausrad: Zoom\n"
                    f"• Drag: Pan\n"
                    f"• F11: Vollbild\n"
                    f"• F: Fog of War\n"
                    f"• ESC: Beenden")
                return
            
            # JSON → Lade als normale Karte
            try:
                from map_system import MapSystem
                ms = MapSystem()
                map_data = ms.load_map(filename)
                
                if map_data:
                    self.current_map_data = map_data
                    self.loaded_svg_path = None  # Reset SVG-Modus
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
                    
                    # SVG? → Merke Pfad für Projektor
                    if filename.lower().endswith('.svg'):
                        self.loaded_svg_path = os.path.join('maps', filename)
                        messagebox.showinfo("SVG geladen", 
                            f"✅ {filename} geladen!\n\n"
                            f"Öffne nun '📺 Projektor-Modus'")
                        list_win.destroy()
                        return
                    
                    # JSON → Lade als normale Karte
                    map_data = ms.load_map(filename)
                    if map_data:
                        self.current_map_data = map_data
                        self.loaded_svg_path = None  # Reset SVG-Modus
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
    
    def import_png_map(self):
        """PNG-Karte importieren mit Dialog"""
        # PNG-Datei auswählen
        png_path = filedialog.askopenfilename(
            title="PNG-Karte auswählen",
            filetypes=[("PNG Bilder", "*.png"), ("Alle Dateien", "*.*")]
        )
        
        if not png_path:
            return
        
        # Import-Dialog erstellen
        dialog = tk.Toplevel(self)
        dialog.title("PNG-Karte importieren")
        dialog.geometry("750x700")
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Canvas + Scrollbar für scrollbaren Inhalt
        main_canvas = tk.Canvas(dialog, bg="#1a1a1a", highlightthickness=0)
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg="#1a1a1a")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mausrad-Scrolling
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Header (in scrollable_frame)
        tk.Label(scrollable_frame, text="🖼️ PNG-Karte importieren",
                font=("Arial", 18, "bold"),
                bg="#1a1a1a", fg="#d4af37").pack(pady=10)
        
        # Dateiinfo
        info_frame = tk.LabelFrame(scrollable_frame, text="Datei-Info", 
                                  bg="#2a2a2a", fg="white", 
                                  font=("Arial", 10, "bold"))
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(info_frame, text=f"📁 {os.path.basename(png_path)}",
                bg="#2a2a2a", fg="white", 
                font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=5)
        
        # Bild laden für Info
        from PIL import Image, ImageTk
        img = Image.open(png_path)
        img_w, img_h = img.size
        
        tk.Label(info_frame, text=f"📐 Größe: {img_w} x {img_h} Pixel",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=2)
        
        # AUTOMATISCHE EMPFEHLUNG basierend auf PNG-Größe
        max_dimension = max(img_w, img_h)
        recommended_tile_size = 64  # Default
        
        if max_dimension > 4000:
            recommended_tile_size = 256
            recommendation = "🔥 Sehr groß! Empfehlung: 256px Tiles"
            rec_color = "#ff6666"
        elif max_dimension > 3000:
            recommended_tile_size = 192
            recommendation = "⚠️ Groß! Empfehlung: 192px Tiles"
            rec_color = "#ffaa00"
        elif max_dimension > 2000:
            recommended_tile_size = 128
            recommendation = "⚠️ Mittel-groß! Empfehlung: 128px Tiles"
            rec_color = "#ffcc00"
        else:
            recommendation = "✅ Normale Größe - 64px Tiles OK"
            rec_color = "#44ff44"
        
        tk.Label(info_frame, text=recommendation,
                bg="#2a2a2a", fg=rec_color,
                font=("Arial", 9, "bold")).pack(anchor=tk.W, padx=10, pady=2)
        
        # Import-Optionen
        options_frame = tk.LabelFrame(scrollable_frame, text="Import-Optionen",
                                     bg="#2a2a2a", fg="white",
                                     font=("Arial", 10, "bold"))
        options_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Import-Modus
        mode_frame = tk.Frame(options_frame, bg="#2a2a2a")
        mode_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(mode_frame, text="Import-Modus:",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        import_mode = tk.StringVar(value="grid")
        
        tk.Radiobutton(mode_frame, text="🔲 Grid-Modus (PNG in Tiles aufteilen)",
                      variable=import_mode, value="grid",
                      bg="#2a2a2a", fg="white", selectcolor="#1a1a1a",
                      font=("Arial", 9)).pack(anchor=tk.W, padx=20, pady=2)
        
        tk.Radiobutton(mode_frame, text="🖼️ Single-Modus (PNG als eine Textur) ⭐ FÜR GROSSE BILDER",
                      variable=import_mode, value="single",
                      bg="#2a2a2a", fg="white", selectcolor="#1a1a1a",
                      font=("Arial", 9)).pack(anchor=tk.W, padx=20, pady=2)
        
        # Hilfe-Text
        tk.Label(mode_frame, 
                text="💡 Bei großen Bildern (>2000px) nutze Single-Modus!",
                bg="#2a2a2a", fg="#ffaa66", font=("Arial", 8, "italic")).pack(anchor=tk.W, padx=20, pady=2)
        
        # Tile-Größe (nur für Grid-Modus)
        tile_frame = tk.Frame(options_frame, bg="#2a2a2a")
        tile_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(tile_frame, text="Tile-Größe (Grid-Modus):",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # Nutze empfohlene Tile-Größe als Default
        tile_size_var = tk.IntVar(value=recommended_tile_size)
        
        tile_size_frame = tk.Frame(tile_frame, bg="#2a2a2a")
        tile_size_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # Verbesserter Slider mit Markierungen
        slider = tk.Scale(tile_size_frame, from_=32, to=256, orient=tk.HORIZONTAL,
                variable=tile_size_var, bg="#2a2a2a", fg="white",
                font=("Arial", 9), length=300,
                tickinterval=32,  # Zeigt 32, 64, 96, 128, 160, 192, 224, 256
                resolution=8,  # Schritte von 8px
                troughcolor="#1a1a1a",
                highlightthickness=0)
        slider.pack(side=tk.LEFT)
        
        # Live-Info-Label (größer und besser sichtbar)
        tile_info_label = tk.Label(tile_size_frame, text=f"{recommended_tile_size}px → {img_w//recommended_tile_size}×{img_h//recommended_tile_size}",
                                   bg="#2a2a2a", fg="#66ff66",
                                   font=("Arial", 11, "bold"))
        tile_info_label.pack(side=tk.LEFT, padx=15)
        
        # Quick-Select Buttons für gängige Größen
        quick_frame = tk.Frame(tile_frame, bg="#2a2a2a")
        quick_frame.pack(fill=tk.X, padx=20, pady=5)
        
        tk.Label(quick_frame, text="Schnellwahl:",
                bg="#2a2a2a", fg="#888",
                font=("Arial", 8)).pack(side=tk.LEFT, padx=5)
        
        for size in [32, 64, 96, 128, 160, 192, 256]:
            btn = tk.Button(quick_frame, text=f"{size}px",
                          bg="#3a3a3a", fg="white",
                          font=("Arial", 7),
                          padx=5, pady=2,
                          command=lambda s=size: tile_size_var.set(s))
            btn.pack(side=tk.LEFT, padx=2)
            
            # Empfohlenen Button hervorheben
            if size == recommended_tile_size:
                btn.config(bg="#2a7d2a", font=("Arial", 7, "bold"))
        
        def update_tile_info(*args):
            ts = tile_size_var.get()
            grid_w = img_w // ts
            grid_h = img_h // ts
            total_tiles = grid_w * grid_h
            
            # Größe und Grid-Info
            base_text = f"{ts}px → {grid_w}×{grid_h} = {total_tiles} Tiles"
            
            # Warnung bei zu vielen Tiles mit Emoji
            if total_tiles > 2500:
                tile_info_label.config(
                    text=f"{base_text} ❌",
                    fg="#ff3333"
                )
            elif total_tiles > 1500:
                tile_info_label.config(
                    text=f"{base_text} ⚠️",
                    fg="#ffaa00"
                )
            else:
                tile_info_label.config(
                    text=f"{base_text} ✅",
                    fg="#44ff44"
                )
        
        tile_size_var.trace('w', update_tile_info)
        
        # Map-Name
        name_frame = tk.Frame(options_frame, bg="#2a2a2a")
        name_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(name_frame, text="Map-Name:",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        map_name_var = tk.StringVar(value=os.path.splitext(os.path.basename(png_path))[0])
        tk.Entry(name_frame, textvariable=map_name_var,
                bg="#3a3a3a", fg="white", font=("Arial", 10),
                width=40).pack(anchor=tk.W, padx=20, pady=5)
        
        # Preview
        preview_frame = tk.LabelFrame(scrollable_frame, text="Vorschau",
                                     bg="#2a2a2a", fg="white",
                                     font=("Arial", 10, "bold"))
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        preview_label = tk.Label(preview_frame, bg="#1a1a1a")
        preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def update_preview(*args):
            from png_map_importer import PNGMapImporter
            importer = PNGMapImporter()
            
            if import_mode.get() == "grid":
                preview_img = importer.get_import_preview(png_path, tile_size_var.get(), preview_size=400)
            else:
                preview_img = Image.open(png_path)
                preview_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            if preview_img:
                photo = ImageTk.PhotoImage(preview_img)
                preview_label.config(image=photo)
                preview_label.image = photo
        
        import_mode.trace('w', update_preview)
        tile_size_var.trace('w', update_preview)
        update_preview()
        
        # Buttons (AUSSERHALB scrollable_frame, fixiert am unteren Rand)
        button_frame = tk.Frame(dialog, bg="#1a1a1a")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        def do_import():
            try:
                from png_map_importer import PNGMapImporter
                importer = PNGMapImporter()
                
                map_name = map_name_var.get()
                
                if import_mode.get() == "grid":
                    # Grid-Import
                    self.current_map_data = importer.import_png_map(
                        png_path, 
                        tile_size=tile_size_var.get(),
                        map_name=map_name
                    )
                    msg = f"✅ Map importiert: {self.current_map_data['width']}x{self.current_map_data['height']} Tiles"
                else:
                    # Single-Texture-Import
                    self.current_map_data = importer.import_png_as_single_texture(
                        png_path,
                        map_width=50,
                        map_height=50
                    )
                    msg = f"✅ Map als einzelne Textur importiert"
                
                # Bundle erstellen (bei Grid-Import mit vielen Tiles)
                bundle_created = False
                if import_mode.get() == "grid" and "custom_materials" in self.current_map_data:
                    material_count = len(self.current_map_data["custom_materials"])
                    
                    # Nur bei vielen Materialien Bundle anbieten (>20)
                    if material_count > 20:
                        if messagebox.askyesno("Bundle erstellen?",
                                              f"Diese Map hat {material_count} Materialien.\n\n"
                                              f"Möchtest du ein Material-Bundle erstellen?\n"
                                              f"Das verbessert die Performance im Editor!"):
                            try:
                                from material_bundle_manager import MaterialBundleManager
                                bundle_mgr = MaterialBundleManager()
                                bundle_id = bundle_mgr.create_bundle_from_imported_map(
                                    self.current_map_data,
                                    bundle_name=map_name
                                )
                                if bundle_id:
                                    bundle_created = True
                                    msg += f"\n\n📦 Bundle '{map_name}' erstellt!"
                            except Exception as e:
                                print(f"⚠️ Bundle-Erstellung fehlgeschlagen: {e}")
                
                messagebox.showinfo("Erfolg", 
                                   f"{msg}\n\n"
                                   f"Du kannst die Map jetzt:\n"
                                   f"• Im Editor bearbeiten\n"
                                   f"• Als SVG exportieren\n"
                                   f"• Im Projektor anzeigen" +
                                   (f"\n\n📦 Bundle '{map_name}' kann im Editor aktiviert werden!" if bundle_created else ""))
                main_canvas.unbind_all("<MouseWheel>")
                dialog.destroy()
                
                # OPTIONAL: Frage ob Editor direkt öffnen
                if messagebox.askyesno("Editor öffnen?", 
                                      "Möchtest du die importierte Map jetzt im Editor öffnen?"):
                    self.start_editor()
                
            except Exception as e:
                messagebox.showerror("Fehler", f"Import fehlgeschlagen:\n{e}")
        
        def on_dialog_close():
            main_canvas.unbind_all("<MouseWheel>")
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        tk.Button(button_frame, text="✅ Importieren",
                 font=("Arial", 12, "bold"),
                 bg="#2a7d2a", fg="white",
                 padx=30, pady=10,
                 command=do_import).pack(side=tk.LEFT, padx=10)
        
        tk.Button(button_frame, text="❌ Abbrechen",
                 font=("Arial", 12, "bold"),
                 bg="#7d2a2a", fg="white",
                 padx=30, pady=10,
                 command=on_dialog_close).pack(side=tk.LEFT, padx=10)
    
    def destroy(self):
        """Aufräumen beim Schließen"""
        # Webcam stoppen
        if self.webcam_tracker:
            self.webcam_tracker.stop()
        super().destroy()

if __name__ == "__main__":
    DerEineRingProApp().mainloop()
