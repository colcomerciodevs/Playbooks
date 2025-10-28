## Rol: Despliegue de Monitores Personalizados – Top 5 Procesos (CPU/Memoria)

Este rol implementa monitores personalizados para Zabbix Agent 2 (Linux), que permiten obtener los 5 procesos con mayor uso de memoria y CPU desde el agente.
Cada monitor expone métricas legibles que pueden visualizarse directamente desde Zabbix Server a través de UserParameter.

## Estructura
```
    zabbix_agent_check/
    ├── zabbix_deploy_monitor_process.yml
    ├── README_MONITOR_PROCESS.md
    ├── Salidas_Playbooks/            # Carpeta de salidas (JSON/XLSX)
    │   └── .gitkeep
    ├── scripts/                      # Scripts fuera del rol
    │   └── report_monitor_process_excel.py
    └── roles/
        └── zabbix_agent2/
            ├── defaults/
            │   └── main.yml                         # Variables (zabbix_desired_version, repo_base_url)
            ├── handlers/
            │   └── main.yml                         # Reinicio del servicio
            ├── tasks/
            │   └── deploy_monitor_process.yml       # Lógica principal (idéntica a tu playbook)
            └── templates/
                └── top5_mem_readable.sh.j2          # monitores personalizados para validar top 5 
                └── top5_cpu_readable.sh.j2 
                └── top5_userparams.conf.j2  

```

## Componentes desplegados

/usr/local/bin/top5_mem_readable.sh
Script Bash que muestra los 5 procesos con mayor consumo de memoria.

/usr/local/bin/top5_cpu_readable.sh
Script Bash que muestra los 5 procesos con mayor uso de CPU.

/etc/zabbix/zabbix_agent2.d/top5_readable.conf
Configuración UserParameter que expone ambos monitores a Zabbix Agent2.

## UserParameters creados

custom.top5mem.readable → /usr/local/bin/top5_mem_readable.sh
custom.top5cpu.readable → /usr/local/bin/top5_cpu_readable.sh

## Ejemplo de prueba desde el agente:

zabbix_agent2 -t custom.top5mem.readable
zabbix_agent2 -t custom.top5cpu.readable

## Funcionalidad del rol

Valida que exista Zabbix Agent2 (/usr/sbin/zabbix_agent2).
Crea las rutas necesarias para scripts y configuración.
Copia los archivos con permisos seguros:
root:zabbix, 0750 para scripts, 0640 para configuraciones.
Evita reprocesar si ya existen sin cambios (idempotente).
Reinicia el servicio Zabbix Agent2 solo si hubo modificaciones.
Genera reporte JSON + Excel con resultado de cada host:
Reinicio aplicado
Estado y versión del servicio

## Autor

Infraestructura Linux – Colombiana de Comercio S.A. (Corbeta / Alkosto)
Última actualización: Octubre 2025