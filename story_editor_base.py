"""
Story Editor - Teil 1: Basis-UI
================================

Hauptfenster, Menü und Toolbar für den Storyboard-Editor.

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable
import os

# Import der Storyboard-Komponenten
from storyboard_system import (
    Storyboard, Chapter, Scene, Trigger, Action, Overlay,
    SceneType, TriggerType, ActionType, StoryboardEngine
)


class StoryEditorWindow(tk.Toplevel):
    """
    Hauptfenster des Story-Editors
    """
    
    def __init__(self, parent, storyboard: Optional[Storyboard] = None):
        super().__init__(parent)
        
        self.title("🎬 Story Editor - Der Eine Ring VTT")
        self.configure(bg="#1a1a2e")
        
        # Fenstergröße
        self.geometry("1400x900")
        self.minsize(1000, 700)
        
        # Storyboard
        self.storyboard = storyboard or Storyboard(name="Neues Abenteuer")
        self.current_chapter: Optional[Chapter] = None
        self.current_scene: Optional[Scene] = None
        
        # Unsaved Changes Tracking
        self.has_unsaved_changes = False
        self._current_file_path: Optional[str] = None
        
        # Callbacks für externe Integration
        self.on_scene_preview: Optional[Callable[[Scene], None]] = None
        self.on_storyboard_save: Optional[Callable[[Storyboard], None]] = None
        
        # UI Setup
        self._setup_menu()
        self._setup_toolbar()
        self._setup_main_layout()
        self._setup_statusbar()
        
        # Keyboard Shortcuts
        self._setup_shortcuts()
        
        # Initial Update
        self._refresh_chapter_list()
        self._update_title()
        
        # Close Handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _setup_menu(self):
        """Erstellt das Hauptmenü"""
        self.menubar = tk.Menu(self, bg="#2a2a4e", fg="white")
        self.config(menu=self.menubar)
        
        # Datei-Menü
        file_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="📁 Datei", menu=file_menu)
        
        file_menu.add_command(label="Neu", command=self._new_storyboard, accelerator="Ctrl+N")
        file_menu.add_command(label="Öffnen...", command=self._open_storyboard, accelerator="Ctrl+O")
        file_menu.add_command(label="Speichern", command=self._save_storyboard, accelerator="Ctrl+S")
        file_menu.add_command(label="Speichern unter...", command=self._save_storyboard_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exportieren als JSON...", command=self._export_json)
        file_menu.add_separator()
        file_menu.add_command(label="Schließen", command=self._on_close)
        
        # Bearbeiten-Menü
        edit_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="✏️ Bearbeiten", menu=edit_menu)
        
        edit_menu.add_command(label="Rückgängig", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Wiederholen", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Kapitel hinzufügen", command=self._add_chapter)
        edit_menu.add_command(label="Szene hinzufügen", command=self._add_scene)
        edit_menu.add_separator()
        edit_menu.add_command(label="Ausgewähltes löschen", command=self._delete_selected, accelerator="Del")
        
        # Ansicht-Menü
        view_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="👁️ Ansicht", menu=view_menu)
        
        self.show_flow_graph = tk.BooleanVar(value=True)
        self.show_properties = tk.BooleanVar(value=True)
        
        view_menu.add_checkbutton(label="Flow-Graph anzeigen", variable=self.show_flow_graph,
                                  command=self._toggle_flow_graph)
        view_menu.add_checkbutton(label="Eigenschaften anzeigen", variable=self.show_properties,
                                  command=self._toggle_properties)
        view_menu.add_separator()
        view_menu.add_command(label="Alles einblenden", command=self._show_all_panels)
        
        # Hilfe-Menü
        help_menu = tk.Menu(self.menubar, tearoff=0, bg="#2a2a4e", fg="white")
        self.menubar.add_cascade(label="❓ Hilfe", menu=help_menu)
        
        help_menu.add_command(label="Tastenkürzel...", command=self._show_shortcuts)
        help_menu.add_command(label="Über Story Editor...", command=self._show_about)
    
    def _setup_toolbar(self):
        """Erstellt die Toolbar"""
        self.toolbar = tk.Frame(self, bg="#16213e", height=50)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.toolbar.pack_propagate(False)
        
        # Linke Seite: Datei-Operationen
        left_frame = tk.Frame(self.toolbar, bg="#16213e")
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        self._create_toolbar_button(left_frame, "📄", "Neu", self._new_storyboard)
        self._create_toolbar_button(left_frame, "📂", "Öffnen", self._open_storyboard)
        self._create_toolbar_button(left_frame, "💾", "Speichern", self._save_storyboard)
        
        # Separator
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Mitte: Kapitel/Szenen-Operationen
        mid_frame = tk.Frame(self.toolbar, bg="#16213e")
        mid_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        self._create_toolbar_button(mid_frame, "📖", "Kapitel +", self._add_chapter)
        self._create_toolbar_button(mid_frame, "🎬", "Szene +", self._add_scene)
        self._create_toolbar_button(mid_frame, "⚡", "Trigger +", self._add_trigger)
        self._create_toolbar_button(mid_frame, "🎭", "Overlay +", self._add_overlay)
        
        # Separator
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # Rechte Seite: Vorschau und Test
        right_frame = tk.Frame(self.toolbar, bg="#16213e")
        right_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        self._create_toolbar_button(right_frame, "▶️", "Vorschau", self._preview_scene)
        self._create_toolbar_button(right_frame, "🎮", "Testen", self._test_storyboard)
        
        # Ganz rechts: Storyboard-Info
        info_frame = tk.Frame(self.toolbar, bg="#16213e")
        info_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        self.storyboard_name_label = tk.Label(
            info_frame,
            text=f"📚 {self.storyboard.name}",
            bg="#16213e", fg="#e94560",
            font=("Arial", 12, "bold")
        )
        self.storyboard_name_label.pack(side=tk.RIGHT)
    
    def _create_toolbar_button(self, parent, icon: str, tooltip: str, command: Callable):
        """Erstellt einen Toolbar-Button"""
        btn = tk.Button(
            parent,
            text=icon,
            font=("Arial", 16),
            bg="#0f3460",
            fg="white",
            activebackground="#e94560",
            activeforeground="white",
            relief=tk.FLAT,
            width=3,
            command=command
        )
        btn.pack(side=tk.LEFT, padx=2)
        
        # Tooltip (einfache Variante)
        btn.bind("<Enter>", lambda e, t=tooltip: self._show_tooltip(e, t))
        btn.bind("<Leave>", lambda e: self._hide_tooltip())
        
        return btn
    
    def _setup_main_layout(self):
        """Erstellt das Haupt-Layout mit PanedWindow"""
        # Haupt-PanedWindow (horizontal)
        self.main_paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            bg="#1a1a2e",
            sashwidth=5,
            sashrelief=tk.RAISED
        )
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Linkes Panel: Kapitel/Szenen-Liste
        self.left_panel = tk.Frame(self.main_paned, bg="#16213e", width=280)
        self.main_paned.add(self.left_panel, minsize=200)
        
        self._setup_chapter_panel()
        
        # Mittleres Panel: Flow-Graph (Platzhalter)
        self.center_panel = tk.Frame(self.main_paned, bg="#0f3460")
        self.main_paned.add(self.center_panel, minsize=400)
        
        self._setup_flow_graph_placeholder()
        
        # Rechtes Panel: Properties (Platzhalter)
        self.right_panel = tk.Frame(self.main_paned, bg="#16213e", width=320)
        self.main_paned.add(self.right_panel, minsize=250)
        
        self._setup_properties_placeholder()
    
    def _setup_chapter_panel(self):
        """Erstellt das Kapitel/Szenen-Panel (linke Seite)"""
        # Header
        header = tk.Frame(self.left_panel, bg="#0f3460")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header,
            text="📚 Kapitel & Szenen",
            bg="#0f3460", fg="white",
            font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Buttons
        btn_frame = tk.Frame(header, bg="#0f3460")
        btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(
            btn_frame, text="+📖", font=("Arial", 10),
            bg="#2a7d2a", fg="white", relief=tk.FLAT,
            command=self._add_chapter
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame, text="+🎬", font=("Arial", 10),
            bg="#2a5d8d", fg="white", relief=tk.FLAT,
            command=self._add_scene
        ).pack(side=tk.LEFT, padx=2)
        
        # Treeview für Kapitel/Szenen
        tree_frame = tk.Frame(self.left_panel, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview
        style = ttk.Style()
        style.configure("Story.Treeview",
                       background="#1a1a2e",
                       foreground="white",
                       fieldbackground="#1a1a2e",
                       rowheight=28)
        style.map("Story.Treeview",
                 background=[("selected", "#e94560")],
                 foreground=[("selected", "white")])
        
        self.chapter_tree = ttk.Treeview(
            tree_frame,
            style="Story.Treeview",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        self.chapter_tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.chapter_tree.yview)
        
        # Spalten konfigurieren
        self.chapter_tree["columns"] = ("type", "info")
        self.chapter_tree.column("#0", width=180, minwidth=150)
        self.chapter_tree.column("type", width=50, minwidth=50)
        self.chapter_tree.column("info", width=40, minwidth=40)
        
        self.chapter_tree.heading("#0", text="Name")
        self.chapter_tree.heading("type", text="Typ")
        self.chapter_tree.heading("info", text="Info")
        
        # Events
        self.chapter_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.chapter_tree.bind("<Double-1>", self._on_tree_double_click)
        self.chapter_tree.bind("<Delete>", lambda e: self._delete_selected())
    
    def _setup_flow_graph_placeholder(self):
        """Platzhalter für Flow-Graph (wird in Teil 3 implementiert)"""
        placeholder = tk.Frame(self.center_panel, bg="#0f3460")
        placeholder.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas für Flow-Graph
        self.flow_canvas = tk.Canvas(
            placeholder,
            bg="#1a1a2e",
            highlightthickness=1,
            highlightbackground="#e94560"
        )
        self.flow_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Platzhalter-Text
        self.flow_canvas.create_text(
            400, 300,
            text="🔗 Flow-Graph\n\nWähle eine Szene aus der Liste,\num ihre Verbindungen zu sehen.",
            fill="#666",
            font=("Arial", 14),
            justify=tk.CENTER
        )
        
        # Wird später mit echtem Flow-Graph ersetzt
        self.flow_graph = None
    
    def _setup_properties_placeholder(self):
        """Platzhalter für Properties-Panel (wird in Teil 4 implementiert)"""
        # Header
        header = tk.Frame(self.right_panel, bg="#0f3460")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            header,
            text="⚙️ Eigenschaften",
            bg="#0f3460", fg="white",
            font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Scrollbarer Bereich
        self.props_canvas = tk.Canvas(self.right_panel, bg="#16213e", highlightthickness=0)
        props_scrollbar = ttk.Scrollbar(self.right_panel, orient=tk.VERTICAL, command=self.props_canvas.yview)
        
        self.props_frame = tk.Frame(self.props_canvas, bg="#16213e")
        
        self.props_canvas.create_window((0, 0), window=self.props_frame, anchor=tk.NW)
        self.props_canvas.configure(yscrollcommand=props_scrollbar.set)
        
        props_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.props_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.props_frame.bind("<Configure>", 
            lambda e: self.props_canvas.configure(scrollregion=self.props_canvas.bbox("all")))
        
        # Platzhalter
        tk.Label(
            self.props_frame,
            text="Wähle ein Element aus,\num seine Eigenschaften\nzu bearbeiten.",
            bg="#16213e", fg="#666",
            font=("Arial", 10),
            justify=tk.CENTER
        ).pack(pady=50)
    
    def _setup_statusbar(self):
        """Erstellt die Statusleiste"""
        self.statusbar = tk.Frame(self, bg="#0f3460", height=25)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.statusbar.pack_propagate(False)
        
        # Status-Text
        self.status_label = tk.Label(
            self.statusbar,
            text="Bereit",
            bg="#0f3460", fg="#aaa",
            font=("Arial", 9),
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # Statistiken rechts
        self.stats_label = tk.Label(
            self.statusbar,
            text="0 Kapitel | 0 Szenen",
            bg="#0f3460", fg="#888",
            font=("Arial", 9)
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)
    
    def _setup_shortcuts(self):
        """Keyboard Shortcuts"""
        self.bind("<Control-n>", lambda e: self._new_storyboard())
        self.bind("<Control-o>", lambda e: self._open_storyboard())
        self.bind("<Control-s>", lambda e: self._save_storyboard())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<F5>", lambda e: self._preview_scene())
    
    # ============================================================
    # DATEI-OPERATIONEN
    # ============================================================
    
    def _new_storyboard(self):
        """Neues Storyboard erstellen"""
        if self.has_unsaved_changes:
            if not messagebox.askyesno("Ungespeicherte Änderungen",
                                       "Es gibt ungespeicherte Änderungen. Trotzdem fortfahren?"):
                return
        
        self.storyboard = Storyboard(name="Neues Abenteuer")
        self.current_chapter = None
        self.current_scene = None
        self._current_file_path = None
        self.has_unsaved_changes = False
        
        self._refresh_chapter_list()
        self._update_title()
        self._set_status("Neues Storyboard erstellt")
    
    def _open_storyboard(self):
        """Storyboard öffnen"""
        if self.has_unsaved_changes:
            if not messagebox.askyesno("Ungespeicherte Änderungen",
                                       "Es gibt ungespeicherte Änderungen. Trotzdem fortfahren?"):
                return
        
        filepath = filedialog.askopenfilename(
            title="Storyboard öffnen",
            filetypes=[("Storyboard JSON", "*.story.json"), ("JSON", "*.json"), ("Alle", "*.*")],
            defaultextension=".story.json"
        )
        
        if filepath:
            try:
                self.storyboard = Storyboard.load(filepath)
                self._current_file_path = filepath
                self.has_unsaved_changes = False
                
                self._refresh_chapter_list()
                self._update_title()
                self._set_status(f"Geladen: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Datei nicht laden:\n{e}")
    
    def _save_storyboard(self):
        """Storyboard speichern"""
        if self._current_file_path:
            try:
                self.storyboard.save(self._current_file_path)
                self.has_unsaved_changes = False
                self._update_title()
                self._set_status(f"Gespeichert: {os.path.basename(self._current_file_path)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte nicht speichern:\n{e}")
        else:
            self._save_storyboard_as()
    
    def _save_storyboard_as(self):
        """Storyboard unter neuem Namen speichern"""
        filepath = filedialog.asksaveasfilename(
            title="Storyboard speichern",
            filetypes=[("Storyboard JSON", "*.story.json"), ("JSON", "*.json")],
            defaultextension=".story.json",
            initialfile=f"{self.storyboard.name}.story.json"
        )
        
        if filepath:
            try:
                self.storyboard.save(filepath)
                self._current_file_path = filepath
                self.has_unsaved_changes = False
                self._update_title()
                self._set_status(f"Gespeichert: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte nicht speichern:\n{e}")
    
    def _export_json(self):
        """Als Standard-JSON exportieren"""
        filepath = filedialog.asksaveasfilename(
            title="Als JSON exportieren",
            filetypes=[("JSON", "*.json")],
            defaultextension=".json",
            initialfile=f"{self.storyboard.name}_export.json"
        )
        
        if filepath:
            try:
                import json
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.storyboard.to_dict(), f, indent=2, ensure_ascii=False)
                self._set_status(f"Exportiert: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
    
    # ============================================================
    # BEARBEITEN-OPERATIONEN
    # ============================================================
    
    def _add_chapter(self):
        """Neues Kapitel hinzufügen"""
        from tkinter import simpledialog
        
        name = simpledialog.askstring("Neues Kapitel", "Name des Kapitels:", parent=self)
        if name:
            chapter = Chapter(name=name, order=len(self.storyboard.chapters))
            self.storyboard.chapters.append(chapter)
            
            self._mark_changed()
            self._refresh_chapter_list()
            self._set_status(f"Kapitel '{name}' hinzugefügt")
    
    def _add_scene(self):
        """Neue Szene zum aktuellen Kapitel hinzufügen"""
        if not self.current_chapter:
            messagebox.showwarning("Kein Kapitel", "Bitte wähle zuerst ein Kapitel aus.")
            return
        
        from tkinter import simpledialog
        
        name = simpledialog.askstring("Neue Szene", "Name der Szene:", parent=self)
        if name:
            scene = Scene(name=name)
            self.current_chapter.scenes.append(scene)
            
            # Erste Szene = Start-Szene
            if len(self.current_chapter.scenes) == 1:
                self.current_chapter.start_scene_id = scene.id
            
            self._mark_changed()
            self._refresh_chapter_list()
            self._set_status(f"Szene '{name}' hinzugefügt")
    
    def _add_trigger(self):
        """Neuen Trigger zur aktuellen Szene hinzufügen"""
        if not self.current_scene:
            messagebox.showwarning("Keine Szene", "Bitte wähle zuerst eine Szene aus.")
            return
        
        trigger = Trigger(name="Neuer Trigger", trigger_type=TriggerType.CLICK)
        self.current_scene.triggers.append(trigger)
        
        self._mark_changed()
        self._refresh_properties()
        self._set_status("Trigger hinzugefügt")
    
    def _add_overlay(self):
        """Neues Overlay zur aktuellen Szene hinzufügen"""
        if not self.current_scene:
            messagebox.showwarning("Keine Szene", "Bitte wähle zuerst eine Szene aus.")
            return
        
        overlay = Overlay(name="Neues Overlay")
        self.current_scene.overlays.append(overlay)
        
        self._mark_changed()
        self._refresh_properties()
        self._set_status("Overlay hinzugefügt")
    
    def _delete_selected(self):
        """Ausgewähltes Element löschen"""
        selection = self.chapter_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        item_data = self.chapter_tree.item(item_id)
        item_type = item_data["values"][0] if item_data["values"] else ""
        
        if item_type == "📖":
            # Kapitel löschen
            if messagebox.askyesno("Löschen", "Kapitel wirklich löschen?\nAlle Szenen werden ebenfalls gelöscht!"):
                self.storyboard.chapters = [c for c in self.storyboard.chapters if c.id != item_id]
                self.current_chapter = None
                self.current_scene = None
                self._mark_changed()
                self._refresh_chapter_list()
        
        elif item_type == "🎬":
            # Szene löschen
            if messagebox.askyesno("Löschen", "Szene wirklich löschen?"):
                if self.current_chapter:
                    self.current_chapter.scenes = [s for s in self.current_chapter.scenes if s.id != item_id]
                    self.current_scene = None
                    self._mark_changed()
                    self._refresh_chapter_list()
    
    def _undo(self):
        """Rückgängig (Platzhalter)"""
        self._set_status("Undo noch nicht implementiert")
    
    def _redo(self):
        """Wiederholen (Platzhalter)"""
        self._set_status("Redo noch nicht implementiert")
    
    # ============================================================
    # VORSCHAU UND TEST
    # ============================================================
    
    def _preview_scene(self):
        """Aktuelle Szene im Projektor anzeigen"""
        if not self.current_scene:
            messagebox.showinfo("Keine Szene", "Bitte wähle eine Szene zum Vorschauen.")
            return
        
        if self.on_scene_preview:
            self.on_scene_preview(self.current_scene)
            self._set_status(f"Vorschau: {self.current_scene.name}")
        else:
            self._set_status("Vorschau nicht verfügbar (keine Callback-Funktion)")
    
    def _test_storyboard(self):
        """Storyboard im Test-Modus starten"""
        if not self.storyboard.chapters:
            messagebox.showwarning("Leer", "Das Storyboard hat keine Kapitel!")
            return
        
        self._set_status("Test-Modus gestartet...")
        # Wird später mit echtem Test-Modus verbunden
    
    # ============================================================
    # TREEVIEW-OPERATIONEN
    # ============================================================
    
    def _refresh_chapter_list(self):
        """Aktualisiert die Kapitel/Szenen-Liste"""
        # Alle Items entfernen
        for item in self.chapter_tree.get_children():
            self.chapter_tree.delete(item)
        
        # Kapitel und Szenen einfügen
        for chapter in self.storyboard.chapters:
            # Kapitel einfügen
            chapter_item = self.chapter_tree.insert(
                "",
                tk.END,
                iid=chapter.id,
                text=f"{chapter.icon} {chapter.name}",
                values=("📖", f"{len(chapter.scenes)}"),
                open=True
            )
            
            # Szenen des Kapitels
            for scene in chapter.scenes:
                scene_icon = self._get_scene_icon(scene.scene_type)
                trigger_count = len(scene.triggers)
                
                self.chapter_tree.insert(
                    chapter_item,
                    tk.END,
                    iid=scene.id,
                    text=f"{scene_icon} {scene.name}",
                    values=("🎬", f"⚡{trigger_count}")
                )
        
        # Stats aktualisieren
        total_chapters = len(self.storyboard.chapters)
        total_scenes = sum(len(c.scenes) for c in self.storyboard.chapters)
        self.stats_label.config(text=f"{total_chapters} Kapitel | {total_scenes} Szenen")
    
    def _get_scene_icon(self, scene_type: SceneType) -> str:
        """Gibt das passende Icon für einen Szenentyp zurück"""
        icons = {
            SceneType.VIDEO: "🎥",
            SceneType.MAP_JSON: "🗺️",
            SceneType.MAP_SVG: "📐",
            SceneType.IMAGE: "🖼️",
            SceneType.CUTSCENE: "🎞️"
        }
        return icons.get(scene_type, "🎬")
    
    def _on_tree_select(self, event):
        """Handler für Auswahl in der Baumliste"""
        selection = self.chapter_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        # Prüfen ob Kapitel oder Szene
        parent = self.chapter_tree.parent(item_id)
        
        if not parent:
            # Es ist ein Kapitel
            for chapter in self.storyboard.chapters:
                if chapter.id == item_id:
                    self.current_chapter = chapter
                    self.current_scene = None
                    self._refresh_properties()
                    break
        else:
            # Es ist eine Szene
            for chapter in self.storyboard.chapters:
                if chapter.id == parent:
                    self.current_chapter = chapter
                    for scene in chapter.scenes:
                        if scene.id == item_id:
                            self.current_scene = scene
                            self._refresh_properties()
                            self._update_flow_graph()
                            break
                    break
    
    def _on_tree_double_click(self, event):
        """Handler für Doppelklick - öffnet Bearbeitung"""
        selection = self.chapter_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        parent = self.chapter_tree.parent(item_id)
        
        if parent:
            # Szene doppelgeklickt -> Vorschau
            self._preview_scene()
    
    # ============================================================
    # HILFSFUNKTIONEN
    # ============================================================
    
    def _refresh_properties(self):
        """Aktualisiert das Properties-Panel"""
        # Alte Widgets entfernen
        for widget in self.props_frame.winfo_children():
            widget.destroy()
        
        if self.current_scene:
            self._show_scene_properties()
        elif self.current_chapter:
            self._show_chapter_properties()
        else:
            tk.Label(
                self.props_frame,
                text="Wähle ein Element aus,\num seine Eigenschaften\nzu bearbeiten.",
                bg="#16213e", fg="#666",
                font=("Arial", 10),
                justify=tk.CENTER
            ).pack(pady=50)
    
    def _show_chapter_properties(self):
        """Zeigt Kapitel-Eigenschaften"""
        chapter = self.current_chapter
        if not chapter:
            return
        
        # Titel
        tk.Label(
            self.props_frame,
            text=f"📖 {chapter.name}",
            bg="#16213e", fg="#e94560",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Name bearbeiten
        name_frame = tk.Frame(self.props_frame, bg="#16213e")
        name_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(name_frame, text="Name:", bg="#16213e", fg="white").pack(anchor=tk.W)
        name_entry = tk.Entry(name_frame, bg="#0f3460", fg="white", insertbackground="white")
        name_entry.insert(0, chapter.name)
        name_entry.pack(fill=tk.X, pady=2)
        name_entry.bind("<FocusOut>", lambda e: self._update_chapter_name(name_entry.get()))
        
        # Beschreibung
        desc_frame = tk.Frame(self.props_frame, bg="#16213e")
        desc_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(desc_frame, text="Beschreibung:", bg="#16213e", fg="white").pack(anchor=tk.W)
        desc_text = tk.Text(desc_frame, bg="#0f3460", fg="white", height=4, insertbackground="white")
        desc_text.insert("1.0", chapter.description)
        desc_text.pack(fill=tk.X, pady=2)
        
        # Szenen-Anzahl
        tk.Label(
            self.props_frame,
            text=f"Szenen: {len(chapter.scenes)}",
            bg="#16213e", fg="#888"
        ).pack(anchor=tk.W, padx=10, pady=5)
    
    def _show_scene_properties(self):
        """Zeigt Szenen-Eigenschaften (Basis-Version)"""
        scene = self.current_scene
        if not scene:
            return
        
        icon = self._get_scene_icon(scene.scene_type)
        
        # Titel
        tk.Label(
            self.props_frame,
            text=f"{icon} {scene.name}",
            bg="#16213e", fg="#e94560",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Typ
        tk.Label(
            self.props_frame,
            text=f"Typ: {scene.scene_type.value}",
            bg="#16213e", fg="#888"
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        # Name bearbeiten
        name_frame = tk.Frame(self.props_frame, bg="#16213e")
        name_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(name_frame, text="Name:", bg="#16213e", fg="white").pack(anchor=tk.W)
        name_entry = tk.Entry(name_frame, bg="#0f3460", fg="white", insertbackground="white")
        name_entry.insert(0, scene.name)
        name_entry.pack(fill=tk.X, pady=2)
        name_entry.bind("<FocusOut>", lambda e: self._update_scene_name(name_entry.get()))
        
        # Trigger-Anzahl
        tk.Label(
            self.props_frame,
            text=f"⚡ Trigger: {len(scene.triggers)}",
            bg="#16213e", fg="#888"
        ).pack(anchor=tk.W, padx=10, pady=2)
        
        # Overlay-Anzahl
        tk.Label(
            self.props_frame,
            text=f"🎭 Overlays: {len(scene.overlays)}",
            bg="#16213e", fg="#888"
        ).pack(anchor=tk.W, padx=10, pady=2)
    
    def _update_chapter_name(self, new_name: str):
        """Aktualisiert den Kapitelnamen"""
        if self.current_chapter and new_name:
            self.current_chapter.name = new_name
            self._mark_changed()
            self._refresh_chapter_list()
    
    def _update_scene_name(self, new_name: str):
        """Aktualisiert den Szenennamen"""
        if self.current_scene and new_name:
            self.current_scene.name = new_name
            self._mark_changed()
            self._refresh_chapter_list()
    
    def _update_flow_graph(self):
        """Aktualisiert den Flow-Graph (Platzhalter)"""
        self.flow_canvas.delete("all")
        
        if self.current_scene:
            # Einfache Darstellung
            self.flow_canvas.create_text(
                400, 50,
                text=f"🎬 {self.current_scene.name}",
                fill="#e94560",
                font=("Arial", 14, "bold")
            )
            
            # Trigger anzeigen
            y = 120
            for i, trigger in enumerate(self.current_scene.triggers):
                self.flow_canvas.create_rectangle(
                    50, y, 350, y + 60,
                    fill="#0f3460", outline="#e94560"
                )
                self.flow_canvas.create_text(
                    200, y + 30,
                    text=f"⚡ {trigger.name or f'Trigger {i+1}'}",
                    fill="white",
                    font=("Arial", 10)
                )
                y += 80
        else:
            self.flow_canvas.create_text(
                400, 300,
                text="🔗 Flow-Graph\n\nWähle eine Szene aus der Liste,\num ihre Verbindungen zu sehen.",
                fill="#666",
                font=("Arial", 14),
                justify=tk.CENTER
            )
    
    def _mark_changed(self):
        """Markiert das Storyboard als geändert"""
        self.has_unsaved_changes = True
        self._update_title()
    
    def _update_title(self):
        """Aktualisiert den Fenstertitel"""
        title = f"🎬 Story Editor - {self.storyboard.name}"
        if self.has_unsaved_changes:
            title += " *"
        self.title(title)
        
        # Auch Label aktualisieren
        self.storyboard_name_label.config(text=f"📚 {self.storyboard.name}")
    
    def _set_status(self, message: str):
        """Setzt die Statusnachricht"""
        self.status_label.config(text=message)
    
    # ============================================================
    # ANSICHT-TOGGLE
    # ============================================================
    
    def _toggle_flow_graph(self):
        """Flow-Graph ein/ausblenden"""
        if self.show_flow_graph.get():
            self.main_paned.add(self.center_panel, after=self.left_panel)
        else:
            self.main_paned.forget(self.center_panel)
    
    def _toggle_properties(self):
        """Properties-Panel ein/ausblenden"""
        if self.show_properties.get():
            self.main_paned.add(self.right_panel)
        else:
            self.main_paned.forget(self.right_panel)
    
    def _show_all_panels(self):
        """Alle Panels einblenden"""
        self.show_flow_graph.set(True)
        self.show_properties.set(True)
        self._toggle_flow_graph()
        self._toggle_properties()
    
    # ============================================================
    # TOOLTIP
    # ============================================================
    
    def _show_tooltip(self, event, text: str):
        """Zeigt einen Tooltip"""
        if hasattr(self, '_tooltip'):
            self._tooltip.destroy()
        
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = tk.Label(
            self._tooltip,
            text=text,
            bg="#ffffe0",
            fg="black",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9)
        )
        label.pack()
    
    def _hide_tooltip(self):
        """Versteckt den Tooltip"""
        if hasattr(self, '_tooltip'):
            self._tooltip.destroy()
    
    # ============================================================
    # DIALOGE
    # ============================================================
    
    def _show_shortcuts(self):
        """Zeigt Tastenkürzel-Dialog"""
        shortcuts = """
Tastenkürzel:

Ctrl+N     Neues Storyboard
Ctrl+O     Öffnen
Ctrl+S     Speichern
Ctrl+Z     Rückgängig
Ctrl+Y     Wiederholen

Del        Ausgewähltes löschen
F5         Vorschau

Doppelklick auf Szene = Vorschau
"""
        messagebox.showinfo("Tastenkürzel", shortcuts)
    
    def _show_about(self):
        """Zeigt Über-Dialog"""
        about = """
🎬 Story Editor
für "Der Eine Ring" VTT

Version 1.0.0

Erstelle interaktive Geschichten
mit Szenen, Triggern und Overlays.
"""
        messagebox.showinfo("Über Story Editor", about)
    
    # ============================================================
    # SCHLIESSEN
    # ============================================================
    
    def _on_close(self):
        """Handler beim Schließen des Fensters"""
        if self.has_unsaved_changes:
            result = messagebox.askyesnocancel(
                "Ungespeicherte Änderungen",
                "Es gibt ungespeicherte Änderungen. Speichern?"
            )
            if result is True:
                self._save_storyboard()
            elif result is None:
                return  # Abbrechen
        
        self.destroy()


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hauptfenster verstecken
    
    editor = StoryEditorWindow(root)
    editor.mainloop()
