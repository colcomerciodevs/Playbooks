🧾 README – Playbook check_ds2022_json.yml
📘 Descripción general

Este playbook de Ansible permite verificar en múltiples servidores Linux si los agentes de Trend Micro Deep Security / Cloud One Workload presentan problemas relacionados con el certificado DS2022.der (o variantes como DS20_v2.der).
Estos errores suelen manifestarse cuando el agente no puede validar el driver del módulo tmhook o se reportan mensajes como "missing key DS2022.der".

El playbook automatiza toda la verificación, genera un informe consolidado en JSON y luego lo convierte automáticamente en Excel mediante un script Python.

🎯 Objetivos
Revisar los logs del servicio ds_agent y del kernel (dmesg) para detectar fallas relacionadas con certificados o módulos.
Verificar si el módulo tmhook está cargado correctamente.
Determinar si el host requiere enrolar nuevamente el certificado DS2022.
Consolidar los resultados en un archivo JSON.
Ejecutar un script Python que convierte el JSON en un archivo Excel (.xlsx).

🧩 Requisitos previos
Ansible instalado y funcional.
Acceso por SSH a los hosts definidos en el inventario (sin contraseña o con clave configurada).
En el control node (localhost):
Tener instalado el comando jq.
Tener Python 3 disponible.
El script json_to_excel_ds2022.py ubicado en la carpeta Scripts/.
En los hosts destino:
El agente ds_agent debe estar instalado.
Se recomienda ejecutar como usuario con privilegios (become: true).

📂 Estructura de archivos
Playbooks/
│
├── check_ds2022.yml          ← Playbook principal
├── Scripts/
│   └── json_to_excel_ds2022.py    ← Script Python que convierte JSON → Excel
└── Salidas_Playbooks/
    ├── ds2022_result.json         ← Archivo JSON generado
    └── ds2022_result.xlsx         ← Archivo Excel generado

⚙️ Variables principales
Variable	Descripción	Valor por defecto
output_dir	Directorio donde se almacenan los resultados	./Salidas_Playbooks
output_json	Ruta completa del JSON consolidado	{{ output_dir }}/ds2022_result.json
python_script	Ruta al script Python que genera el Excel	./Scripts/json_to_excel_ds2022.py


🧠 Flujo del playbook
Crea el directorio de salida (Salidas_Playbooks).
Inicializa un JSON vacío si no existe.
Ejecuta comandos de diagnóstico en cada host:
- journalctl -u ds_agent
- dmesg -T
- lsmod | grep tmhook
- /opt/ds_agent/dsa_query --cmd GetAgentStatus -t xml
Evalúa condiciones para determinar si el host requiere enrolar DS2022.
Guarda resultados parciales (uno por host) en /tmp/<hostname>_ds2022.tmp.json.
Agrega cada resultado al archivo global ds2022_result.json usando jq (serializado con throttle: 1 para evitar colisiones).
Ejecuta el script Python que convierte el JSON a Excel.