"""
Hotbar & Macros System - FoundryVTT-ähnliche Schnellzugriffsleiste
Ermöglicht schnellen Zugriff auf häufige Aktionen
"""

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
import json
import uuid

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


class MacroType(Enum):
    """Typen von Makros"""
    SCRIPT = "script"           # Python-Code ausführen
    CHAT = "chat"               # Chat-Nachricht senden
    ROLL = "roll"               # Würfelwurf
    SCENE_CHANGE = "scene"      # Szene wechseln
    SOUND = "sound"             # Sound abspielen
    TOKEN_ACTION = "token"      # Token-Aktion
    JOURNAL = "journal"         # Journal-Eintrag öffnen
    CUSTOM = "custom"           # Benutzerdefiniert


@dataclass
class Macro:
    """Ein Makro"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Neues Makro"
    icon: str = "⚡"            # Emoji oder Icon
    macro_type: MacroType = MacroType.SCRIPT
    command: str = ""           # Auszuführender Befehl/Code
    description: str = ""
    color: str = "#4a4a6a"      # Button-Farbe
    
    # Für Würfelwürfe
    dice_formula: str = ""      # z.B. "2d6+3"
    
    # Für Sounds
    sound_path: str = ""
    
    # Für Szenen
    scene_id: str = ""
    
    # Für Journal
    journal_id: str = ""
    
    # Sichtbarkeit
    gm_only: bool = False
    
    def to_dict(self) -> dict:
        """Makro als Dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'macro_type': self.macro_type.value,
            'command': self.command,
            'description': self.description,
            'color': self.color,
            'dice_formula': self.dice_formula,
            'sound_path': self.sound_path,
            'scene_id': self.scene_id,
            'journal_id': self.journal_id,
            'gm_only': self.gm_only
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Macro':
        """Makro aus Dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Makro'),
            icon=data.get('icon', '⚡'),
            macro_type=MacroType(data.get('macro_type', 'script')),
            command=data.get('command', ''),
            description=data.get('description', ''),
            color=data.get('color', '#4a4a6a'),
            dice_formula=data.get('dice_formula', ''),
            sound_path=data.get('sound_path', ''),
            scene_id=data.get('scene_id', ''),
            journal_id=data.get('journal_id', ''),
            gm_only=data.get('gm_only', False)
        )


@dataclass
class HotbarSlot:
    """Ein Slot in der Hotbar"""
    position: int = 0
    macro_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'position': self.position,
            'macro_id': self.macro_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'HotbarSlot':
        return cls(
            position=data.get('position', 0),
            macro_id=data.get('macro_id')
        )


class MacroManager:
    """Verwaltet alle Makros"""
    
    def __init__(self):
        self.macros: Dict[str, Macro] = {}
        self.hotbar_slots: List[HotbarSlot] = []
        self.current_page = 0
        self.slots_per_page = 10
        
        # Callbacks für Ausführung
        self.action_handlers: Dict[MacroType, Callable] = {}
        
        # Hotbar initialisieren (5 Seiten à 10 Slots)
        for page in range(5):
            for slot in range(self.slots_per_page):
                self.hotbar_slots.append(HotbarSlot(position=page * self.slots_per_page + slot))
    
    def create_macro(self, **kwargs) -> Macro:
        """Neues Makro erstellen"""
        macro = Macro(**kwargs)
        self.macros[macro.id] = macro
        return macro
    
    def get_macro(self, macro_id: str) -> Optional[Macro]:
        """Makro nach ID"""
        return self.macros.get(macro_id)
    
    def delete_macro(self, macro_id: str) -> bool:
        """Makro löschen"""
        if macro_id in self.macros:
            # Aus Hotbar entfernen
            for slot in self.hotbar_slots:
                if slot.macro_id == macro_id:
                    slot.macro_id = None
            
            del self.macros[macro_id]
            return True
        return False
    
    def assign_to_slot(self, macro_id: str, slot_position: int) -> bool:
        """Makro einem Slot zuweisen"""
        if slot_position < 0 or slot_position >= len(self.hotbar_slots):
            return False
        
        self.hotbar_slots[slot_position].macro_id = macro_id
        return True
    
    def clear_slot(self, slot_position: int):
        """Slot leeren"""
        if 0 <= slot_position < len(self.hotbar_slots):
            self.hotbar_slots[slot_position].macro_id = None
    
    def get_current_page_slots(self) -> List[HotbarSlot]:
        """Slots der aktuellen Seite"""
        start = self.current_page * self.slots_per_page
        end = start + self.slots_per_page
        return self.hotbar_slots[start:end]
    
    def next_page(self):
        """Zur nächsten Seite"""
        max_pages = len(self.hotbar_slots) // self.slots_per_page
        self.current_page = (self.current_page + 1) % max_pages
    
    def prev_page(self):
        """Zur vorherigen Seite"""
        max_pages = len(self.hotbar_slots) // self.slots_per_page
        self.current_page = (self.current_page - 1) % max_pages
    
    def go_to_page(self, page: int):
        """Zu bestimmter Seite"""
        max_pages = len(self.hotbar_slots) // self.slots_per_page
        self.current_page = max(0, min(page, max_pages - 1))
    
    def register_handler(self, macro_type: MacroType, handler: Callable):
        """Handler für Makro-Typ registrieren"""
        self.action_handlers[macro_type] = handler
    
    def execute_macro(self, macro: Macro) -> Any:
        """Makro ausführen"""
        handler = self.action_handlers.get(macro.macro_type)
        
        if handler:
            return handler(macro)
        
        # Standard-Handler
        if macro.macro_type == MacroType.CHAT:
            print(f"[Chat] {macro.command}")
            return macro.command
        
        elif macro.macro_type == MacroType.ROLL:
            return self._roll_dice(macro.dice_formula)
        
        elif macro.macro_type == MacroType.SCRIPT:
            try:
                exec(macro.command)
                return True
            except Exception as e:
                print(f"Makro-Fehler: {e}")
                return False
        
        return None
    
    def _roll_dice(self, formula: str) -> dict:
        """Würfelformel auswerten"""
        import random
        import re
        
        result = {
            'formula': formula,
            'rolls': [],
            'modifier': 0,
            'total': 0
        }
        
        if not formula:
            return result
        
        # Format: XdY+Z oder XdY-Z
        match = re.match(r'(\d+)d(\d+)([+-]\d+)?', formula.lower().replace(' ', ''))
        
        if match:
            num_dice = int(match.group(1))
            die_size = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0
            
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            
            result['rolls'] = rolls
            result['modifier'] = modifier
            result['total'] = sum(rolls) + modifier
        
        return result
    
    def to_dict(self) -> dict:
        """Alles als Dictionary"""
        return {
            'macros': {k: v.to_dict() for k, v in self.macros.items()},
            'hotbar_slots': [s.to_dict() for s in self.hotbar_slots],
            'current_page': self.current_page
        }
    
    def from_dict(self, data: dict):
        """Aus Dictionary laden"""
        self.macros.clear()
        
        for macro_id, macro_data in data.get('macros', {}).items():
            self.macros[macro_id] = Macro.from_dict(macro_data)
        
        # Slots laden
        slot_data = data.get('hotbar_slots', [])
        for i, slot_dict in enumerate(slot_data):
            if i < len(self.hotbar_slots):
                self.hotbar_slots[i] = HotbarSlot.from_dict(slot_dict)
        
        self.current_page = data.get('current_page', 0)
    
    def save_to_file(self, filepath: str):
        """In Datei speichern"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Aus Datei laden"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_dict(data)


class HotbarWidget(tk.Frame):
    """Die Hotbar-Leiste am unteren Bildschirmrand"""
    
    def __init__(self, parent: tk.Widget, macro_manager: MacroManager):
        super().__init__(parent, bg=UIColors.BG_MEDIUM)
        self.macro_manager = macro_manager
        
        # Callbacks
        self.on_macro_executed: Optional[Callable[[Macro, Any], None]] = None
        
        # Button-Referenzen
        self.slot_buttons: List[tk.Button] = []
        
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        """UI aufbauen"""
        # Container
        container = tk.Frame(self, bg=UIColors.BG_MEDIUM)
        container.pack(pady=5)
        
        # Seiten-Navigation links
        nav_left = tk.Frame(container, bg=UIColors.BG_MEDIUM)
        nav_left.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            nav_left,
            text="◀",
            command=self._prev_page,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=2,
            font=("Segoe UI", 10)
        ).pack()
        
        # Slot-Buttons
        slots_frame = tk.Frame(container, bg=UIColors.BG_MEDIUM)
        slots_frame.pack(side=tk.LEFT, padx=5)
        
        for i in range(self.macro_manager.slots_per_page):
            btn = tk.Button(
                slots_frame,
                text="",
                width=5,
                height=2,
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT,
                relief=tk.RAISED,
                font=("Segoe UI Emoji", 14)
            )
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind("<Button-1>", lambda e, idx=i: self._on_slot_click(idx))
            btn.bind("<Button-3>", lambda e, idx=i: self._on_slot_right_click(e, idx))
            self.slot_buttons.append(btn)
        
        # Seiten-Navigation rechts
        nav_right = tk.Frame(container, bg=UIColors.BG_MEDIUM)
        nav_right.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            nav_right,
            text="▶",
            command=self._next_page,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=2,
            font=("Segoe UI", 10)
        ).pack()
        
        # Seitenanzeige
        self.page_label = tk.Label(
            nav_right,
            text="1/5",
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT_DIM,
            font=("Segoe UI", 9)
        )
        self.page_label.pack()
        
        # Makro-Manager Button
        tk.Button(
            container,
            text="⚙️",
            command=self._open_macro_manager,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=3,
            font=("Segoe UI Emoji", 12)
        ).pack(side=tk.LEFT, padx=10)
        
        # Keyboard-Shortcuts Info
        info_label = tk.Label(
            self,
            text="Tastatur: 1-0 für Slots | Shift+1-5 für Seiten",
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT_DIM,
            font=("Segoe UI", 8)
        )
        info_label.pack(pady=2)
    
    def refresh(self):
        """Hotbar aktualisieren"""
        slots = self.macro_manager.get_current_page_slots()
        
        for i, slot in enumerate(slots):
            btn = self.slot_buttons[i]
            
            if slot.macro_id:
                macro = self.macro_manager.get_macro(slot.macro_id)
                if macro:
                    btn.config(
                        text=macro.icon,
                        bg=macro.color,
                        relief=tk.RAISED
                    )
                    
                    # Tooltip
                    self._create_tooltip(btn, f"{macro.name}\n{macro.description}")
                else:
                    # Ungültiges Makro
                    btn.config(text="?", bg=UIColors.BG_DARK)
            else:
                # Leerer Slot
                btn.config(
                    text="",
                    bg=UIColors.BG_DARK,
                    relief=tk.SUNKEN
                )
        
        # Seitenanzeige
        max_pages = len(self.macro_manager.hotbar_slots) // self.macro_manager.slots_per_page
        self.page_label.config(text=f"{self.macro_manager.current_page + 1}/{max_pages}")
    
    def _create_tooltip(self, widget: tk.Widget, text: str):
        """Tooltip für Widget erstellen"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(
                tooltip,
                text=text,
                bg="#ffffe0",
                fg="black",
                relief=tk.SOLID,
                borderwidth=1,
                font=("Segoe UI", 9)
            )
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget._tooltip = tooltip
            widget.after(2000, hide_tooltip)
        
        def hide_tooltip(event):
            if hasattr(widget, '_tooltip'):
                try:
                    widget._tooltip.destroy()
                except:
                    pass
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
    
    def _on_slot_click(self, slot_index: int):
        """Slot angeklickt"""
        slots = self.macro_manager.get_current_page_slots()
        slot = slots[slot_index]
        
        if slot.macro_id:
            macro = self.macro_manager.get_macro(slot.macro_id)
            if macro:
                result = self.macro_manager.execute_macro(macro)
                
                if self.on_macro_executed:
                    self.on_macro_executed(macro, result)
    
    def _on_slot_right_click(self, event, slot_index: int):
        """Rechtsklick auf Slot"""
        slots = self.macro_manager.get_current_page_slots()
        slot = slots[slot_index]
        
        menu = tk.Menu(self, tearoff=0)
        
        if slot.macro_id:
            menu.add_command(
                label="Bearbeiten",
                command=lambda: self._edit_macro(slot.macro_id)
            )
            menu.add_command(
                label="Slot leeren",
                command=lambda: self._clear_slot(slot_index)
            )
            menu.add_separator()
        
        menu.add_command(
            label="Neues Makro erstellen",
            command=lambda: self._create_new_macro(slot_index)
        )
        menu.add_command(
            label="Makro zuweisen...",
            command=lambda: self._assign_macro(slot_index)
        )
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def _prev_page(self):
        """Vorherige Seite"""
        self.macro_manager.prev_page()
        self.refresh()
    
    def _next_page(self):
        """Nächste Seite"""
        self.macro_manager.next_page()
        self.refresh()
    
    def _clear_slot(self, slot_index: int):
        """Slot leeren"""
        global_index = self.macro_manager.current_page * self.macro_manager.slots_per_page + slot_index
        self.macro_manager.clear_slot(global_index)
        self.refresh()
    
    def _create_new_macro(self, slot_index: int):
        """Neues Makro erstellen und Slot zuweisen"""
        macro = self.macro_manager.create_macro(name="Neues Makro")
        
        global_index = self.macro_manager.current_page * self.macro_manager.slots_per_page + slot_index
        self.macro_manager.assign_to_slot(macro.id, global_index)
        
        self.refresh()
        self._edit_macro(macro.id)
    
    def _edit_macro(self, macro_id: str):
        """Makro bearbeiten"""
        macro = self.macro_manager.get_macro(macro_id)
        if macro:
            MacroEditDialog(
                self.winfo_toplevel(),
                macro,
                self.macro_manager,
                lambda: self.refresh()
            )
    
    def _assign_macro(self, slot_index: int):
        """Makro aus Liste zuweisen"""
        if not self.macro_manager.macros:
            messagebox.showinfo("Info", "Keine Makros vorhanden.\nErstelle zuerst ein Makro.")
            return
        
        MacroSelectDialog(
            self.winfo_toplevel(),
            self.macro_manager,
            lambda macro_id: self._do_assign(slot_index, macro_id)
        )
    
    def _do_assign(self, slot_index: int, macro_id: str):
        """Makro tatsächlich zuweisen"""
        global_index = self.macro_manager.current_page * self.macro_manager.slots_per_page + slot_index
        self.macro_manager.assign_to_slot(macro_id, global_index)
        self.refresh()
    
    def _open_macro_manager(self):
        """Makro-Manager öffnen"""
        MacroManagerWindow(self.winfo_toplevel(), self.macro_manager, self.refresh)
    
    def bind_keyboard_shortcuts(self, root: tk.Tk):
        """Keyboard-Shortcuts binden"""
        # Slots 1-0 (0 = 10)
        for i in range(10):
            key = str((i + 1) % 10)
            root.bind(f"<Key-{key}>", lambda e, idx=i: self._on_slot_click(idx))
        
        # Seiten mit Shift+1-5
        for i in range(5):
            root.bind(f"<Shift-Key-{i+1}>", lambda e, page=i: self._go_to_page(page))
    
    def _go_to_page(self, page: int):
        """Zu Seite wechseln"""
        self.macro_manager.go_to_page(page)
        self.refresh()


class MacroEditDialog(tk.Toplevel):
    """Dialog zum Bearbeiten eines Makros"""
    
    def __init__(self, parent: tk.Tk, macro: Macro, 
                 macro_manager: MacroManager, on_save: Callable):
        super().__init__(parent)
        self.macro = macro
        self.macro_manager = macro_manager
        self.on_save = on_save
        
        self.title(f"Makro bearbeiten: {macro.name}")
        self.configure(bg=UIColors.BG_DARK)
        self.transient(parent)
        self.grab_set()
        
        # Fenster zentriert platzieren
        self._center_on_screen(500, 600)
        self.minsize(400, 500)
        
        self._create_widgets()
    
    def _center_on_screen(self, width: int, height: int):
        """Zentriert Fenster"""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(width, screen_w - 100)
        height = min(height, screen_h - 100)
        x = max(50, (screen_w - width) // 2)
        y = max(30, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        """UI aufbauen"""
        main_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Name
        name_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        name_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            name_frame,
            text="Name:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=10,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.name_var = tk.StringVar(value=self.macro.name)
        tk.Entry(
            name_frame,
            textvariable=self.name_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Icon
        icon_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        icon_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            icon_frame,
            text="Icon:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=10,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.icon_var = tk.StringVar(value=self.macro.icon)
        tk.Entry(
            icon_frame,
            textvariable=self.icon_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            width=5,
            font=("Segoe UI Emoji", 14)
        ).pack(side=tk.LEFT)
        
        # Icon-Auswahl
        icons = ["⚡", "🎲", "⚔️", "🛡️", "🔥", "❄️", "💀", "✨", "🎵", "📖", 
                 "🏃", "👁️", "💡", "🔔", "⚙️", "🎯", "💥", "🌟", "🔮", "💎"]
        
        icon_picker = tk.Frame(icon_frame, bg=UIColors.BG_DARK)
        icon_picker.pack(side=tk.LEFT, padx=10)
        
        for icon in icons:
            btn = tk.Button(
                icon_picker,
                text=icon,
                font=("Segoe UI Emoji", 10),
                bg=UIColors.BG_LIGHT,
                command=lambda i=icon: self.icon_var.set(i),
                width=2
            )
            btn.pack(side=tk.LEFT, padx=1)
        
        # Typ
        type_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        type_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            type_frame,
            text="Typ:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=10,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.type_var = tk.StringVar(value=self.macro.macro_type.value)
        type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.type_var,
            values=[t.value for t in MacroType],
            state="readonly"
        )
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)
        
        # Beschreibung
        desc_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        desc_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            desc_frame,
            text="Beschreibung:",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT,
            width=10,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        self.desc_var = tk.StringVar(value=self.macro.description)
        tk.Entry(
            desc_frame,
            textvariable=self.desc_var,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            insertbackground=UIColors.TEXT
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Typ-spezifische Felder
        self.specific_frame = tk.LabelFrame(
            main_frame,
            text="Konfiguration",
            bg=UIColors.BG_DARK,
            fg=UIColors.TEXT
        )
        self.specific_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self._update_specific_fields()
        
        # Buttons
        btn_frame = tk.Frame(main_frame, bg=UIColors.BG_DARK)
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(
            btn_frame,
            text="Speichern",
            command=self._save,
            bg=UIColors.SUCCESS,
            fg="white",
            width=12
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Abbrechen",
            command=self.destroy,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT,
            width=12
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Löschen",
            command=self._delete,
            bg=UIColors.DANGER,
            fg="white",
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _on_type_changed(self, event=None):
        """Typ wurde geändert"""
        self._update_specific_fields()
    
    def _update_specific_fields(self):
        """Typ-spezifische Felder aktualisieren"""
        # Alte Widgets löschen
        for widget in self.specific_frame.winfo_children():
            widget.destroy()
        
        macro_type = MacroType(self.type_var.get())
        
        if macro_type == MacroType.SCRIPT:
            tk.Label(
                self.specific_frame,
                text="Python-Code:",
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT
            ).pack(anchor=tk.W, padx=10, pady=5)
            
            self.command_text = tk.Text(
                self.specific_frame,
                bg=UIColors.BG_MEDIUM,
                fg=UIColors.TEXT,
                insertbackground=UIColors.TEXT,
                font=("Consolas", 10),
                height=10
            )
            self.command_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            self.command_text.insert("1.0", self.macro.command)
        
        elif macro_type == MacroType.CHAT:
            tk.Label(
                self.specific_frame,
                text="Chat-Nachricht:",
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT
            ).pack(anchor=tk.W, padx=10, pady=5)
            
            self.command_text = tk.Text(
                self.specific_frame,
                bg=UIColors.BG_MEDIUM,
                fg=UIColors.TEXT,
                height=5
            )
            self.command_text.pack(fill=tk.X, padx=10, pady=5)
            self.command_text.insert("1.0", self.macro.command)
        
        elif macro_type == MacroType.ROLL:
            roll_frame = tk.Frame(self.specific_frame, bg=UIColors.BG_DARK)
            roll_frame.pack(fill=tk.X, padx=10, pady=10)
            
            tk.Label(
                roll_frame,
                text="Würfelformel:",
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT
            ).pack(side=tk.LEFT)
            
            self.dice_var = tk.StringVar(value=self.macro.dice_formula)
            tk.Entry(
                roll_frame,
                textvariable=self.dice_var,
                bg=UIColors.BG_MEDIUM,
                fg=UIColors.TEXT,
                width=15
            ).pack(side=tk.LEFT, padx=10)
            
            tk.Label(
                roll_frame,
                text="z.B. 2d6+3, 1d20, 3d8-2",
                bg=UIColors.BG_DARK,
                fg=UIColors.TEXT_DIM
            ).pack(side=tk.LEFT)
            
            # Test-Button
            tk.Button(
                self.specific_frame,
                text="🎲 Testen",
                command=self._test_roll,
                bg=UIColors.BG_LIGHT,
                fg=UIColors.TEXT
            ).pack(anchor=tk.W, padx=10, pady=5)
            
            self.roll_result_label = tk.Label(
                self.specific_frame,
                text="",
                bg=UIColors.BG_DARK,
                fg=UIColors.SUCCESS
            )
            self.roll_result_label.pack(anchor=tk.W, padx=10)
    
    def _test_roll(self):
        """Würfelwurf testen"""
        formula = self.dice_var.get()
        result = self.macro_manager._roll_dice(formula)
        
        if result['rolls']:
            rolls_str = ", ".join(str(r) for r in result['rolls'])
            mod_str = f" + {result['modifier']}" if result['modifier'] > 0 else (
                f" - {abs(result['modifier'])}" if result['modifier'] < 0 else ""
            )
            
            self.roll_result_label.config(
                text=f"Würfe: [{rolls_str}]{mod_str} = {result['total']}"
            )
        else:
            self.roll_result_label.config(text="Ungültige Formel")
    
    def _save(self):
        """Makro speichern"""
        self.macro.name = self.name_var.get()
        self.macro.icon = self.icon_var.get()
        self.macro.macro_type = MacroType(self.type_var.get())
        self.macro.description = self.desc_var.get()
        
        if hasattr(self, 'command_text'):
            self.macro.command = self.command_text.get("1.0", tk.END).strip()
        
        if hasattr(self, 'dice_var'):
            self.macro.dice_formula = self.dice_var.get()
        
        self.on_save()
        self.destroy()
    
    def _delete(self):
        """Makro löschen"""
        if messagebox.askyesno("Löschen", f"Makro '{self.macro.name}' wirklich löschen?"):
            self.macro_manager.delete_macro(self.macro.id)
            self.on_save()
            self.destroy()


class MacroSelectDialog(tk.Toplevel):
    """Dialog zur Makro-Auswahl"""
    
    def __init__(self, parent: tk.Tk, macro_manager: MacroManager,
                 on_select: Callable[[str], None]):
        super().__init__(parent)
        self.macro_manager = macro_manager
        self.on_select = on_select
        
        self.title("Makro auswählen")
        self.geometry("400x400")
        self.configure(bg=UIColors.BG_DARK)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
    
    def _create_widgets(self):
        """UI aufbauen"""
        # Liste der Makros
        list_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.listbox = tk.Listbox(
            list_frame,
            bg=UIColors.BG_MEDIUM,
            fg=UIColors.TEXT,
            selectbackground=UIColors.ACCENT,
            font=("Segoe UI", 11)
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                  command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        # Makros einfügen
        self.macro_ids = []
        for macro_id, macro in self.macro_manager.macros.items():
            self.listbox.insert(tk.END, f"{macro.icon} {macro.name}")
            self.macro_ids.append(macro_id)
        
        # Buttons
        btn_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Button(
            btn_frame,
            text="Auswählen",
            command=self._select,
            bg=UIColors.SUCCESS,
            fg="white"
        ).pack(side=tk.RIGHT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Abbrechen",
            command=self.destroy,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.RIGHT, padx=5)
        
        # Doppelklick
        self.listbox.bind("<Double-1>", lambda e: self._select())
    
    def _select(self):
        """Makro auswählen"""
        selection = self.listbox.curselection()
        if selection:
            macro_id = self.macro_ids[selection[0]]
            self.on_select(macro_id)
            self.destroy()


class MacroManagerWindow(tk.Toplevel):
    """Fenster zur Makro-Verwaltung"""
    
    def __init__(self, parent: tk.Tk, macro_manager: MacroManager,
                 on_change: Callable):
        super().__init__(parent)
        self.macro_manager = macro_manager
        self.on_change = on_change
        
        self.title("Makro-Manager")
        self.configure(bg=UIColors.BG_DARK)
        
        # Fenster zentriert platzieren
        self._center_on_screen(600, 500)
        self.minsize(500, 400)
        
        self._create_widgets()
    
    def _center_on_screen(self, width: int, height: int):
        """Zentriert Fenster"""
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(width, screen_w - 100)
        height = min(height, screen_h - 100)
        x = max(50, (screen_w - width) // 2)
        y = max(30, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _create_widgets(self):
        """UI aufbauen"""
        # Toolbar
        toolbar = tk.Frame(self, bg=UIColors.BG_MEDIUM)
        toolbar.pack(fill=tk.X)
        
        tk.Button(
            toolbar,
            text="➕ Neues Makro",
            command=self._create_macro,
            bg=UIColors.SUCCESS,
            fg="white"
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        tk.Button(
            toolbar,
            text="📂 Importieren",
            command=self._import_macros,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            toolbar,
            text="💾 Exportieren",
            command=self._export_macros,
            bg=UIColors.BG_LIGHT,
            fg=UIColors.TEXT
        ).pack(side=tk.LEFT, padx=5)
        
        # Makro-Liste
        list_frame = tk.Frame(self, bg=UIColors.BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("icon", "name", "type", "description")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        self.tree.heading("icon", text="")
        self.tree.heading("name", text="Name")
        self.tree.heading("type", text="Typ")
        self.tree.heading("description", text="Beschreibung")
        
        self.tree.column("icon", width=40)
        self.tree.column("name", width=150)
        self.tree.column("type", width=100)
        self.tree.column("description", width=250)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Events
        self.tree.bind("<Double-1>", self._on_double_click)
        
        self._refresh_list()
    
    def _refresh_list(self):
        """Liste aktualisieren"""
        self.tree.delete(*self.tree.get_children())
        
        for macro_id, macro in self.macro_manager.macros.items():
            self.tree.insert("", tk.END, iid=macro_id, values=(
                macro.icon,
                macro.name,
                macro.macro_type.value,
                macro.description
            ))
    
    def _create_macro(self):
        """Neues Makro erstellen"""
        macro = self.macro_manager.create_macro()
        MacroEditDialog(self, macro, self.macro_manager, self._on_edit_done)
    
    def _on_double_click(self, event):
        """Doppelklick auf Makro"""
        selection = self.tree.selection()
        if selection:
            macro_id = selection[0]
            macro = self.macro_manager.get_macro(macro_id)
            if macro:
                MacroEditDialog(self, macro, self.macro_manager, self._on_edit_done)
    
    def _on_edit_done(self):
        """Nach Bearbeitung"""
        self._refresh_list()
        self.on_change()
    
    def _import_macros(self):
        """Makros importieren"""
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="Makros importieren",
            filetypes=[("JSON", "*.json")]
        )
        
        if filepath:
            try:
                self.macro_manager.load_from_file(filepath)
                self._refresh_list()
                self.on_change()
            except Exception as e:
                messagebox.showerror("Fehler", f"Import fehlgeschlagen:\n{e}")
    
    def _export_macros(self):
        """Makros exportieren"""
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            title="Makros exportieren",
            filetypes=[("JSON", "*.json")],
            defaultextension=".json"
        )
        
        if filepath:
            try:
                self.macro_manager.save_to_file(filepath)
                messagebox.showinfo("Erfolg", "Makros exportiert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")


# Testfunktion
def test_hotbar_system():
    """Testet das Hotbar-System"""
    root = tk.Tk()
    root.title("Hotbar & Macros Test")
    root.geometry("900x600")
    root.configure(bg=UIColors.BG_DARK)
    
    # Manager erstellen
    macro_manager = MacroManager()
    
    # Test-Makros
    macro_manager.create_macro(
        name="Feuerball",
        icon="🔥",
        macro_type=MacroType.ROLL,
        dice_formula="8d6",
        description="Zauber: Feuerball"
    )
    
    macro_manager.create_macro(
        name="Initiative",
        icon="⚡",
        macro_type=MacroType.ROLL,
        dice_formula="1d20+3",
        description="Initiative würfeln"
    )
    
    macro_manager.create_macro(
        name="GM Nachricht",
        icon="📢",
        macro_type=MacroType.CHAT,
        command="Willkommen zur Session!",
        description="Begrüßung"
    )
    
    # Makros in Hotbar
    macro_manager.assign_to_slot(list(macro_manager.macros.keys())[0], 0)
    macro_manager.assign_to_slot(list(macro_manager.macros.keys())[1], 1)
    macro_manager.assign_to_slot(list(macro_manager.macros.keys())[2], 2)
    
    # Inhalt
    content = tk.Frame(root, bg=UIColors.BG_DARK)
    content.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(
        content,
        text="Hotbar & Macros Demo",
        font=("Segoe UI", 20, "bold"),
        bg=UIColors.BG_DARK,
        fg=UIColors.TEXT
    ).pack(pady=50)
    
    tk.Label(
        content,
        text="Klicke auf die Makros in der Hotbar unten",
        bg=UIColors.BG_DARK,
        fg=UIColors.TEXT_DIM
    ).pack()
    
    # Ergebnis-Anzeige
    result_label = tk.Label(
        content,
        text="",
        font=("Segoe UI", 14),
        bg=UIColors.BG_DARK,
        fg=UIColors.SUCCESS
    )
    result_label.pack(pady=20)
    
    def on_macro_executed(macro, result):
        if macro.macro_type == MacroType.ROLL and isinstance(result, dict):
            rolls = ", ".join(str(r) for r in result.get('rolls', []))
            result_label.config(
                text=f"🎲 {macro.name}: [{rolls}] = {result.get('total', 0)}"
            )
        else:
            result_label.config(text=f"✓ {macro.name} ausgeführt")
    
    # Hotbar
    hotbar = HotbarWidget(root, macro_manager)
    hotbar.pack(side=tk.BOTTOM, fill=tk.X)
    hotbar.on_macro_executed = on_macro_executed
    hotbar.bind_keyboard_shortcuts(root)
    
    root.mainloop()


if __name__ == "__main__":
    test_hotbar_system()
