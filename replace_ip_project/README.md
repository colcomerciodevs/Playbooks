## README PROYECTO REEMPLAZO IP EXACTA POR HOSTNAME
## OBJETIVO DEL PROYECTO

Este proyecto permite realizar de forma controlada y auditable el reemplazo de una IP específica dentro de scripts, validando antes y después del cambio y generando evidencia técnica.

1). El proyecto permite:

Escanear scripts .sh y .bash dentro de una ruta definida
Detectar si existe una IP específica (ejemplo: 10.181.0.77)
Reemplazar la IP por un hostname (ejemplo: batch01)
Validar antes y después del cambio
Generar evidencias en JSON
Generar reporte HTML visual con estados OK / FAIL / SKIPPED

## ESTRUCTURA GENERAL DEL PROYECTO

project_root/

site.yml
ansible.cfg

inventories/
inventory.ini

roles/
replace_ip_host/
defaults/main.yml
tasks/main.yml
tasks/one_file.yml

scripts/
genera_reporte_replace_ip.py

Salidas_Playbooks/



## Contiene dos plays principales.

# Play 1
Ejecuta el rol en los servidores destino.

1). Funciones:
Escaneo de scripts
Validación de IP antes del cambio
Reemplazo IP → Hostname
Validación posterior al cambio
Construcción de resultados en variables internas

# Play 2
Ejecutado en localhost.

2). Funciones:
Crear carpeta Salidas_Playbooks en la raíz del proyecto
Consolidar resultados de todos los hosts
Exportar JSON consolidado
Ejecutar Python para generar reporte HTML

# Salidas generadas:
Salidas_Playbooks/replace_ip_report.json
Salidas_Playbooks/replace_ip_report.html


## DEFAULTS MAIN.YML

Define variables base del rol.

Variables principales:

scan_root
Ruta donde se buscarán scripts
Ejemplo: /home /app /data/scripts

old_ip
IP exacta a buscar y reemplazar
Ejemplo: 10.181.0.77

new_host
Hostname destino
Ejemplo: batch01

file_patterns
Tipos de archivos a escanear
Ejemplo: *.sh *.bash

capture_after_host_lines
Define si se guarda evidencia del hostname después del cambio

# TASKS MAIN.YML

Controla el flujo principal del rol.

1). Funciones:
Construcción de regex exacto para evitar reemplazos parciales
Búsqueda de archivos según patrones definidos
Inicialización de estructura de resultados
Llamado al procesamiento individual por archivo
Generación de resumen final por host

# TASKS ONE_FILE.YML

Procesa cada archivo individualmente.

Etapas del proceso:

BEFORE
Busca la IP con grep -nE
Captura número de línea y contenido

MATCH FLAG
Determina si el archivo contiene la IP
Evita advertencias ansible-lint

REPLACE
Reemplaza IP por hostname usando módulo replace
Solo ejecuta si existe coincidencia

AFTER VALIDATION IP
Verifica que la IP ya no exista

AFTER VALIDATION HOSTNAME
Opcional
Verifica que el hostname exista

RESULT REGISTRATION
Construye objeto resultado con:

Archivo
Before lines
After IP lines
After Host lines
Estado
Changed

Estados posibles:

OK → Cambio correcto
FAIL → Cambio incorrecto
SKIPPED → No había IP en el archivo

# SCRIPT PYTHON GENERA_REPORTE_REPLACE_IP.PY

Responsable de generar reporte HTML visual.

Entrada:
replace_ip_report.json

Procesa:
Totales globales
Resultados por host
Resultados por archivo
Comparación BEFORE / AFTER

Salida:
replace_ip_report.html

Colores del reporte:

Verde → OK
Rojo → FAIL
Gris → SKIPPED

FLUJO GENERAL DE EJECUCION

site.yml
↓
Rol replace_ip_host
↓
tasks main
↓
tasks one_file
↓
Resultados en hostvars
↓
Play 2 localhost
↓
JSON consolidado
↓
Reporte HTML

## EJECUCION DEL PROYECTO

ansible-playbook site.yml -e "scan_root=/home/carvajal old_ip=10.181.0.77 new_host=batch01"