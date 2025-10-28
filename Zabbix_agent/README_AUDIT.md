## Rol: Auditoría de Zabbix Agent (v1 y v2) – Linux

Este rol ejecuta una auditoría sobre los agentes Zabbix instalados en los servidores Linux gestionados por Ansible.
Permite identificar qué versión del agente está presente (v1 o v2), su estado de servicio, versión instalada y los datos del sistema operativo.
Su objetivo es generar un inventario actualizado y útil para procesos de migración o validación de configuración de monitoreo.

## Estructura

    zabbix_agent_check/
    ├── zabbix_audit.yml
    ├── README_AUDIT.md
    ├── Salidas_Playbooks/             # Carpeta de resultados (JSON/XLSX)
    │   └── .gitkeep
    ├── scripts/
    │   └── export_audit_excel.py     # Convierte JSON en Excel
    └── roles/
        └── zabbix_agent2/
            ├── defaults/
            │   └── main.yml                      # Variables del rol
            ├── tasks/
            │   └── audit.yml                     # Lógica de auditoría
            ├── handlers/
            │   └── main.yml                      # Reinicio o tareas comunes
            └── templates/
                └── (no aplica, solo tareas YAML)

## Componentes auditados

Zabbix Agent 1 (zabbix-agent)
Verifica si está instalado, su versión y el estado del servicio.

Zabbix Agent 2 (zabbix-agent2)
Verifica instalación, versión, estado del servicio y versión exacta.

Facts del sistema operativo
Incluye nombre del host, IP principal, distribución, versión y arquitectura.

## Funcionalidad del rol

Valida la presencia de los agentes Zabbix (v1 y v2).
Recolecta facts del sistema operativo si está habilitado (zbx_audit_include_os_facts).
Obtiene las versiones y estados de los servicios instalados.
Genera un reporte consolidado en formato JSON y Excel.
Permite identificar qué equipos están listos para migrar a Zabbix Agent2 o cuáles aún usan Agent1.

## Reporte generado

El rol genera los siguientes archivos en la carpeta Salidas_Playbooks:
zbx_audit_results.json
zbx_audit_results.xlsx

## Columnas del Excel generado:

InventoryHostname | Hostname | IP | Estado_Agent1 | Estado_Agent2 | Version_Agent1 | Version_Agent2 | Sistema_Operativo

## Ejemplo de ejecución
ansible-playbook zabbix_audit.yml -i inventario.ini

## Variables principales

zbx_audit_include_os_facts → true (habilita facts del sistema operativo)
zabbix_agent2_bin → /usr/sbin/zabbix_agent2
zabbix_agent1_bin → /usr/sbin/zabbix_agentd

## Consideraciones

No realiza cambios en los servidores, solo lectura y recolección de información.
Puede ejecutarse de forma independiente o previa a otros roles (por ejemplo, migración o despliegue de monitores).
Compatible únicamente con sistemas Linux administrados vía Ansible.

## Autor
Infraestructura Linux – Colombiana de Comercio S.A. (Corbeta / Alkosto)
Última actualización: Octubre 2025