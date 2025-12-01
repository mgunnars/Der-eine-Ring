"""
Journal & Notes System - FoundryVTT-ähnliches Kampagnen-Notizsystem
Ermöglicht Notizen, Handouts und Charakter-Informationen
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable, Set
from enum import Enum
from datetime import datetime
import json
import uuid
import os

# UI Framework importieren
try:
    from ui_framework import UIColors, UISizes, WindowManager, BaseDialog
except ImportError:
    class UIColors:
        BG_DARK = "#1a1a2e"
        BG_MEDIUM = "#16213e"
        BG_LIGHT = "#0f3460"
        ACCENT = "#e94560"
        TEXT = "#eaeaea"
        TEXT_DIM = "#888888"
        SUCCESS = "#4ecca3"
        WARNING = "#ffc107"
        DANGER = "#ff6b6b"
        BORDER = "#333355"

# Pillow für Bilder
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class JournalEntryType(Enum):
    """Typen von Journal-Einträgen"""
    NOTE = "note"              # Einfache Notiz
    HANDOUT = "handout"        # Spieler-Handout
    CHARACTER = "character"    # Charakter-Info
    LOCATION = "location"      # Ort/Location
    ITEM = "item"             # Gegenstand
    QUEST = "quest"           # Quest/Aufgabe
    SESSION = "session"       # Session-Notizen
    SECRET = "secret"         # Geheime GM-Notiz


class Permission(Enum):
    """Zugriffsrechte"""
    NONE = "none"
    LIMITED = "limited"   # Nur Name/Thumbnail
    OBSERVER = "observer" # Lesen
    OWNER = "owner"       # Lesen + Bearbeiten


@dataclass
class JournalEntry:
    """Ein Journal-Eintrag"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Neuer Eintrag"
    content: str = ""
    entry_type: JournalEntryType = JournalEntryType.NOTE
    folder_id: Optional[str] = None
    
    # Metadaten
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    author: str = "GM"
    
    # Bilder
    image_path: str = ""
    thumbnail_path: str = ""
    
    # Berechtigungen
    default_permission: Permission = Permission.NONE
    player_permissions: Dict[str, Permission] = field(default_factory=dict)
    
    # Verlinkungen
    linked_entries: List[str] = field(default_factory=list)  # IDs anderer Einträge
    linked_scene: Optional[str] = None  # Szenen-ID
    map_marker_x: Optional[float] = None
    map_marker_y: Optional[float] = None
    
    # Tags für Suche
    tags: List[str] = field(default_factory=list)
    
    # Sortierung
    sort_order: int = 0
    
    def update_modified(self):
        """Änderungszeitpunkt aktualisieren"""
        self.modified = datetime.now().isoformat()
    
    def can_view(self, player_id: str, is_gm: bool = False) -> bool:
        """Prüft ob Spieler den Eintrag sehen kann"""
        if is_gm:
            return True
        
        perm = self.player_permissions.get(player_id, self.default_permission)
        return perm != Permission.NONE
    
    def can_edit(self, player_id: str, is_gm: bool = False) -> bool:
        """Prüft ob Spieler bearbeiten kann"""
        if is_gm:
            return True
        
        perm = self.player_permissions.get(player_id, self.default_permission)
        return perm == Permission.OWNER
    
    def to_dict(self) -> dict:
        """Eintrag als Dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'entry_type': self.entry_type.value,
            'folder_id': self.folder_id,
            'created': self.created,
            'modified': self.modified,
            'author': self.author,
            'image_path': self.image_path,
            'thumbnail_path': self.thumbnail_path,
            'default_permission': self.default_permission.value,
            'player_permissions': {k: v.value for k, v in self.player_permissions.items()},
            'linked_entries': self.linked_entries,
            'linked_scene': self.linked_scene,
            'map_marker_x': self.map_marker_x,
            'map_marker_y': self.map_marker_y,
            'tags': self.tags,
            'sort_order': self.sort_order
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JournalEntry':
        """Eintrag aus Dictionary"""
        entry = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Eintrag'),
            content=data.get('content', ''),
            entry_type=JournalEntryType(data.get('entry_type', 'note')),
            folder_id=data.get('folder_id'),
            created=data.get('created', datetime.now().isoformat()),
            modified=data.get('modified', datetime.now().isoformat()),
            author=data.get('author', 'GM'),
            image_path=data.get('image_path', ''),
            thumbnail_path=data.get('thumbnail_path', ''),
            default_permission=Permission(data.get('default_permission', 'none')),
            linked_entries=data.get('linked_entries', []),
            linked_scene=data.get('linked_scene'),
            map_marker_x=data.get('map_marker_x'),
            map_marker_y=data.get('map_marker_y'),
            tags=data.get('tags', []),
            sort_order=data.get('sort_order', 0)
        )
        
        for player_id, perm_value in data.get('player_permissions', {}).items():
            entry.player_permissions[player_id] = Permission(perm_value)
        
        return entry


@dataclass
class JournalFolder:
    """Ordner für Journal-Einträge"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Neuer Ordner"
    parent_id: Optional[str] = None
    color: str = "#888888"
    expanded: bool = True
    sort_order: int = 0
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'color': self.color,
            'expanded': self.expanded,
            'sort_order': self.sort_order
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JournalFolder':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Ordner'),
            parent_id=data.get('parent_id'),
            color=data.get('color', '#888888'),
            expanded=data.get('expanded', True),
            sort_order=data.get('sort_order', 0)
        )


class JournalManager:
    """Verwaltet alle Journal-Einträge"""
    
    def __init__(self):
        self.entries: List[JournalEntry] = []
        self.folders: List[JournalFolder] = []
        
        # Callbacks
        self.on_entry_changed: Optional[Callable[[JournalEntry], None]] = None
    
    def create_entry(self, **kwargs) -> JournalEntry:
        """Neuen Eintrag erstellen"""
        entry = JournalEntry(**kwargs)
        self.entries.append(entry)
        return entry
    
    def create_folder(self, name: str, parent_id: str = None) -> JournalFolder:
        """Neuen Ordner erstellen"""
        folder = JournalFolder(name=name, parent_id=parent_id)
        self.folders.append(folder)
        return folder
    
    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Eintrag nach ID"""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    def get_folder(self, folder_id: str) -> Optional[JournalFolder]:
        """Ordner nach ID"""
        for folder in self.folders:
            if folder.id == folder_id:
                return folder
        return None
    
    def delete_entry(self, entry_id: str) -> bool:
        """Eintrag löschen"""
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                del self.entries[i]
                return True
        return False
    
    def delete_folder(self, folder_id: str, delete_contents: bool = False) -> bool:
        """Ordner löschen"""
        # Einträge im Ordner behandeln
        for entry in self.entries:
            if entry.folder_id == folder_id:
                if delete_contents:
                    self.delete_entry(entry.id)
                else:
                    entry.folder_id = None
        
        # Unterordner behandeln
        for folder in self.folders:
            if folder.parent_id == folder_id:
                if delete_contents:
                    self.delete_folder(folder.id, True)
                else:
                    folder.parent_id = None
        
        # Ordner selbst löschen
        for i, folder in enumerate(self.folders):
            if folder.id == folder_id:
                del self.folders[i]
                return True
        return False
    
    def get_entries_in_folder(self, folder_id: Optional[str]) -> List[JournalEntry]:
        """Einträge in einem Ordner"""
        return [e for e in self.entries if e.folder_id == folder_id]
    
    def get_subfolders(self, parent_id: Optional[str]) -> List[JournalFolder]:
        """Unterordner eines Ordners"""
        return [f for f in self.folders if f.parent_id == parent_id]
    
    def search_entries(self, query: str, entry_types: List[JournalEntryType] = None,
                      tags: List[str] = None) -> List[JournalEntry]:
        """Einträge suchen"""
        results = []
        query_lower = query.lower()
        
        for entry in self.entries:
            # Typ-Filter
            if entry_types and entry.entry_type not in entry_types:
                continue
            
            # Tag-Filter
            if tags and not any(t in entry.tags for t in tags):
                continue
            
            # Text-Suche
            if (query_lower in entry.name.lower() or 
                query_lower in entry.content.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)
        
        return results
    
    def get_all_tags(self) -> Set[str]:
        """Alle verwendeten Tags"""
        tags = set()
        for entry in self.entries:
            tags.update(entry.tags)
        return tags
    
    def to_dict(self) -> dict:
        """Alles als Dictionary"""
        return {
            'entries': [e.to_dict() for e in self.entries],
            'folders': [f.to_dict() for f in self.folders]
        }
    
    def from_dict(self, data: dict):
        """Aus Dictionary laden"""
        self.entries.clear()
        self.folders.clear()
        
        for folder_data in data.get('folders', []):
            self.folders.append(JournalFolder.from_dict(folder_data))
        
        for entry_data in data.get('entries', []):
            self.entries.append(JournalEntry.from_dict(entry_data))
    
    def save_to_file(self, filepath: str):
        """In Datei speichern"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: str):
        """Aus Datei laden"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_dict(data)


class JournalTreeView(tk.Frame):
    """Baumansicht für Journal-Einträge"""
    
    def __init__(self, parent: tk.Widget, journal_manager: JournalManager):
        super().__init__(parent, bg=UIColors.BG_DARK)
        self.journal_manager = journal_manager
        
        # Auswahl-Callback
        self.on_entry_selected: Optional[Callable[[JournalEntry], None]] = None
        
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """UI aufbauen"""
        # Toolbar
        toolbar = tk.Frame(self, bg=UIColors.BG_MEDIUM)
        toolbar.pack(fill=tk.X)
        
        tk.Button(
            toolbar,
            text="➕ Eintrag",
            command=self._add_entry,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        tk.Button(
            toolbar,
            text="📁 Ordner",
            command=self._add_folder,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=2, pady=2)
        
        # Suche
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter())
        
        search_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            search_frame,
            text="🔍",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Treeview
        style = ttk.Style()
        style.configure(
            "Journal.Treeview",
            background=UIColors.BG_DARK,
            foreground=UIColors.TEXT,
            fieldbackground=UIColors.BG_DARK
        )
        
        tree_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        self.tree = ttk.Treeview(
            tree_frame,
            style="Journal.Treeview",
            selectmode="browse",
            show="tree"
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Events
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)
    
    def refresh(self):
        """Baum neu aufbauen"""
        self.tree.delete(*self.tree.get_children())
        
        # Icons für Typen
        type_icons = {
            JournalEntryType.NOTE: "📝",
            JournalEntryType.HANDOUT: "📜",
            JournalEntryType.CHARACTER: "👤",
            JournalEntryType.LOCATION: "🏰",
            JournalEntryType.ITEM: "⚔️",
            JournalEntryType.QUEST: "❗",
            JournalEntryType.SESSION: "📅",
            JournalEntryType.SECRET: "🔒"
        }
        
        # Ordner und Einträge ohne Ordner
        self._add_folder_to_tree("", None, type_icons)
    
    def _add_folder_to_tree(self, parent_node: str, folder_id: Optional[str], 
                            type_icons: dict):
        """Ordner und Inhalt zum Baum hinzufügen"""
        # Unterordner
        for folder in sorted(self.journal_manager.get_subfolders(folder_id), 
                           key=lambda f: f.sort_order):
            node_id = f"folder_{folder.id}"
            self.tree.insert(
                parent_node, "end",
                iid=node_id,
                text=f"📁 {folder.name}",
                open=folder.expanded
            )
            self._add_folder_to_tree(node_id, folder.id, type_icons)
        
        # Einträge
        for entry in sorted(self.journal_manager.get_entries_in_folder(folder_id),
                          key=lambda e: e.sort_order):
            icon = type_icons.get(entry.entry_type, "📄")
            self.tree.insert(
                parent_node, "end",
                iid=f"entry_{entry.id}",
                text=f"{icon} {entry.name}"
            )
    
    def _filter(self):
        """Einträge filtern"""
        query = self.search_var.get()
        if not query:
            self.refresh()
            return
        
        # Alle löschen
        self.tree.delete(*self.tree.get_children())
        
        # Gefilterte Einträge anzeigen
        results = self.journal_manager.search_entries(query)
        
        type_icons = {
            JournalEntryType.NOTE: "📝",
            JournalEntryType.HANDOUT: "📜",
            JournalEntryType.CHARACTER: "👤",
            JournalEntryType.LOCATION: "🏰",
            JournalEntryType.ITEM: "⚔️",
            JournalEntryType.QUEST: "❗",
            JournalEntryType.SESSION: "📅",
            JournalEntryType.SECRET: "🔒"
        }
        
        for entry in results:
            icon = type_icons.get(entry.entry_type, "📄")
            self.tree.insert(
                "", "end",
                iid=f"entry_{entry.id}",
                text=f"{icon} {entry.name}"
            )
    
    def _on_select(self, event):
        """Eintrag ausgewählt"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        if item_id.startswith("entry_"):
            entry_id = item_id.replace("entry_", "")
            entry = self.journal_manager.get_entry(entry_id)
            if entry and self.on_entry_selected:
                self.on_entry_selected(entry)
    
    def _on_double_click(self, event):
        """Doppelklick"""
        self._on_select(event)
    
    def _add_entry(self):
        """Neuen Eintrag erstellen"""
        # Aktuellen Ordner ermitteln
        folder_id = None
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            if item_id.startswith("folder_"):
                folder_id = item_id.replace("folder_", "")
        
        entry = self.journal_manager.create_entry(
            name="Neuer Eintrag",
            folder_id=folder_id
        )
        self.refresh()
        
        # Neuen Eintrag auswählen
        self.tree.selection_set(f"entry_{entry.id}")
        if self.on_entry_selected:
            self.on_entry_selected(entry)
    
    def _add_folder(self):
        """Neuen Ordner erstellen"""
        # Parent ermitteln
        parent_id = None
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            if item_id.startswith("folder_"):
                parent_id = item_id.replace("folder_", "")
        
        folder = self.journal_manager.create_folder("Neuer Ordner", parent_id)
        self.refresh()
    
    def _show_context_menu(self, event):
        """Kontextmenü anzeigen"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        self.tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        
        if item.startswith("entry_"):
            menu.add_command(label="Bearbeiten", command=self._edit_selected)
            menu.add_command(label="Duplizieren", command=self._duplicate_selected)
            menu.add_separator()
            menu.add_command(label="Löschen", command=self._delete_selected)
        elif item.startswith("folder_"):
            menu.add_command(label="Umbenennen", command=self._rename_folder)
            menu.add_separator()
            menu.add_command(label="Ordner löschen", command=self._delete_selected)
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def _edit_selected(self):
        """Ausgewählten Eintrag bearbeiten"""
        self._on_select(None)
    
    def _duplicate_selected(self):
        """Ausgewählten Eintrag duplizieren"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        if item_id.startswith("entry_"):
            entry_id = item_id.replace("entry_", "")
            entry = self.journal_manager.get_entry(entry_id)
            if entry:
                new_entry = self.journal_manager.create_entry(
                    name=f"{entry.name} (Kopie)",
                    content=entry.content,
                    entry_type=entry.entry_type,
                    folder_id=entry.folder_id,
                    tags=entry.tags.copy()
                )
                self.refresh()
    
    def _delete_selected(self):
        """Ausgewähltes Element löschen"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        if item_id.startswith("entry_"):
            entry_id = item_id.replace("entry_", "")
            if messagebox.askyesno("Löschen", "Eintrag wirklich löschen?"):
                self.journal_manager.delete_entry(entry_id)
                self.refresh()
        
        elif item_id.startswith("folder_"):
            folder_id = item_id.replace("folder_", "")
            result = messagebox.askyesnocancel(
                "Ordner löschen",
                "Inhalt auch löschen?\n\nJa = Inhalt löschen\nNein = Inhalt behalten"
            )
            if result is not None:
                self.journal_manager.delete_folder(folder_id, delete_contents=result)
                self.refresh()
    
    def _rename_folder(self):
        """Ordner umbenennen"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        if not item_id.startswith("folder_"):
            return
        
        folder_id = item_id.replace("folder_", "")
        folder = self.journal_manager.get_folder(folder_id)
        if not folder:
            return
        
        # Einfacher Dialog
        dialog = tk.Toplevel(self)
        dialog.title("Ordner umbenennen")
        dialog.geometry("300x100")
        dialog.configure(bg=UIColors.BG_DARK)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Neuer Name:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(pady=10)
        
        name_var = tk.StringVar(value=folder.name)
        entry = tk.Entry(
            dialog,
            textvariable=name_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            width=30
        )
        entry.pack(pady=5)
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save():
            folder.name = name_var.get()
            self.refresh()
            dialog.destroy()
        
        tk.Button(
            dialog,
            text="OK",
            command=save,
            bg=UIColors.SUCCESS,
            fg="white"
        ).pack(pady=10)
        
        entry.bind("<Return>", lambda e: save())


class JournalEditor(tk.Frame):
    """Editor für Journal-Einträge"""
    
    def __init__(self, parent: tk.Widget, journal_manager: JournalManager):
        super().__init__(parent, bg=UIColors.BG_DARK)
        self.journal_manager = journal_manager
        
        self.current_entry: Optional[JournalEntry] = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """UI aufbauen"""
        # Header
        header = tk.Frame(self, bg=UIColors.BG_MEDIUM)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        # Name
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(
            header,
            textvariable=self.name_var,
            font=("Segoe UI", 14, "bold"),
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT,
            relief=tk.FLAT
        )
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Typ
        self.type_var = tk.StringVar()
        type_combo = ttk.Combobox(
            header,
            textvariable=self.type_var,
            values=[t.value for t in JournalEntryType],
            state="readonly",
            width=12
        )
        type_combo.pack(side=tk.LEFT, padx=5)
        
        # Speichern
        tk.Button(
            header,
            text="💾 Speichern",
            command=self._save,
            bg=UIColors.SUCCESS,
            fg="white"
        ).pack(side=tk.RIGHT, padx=5)
        
        # Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Inhalt-Tab
        content_frame = tk.Frame(self.notebook, bg=UIColors.BG_DARK)
        self.notebook.add(content_frame, text="Inhalt")
        
        # Text-Editor
        text_frame = tk.Frame(content_frame, bg=UIColors.BG_DARK)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.content_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT,
            font=("Consolas", 11),
            padx=10,
            pady=10
        )
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, 
                                  command=self.content_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_text.configure(yscrollcommand=scrollbar.set)
        
        # Bild-Tab
        image_frame = tk.Frame(self.notebook, bg=UIColors.BG_DARK)
        self.notebook.add(image_frame, text="Bild")
        
        img_btn_frame = tk.Frame(image_frame, bg=UIColors.BG_DARK)
        img_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(
            img_btn_frame,
            text="Bild wählen...",
            command=self._choose_image,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT)
        
        self.image_path_label = tk.Label(
            img_btn_frame,
            text="Kein Bild",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT_DIM
        )
        self.image_path_label.pack(side=tk.LEFT, padx=10)
        
        self.image_label = tk.Label(
            image_frame,
            bg=UIColors.BG_DARK,
            text="Kein Bild geladen"
        )
        self.image_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tags-Tab
        tags_frame = tk.Frame(self.notebook, bg=UIColors.BG_DARK)
        self.notebook.add(tags_frame, text="Tags")
        
        tk.Label(
            tags_frame,
            text="Tags (kommasepariert):",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(anchor=tk.W, padx=10, pady=10)
        
        self.tags_var = tk.StringVar()
        tk.Entry(
            tags_frame,
            textvariable=self.tags_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT
        ).pack(fill=tk.X, padx=10)
        
        tk.Label(
            tags_frame,
            text="Alle Tags:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(anchor=tk.W, padx=10, pady=(20, 5))
        
        self.all_tags_label = tk.Label(
            tags_frame,
            text="",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT_DIM,
            wraplength=400,
            justify=tk.LEFT
        )
        self.all_tags_label.pack(anchor=tk.W, padx=10)
        
        # Berechtigungen-Tab
        perm_frame = tk.Frame(self.notebook, bg=UIColors.BG_DARK)
        self.notebook.add(perm_frame, text="Berechtigungen")
        
        tk.Label(
            perm_frame,
            text="Standard-Berechtigung:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        ).pack(anchor=tk.W, padx=10, pady=10)
        
        self.perm_var = tk.StringVar()
        ttk.Combobox(
            perm_frame,
            textvariable=self.perm_var,
            values=[p.value for p in Permission],
            state="readonly",
            width=15
        ).pack(anchor=tk.W, padx=10)
        
        tk.Label(
            perm_frame,
            text="Spieler-Berechtigungen können hier später konfiguriert werden",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT_DIM
        ).pack(anchor=tk.W, padx=10, pady=20)
        
        # Initial leer
        self._clear()
    
    def load_entry(self, entry: JournalEntry):
        """Eintrag laden"""
        self.current_entry = entry
        
        self.name_var.set(entry.name)
        self.type_var.set(entry.entry_type.value)
        
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", entry.content)
        
        self.tags_var.set(", ".join(entry.tags))
        self.perm_var.set(entry.default_permission.value)
        
        # Bild
        if entry.image_path and os.path.exists(entry.image_path):
            self.image_path_label.config(text=os.path.basename(entry.image_path))
            self._load_image(entry.image_path)
        else:
            self.image_path_label.config(text="Kein Bild")
            self.image_label.config(image="", text="Kein Bild geladen")
        
        # Alle Tags aktualisieren
        all_tags = self.journal_manager.get_all_tags()
        self.all_tags_label.config(text=", ".join(sorted(all_tags)) or "Keine Tags")
    
    def _clear(self):
        """Editor leeren"""
        self.current_entry = None
        self.name_var.set("")
        self.type_var.set("note")
        self.content_text.delete("1.0", tk.END)
        self.tags_var.set("")
        self.perm_var.set("none")
        self.image_path_label.config(text="Kein Bild")
        self.image_label.config(image="", text="Kein Bild geladen")
    
    def _save(self):
        """Änderungen speichern"""
        if not self.current_entry:
            return
        
        self.current_entry.name = self.name_var.get()
        self.current_entry.entry_type = JournalEntryType(self.type_var.get())
        self.current_entry.content = self.content_text.get("1.0", tk.END).strip()
        
        # Tags parsen
        tags_str = self.tags_var.get()
        self.current_entry.tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        
        self.current_entry.default_permission = Permission(self.perm_var.get())
        self.current_entry.update_modified()
        
        if self.journal_manager.on_entry_changed:
            self.journal_manager.on_entry_changed(self.current_entry)
    
    def _choose_image(self):
        """Bild auswählen"""
        if not self.current_entry:
            return
        
        filetypes = [
            ("Bilder", "*.png *.jpg *.jpeg *.gif *.bmp"),
            ("Alle Dateien", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Bild wählen",
            filetypes=filetypes
        )
        
        if filepath:
            self.current_entry.image_path = filepath
            self.image_path_label.config(text=os.path.basename(filepath))
            self._load_image(filepath)
    
    def _load_image(self, filepath: str):
        """Bild laden und anzeigen"""
        if not PIL_AVAILABLE:
            self.image_label.config(text="PIL nicht verfügbar")
            return
        
        try:
            img = Image.open(filepath)
            
            # Größe anpassen
            max_size = (400, 400)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Referenz behalten
        
        except Exception as e:
            self.image_label.config(text=f"Fehler: {e}", image="")


class JournalWindow(tk.Toplevel):
    """Hauptfenster für das Journal-System"""
    
    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        
        self.title("📚 Journal & Notizen")
        self.geometry("1000x700")
        self.minsize(800, 500)
        self.configure(bg=UIColors.BG_DARK)
        
        self.journal_manager = JournalManager()
        
        self._create_widgets()
        self._create_menu()
    
    def _create_widgets(self):
        """UI aufbauen"""
        # PanedWindow für resizable Bereiche
        paned = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            bg=UIColors.BORDER,
            sashwidth=4
        )
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Linke Seite: Baumansicht
        left_frame = tk.Frame(paned, bg=UIColors.BG_DARK)
        paned.add(left_frame, width=300)
        
        self.tree_view = JournalTreeView(left_frame, self.journal_manager)
        self.tree_view.pack(fill=tk.BOTH, expand=True)
        self.tree_view.on_entry_selected = self._on_entry_selected
        
        # Rechte Seite: Editor
        right_frame = tk.Frame(paned, bg=UIColors.BG_DARK)
        paned.add(right_frame)
        
        self.editor = JournalEditor(right_frame, self.journal_manager)
        self.editor.pack(fill=tk.BOTH, expand=True)
        
        # Callback für Änderungen
        self.journal_manager.on_entry_changed = self._on_entry_changed
    
    def _create_menu(self):
        """Menü erstellen"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Neu", command=self._new_journal)
        file_menu.add_command(label="Öffnen...", command=self._open_journal)
        file_menu.add_command(label="Speichern...", command=self._save_journal)
        file_menu.add_separator()
        file_menu.add_command(label="Schließen", command=self.destroy)
        
        # Bearbeiten-Menü
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(label="Neuer Eintrag", command=self.tree_view._add_entry)
        edit_menu.add_command(label="Neuer Ordner", command=self.tree_view._add_folder)
    
    def _on_entry_selected(self, entry: JournalEntry):
        """Eintrag wurde ausgewählt"""
        self.editor.load_entry(entry)
    
    def _on_entry_changed(self, entry: JournalEntry):
        """Eintrag wurde geändert"""
        self.tree_view.refresh()
    
    def _new_journal(self):
        """Neues Journal"""
        self.journal_manager.entries.clear()
        self.journal_manager.folders.clear()
        self.tree_view.refresh()
        self.editor._clear()
    
    def _open_journal(self):
        """Journal öffnen"""
        filepath = filedialog.askopenfilename(
            title="Journal öffnen",
            filetypes=[("Journal-Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        
        if filepath:
            try:
                self.journal_manager.load_from_file(filepath)
                self.tree_view.refresh()
                self.editor._clear()
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte Datei nicht laden:\n{e}")
    
    def _save_journal(self):
        """Journal speichern"""
        filepath = filedialog.asksaveasfilename(
            title="Journal speichern",
            filetypes=[("Journal-Dateien", "*.json")],
            defaultextension=".json"
        )
        
        if filepath:
            try:
                self.journal_manager.save_to_file(filepath)
                messagebox.showinfo("Gespeichert", "Journal wurde gespeichert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Konnte nicht speichern:\n{e}")


# Testfunktion
def test_journal_system():
    """Testet das Journal-System"""
    root = tk.Tk()
    root.withdraw()  # Hauptfenster verstecken
    
    window = JournalWindow(root)
    
    # Test-Einträge erstellen
    folder = window.journal_manager.create_folder("NPCs")
    
    window.journal_manager.create_entry(
        name="Gandalf der Graue",
        content="Ein mächtiger Zauberer...",
        entry_type=JournalEntryType.CHARACTER,
        folder_id=folder.id,
        tags=["zauberer", "wichtig"]
    )
    
    window.journal_manager.create_entry(
        name="Bruchtal",
        content="Die verborgene Zuflucht der Elben...",
        entry_type=JournalEntryType.LOCATION,
        tags=["elben", "ort"]
    )
    
    window.journal_manager.create_entry(
        name="Der Eine Ring",
        content="Der mächtigste der Ringe der Macht...",
        entry_type=JournalEntryType.ITEM,
        tags=["artefakt", "gefährlich"]
    )
    
    window.tree_view.refresh()
    
    window.mainloop()


if __name__ == "__main__":
    test_journal_system()
