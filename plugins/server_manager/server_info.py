# plugins/server_manager/server_info.py

import socket
import time
import requests
import os
import sys

# Base path del programa (ya sea .py o .exe)
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

def ping_server(host: str, port: int, timeout=1.0) -> float | None:
    """
    Hace un ping TCP (intenta conectar y mide tiempo).
    Retorna el ping en ms o None si no responde.
    """
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=timeout):
            end = time.time()
        return (end - start) * 1000  # ms
    except Exception:
        return None

def get_server_info(host: str, port: int, timeout=2.0) -> dict | None:
    """
    Consulta la URL http://host:port/info y devuelve el JSON como dict.
    Retorna None si falla.
    """
    url = f"http://{host}:{port}/info"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def fetch_server_status(address: str) -> dict:
    """
    address en formato host:port
    Retorna dict con:
    {
        "estado": "Activo" | "Apagado",
        "jugando": int,
        "version": str,
        "ping": int (ms) | None
    }
    """
    if ":" not in address:
        return {"estado": "Apagado", "jugando": 0, "version": "N/A", "ping": None}
    host, port_str = address.split(":")
    try:
        port = int(port_str)
    except ValueError:
        return {"estado": "Apagado", "jugando": 0, "version": "N/A", "ping": None}

    ping = ping_server(host, port)
    if ping is None:
        return {"estado": "Apagado", "jugando": 0, "version": "N/A", "ping": None}

    info = get_server_info(host, port)
    if info is None:
        return {"estado": "Activo", "jugando": 0, "version": "N/A", "ping": int(ping)}

    jugando = info.get("online", 0)
    version = info.get("version", "N/A")

    return {"estado": "Activo", "jugando": jugando, "version": version, "ping": int(ping)}
