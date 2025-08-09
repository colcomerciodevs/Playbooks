#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: docker_stats_to_excel.py
Descripción:
  - Lee un JSON con los objetos que provienen de `docker stats --no-stream` (empacado a lista).
  - Normaliza campos y genera un Excel.
  - Calcula `CPU % (vs host)` dividiendo el CPU % bruto entre la cantidad de vCPUs del host.
  - IMPORTANTE: CPU_Risk se evalúa con `CPU % (vs host)` (no con el valor bruto).

Uso:
  python3 docker_stats_to_excel.py <json_path> <excel_path>
                                   <cpu_hi> <cpu_med>
                                   <mem_hi> <mem_med>
                                   <pids_hi> <pids_med>
                                   <host_vcpus>
"""

import sys
import json
import re
from pathlib import Path
import pandas as pd

# -----------------------------
# Funciones auxiliares
# -----------------------------
def to_float_percent(x):
    """Convierte '12.34%' (o variantes con espacios) a 12.34 (float)."""
    if x is None:
        return 0.0
    s = str(x).strip()
    m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*%?\s*$", s)
    return float(m.group(1)) if m else 0.0

def to_int(x):
    """Convierte a int; si falla, 0."""
    try:
        return int(str(x).strip())
    except Exception:
        return 0

def risk(value, hi, med):
    """Clasifica en OK / MED / HIGH según umbrales."""
    try:
        v = float(value)
    except Exception:
        v = 0.0
    if v >= hi:
        return "HIGH"
    if v >= med:
        return "MED"
    return "OK"

# -----------------------------
# Main
# -----------------------------
def main():
    # script + 9 args = 10 elementos
    if len(sys.argv) != 10:
        print(
            "Uso: docker_stats_to_excel.py <json_path> <excel_path> "
            "<cpu_hi> <cpu_med> <mem_hi> <mem_med> <pids_hi> <pids_med> <host_vcpus>",
            file=sys.stderr,
        )
        sys.exit(1)

    # Args
    json_path = Path(sys.argv[1])
    xlsx_path = Path(sys.argv[2])
    cpu_hi, cpu_med = float(sys.argv[3]), float(sys.argv[4])   # Umbrales CPU (se aplicarán a 'CPU % (vs host)')
    mem_hi, mem_med = float(sys.argv[5]), float(sys.argv[6])   # Umbrales Memoria
    pids_hi, pids_med = int(sys.argv[7]), int(sys.argv[8])     # Umbrales PIDs
    host_vcpus = max(1, int(float(sys.argv[9])))               # vCPU totales del host

    # Cargar JSON
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"No se encuentra el archivo JSON: {json_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON inválido en {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print("El JSON raíz debe ser un arreglo (lista) de objetos.", file=sys.stderr)
        sys.exit(1)

    host_name = json_path.stem  # p.ej., crm04_k8s.json -> crm04_k8s

    # Normalización de registros provenientes de docker stats
    rows = []
    for rec in data:
        if not isinstance(rec, dict):
            continue

        container_id = rec.get("ID") or rec.get("ContainerID") or rec.get("Container") or ""
        container_name = rec.get("Name") or rec.get("ContainerName") or rec.get("Container") or ""

        cpu_perc_bruto = to_float_percent(rec.get("CPUPerc"))  # Puede ser >100 si usa varios cores
        mem_perc = to_float_percent(rec.get("MemPerc"))
        pids = to_int(rec.get("PIDs"))

        rows.append({
            "host": host_name,
            "container_name": container_name,
            "container_id": container_id,
            "cpu_perc": cpu_perc_bruto,       # CPU % bruto de docker
            "mem_perc": mem_perc,
            "pids": pids,
            "mem_usage_raw": rec.get("MemUsage", ""),
            "net_io_raw": rec.get("NetIO", ""),
            "block_io_raw": rec.get("BlockIO", ""),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=[
            "host","container_name","container_id","cpu_perc","mem_perc","pids",
            "mem_usage_raw","net_io_raw","block_io_raw"
        ])

    # Asegurar columnas base y orden
    base_cols = [
        ("host", "Host"),
        ("container_name", "Container"),
        ("container_id", "ID"),
        ("cpu_perc", "CPU %"),         # dejamos el bruto con este encabezado
        ("mem_perc", "Mem %"),
        ("pids", "PIDs"),
        ("mem_usage_raw", "MemUsage"),
        ("net_io_raw", "NetIO"),
        ("block_io_raw", "BlockIO"),
    ]
    for c, _ in base_cols:
        if c not in df.columns:
            df[c] = "" if c.endswith("_raw") or c in ("host","container_name","container_id") else 0
    df = df[[c for c,_ in base_cols]].copy()

    # ---- Cálculo de métricas derivadas ----
    # Normalización de CPU respecto al host completo
    df["Host_vCPUs"] = host_vcpus
    df["CPU % (vs host)"] = (df["cpu_perc"] / df["Host_vCPUs"]).round(2)

    # Riesgos:
    #   - CPU_Risk se calcula con 'CPU % (vs host)' (lo que pediste).
    #   - Mem_Risk y PIDs_Risk se mantienen igual.
    df["CPU_Risk"] = df["CPU % (vs host)"].apply(lambda v: risk(v, cpu_hi, cpu_med))
    df["Mem_Risk"] = df["mem_perc"].apply(lambda v: risk(v, mem_hi, mem_med))
    df["PIDs_Risk"] = df["pids"].apply(lambda v: risk(v, pids_hi, pids_med))

    # Renombrar columnas base para presentación
    rename_map = {src: hdr for src, hdr in base_cols}
    df = df.rename(columns=rename_map)

    # Orden final de columnas:
    #  CPU % (vs host)  -> inmediatamente seguida por  CPU_Risk
    final_cols = [
        "Host","Container","ID",
        "CPU %","CPU % (vs host)","CPU_Risk","Host_vCPUs",
        "Mem %","Mem_Risk",
        "PIDs","PIDs_Risk",
        "MemUsage","NetIO","BlockIO"
    ]
    for c in final_cols:
        if c not in df.columns:
            df[c] = ""
    df = df[final_cols]

    # Exportar a Excel
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(xlsx_path, index=False)

    print(f"Registros: {len(df)} | Excel: {xlsx_path}")

if __name__ == "__main__":
    main()
