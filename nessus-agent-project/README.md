## DESPLIEGUE Y VALIDACIÓN DE NESSUS AGENT (OFFLINE)

Automatización con Ansible para instalar, validar y vincular agentes Nessus Agent de forma offline.
Compatible con:

- Oracle Linux / RHEL / Rocky / Alma / Fedora
- SUSE Linux Enterprise Server (SLES 12 / 15)
- Debian / Ubuntu
- Amazon Linux

## El playbook realiza las siguientes tareas:

Limpieza completa de versiones previas del agente.
Instalación desde paquete local (.rpm o .deb).
Habilitación del servicio systemd.
Vinculación con el Tenable Nessus Manager.
Extracción de resultados (Link status, versión, estado, etc.).
Generación de reporte JSON y Excel consolidado.

## ESTRUCTURA DEL PROYECTO

nessus-agent-project/
├── deploy_nessus_offline.yml
├── roles/
│ └── nessus_agent/
│ ├── tasks/main.yml
│ ├── handlers/main.yml
│ └── defaults/main.yml
├── scripts/
│ └── nessus_excel_report.py
└── Salidas_Playbooks/
├── nessus_results.json
└── nessus_agent_reporte.xlsx

## VARIABLES PRINCIPALES

nessus_installers_dir → Directorio local con los paquetes (.rpm / .deb)
nessus_installer_dest_dir → Ruta destino en el host remoto
nessus_manager_host → IP o hostname del Tenable Manager
nessus_manager_port → Puerto del Manager
nessus_agent_key → Clave de registro del agente
nessus_agent_groups → Grupo de registro del agente
nessus_try_link → true/false para ejecutar el enlace automático
nessus_output_dir → Directorio donde se guardan los reportes

## Ejemplo de valores:
nessus_installers_dir: /root/NessusInstallers
nessus_installer_dest_dir: /root
nessus_manager_host: 10.181.8.192
nessus_manager_port: 8834
nessus_agent_key: 279fa0cfb3549180f65cffe7a095455a4ba825af6ed6ad923cb7f228870a1694
nessus_agent_groups: corbeta
nessus_try_link: true
nessus_output_dir: ./Salidas_Playbooks

## FLUJO GENERAL DEL PLAYBOOK

Etapa 01–09: Recolección de facts y selección del instalador adecuado
Etapa 10–18: Limpieza de versiones previas del agente
Etapa 19–23: Instalación del nuevo paquete Nessus Agent
Etapa 24–28: Activación y verificación del servicio systemd
Etapa 29–30: Verificación / vinculación con el Manager
Etapa 31–37: Extracción de versión, link status y estado general
Etapa 38–41: Consolidación de resultados en JSON y Excel

# EJECUCIÓN

Ejemplo de ejecución desde el controlador:
ansible-playbook deploy_nessus_offline.yml -i inventario.yml

# Ejemplo de inventario:

[nessus_targets]
ansible_test ansible_host=10.181.11.55 ansible_user=root

# SALIDAS GENERADAS

JSON consolidado
Ruta: Salidas_Playbooks/nessus_results.json

Ejemplo de contenido:
[
{
"host": "ansible_test",
"os_name": "OracleLinux",
"os_family": "RedHat",
"os_version": "9.5",
"agent_version": "11.0.1-el9",
"installed": true,
"service_active": true,
"linked": false,
"link_status": "Not linked to a manager",
"manager_host": "10.181.8.192",
"manager_port": "8834",
"groups": "corbeta",
"timestamp": "2025-10-21T19:07:01Z"
}
]

## Excel consolidado
Ruta: Salidas_Playbooks/nessus_agent_reporte.xlsx
El archivo contiene columnas como:
Host | OS Name | OS Family | Versión | Agent Version | Agente Instalado | Servicio Activo | Vinculado | Link Status | Manager Host | Manager Port | Grupos | Link Output | Error | Timestamp

## REQUISITOS

Ansible 2.12 o superior
Python 3.x con los módulos:
openpyxl (para generación de Excel)
json, os, sys (incluidos por defecto)
Permisos root en los hosts destino
Acceso local a los instaladores Nessus Agent
Clave de registro válida del Tenable Manager

## RESULTADO FINAL

El proceso deja:

Nessus Agent instalado y en ejecución.
Resultado verificado en JSON y Excel.
Campo “Link status” correctamente evaluado:
“Not linked to a manager” → agente sin vincular
“Connected (pending heartbeat)” → vinculación en espera
“Linked successfully” → vinculación confirmada

## MANTENIMIENTO

Para actualizar la versión del agente:

Copiar el nuevo instalador al directorio NessusInstallers.
Ajustar nessus_agent_key o nessus_agent_groups según corresponda.
Ejecutar nuevamente el playbook.

## AUTOR
Infraestructura Linux 
Fecha de última actualización: 21-Oct-2025