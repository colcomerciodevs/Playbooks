# Zabbix Agent 2 - Playbook con rol

Este proyecto instala/verifica **Zabbix Agent 2** desde un repositorio HTTP local y genera un **reporte JSON + Excel**.
Se separaron **variables** y **handlers** dentro del rol, y **los scripts** quedaron **fuera del rol**.

## Estructura
```
zabbix_agent_check/
├── site.yml
├── README.md
├── Salidas_Playbooks/            # Carpeta de salidas (JSON/XLSX)
│   └── .gitkeep
├── scripts/                      # Scripts fuera del rol
│   └── generar_excel_zabbix.py
└── roles/
    └── zabbix_agent2/
        ├── defaults/
        │   └── main.yml          # Variables (zabbix_desired_version, repo_base_url)
        ├── handlers/
        │   └── main.yml          # Reinicio del servicio
        ├── tasks/
        │   └── main.yml          # Lógica principal (idéntica a tu playbook)
        └── templates/
            └── zabbix_agent2.conf.template
```

## Variables (roles/zabbix_agent2/defaults/main.yml)
- `zabbix_desired_version`: versión exacta a instalar (por defecto `7.0.18`).
- `repo_base_url`: URL base del repositorio HTTP local (por defecto `http://10.181.8.209:8080/repos/localrepo/zabbix2`).

## Requisitos
- Ansible 2.9+ (o colección equivalente con módulos `ansible.builtin.*`).
- Python con `xlsxwriter` en el controlador si quieres generar el Excel:
  ```bash
  pip install xlsxwriter
  ```

## Inventario
Asegura que tu inventario define el grupo/host `prueba2` apuntando a tus SLES/RHEL/etc.

## Ejecución
Desde la carpeta `zabbix_agent_check`:
```bash
ansible-playbook -i <tu_inventario> site.yml
```
- El primer play ejecuta el rol `zabbix_agent2` en los hosts `prueba2`.
- El segundo play (localhost) crea la carpeta `Salidas_Playbooks/`, exporta `zabbix_auditoria.json`
  y luego ejecuta el script `scripts/generar_excel_zabbix.py` para generar un Excel dentro de esa misma carpeta.

## Notas
- Si el servicio `zabbix-agent2` no existe tras la instalación (por ejemplo porque el paquete no está en el repo),
  revisa que el repositorio local incluya exactamente `zabbix-agent2 = {{ zabbix_desired_version }}` para tu distro
  (`sles15/`, `sles12/`, `el8/`, etc.).
- El rol hace *lockdown* de repos en SLES para forzar instalación solo desde el repo local.
- El template `templates/zabbix_agent2.conf.template` es un ejemplo; ajústalo a tu entorno y credenciales.
```
