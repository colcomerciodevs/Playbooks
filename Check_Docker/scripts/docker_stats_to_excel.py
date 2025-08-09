#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: docker_stats_to_excel.py
Autor: (tu nombre o equipo)
Descripción:
    Convierte un archivo JSON (generado desde docker stats en NDJSON y luego empaquetado en una lista)
    en un Excel, normalizando campos y aplicando umbrales de riesgo. 
    Además, si el contenedor no tiene límite de CPU, calcula el porcentaje de uso normalizado
    según la cantidad total de vCPU del host.

Uso:
    python3 docker_stats_to_excel.py <json_path> <excel_path>
                                     <cpu_hi> <cpu_med>
                                     <mem_hi> <mem_med>
                                     <pids_hi> <pids_med>
                                     <host_vcpus>

Ejemplo:
    python3 docker_stats_to_excel.py salidas_docker/host.json salidas_docker/host.xlsx 85 70 90 75 400 200 8
"""

import sys
import json
import re
from pathlib import Path
import pandas as pd

# ===========================
# FUNCIONES AUXILIARES
# ===========================

def to_float_percent(x):
    """
    Convierte un valor como '12.34%' o ' 12.34 % ' en un float (12.34).
    Si no es posible convertirlo, devuelve 0.0.
    """
    if x is None:
        return 0.0
    s = str(x).strip()
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*%?\s*$", s)  # Extrae el número antes del símbolo %
    return float(m.group(1)) if m else 0.0

def to_int(x):
    """
    Convierte un valor en entero. 
    Si no es posible, devuelve 0.
    """
    try:
        return int(str(x).strip())
    except Exception:
        return 0

def risk(value, hi, med):
    """
    Clasifica el valor en OK / MED / HIGH según los umbrales:
        - HIGH: mayor o igual que 'hi'
        - MED: mayor o igual que 'med' pero menor que 'hi'
        - OK: por debajo de 'med'
    """
    try:
        v = float(value)
    except Exception:
        v = 0.0
    if v >= hi:
        return "HIGH"
    if v >= med:
        return "MED"
    return "OK"

# ===========================
# PROGRAMA PRINCIPAL
# ===========================

def main():
    # Verificamos que tengamos los argumentos correctos (script + 9 parámetros = 10 elementos en sys.argv)
    if len(sys.argv) != 10:
        print(
            "Uso: docker_stats_to_excel.py <json_path> <excel_path> "
            "<cpu_hi> <cpu_med> <mem_hi> <mem_med> <pids_hi> <pids_med> <host_vcpus>",
            file=sys.stderr,
        )
        sys.exit(1)

    # Asignamos los argumentos a variables
    json_path = Path(sys.argv[1])   # Ruta del archivo JSON
    xlsx_path = Path(sys.argv[2])   # Ruta donde se guardará el Excel

    # Umbrales para riesgos
    cpu_hi, cpu_med = float(sys.argv[3]), float(sys.argv[4])
    mem_hi, mem_med = float(sys.argv[5]), float(sys.argv[6])
    pids_hi, pids_med = int(sys.argv[7]), int(sys.argv[8])

    # Número total de vCPU del host (para normalizar el uso de CPU si no hay límite)
    host_vcpus = max(1, int(float(sys.argv[9])))

    # Cargamos el JSON (debe ser una lista de objetos)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"No se encuentra el archivo JSON: {json_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON inválido en {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("El JSON raíz debe ser un arreglo de objetos.", file=sys.stderr)
        sys.exit(1)

    # Usamos el nombre del archivo (sin extensión) como nombre del host
    host_name = json_path.stem

    # ===========================
    # NORMALIZACIÓN DE REGISTROS
    # ===========================
    rows = []
    for rec in data:
        if not isinstance(rec, dict):
            continue

        # Extraemos datos clave (usando varias opciones porque docker stats puede variar en los nombres de campo)
        container_id = rec.get("ID") or rec.get("ContainerID") or rec.get("Container") or ""
        container_name = rec.get("Name") or rec.get("ContainerName") or rec.get("Container") or ""

        # Conversión de porcentajes y enteros
        cpu_perc = to_float_percent(rec.get("CPUPerc"))
        mem_perc = to_float_percent(rec.get("MemPerc"))
        pids = to_int(rec.get("PIDs"))

        # Campos tal como los da docker stats
        mem_usage = rec.get("MemUsage", "")
        net_io = rec.get("NetIO", "")
        block_io = rec.get("BlockIO", "")

        rows.append({
            "host": host_name,
            "container_name": container_name,
            "container_id": container_id,
            "cpu_perc": cpu_perc,
            "mem_perc": mem_perc,
            "pids": pids,
            "mem_usage_raw": mem_usage,
            "net_io_raw": net_io,
            "block_io_raw": block_io,
        })

    # Creamos DataFrame con los datos recolectados
    df = pd.DataFrame(rows)

    # Si no hay datos, generamos DataFrame vacío con las columnas esperadas
    if df.empty:
        df = pd.DataFrame(columns=[
            "host","container_name","container_id","cpu_perc","mem_perc","pids",
            "mem_usage_raw","net_io_raw","block_io_raw"
        ])

    # ===========================
    # ASEGURAR ORDEN DE COLUMNAS
    # ===========================
    base_cols = [
        ("host", "Host"),
        ("container_name", "Container"),
        ("container_id", "ID"),
        ("cpu_perc", "CPU %"),
        ("mem_perc", "Mem %"),
        ("pids", "PIDs"),
        ("mem_usage_raw", "MemUsage"),
        ("net_io_raw", "NetIO"),
        ("block_io_raw", "BlockIO"),
    ]

    # Si falta alguna columna, la agregamos con valor vacío o cero
    for c, _ in base_cols:
        if c not in df.columns:
            df[c] = "" if c.endswith("_raw") or c in ("host","container_name","container_id") else 0

    # Reordenamos las columnas
    df = df[[c for c,_ in base_cols]].copy()

    # ===========================
    # CALCULAR RIESGOS
    # ===========================
    df["CPU_Risk"] = df["cpu_perc"].apply(lambda v: risk(v, cpu_hi, cpu_med))
    df["Mem_Risk"] = df["mem_perc"].apply(lambda v: risk(v, mem_hi, mem_med))
    df["PIDs_Risk"] = df["pids"].apply(lambda v: risk(v, pids_hi, pids_med))

    # ===========================
    # NORMALIZACIÓN POR vCPUs DEL HOST
    # ===========================
    # Ejemplo: 106.74% de uso de CPU en host con 8 vCPU -> 13.34% del total de CPU físico del host
    df["Host_vCPUs"] = host_vcpus
    df["CPU % (vs host)"] = (df["cpu_perc"] / df["Host_vCPUs"]).round(2)

    # ===========================
    # RENOMBRAR Y ORDENAR PARA PRESENTACIÓN
    # ===========================
    rename_map = {src: hdr for src, hdr in base_cols}
    df = df.rename(columns=rename_map)

    final_cols = [
        "Host","Container","ID",
        "CPU %","CPU_Risk","CPU % (vs host)","Host_vCPUs",
        "Mem %","Mem_Risk",
        "PIDs","PIDs_Risk",
        "MemUsage","NetIO","BlockIO"
    ]
    for c in final_cols:
        if c not in df.columns:
            df[c] = ""
    df = df[final_cols]

    # ===========================
    # EXPORTAR A EXCEL
    # ===========================
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(xlsx_path, index=False)

    # Mensaje de salida para Ansible
    print(f"Registros: {len(df)} | Excel: {xlsx_path}")

# Punto de entrada del script
if __name__ == "__main__":
    main()
