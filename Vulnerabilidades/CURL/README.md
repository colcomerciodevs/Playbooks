# Auditoría curl/libcurl (JSON + Excel)

## Objetivo
Este playbook audita servidores Linux/Unix (CentOS 7, RHEL 7/8, Oracle Linux 8/9, SLES 15 SP4/SP5) para:
- Identificar si `curl` está instalado.
- Obtener versión de `curl` y `libcurl`.
- Capturar indicios del backend/feature set (p.ej. GnuTLS, libssh/libssh2).
- Generar evidencia consolidada:
  - `curl_audit.json`
  - `curl_audit_report.xlsx` (con filas coloreadas)

## Alcance de vulnerabilidad
- **Rango afectado indicado por Ciber:** `curl 7.17.0` hasta `8.17.0` (inclusive).
- El Excel marca:
  - **AFECTADA** (rojo) si `curl_version` cae dentro del rango.
  - **NO AFECTADA** (verde) si está fuera del rango o si `curl` no está instalado.

## Archivos incluidos
- `curl_audit.yml`  
  Playbook principal de auditoría y exportación.
- `curl_audit_to_excel.py`  
  Script Python que convierte el JSON consolidado a Excel.
- `Salidas_Playbooks/`  
  Carpeta generada automáticamente con resultados.

## Estructura esperada
