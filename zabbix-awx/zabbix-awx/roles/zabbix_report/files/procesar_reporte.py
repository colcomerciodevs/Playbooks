#!/usr/bin/env python3
"""
procesar_reporte.py
-------------------
Etapa de PROCESAMIENTO del flujo Zabbix.

NO se conecta a Zabbix. Lee el JSON crudo (o .gz) producido por
extraer_zabbix.py, calcula promedios/máximos, parsea umbrales, convierte
unidades y genera el Excel (hoja de datos + hoja Summary).

    python3 procesar_reporte.py --input datos.json.gz --output Reporte.xlsx
"""

import argparse
import gzip
import json
import re
import sys
from datetime import datetime

import pandas as pd


def cargar_json(ruta):
    abrir = gzip.open if ruta.endswith(".gz") else open
    with abrir(ruta, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def extraer_umbrales(triggers):
    umbrales = []
    for t in triggers:
        desc = t.get("description", "")
        expr = t.get("expression", "")
        match = re.search(r"([><=]+)\s*(\d+(?:\.\d+)?|\{\$[^\}]+})", expr)
        if match:
            umbrales.append(f"{desc} [{match.group(1)} {match.group(2)}]")
        else:
            umbrales.append(desc)
    return umbrales


def reducir_serie(puntos, usar_tendencias):
    if not puntos:
        return None, None
    if usar_tendencias:
        promedio = sum(float(p["value_avg"]) for p in puntos) / len(puntos)
        maximo = max(float(p["value_max"]) for p in puntos)
    else:
        valores = [float(p["value"]) for p in puntos]
        promedio = sum(valores) / len(valores)
        maximo = max(valores)
    return promedio, maximo


def construir_fila(maquina):
    fila = {
        "Nombre Activo": maquina["nombre_maquina"],
        "ip": maquina["objetivo"],
        "servicio": maquina["grupo"],
        "memoria actual": 0,
        "% uso memoria ram AVG": 0,
        "CPU actual asignada": 0,
        "% uso procesador AVG": 0,
    }
    notas_umbrales = []

    for metrica in maquina["metricas"]:
        concepto = metrica["nombre_reporte"]
        usar_tendencias = metrica["usar_tendencias"]
        promedio, maximo = reducir_serie(metrica.get("datos", []), usar_tendencias)

        if promedio is None:
            continue

        if "Number" in concepto:
            fila["CPU actual asignada"] = int(maximo)
        elif "Total memory" in concepto:
            fila["memoria actual"] = f"{maximo / (1024 ** 3):.2f} GB"
        elif "utilization" in concepto.lower():
            if "CPU" in concepto:
                fila["% uso procesador AVG"] = f"{promedio:.4f} %"
            else:
                fila["% uso memoria ram AVG"] = f"{promedio:.4f} %"

            for u in extraer_umbrales(metrica.get("triggers", [])):
                notas_umbrales.append(f"{concepto}: {u}")

    fila["Umbrales detectados"] = " | ".join(notas_umbrales) if notas_umbrales else "—"
    return fila


def generar_excel(filas, ruta_salida, trafico):
    df = pd.DataFrame(filas)

    def parse_pct(serie):
        vals = []
        for v in serie:
            if isinstance(v, str) and "%" in v:
                try:
                    vals.append(float(v.replace("%", "").strip()))
                except ValueError:
                    pass
        return vals

    cpu_vals = parse_pct(df["% uso procesador AVG"]) if "% uso procesador AVG" in df else []
    ram_vals = parse_pct(df["% uso memoria ram AVG"]) if "% uso memoria ram AVG" in df else []

    resumen = {
        "Indicador": [
            "Máquinas procesadas", "Total vCPU asignadas",
            "Promedio uso CPU (%)", "Promedio uso RAM (%)",
            "Tráfico subida (MB)", "Tráfico bajada (MB)", "Generado",
        ],
        "Valor": [
            len(df),
            int(df["CPU actual asignada"].apply(lambda x: x if isinstance(x, int) else 0).sum()),
            f"{sum(cpu_vals) / len(cpu_vals):.4f}" if cpu_vals else "N/A",
            f"{sum(ram_vals) / len(ram_vals):.4f}" if ram_vals else "N/A",
            f"{trafico.get('subida_bytes', 0) / (1024 ** 2):.2f}",
            f"{trafico.get('bajada_bytes', 0) / (1024 ** 2):.2f}",
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ],
    }
    df_resumen = pd.DataFrame(resumen)

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Metricas_Infraestructura")
        df_resumen.to_excel(writer, index=False, sheet_name="Summary")
        for nombre_hoja in writer.sheets:
            ws = writer.sheets[nombre_hoja]
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 28

    return ruta_salida


def main():
    parser = argparse.ArgumentParser(description="Procesa JSON crudo de Zabbix y genera Excel")
    parser.add_argument("--input", required=True, help="JSON crudo (.json o .json.gz)")
    parser.add_argument("--output", required=True, help="Ruta del Excel a generar")
    args = parser.parse_args()

    payload = cargar_json(args.input)
    maquinas = payload.get("maquinas", [])
    trafico = payload.get("trafico", {})

    if not maquinas:
        print("[!] No hay máquinas en el JSON de entrada.", file=sys.stderr)
        sys.exit(1)

    filas = [construir_fila(m) for m in maquinas]
    ruta = generar_excel(filas, args.output, trafico)
    print(f"Excel generado: {ruta} ({len(filas)} máquina(s))")


if __name__ == "__main__":
    main()
