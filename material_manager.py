"""
Material Manager für "Der Eine Ring"
Verwaltung aller Materialien mit scrollbarer, ein-/ausklappbarer Leiste
"""
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from texture_editor import TextureEditor


class MaterialBar(tk.Frame):
    """
    Ein-/ausklappbare Material-Leiste oben im Editor
    Scrollbar, A-Z sortiert, mit Preview-Bildern
    """
    
    def __init__(self, parent, renderer, on_material_select=None, tile_size=32):
        super().__init__(parent, bg="#1a1a1a")
        
        self.renderer = renderer
        self.on_material_select = on_material_select
        self.tile_size = tile_size  # Für TextureEditor
        
        self.is_collapsed = False
        self.selected_material = None
        
        # Preview-Größe für Material-Buttons
        self.preview_size = 48
        
        # PhotoImage-Cache (wichtig für Tkinter)
        self.photo_cache = {}
        
        self.setup_ui()
        self.refresh_materials()
    
    def setup_ui(self):
        """UI erstellen"""
        # Toggle-Bar (immer sichtbar)
        self.toggle_bar = tk.Frame(self, bg="#0a0a0a", height=30)
        self.toggle_bar.pack(side=tk.TOP, fill=tk.X)
        self.toggle_bar.pack_propagate(False)
        
        # Toggle-Button
        self.toggle_button = tk.Button(
            self.toggle_bar,
            text="▼ Materialien",
            bg="#0a0a0a",
            fg="#d4af37",
            font=("Arial", 11, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self.toggle_collapse
        )
        self.toggle_button.pack(side=tk.LEFT, padx=10, pady=2)
        
        # Aktionen-Buttons (rechts)
        action_frame = tk.Frame(self.toggle_bar, bg="#0a0a0a")
        action_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(
            action_frame,
            text="➕ Neu",
            bg="#2a7d2a",
            fg="white",
            font=("Arial", 9),
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor="hand2",
            command=self.create_new_material
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            action_frame,
            text="✏️ Bearbeiten",
            bg="#2a5d8d",
            fg="white",
            font=("Arial", 9),
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor="hand2",
            command=self.edit_selected_material
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            action_frame,
            text="🔄 Aktualisieren",
            bg="#7d5d2a",
            fg="white",
            font=("Arial", 9),
            relief=tk.FLAT,
            padx=10,
            pady=2,
            cursor="hand2",
            command=self.refresh_materials
        ).pack(side=tk.LEFT, padx=2)
        
        # Content-Frame (ein-/ausklappbar) - MIT MAXIMALER HÖHE
        self.content_frame = tk.Frame(self, bg="#1a1a1a", height=150)
        self.content_frame.pack(side=tk.TOP, fill=tk.X)
        self.content_frame.pack_propagate(False)  # Höhe beibehalten
        
        # Canvas mit Scrollbar für Materialien
        canvas_container = tk.Frame(self.content_frame, bg="#1a1a1a")
        canvas_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Horizontale Scrollbar
        h_scrollbar = tk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas - KEINE feste Höhe, passt sich an
        self.materials_canvas = tk.Canvas(
            canvas_container,
            bg="#1a1a1a",
            highlightthickness=0,
            xscrollcommand=h_scrollbar.set
        )
        self.materials_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        h_scrollbar.config(command=self.materials_canvas.xview)
        
        # Frame INNERHALB des Canvas für die Material-Buttons
        self.materials_inner_frame = tk.Frame(self.materials_canvas, bg="#1a1a1a")
        self.canvas_frame = self.materials_canvas.create_window(
            (0, 0),
            window=self.materials_inner_frame,
            anchor=tk.NW
        )
        
        # Scrollregion aktualisieren wenn sich Größe ändert
        self.materials_inner_frame.bind(
            "<Configure>",
            lambda e: self.materials_canvas.configure(
                scrollregion=self.materials_canvas.bbox("all")
            )
        )
        
        # Mausrad-Scroll
        self.materials_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        """Mausrad-Scrolling (horizontal)"""
        if self.materials_canvas.winfo_containing(event.x_root, event.y_root) == self.materials_canvas:
            self.materials_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def toggle_collapse(self):
        """Klappt die Material-Leiste ein/aus"""
        if self.is_collapsed:
            # Ausklappen
            self.content_frame.pack(side=tk.TOP, fill=tk.X)
            self.toggle_button.config(text="▼ Materialien")
            self.is_collapsed = False
        else:
            # Einklappen
            self.content_frame.pack_forget()
            self.toggle_button.config(text="▶ Materialien")
            self.is_collapsed = True
    
    def refresh_materials(self):
        """Lädt und zeigt alle Materialien neu"""
        # Lösche alte Buttons
        for widget in self.materials_inner_frame.winfo_children():
            widget.destroy()
        
        # Cache leeren
        self.photo_cache.clear()
        
        # Alle Materialien holen (sortiert A-Z)
        materials = self.renderer.get_all_materials()
        
        # Material-Buttons erstellen
        for idx, (mat_id, mat_data) in enumerate(materials.items()):
            self.create_material_button(mat_id, mat_data, idx)
        
        # Scrollregion aktualisieren
        self.materials_inner_frame.update_idletasks()
        self.materials_canvas.configure(scrollregion=self.materials_canvas.bbox("all"))
    
    def create_material_button(self, material_id, material_data, index):
        """Erstellt einen Button für ein Material"""
        # Frame für Material-Button
        mat_frame = tk.Frame(
            self.materials_inner_frame,
            bg="#2a2a2a",
            relief=tk.RAISED,
            bd=2,
            cursor="hand2"
        )
        mat_frame.grid(row=0, column=index, padx=5, pady=5, sticky=tk.N)
        
        # Preview-Bild generieren
        try:
            texture_img = self.renderer.get_texture(material_id, self.preview_size, 0)
            
            # SPECIAL: Village (und andere extended tiles) müssen zugeschnitten werden
            if texture_img.size[0] > self.preview_size or texture_img.size[1] > self.preview_size:
                # Schneide den relevanten Teil aus (unten, wo das Gebäude ist)
                # Bei village ist das Gebäude im untersten Drittel des 3x Canvas
                orig_size = texture_img.size[0] // 3  # Original tile size
                # Extrahiere das unterste Tile (dort ist das Gebäude)
                texture_img = texture_img.crop((0, orig_size * 2, orig_size, orig_size * 3))
                # Skaliere auf Preview-Größe
                texture_img = texture_img.resize((self.preview_size, self.preview_size), Image.LANCZOS)
            
            photo = ImageTk.PhotoImage(texture_img)
            self.photo_cache[material_id] = photo  # WICHTIG: Referenz behalten!
        except Exception as e:
            print(f"Fehler beim Laden der Textur für {material_id}: {e}")
            photo = None
        
        # Preview-Label (Bild)
        preview_label = tk.Label(
            mat_frame,
            image=photo,
            bg="#2a2a2a",
            width=self.preview_size,
            height=self.preview_size
        )
        preview_label.pack(padx=2, pady=2)
        
        # Name-Label
        name_text = material_data.get("name", material_id)
        emoji = material_data.get("emoji", "")
        
        name_label = tk.Label(
            mat_frame,
            text=f"{emoji} {name_text}",
            bg="#2a2a2a",
            fg="white",
            font=("Arial", 8),
            wraplength=self.preview_size + 10
        )
        name_label.pack(pady=(0, 2))
        
        # Animation-Indikator
        if material_data.get("animated", False):
            anim_label = tk.Label(
                mat_frame,
                text="🎬",
                bg="#2a2a2a",
                fg="#d4af37",
                font=("Arial", 7)
            )
            anim_label.pack()
        
        # Click-Handler
        def on_click(event=None):
            self.select_material(material_id, mat_frame)
        
        mat_frame.bind("<Button-1>", on_click)
        preview_label.bind("<Button-1>", on_click)
        name_label.bind("<Button-1>", on_click)
        
        # Doppelklick zum Bearbeiten
        def on_double_click(event=None):
            self.edit_material(material_id)
        
        mat_frame.bind("<Double-Button-1>", on_double_click)
        preview_label.bind("<Double-Button-1>", on_double_click)
        name_label.bind("<Double-Button-1>", on_double_click)
    
    def select_material(self, material_id, frame):
        """Wählt ein Material aus"""
        # Alte Auswahl zurücksetzen
        for widget in self.materials_inner_frame.winfo_children():
            widget.config(relief=tk.RAISED, bg="#2a2a2a")
            for child in widget.winfo_children():
                child.config(bg="#2a2a2a")
        
        # Neue Auswahl hervorheben
        frame.config(relief=tk.SUNKEN, bg="#2a5d8d")
        for child in frame.winfo_children():
            child.config(bg="#2a5d8d")
        
        self.selected_material = material_id
        
        # Callback aufrufen
        if self.on_material_select:
            self.on_material_select(material_id)
    
    def create_new_material(self):
        """Öffnet Editor für neues Material"""
        editor = TextureEditor(
            self,
            material_id=None,
            material_name="Neues Material",
            base_color=(200, 200, 200),
            renderer=self.renderer,
            on_save_callback=lambda mat_id: self.refresh_materials(),
            tile_size=self.tile_size
        )
    
    def edit_selected_material(self):
        """Bearbeitet das ausgewählte Material"""
        if not self.selected_material:
            messagebox.showinfo("Kein Material", "Bitte wählen Sie zuerst ein Material aus!")
            return
        
        self.edit_material(self.selected_material)
    
    def edit_material(self, material_id):
        """Öffnet Editor für existierendes Material"""
        materials = self.renderer.get_all_materials()
        material_data = materials.get(material_id)
        
        if not material_data:
            messagebox.showerror("Fehler", "Material nicht gefunden!")
            return
        
        # Prüfe ob es ein Basis-Material ist
        if material_id in self.renderer.base_materials and material_id not in self.renderer.custom_textures:
            # Basis-Material: Kopie erstellen?
            response = messagebox.askyesno(
                "Basis-Material",
                f"'{material_data['name']}' ist ein Basis-Material.\n\n"
                "Möchten Sie eine angepasste Version erstellen?",
                icon='question'
            )
            
            if response:
                # Neue Custom-Version erstellen
                editor = TextureEditor(
                    self,
                    material_id=None,
                    material_name=f"{material_data['name']} (Angepasst)",
                    base_color=material_data.get("color", (128, 128, 128)),
                    renderer=self.renderer,
                    on_save_callback=lambda mat_id: self.refresh_materials(),
                    tile_size=self.tile_size
                )
        else:
            # Custom-Material bearbeiten
            editor = TextureEditor(
                self,
                material_id=material_id,
                material_name=material_data.get("name", material_id),
                base_color=material_data.get("color", (128, 128, 128)),
                renderer=self.renderer,
                on_save_callback=lambda mat_id: self.refresh_materials(),
                tile_size=self.tile_size
            )
    
    def get_selected_material(self):
        """Gibt das aktuell ausgewählte Material zurück"""
        return self.selected_material


class MaterialManagerWindow(tk.Toplevel):
    """
    Eigenständiges Fenster für Material-Management
    """
    
    def __init__(self, parent, renderer):
        super().__init__(parent)
        
        self.renderer = renderer
        
        self.title("Material-Manager - Der Eine Ring")
        self.geometry("800x600")
        self.configure(bg="#2a2a2a")
        
        self.setup_ui()
    
    def setup_ui(self):
        """UI erstellen"""
        # Header
        header = tk.Frame(self, bg="#1a1a1a")
        header.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header,
            text="🎨 Material-Manager",
            font=("Arial", 18, "bold"),
            bg="#1a1a1a",
            fg="#d4af37"
        ).pack(pady=10)
        
        tk.Label(
            header,
            text="Verwalte alle Terrain-Materialien und erstelle eigene Texturen",
            font=("Arial", 10),
            bg="#1a1a1a",
            fg="#888888"
        ).pack(pady=(0, 10))
        
        # Material-Liste mit Details
        list_frame = tk.Frame(self, bg="#2a2a2a", relief=tk.SUNKEN, bd=2)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        v_scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        h_scrollbar = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Listbox/Treeview für Materialien
        columns = ("emoji", "name", "type", "animated")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="tree headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        
        # Spalten konfigurieren
        self.tree.heading("#0", text="ID")
        self.tree.heading("emoji", text="")
        self.tree.heading("name", text="Name")
        self.tree.heading("type", text="Typ")
        self.tree.heading("animated", text="Animiert")
        
        self.tree.column("#0", width=150)
        self.tree.column("emoji", width=40, anchor=tk.CENTER)
        self.tree.column("name", width=200)
        self.tree.column("type", width=100)
        self.tree.column("animated", width=80, anchor=tk.CENTER)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        # Buttons
        button_frame = tk.Frame(self, bg="#2a2a2a")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            button_frame,
            text="➕ Neues Material",
            bg="#2a7d2a",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            command=self.create_new_material
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="✏️ Bearbeiten",
            bg="#2a5d8d",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            command=self.edit_selected
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="🗑️ Löschen",
            bg="#7d2a2a",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            command=self.delete_selected
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="📤 Exportieren",
            bg="#5d2a7d",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8,
            command=self.export_selected
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame,
            text="❌ Schließen",
            bg="#555555",
            fg="white",
            font=("Arial", 11),
            padx=20,
            pady=8,
            command=self.destroy
        ).pack(side=tk.RIGHT, padx=5)
        
        # Materialien laden
        self.refresh_list()
    
    def refresh_list(self):
        """Aktualisiert die Material-Liste"""
        # Alte Einträge löschen
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Materialien holen
        materials = self.renderer.get_all_materials()
        
        # Einträge hinzufügen
        for mat_id, mat_data in materials.items():
            # Typ bestimmen
            if mat_id in self.renderer.base_materials:
                mat_type = "Basis"
            else:
                mat_type = "Custom"
            
            # Animiert?
            animated = "Ja" if mat_data.get("animated", False) else "Nein"
            
            self.tree.insert(
                "",
                tk.END,
                text=mat_id,
                values=(
                    mat_data.get("emoji", "🎨"),
                    mat_data.get("name", mat_id),
                    mat_type,
                    animated
                )
            )
    
    def create_new_material(self):
        """Erstellt ein neues Material"""
        editor = TextureEditor(
            self,
            material_id=None,
            material_name="Neues Material",
            base_color=(200, 200, 200),
            renderer=self.renderer,
            on_save_callback=lambda mat_id: self.refresh_list()
        )
    
    def edit_selected(self):
        """Bearbeitet das ausgewählte Material"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Keine Auswahl", "Bitte wählen Sie ein Material aus!")
            return
        
        item = selection[0]
        material_id = self.tree.item(item, "text")
        
        materials = self.renderer.get_all_materials()
        material_data = materials.get(material_id)
        
        if not material_data:
            return
        
        # Basis-Material?
        if material_id in self.renderer.base_materials and material_id not in self.renderer.custom_textures:
            response = messagebox.askyesno(
                "Basis-Material",
                f"'{material_data['name']}' ist ein Basis-Material.\n\n"
                "Möchten Sie eine angepasste Version erstellen?"
            )
            
            if not response:
                return
            
            # Neue Custom-Version
            editor = TextureEditor(
                self,
                material_id=None,
                material_name=f"{material_data['name']} (Angepasst)",
                base_color=material_data.get("color", (128, 128, 128)),
                renderer=self.renderer,
                on_save_callback=lambda mat_id: self.refresh_list()
            )
        else:
            # Custom bearbeiten
            editor = TextureEditor(
                self,
                material_id=material_id,
                material_name=material_data.get("name", material_id),
                base_color=material_data.get("color", (128, 128, 128)),
                renderer=self.renderer,
                on_save_callback=lambda mat_id: self.refresh_list()
            )
    
    def delete_selected(self):
        """Löscht das ausgewählte Material (nur Custom)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Keine Auswahl", "Bitte wählen Sie ein Material aus!")
            return
        
        item = selection[0]
        material_id = self.tree.item(item, "text")
        
        # Nur Custom-Materialien können gelöscht werden
        if material_id in self.renderer.base_materials and material_id not in self.renderer.custom_textures:
            messagebox.showinfo("Basis-Material", "Basis-Materialien können nicht gelöscht werden!")
            return
        
        # Bestätigung
        materials = self.renderer.get_all_materials()
        material_name = materials[material_id].get("name", material_id)
        
        if messagebox.askyesno("Löschen bestätigen", f"Material '{material_name}' wirklich löschen?"):
            # Aus custom_textures entfernen
            if material_id in self.renderer.custom_textures:
                del self.renderer.custom_textures[material_id]
                self.renderer.save_custom_materials()
                self.refresh_list()
                messagebox.showinfo("Erfolg", "Material wurde gelöscht!")
    
    def export_selected(self):
        """Exportiert die Textur des ausgewählten Materials"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Keine Auswahl", "Bitte wählen Sie ein Material aus!")
            return
        
        item = selection[0]
        material_id = self.tree.item(item, "text")
        
        try:
            filename = self.renderer.export_texture(material_id, size=256)
            messagebox.showinfo("Erfolg", f"Textur exportiert nach:\n{filename}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Exportieren:\n{e}")
