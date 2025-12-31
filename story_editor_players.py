"""
Story Editor - Player Panel
=============================

Spieler-Verwaltung im Story Editor für Definition von Spielern und Teams,
die auf Spawn-Hexagonen platziert werden können.

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from typing import Optional, Callable, List
import os
import json

from player_system import (
    PlayerManager, PlayerDefinition, TeamDefinition,
    TEAM_COLORS
)


class PlayerPanel(tk.Frame):
    """Panel zur Verwaltung von Spieler- und Team-Definitionen im Story Editor"""
    
    def __init__(self, parent, on_change: Optional[Callable] = None):
        super().__init__(parent, bg="#1a1a2e")
        self.on_change = on_change
        self.player_manager = PlayerManager()
        self.selected_player_id: Optional[str] = None
        self.selected_team_id: Optional[str] = None
        
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        # Header
        header = tk.Frame(self, bg="#16213e")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header, text="🎮 SPIELER & TEAMS", 
                font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(side=tk.LEFT, padx=10, pady=5)
        
        # Notebook für Tabs (Spieler / Teams)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Spieler-Tab
        self.players_tab = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.players_tab, text="👤 Spieler")
        self._create_players_tab()
        
        # Teams-Tab
        self.teams_tab = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.teams_tab, text="👥 Teams")
        self._create_teams_tab()
        
        # Import/Export
        io_frame = tk.Frame(self, bg="#1a1a2e")
        io_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(io_frame, text="💾 Speichern", command=self._save_players,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(io_frame, text="📂 Laden", command=self._load_players,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
    
    def _create_players_tab(self):
        """Erstellt den Spieler-Tab"""
        # Toolbar
        toolbar = tk.Frame(self.players_tab, bg="#1a1a2e")
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(toolbar, text="➕ Neuer Spieler", command=self._add_player,
                 bg="#28a745", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="✏️ Bearbeiten", command=self._edit_player,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🗑️ Löschen", command=self._delete_player,
                 bg="#dc3545", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        
        # Spieler-Liste
        list_frame = tk.Frame(self.players_tab, bg="#1a1a2e")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.player_listbox = tk.Listbox(
            list_frame, 
            bg="#0f3460", fg="white",
            selectbackground="#e94560",
            selectforeground="white",
            font=("Arial", 11),
            activestyle="none",
            yscrollcommand=scrollbar.set
        )
        self.player_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.player_listbox.yview)
        
        self.player_listbox.bind("<<ListboxSelect>>", self._on_player_select)
        self.player_listbox.bind("<Double-1>", lambda e: self._edit_player())
        
        # Details
        self.player_details_frame = tk.Frame(self.players_tab, bg="#16213e")
        self.player_details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(self.player_details_frame, text="📋 DETAILS", 
                font=("Arial", 10, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=5)
        
        self.player_details = tk.Frame(self.player_details_frame, bg="#16213e")
        self.player_details.pack(fill=tk.X, padx=10, pady=5)
        
        self.player_labels = {}
        for field, label_text in [("name", "Name:"), ("team", "Team:"), 
                                   ("color", "Farbe:"), ("active", "Status:")]:
            frame = tk.Frame(self.player_details, bg="#16213e")
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(frame, text=label_text, width=12, anchor=tk.W,
                    bg="#16213e", fg="#888888", font=("Arial", 9)).pack(side=tk.LEFT)
            
            self.player_labels[field] = tk.Label(
                frame, text="-", anchor=tk.W,
                bg="#16213e", fg="white", font=("Arial", 9)
            )
            self.player_labels[field].pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def _create_teams_tab(self):
        """Erstellt den Teams-Tab"""
        # Toolbar
        toolbar = tk.Frame(self.teams_tab, bg="#1a1a2e")
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(toolbar, text="➕ Neues Team", command=self._add_team,
                 bg="#28a745", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="✏️ Bearbeiten", command=self._edit_team,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🗑️ Löschen", command=self._delete_team,
                 bg="#dc3545", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        
        # Team-Liste
        list_frame = tk.Frame(self.teams_tab, bg="#1a1a2e")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.team_listbox = tk.Listbox(
            list_frame, 
            bg="#0f3460", fg="white",
            selectbackground="#e94560",
            selectforeground="white",
            font=("Arial", 11),
            activestyle="none",
            yscrollcommand=scrollbar.set
        )
        self.team_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.team_listbox.yview)
        
        self.team_listbox.bind("<<ListboxSelect>>", self._on_team_select)
        self.team_listbox.bind("<Double-1>", lambda e: self._edit_team())
        
        # Details
        self.team_details_frame = tk.Frame(self.teams_tab, bg="#16213e")
        self.team_details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(self.team_details_frame, text="📋 TEAM DETAILS", 
                font=("Arial", 10, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=5)
        
        self.team_details = tk.Frame(self.team_details_frame, bg="#16213e")
        self.team_details.pack(fill=tk.X, padx=10, pady=5)
        
        self.team_labels = {}
        for field, label_text in [("name", "Name:"), ("color", "Farbe:"), 
                                   ("members", "Mitglieder:"), ("position", "Position:")]:
            frame = tk.Frame(self.team_details, bg="#16213e")
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(frame, text=label_text, width=12, anchor=tk.W,
                    bg="#16213e", fg="#888888", font=("Arial", 9)).pack(side=tk.LEFT)
            
            self.team_labels[field] = tk.Label(
                frame, text="-", anchor=tk.W,
                bg="#16213e", fg="white", font=("Arial", 9)
            )
            self.team_labels[field].pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # =========================================================
    # SPIELER-FUNKTIONEN
    # =========================================================
    
    def refresh(self):
        """Aktualisiert beide Listen."""
        self._refresh_player_list()
        self._refresh_team_list()
    
    def _refresh_player_list(self):
        """Aktualisiert die Spieler-Liste."""
        self.player_listbox.delete(0, tk.END)
        
        for player in self.player_manager.players.values():
            icon = "👤" if player.is_active else "👻"
            team_info = f" [{player.team_name}]" if player.team_name else ""
            self.player_listbox.insert(tk.END, f"{icon} {player.name}{team_info}")
        
        self._update_player_details()
    
    def _on_player_select(self, event):
        """Handler für Spieler-Auswahl."""
        selection = self.player_listbox.curselection()
        if selection:
            idx = selection[0]
            player_list = list(self.player_manager.players.values())
            if idx < len(player_list):
                self.selected_player_id = player_list[idx].id
                self._update_player_details()
    
    def _update_player_details(self):
        """Aktualisiert die Spieler-Details."""
        if self.selected_player_id:
            player = self.player_manager.get_player(self.selected_player_id)
            if player:
                self.player_labels["name"].config(text=player.name)
                self.player_labels["team"].config(text=player.team_name or "(Kein Team)")
                self.player_labels["color"].config(text=player.color, fg=player.color)
                self.player_labels["active"].config(
                    text="Aktiv" if player.is_active else "Inaktiv",
                    fg="#00ff00" if player.is_active else "#ff0000"
                )
        else:
            for label in self.player_labels.values():
                label.config(text="-")
    
    def _add_player(self):
        """Fügt einen neuen Spieler hinzu."""
        dialog = PlayerEditorDialog(self, self.player_manager)
        self.wait_window(dialog)
        
        if dialog.result:
            self.player_manager.add_player(dialog.result)
            self._refresh_player_list()
            self._notify_change()
    
    def _edit_player(self):
        """Bearbeitet den ausgewählten Spieler."""
        if not self.selected_player_id:
            return
        
        player = self.player_manager.get_player(self.selected_player_id)
        if not player:
            return
        
        dialog = PlayerEditorDialog(self, self.player_manager, player)
        self.wait_window(dialog)
        
        if dialog.result:
            # Spieler aktualisieren
            self.player_manager.players[player.id] = dialog.result
            self._refresh_player_list()
            self._notify_change()
    
    def _delete_player(self):
        """Löscht den ausgewählten Spieler."""
        if not self.selected_player_id:
            return
        
        player = self.player_manager.get_player(self.selected_player_id)
        if not player:
            return
        
        if messagebox.askyesno("Spieler löschen", 
                               f"Spieler '{player.name}' wirklich löschen?"):
            self.player_manager.remove_player(self.selected_player_id)
            self.selected_player_id = None
            self._refresh_player_list()
            self._notify_change()
    
    # =========================================================
    # TEAM-FUNKTIONEN
    # =========================================================
    
    def _refresh_team_list(self):
        """Aktualisiert die Team-Liste."""
        self.team_listbox.delete(0, tk.END)
        
        for team in self.player_manager.teams.values():
            member_count = len(team.member_ids)
            self.team_listbox.insert(tk.END, f"👥 {team.name} ({member_count} Spieler)")
        
        self._update_team_details()
    
    def _on_team_select(self, event):
        """Handler für Team-Auswahl."""
        selection = self.team_listbox.curselection()
        if selection:
            idx = selection[0]
            team_list = list(self.player_manager.teams.values())
            if idx < len(team_list):
                self.selected_team_id = team_list[idx].id
                self._update_team_details()
    
    def _update_team_details(self):
        """Aktualisiert die Team-Details."""
        if self.selected_team_id:
            team = self.player_manager.get_team(self.selected_team_id)
            if team:
                self.team_labels["name"].config(text=team.name)
                self.team_labels["color"].config(text=team.color, fg=team.color)
                
                members = self.player_manager.get_team_members(team.id)
                member_names = ", ".join([m.name for m in members]) if members else "(keine)"
                self.team_labels["members"].config(text=member_names)
                self.team_labels["position"].config(text=f"({team.hex_q}, {team.hex_r})")
        else:
            for label in self.team_labels.values():
                label.config(text="-")
    
    def _add_team(self):
        """Fügt ein neues Team hinzu."""
        dialog = TeamEditorDialog(self, self.player_manager)
        self.wait_window(dialog)
        
        if dialog.result:
            self.player_manager.add_team(dialog.result)
            self._refresh_team_list()
            self._notify_change()
    
    def _edit_team(self):
        """Bearbeitet das ausgewählte Team."""
        if not self.selected_team_id:
            return
        
        team = self.player_manager.get_team(self.selected_team_id)
        if not team:
            return
        
        dialog = TeamEditorDialog(self, self.player_manager, team)
        self.wait_window(dialog)
        
        if dialog.result:
            self.player_manager.teams[team.id] = dialog.result
            self._refresh_team_list()
            self._refresh_player_list()  # Team-Namen bei Spielern aktualisieren
            self._notify_change()
    
    def _delete_team(self):
        """Löscht das ausgewählte Team."""
        if not self.selected_team_id:
            return
        
        team = self.player_manager.get_team(self.selected_team_id)
        if not team:
            return
        
        if messagebox.askyesno("Team löschen", 
                               f"Team '{team.name}' wirklich löschen?\n"
                               f"Spieler werden zu Einzelspielern."):
            self.player_manager.remove_team(self.selected_team_id)
            self.selected_team_id = None
            self._refresh_team_list()
            self._refresh_player_list()
            self._notify_change()
    
    # =========================================================
    # SPEICHERN/LADEN
    # =========================================================
    
    def _save_players(self):
        """Speichert Spieler-Daten."""
        filepath = filedialog.asksaveasfilename(
            title="Spieler speichern",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if filepath:
            self.player_manager.save_to_file(filepath)
            messagebox.showinfo("Gespeichert", f"Spieler gespeichert: {filepath}")
    
    def _load_players(self):
        """Lädt Spieler-Daten."""
        filepath = filedialog.askopenfilename(
            title="Spieler laden",
            filetypes=[("JSON", "*.json")]
        )
        if filepath:
            self.player_manager = PlayerManager.load_from_file(filepath)
            self.refresh()
            self._notify_change()
            messagebox.showinfo("Geladen", f"Spieler geladen: {filepath}")
    
    def _notify_change(self):
        """Benachrichtigt über Änderungen."""
        if self.on_change:
            self.on_change()
    
    # =========================================================
    # API
    # =========================================================
    
    def get_player_manager(self) -> PlayerManager:
        """Gibt den Player Manager zurück."""
        return self.player_manager
    
    def set_player_manager(self, manager: PlayerManager):
        """Setzt den Player Manager."""
        self.player_manager = manager
        self.refresh()
    
    def to_dict(self) -> dict:
        """Serialisiert die Spieler-Daten."""
        return self.player_manager.to_dict()
    
    def from_dict(self, data: dict):
        """Lädt Spieler-Daten aus Dictionary."""
        self.player_manager = PlayerManager.from_dict(data)
        self.refresh()


class PlayerEditorDialog(tk.Toplevel):
    """Dialog zum Erstellen/Bearbeiten eines Spielers"""
    
    def __init__(self, parent, player_manager: PlayerManager, 
                 player: PlayerDefinition = None):
        super().__init__(parent)
        
        self.title("Spieler bearbeiten" if player else "Neuer Spieler")
        self.configure(bg="#1a1a2e")
        self.geometry("400x450")
        self.resizable(False, False)
        
        self.player_manager = player_manager
        self.player = player
        self.result = None
        
        self._create_widgets()
        
        if player:
            self._load_player(player)
        
        self.transient(parent)
        self.grab_set()
        self._center_on_parent(parent)
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 450) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
    
    def _create_widgets(self):
        main = tk.Frame(self, bg="#1a1a2e", padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Name
        tk.Label(main, text="Name:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar(value="Neuer Spieler")
        tk.Entry(main, textvariable=self.name_var, bg="#0f3460", fg="white",
                insertbackground="white", font=("Arial", 11)).pack(fill=tk.X, pady=(0, 15))
        
        # Farbe
        tk.Label(main, text="Farbe:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        
        color_frame = tk.Frame(main, bg="#1a1a2e")
        color_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.color_var = tk.StringVar(value="#4488FF")
        
        for name, color in TEAM_COLORS.items():
            btn = tk.Button(color_frame, text="  ", bg=color, width=3,
                           command=lambda c=color: self._set_color(c),
                           relief=tk.FLAT)
            btn.pack(side=tk.LEFT, padx=2)
        
        # Custom Color Button
        tk.Button(color_frame, text="🎨", command=self._pick_color,
                  bg="#0f3460", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        
        # Farb-Vorschau
        self.color_preview = tk.Label(main, text="Ausgewählte Farbe", 
                                      bg=self.color_var.get(), fg="white",
                                      font=("Arial", 10), pady=5)
        self.color_preview.pack(fill=tk.X, pady=(0, 15))
        
        # Team-Auswahl
        tk.Label(main, text="Team:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        
        self.team_var = tk.StringVar(value="(Kein Team)")
        team_options = ["(Kein Team)"] + [t.name for t in self.player_manager.teams.values()]
        self.team_combo = ttk.Combobox(main, textvariable=self.team_var, 
                                        values=team_options, state="readonly")
        self.team_combo.pack(fill=tk.X, pady=(0, 15))
        
        # Aktiv
        self.active_var = tk.BooleanVar(value=True)
        tk.Checkbutton(main, text="Spieler ist aktiv", variable=self.active_var,
                       bg="#1a1a2e", fg="white", selectcolor="#0f3460",
                       activebackground="#1a1a2e", activeforeground="white",
                       font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 15))
        
        # Notizen
        tk.Label(main, text="Notizen:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        self.notes_text = tk.Text(main, height=4, bg="#0f3460", fg="white",
                                  insertbackground="white", font=("Arial", 10))
        self.notes_text.pack(fill=tk.X, pady=(0, 15))
        
        # Buttons
        btn_frame = tk.Frame(main, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="✓ Speichern", command=self._save,
                  bg="#28a745", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self.destroy,
                  bg="#dc3545", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
    
    def _set_color(self, color):
        self.color_var.set(color)
        self.color_preview.config(bg=color)
    
    def _pick_color(self):
        color = colorchooser.askcolor(title="Farbe wählen", color=self.color_var.get())
        if color[1]:
            self._set_color(color[1])
    
    def _load_player(self, player: PlayerDefinition):
        """Lädt Spieler-Daten in den Dialog."""
        self.name_var.set(player.name)
        self._set_color(player.color)
        
        if player.team_name:
            self.team_var.set(player.team_name)
        
        self.active_var.set(player.is_active)
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", player.notes)
    
    def _save(self):
        """Speichert den Spieler."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Name darf nicht leer sein!")
            return
        
        if self.player:
            # Bearbeiten
            result = self.player
            result.name = name
            result.color = self.color_var.get()
            result.is_active = self.active_var.get()
            result.notes = self.notes_text.get("1.0", tk.END).strip()
        else:
            # Neu
            result = PlayerDefinition(
                name=name,
                color=self.color_var.get(),
                is_active=self.active_var.get(),
                notes=self.notes_text.get("1.0", tk.END).strip()
            )
        
        # Team-Zuordnung
        team_name = self.team_var.get()
        if team_name != "(Kein Team)":
            for team in self.player_manager.teams.values():
                if team.name == team_name:
                    result.team_id = team.id
                    result.team_name = team.name
                    result.color = team.color  # Team-Farbe übernehmen
                    break
        else:
            result.team_id = None
            result.team_name = ""
        
        self.result = result
        self.destroy()


class TeamEditorDialog(tk.Toplevel):
    """Dialog zum Erstellen/Bearbeiten eines Teams"""
    
    def __init__(self, parent, player_manager: PlayerManager, 
                 team: TeamDefinition = None):
        super().__init__(parent)
        
        self.title("Team bearbeiten" if team else "Neues Team")
        self.configure(bg="#1a1a2e")
        self.geometry("450x500")
        self.resizable(False, False)
        
        self.player_manager = player_manager
        self.team = team
        self.result = None
        
        self._create_widgets()
        
        if team:
            self._load_team(team)
        
        self.transient(parent)
        self.grab_set()
        self._center_on_parent(parent)
    
    def _center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 500) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
    
    def _create_widgets(self):
        main = tk.Frame(self, bg="#1a1a2e", padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Name
        tk.Label(main, text="Team-Name:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar(value="Neues Team")
        tk.Entry(main, textvariable=self.name_var, bg="#0f3460", fg="white",
                insertbackground="white", font=("Arial", 11)).pack(fill=tk.X, pady=(0, 15))
        
        # Farbe
        tk.Label(main, text="Team-Farbe:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        
        color_frame = tk.Frame(main, bg="#1a1a2e")
        color_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.color_var = tk.StringVar(value="#4488FF")
        
        for name, color in TEAM_COLORS.items():
            btn = tk.Button(color_frame, text="  ", bg=color, width=2,
                           command=lambda c=color: self._set_color(c),
                           relief=tk.FLAT)
            btn.pack(side=tk.LEFT, padx=1)
        
        # Farb-Vorschau
        self.color_preview = tk.Label(main, text="Team-Farbe", 
                                      bg=self.color_var.get(), fg="white",
                                      font=("Arial", 10), pady=5)
        self.color_preview.pack(fill=tk.X, pady=(0, 15))
        
        # Mitglieder
        tk.Label(main, text="Mitglieder:", bg="#1a1a2e", fg="white",
                font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 5))
        
        members_frame = tk.Frame(main, bg="#1a1a2e")
        members_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Zwei Listen: Verfügbar | Im Team
        left_frame = tk.Frame(members_frame, bg="#1a1a2e")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(left_frame, text="Verfügbar:", bg="#1a1a2e", fg="#888888",
                font=("Arial", 9)).pack(anchor=tk.W)
        
        self.available_listbox = tk.Listbox(left_frame, bg="#0f3460", fg="white",
                                            selectbackground="#e94560", height=6)
        self.available_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Buttons in der Mitte
        btn_frame = tk.Frame(members_frame, bg="#1a1a2e")
        btn_frame.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="→", command=self._add_member,
                  bg="#28a745", fg="white", width=3).pack(pady=2)
        tk.Button(btn_frame, text="←", command=self._remove_member,
                  bg="#dc3545", fg="white", width=3).pack(pady=2)
        
        right_frame = tk.Frame(members_frame, bg="#1a1a2e")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(right_frame, text="Im Team:", bg="#1a1a2e", fg="#888888",
                font=("Arial", 9)).pack(anchor=tk.W)
        
        self.team_listbox = tk.Listbox(right_frame, bg="#0f3460", fg="white",
                                       selectbackground="#e94560", height=6)
        self.team_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Gemeinsame Sicht
        self.shared_vision_var = tk.BooleanVar(value=True)
        tk.Checkbutton(main, text="Teammitglieder teilen Sichtfeld", 
                       variable=self.shared_vision_var,
                       bg="#1a1a2e", fg="white", selectcolor="#0f3460",
                       activebackground="#1a1a2e", activeforeground="white",
                       font=("Arial", 10)).pack(anchor=tk.W, pady=(0, 15))
        
        # Buttons
        btn_frame = tk.Frame(main, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X)
        
        tk.Button(btn_frame, text="✓ Speichern", command=self._save,
                  bg="#28a745", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="✕ Abbrechen", command=self.destroy,
                  bg="#dc3545", fg="white", font=("Arial", 10),
                  relief=tk.FLAT, padx=20).pack(side=tk.RIGHT, padx=5)
        
        # Listen füllen
        self._refresh_member_lists()
    
    def _set_color(self, color):
        self.color_var.set(color)
        self.color_preview.config(bg=color)
    
    def _refresh_member_lists(self):
        """Aktualisiert die Mitglieder-Listen."""
        self.available_listbox.delete(0, tk.END)
        self.team_listbox.delete(0, tk.END)
        
        current_members = set()
        if self.team:
            current_members = set(self.team.member_ids)
        
        for player in self.player_manager.players.values():
            if player.id in current_members:
                self.team_listbox.insert(tk.END, player.name)
            else:
                # Nur Spieler ohne Team oder aus diesem Team
                if not player.team_id or player.team_id == (self.team.id if self.team else None):
                    self.available_listbox.insert(tk.END, player.name)
    
    def _add_member(self):
        """Fügt ausgewählten Spieler zum Team hinzu."""
        selection = self.available_listbox.curselection()
        if selection:
            name = self.available_listbox.get(selection[0])
            self.available_listbox.delete(selection[0])
            self.team_listbox.insert(tk.END, name)
    
    def _remove_member(self):
        """Entfernt ausgewählten Spieler aus Team."""
        selection = self.team_listbox.curselection()
        if selection:
            name = self.team_listbox.get(selection[0])
            self.team_listbox.delete(selection[0])
            self.available_listbox.insert(tk.END, name)
    
    def _load_team(self, team: TeamDefinition):
        """Lädt Team-Daten in den Dialog."""
        self.name_var.set(team.name)
        self._set_color(team.color)
        self.shared_vision_var.set(team.shared_vision)
        self._refresh_member_lists()
    
    def _save(self):
        """Speichert das Team."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Fehler", "Name darf nicht leer sein!")
            return
        
        if self.team:
            result = self.team
            result.name = name
            result.color = self.color_var.get()
            result.shared_vision = self.shared_vision_var.get()
        else:
            result = TeamDefinition(
                name=name,
                color=self.color_var.get(),
                shared_vision=self.shared_vision_var.get()
            )
        
        # Mitglieder aktualisieren
        new_member_ids = []
        for i in range(self.team_listbox.size()):
            player_name = self.team_listbox.get(i)
            for player in self.player_manager.players.values():
                if player.name == player_name:
                    new_member_ids.append(player.id)
                    break
        
        result.member_ids = new_member_ids
        
        self.result = result
        self.destroy()


if __name__ == "__main__":
    # Test
    root = tk.Tk()
    root.title("Player Panel Test")
    root.geometry("400x600")
    root.configure(bg="#1a1a2e")
    
    panel = PlayerPanel(root)
    panel.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
