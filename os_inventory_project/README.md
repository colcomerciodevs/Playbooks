# OS Inventory Project (JSON -> Excel)

## Qué hace
1. Playbook `generate_os_json.yml`:
   - Recolecta en cada host:
     - `hostname` real de la máquina (`ansible_hostname`)
     - `ip` tomada del inventario (`ansible_host`, con fallback a `inventory_hostname`)
     - `os_full_version` (toma `PRETTY_NAME` de `/etc/os-release` o usa distribución + versión)
   - Consolida todo en `Salidas_Playbooks/version_sistemas.json`.

2. Script `scripts/convert_json_to_excel.py`:
   - Lee el JSON y genera un Excel `Salidas_Playbooks/version_sistemas_YYYYMMDD_HHMMSS.xlsx`.

## Uso
1. Ejecuta el playbook (ajusta el grupo `prueba2` en tu inventario):
   ```bash
   ansible-playbook generate_os_json.yml
   ```

2. Convierte a Excel:
   ```bash
   python3 scripts/convert_json_to_excel.py
   ```

## Requisitos Python
Instala dependencias para la conversión a Excel:
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## Notas
- La salida **siempre** se guarda en `Salidas_Playbooks/` en la raíz del proyecto.
- El JSON es una lista de objetos con las llaves: `hostname`, `ip`, `os_full_version`.
