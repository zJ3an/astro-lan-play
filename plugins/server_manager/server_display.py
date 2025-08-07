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
import re

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
        self.connection_callback = None

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

    def set_connection_callback(self, callback):
        """Establece el callback para notificar cambios de estado de conexión"""
        self.connection_callback = callback

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

        # Verificar que el ejecutable existe
        if not os.path.exists(LAN_PLAY_EXECUTABLE):
            messagebox.showerror("Error", f"No se encontró lan-play.exe en:\n{LAN_PLAY_EXECUTABLE}")
            return

        try:
            show_logs = self.get_show_logs_setting()
            
            # Configuración para ocultar la consola en Windows
            startupinfo = None
            creation_flags = 0
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            if show_logs:
                self.open_log_window()
                self.lan_play_process = subprocess.Popen(
                    [LAN_PLAY_EXECUTABLE, "--relay-server-addr", server["address"]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                    startupinfo=startupinfo,
                    creationflags=creation_flags
                )
                threading.Thread(target=self._read_log_output, daemon=True).start()
            else:
                self.lan_play_process = subprocess.Popen(
                    [LAN_PLAY_EXECUTABLE, "--relay-server-addr", server["address"]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    creationflags=creation_flags
                )

            self.connected_server_address = server["address"]
            
            # Notificar al callback que se conectó
            if self.connection_callback:
                self.connection_callback(True, server["name"])
            
        except FileNotFoundError:
            messagebox.showerror("Error", f"No se encontró el archivo lan-play.exe")
            self.lan_play_process = None
            self.connected_server_address = None
            if self.connection_callback:
                self.connection_callback(False)
        except PermissionError:
            messagebox.showerror("Error", "No tienes permisos para ejecutar lan-play.exe")
            self.lan_play_process = None
            self.connected_server_address = None
            if self.connection_callback:
                self.connection_callback(False)
        except subprocess.SubprocessError as e:
            messagebox.showerror("Error", f"Error al iniciar el proceso:\n{str(e)}")
            self.lan_play_process = None
            self.connected_server_address = None
            if self.connection_callback:
                self.connection_callback(False)
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado:\n{str(e)}")
            self.lan_play_process = None
            self.connected_server_address = None
            if self.connection_callback:
                self.connection_callback(False)

        self.refresh_servers()

    def disconnect_server(self, server):
        if self.connected_server_address == server["address"]:
            self.disconnect_existing_connection()
            self.connected_server_address = None
            
            # Notificar al callback que se desconectó
            if self.connection_callback:
                self.connection_callback(False)
                
            self.refresh_servers()

    def disconnect_existing_connection(self):
        """Desconecta la conexión existente de forma segura"""
        if self.lan_play_process and self.lan_play_process.poll() is None:
            try:
                # Intentar terminación suave primero
                self.lan_play_process.terminate()
                # Esperar hasta 5 segundos para terminación suave
                try:
                    self.lan_play_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Si no termina suavemente, forzar terminación
                    self.lan_play_process.kill()
                    self.lan_play_process.wait()  # Esperar a que termine
            except Exception as e:
                print(f"Error al terminar proceso: {e}")
                # Como último recurso, intentar kill
                try:
                    self.lan_play_process.kill()
                except:
                    pass
        
        self.lan_play_process = None

        # Cerrar ventana de logs si existe
        if self.log_window and self.log_window.winfo_exists():
            try:
                self.log_window.destroy()
            except:
                pass
        self.log_window = None

    def _read_log_output(self):
        """Lee la salida del proceso lan-play de forma segura"""
        try:
            if not self.lan_play_process or not self.lan_play_process.stdout:
                return
                
            for line in iter(self.lan_play_process.stdout.readline, ''):
                if not line:  # EOF
                    break
                    
                # Verificar que la ventana de logs aún existe
                if not (self.log_window and self.log_window.winfo_exists()):
                    break
                    
                # Actualizar UI desde el thread principal
                def update_log():
                    try:
                        if self.log_window and self.log_window.winfo_exists() and hasattr(self, 'log_textbox'):
                            self.log_textbox.insert("end", line)
                            self.log_textbox.see("end")
                    except Exception:
                        pass
                
                if self.log_window and self.log_window.winfo_exists():
                    self.log_window.after(0, update_log)
                    
        except Exception as e:
            print(f"Error leyendo logs: {e}")
        finally:
            # Cerrar el stdout si está abierto
            try:
                if self.lan_play_process and self.lan_play_process.stdout:
                    self.lan_play_process.stdout.close()
            except:
                pass

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
        """Actualiza la información de un servidor de forma segura"""
        try:
            # Validar y parsear dirección
            if ":" not in address:
                self._set_server_status_offline(status_dot, label_before_online, label_online, label_version, label_ping)
                return
                
            host, port_str = address.split(":", 1)
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError("Puerto fuera de rango")
            except ValueError:
                self._set_server_status_offline(status_dot, label_before_online, label_online, label_version, label_ping)
                return
        except Exception:
            self._set_server_status_offline(status_dot, label_before_online, label_online, label_version, label_ping)
            return

        # Hacer ping con timeout más corto para mejor experiencia
        ping_ms = self.ping_server(host, port, timeout=2)
        if ping_ms is None:
            self._set_server_status_offline(status_dot, label_before_online, label_online, label_version, label_ping)
            return

        # Intentar obtener información del servidor
        online = "?"
        version = "?"
        color = "orange"  # Por defecto, si no se puede obtener info HTTP
        
        try:
            url = f"http://{address}/info"
            resp = requests.get(url, timeout=2)  # Timeout más corto
            resp.raise_for_status()
            data = resp.json()
            online = data.get("online", 0)
            version = data.get("version", "-")
            color = "green"  # Verde si se obtuvo info completa
        except requests.exceptions.Timeout:
            # El servidor responde a ping pero HTTP timeout
            color = "orange"
        except requests.exceptions.ConnectionError:
            # Puerto abierto pero no es servidor HTTP
            color = "orange" 
        except requests.exceptions.RequestException:
            # Otros errores de request
            color = "orange"
        except (json.JSONDecodeError, KeyError):
            # Respuesta HTTP pero JSON inválido
            color = "orange"
        except Exception:
            # Cualquier otro error
            color = "orange"

        def safe_update():
            try:
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
            except Exception:
                # Si hay error actualizando UI, ignorar
                pass

        # Usar after para actualizar UI desde thread principal
        if label_before_online.winfo_exists():
            label_before_online.after(0, safe_update)

    def _set_server_status_offline(self, status_dot, label_before_online, label_online, label_version, label_ping):
        """Establece el estado del servidor como offline de forma segura"""
        def safe_update_off():
            try:
                if status_dot.winfo_exists():
                    status_dot.configure(fg_color="red")
                if label_before_online.winfo_exists():
                    label_before_online.configure(text="Apagado | - | - | -")
                for label in (label_online, label_version, label_ping):
                    if label.winfo_exists():
                        label.configure(text="", image=None)
            except Exception:
                # Si hay error actualizando UI, ignorar
                pass

        # Usar after para actualizar UI desde thread principal
        if label_before_online.winfo_exists():
            label_before_online.after(0, safe_update_off)

    def ping_server(self, host, port, timeout=3):
        """Hace ping a un servidor con timeout configurado"""
        try:
            start = time.time()
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            end = time.time()
            ping_ms = int((end - start) * 1000)
            return max(1, ping_ms)  # Mínimo 1ms para evitar 0ms
        except socket.timeout:
            return None
        except (socket.error, OSError, ConnectionRefusedError):
            return None
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
