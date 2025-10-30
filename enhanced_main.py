"""
Der Eine Ring PRO - Erweiterte Hauptanwendung
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class DerEineRingProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Der Eine Ring PRO")
        self.geometry("1600x900")
        self.configure(bg="#1a1a1a")
        
        ttk.Label(self, text="🗺️ Der Eine Ring", font=("Arial", 24, "bold")).pack(pady=30)
        
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)
        ttk.Button(btn_frame, text="🎨 Editor", command=self.start_editor).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="📁 Laden", command=self.load_map).pack(side=tk.LEFT, padx=10)
    
    def start_editor(self):
        try:
            from main import MapEditor
            editor_win = tk.Toplevel(self)
            editor_win.title("Editor")
            editor_win.geometry("1400x900")
            MapEditor(editor_win).pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            messagebox.showerror("Fehler", str(e))
    
    def load_map(self):
        filedialog.askopenfilename(filetypes=[("JSON", "*.json")])

if __name__ == "__main__":
    DerEineRingProApp().mainloop()