#!/usr/bin/env python3
"""
extraer_zabbix.py
-----------------
Etapa de EXTRACCIÓN del flujo Zabbix.

Hace TODAS las llamadas a la API JSON-RPC de Zabbix (host.get, item.get,
trend.get / history.get, trigger.get) y vuelca el resultado CRUDO a:
    - <salida>.json      (JSON puro)
    - <salida>.json.gz   (JSON comprimido gzip)

Ansible invoca este script pasándole por --objetivos la lista ya resuelta
de IPs/nombres (Ansible expande los grupos JD/PPS/GP desde defaults/survey).

NO genera Excel. Eso lo hace procesar_reporte.py.
"""

import argparse
import gzip
import json
import os
import re
import sys
from datetime import datetime

import requests
import urllib3

# Carga opcional de .env (uso fuera de AWX). En AWX las credenciales
# llegan como variables de entorno inyectadas por una Custom Credential.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

METRICAS_REQUERIDAS = [
    {"nombre_reporte": "Number of CPUs/Cores", "variaciones": ["number of cpus", "number of cores"]},
    {"nombre_reporte": "Total memory", "variaciones": ["total memory"]},
    {"nombre_reporte": "CPU utilization", "variaciones": ["cpu utilization"]},
    {"nombre_reporte": "Memory utilization", "variaciones": ["memory utilization"]},
]


class ZabbixClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.headers = {"Content-Type": "application/json", "Accept-Encoding": "gzip, deflate"}
        self.bytes_subida = 0
        self.bytes_bajada = 0

    def peticion(self, payload):
        payload["auth"] = self.token
        resp = requests.post(self.url, json=payload, headers=self.headers, verify=False)
        self.bytes_subida += len(resp.request.body or b"")
        self.bytes_bajada += len(resp.content or b"")
        return resp.json().get("result", [])

    def resolver_host(self, objetivo):
        hosts = self.peticion({
            "jsonrpc": "2.0", "method": "host.get", "id": 1,
            "params": {"output": ["hostid", "name"], "filter": {"ip": [objetivo]}},
        })
        if not hosts:
            hosts = self.peticion({
                "jsonrpc": "2.0", "method": "host.get", "id": 1,
                "params": {"output": ["hostid", "name"], "filter": {"name": [objetivo]}},
            })
        return hosts[0] if hosts else None

    def get_items(self, host_id, terminos):
        return self.peticion({
            "jsonrpc": "2.0", "method": "item.get", "id": 2,
            "params": {
                "output": ["itemid", "name", "units", "value_type"],
                "hostids": host_id,
                "search": {"name": terminos},
                "searchByAny": True,
            },
        })

    def get_datos(self, item, concepto, ts_inicio, ts_fin, usar_tendencias):
        metodo = "trend.get" if usar_tendencias else "history.get"
        params = {
            "output": ["value_avg", "value_max"] if usar_tendencias else ["value"],
            "itemids": [item["itemid"]],
            "time_from": ts_inicio,
            "time_till": ts_fin,
        }
        if not usar_tendencias:
            params["history"] = item["value_type"]
            if "utilization" not in concepto.lower():
                params["limit"] = 1
        return self.peticion({"jsonrpc": "2.0", "method": metodo, "id": 3, "params": params})

    def get_triggers(self, item_id):
        return self.peticion({
            "jsonrpc": "2.0", "method": "trigger.get", "id": 4,
            "params": {
                "output": ["description", "expression"],
                "itemids": [item_id],
                "expandDescription": True,
                "expandExpression": True,
            },
        })


def ip_a_grupo_map(grupos):
    mapa = {}
    for grupo, ips in grupos.items():
        for ip in ips:
            mapa[ip] = grupo
    return mapa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objetivos", required=True, help="IPs/nombres separados por coma (ya expandidos)")
    parser.add_argument("--grupos-json", required=True, help="JSON con el mapeo grupo->IPs para etiquetar")
    parser.add_argument("--fecha-inicio", required=True)
    parser.add_argument("--fecha-fin", required=True)
    parser.add_argument("--salida", required=True, help="Ruta base sin extensión")
    args = parser.parse_args()

    url = os.getenv("ZABBIX_URL")
    token = os.getenv("ZABBIX_TOKEN")
    if not url or not token:
        print("[!] Faltan ZABBIX_URL / ZABBIX_TOKEN en el entorno.", file=sys.stderr)
        sys.exit(2)

    grupos = json.loads(args.grupos_json)
    mapa_grupo = ip_a_grupo_map(grupos)

    ts_inicio = int(datetime.strptime(args.fecha_inicio, "%Y-%m-%d %H:%M:%S").timestamp())
    ts_fin = int(datetime.strptime(args.fecha_fin, "%Y-%m-%d %H:%M:%S").timestamp())
    usar_tendencias = (ts_fin - ts_inicio) / 86400 > 3

    objetivos = [o.strip() for o in args.objetivos.split(",") if o.strip()]
    objetivos = list(dict.fromkeys(objetivos))  # dedup preservando orden

    terminos = [v for m in METRICAS_REQUERIDAS for v in m["variaciones"]]
    cli = ZabbixClient(url, token)
    maquinas = []

    for objetivo in objetivos:
        grupo = mapa_grupo.get(objetivo, "SIN GRUPO ASIGNADO")
        host = cli.resolver_host(objetivo)
        if not host:
            print(f"[!] No se encontró máquina: {objetivo}", file=sys.stderr)
            continue

        items = cli.get_items(host["hostid"], terminos)
        bloque_metricas = []

        for metrica in METRICAS_REQUERIDAS:
            item = next(
                (it for it in items if any(v in it["name"].lower() for v in metrica["variaciones"])),
                None,
            )
            if not item:
                continue

            datos = cli.get_datos(item, metrica["nombre_reporte"], ts_inicio, ts_fin, usar_tendencias)
            triggers = []
            if "utilization" in metrica["nombre_reporte"].lower():
                triggers = cli.get_triggers(item["itemid"])

            bloque_metricas.append({
                "nombre_reporte": metrica["nombre_reporte"],
                "item_name": item["name"],
                "usar_tendencias": usar_tendencias,
                "datos": datos,
                "triggers": triggers,
            })

        maquinas.append({
            "objetivo": objetivo,
            "nombre_maquina": host["name"],
            "grupo": grupo,
            "metricas": bloque_metricas,
        })
        print(f"[ok] {host['name']} ({objetivo}) - {len(bloque_metricas)} métrica(s)")

    payload = {
        "generado": datetime.now().isoformat(),
        "rango": {"inicio": args.fecha_inicio, "fin": args.fecha_fin, "usar_tendencias": usar_tendencias},
        "trafico": {"subida_bytes": cli.bytes_subida, "bajada_bytes": cli.bytes_bajada},
        "maquinas": maquinas,
    }

    ruta_json = f"{args.salida}.json"
    ruta_gz = f"{args.salida}.json.gz"
    with open(ruta_json, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    with gzip.open(ruta_gz, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)

    print(f"JSON puro: {ruta_json}")
    print(f"JSON gzip: {ruta_gz}")
    print(f"Máquinas procesadas: {len(maquinas)}")


if __name__ == "__main__":
    main()
