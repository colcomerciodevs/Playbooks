#!/usr/bin/env python3
"""
extraer_zabbix.py
-----------------
Etapa de EXTRACCIÓN del flujo Zabbix.

Hace las llamadas a la API JSON-RPC de Zabbix y genera un JSON optimizado:

    - Para métricas estáticas:
        Number of CPUs/Cores
        Total memory

      Solo toma el último valor disponible.

    - Para métricas de utilización:
        CPU utilization
        Memory utilization

      Usa trend.get si el rango es mayor a 3 días.
      Usa history.get si el rango es menor o igual a 3 días.

IMPORTANTE:
    Ya no guarda todos los puntos crudos dentro del JSON.
    Guarda solo un resumen:

        {
          "avg": 10.25,
          "max": 80.5,
          "min": 2.1,
          "puntos": 720
        }

Esto reduce mucho el tamaño del JSON y mejora el tiempo del procesamiento posterior.

Ansible invoca este script pasándole por --objetivos la lista ya resuelta
de IPs/nombres.

NO genera Excel. Eso lo hace procesar_reporte.py.
"""

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


METRICAS_REQUERIDAS = [
    {
        "nombre_reporte": "Number of CPUs/Cores",
        "variaciones": ["number of cpus", "number of cores"],
        "tipo": "estatica",
    },
    {
        "nombre_reporte": "Total memory",
        "variaciones": ["total memory"],
        "tipo": "estatica",
    },
    {
        "nombre_reporte": "CPU utilization",
        "variaciones": ["cpu utilization"],
        "tipo": "utilizacion",
    },
    {
        "nombre_reporte": "Memory utilization",
        "variaciones": ["memory utilization"],
        "tipo": "utilizacion",
    },
]


class ZabbixClient:
    def __init__(self, url, token, timeout=60):
        self.url = url
        self.token = token
        self.timeout = timeout
        self.headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        self.bytes_subida = 0
        self.bytes_bajada = 0

    def peticion(self, payload):
        payload["auth"] = self.token

        try:
            resp = requests.post(
                self.url,
                json=payload,
                headers=self.headers,
                verify=False,
                timeout=self.timeout,
            )
            self.bytes_subida += len(resp.request.body or b"")
            self.bytes_bajada += len(resp.content or b"")
            resp.raise_for_status()

            respuesta = resp.json()

            if "error" in respuesta:
                print(
                    f"[!] Error API Zabbix en método {payload.get('method')}: "
                    f"{respuesta['error']}",
                    file=sys.stderr,
                )
                return []

            return respuesta.get("result", [])

        except requests.exceptions.RequestException as exc:
            print(f"[!] Error HTTP contra Zabbix: {exc}", file=sys.stderr)
            return []
        except ValueError as exc:
            print(f"[!] Respuesta no JSON desde Zabbix: {exc}", file=sys.stderr)
            return []

    def resolver_host(self, objetivo):
        """
        Resuelve host por IP. Si no encuentra, intenta por nombre.
        """
        hosts = self.peticion({
            "jsonrpc": "2.0",
            "method": "host.get",
            "id": 1,
            "params": {
                "output": ["hostid", "name"],
                "filter": {"ip": [objetivo]},
            },
        })

        if not hosts:
            hosts = self.peticion({
                "jsonrpc": "2.0",
                "method": "host.get",
                "id": 1,
                "params": {
                    "output": ["hostid", "name"],
                    "filter": {"name": [objetivo]},
                },
            })

        return hosts[0] if hosts else None

    def get_items(self, host_id, terminos):
        """
        Obtiene los items candidatos del host usando searchByAny.
        """
        return self.peticion({
            "jsonrpc": "2.0",
            "method": "item.get",
            "id": 2,
            "params": {
                "output": ["itemid", "name", "units", "value_type"],
                "hostids": host_id,
                "search": {"name": terminos},
                "searchByAny": True,
            },
        })

    def get_ultimo_valor_history(self, item):
        """
        Para métricas estáticas:
            - Number of CPUs/Cores
            - Total memory

        Solo trae el último valor conocido.
        Esto evita consultar un mes completo de tendencias para datos que
        normalmente no cambian.
        """
        params = {
            "output": ["clock", "value"],
            "itemids": [item["itemid"]],
            "history": item["value_type"],
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 1,
        }

        return self.peticion({
            "jsonrpc": "2.0",
            "method": "history.get",
            "id": 3,
            "params": params,
        })

    def get_datos_utilizacion(self, item, ts_inicio, ts_fin, usar_tendencias):
        """
        Para métricas de utilización:
            - CPU utilization
            - Memory utilization

        Si el rango es mayor a 3 días usa trend.get.
        Si el rango es corto usa history.get.
        """
        if usar_tendencias:
            metodo = "trend.get"
            params = {
                "output": ["clock", "value_avg", "value_max", "value_min"],
                "itemids": [item["itemid"]],
                "time_from": ts_inicio,
                "time_till": ts_fin,
                "sortfield": "clock",
                "sortorder": "ASC",
            }
        else:
            metodo = "history.get"
            params = {
                "output": ["clock", "value"],
                "itemids": [item["itemid"]],
                "history": item["value_type"],
                "time_from": ts_inicio,
                "time_till": ts_fin,
                "sortfield": "clock",
                "sortorder": "ASC",
            }

        return self.peticion({
            "jsonrpc": "2.0",
            "method": metodo,
            "id": 3,
            "params": params,
        })

    def get_triggers(self, item_id):
        return self.peticion({
            "jsonrpc": "2.0",
            "method": "trigger.get",
            "id": 4,
            "params": {
                "output": ["description", "expression"],
                "itemids": [item_id],
                "expandDescription": True,
                "expandExpression": True,
            },
        })


def ip_a_grupo_map(grupos):
    mapa = {}

    for grupo, objetivos in grupos.items():
        for objetivo in objetivos:
            mapa[objetivo] = grupo

    return mapa


def convertir_float(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def resumir_ultimo_valor(puntos):
    """
    Convierte una respuesta de history.get con limit 1 a formato resumen.
    """
    if not puntos:
        return {
            "avg": None,
            "max": None,
            "min": None,
            "ultimo": None,
            "puntos": 0,
        }

    valor = convertir_float(puntos[0].get("value"))

    return {
        "avg": valor,
        "max": valor,
        "min": valor,
        "ultimo": valor,
        "puntos": 1,
    }


def resumir_serie(puntos, usar_tendencias):
    """
    Resume una serie de history.get o trend.get.

    Para trend.get:
        usa value_avg, value_max y value_min.

    Para history.get:
        usa value.
    """
    if not puntos:
        return {
            "avg": None,
            "max": None,
            "min": None,
            "ultimo": None,
            "puntos": 0,
        }

    if usar_tendencias:
        valores_avg = []
        valores_max = []
        valores_min = []

        for punto in puntos:
            avg = convertir_float(punto.get("value_avg"))
            maximo = convertir_float(punto.get("value_max"))
            minimo = convertir_float(punto.get("value_min"))

            if avg is not None:
                valores_avg.append(avg)
            if maximo is not None:
                valores_max.append(maximo)
            if minimo is not None:
                valores_min.append(minimo)

        promedio = (
            sum(valores_avg) / len(valores_avg)
            if valores_avg else None
        )

        return {
            "avg": round(promedio, 4) if promedio is not None else None,
            "max": round(max(valores_max), 4) if valores_max else None,
            "min": round(min(valores_min), 4) if valores_min else None,
            "ultimo": round(valores_avg[-1], 4) if valores_avg else None,
            "puntos": len(puntos),
        }

    valores = []

    for punto in puntos:
        valor = convertir_float(punto.get("value"))
        if valor is not None:
            valores.append(valor)

    if not valores:
        return {
            "avg": None,
            "max": None,
            "min": None,
            "ultimo": None,
            "puntos": len(puntos),
        }

    promedio = sum(valores) / len(valores)

    return {
        "avg": round(promedio, 4),
        "max": round(max(valores), 4),
        "min": round(min(valores), 4),
        "ultimo": round(valores[-1], 4),
        "puntos": len(puntos),
    }


def seleccionar_item(items, variaciones):
    """
    Selecciona el primer item cuyo nombre contenga alguna variación esperada.
    """
    for item in items:
        nombre = item.get("name", "").lower()
        if any(v in nombre for v in variaciones):
            return item

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Extrae métricas Zabbix y genera JSON optimizado"
    )

    parser.add_argument(
        "--objetivos",
        required=True,
        help="IPs/nombres separados por coma",
    )
    parser.add_argument(
        "--grupos-json",
        required=True,
        help="JSON con el mapeo grupo->IPs/nombres para etiquetar",
    )
    parser.add_argument(
        "--fecha-inicio",
        required=True,
        help="Fecha inicio en formato YYYY-MM-DD HH:MM:SS",
    )
    parser.add_argument(
        "--fecha-fin",
        required=True,
        help="Fecha fin en formato YYYY-MM-DD HH:MM:SS",
    )
    parser.add_argument(
        "--salida",
        required=True,
        help="Ruta base sin extensión",
    )
    parser.add_argument(
        "--solo-gzip",
        action="store_true",
        help="Si se indica, solo genera .json.gz y no genera .json plano",
    )

    args = parser.parse_args()

    url = os.getenv("ZABBIX_URL")
    token = os.getenv("ZABBIX_TOKEN")

    if not url or not token:
        print("[!] Faltan ZABBIX_URL / ZABBIX_TOKEN en el entorno.", file=sys.stderr)
        sys.exit(2)

    try:
        grupos = json.loads(args.grupos_json)
    except json.JSONDecodeError as exc:
        print(f"[!] --grupos-json no es un JSON válido: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        ts_inicio = int(datetime.strptime(args.fecha_inicio, "%Y-%m-%d %H:%M:%S").timestamp())
        ts_fin = int(datetime.strptime(args.fecha_fin, "%Y-%m-%d %H:%M:%S").timestamp())
    except ValueError as exc:
        print(f"[!] Formato de fecha inválido: {exc}", file=sys.stderr)
        sys.exit(2)

    if ts_fin <= ts_inicio:
        print("[!] La fecha fin debe ser mayor que la fecha inicio.", file=sys.stderr)
        sys.exit(2)

    mapa_grupo = ip_a_grupo_map(grupos)
    usar_tendencias_global = (ts_fin - ts_inicio) / 86400 > 3

    objetivos = [o.strip() for o in args.objetivos.split(",") if o.strip()]
    objetivos = list(dict.fromkeys(objetivos))

    if not objetivos:
        print("[!] No se recibieron objetivos válidos.", file=sys.stderr)
        sys.exit(2)

    terminos = [
        variacion
        for metrica in METRICAS_REQUERIDAS
        for variacion in metrica["variaciones"]
    ]

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
            item = seleccionar_item(items, metrica["variaciones"])

            if not item:
                print(
                    f"[!] Item no encontrado para {metrica['nombre_reporte']} "
                    f"en {host['name']} ({objetivo})",
                    file=sys.stderr,
                )
                continue

            if metrica["tipo"] == "estatica":
                usar_tendencias_metrica = False
                datos_crudos = cli.get_ultimo_valor_history(item)
                datos_resumen = resumir_ultimo_valor(datos_crudos)
            else:
                usar_tendencias_metrica = usar_tendencias_global
                datos_crudos = cli.get_datos_utilizacion(
                    item,
                    ts_inicio,
                    ts_fin,
                    usar_tendencias_metrica,
                )
                datos_resumen = resumir_serie(
                    datos_crudos,
                    usar_tendencias_metrica,
                )

            triggers = []

            if metrica["tipo"] == "utilizacion":
                triggers = cli.get_triggers(item["itemid"])

            bloque_metricas.append({
                "nombre_reporte": metrica["nombre_reporte"],
                "item_name": item["name"],
                "itemid": item["itemid"],
                "units": item.get("units", ""),
                "value_type": item.get("value_type", ""),
                "usar_tendencias": usar_tendencias_metrica,
                "datos": datos_resumen,
                "triggers": triggers,
            })

        maquinas.append({
            "objetivo": objetivo,
            "nombre_maquina": host["name"],
            "grupo": grupo,
            "metricas": bloque_metricas,
        })

        print(
            f"[ok] {host['name']} ({objetivo}) - "
            f"{len(bloque_metricas)} métrica(s)"
        )

    payload = {
        "generado": datetime.now().isoformat(),
        "rango": {
            "inicio": args.fecha_inicio,
            "fin": args.fecha_fin,
            "usar_tendencias": usar_tendencias_global,
            "modo_datos": "resumido",
        },
        "trafico": {
            "subida_bytes": cli.bytes_subida,
            "bajada_bytes": cli.bytes_bajada,
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
    print(f"Tráfico subida: {cli.bytes_subida / (1024 ** 2):.2f} MB")
    print(f"Tráfico bajada: {cli.bytes_bajada / (1024 ** 2):.2f} MB")


if __name__ == "__main__":
    main()