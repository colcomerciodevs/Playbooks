# Rol: replace_ip_host

Este rol:
- Busca scripts por patrones (por defecto `*.sh` y `*.bash`) en `scan_root`
- Valida coincidencias **ANTES** con `grep -nE` usando un regex exacto (solo la IP literal)
- Reemplaza la IP exacta por un hostname (ej. `batch01`)
- Valida **DESPUÉS**:
  - Que la IP ya no exista
  - (Opcional) que existan líneas con el hostname
- Construye:
  - `replace_ip_results` (lista por archivo)
  - `replace_ip_summary` (resumen + totales)

## Variables
- `scan_root` (default `/home`)
- `old_ip` (default `10.181.0.77`)
- `new_host` (default `batch01`)
- `file_patterns` (default `["*.sh","*.bash"]`)
- `capture_after_host_lines` (default `true`)

> Si `old_ip_regex` está vacío, el rol construye `\bold_ip\b` automáticamente (exacto).
