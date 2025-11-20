## README – Rol Ansible: Instalación y Gestión de Nessus Agent

Este rol automatiza la instalación, purga completa, reinstalación y vinculación del agente Tenable Nessus en múltiples distribuciones Linux.

## Incluye:

Detección automática de distribución y versión del sistema.
Selección automática del instalador correcto según el sistema operativo.
Copia del instalador desde el controlador.
Eliminación completa de instalaciones previas.
Instalación usando exactamente los comandos oficiales de Tenable por sistema operativo.
Reinicio del servicio mediante handlers.
Obtención detallada del estado del agente (versión, link status, linked to).
Generación de archivo JSON consolidado con resultados.
Generación de reporte Excel mediante script Python.

## SECCIÓN: VARIABLES PRINCIPALES

Variables que deben configurarse en group_vars, host_vars o en el playbook:

nessus_installers_dir: Ruta en el controlador donde están los instaladores.
nessus_installer_dest_dir: Ruta temporal en el host destino para colocar el instalador.
nessus_agent_key: Clave de vinculación (link key).
nessus_manager_host: Host del Tenable Manager.
nessus_manager_port: Puerto del Manager.
nessus_try_link: true/false para habilitar vinculación.
nessus_agent_groups: Grupo o grupos en Tenable.
nessus_output_dir: Directorio donde se generarán los resultados JSON y Excel.

## También se utiliza un mapa de subcarpetas donde se espera encontrar los instaladores:

nessus_pkg_dir_map:
RedHat-7 -> rhel7
RedHat-8 -> rhel8
OracleLinux-7 -> ol7
OracleLinux-8 -> ol8
Debian-any -> debian
Ubuntu-any -> ubuntu
Suse-12 -> sles12
Amazon-any -> amazon
default -> otros

## SECCIÓN: INSTALACIÓN SEGÚN SISTEMA OPERATIVO (OFICIAL TENABLE)

Debian / Ubuntu:
dpkg -i NessusAgent-<version>.deb

Fedora 34+, RHEL8+, Oracle Linux 8+:
dnf install NessusAgent-<version>.rpm

RHEL7 y Oracle Linux 7:
rpm -ivh NessusAgent-<version>.el7.x86_64.rpm

SUSE:
zypper install NessusAgent-<version>.suse12.x86_64.rpm

## El rol ejecuta automáticamente el comando correcto según el sistema operativo.

## SECCIÓN: HANDLERS INCLUIDOS

Reload systemd daemon: Recarga el demonio systemd cuando se elimina o reemplaza una unit.
Reiniciar Nessus Agent: Reinicia y habilita la unidad detectada (nessusagent o nessus-agent).
El reinicio del servicio nunca se hace directamente desde las tareas, únicamente por handlers.

## SECCIÓN: RESULTADOS CONSOLIDADOS

El rol genera un JSON con información por host:

host
ip_address
os_name
os_family
os_version
agent_version
installed (true/false)
service_active (true/false)
linked (true/false)
link_status
manager_host
manager_port
groups
stdout completo del link
errores
timestamp

Posteriormente genera un archivo Excel usando el script:
scripts/nessus_excel_report.py

## SECCIÓN: FLUJO GENERAL DEL ROL

Recolecta facts del sistema y servicios.
Determina la ruta correcta del instalador.
Purga completamente Nessus previo (unlink + eliminación de carpetas + eliminación de units viejas).
Copia el instalador local al host.
Instala Nessus Agent usando el comando adecuado según el sistema.
Ejecuta handlers (reinicio del servicio).
Verifica estado del servicio.
Extrae datos del agente: versión, estado, link status.
Realiza el link si está habilitado y no está vinculado.
Construye un objeto de resultados por host.
En el controlador consolida todos los hosts en JSON.
Genera el Excel final.