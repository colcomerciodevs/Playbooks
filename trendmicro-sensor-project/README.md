# Trend Micro Sensor Deployment (Ansible Project)

Este proyecto automatiza:
1) Precheck de conectividad (DNS+TCP/443) a endpoints Trend Micro. - RETIRADO
2) Copia de instaladores (ServerAgent y Sensor) al host remoto.
3) Validación inicial (versión/release de `ds_agent` y estados de servicios `vls_agent`/`tmxbc`).
4) Instalación de **ServerAgent** y luego **Sensor** con `./tmxbc install`.
5) Validación final y exporte de **JSON** y **CSV**.
6) Generación de **Excel con colores** (verde=activo/OK, naranja=REVISAR).

## Uso
1. Edita `inventories/hosts.ini` con tus servidores.
2. Ajusta variables en `group_vars/all.yml` (rutas, endpoints, criterio OK).
3. Ejecuta:
   ```bash
   pip install -r requirements.txt
   ansible-playbook -i inventories/hosts.ini playbooks/deploy_trendmicro.yml
   ```
4. Genera el Excel:
   ```bash
   python3 scripts/generate_excel.py Salidas_Playbooks/trendmicro_instalacion_sensor.json Salidas_Playbooks/reporte_trendmicro.xlsx
   ```

## Requisitos (control node)
- Ansible 2.12+
- Python 3.8+ (`pip install -r requirements.txt`)
