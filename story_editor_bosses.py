"""
Story Editor - Boss Panel
==========================

Boss-Verwaltung im Story Editor für Definition von Bossen,
die auf Boss-Hexagonen platziert werden können.

Autor: VTT Development Team
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable, List
import os

from boss_system import BossManager, BossDefinition, BossEditorDialog


class BossPanel(tk.Frame):
    """Panel zur Verwaltung von Boss-Definitionen im Story Editor"""
    
    def __init__(self, parent, on_change: Optional[Callable] = None):
        super().__init__(parent, bg="#1a1a2e")
        self.on_change = on_change
        self.boss_manager = BossManager()
        self.selected_boss_id: Optional[str] = None
        
        self._create_widgets()
        self.refresh()
    
    def _create_widgets(self):
        # Header
        header = tk.Frame(self, bg="#16213e")
        header.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(header, text="🐉 BOSS-VERWALTUNG", 
                font=("Arial", 12, "bold"),
                bg="#16213e", fg="#e94560").pack(side=tk.LEFT, padx=10, pady=5)
        
        # Toolbar
        toolbar = tk.Frame(self, bg="#1a1a2e")
        toolbar.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Button(toolbar, text="➕ Neuer Boss", command=self._add_boss,
                 bg="#28a745", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="✏️ Bearbeiten", command=self._edit_boss,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🗑️ Löschen", command=self._delete_boss,
                 bg="#dc3545", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)
        
        # Boss-Liste
        list_frame = tk.Frame(self, bg="#1a1a2e")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.boss_listbox = tk.Listbox(
            list_frame, 
            bg="#0f3460", fg="white",
            selectbackground="#e94560",
            selectforeground="white",
            font=("Arial", 11),
            activestyle="none",
            yscrollcommand=scrollbar.set
        )
        self.boss_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.boss_listbox.yview)
        
        self.boss_listbox.bind("<<ListboxSelect>>", self._on_select)
        self.boss_listbox.bind("<Double-1>", lambda e: self._edit_boss())
        
        # Details-Bereich
        self.details_frame = tk.Frame(self, bg="#16213e")
        self.details_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(self.details_frame, text="📋 DETAILS", 
                font=("Arial", 10, "bold"),
                bg="#16213e", fg="#e94560").pack(anchor=tk.W, padx=10, pady=5)
        
        self.details_content = tk.Frame(self.details_frame, bg="#16213e")
        self.details_content.pack(fill=tk.X, padx=10, pady=5)
        
        self.details_labels = {}
        for field in ["name", "health", "image", "description"]:
            frame = tk.Frame(self.details_content, bg="#16213e")
            frame.pack(fill=tk.X, pady=2)
            
            label_text = {
                "name": "Name:",
                "health": "HP:",
                "image": "Bild:",
                "description": "Beschreibung:"
            }[field]
            
            tk.Label(frame, text=label_text, width=12, anchor=tk.W,
                    bg="#16213e", fg="#888888", font=("Arial", 9)).pack(side=tk.LEFT)
            
            self.details_labels[field] = tk.Label(
                frame, text="-", anchor=tk.W,
                bg="#16213e", fg="white", font=("Arial", 9)
            )
            self.details_labels[field].pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Import/Export
        io_frame = tk.Frame(self, bg="#1a1a2e")
        io_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(io_frame, text="💾 Speichern", command=self._save_bosses,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(io_frame, text="📂 Laden", command=self._load_bosses,
                 bg="#0f3460", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
    
    def refresh(self):
        """Aktualisiert die Boss-Liste."""
        self.boss_listbox.delete(0, tk.END)
        
        for boss in self.boss_manager.boss_definitions.values():
            icon = "🐉" if boss.max_health >= 500 else "👹"
            defeated = " ☠️" if boss.is_defeated else ""
            self.boss_listbox.insert(tk.END, f"{icon} {boss.name} ({boss.max_health} HP){defeated}")
        
        self._update_details()
    
    def _on_select(self, event):
        """Handler für Listbox-Auswahl."""
        selection = self.boss_listbox.curselection()
        if selection:
            idx = selection[0]
            boss_list = list(self.boss_manager.boss_definitions.values())
            if idx < len(boss_list):
                self.selected_boss_id = boss_list[idx].id
                self._update_details()
    
    def _update_details(self):
        """Aktualisiert die Detail-Anzeige."""
        if self.selected_boss_id:
            boss = self.boss_manager.get_boss(self.selected_boss_id)
            if boss:
                self.details_labels["name"].config(text=boss.name)
                self.details_labels["health"].config(text=f"{boss.current_health}/{boss.max_health}")
                
                if boss.image_path:
                    # Nur Dateiname anzeigen
                    img_name = os.path.basename(boss.image_path)
                    self.details_labels["image"].config(text=img_name)
                else:
                    self.details_labels["image"].config(text="(kein Bild)")
                
                desc = boss.description[:50] + "..." if len(boss.description) > 50 else boss.description
                self.details_labels["description"].config(text=desc or "(keine)")
                return
        
        # Keine Auswahl
        for label in self.details_labels.values():
            label.config(text="-")
    
    def _add_boss(self):
        """Fügt einen neuen Boss hinzu."""
        dialog = BossEditorDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
            self.boss_manager.add_boss(dialog.result)
            self.refresh()
            if self.on_change:
                self.on_change()
    
    def _edit_boss(self):
        """Bearbeitet den ausgewählten Boss."""
        if not self.selected_boss_id:
            messagebox.showinfo("Hinweis", "Bitte einen Boss auswählen.")
            return
        
        boss = self.boss_manager.get_boss(self.selected_boss_id)
        if boss:
            dialog = BossEditorDialog(self, boss)
            self.wait_window(dialog)
            
            if dialog.result:
                # Boss-Manager aktualisieren
                self.boss_manager.boss_definitions[dialog.result.id] = dialog.result
                self.refresh()
                if self.on_change:
                    self.on_change()
    
    def _delete_boss(self):
        """Löscht den ausgewählten Boss."""
        if not self.selected_boss_id:
            messagebox.showinfo("Hinweis", "Bitte einen Boss auswählen.")
            return
        
        boss = self.boss_manager.get_boss(self.selected_boss_id)
        if boss:
            if messagebox.askyesno("Boss löschen?", 
                                   f"Boss '{boss.name}' wirklich löschen?"):
                self.boss_manager.remove_boss(self.selected_boss_id)
                self.selected_boss_id = None
                self.refresh()
                if self.on_change:
                    self.on_change()
    
    def _save_bosses(self):
        """Speichert alle Bosse in eine Datei."""
        path = filedialog.asksaveasfilename(
            title="Bosse speichern",
            filetypes=[("Boss-Daten", "*.bosses.json"), ("JSON", "*.json")],
            defaultextension=".bosses.json"
        )
        if path:
            try:
                self.boss_manager.save(path)
                messagebox.showinfo("Gespeichert", f"Bosse gespeichert in:\n{path}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
    
    def _load_bosses(self):
        """Lädt Bosse aus einer Datei."""
        path = filedialog.askopenfilename(
            title="Bosse laden",
            filetypes=[("Boss-Daten", "*.bosses.json"), ("JSON", "*.json"), ("Alle", "*.*")]
        )
        if path:
            try:
                self.boss_manager = BossManager.load(path)
                self.selected_boss_id = None
                self.refresh()
                messagebox.showinfo("Geladen", f"{len(self.boss_manager.boss_definitions)} Bosse geladen.")
                if self.on_change:
                    self.on_change()
            except Exception as e:
                messagebox.showerror("Fehler", f"Laden fehlgeschlagen:\n{e}")
    
    def get_boss_manager(self) -> BossManager:
        """Gibt den aktuellen BossManager zurück."""
        return self.boss_manager
    
    def set_boss_manager(self, manager: BossManager):
        """Setzt einen neuen BossManager."""
        self.boss_manager = manager
        self.selected_boss_id = None
        self.refresh()
    
    def to_dict(self) -> dict:
        """Exportiert die Boss-Daten als Dictionary."""
        return self.boss_manager.to_dict()
    
    def from_dict(self, data: dict):
        """Lädt Boss-Daten aus einem Dictionary."""
        self.boss_manager = BossManager.from_dict(data)
        self.selected_boss_id = None
        self.refresh()


# Standalone-Test
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Boss Panel Test")
    root.geometry("400x600")
    root.configure(bg="#1a1a2e")
    
    panel = BossPanel(root)
    panel.pack(fill=tk.BOTH, expand=True)
    
    # Test-Bosse hinzufügen
    panel.boss_manager.add_boss(BossDefinition(name="Saurons Schatten", max_health=500))
    panel.boss_manager.add_boss(BossDefinition(name="Balrog von Moria", max_health=800))
    panel.boss_manager.add_boss(BossDefinition(name="Nazgûl-König", max_health=300))
    panel.refresh()
    
    root.mainloop()
