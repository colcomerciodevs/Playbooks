#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from html import escape


def to_int(v, default=0):
    """
    Convierte v a int de forma segura.
    Soporta: int, str numérico, None.
    Si falla, retorna default.
    """
    if v is None:
        return default
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return default
        # intenta int directo
        try:
            return int(s)
        except ValueError:
            # intenta float -> int
            try:
                return int(float(s))
            except ValueError:
                return default
    return default


def status_badge(status: str) -> str:
    cls = {"OK": "ok", "FAIL": "fail", "SKIPPED": "skip"}.get(status, "skip")
    return f"<span class='badge {cls}'>{escape(status)}</span>"


def parse_line(s: str):
    if ":" in s:
        left, right = s.split(":", 1)
        try:
            return int(left.strip()), right.rstrip("\n")
        except ValueError:
            return None, s.rstrip("\n")
    return None, s.rstrip("\n")


def render_lines(lines):
    if not lines:
        return "<div class='muted'>&lt;sin coincidencias&gt;</div>"

    rows = []
    for ln in lines:
        n, text = parse_line(ln)
        ln_cell = "-" if n is None else str(n)
        rows.append(
            "<tr>"
            f"<td class='ln'>{escape(ln_cell)}</td>"
            f"<td class='code'>{escape(text)}</td>"
            "</tr>"
        )
    return "<table class='tbl'>" + "".join(rows) + "</table>"


def main():
    ap = argparse.ArgumentParser(description="Genera reporte HTML a partir del JSON consolidado de Ansible.")
    ap.add_argument("--input", required=True, help="Ruta JSON consolidado (lista de summaries por host).")
    ap.add_argument("--output", required=True, help="Ruta HTML de salida.")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise SystemExit("El JSON de entrada debe ser una LISTA (summaries por host).")

    # Totales globales (cast seguro a int)
    sum_ok = sum(to_int(h.get("totals", {}).get("ok", 0)) for h in data)
    sum_fail = sum(to_int(h.get("totals", {}).get("fail", 0)) for h in data)
    sum_skip = sum(to_int(h.get("totals", {}).get("skipped", 0)) for h in data)

    css = '''
    body{font-family:Arial,Helvetica,sans-serif;margin:24px;background:#fff;color:#111;}
    h1{margin:0 0 8px 0;}
    .meta{color:#444;margin-bottom:16px;}
    .card{border:1px solid #ddd;border-radius:10px;padding:16px;margin:14px 0;}
    .host{font-size:18px;margin:0 0 8px 0;}
    .badge{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:700;font-size:12px;}
    .ok{background:#e7f7ec;color:#0b6b2e;border:1px solid #bfe8c9;}
    .fail{background:#fde8e8;color:#a40000;border:1px solid #f5bcbc;}
    .skip{background:#f0f0f0;color:#444;border:1px solid #ddd;}
    .file{font-weight:700;margin:12px 0 6px 0;}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
    .box{border:1px solid #eee;border-radius:10px;padding:10px;background:#fafafa;}
    .title{font-weight:700;margin:0 0 8px 0;}
    .tbl{width:100%;border-collapse:collapse;}
    .tbl td{border-top:1px solid #eee;vertical-align:top;padding:6px 8px;}
    .ln{width:60px;color:#666;font-variant-numeric:tabular-nums;}
    .code{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;white-space:pre-wrap;}
    .muted{color:#666;font-style:italic;}
    .summary{display:flex;gap:10px;align-items:center;margin:10px 0 18px 0;}
    '''

    now = datetime.now().isoformat(timespec="seconds")
    html = [
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Reporte Replace IP</title>"
        f"<style>{css}</style></head><body>"
    ]

    html.append("<h1>Reporte: Reemplazo IP → Hostname</h1>")
    html.append(f"<div class='meta'>Generado: {escape(now)}</div>")
    html.append(
        "<div class='summary'>"
        f"<span class='badge ok'>OK: {sum_ok}</span>"
        f"<span class='badge fail'>FAIL: {sum_fail}</span>"
        f"<span class='badge skip'>SKIPPED: {sum_skip}</span>"
        "</div>"
    )

    for h in data:
        host = h.get("host", "unknown")
        scan_root = h.get("scan_root", "")
        old_ip = h.get("old_ip", "")
        new_host = h.get("new_host", "")
        generated_at = h.get("generated_at", "")
        totals = h.get("totals", {}) or {}
        files = h.get("files", []) or []

        # Cast seguro también aquí por si vienen como strings
        t_scanned = to_int(totals.get("files_scanned", 0))
        t_before = to_int(totals.get("files_with_ip_before", 0))
        t_ok = to_int(totals.get("ok", 0))
        t_fail = to_int(totals.get("fail", 0))
        t_skip = to_int(totals.get("skipped", 0))

        html.append("<div class='card'>")
        html.append(f"<div class='host'><b>Host:</b> {escape(host)}</div>")
        html.append(
            "<div class='meta'>"
            f"<b>Ruta:</b> {escape(scan_root)} &nbsp; | &nbsp; "
            f"<b>Cambio:</b> {escape(old_ip)} → {escape(new_host)} &nbsp; | &nbsp; "
            f"<b>Fecha:</b> {escape(generated_at)}<br>"
            f"<b>Totales:</b> scanned={t_scanned}, con_ip_antes={t_before}, OK={t_ok}, FAIL={t_fail}, SKIPPED={t_skip}"
            "</div>"
        )

        for item in files:
            path = item.get("file", "")
            status = item.get("status", "SKIPPED")
            before_lines = item.get("before_lines", []) or []
            after_ip_lines = item.get("after_ip_lines", []) or []
            after_host_lines = item.get("after_host_lines", []) or []

            html.append(f"<div class='file'>{escape(path)} &nbsp; {status_badge(status)}</div>")
            html.append("<div class='grid'>")

            html.append(
                "<div class='box'>"
                "<div class='title'>ANTES (coincidencias IP)</div>"
                f"{render_lines(before_lines)}"
                "</div>"
            )

            html.append(
                "<div class='box'>"
                "<div class='title'>DESPUÉS (IP debería estar vacío)</div>"
                f"{render_lines(after_ip_lines)}"
                f"<div class='title' style='margin-top:10px;'>DESPUÉS (líneas con {escape(new_host)})</div>"
                f"{render_lines(after_host_lines)}"
                "</div>"
            )

            html.append("</div>")

        html.append("</div>")

    html.append("</body></html>")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("".join(html))

    print(f"OK: reporte generado en: {args.output}")


if __name__ == "__main__":
    main()
