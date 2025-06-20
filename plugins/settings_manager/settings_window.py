# plugins/settings_manager/settings_window.py

import customtkinter as ctk
import os
import sys
import json

def resource_path(relative_path):
    """Devuelve la ruta absoluta desde el ejecutable (ya sea .py o .exe)."""
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), relative_path)

SETTINGS_FILE = resource_path("settings.json")
ICON_PATH = resource_path(os.path.join("assets", "icon.ico"))

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Ajustes")
        self.geometry("300x150")
        self.resizable(False, False)

        self.after(200, self.set_icon)

        self.transient(parent)
        self.grab_set()
        self.focus()
        self.lift()

        self.update_idletasks()
        self.center_on_parent(parent)

        self.settings = self.load_settings()

        self.checkbox_logs = ctk.CTkCheckBox(
            self,
            text="Mostrar Logs al Conectar",
            text_color="white",
            command=self.save_settings
        )
        self.checkbox_logs.pack(pady=20, padx=20, anchor="w")

        if self.settings.get("show_logs", False):
            self.checkbox_logs.select()
        else:
            self.checkbox_logs.deselect()

    def set_icon(self):
        try:
            if os.path.exists(ICON_PATH):
                self.iconbitmap(ICON_PATH)
        except Exception:
            pass

    def center_on_parent(self, parent):
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        window_width = 300
        window_height = 150

        pos_x = parent_x + (parent_width // 2) - (window_width // 2)
        pos_y = parent_y + (parent_height // 2) - (window_height // 2)
        self.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_settings(self):
        self.settings["show_logs"] = bool(self.checkbox_logs.get())
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)
