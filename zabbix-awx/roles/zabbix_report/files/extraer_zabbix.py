#!/usr/bin/env python3

import argparse
import gzip
import json
import os
import sys
from datetime import datetime

import requests
import urllib3

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


METRICAS = [
    {
        "reporte": "Number of CPUs/Cores",
        "buscar": ["number of cpus", "number of cores"],
        "tipo": "estatica",
        "preferidos": ["Linux: Number of CPUs", "Linux: Number of cores", "Number of CPUs", "Number of cores"],
    },
    {
        "reporte": "Total memory",
        "buscar": ["total memory"],
        "tipo": "estatica",
        "preferidos": ["Linux: Total memory", "Total memory"],
    },
    {
        "reporte": "CPU utilization",
        "buscar": ["cpu utilization"],
        "tipo": "utilizacion",
        "preferidos": ["Linux: CPU utilization", "CPU utilization"],
    },
    {
        "reporte": "Memory utilization",
        "buscar": ["memory utilization"],
        "tipo": "utilizacion",
        "preferidos": ["Linux: Memory utilization", "Memory utilization"],
    },
]


class Zabbix:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.bytes_subida = 0
        self.bytes_bajada = 0

    def api(self, method, params):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": self.token,
            "id": 1,
        }

        r = requests.post(
            self.url,
            json=payload,
            headers={"Content-Type": "application/json"},
            verify=False,
            timeout=60,
        )

        self.bytes_subida += len(r.request.body or b"")
        self.bytes_bajada += len(r.content or b"")

        r.raise_for_status()
        data = r.json()

        if "error" in data:
            print(f"[!] Error API {method}: {data['error']}", file=sys.stderr)
            return []

        return data.get("result", [])

    def buscar_host(self, objetivo):
        # Primero intenta por IP
        hosts = self.api("host.get", {
            "output": ["hostid", "name", "host"],
            "selectInterfaces": ["ip", "dns", "main", "type"],
            "filter": {"ip": [objetivo]},
        })

        # Luego por nombre visible
        if not hosts:
            hosts = self.api("host.get", {
                "output": ["hostid", "name", "host"],
                "selectInterfaces": ["ip", "dns", "main", "type"],
                "filter": {"name": [objetivo]},
            })

        # Luego por host técnico
        if not hosts:
            hosts = self.api("host.get", {
                "output": ["hostid", "name", "host"],
                "selectInterfaces": ["ip", "dns", "main", "type"],
                "filter": {"host": [objetivo]},
            })

        return hosts[0] if hosts else None

    def obtener_items(self, hostid, terminos):
        return self.api("item.get", {
            "output": ["itemid", "name", "key_", "units", "value_type"],
            "hostids": hostid,
            "search": {"name": terminos},
            "searchByAny": True,
            "sortfield": "name",
        })

    def ultimo_valor(self, item):
        return self.api("history.get", {
            "output": ["clock", "value"],
            "itemids": [item["itemid"]],
            "history": item["value_type"],
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 1,
        })

    def datos_rango(self, item, inicio, fin, usar_trends):
        if usar_trends:
            return self.api("trend.get", {
                "output": ["clock", "value_avg", "value_max", "value_min"],
                "itemids": [item["itemid"]],
                "time_from": inicio,
                "time_till": fin,
                "sortfield": "clock",
                "sortorder": "ASC",
            })

        return self.api("history.get", {
            "output": ["clock", "value"],
            "itemids": [item["itemid"]],
            "history": item["value_type"],
            "time_from": inicio,
            "time_till": fin,
            "sortfield": "clock",
            "sortorder": "ASC",
        })

    def triggers(self, itemid):
        return self.api("trigger.get", {
            "output": ["description", "expression"],
            "itemids": [itemid],
            "expandDescription": True,
            "expandExpression": True,
        })


def normalizar(texto):
    return " ".join(str(texto).lower().strip().split())


def seleccionar_item(items, metrica):
    """
    Selecciona primero por nombre exacto/preferido.
    Si no encuentra, usa coincidencia parcial.
    Esto ayuda a que las IPs adicionales tomen el mismo item que se ve en Zabbix.
    """
    preferidos = [normalizar(x) for x in metrica["preferidos"]]
    buscar = [normalizar(x) for x in metrica["buscar"]]

    # 1. Nombre exacto
    for esperado in preferidos:
        for item in items:
            if normalizar(item.get("name", "")) == esperado:
                return item

    # 2. Nombre que termine igual
    for esperado in preferidos:
        for item in items:
            if normalizar(item.get("name", "")).endswith(esperado):
                return item

    # 3. Coincidencia parcial
    for item in items:
        nombre = normalizar(item.get("name", ""))
        if any(x in nombre for x in buscar):
            return item

    return None


def to_float(valor):
    try:
        return float(valor)
    except Exception:
        return None


def resumir_ultimo(puntos):
    if not puntos:
        return {"avg": None, "max": None, "min": None, "ultimo": None, "puntos": 0}

    valor = to_float(puntos[0].get("value"))
    return {
        "avg": valor,
        "max": valor,
        "min": valor,
        "ultimo": valor,
        "puntos": 1,
    }


def resumir_serie(puntos, usar_trends):
    if not puntos:
        return {"avg": None, "max": None, "min": None, "ultimo": None, "puntos": 0}

    if usar_trends:
        avgs = [to_float(p.get("value_avg")) for p in puntos]
        maxs = [to_float(p.get("value_max")) for p in puntos]
        mins = [to_float(p.get("value_min")) for p in puntos]

        avgs = [x for x in avgs if x is not None]
        maxs = [x for x in maxs if x is not None]
        mins = [x for x in mins if x is not None]

        promedio = sum(avgs) / len(avgs) if avgs else None

        return {
            "avg": round(promedio, 4) if promedio is not None else None,
            "max": round(max(maxs), 4) if maxs else None,
            "min": round(min(mins), 4) if mins else None,
            "ultimo": round(avgs[-1], 4) if avgs else None,
            "puntos": len(puntos),
        }

    valores = [to_float(p.get("value")) for p in puntos]
    valores = [x for x in valores if x is not None]

    if not valores:
        return {"avg": None, "max": None, "min": None, "ultimo": None, "puntos": len(puntos)}

    promedio = sum(valores) / len(valores)

    return {
        "avg": round(promedio, 4),
        "max": round(max(valores), 4),
        "min": round(min(valores), 4),
        "ultimo": round(valores[-1], 4),
        "puntos": len(puntos),
    }


def grupo_por_objetivo(grupos):
    mapa = {}
    for grupo, objetivos in grupos.items():
        for objetivo in objetivos:
            mapa[objetivo] = grupo
    return mapa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--objetivos", required=True)
    parser.add_argument("--grupos-json", required=True)
    parser.add_argument("--fecha-inicio", required=True)
    parser.add_argument("--fecha-fin", required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument("--solo-gzip", action="store_true")
    args = parser.parse_args()

    url = os.getenv("ZABBIX_URL")
    token = os.getenv("ZABBIX_TOKEN")

    if not url or not token:
        print("[!] Faltan ZABBIX_URL / ZABBIX_TOKEN", file=sys.stderr)
        sys.exit(2)

    grupos = json.loads(args.grupos_json)
    mapa_grupos = grupo_por_objetivo(grupos)

    ts_inicio = int(datetime.strptime(args.fecha_inicio, "%Y-%m-%d %H:%M:%S").timestamp())
    ts_fin = int(datetime.strptime(args.fecha_fin, "%Y-%m-%d %H:%M:%S").timestamp())

    usar_trends = (ts_fin - ts_inicio) / 86400 > 3

    objetivos = [x.strip() for x in args.objetivos.split(",") if x.strip()]
    objetivos = list(dict.fromkeys(objetivos))

    terminos = []
    for metrica in METRICAS:
        terminos.extend(metrica["buscar"])

    zbx = Zabbix(url, token)
    maquinas = []

    for objetivo in objetivos:
        grupo = mapa_grupos.get(objetivo, "SIN GRUPO ASIGNADO")

        host = zbx.buscar_host(objetivo)
        if not host:
            print(f"[!] No se encontró host: {objetivo}", file=sys.stderr)
            continue

        print(f"[host] {objetivo} -> {host['name']} | grupo={grupo}")

        items = zbx.obtener_items(host["hostid"], terminos)
        metricas_host = []

        for metrica in METRICAS:
            item = seleccionar_item(items, metrica)

            if not item:
                print(f"  [!] No se encontró item: {metrica['reporte']}", file=sys.stderr)
                continue

            if metrica["tipo"] == "estatica":
                metodo = "history.get"
                datos = resumir_ultimo(zbx.ultimo_valor(item))
                usa_trend_metrica = False
            else:
                metodo = "trend.get" if usar_trends else "history.get"
                crudos = zbx.datos_rango(item, ts_inicio, ts_fin, usar_trends)
                datos = resumir_serie(crudos, usar_trends)
                usa_trend_metrica = usar_trends

            triggers = zbx.triggers(item["itemid"]) if metrica["tipo"] == "utilizacion" else []

            metricas_host.append({
                "nombre_reporte": metrica["reporte"],
                "item_name": item.get("name", ""),
                "itemid": item.get("itemid", ""),
                "key_": item.get("key_", ""),
                "units": item.get("units", ""),
                "value_type": item.get("value_type", ""),
                "metodo_usado": metodo,
                "usar_tendencias": usa_trend_metrica,
                "datos": datos,
                "triggers": triggers,
            })

            print(
                f"  [item] {metrica['reporte']} -> "
                f"{item.get('name', '')} | "
                f"key={item.get('key_', '')} | "
                f"metodo={metodo} | "
                f"avg={datos.get('avg')} | "
                f"max={datos.get('max')}"
            )

        maquinas.append({
            "objetivo": objetivo,
            "nombre_maquina": host.get("name", ""),
            "hostid": host.get("hostid", ""),
            "grupo": grupo,
            "metricas": metricas_host,
        })

    payload = {
        "generado": datetime.now().isoformat(),
        "rango": {
            "inicio": args.fecha_inicio,
            "fin": args.fecha_fin,
            "usar_tendencias": usar_trends,
            "modo_datos": "resumido",
        },
        "trafico": {
            "subida_bytes": zbx.bytes_subida,
            "bajada_bytes": zbx.bytes_bajada,
        },
        "maquinas": maquinas,
    }

    ruta_json = f"{args.salida}.json"
    ruta_gz = f"{args.salida}.json.gz"

    if not args.solo_gzip:
        with open(ruta_json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"JSON puro: {ruta_json}")

    with gzip.open(ruta_gz, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)

    print(f"JSON gzip: {ruta_gz}")
    print(f"Máquinas procesadas: {len(maquinas)}")
    print(f"Tráfico subida: {zbx.bytes_subida / (1024 ** 2):.2f} MB")
    print(f"Tráfico bajada: {zbx.bytes_bajada / (1024 ** 2):.2f} MB")


if __name__ == "__main__":
    main()