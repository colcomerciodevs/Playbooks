# replace_ip_project (Rol + Reporte)

Reemplaza una IP exacta (ej. `10.181.0.77`) por un hostname (ej. `batch01`) en scripts `.sh` / `.bash`,
con validación **ANTES**/**DESPUÉS** y reporte en `Salidas_Playbooks`.

## Ejecutar (Ansible Core)

1) Edita el inventario:
- `inventories/inventory.ini` (grupo `[targets]`)

2) Ejecuta el playbook:
```bash
ansible-playbook playbooks/site.yml -e "scan_root=/home/carvajal old_ip=10.181.0.77 new_host=batch01"
```

3) Salidas:
- `Salidas_Playbooks/replace_ip_report.json`
- `Salidas_Playbooks/replace_ip_report.html`

## Cambiar extensiones
```bash
ansible-playbook playbooks/site.yml -e 'file_patterns=["*.sh","*.bash","*.ksh"]'
```

## Notas
- El rol construye el regex exacto automáticamente con bordes `\b` para evitar reemplazos parciales.
