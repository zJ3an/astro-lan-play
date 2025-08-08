import customtkinter as ctk
import os
import sys
import json
import webbrowser
from plugins import server_manager
from plugins.server_manager import server_display
from plugins.settings_manager.settings_window import SettingsWindow  # Importación externa

def resource_path(relative_path):
    """Devuelve la ruta absoluta del recurso, adaptada para PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

SETTINGS_FILE = resource_path("settings.json")
ICON_PATH = resource_path(os.path.join("assets", "icon.ico"))

def ensure_settings_file():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"show_logs": False}, f, indent=4)

class AstroLanPlayApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Astro Lan-Play v1.1.0 | GitHub - @zj3an")
        self.geometry("800x500")

        # Carga segura del icono
        try:
            self.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"[WARN] No se pudo cargar el icono: {e}")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        top_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_container.pack(fill="x", pady=(1))

        self.settings_button = ctk.CTkButton(
            top_container,
            text="Ajustes",
            fg_color="#6c757d",
            hover_color=None,
            text_color="white",
            width=120,
            command=self.open_settings
        )
        self.settings_button.pack(side="left", padx=(0, 10))

        self.add_button = ctk.CTkButton(
            top_container,
            text="Agregar Servidor",
            fg_color="#28a745",
            hover_color=None,
            text_color="white",
            width=150,
            command=self.open_add_server
        )
        self.add_button.pack(side="right", padx=(0, 10))

        self.update_button = ctk.CTkButton(
            top_container,
            text="Actualizar",
            fg_color="#007bff",
            hover_color=None,
            text_color="white",
            width=120,
            command=self._on_update_clicked
        )
        self.update_button.pack(side="right", padx=(0, 10))

        self.github_button = ctk.CTkButton(
            top_container,
            text="GitHub",
            fg_color="#24292e",
            hover_color="#444c56",
            text_color="white",
            width=100,
            command=self.open_github
        )
        self.github_button.pack(side="right", padx=(0, 10))

        self.server_list_display = server_display.ServerListDisplay(self.main_frame)
        self.server_list_display.pack(fill="both", expand=True)

        # Contenedor para los botones inferiores
        self.bottom_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.bottom_container.pack(side="bottom", fill="x", pady=10)

        # Botón de GitHub (esquina izquierda)
        self.donate_button = ctk.CTkButton(
            self.bottom_container,
            text="Cómprame un Café",
            fg_color="#FFDD44",
            hover_color="#E6C73A",
            text_color="#333333",
            width=150,
            command=self.open_donate
        )
        self.donate_button.pack(side="left")

        # Botón de "Conectado" (centrado, inicialmente oculto)
        self.connected_button = ctk.CTkButton(
            self.bottom_container,
            text="Conectado",
            fg_color="#28a745",
            hover_color="#1e7e34",
            text_color="#FFFFFF",
            width=150,
            font=ctk.CTkFont(size=12, weight="bold"),
            state="normal"
        )
        # Inicialmente no se empaqueta (oculto)

        # Configurar callback para actualizar estado de conexión
        self.server_list_display.set_connection_callback(self.update_connection_status)

        self.settings_window = None
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_add_server(self):
        self.after(200, lambda: server_manager.open_add_server_popup(self, on_server_added=self.server_list_display.load_servers))

    def _on_update_clicked(self):
        self.server_list_display.load_servers()
        self.server_list_display.update_server_data()

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.after(200, lambda: self._create_settings_window())
        else:
            self.settings_window.lift()
            self.settings_window.focus()

    def _create_settings_window(self):
        self.settings_window = SettingsWindow(self)

    def open_github(self):
        url = "https://github.com/zj3an/astro-lan-play"
        webbrowser.open(url)

    def open_donate(self):
        url = "https://zj3an.vercel.app/donate.html"
        webbrowser.open(url)

    def update_connection_status(self, connected, server_name=None):
        """Actualiza la UI según el estado de conexión"""
        if connected and server_name:
            # Mostrar botón de "Conectado" centrado
            self.connected_button.configure(text="Conectado")
            self.connected_button.pack(anchor="center", pady=5)  # Centrado perfecto
        else:
            # Ocultar botón de "Conectado"
            self.connected_button.pack_forget()

    def on_closing(self):
        # Notificar desconexión al cerrar
        if self.server_list_display.connected_server_address:
            self.update_connection_status(False)
            
        if self.server_list_display.lan_play_process and self.server_list_display.lan_play_process.poll() is None:
            try:
                self.server_list_display.lan_play_process.terminate()
                self.server_list_display.lan_play_process.wait(timeout=5)
            except Exception:
                self.server_list_display.lan_play_process.kill()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    server_manager.ensure_servers_file()
    ensure_settings_file()

    app = AstroLanPlayApp()
    app.mainloop()
