# plugins/server_manager/server_storage.py

import json
import os
import sys

def resource_path(relative_path):
    """Devuelve la ruta absoluta desde el directorio donde se ejecuta el programa."""
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), relative_path)

SERVERS_FILE = resource_path("servers.json")

def ensure_servers_file():
    if not os.path.exists(SERVERS_FILE):
        with open(SERVERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"servers": []}, f, indent=4)

def get_servers():
    ensure_servers_file()
    with open(SERVERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("servers", [])

def save_server(name, address):
    servers = get_servers()
    servers.append({"name": name, "address": address})
    with open(SERVERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"servers": servers}, f, indent=4, ensure_ascii=False)

def delete_server(address):
    servers = get_servers()
    servers = [s for s in servers if s["address"] != address]
    with open(SERVERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"servers": servers}, f, indent=4, ensure_ascii=False)
