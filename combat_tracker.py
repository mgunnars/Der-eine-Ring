"""
Combat Tracker für "Der Eine Ring" VTT
========================================

Implementiert Kampf-Management ähnlich FoundryVTT:
- Initiative-Tracking mit automatischer Sortierung
- Aktiver Kämpfer-Indikator
- HP-Management
- Runden-/Zugtimer
- Integration mit Token-System

Inspiriert von FoundryVTT's Combat Encounter System.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, List, Callable, Dict
from dataclasses import dataclass, field
from enum import Enum
import random
import time

# Token-System importieren
try:
    from token_system import Token, TokenLayer, TokenType, TokenCondition
    TOKEN_SYSTEM_AVAILABLE = True
except ImportError:
    TOKEN_SYSTEM_AVAILABLE = False
    print("⚠️ Token-System nicht verfügbar")

# UI-Framework importieren
try:
    from ui_framework import (
        UIColors, UISizes, UIIcons, 
        BaseDialog, VTTButton, VTTLabel,
        show_info, show_warning, ask_confirm
    )
    UI_FRAMEWORK_AVAILABLE = True
except ImportError:
    UI_FRAMEWORK_AVAILABLE = False


class CombatPhase(Enum):
    """Kampfphasen"""
    PREPARATION = "preparation"  # Vor dem Kampf
    INITIATIVE = "initiative"     # Initiative würfeln
    COMBAT = "combat"             # Kampf läuft
    ENDED = "ended"               # Kampf beendet


@dataclass
class Combatant:
    """
    Ein Kämpfer im Combat Tracker.
    
    Kann mit einem Token verknüpft sein oder standalone.
    """
    id: str
    name: str
    initiative: float = 0.0
    hp_current: int = 10
    hp_max: int = 10
    ac: int = 10
    
    # Verknüpfung mit Token
    token_id: Optional[str] = None
    
    # Status
    is_active: bool = False  # Aktuell am Zug
    is_defeated: bool = False  # Besiegt/Tot
    is_hidden: bool = False  # Nur für GM sichtbar
    
    # Aktionen
    has_action: bool = True
    has_bonus_action: bool = True
    has_reaction: bool = True
    has_movement: bool = True
    
    # Notizen für diese Runde
    round_notes: str = ""
    
    def reset_turn(self):
        """Setzt Aktionen für neue Runde zurück"""
        self.has_action = True
        self.has_bonus_action = True
        self.has_reaction = True
        self.has_movement = True
        self.round_notes = ""
    
    def get_hp_percentage(self) -> float:
        """HP als Prozentsatz"""
        if self.hp_max <= 0:
            return 0.0
        return max(0.0, min(1.0, self.hp_current / self.hp_max))
    
    def get_hp_color(self) -> str:
        """Farbe basierend auf HP"""
        pct = self.get_hp_percentage()
        if self.is_defeated:
            return "#888888"
        elif pct > 0.5:
            return "#44ff44"
        elif pct > 0.25:
            return "#ffaa00"
        else:
            return "#ff4444"


class CombatEncounter:
    """
    Ein Kampfbegegnung/Encounter.
    
    Verwaltet alle Kämpfer, Initiative-Reihenfolge, Runden und Züge.
    """
    
    def __init__(self, name: str = "Kampf"):
        self.name = name
        self.combatants: Dict[str, Combatant] = {}
        self.turn_order: List[str] = []  # Sortierte IDs nach Initiative
        
        self.phase = CombatPhase.PREPARATION
        self.current_round = 0
        self.current_turn_index = 0
        
        # Callbacks
        self.on_turn_change: Optional[Callable[[Combatant], None]] = None
        self.on_round_change: Optional[Callable[[int], None]] = None
        self.on_combat_end: Optional[Callable[[], None]] = None
        
        # Timer
        self.turn_start_time: Optional[float] = None
        self.round_start_time: Optional[float] = None
    
    def add_combatant(self, combatant: Combatant) -> str:
        """Fügt Kämpfer hinzu"""
        self.combatants[combatant.id] = combatant
        self._update_turn_order()
        return combatant.id
    
    def add_from_token(self, token: 'Token') -> str:
        """Erstellt Kämpfer aus Token"""
        combatant = Combatant(
            id=f"c_{token.id}",
            name=token.name,
            initiative=token.initiative,
            hp_current=token.hp_current,
            hp_max=token.hp_max,
            ac=token.ac,
            token_id=token.id,
            is_hidden=token.is_hidden
        )
        return self.add_combatant(combatant)
    
    def remove_combatant(self, combatant_id: str):
        """Entfernt Kämpfer"""
        if combatant_id in self.combatants:
            del self.combatants[combatant_id]
            self._update_turn_order()
    
    def get_combatant(self, combatant_id: str) -> Optional[Combatant]:
        """Holt Kämpfer nach ID"""
        return self.combatants.get(combatant_id)
    
    def get_current_combatant(self) -> Optional[Combatant]:
        """Gibt aktuellen Kämpfer zurück"""
        if self.turn_order and 0 <= self.current_turn_index < len(self.turn_order):
            return self.combatants.get(self.turn_order[self.current_turn_index])
        return None
    
    def roll_all_initiatives(self, modifier: int = 0, d20_func: Callable = None):
        """
        Würfelt Initiative für alle Kämpfer.
        
        Args:
            modifier: Globaler Modifikator
            d20_func: Custom W20-Funktion (für externe Würfelsysteme)
        """
        if d20_func is None:
            d20_func = lambda: random.randint(1, 20)
        
        for combatant in self.combatants.values():
            if not combatant.is_defeated:
                roll = d20_func()
                combatant.initiative = roll + modifier
        
        self._update_turn_order()
        self.phase = CombatPhase.INITIATIVE
    
    def set_initiative(self, combatant_id: str, initiative: float):
        """Setzt Initiative für einen Kämpfer"""
        combatant = self.combatants.get(combatant_id)
        if combatant:
            combatant.initiative = initiative
            self._update_turn_order()
    
    def _update_turn_order(self):
        """Aktualisiert Initiative-Reihenfolge"""
        # Sortiere nach Initiative (höchste zuerst), dann nach Name
        active = [c for c in self.combatants.values() if not c.is_defeated]
        sorted_combatants = sorted(active, key=lambda c: (-c.initiative, c.name))
        self.turn_order = [c.id for c in sorted_combatants]
    
    def start_combat(self):
        """Startet den Kampf"""
        if not self.turn_order:
            self.roll_all_initiatives()
        
        self.phase = CombatPhase.COMBAT
        self.current_round = 1
        self.current_turn_index = 0
        self.round_start_time = time.time()
        self.turn_start_time = time.time()
        
        # Ersten Kämpfer aktivieren
        self._set_active_combatant()
        
        if self.on_round_change:
            self.on_round_change(self.current_round)
    
    def next_turn(self):
        """Geht zum nächsten Zug"""
        if self.phase != CombatPhase.COMBAT:
            return
        
        # Aktuellen deaktivieren
        current = self.get_current_combatant()
        if current:
            current.is_active = False
        
        # Nächsten Index
        self.current_turn_index += 1
        
        # Neue Runde?
        if self.current_turn_index >= len(self.turn_order):
            self._next_round()
        else:
            self._set_active_combatant()
    
    def previous_turn(self):
        """Geht zum vorherigen Zug"""
        if self.phase != CombatPhase.COMBAT:
            return
        
        current = self.get_current_combatant()
        if current:
            current.is_active = False
        
        self.current_turn_index -= 1
        
        if self.current_turn_index < 0:
            if self.current_round > 1:
                self.current_round -= 1
                self.current_turn_index = len(self.turn_order) - 1
            else:
                self.current_turn_index = 0
        
        self._set_active_combatant()
    
    def _next_round(self):
        """Startet neue Runde"""
        self.current_round += 1
        self.current_turn_index = 0
        self.round_start_time = time.time()
        
        # Alle Kämpfer zurücksetzen
        for combatant in self.combatants.values():
            combatant.reset_turn()
        
        self._set_active_combatant()
        
        if self.on_round_change:
            self.on_round_change(self.current_round)
    
    def _set_active_combatant(self):
        """Setzt aktuellen Kämpfer aktiv"""
        # Überspringe besiegte Kämpfer
        while (self.current_turn_index < len(self.turn_order) and
               self.combatants.get(self.turn_order[self.current_turn_index], Combatant("", "")).is_defeated):
            self.current_turn_index += 1
        
        if self.current_turn_index >= len(self.turn_order):
            self._next_round()
            return
        
        self.turn_start_time = time.time()
        current = self.get_current_combatant()
        if current:
            current.is_active = True
            if self.on_turn_change:
                self.on_turn_change(current)
    
    def end_combat(self):
        """Beendet den Kampf"""
        self.phase = CombatPhase.ENDED
        
        for combatant in self.combatants.values():
            combatant.is_active = False
        
        if self.on_combat_end:
            self.on_combat_end()
    
    def defeat_combatant(self, combatant_id: str):
        """Markiert Kämpfer als besiegt"""
        combatant = self.combatants.get(combatant_id)
        if combatant:
            combatant.is_defeated = True
            combatant.is_active = False
            combatant.hp_current = 0
            self._update_turn_order()
            
            # Wenn aktueller Kämpfer besiegt, zum nächsten
            if self.get_current_combatant() == combatant:
                self.next_turn()
    
    def get_turn_elapsed(self) -> float:
        """Gibt verstrichene Zug-Zeit in Sekunden zurück"""
        if self.turn_start_time:
            return time.time() - self.turn_start_time
        return 0.0
    
    def get_round_elapsed(self) -> float:
        """Gibt verstrichene Runden-Zeit in Sekunden zurück"""
        if self.round_start_time:
            return time.time() - self.round_start_time
        return 0.0


class CombatTrackerPanel(tk.Frame):
    """
    UI-Panel für den Combat Tracker.
    
    Zeigt alle Kämpfer, Initiative, HP und ermöglicht Kampf-Management.
    """
    
    def __init__(self, parent, encounter: CombatEncounter = None, 
                 token_layer: 'TokenLayer' = None):
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        super().__init__(parent, bg=bg)
        
        self.encounter = encounter or CombatEncounter()
        self.token_layer = token_layer
        
        # Callbacks registrieren
        self.encounter.on_turn_change = self._on_turn_change
        self.encounter.on_round_change = self._on_round_change
        
        self._setup_ui()
        self._start_timer_update()
    
    def _setup_ui(self):
        """Erstellt das UI"""
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        bg_dark = UIColors.BG_DARK if UI_FRAMEWORK_AVAILABLE else "#0a0a0a"
        fg = UIColors.TEXT_PRIMARY if UI_FRAMEWORK_AVAILABLE else "#ffffff"
        accent = UIColors.ACCENT_GOLD if UI_FRAMEWORK_AVAILABLE else "#d4af37"
        
        # Header
        header = tk.Frame(self, bg=bg_dark)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header, text="⚔️ Combat Tracker", bg=bg_dark, fg=accent,
                font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=10)
        
        # Runden-Anzeige
        self.round_label = tk.Label(header, text="Runde: --", bg=bg_dark, fg=fg,
                                   font=("Arial", 12))
        self.round_label.pack(side=tk.RIGHT, padx=10)
        
        # Timer-Anzeige
        self.timer_label = tk.Label(header, text="⏱️ 0:00", bg=bg_dark, fg=fg,
                                   font=("Arial", 10))
        self.timer_label.pack(side=tk.RIGHT, padx=10)
        
        # Control Buttons
        control_frame = tk.Frame(self, bg=bg)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        buttons = [
            ("🎲 Initiative", self._roll_initiative, "#5d2a7d"),
            ("▶️ Start", self._start_combat, "#2a7d2a"),
            ("⏭️ Weiter", self._next_turn, "#2a5d8d"),
            ("⏮️ Zurück", self._previous_turn, "#2a5d8d"),
            ("🏁 Ende", self._end_combat, "#7d2a2a"),
        ]
        
        for text, cmd, color in buttons:
            tk.Button(control_frame, text=text, bg=color, fg="white",
                     font=("Arial", 9), padx=8, pady=4,
                     command=cmd).pack(side=tk.LEFT, padx=2)
        
        # Kämpfer-Liste mit Scrollbar
        list_frame = tk.Frame(self, bg=bg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas für scrollbaren Inhalt
        self.canvas = tk.Canvas(list_frame, bg=bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.combatants_frame = tk.Frame(self.canvas, bg=bg)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.combatants_frame, anchor=tk.NW)
        
        self.combatants_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Add-Button unten
        add_frame = tk.Frame(self, bg=bg)
        add_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(add_frame, text="➕ Kämpfer hinzufügen", bg="#2a7d2a", fg="white",
                 font=("Arial", 10), padx=15, pady=5,
                 command=self._add_combatant).pack(side=tk.LEFT, padx=5)
        
        if self.token_layer:
            tk.Button(add_frame, text="🎭 Von Tokens", bg="#5d2a7d", fg="white",
                     font=("Arial", 10), padx=15, pady=5,
                     command=self._add_from_tokens).pack(side=tk.LEFT, padx=5)
        
        # Initial rendern
        self._refresh_combatants()
    
    def _on_frame_configure(self, event):
        """Aktualisiert Scroll-Region"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Passt Breite an"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _refresh_combatants(self):
        """Aktualisiert Kämpfer-Anzeige"""
        # Alte Widgets entfernen
        for widget in self.combatants_frame.winfo_children():
            widget.destroy()
        
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        bg_active = UIColors.ACCENT_BLUE if UI_FRAMEWORK_AVAILABLE else "#2a5d8d"
        fg = UIColors.TEXT_PRIMARY if UI_FRAMEWORK_AVAILABLE else "#ffffff"
        fg_muted = UIColors.TEXT_MUTED if UI_FRAMEWORK_AVAILABLE else "#666666"
        
        # Kämpfer in Initiative-Reihenfolge anzeigen
        for i, combatant_id in enumerate(self.encounter.turn_order):
            combatant = self.encounter.combatants.get(combatant_id)
            if not combatant:
                continue
            
            # Frame für diesen Kämpfer
            row_bg = bg_active if combatant.is_active else bg
            frame = tk.Frame(self.combatants_frame, bg=row_bg, relief=tk.RIDGE, bd=1)
            frame.pack(fill=tk.X, padx=2, pady=2)
            
            # Initiative
            init_text = f"{int(combatant.initiative):2d}"
            tk.Label(frame, text=init_text, bg=row_bg, fg=fg,
                    font=("Arial", 12, "bold"), width=3).pack(side=tk.LEFT, padx=5)
            
            # Aktiv-Indikator
            active_text = "▶" if combatant.is_active else "  "
            tk.Label(frame, text=active_text, bg=row_bg, fg="#ffaa00",
                    font=("Arial", 14, "bold")).pack(side=tk.LEFT)
            
            # Name
            name_color = fg_muted if combatant.is_defeated else fg
            name_style = "overstrike" if combatant.is_defeated else "normal"
            name_label = tk.Label(frame, text=combatant.name, bg=row_bg, fg=name_color,
                                 font=("Arial", 11, name_style))
            name_label.pack(side=tk.LEFT, padx=10)
            
            # HP-Anzeige
            hp_color = combatant.get_hp_color()
            hp_text = f"HP: {combatant.hp_current}/{combatant.hp_max}"
            tk.Label(frame, text=hp_text, bg=row_bg, fg=hp_color,
                    font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
            
            # HP-Bar
            bar_frame = tk.Frame(frame, bg="#333333", width=80, height=12)
            bar_frame.pack(side=tk.LEFT, padx=5)
            bar_frame.pack_propagate(False)
            
            hp_pct = combatant.get_hp_percentage()
            bar_width = int(80 * hp_pct)
            if bar_width > 0:
                bar_fill = tk.Frame(bar_frame, bg=hp_color, width=bar_width)
                bar_fill.pack(side=tk.LEFT, fill=tk.Y)
            
            # AC
            tk.Label(frame, text=f"🛡️{combatant.ac}", bg=row_bg, fg=fg,
                    font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
            
            # Aktionen-Buttons
            btn_frame = tk.Frame(frame, bg=row_bg)
            btn_frame.pack(side=tk.RIGHT, padx=5)
            
            # Schaden-Button
            tk.Button(btn_frame, text="💔", bg="#7d2a2a", fg="white",
                     font=("Arial", 8), padx=3,
                     command=lambda c=combatant: self._damage_combatant(c)).pack(side=tk.LEFT, padx=1)
            
            # Heilen-Button
            tk.Button(btn_frame, text="💚", bg="#2a7d2a", fg="white",
                     font=("Arial", 8), padx=3,
                     command=lambda c=combatant: self._heal_combatant(c)).pack(side=tk.LEFT, padx=1)
            
            # Besiegt-Button
            defeat_text = "💀" if not combatant.is_defeated else "↺"
            tk.Button(btn_frame, text=defeat_text, bg="#444444", fg="white",
                     font=("Arial", 8), padx=3,
                     command=lambda c=combatant: self._toggle_defeated(c)).pack(side=tk.LEFT, padx=1)
        
        # Nicht in der Turn-Order (noch nicht hinzugefügt, etc.)
        for combatant_id, combatant in self.encounter.combatants.items():
            if combatant_id not in self.encounter.turn_order:
                frame = tk.Frame(self.combatants_frame, bg="#333333", relief=tk.RIDGE, bd=1)
                frame.pack(fill=tk.X, padx=2, pady=2)
                
                tk.Label(frame, text="?", bg="#333333", fg=fg_muted,
                        font=("Arial", 12, "bold"), width=3).pack(side=tk.LEFT, padx=5)
                tk.Label(frame, text=combatant.name, bg="#333333", fg=fg_muted,
                        font=("Arial", 11)).pack(side=tk.LEFT, padx=10)
                tk.Label(frame, text="(Keine Initiative)", bg="#333333", fg=fg_muted,
                        font=("Arial", 9, "italic")).pack(side=tk.LEFT)
    
    def _roll_initiative(self):
        """Würfelt Initiative für alle"""
        self.encounter.roll_all_initiatives()
        self._refresh_combatants()
        self._update_round_display()
    
    def _start_combat(self):
        """Startet den Kampf"""
        self.encounter.start_combat()
        self._refresh_combatants()
        self._update_round_display()
    
    def _next_turn(self):
        """Nächster Zug"""
        self.encounter.next_turn()
        self._refresh_combatants()
    
    def _previous_turn(self):
        """Vorheriger Zug"""
        self.encounter.previous_turn()
        self._refresh_combatants()
    
    def _end_combat(self):
        """Beendet Kampf"""
        self.encounter.end_combat()
        self._refresh_combatants()
        self._update_round_display()
    
    def _add_combatant(self):
        """Fügt neuen Kämpfer hinzu"""
        from tkinter import simpledialog
        name = simpledialog.askstring("Neuer Kämpfer", "Name des Kämpfers:")
        if name:
            import uuid
            combatant = Combatant(
                id=str(uuid.uuid4())[:8],
                name=name,
                initiative=random.randint(1, 20)
            )
            self.encounter.add_combatant(combatant)
            self._refresh_combatants()
    
    def _add_from_tokens(self):
        """Fügt alle Tokens als Kämpfer hinzu"""
        if not self.token_layer:
            return
        
        added = 0
        for token in self.token_layer.get_all_tokens():
            # Prüfe ob bereits vorhanden
            exists = any(c.token_id == token.id for c in self.encounter.combatants.values())
            if not exists:
                self.encounter.add_from_token(token)
                added += 1
        
        self._refresh_combatants()
        if UI_FRAMEWORK_AVAILABLE:
            show_info(self, "Tokens hinzugefügt", f"{added} Token(s) als Kämpfer hinzugefügt!")
    
    def _damage_combatant(self, combatant: Combatant):
        """Fügt Schaden zu"""
        from tkinter import simpledialog
        damage = simpledialog.askinteger("Schaden", f"Schaden an {combatant.name}:", minvalue=0)
        if damage:
            combatant.hp_current = max(0, combatant.hp_current - damage)
            if combatant.hp_current <= 0:
                combatant.is_defeated = True
            self._refresh_combatants()
    
    def _heal_combatant(self, combatant: Combatant):
        """Heilt Kämpfer"""
        from tkinter import simpledialog
        healing = simpledialog.askinteger("Heilung", f"Heilung für {combatant.name}:", minvalue=0)
        if healing:
            combatant.hp_current = min(combatant.hp_max, combatant.hp_current + healing)
            if combatant.hp_current > 0:
                combatant.is_defeated = False
            self._refresh_combatants()
    
    def _toggle_defeated(self, combatant: Combatant):
        """Toggled Besiegt-Status"""
        combatant.is_defeated = not combatant.is_defeated
        if combatant.is_defeated:
            combatant.hp_current = 0
            self.encounter._update_turn_order()
        self._refresh_combatants()
    
    def _on_turn_change(self, combatant: Combatant):
        """Callback bei Zug-Wechsel"""
        self._refresh_combatants()
    
    def _on_round_change(self, round_num: int):
        """Callback bei Runden-Wechsel"""
        self._update_round_display()
    
    def _update_round_display(self):
        """Aktualisiert Runden-Anzeige"""
        if self.encounter.phase == CombatPhase.COMBAT:
            self.round_label.config(text=f"Runde: {self.encounter.current_round}")
        elif self.encounter.phase == CombatPhase.ENDED:
            self.round_label.config(text="Kampf beendet")
        else:
            self.round_label.config(text="Runde: --")
    
    def _start_timer_update(self):
        """Startet Timer-Updates"""
        self._update_timer()
    
    def _update_timer(self):
        """Aktualisiert Timer-Anzeige"""
        if self.encounter.phase == CombatPhase.COMBAT:
            elapsed = self.encounter.get_turn_elapsed()
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timer_label.config(text=f"⏱️ {minutes}:{seconds:02d}")
        else:
            self.timer_label.config(text="⏱️ --:--")
        
        # Alle 500ms aktualisieren
        self.after(500, self._update_timer)


class CombatTrackerWindow(tk.Toplevel):
    """
    Standalone-Fenster für den Combat Tracker.
    """
    
    def __init__(self, parent, encounter: CombatEncounter = None,
                 token_layer: 'TokenLayer' = None):
        super().__init__(parent)
        
        self.title("⚔️ Combat Tracker")
        
        # Größe
        self.geometry("500x600")
        self.minsize(400, 500)
        
        bg = UIColors.BG_PANEL if UI_FRAMEWORK_AVAILABLE else "#1e1e1e"
        self.configure(bg=bg)
        
        # Combat Tracker Panel
        self.tracker = CombatTrackerPanel(self, encounter, token_layer)
        self.tracker.pack(fill=tk.BOTH, expand=True)


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Combat Tracker Test")
    root.geometry("600x700")
    root.configure(bg="#1a1a1a")
    
    # Test-Encounter erstellen
    encounter = CombatEncounter("Test-Kampf")
    
    # Test-Kämpfer
    import uuid
    combatants = [
        Combatant(id=str(uuid.uuid4())[:8], name="Aragorn", initiative=18, 
                 hp_current=50, hp_max=50, ac=16),
        Combatant(id=str(uuid.uuid4())[:8], name="Legolas", initiative=20,
                 hp_current=35, hp_max=40, ac=15),
        Combatant(id=str(uuid.uuid4())[:8], name="Gimli", initiative=12,
                 hp_current=60, hp_max=60, ac=18),
        Combatant(id=str(uuid.uuid4())[:8], name="Orc Krieger 1", initiative=14,
                 hp_current=15, hp_max=20, ac=13),
        Combatant(id=str(uuid.uuid4())[:8], name="Orc Krieger 2", initiative=8,
                 hp_current=20, hp_max=20, ac=13),
        Combatant(id=str(uuid.uuid4())[:8], name="Orc Hauptmann", initiative=16,
                 hp_current=45, hp_max=45, ac=15),
    ]
    
    for c in combatants:
        encounter.add_combatant(c)
    
    # Panel erstellen
    tracker = CombatTrackerPanel(root, encounter)
    tracker.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    root.mainloop()
