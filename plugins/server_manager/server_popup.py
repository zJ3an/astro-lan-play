import customtkinter as ctk
import os
import tkinter.messagebox as messagebox
from . import server_storage
import sys

def resource_path(relative_path):
    """Devuelve la ruta absoluta desde el directorio del ejecutable o script."""
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), relative_path)

def open_add_server_popup(master, on_server_added=None):
    popup = ctk.CTkToplevel(master)
    popup.title("Agregar Servidor")

    # Centro y demás setup
    width, height = 350, 230
    master.update_idletasks()
    x = master.winfo_x()
    y = master.winfo_y()
    master_width = master.winfo_width()
    master_height = master.winfo_height()
    pos_x = x + (master_width // 2) - (width // 2)
    pos_y = y + (master_height // 2) - (height // 2)
    popup.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    popup.grab_set()

    # Función para asignar icono con retraso
    def set_icon():
        icon_path = resource_path("assets/icon.ico")
        try:
            if os.path.exists(icon_path):
                popup.wm_iconbitmap(icon_path)
        except Exception as e:
            print(f"[ERROR] No se pudo asignar el icono al popup: {e}")

    popup.after(200, set_icon)  # 200ms después de creado el popup

    container = ctk.CTkFrame(popup)
    container.pack(expand=True, fill="both", padx=15, pady=15)

    label_name = ctk.CTkLabel(container, text="Nombre del Servidor:")
    label_name.pack(anchor="w", pady=(0, 5))
    entry_name = ctk.CTkEntry(container, placeholder_text="Ej. Mi Switch")
    entry_name.pack(fill="x", pady=(0, 10))

    label_address = ctk.CTkLabel(container, text="Servidor (host:port):")
    label_address.pack(anchor="w", pady=(0, 5))
    entry_address = ctk.CTkEntry(container, placeholder_text="ej. 192.168.0.1:11451")
    entry_address.pack(fill="x", pady=(0, 15))

    def on_save():
        name = entry_name.get().strip()
        address = entry_address.get().strip()

        if not name or not address:
            messagebox.showerror("Error", "Debes completar ambos campos.")
            return

        if ":" not in address:
            messagebox.showerror("Error", "Dirección inválida. Usa el formato host:port.")
            return

        existing = server_storage.get_servers()

        for server in existing:
            if server["name"] == name:
                messagebox.showerror("Duplicado", "Ya existe un servidor con ese nombre.")
                return
            if server["address"] == address:
                messagebox.showerror("Duplicado", "Ya existe un servidor con esa dirección.")
                return

        server_storage.save_server(name, address)
        
        if on_server_added:
            on_server_added()

        popup.destroy()

    save_btn = ctk.CTkButton(container, text="Guardar", command=on_save)
    save_btn.pack(fill="x")
