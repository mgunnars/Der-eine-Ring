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
            from map_editor import MapEditor, ask_canvas_size
            
            print(f"\n🔍 DEBUG start_editor:")
            print(f"   self.current_map_data: {'vorhanden' if self.current_map_data else 'None'}")
            
            # Wenn keine Map geladen ist, frage nach Größe
            if not self.current_map_data:
                print(f"   → Keine Map geladen, frage nach Größe...")
                size = ask_canvas_size(self)
                
                if not size["confirmed"]:
                    return  # Benutzer hat abgebrochen
                
                width = size["width"]
                height = size["height"]
                map_data_to_pass = None
            else:
                # Map bereits geladen, nutze deren Größe UND Daten
                width = self.current_map_data.get("width", 50)
                height = self.current_map_data.get("height", 50)
                map_data_to_pass = self.current_map_data
                print(f"   → Map vorhanden: {width}×{height}")
                print(f"   → map_data_to_pass wird übergeben!")
            
            print(f"📋 Erstelle Editor mit: width={width}, height={height}, map_data={'JA' if map_data_to_pass else 'NEIN'}")
            
            editor_win = tk.Toplevel(self)
            editor_win.title("Map Editor - Der Eine Ring")
            editor_win.state('zoomed')  # Fullscreen/Maximiert starten
            editor_win.configure(bg="#1a1a1a")
            
            # MapEditor mit aktuellen Daten oder neu
            editor = MapEditor(editor_win, width=width, height=height, map_data=map_data_to_pass)
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
            
            # Hole Map-Daten
            map_data = self.current_map_data
            if self.current_editor:
                map_data = self.current_editor.get_map_data()
            
            # Prüfe ob SVG-Path in Map-Daten oder als loaded_svg_path
            svg_path = None
            if hasattr(self, 'loaded_svg_path') and self.loaded_svg_path:
                svg_path = self.loaded_svg_path
            elif map_data and map_data.get("svg_path"):
                svg_path = map_data.get("svg_path")
            
            # SVG-Modus: Öffne Projektor mit Original-SVG
            if svg_path:
                if self.projector_window and self.projector_window.winfo_exists():
                    self.projector_window.destroy()
                
                # Projektor mit map_data UND svg_path erstellen
                self.projector_window = ProjectorWindow(
                    self, 
                    map_data=map_data,
                    svg_path=svg_path, 
                    webcam_tracker=self.webcam_tracker
                )
                return
            
            # JSON-Modus: Normale Tile-basierte Map
            # Wenn keine Daten vorhanden, Standardkarte laden
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
    
    def parse_svg_to_map(self, svg_path):
        """Parst SVG und erstellt Map-Daten für Editor"""
        try:
            import xml.etree.ElementTree as ET
            from PIL import Image, ImageTk
            import io
            import base64
            
            print(f"🔍 Parse SVG: {svg_path}")
            
            # Parse SVG
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # SVG-Dimensionen
            svg_width = float(root.get('width', '1000').replace('px', ''))
            svg_height = float(root.get('height', '1000').replace('px', ''))
            
            print(f"   SVG-Größe: {svg_width}×{svg_height}px")
            
            # Zähle embedded images
            images = [elem for elem in root.iter() if 'image' in elem.tag]
            print(f"   Gefundene <image> Elemente: {len(images)}")
            
            # STRATEGIE: SVGs mit vielen embedded images
            # → Verwende FESTE Tile-Größe für bessere Auflösung (nicht Image-Größe!)
            # Die Images in der SVG sind oft zu groß (z.B. 206px)
            # Wir wollen aber eine editierbare Map mit vielen Tiles
            tile_size = 64  # FESTE Tile-Größe für gute Balance zwischen Detail und Performance
            
            if images:
                first_img = images[0]
                img_width = float(first_img.get('width', 32))
                img_height = float(first_img.get('height', 32))
                print(f"   SVG enthält {len(images)} Images à {int(img_width)}×{int(img_height)}px")
                print(f"   → Konvertiere zu {tile_size}px Tiles für bessere Editierbarkeit")
            else:
                print(f"   → Verwende {tile_size}px Tiles")
            
            # Berechne Grid-Größe basierend auf SVG-Dimensionen und Tile-Größe
            # Runde auf, um sicherzustellen dass alle Tiles passen
            import math
            grid_width = max(10, math.ceil(svg_width / tile_size))
            grid_height = max(7, math.ceil(svg_height / tile_size))
            
            print(f"   Grid: {grid_width}×{grid_height} tiles")
            
            # Erstelle leeres Tile-Array
            tiles = [["empty" for _ in range(grid_width)] for _ in range(grid_height)]
            
            # Sammle Materials aus SVG
            materials_found = set()
            tiles_filled = 0
            
            # Tracking: Welche Tiles wurden bereits gefüllt?
            filled_positions = set()
            
            # Parse alle <image> Elemente
            for img_elem in images:
                try:
                    x = float(img_elem.get('x', 0))
                    y = float(img_elem.get('y', 0))
                    w = float(img_elem.get('width', 64))
                    h = float(img_elem.get('height', 64))
                    
                    # href kann base64-kodiertes Bild sein
                    href = img_elem.get('{http://www.w3.org/1999/xlink}href', img_elem.get('href', ''))
                    
                    # Versuche Material aus base64-Daten zu erraten
                    material = 'grass'  # Default
                    
                    if href.startswith('data:image'):
                        # Base64-kodiertes Bild → Analysiere Bildfarben
                        try:
                            # Extrahiere base64-Daten
                            base64_data = href.split(',')[1] if ',' in href else href
                            img_data = base64.b64decode(base64_data)
                            pil_img = Image.open(io.BytesIO(img_data))
                            
                            # Analysiere dominante Farbe (vereinfacht)
                            pil_img_small = pil_img.resize((10, 10), Image.Resampling.LANCZOS)
                            colors = pil_img_small.convert('RGB').getcolors(maxcolors=100)
                            if colors:
                                # Häufigste Farbe
                                dominant_color = max(colors, key=lambda x: x[0])[1]
                                r, g, b = dominant_color
                                
                                # Material aus dominanter Farbe erraten
                                if g > r and g > b:  # Grünlich
                                    if g > 150:
                                        material = 'grass'
                                    else:
                                        material = 'forest'
                                elif b > r and b > g and b > 100:  # Bläulich
                                    material = 'water'
                                elif r > 150 and g > 150 and b < 100:  # Gelblich
                                    material = 'sand'
                                elif r < 100 and g < 100 and b < 100:  # Dunkel
                                    material = 'mountain'
                                elif r > 100 and g > 100 and b > 100:  # Hell grau
                                    material = 'stone'
                                elif r > 100 and g > 80 and b < 80:  # Bräunlich
                                    material = 'road'
                        except:
                            pass
                    
                    materials_found.add(material)
                    
                    # Tile-Koordinaten berechnen: Ein Image deckt mehrere Tiles ab
                    # Berechne welche Tiles von diesem Image abgedeckt werden
                    tx_start = int(x / tile_size)
                    ty_start = int(y / tile_size)
                    tx_end = min(grid_width, int((x + w) / tile_size) + 1)
                    ty_end = min(grid_height, int((y + h) / tile_size) + 1)
                    
                    # Fülle alle Tiles die von diesem Image abgedeckt werden
                    for ty in range(ty_start, ty_end):
                        for tx in range(tx_start, tx_end):
                            if 0 <= ty < grid_height and 0 <= tx < grid_width:
                                pos_key = (ty, tx)
                                if pos_key not in filled_positions:
                                    tiles[ty][tx] = material
                                    filled_positions.add(pos_key)
                                    tiles_filled += 1
                
                except Exception as e:
                    print(f"      Fehler bei Image-Element: {e}")
                    continue
            
            # Parse alle <rect> Elemente (falls vorhanden)
            rects = [elem for elem in root.iter() if 'rect' in elem.tag]
            for rect_elem in rects:
                try:
                    x = float(rect_elem.get('x', 0))
                    y = float(rect_elem.get('y', 0))
                    w = float(rect_elem.get('width', tile_size))
                    h = float(rect_elem.get('height', tile_size))
                    
                    fill = rect_elem.get('fill', 'grass')
                    elem_id = rect_elem.get('id', '')
                    
                    material = self.guess_material_from_svg(elem_id, fill)
                    materials_found.add(material)
                    
                    # Tile-Koordinaten
                    tx1 = int(x / tile_size)
                    ty1 = int(y / tile_size)
                    tx2 = min(grid_width, int((x + w) / tile_size) + 1)
                    ty2 = min(grid_height, int((y + h) / tile_size) + 1)
                    
                    for ty in range(ty1, ty2):
                        for tx in range(tx1, tx2):
                            if 0 <= ty < grid_height and 0 <= tx < grid_width:
                                tiles[ty][tx] = material
                                tiles_filled += 1
                except:
                    continue
            
            # Fülle leere Tiles mit grass (falls SVG Lücken hat)
            empty_count = 0
            for ty in range(grid_height):
                for tx in range(grid_width):
                    if tiles[ty][tx] == "empty":
                        tiles[ty][tx] = "grass"
                        empty_count += 1
            
            print(f"   Materials gefunden: {materials_found}")
            print(f"   Tiles gefüllt: {tiles_filled}/{grid_width * grid_height} ({empty_count} mit 'grass' aufgefüllt)")
            print(f"   ℹ️ Hinweis: SVG-Texturen werden farbanalysiert und in Tiles konvertiert")
            
            return {
                "is_svg_mode": True,
                "svg_path": svg_path,
                "width": grid_width,
                "height": grid_height,
                "tiles": tiles,
                "river_directions": {},
                "version": "2.0-svg",
                "original_svg_size": (svg_width, svg_height)
            }
            
        except Exception as e:
            print(f"❌ SVG-Parse-Fehler: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def guess_material_from_svg(self, elem_id, fill_color):
        """Errät Material aus SVG-Element-ID, Farbe oder base64 data"""
        elem_id = elem_id.lower()
        fill_color = fill_color.lower()
        
        # Material-Keywords
        if 'grass' in elem_id or 'wiese' in elem_id or '#90ee90' in fill_color:
            return 'grass'
        elif 'water' in elem_id or 'wasser' in elem_id or '#4169e1' in fill_color:
            return 'water'
        elif 'forest' in elem_id or 'wald' in elem_id or 'tree' in elem_id or '#228b22' in fill_color:
            return 'forest'
        elif 'mountain' in elem_id or 'berg' in elem_id or '#808080' in fill_color:
            return 'mountain'
        elif 'sand' in elem_id or 'desert' in elem_id or '#f4a460' in fill_color:
            return 'sand'
        elif 'stone' in elem_id or 'stein' in elem_id or 'rock' in elem_id:
            return 'stone'
        elif 'road' in elem_id or 'weg' in elem_id or 'path' in elem_id:
            return 'road'
        elif 'village' in elem_id or 'dorf' in elem_id or 'town' in elem_id:
            return 'village'
        else:
            return 'grass'  # Default
    
    def load_map(self):
        """Karte laden - unterstützt JSON und SVG"""
        print(f"\n🔍 DEBUG load_map() aufgerufen!")
        print(f"   Vor Laden: self.current_map_data = {'vorhanden' if self.current_map_data else 'None'}")
        
        filename = filedialog.askopenfilename(
            title="Karte laden",
            filetypes=[("Alle Dateien", "*.*"), ("JSON Dateien", "*.json"), ("SVG Dateien", "*.svg")],
            initialdir="maps"
        )
        
        print(f"   Ausgewählte Datei: {filename if filename else 'ABGEBROCHEN'}")
        
        if filename:
            # SVG? → Parse und konvertiere zu editierbarem Format
            if filename.lower().endswith('.svg'):
                self.loaded_svg_path = filename
                print(f"📌 SVG wird geladen: {filename}")
                
                try:
                    # Für komplexe SVGs: Biete zwei Optionen an
                    choice = messagebox.askquestion(
                        "SVG laden",
                        f"SVG-Datei: {os.path.basename(filename)}\n\n"
                        f"Wie möchtest du die SVG öffnen?\n\n"
                        f"JA = Im Projektor anzeigen (empfohlen für komplexe SVGs)\n"
                        f"NEIN = In Editor konvertieren (nur für einfache SVGs)",
                        icon='question'
                    )
                    
                    if choice == 'yes':
                        # Projektor-Modus
                        messagebox.showinfo("SVG geladen", 
                            f"✅ SVG-Karte geladen!\n\n"
                            f"Datei: {os.path.basename(filename)}\n\n"
                            f"Öffne jetzt '📺 Projektor-Modus' um die SVG anzuzeigen.\n\n"
                            f"Tipp: Im Projektor kannst du zoomen, pannen und Fog-of-War nutzen!")
                        return
                    
                    # Editor-Modus: Parse SVG
                    svg_map_data = self.parse_svg_to_map(filename)
                    
                    if svg_map_data:
                        self.current_map_data = svg_map_data
                        
                        msg = (f"✅ SVG-Karte geladen!\n\n"
                               f"Datei: {os.path.basename(filename)}\n"
                               f"Größe: {svg_map_data.get('width')}×{svg_map_data.get('height')}\n\n"
                               f"Die SVG wurde in ein editierbares Tile-Grid konvertiert.\n"
                               f"Du kannst sie jetzt mit allen Tools bearbeiten!\n\n"
                               f"Im Editor öffnen?")
                        
                        if messagebox.askyesno("SVG geladen", msg):
                            self.start_editor()
                        else:
                            messagebox.showinfo("Info", "SVG geladen! Öffne Editor oder Projektor.")
                    else:
                        messagebox.showerror("Fehler", "SVG konnte nicht geparst werden")
                        
                except Exception as e:
                    import traceback
                    print(f"❌ SVG-Fehler:\n{traceback.format_exc()}")
                    messagebox.showerror("SVG-Fehler", f"Fehler beim Laden:\n{e}")
                return
            
            # JSON → Lade als normale Karte
            try:
                from map_system import MapSystem
                ms = MapSystem()
                map_data = ms.load_map(filename)
                
                print(f"\n🔍 DEBUG load_map:")
                print(f"   Datei: {os.path.basename(filename)}")
                print(f"   map_data: {'vorhanden' if map_data else 'None'}")
                if map_data:
                    print(f"   Größe: {map_data.get('width')}×{map_data.get('height')}")
                    print(f"   Keys: {list(map_data.keys())}")
                
                if map_data:
                    self.current_map_data = map_data
                    self.loaded_svg_path = None  # Reset SVG-Modus
                    
                    print(f"✅ self.current_map_data gesetzt!")
                    print(f"   self.current_map_data ist: {'vorhanden' if self.current_map_data else 'None'}")
                    
                    # Frage ob Editor geöffnet werden soll
                    msg = f"Karte geladen:\n{os.path.basename(filename)}\n\nGröße: {map_data.get('width')}×{map_data.get('height')}\n\nIm Editor öffnen?"
                    
                    if messagebox.askyesno("Karte geladen", msg):
                        print(f"🚀 Rufe start_editor() auf...")
                        self.start_editor()
                    else:
                        messagebox.showinfo("Info", "Karte geladen! Du kannst sie jetzt im Editor oder Projektor öffnen.")
                else:
                    messagebox.showerror("Fehler", "Karte konnte nicht geladen werden")
            except Exception as e:
                import traceback
                print(f"❌ FEHLER beim Laden:\n{traceback.format_exc()}")
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
        
        # Import-Dialog erstellen (BREITER für mehr Platz!)
        dialog = tk.Toplevel(self)
        dialog.title("PNG-Karte importieren")
        dialog.geometry("950x750")  # Breiter: 750→950
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
        
        if max_dimension > 8000:
            recommended_tile_size = 512
            recommendation = "🔥🔥 EXTREM! Empfehlung: 512px Tiles"
            rec_color = "#ff0000"
        elif max_dimension > 6000:
            recommended_tile_size = 384
            recommendation = "🔥 Riesig! Empfehlung: 384px Tiles"
            rec_color = "#ff3333"
        elif max_dimension > 4000:
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
        
        # Verbesserter Slider mit Markierungen (bis 512px!)
        slider = tk.Scale(tile_size_frame, from_=32, to=512, orient=tk.HORIZONTAL,
                variable=tile_size_var, bg="#2a2a2a", fg="white",
                font=("Arial", 9), length=400,
                tickinterval=64,  # Zeigt 32, 96, 160, 224, 288, 352, 416, 480
                resolution=16,  # Schritte von 16px
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
        
        for size in [32, 64, 96, 128, 192, 256, 384, 512]:
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
        
        # Speicherpfad für Tile-Set (nur Grid-Modus)
        storage_frame = tk.Frame(options_frame, bg="#2a2a2a")
        storage_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(storage_frame, text="Speicherpfad für Tile-Set:",
                bg="#2a2a2a", fg="white",
                font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        tk.Label(storage_frame, 
                text="💡 Gib einen Unterordner-Namen an. Tiles werden in imported_maps/DEIN_NAME/ gespeichert",
                bg="#2a2a2a", fg="#888", font=("Arial", 8, "italic")).pack(anchor=tk.W, padx=20, pady=2)
        
        storage_path_var = tk.StringVar(value=map_name_var.get().lower().replace(" ", "_"))
        
        storage_entry_frame = tk.Frame(storage_frame, bg="#2a2a2a")
        storage_entry_frame.pack(anchor=tk.W, padx=20, pady=5)
        
        tk.Label(storage_entry_frame, text="imported_maps/",
                bg="#2a2a2a", fg="#888", font=("Arial", 10)).pack(side=tk.LEFT)
        
        storage_entry = tk.Entry(storage_entry_frame, textvariable=storage_path_var,
                                bg="#3a3a3a", fg="white", font=("Arial", 10),
                                width=30)
        storage_entry.pack(side=tk.LEFT)
        
        tk.Label(storage_entry_frame, text="/",
                bg="#2a2a2a", fg="#888", font=("Arial", 10)).pack(side=tk.LEFT)
        
        # Map-Name ändert auch Speicherpfad
        def sync_storage_path(*args):
            if storage_path_var.get() == "" or not storage_entry.focus_get():
                storage_path_var.set(map_name_var.get().lower().replace(" ", "_"))
        
        map_name_var.trace('w', sync_storage_path)
        
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
                storage_path = storage_path_var.get().strip()
                
                # Validiere Speicherpfad
                if not storage_path:
                    storage_path = map_name.lower().replace(" ", "_")
                
                if import_mode.get() == "grid":
                    # Grid-Import mit Custom-Speicherpfad
                    # Ändere den texture_storage_dir des Importers
                    custom_storage_dir = os.path.join("imported_maps", storage_path)
                    importer.texture_storage_dir = custom_storage_dir
                    
                    self.current_map_data = importer.import_png_map(
                        png_path, 
                        tile_size=tile_size_var.get(),
                        map_name=map_name
                    )
                    msg = f"✅ Map importiert: {self.current_map_data['width']}x{self.current_map_data['height']} Tiles\n"
                    msg += f"📁 Tiles gespeichert in: {custom_storage_dir}"
                else:
                    # Single-Texture-Import
                    self.current_map_data = importer.import_png_as_single_texture(
                        png_path,
                        map_width=50,
                        map_height=50
                    )
                    msg = f"✅ Map als einzelne Textur importiert"
                
                # Info über Bundle (wird automatisch im Editor erstellt)
                if import_mode.get() == "grid" and "custom_materials" in self.current_map_data:
                    material_count = len(self.current_map_data["custom_materials"])
                    if material_count > 20:
                        msg += f"\n\n📦 Material-Bundle wird automatisch im Editor erstellt"
                
                messagebox.showinfo("Erfolg", 
                                   f"{msg}\n\n"
                                   f"Du kannst die Map jetzt:\n"
                                   f"• Im Editor bearbeiten\n"
                                   f"• Als SVG exportieren\n"
                                   f"• Im Projektor anzeigen")
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
