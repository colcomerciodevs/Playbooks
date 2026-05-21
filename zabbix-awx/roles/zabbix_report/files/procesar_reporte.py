#!/usr/bin/env python3

import argparse
import gzip
import json
import re
from datetime import datetime

import pandas as pd


def cargar_json(ruta):
    abrir = gzip.open if ruta.endswith(".gz") else open
    with abrir(ruta, "rt", encoding="utf-8") as f:
        return json.load(f)


def valor(datos, campo):
    try:
        return float(datos.get(campo))
    except (TypeError, ValueError):
        return None


def formato_pct(v):
    return f"{v:.4f} %" if v is not None else "N/A"


def bytes_a_gb(v):
    if v is None:
        return "N/A"
    return f"{v / (1024 ** 3):.2f} GB"


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


def construir_fila_principal(maquina):
    fila = {
        "Nombre Activo": maquina.get("nombre_maquina", ""),
        "IP": maquina.get("objetivo", ""),
        "Grupo": maquina.get("grupo", ""),
        "Memoria actual": "N/A",
        "CPU actual asignada": "N/A",
        "% uso procesador AVG": "N/A",
        "% uso procesador MAX": "N/A",
        "% uso memoria ram AVG": "N/A",
        "% uso memoria ram MAX": "N/A",
        "Item CPU usado": "",
        "Item RAM usado": "",
        "Key CPU": "",
        "Key RAM": "",
        "Umbrales detectados": "—",
    }

    umbrales_total = []

    for metrica in maquina.get("metricas", []):
        nombre = metrica.get("nombre_reporte", "")
        item_name = metrica.get("item_name", "")
        key = metrica.get("key_", "")
        datos = metrica.get("datos", {})

        avg = valor(datos, "avg")
        maximo = valor(datos, "max")
        ultimo = valor(datos, "ultimo")

        base = maximo if maximo is not None else ultimo
        if base is None:
            base = avg

        if nombre == "Number of CPUs/Cores":
            fila["CPU actual asignada"] = int(round(base)) if base is not None else "N/A"

        elif nombre == "Total memory":
            fila["Memoria actual"] = bytes_a_gb(base)

        elif nombre == "CPU utilization":
            fila["% uso procesador AVG"] = formato_pct(avg)
            fila["% uso procesador MAX"] = formato_pct(maximo)
            fila["Item CPU usado"] = item_name
            fila["Key CPU"] = key

        elif nombre == "Memory utilization":
            fila["% uso memoria ram AVG"] = formato_pct(avg)
            fila["% uso memoria ram MAX"] = formato_pct(maximo)
            fila["Item RAM usado"] = item_name
            fila["Key RAM"] = key

        if "utilization" in nombre.lower():
            for u in extraer_umbrales(metrica.get("triggers", [])):
                umbrales_total.append(f"{item_name}: {u}")

    if umbrales_total:
        fila["Umbrales detectados"] = " | ".join(umbrales_total)

    return fila


def construir_summary(maquinas):
    filas = []

    for maquina in maquinas:
        grupo = maquina.get("grupo", "")
        nombre_maquina = maquina.get("nombre_maquina", "")
        ip = maquina.get("objetivo", "")

        for metrica in maquina.get("metricas", []):
            nombre = metrica.get("nombre_reporte", "")

            if "utilization" not in nombre.lower():
                continue

            datos = metrica.get("datos", {})
            avg = valor(datos, "avg")
            maximo = valor(datos, "max")

            umbrales = extraer_umbrales(metrica.get("triggers", []))
            umbrales_txt = "\n".join(f"- {u}" for u in umbrales) if umbrales else "—"

            filas.append({
                "Grupo": grupo,
                "Nombre maquina": nombre_maquina,
                "IP": ip,
                "Metrica": metrica.get("item_name", nombre),
                "Key": metrica.get("key_", ""),
                "Promedio": formato_pct(avg),
                "Maximo": formato_pct(maximo),
                "Umbrales detectados": umbrales_txt,
            })

        filas.append({
            "Grupo": "",
            "Nombre maquina": "",
            "IP": "",
            "Metrica": "",
            "Key": "",
            "Promedio": "",
            "Maximo": "",
            "Umbrales detectados": "",
        })

    return filas


def ajustar_excel(writer):
    for hoja in writer.sheets:
        ws = writer.sheets[hoja]
        ws.freeze_panes = "A2"

        for col in ws.columns:
            letra = col[0].column_letter
            ancho = 18

            for celda in col:
                texto = str(celda.value) if celda.value is not None else ""
                ancho = max(ancho, min(len(texto) + 2, 55))

            ws.column_dimensions[letra].width = ancho


def generar_excel(payload, salida):
    maquinas = payload.get("maquinas", [])
    trafico = payload.get("trafico", {})

    filas_principal = [construir_fila_principal(m) for m in maquinas]
    filas_summary = construir_summary(maquinas)

    resumen_general = [
        {
            "Indicador": "Máquinas procesadas",
            "Valor": len(maquinas),
        },
        {
            "Indicador": "Tráfico subida (MB)",
            "Valor": f"{trafico.get('subida_bytes', 0) / (1024 ** 2):.2f}",
        },
        {
            "Indicador": "Tráfico bajada (MB)",
            "Valor": f"{trafico.get('bajada_bytes', 0) / (1024 ** 2):.2f}",
        },
        {
            "Indicador": "Generado",
            "Valor": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
    ]

    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        pd.DataFrame(filas_principal).to_excel(
            writer,
            index=False,
            sheet_name="Metricas_Infraestructura",
        )

        pd.DataFrame(filas_summary).to_excel(
            writer,
            index=False,
            sheet_name="Summary",
        )

        pd.DataFrame(resumen_general).to_excel(
            writer,
            index=False,
            sheet_name="Resumen_General",
        )

        ajustar_excel(writer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Archivo .json o .json.gz generado por extraer_zabbix.py")
    parser.add_argument("--output", required=True, help="Archivo Excel de salida")
    args = parser.parse_args()

    payload = cargar_json(args.input)

    if not payload.get("maquinas"):
        raise SystemExit("[!] No hay máquinas en el JSON de entrada.")

    generar_excel(payload, args.output)

    print(f"Excel generado: {args.output}")


if __name__ == "__main__":
    main()