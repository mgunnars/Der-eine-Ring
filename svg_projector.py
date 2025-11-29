"""
SVG Projector Renderer - High-Quality Rendering für Projektor-Modus

Vorteile gegenüber PNG-Tiles:
- Verlustfreie Skalierung
- Bessere Qualität bei Zoom/Pan
- Geringerer Speicherverbrauch
- Native Auflösungsanpassung
"""

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import os
import time
import xml.etree.ElementTree as ET
import base64

# cairosvg ist für High-Quality Vektor-Rendering erforderlich
try:
    import cairosvg
    HAS_CAIROSVG = True
    print("✅ CairoSVG verfügbar - nutze High-Quality SVG-Rendering")
except ImportError as e:
    HAS_CAIROSVG = False
    print("⚠️  CairoSVG nicht installiert - nutze PIL-Fallback")
    print("   📦 Installiere mit: py -m pip install cairosvg")
    print("   🔧 Unter Windows zusätzlich benötigt: GTK3 Runtime")
    print("   📥 Download: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
    print("   ℹ️  Oder führe aus: INSTALL_CAIRO.bat")
except OSError as e:
    HAS_CAIROSVG = False
    print("⚠️  CairoSVG installiert, aber Cairo-DLLs fehlen!")
    print("   🔧 Unter Windows benötigt: GTK3 Runtime für Cairo-DLLs")
    print("   📥 Download: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
    print("   ℹ️  Oder führe aus: INSTALL_CAIRO.bat")
    print(f"   🐛 Fehler: {e}")

print(f"🔍 DEBUG: HAS_CAIROSVG = {HAS_CAIROSVG}")


class SVGProjectorRenderer:
    """Rendert SVG-Karten für Projektor mit optimaler Qualität"""
    
    def __init__(self, svg_path):
        self.svg_path = svg_path
        self.svg_data = None
        self.cached_render = None
        self.cached_size = None
        self.render_time = 0
        
        # MULTI-LEVEL CACHE: Speichere mehrere Zoom-Stufen
        self.render_cache = {}  # {(width, height): PIL.Image}
        self.max_cache_size = 5  # Max 5 verschiedene Größen cachen
        
        # SVG laden
        self.load_svg()
    
    def load_svg(self):
        """Lädt SVG-Datei und entfernt Grid-Layer für Projektor"""
        try:
            with open(self.svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Parse SVG und entferne Grid-Layer (für Spieler-Projektor unnötig)
            try:
                root = ET.fromstring(svg_content)
                
                # Namespace-Map
                ns = {'svg': 'http://www.w3.org/2000/svg'}
                
                # Finde und entferne grid-overlay Gruppe (mit und ohne Namespace)
                for group in root.findall('.//svg:g[@id="grid-overlay"]', ns):
                    root.remove(group)
                
                # Fallback ohne Namespace
                for group in root.findall('.//g[@id="grid-overlay"]'):
                    root.remove(group)
                
                # Zurück zu String
                self.svg_data = ET.tostring(root, encoding='unicode')
                print(f"✅ SVG geladen (Grid-Layer entfernt für Projektor): {self.svg_path}")
            except Exception as e:
                # Fallback: Originales SVG verwenden
                print(f"⚠️ Grid-Entfernung fehlgeschlagen: {e}")
                self.svg_data = svg_content
                print(f"✅ SVG geladen: {self.svg_path}")
            
            return True
        except Exception as e:
            print(f"❌ Fehler beim Laden der SVG: {e}")
            return False
    
    def render_to_size(self, width, height, cache=True):
        """
        Rendert SVG zu spezifischer Größe
        
        Args:
            width: Zielbreite in Pixeln
            height: Zielhöhe in Pixeln
            cache: Wenn True, wird Rendering gecacht
            
        Returns:
            PIL Image
        """
        # MULTI-LEVEL CACHE prüfen
        cache_key = (width, height)
        if cache and cache_key in self.render_cache:
            print(f"📦 Verwende gecachtes Rendering ({width}×{height})")
            return self.render_cache[cache_key]
        
        if not self.svg_data:
            print("⚠️ Keine SVG-Daten geladen!")
            return None
        
        print(f"🎨 Rendere SVG zu {width}×{height}px...")
        start_time = time.time()
        
        try:
            if HAS_CAIROSVG:
                print("🔍 DEBUG: Verwende CairoSVG-Rendering")
                # Hochwertig mit cairosvg
                image = self._render_with_cairosvg(width, height)
            else:
                print("🔍 DEBUG: Verwende PIL-Fallback-Rendering")
                # Fallback mit PIL (extrahiert eingebettete Bilder)
                image = self._render_with_pil_fallback(width, height)
            
            if not image:
                print("❌ DEBUG: Rendering fehlgeschlagen - image ist None")
                return None
            
            self.render_time = time.time() - start_time
            print(f"✅ Rendering abgeschlossen in {self.render_time:.2f}s")
            
            # MULTI-LEVEL CACHE speichern
            if cache:
                # Cache-Größe begrenzen (FIFO)
                if len(self.render_cache) >= self.max_cache_size:
                    # Ältesten Eintrag entfernen
                    oldest_key = next(iter(self.render_cache))
                    del self.render_cache[oldest_key]
                
                self.render_cache[cache_key] = image
                print(f"💾 Cached: {len(self.render_cache)} Größen im Speicher")
            
            return image
            
        except Exception as e:
            print(f"❌ Fehler beim Rendern: {e}")
            return None
    
    def _render_with_cairosvg(self, width, height):
        """Rendert mit CairoSVG (hohe Qualität, echte Vektoren)"""
        print(f"🔍 DEBUG: _render_with_cairosvg aufgerufen mit {width}×{height}")
        try:
            png_data = cairosvg.svg2png(
                bytestring=self.svg_data.encode('utf-8'),
                output_width=width,
                output_height=height,
                dpi=96  # Standard-DPI für Screens
            )
            print(f"🔍 DEBUG: cairosvg.svg2png erfolgreich, PNG-Daten Größe: {len(png_data)} bytes")
            image = Image.open(BytesIO(png_data))
            print(f"🔍 DEBUG: PIL Image erstellt: {image.size}, Mode: {image.mode}")
            return image
        except Exception as e:
            print(f"⚠️ Cairo-Rendering fehlgeschlagen: {e}")
            print("   Fallback zu PIL...")
            return self._render_with_pil_fallback(width, height)
    
    def _render_with_pil_fallback(self, width, height):
        """
        Fallback-Rendering mit PIL
        Extrahiert base64-eingebettete PNG-Tiles und compositet sie
        """
        print(f"🔍 DEBUG: _render_with_pil_fallback aufgerufen mit {width}×{height}")
        try:
            root = ET.fromstring(self.svg_data)
            
            # SVG Namespaces
            namespaces = {
                'svg': 'http://www.w3.org/2000/svg',
                'xlink': 'http://www.w3.org/1999/xlink'
            }
            
            # SVG Dimensionen auslesen
            svg_width = int(root.get('width', '1000').replace('px', ''))
            svg_height = int(root.get('height', '1000').replace('px', ''))
            
            # Skalierungsfaktor
            scale_x = width / svg_width
            scale_y = height / svg_height
            
            # Schwarzer Hintergrund
            composite = Image.new('RGB', (width, height), (26, 26, 26))
            
            # Alle <image> Elemente finden MIT Namespace
            images = root.findall('.//{http://www.w3.org/2000/svg}image', namespaces)
            
            # Fallback: Auch ohne Namespace versuchen
            if len(images) == 0:
                images = root.findall('.//image')
            
            print(f"   Gefunden: {len(images)} Bilder")
            
            # DEBUG: Prüfe erste paar Tiles auf Borders
            border_check_count = 0
            tiles_with_borders = 0
            
            success_count = 0
            for idx, img_elem in enumerate(images):
                try:
                    # Position und Größe
                    x = float(img_elem.get('x', 0))
                    y = float(img_elem.get('y', 0))
                    w = float(img_elem.get('width', 256))
                    h = float(img_elem.get('height', 256))
                    
                    # Skaliert
                    scaled_x = int(x * scale_x)
                    scaled_y = int(y * scale_y)
                    scaled_w = int(w * scale_x)
                    scaled_h = int(h * scale_y)
                    
                    # Bild-Daten mit xlink:href Namespace
                    href = img_elem.get('{http://www.w3.org/1999/xlink}href')
                    
                    # Debug ersten paar Bilder
                    if idx < 3:
                        print(f"   Bild {idx}: href={href[:50] if href else 'None'}...")
                    
                    if href and 'data:image/png;base64,' in href:
                        # Base64 decodieren
                        base64_data = href.split(',', 1)[1]
                        img_data = base64.b64decode(base64_data)
                        tile_img = Image.open(BytesIO(img_data))
                        
                        # Prüfe VOR der Bereinigung ob Borders vorhanden sind (für Statistik)
                        had_border = False
                        if border_check_count < 10:
                            had_border = self._check_tile_for_borders(tile_img)
                            if had_border:
                                tiles_with_borders += 1
                            border_check_count += 1
                        
                        # BORDER-REMOVAL: Entferne Borders falls vorhanden
                        tile_img = self._remove_tile_border(tile_img)
                        
                        # Skalieren falls nötig
                        if tile_img.size != (scaled_w, scaled_h):
                            tile_img = tile_img.resize((scaled_w, scaled_h), Image.LANCZOS)
                        
                        # Einfügen
                        composite.paste(tile_img, (scaled_x, scaled_y))
                        success_count += 1
                    
                except Exception as e:
                    if idx < 3:  # Nur erste paar Fehler anzeigen
                        print(f"   ⚠️ Fehler bei Bild {idx}: {e}")
                    continue
            
            print(f"   ✅ {success_count}/{len(images)} Bilder erfolgreich eingefügt")
            
            if tiles_with_borders > 0:
                print(f"   🧹 {tiles_with_borders}/{border_check_count} Tiles hatten Borders → automatisch bereinigt!")
            else:
                print(f"   ✅ Keine Tile-Borders erkannt - saubere Texturen!")
            
            return composite
            
        except Exception as e:
            print(f"❌ PIL-Fallback Fehler: {e}")
            import traceback
            traceback.print_exc()
            # Notfall: Schwarzes Bild
            print("🔍 DEBUG: Erstelle Notfall-Bild (schwarz)")
            return Image.new('RGB', (width, height), (26, 26, 26))
    
    def _check_tile_for_borders(self, tile_img):
        """
        Prüft ob ein Tile dunkle Ränder hat (Grid-Lines)
        Gibt True zurück wenn Borders erkannt werden
        """
        try:
            width, height = tile_img.size
            
            # Zu kleine Tiles nicht prüfen
            if width < 10 or height < 10:
                return False
            
            # Konvertiere zu RGB
            if tile_img.mode == 'RGBA':
                tile_rgb = tile_img.convert('RGB')
            else:
                tile_rgb = tile_img
            
            pixels = tile_rgb.load()
            
            # Sample Ränder
            edge_samples = []
            # Top & Bottom (nur ein paar Samples)
            for x in [0, width//4, width//2, width*3//4, width-1]:
                edge_samples.append(sum(pixels[x, 0]))  # Top
                edge_samples.append(sum(pixels[x, height-1]))  # Bottom
            
            # Left & Right
            for y in [0, height//4, height//2, height*3//4, height-1]:
                edge_samples.append(sum(pixels[0, y]))  # Left
                edge_samples.append(sum(pixels[width-1, y]))  # Right
            
            edge_brightness = sum(edge_samples) / len(edge_samples)
            
            # Sample Center
            cx = width // 2
            cy = height // 2
            center_samples = [
                sum(pixels[cx, cy]),
                sum(pixels[cx-width//4, cy]),
                sum(pixels[cx+width//4, cy]),
                sum(pixels[cx, cy-height//4]),
                sum(pixels[cx, cy+height//4])
            ]
            center_brightness = sum(center_samples) / len(center_samples)
            
            # Wenn Ränder mindestens 20% dunkler → Border vorhanden
            # (Schwellenwert reduziert für bessere Erkennung)
            return edge_brightness < center_brightness * 0.8
            
        except Exception as e:
            return False
    
    def _remove_tile_border(self, tile_img):
        """
        Entfernt 1-2px Border von Tile (Grid-Lines)
        Prüft automatisch ob Borders vorhanden sind
        """
        try:
            width, height = tile_img.size
            
            # Zu kleine Tiles nicht bearbeiten
            if width < 10 or height < 10:
                return tile_img
            
            # Prüfe ob Borders vorhanden sind
            if not self._check_tile_for_borders(tile_img):
                return tile_img
            
            # Crop 2px von allen Seiten und scale zurück
            # (2px für dickere Grid-Lines, funktioniert auch bei dünnen)
            border_size = 2
            cropped = tile_img.crop((border_size, border_size, width-border_size, height-border_size))
            
            # Scale zurück auf Original-Größe mit LANCZOS (beste Qualität)
            return cropped.resize((width, height), Image.LANCZOS)
            
        except Exception as e:
            # Bei Fehler: Original zurückgeben
            return tile_img
    
    def render_to_canvas(self, canvas, scale=1.0, offset_x=0, offset_y=0):
        """
        Rendert SVG direkt auf ein Tkinter Canvas
        
        Args:
            canvas: Tkinter Canvas Widget
            scale: Zoom-Faktor
            offset_x, offset_y: Pan-Offset in Pixeln
        """
        # Canvas-Größe
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            print("⚠️ Canvas noch nicht initialisiert")
            return False
        
        # Render-Größe mit Zoom berechnen
        render_width = int(canvas_width * scale)
        render_height = int(canvas_height * scale)
        
        # Bild rendern
        image = self.render_to_size(render_width, render_height, cache=True)
        
        if not image:
            return False
        
        # Für Tkinter konvertieren
        photo = ImageTk.PhotoImage(image)
        
        # Auf Canvas zeichnen
        canvas.delete("all")
        canvas.create_image(
            offset_x,
            offset_y,
            image=photo,
            anchor=tk.NW,
            tags="svg_map"
        )
        
        # Referenz behalten (wichtig für Tkinter!)
        canvas.image = photo
        
        return True
    
    def get_svg_dimensions(self):
        """Liest die nativen SVG-Dimensionen aus"""
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(self.svg_data)
            width = root.get('width')
            height = root.get('height')
            
            # Px entfernen falls vorhanden
            if width and 'px' in width:
                width = width.replace('px', '')
            if height and 'px' in height:
                height = height.replace('px', '')
            
            return int(width), int(height)
            
        except Exception as e:
            print(f"⚠️ Fehler beim Auslesen der SVG-Dimensionen: {e}")
            return None, None
    
    def clear_cache(self):
        """Löscht den Render-Cache"""
        self.cached_render = None
        self.cached_size = None
        print("🗑️ Render-Cache geleert")
    
    def update_fog(self, fog_data):
        """
        Aktualisiert Fog of War in der SVG
        
        Args:
            fog_data: Dictionary {(x,y): visible}
        """
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(self.svg_data)
            
            # Finde fog-of-war Gruppe
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            fog_group = root.find(".//*[@id='fog-of-war']", ns)
            
            if fog_group is None:
                print("⚠️ Keine fog-of-war Gruppe gefunden")
                return False
            
            # Alle existierenden Nebel-Elemente löschen
            for child in list(fog_group):
                fog_group.remove(child)
            
            # Neue Nebel-Rechtecke hinzufügen
            for (x, y), visible in fog_data.items():
                if not visible:
                    fog_rect = ET.SubElement(fog_group, 'rect', {
                        'x': str(x * 256),  # TODO: Tile-Size aus SVG lesen
                        'y': str(y * 256),
                        'width': '256',
                        'height': '256',
                        'fill': '#000000',
                        'data-fog': 'true',
                        'data-grid': f"{x},{y}"
                    })
            
            # SVG-Daten aktualisieren
            self.svg_data = ET.tostring(root, encoding='unicode')
            
            # Cache invalidieren
            self.clear_cache()
            
            print(f"✅ Nebel aktualisiert ({len([v for v in fog_data.values() if not v])} verdeckte Tiles)")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Aktualisieren des Nebels: {e}")
            return False
    
    def toggle_layer(self, layer_id, visible):
        """
        Schaltet Layer sichtbar/unsichtbar
        
        Args:
            layer_id: ID des Layers ('grid-overlay', 'fog-of-war', etc.)
            visible: True = sichtbar, False = versteckt
        """
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(self.svg_data)
            layer = root.find(f".//*[@id='{layer_id}']")
            
            if layer is not None:
                layer.set('visibility', 'visible' if visible else 'hidden')
                self.svg_data = ET.tostring(root, encoding='unicode')
                self.clear_cache()
                print(f"✅ Layer '{layer_id}' {'eingeblendet' if visible else 'ausgeblendet'}")
                return True
            else:
                print(f"⚠️ Layer '{layer_id}' nicht gefunden")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Toggle Layer: {e}")
            return False


class SVGProjectorWindow:
    """Projektor-Fenster mit SVG-Rendering"""
    
    def __init__(self, svg_path, fullscreen=False):
        self.svg_path = svg_path
        self.window = tk.Toplevel()
        self.window.title("SVG Projektor - Der Eine Ring")
        
        if fullscreen:
            self.window.attributes('-fullscreen', True)
            self.window.configure(bg='black')
        
        # Menu-Leiste
        self.setup_menu()
        
        # SVG Renderer
        self.renderer = SVGProjectorRenderer(svg_path)
        
        # Canvas
        self.canvas = tk.Canvas(
            self.window,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Zoom/Pan State
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Controls
        self.setup_controls()
        
        # Initial render
        self.window.after(100, self.render)
    
    def setup_menu(self):
        """Erstellt Menu-Leiste"""
        from tkinter import filedialog, messagebox
        
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        # Datei-Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="📂 SVG öffnen...", command=self.load_svg)
        file_menu.add_separator()
        file_menu.add_command(label="❌ Schließen", command=self.window.destroy)
    
    def load_svg(self):
        """Lädt eine neue SVG-Datei"""
        from tkinter import filedialog, messagebox
        
        svg_file = filedialog.askopenfilename(
            title="SVG-Karte auswählen",
            initialdir="maps",
            filetypes=[
                ("Alle Dateien", "*.*"),
                ("SVG-Dateien", "*.svg")
            ]
        )
        
        if svg_file and os.path.exists(svg_file):
            try:
                # Neuen Renderer erstellen
                self.svg_path = svg_file
                self.renderer = SVGProjectorRenderer(svg_file)
                
                # View zurücksetzen
                self.scale = 1.0
                self.offset_x = 0
                self.offset_y = 0
                
                # Neu rendern
                self.render()
                
                # Titel aktualisieren
                filename = os.path.basename(svg_file)
                self.window.title(f"SVG Projektor - {filename}")
                
                messagebox.showinfo("Erfolg", f"SVG geladen:\n{filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"SVG konnte nicht geladen werden:\n{e}")
    
    def setup_controls(self):
        """Tastatur-Steuerung"""
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        self.window.bind('<F11>', lambda e: self.toggle_fullscreen())
        self.window.bind('<plus>', lambda e: self.zoom_in())
        self.window.bind('<minus>', lambda e: self.zoom_out())
        self.window.bind('<r>', lambda e: self.reset_view())
        
        # Grid toggle
        self.window.bind('<g>', lambda e: self.toggle_grid())
        self.window.bind('<f>', lambda e: self.toggle_fog())
    
    def render(self):
        """Rendert die Karte"""
        self.renderer.render_to_canvas(
            self.canvas,
            scale=self.scale,
            offset_x=self.offset_x,
            offset_y=self.offset_y
        )
    
    def zoom_in(self):
        """Zoom rein"""
        self.scale *= 1.2
        self.renderer.clear_cache()
        self.render()
    
    def zoom_out(self):
        """Zoom raus"""
        self.scale /= 1.2
        self.renderer.clear_cache()
        self.render()
    
    def reset_view(self):
        """Setzt Ansicht zurück"""
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.renderer.clear_cache()
        self.render()
    
    def toggle_fullscreen(self):
        """Vollbild an/aus"""
        current = self.window.attributes('-fullscreen')
        self.window.attributes('-fullscreen', not current)
    
    def toggle_grid(self):
        """Grid ein/ausblenden"""
        # TODO: State tracking
        self.renderer.toggle_layer('grid-overlay', True)
        self.render()
    
    def toggle_fog(self):
        """Nebel ein/ausblenden"""
        self.renderer.toggle_layer('fog-of-war', True)
        self.render()


def test_svg_projector():
    """Test des SVG-Projektors"""
    import sys
    
    if len(sys.argv) > 1:
        svg_path = sys.argv[1]
    else:
        svg_path = "test_map.svg"
    
    if not os.path.exists(svg_path):
        print(f"❌ SVG nicht gefunden: {svg_path}")
        return
    
    root = tk.Tk()
    root.withdraw()  # Hauptfenster verstecken
    
    projector = SVGProjectorWindow(svg_path, fullscreen=False)
    
    root.mainloop()


if __name__ == "__main__":
    test_svg_projector()
