import customtkinter as ctk
import requests
import threading
import time
import socket
import json
import os
import sys
import tkinter.messagebox as messagebox
from PIL import Image
from . import server_storage
import subprocess
import signal

# Base path donde se ejecuta el .exe o .py
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
SERVERS_FILE = os.path.join(BASE_DIR, "servers.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
LAN_PLAY_EXECUTABLE = os.path.join(BASE_DIR, "lan-play.exe")

def abs_path(relative):
    return os.path.join(BASE_DIR, relative)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ServerListDisplay(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.servers = []
        self.server_widgets = []
        self.connected_server_address = None
        self.lan_play_process = None
        self.log_window = None

        try:
            img_person = Image.open(resource_path("assets/person.png")).convert("RGBA").resize((16, 16), Image.Resampling.LANCZOS)
            self.person_photo = ctk.CTkImage(light_image=img_person, dark_image=img_person)
        except Exception:
            self.person_photo = None

        try:
            img_server = Image.open(resource_path("assets/server.png")).convert("RGBA").resize((16, 16), Image.Resampling.LANCZOS)
            self.server_photo = ctk.CTkImage(light_image=img_server, dark_image=img_server)
        except Exception:
            self.server_photo = None

        try:
            img_ping = Image.open(resource_path("assets/ping.png")).convert("RGBA").resize((16, 16), Image.Resampling.LANCZOS)
            self.ping_photo = ctk.CTkImage(light_image=img_ping, dark_image=img_ping)
        except Exception:
            self.ping_photo = None

        self.list_container = ctk.CTkScrollableFrame(self)
        self.list_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.load_servers()
        self.refresh_servers()
        self.start_periodic_update()

    def load_servers(self):
        server_storage.ensure_servers_file()
        if os.path.exists(SERVERS_FILE):
            with open(SERVERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.servers = data.get("servers", [])
        else:
            self.servers = []
        self.refresh_servers()

    def refresh_servers(self):
        for w in self.server_widgets:
            w[0].destroy()
        self.server_widgets.clear()

        for server in self.servers:
            frame = ctk.CTkFrame(self.list_container)
            frame.pack(fill="x", pady=5, padx=5)

            info_container = ctk.CTkFrame(frame, fg_color="transparent")
            info_container.pack(side="left", fill="x", expand=True, padx=(5, 0), pady=5)

            name_addr = ctk.CTkLabel(info_container, text=f"{server['name']} | {server['address']}", font=ctk.CTkFont(size=12, weight="bold"))
            name_addr.pack(anchor="w")

            status_frame = ctk.CTkFrame(info_container, fg_color="transparent")
            status_frame.pack(anchor="w", padx=(0, 10), pady=(2, 5), fill="x")

            status_dot = ctk.CTkLabel(status_frame, text="", width=5, height=5, corner_radius=10, fg_color="gray")
            status_dot.pack(side="left", padx=(0, 8))

            label_before_online = ctk.CTkLabel(status_frame, text="Cargando estado...", font=ctk.CTkFont(size=11))
            label_before_online.pack(side="left")

            label_online = ctk.CTkLabel(status_frame, text="", font=ctk.CTkFont(size=11))
            label_online.pack(side="left", padx=5)

            label_version = ctk.CTkLabel(status_frame, text="", font=ctk.CTkFont(size=11))
            label_version.pack(side="left", padx=5)

            label_ping = ctk.CTkLabel(status_frame, text="", font=ctk.CTkFont(size=11))
            label_ping.pack(side="left", padx=5)

            btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
            btn_frame.pack(side="right", padx=5, pady=5)

            if self.connected_server_address == server["address"]:
                action_btn = ctk.CTkButton(
                    btn_frame,
                    text="Desconectar",
                    fg_color="#dc3545",
                    text_color="white",
                    width=100,
                    corner_radius=5,
                    command=lambda s=server: self.disconnect_server(s)
                )
                action_btn.pack(fill="x", pady=(0, 5))
            else:
                disabled = self.connected_server_address is not None
                action_btn = ctk.CTkButton(
                    btn_frame,
                    text="Conectar",
                    fg_color="#28a745",
                    text_color="white",
                    width=100,
                    corner_radius=5,
                    state="disabled" if disabled else "normal",
                    command=lambda s=server: self.connect_server(s)
                )
                action_btn.pack(fill="x", pady=(0, 5))

            delete_btn = ctk.CTkButton(
                btn_frame,
                text="Eliminar",
                fg_color="#dc3545",
                text_color="white",
                width=100,
                corner_radius=5,
                command=lambda s=server: self._confirm_delete(s)
            )
            delete_btn.pack(fill="x")

            self.server_widgets.append((frame, status_dot, label_before_online, label_online, label_version, label_ping, action_btn))

            threading.Thread(
                target=self.update_server_info,
                args=(server['address'], status_dot, label_before_online, label_online, label_version, label_ping),
                daemon=True
            ).start()

    def connect_server(self, server):
        self.disconnect_existing_connection()

        try:
            show_logs = self.get_show_logs_setting()
            if show_logs:
                self.open_log_window()
                self.lan_play_process = subprocess.Popen(
                    [LAN_PLAY_EXECUTABLE, "--relay-server-addr", server["address"]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True
                )
                threading.Thread(target=self._read_log_output, daemon=True).start()
            else:
                self.lan_play_process = subprocess.Popen(
                    [LAN_PLAY_EXECUTABLE, "--relay-server-addr", server["address"]]
                )

            self.connected_server_address = server["address"]
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar lan-play.exe:\n{e}")
            self.lan_play_process = None
            self.connected_server_address = None

        self.refresh_servers()

    def disconnect_server(self, server):
        if self.connected_server_address == server["address"]:
            self.disconnect_existing_connection()
            self.connected_server_address = None
            self.refresh_servers()

    def disconnect_existing_connection(self):
        if self.lan_play_process and self.lan_play_process.poll() is None:
            try:
                self.lan_play_process.terminate()
                self.lan_play_process.wait(timeout=5)
            except Exception:
                self.lan_play_process.kill()
        self.lan_play_process = None

        if self.log_window and self.log_window.winfo_exists():
            self.log_window.destroy()
        self.log_window = None

    def _read_log_output(self):
        for line in self.lan_play_process.stdout:
            if self.log_window and self.log_window.winfo_exists():
                self.log_textbox.insert("end", line)
                self.log_textbox.see("end")

    def open_log_window(self):
        self.log_window = ctk.CTkToplevel(self)
        self.log_window.title("Logs de conexión")
        self.log_window.geometry("600x400")

        self.log_textbox = ctk.CTkTextbox(self.log_window, wrap="none")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

    def get_show_logs_setting(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("show_logs", False)
            except Exception:
                return False
        return False

    def _confirm_delete(self, server):
        name = server.get("name", server.get("address", ""))
        if messagebox.askyesno("Confirmar eliminación", f"¿Quieres eliminar el servidor '{name}'?"):
            try:
                server_storage.delete_server(server["address"])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo eliminar el servidor: {e}")
                return
            self.load_servers()

    def update_server_info(self, address, status_dot, label_before_online, label_online, label_version, label_ping):
        try:
            host, port_str = address.split(":")
            port = int(port_str)
        except Exception:
            self._set_server_status_offline(status_dot, label_before_online, label_online, label_version, label_ping)
            return

        ping_ms = self.ping_server(host, port)
        if ping_ms is None:
            self._set_server_status_offline(status_dot, label_before_online, label_online, label_version, label_ping)
            return

        try:
            url = f"http://{address}/info"
            resp = requests.get(url, timeout=3)
            resp.raise_for_status()
            data = resp.json()
            online = data.get("online", 0)
            version = data.get("version", "-")
            color = "green"
        except Exception:
            online = "?"
            version = "?"
            color = "orange"

        def safe_update():
            if status_dot.winfo_exists():
                status_dot.configure(fg_color=color)
            if label_before_online.winfo_exists():
                label_before_online.configure(text="Activo |")
            if label_online.winfo_exists():
                label_online.configure(image=self.person_photo, text=f" {online} |", compound="left")
            if label_version.winfo_exists():
                label_version.configure(image=self.server_photo, text=f" {version} |", compound="left")
            if label_ping.winfo_exists():
                label_ping.configure(image=self.ping_photo, text=f" {ping_ms}ms", compound="left")

        label_before_online.after(0, safe_update)

    def _set_server_status_offline(self, status_dot, label_before_online, label_online, label_version, label_ping):
        def safe_update_off():
            if status_dot.winfo_exists():
                status_dot.configure(fg_color="red")
            if label_before_online.winfo_exists():
                label_before_online.configure(text="Apagado | - | - | -")
            for label in (label_online, label_version, label_ping):
                if label.winfo_exists():
                    label.configure(text="", image=None)

        label_before_online.after(0, safe_update_off)

    def ping_server(self, host, port, timeout=2):
        try:
            start = time.time()
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            end = time.time()
            return int((end - start) * 1000)
        except Exception:
            return None

    def start_periodic_update(self):
        def loop():
            self.update_server_data()
            self.after(10000, loop)
        self.after(10000, loop)

    def update_server_data(self):
        for server, widgets in zip(self.servers, self.server_widgets):
            frame, status_dot, label_before_online, label_online, label_version, label_ping, _ = widgets
            if frame.winfo_exists():
                threading.Thread(
                    target=self.update_server_info,
                    args=(server['address'], status_dot, label_before_online, label_online, label_version, label_ping),
                    daemon=True
                ).start()
