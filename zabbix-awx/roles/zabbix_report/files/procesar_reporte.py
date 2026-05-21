#!/usr/bin/env python3
"""
procesar_reporte.py
-------------------
Etapa de PROCESAMIENTO del flujo Zabbix.

NO se conecta a Zabbix.

Lee el JSON producido por extraer_zabbix.py, calcula/lee promedios y máximos,
parsea umbrales, convierte unidades y genera el Excel.

Es compatible con dos formatos:

1. Formato nuevo recomendado:
    "datos": {
        "avg": 10.5,
        "max": 80.2,
        "min": 2.1,
        "ultimo": 11.0,
        "puntos": 720
    }

2. Formato viejo:
    "datos": [
        {"value_avg": "10", "value_max": "20"},
        {"value_avg": "11", "value_max": "30"}
    ]

Uso:

    python3 procesar_reporte.py \
      --input datos.json.gz \
      --output Reporte.xlsx
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


def convertir_float(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def extraer_umbrales(triggers):
    umbrales = []

    for trigger in triggers:
        desc = trigger.get("description", "")
        expr = trigger.get("expression", "")

        match = re.search(
            r"([><=]+)\s*(\d+(?:\.\d+)?|\{\$[^\}]+})",
            expr,
        )

        if match:
            umbrales.append(
                f"{desc} [{match.group(1)} {match.group(2)}]"
            )
        else:
            umbrales.append(desc)

    return umbrales


def reducir_serie_vieja(puntos, usar_tendencias):
    """
    Compatibilidad con el formato viejo:

        "datos": [
            {"value_avg": "...", "value_max": "..."},
            ...
        ]

    Retorna:
        promedio, maximo, minimo, ultimo, puntos
    """
    if not puntos:
        return None, None, None, None, 0

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

        if not valores_avg and not valores_max:
            return None, None, None, None, len(puntos)

        promedio = (
            sum(valores_avg) / len(valores_avg)
            if valores_avg else None
        )

        maximo = max(valores_max) if valores_max else None
        minimo = min(valores_min) if valores_min else None
        ultimo = valores_avg[-1] if valores_avg else None

        return promedio, maximo, minimo, ultimo, len(puntos)

    valores = []

    for punto in puntos:
        valor = convertir_float(punto.get("value"))
        if valor is not None:
            valores.append(valor)

    if not valores:
        return None, None, None, None, len(puntos)

    promedio = sum(valores) / len(valores)
    maximo = max(valores)
    minimo = min(valores)
    ultimo = valores[-1]

    return promedio, maximo, minimo, ultimo, len(puntos)


def obtener_resumen_datos(datos, usar_tendencias):
    """
    Normaliza datos nuevos o datos viejos.

    Formato nuevo:
        datos es dict con avg/max/min/ultimo/puntos.

    Formato viejo:
        datos es list y se reduce aquí.
    """
    if isinstance(datos, dict):
        promedio = convertir_float(datos.get("avg"))
        maximo = convertir_float(datos.get("max"))
        minimo = convertir_float(datos.get("min"))
        ultimo = convertir_float(datos.get("ultimo"))

        try:
            puntos = int(datos.get("puntos", 0))
        except (TypeError, ValueError):
            puntos = 0

        return promedio, maximo, minimo, ultimo, puntos

    if isinstance(datos, list):
        return reducir_serie_vieja(datos, usar_tendencias)

    return None, None, None, None, 0


def bytes_a_gb(valor):
    if valor is None:
        return None

    return valor / (1024 ** 3)


def construir_fila(maquina):
    fila = {
        "Nombre Activo": maquina.get("nombre_maquina", ""),
        "ip": maquina.get("objetivo", ""),
        "servicio": maquina.get("grupo", ""),
        "memoria actual": 0,
        "% uso memoria ram AVG": 0,
        "CPU actual asignada": 0,
        "% uso procesador AVG": 0,
        "Puntos CPU": 0,
        "Puntos RAM": 0,
    }

    notas_umbrales = []

    for metrica in maquina.get("metricas", []):
        concepto = metrica.get("nombre_reporte", "")
        usar_tendencias = metrica.get("usar_tendencias", False)
        datos = metrica.get("datos", {})

        promedio, maximo, minimo, ultimo, puntos = obtener_resumen_datos(
            datos,
            usar_tendencias,
        )

        if promedio is None and maximo is None and ultimo is None:
            continue

        valor_base = maximo
        if valor_base is None:
            valor_base = ultimo
        if valor_base is None:
            valor_base = promedio

        if "Number" in concepto:
            fila["CPU actual asignada"] = int(round(valor_base))

        elif "Total memory" in concepto:
            memoria_gb = bytes_a_gb(valor_base)
            if memoria_gb is not None:
                fila["memoria actual"] = f"{memoria_gb:.2f} GB"

        elif "utilization" in concepto.lower():
            if "CPU" in concepto:
                fila["% uso procesador AVG"] = (
                    f"{promedio:.4f} %" if promedio is not None else 0
                )
                fila["Puntos CPU"] = puntos

            else:
                fila["% uso memoria ram AVG"] = (
                    f"{promedio:.4f} %" if promedio is not None else 0
                )
                fila["Puntos RAM"] = puntos

            for umbral in extraer_umbrales(metrica.get("triggers", [])):
                notas_umbrales.append(f"{concepto}: {umbral}")

    fila["Umbrales detectados"] = (
        " | ".join(notas_umbrales)
        if notas_umbrales else "—"
    )

    return fila


def parse_pct(serie):
    valores = []

    for valor in serie:
        if isinstance(valor, str) and "%" in valor:
            try:
                valores.append(float(valor.replace("%", "").strip()))
            except ValueError:
                pass

    return valores


def parse_cpu_asignada(valor):
    if isinstance(valor, int):
        return valor

    if isinstance(valor, float):
        return int(valor)

    try:
        return int(str(valor).strip())
    except (TypeError, ValueError):
        return 0


def generar_excel(filas, ruta_salida, trafico):
    df = pd.DataFrame(filas)

    if df.empty:
        raise ValueError("No hay filas para generar el Excel.")

    cpu_vals = (
        parse_pct(df["% uso procesador AVG"])
        if "% uso procesador AVG" in df else []
    )

    ram_vals = (
        parse_pct(df["% uso memoria ram AVG"])
        if "% uso memoria ram AVG" in df else []
    )

    total_vcpu = 0
    if "CPU actual asignada" in df:
        total_vcpu = int(
            df["CPU actual asignada"]
            .apply(parse_cpu_asignada)
            .sum()
        )

    resumen = {
        "Indicador": [
            "Máquinas procesadas",
            "Total vCPU asignadas",
            "Promedio uso CPU (%)",
            "Promedio uso RAM (%)",
            "Tráfico subida (MB)",
            "Tráfico bajada (MB)",
            "Generado",
        ],
        "Valor": [
            len(df),
            total_vcpu,
            f"{sum(cpu_vals) / len(cpu_vals):.4f}" if cpu_vals else "N/A",
            f"{sum(ram_vals) / len(ram_vals):.4f}" if ram_vals else "N/A",
            f"{trafico.get('subida_bytes', 0) / (1024 ** 2):.2f}",
            f"{trafico.get('bajada_bytes', 0) / (1024 ** 2):.2f}",
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ],
    }

    df_resumen = pd.DataFrame(resumen)

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Metricas_Infraestructura",
        )

        df_resumen.to_excel(
            writer,
            index=False,
            sheet_name="Summary",
        )

        for nombre_hoja in writer.sheets:
            ws = writer.sheets[nombre_hoja]

            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 28

            ws.freeze_panes = "A2"

    return ruta_salida


def main():
    parser = argparse.ArgumentParser(
        description="Procesa JSON de Zabbix y genera Excel"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="JSON de entrada .json o .json.gz",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Ruta del Excel a generar",
    )

    args = parser.parse_args()

    payload = cargar_json(args.input)
    maquinas = payload.get("maquinas", [])
    trafico = payload.get("trafico", {})

    if not maquinas:
        print("[!] No hay máquinas en el JSON de entrada.", file=sys.stderr)
        sys.exit(1)

    filas = [construir_fila(maquina) for maquina in maquinas]

    try:
        ruta = generar_excel(filas, args.output, trafico)
    except Exception as exc:
        print(f"[!] Error generando Excel: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Excel generado: {ruta} ({len(filas)} máquina(s))")


if __name__ == "__main__":
    main()