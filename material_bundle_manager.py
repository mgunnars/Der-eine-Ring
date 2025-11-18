"""
Material Bundle Manager
Verwaltet Material-Bundles für bessere Performance im Editor

Bundles gruppieren zusammengehörige Materialien (z.B. Taverne, Dungeon, Wald)
um zu vermeiden, dass alle 1000+ Tiles gleichzeitig geladen werden.
"""

import os
import json
from pathlib import Path


class MaterialBundleManager:
    """Verwaltet Material-Bundles"""
    
    def __init__(self, bundles_folder="material_bundles"):
        self.bundles_folder = bundles_folder
        self.bundles = {}  # {bundle_name: bundle_data}
        self.active_bundles = set()  # Aktuell geladene Bundles
        self.base_bundle = "base"  # Immer geladen
        
        os.makedirs(bundles_folder, exist_ok=True)
        
        # Standard-Bundle erstellen falls nicht vorhanden
        self._ensure_base_bundle()
        
        # Alle Bundles laden
        self.load_all_bundles()
    
    def _ensure_base_bundle(self):
        """Erstellt Standard-Bundle mit Basis-Materialien"""
        base_bundle_path = os.path.join(self.bundles_folder, "base.json")
        
        if not os.path.exists(base_bundle_path):
            base_materials = [
                "empty", "grass", "dirt", "stone", "water", "deep_water",
                "sand", "snow", "ice", "lava", "forest", "mountain",
                "hills", "swamp", "desert", "tundra", "river",
                "road", "path", "bridge", "wall", "door"
            ]
            
            bundle_data = {
                "name": "Basis-Materialien",
                "description": "Standard-Terrain für alle Karten",
                "always_loaded": True,
                "materials": base_materials,
                "icon": "🗺️",
                "order": 0
            }
            
            self.save_bundle("base", bundle_data)
    
    def create_bundle_from_materials(self, bundle_id, name, materials, 
                                    description="", icon="📦", always_loaded=False):
        """
        Erstellt neues Bundle aus Material-Liste
        
        Args:
            bundle_id: Eindeutige ID (z.B. "tavern_bundle")
            name: Anzeige-Name (z.B. "Taverne")
            materials: Liste von Material-Namen
            description: Beschreibung
            icon: Emoji-Icon
            always_loaded: Immer laden (für wichtige Bundles)
        """
        bundle_data = {
            "name": name,
            "description": description,
            "materials": list(materials),
            "icon": icon,
            "always_loaded": always_loaded,
            "order": len(self.bundles) + 1
        }
        
        self.save_bundle(bundle_id, bundle_data)
        self.bundles[bundle_id] = bundle_data
        
        return bundle_id
    
    def create_bundle_from_imported_map(self, map_data, bundle_name=None):
        """
        Erstellt Bundle aus importierter Map
        Analysiert alle verwendeten Custom-Materials
        
        Args:
            map_data: Map-Daten mit custom_materials
            bundle_name: Optionaler Name (sonst aus map_name)
        
        Returns:
            bundle_id oder None
        """
        if "custom_materials" not in map_data:
            print("⚠️ Keine Custom-Materials in Map gefunden")
            return None
        
        custom_materials = map_data["custom_materials"]
        
        if not custom_materials:
            return None
        
        # Bundle-Namen generieren
        if bundle_name is None:
            map_name = map_data.get("name", "imported_map")
            bundle_name = f"{map_name}_bundle"
        
        # Bundle-ID (lowercase, no spaces)
        bundle_id = bundle_name.lower().replace(" ", "_")
        
        # Material-Namen aus custom_materials extrahieren
        material_names = list(custom_materials.keys())
        
        # Bundle erstellen
        display_name = map_data.get("name", bundle_name)
        description = f"Materialien aus {display_name} ({len(material_names)} Tiles)"
        
        self.create_bundle_from_materials(
            bundle_id=bundle_id,
            name=display_name,
            materials=material_names,
            description=description,
            icon="🏘️",
            always_loaded=False
        )
        
        print(f"✅ Bundle erstellt: '{display_name}' ({len(material_names)} Materialien)")
        
        return bundle_id
    
    def save_bundle(self, bundle_id, bundle_data):
        """Speichert Bundle als JSON"""
        filepath = os.path.join(self.bundles_folder, f"{bundle_id}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(bundle_data, f, indent=2, ensure_ascii=False)
    
    def load_bundle(self, bundle_id):
        """Lädt Bundle aus JSON"""
        filepath = os.path.join(self.bundles_folder, f"{bundle_id}.json")
        
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                bundle_data = json.load(f)
                self.bundles[bundle_id] = bundle_data
                return bundle_data
        except Exception as e:
            print(f"⚠️ Fehler beim Laden von Bundle {bundle_id}: {e}")
            return None
    
    def load_all_bundles(self):
        """Lädt alle verfügbaren Bundles"""
        if not os.path.exists(self.bundles_folder):
            return
        
        for filename in os.listdir(self.bundles_folder):
            if filename.endswith('.json'):
                bundle_id = filename[:-5]  # Ohne .json
                self.load_bundle(bundle_id)
        
        # Aktiviere Base-Bundle + always_loaded Bundles
        self.active_bundles.clear()
        self.active_bundles.add(self.base_bundle)
        
        # Aktiviere alle always_loaded Bundles
        for bundle_id, bundle_data in self.bundles.items():
            if bundle_data.get("always_loaded", False):
                self.active_bundles.add(bundle_id)
                print(f"   ✅ Always-loaded: {bundle_id}")
        
        print(f"📦 {len(self.bundles)} Bundles geladen")
    
    def activate_bundle(self, bundle_id):
        """Aktiviert Bundle (lädt Materialien)"""
        if bundle_id in self.bundles:
            self.active_bundles.add(bundle_id)
            return True
        return False
    
    def deactivate_bundle(self, bundle_id):
        """Deaktiviert Bundle (entlädt Materialien)"""
        # Base-Bundle kann nicht deaktiviert werden
        if bundle_id == self.base_bundle:
            return False
        
        # Always-loaded Bundles können nicht deaktiviert werden
        if bundle_id in self.bundles and self.bundles[bundle_id].get("always_loaded", False):
            return False
        
        if bundle_id in self.active_bundles:
            self.active_bundles.remove(bundle_id)
            return True
        return False
    
    def toggle_bundle(self, bundle_id):
        """Bundle aktivieren/deaktivieren"""
        if bundle_id in self.active_bundles:
            success = self.deactivate_bundle(bundle_id)
            return not success  # Return True wenn jetzt aktiv
        else:
            return self.activate_bundle(bundle_id)
    
    def get_active_materials(self):
        """
        Gibt alle Materialien aus aktiven Bundles zurück
        
        Returns:
            Set von Material-Namen
        """
        materials = set()
        
        for bundle_id in self.active_bundles:
            if bundle_id in self.bundles:
                bundle_materials = self.bundles[bundle_id].get("materials", [])
                materials.update(bundle_materials)
        
        return materials
    
    def get_bundle_list(self):
        """
        Gibt Liste aller Bundles zurück (sortiert nach order)
        
        Returns:
            Liste von (bundle_id, bundle_data) tuples
        """
        items = list(self.bundles.items())
        items.sort(key=lambda x: x[1].get("order", 999))
        return items
    
    def get_bundle_info(self, bundle_id):
        """Gibt Bundle-Informationen zurück"""
        return self.bundles.get(bundle_id)
    
    def is_bundle_active(self, bundle_id):
        """Prüft ob Bundle aktiv ist"""
        return bundle_id in self.active_bundles
    
    def delete_bundle(self, bundle_id):
        """Löscht Bundle (außer base)"""
        if bundle_id == self.base_bundle:
            return False
        
        # Aus aktiven entfernen
        self.active_bundles.discard(bundle_id)
        
        # Aus Dictionary entfernen
        if bundle_id in self.bundles:
            del self.bundles[bundle_id]
        
        # Datei löschen
        filepath = os.path.join(self.bundles_folder, f"{bundle_id}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception as e:
                print(f"⚠️ Fehler beim Löschen: {e}")
                return False
        
        return True
    
    def get_material_bundle(self, material_name):
        """
        Findet Bundle für bestimmtes Material
        
        Returns:
            bundle_id oder None
        """
        for bundle_id, bundle_data in self.bundles.items():
            if material_name in bundle_data.get("materials", []):
                return bundle_id
        return None
    
    def auto_activate_for_materials(self, material_names):
        """
        Aktiviert automatisch Bundles die bestimmte Materialien enthalten
        Nützlich beim Laden einer Map
        
        Args:
            material_names: Set/Liste von Material-Namen
        """
        material_set = set(material_names)
        activated = []
        
        for bundle_id, bundle_data in self.bundles.items():
            bundle_materials = set(bundle_data.get("materials", []))
            
            # Wenn Bundle Materials enthält die in der Map sind
            if bundle_materials & material_set:
                if self.activate_bundle(bundle_id):
                    activated.append(bundle_id)
        
        if activated:
            print(f"🔄 Auto-aktiviert: {', '.join(activated)}")
        
        return activated


def create_bundle_from_png_import_dialog(manager, imported_map_path):
    """
    Interaktiver Dialog zum Bundle-Erstellen aus PNG-Import
    
    Args:
        manager: MaterialBundleManager Instanz
        imported_map_path: Pfad zur importierten Map-JSON
    """
    import tkinter as tk
    from tkinter import messagebox
    import json
    
    # Map-Daten laden
    try:
        with open(imported_map_path, 'r', encoding='utf-8') as f:
            map_data = json.load(f)
    except Exception as e:
        messagebox.showerror("Fehler", f"Kann Map nicht laden:\n{e}")
        return None
    
    if "custom_materials" not in map_data or not map_data["custom_materials"]:
        messagebox.showinfo("Info", "Diese Map hat keine Custom-Materials für ein Bundle.")
        return None
    
    # Dialog erstellen
    dialog = tk.Toplevel()
    dialog.title("Bundle aus Import erstellen")
    dialog.geometry("500x400")
    dialog.configure(bg="#1a1a1a")
    
    tk.Label(dialog, text="📦 Neues Material-Bundle erstellen",
            font=("Arial", 14, "bold"),
            bg="#1a1a1a", fg="#d4af37").pack(pady=20)
    
    # Info
    material_count = len(map_data["custom_materials"])
    tk.Label(dialog, text=f"Diese Map enthält {material_count} Custom-Materials.\n"
                         f"Erstelle ein Bundle für schnelleren Zugriff!",
            bg="#1a1a1a", fg="white").pack(pady=10)
    
    # Bundle-Name
    tk.Label(dialog, text="Bundle-Name:",
            bg="#1a1a1a", fg="white").pack(pady=(20, 5))
    
    name_var = tk.StringVar(value=map_data.get("name", "Meine Map"))
    name_entry = tk.Entry(dialog, textvariable=name_var, width=40, font=("Arial", 10))
    name_entry.pack(pady=5)
    
    # Beschreibung
    tk.Label(dialog, text="Beschreibung (optional):",
            bg="#1a1a1a", fg="white").pack(pady=(10, 5))
    
    desc_var = tk.StringVar(value=f"{material_count} Tiles aus importierter PNG-Map")
    desc_entry = tk.Entry(dialog, textvariable=desc_var, width=40, font=("Arial", 10))
    desc_entry.pack(pady=5)
    
    result = {"created": False, "bundle_id": None}
    
    def create():
        bundle_name = name_var.get().strip()
        description = desc_var.get().strip()
        
        if not bundle_name:
            messagebox.showwarning("Fehler", "Bitte Bundle-Namen eingeben!")
            return
        
        try:
            bundle_id = manager.create_bundle_from_materials(
                bundle_id=bundle_name.lower().replace(" ", "_"),
                name=bundle_name,
                materials=list(map_data["custom_materials"].keys()),
                description=description,
                icon="🏘️",
                always_loaded=False
            )
            
            result["created"] = True
            result["bundle_id"] = bundle_id
            
            messagebox.showinfo("Erfolg", 
                              f"Bundle '{bundle_name}' erstellt!\n\n"
                              f"{material_count} Materialien gruppiert.")
            dialog.destroy()
        
        except Exception as e:
            messagebox.showerror("Fehler", f"Bundle-Erstellung fehlgeschlagen:\n{e}")
    
    # Buttons
    button_frame = tk.Frame(dialog, bg="#1a1a1a")
    button_frame.pack(pady=30)
    
    tk.Button(button_frame, text="✅ Bundle erstellen",
             bg="#2a7d2a", fg="white", font=("Arial", 10, "bold"),
             padx=20, pady=5, command=create).pack(side=tk.LEFT, padx=10)
    
    tk.Button(button_frame, text="❌ Abbrechen",
             bg="#7d2a2a", fg="white", font=("Arial", 10, "bold"),
             padx=20, pady=5, command=dialog.destroy).pack(side=tk.LEFT, padx=10)
    
    dialog.wait_window()
    
    return result["bundle_id"] if result["created"] else None


if __name__ == "__main__":
    # Test
    manager = MaterialBundleManager()
    
    # Test-Bundle erstellen
    manager.create_bundle_from_materials(
        bundle_id="test_tavern",
        name="Test Taverne",
        materials=["tavern_floor", "tavern_wall", "tavern_table"],
        description="Test für Taverne",
        icon="🍺"
    )
    
    print(f"Bundles: {list(manager.bundles.keys())}")
    print(f"Aktiv: {manager.active_bundles}")
    print(f"Materials: {manager.get_active_materials()}")
