Proyecto: Validación de Red en Hosts Linux y Windows (Basado en Tasks)

📌 OBJETIVO GENERAL
-------------------
Este proyecto permite validar la conectividad de red desde múltiples hosts Windows y Linux gestionados por Ansible, comprobando:
- Si una lista de IPs responde a PING.
- Si ciertas combinaciones IP:PUERTO están accesibles mediante conexiones TCP.

Los resultados se consolidan en archivos CSV y logs organizados por host, permitiendo análisis y auditorías de conectividad.

🧱 ESTRUCTURA DEL PROYECTO
---------------------------
├── archivo_ips.txt           # IPs de destino a validar (una por línea)
├── archivo_puertos.txt       # Puertos a validar (uno por línea)
├── playbook.yml              # Playbook principal de Ansible
├── Tasks/
│   ├── ping_task.yml         # Subtareas para análisis de ping
│   └── puerto_task.yml       # Subtareas para análisis de puertos
├── vault_windows.yml         # Vault con credenciales para Windows (si aplica)
└── Salidas_Playbooks/        # Carpeta con reportes generados (CSV y logs)

⚙️ FUNCIONAMIENTO GENERAL
---------------------------
1. Inicialización
   - Se define un timestamp global (`YYYY-MM-DD_HHMMSS`) para organizar salidas por sesión.
   - Se leen los archivos `archivo_ips.txt` y `archivo_puertos.txt`.
   - Se normaliza el formato y se asegura que no haya líneas vacías o caracteres erróneos (CRLF).

2. Recopilación de Red Local
   - En cada host se obtiene:
     - Nombre del host
     - IP local
     - Máscara de subred
     - Gateway (puerta de enlace)
   - Esto se hace usando facts de Ansible en Linux o PowerShell en Windows.

3. Validación de Conectividad
   - Por cada IP:
     - Se realiza un `ping` desde el host remoto.
     - Se guarda una línea CSV con el resultado (`Exitoso` o `Fallido`).
   - Por cada combinación IP:PUERTO:
     - Se realiza un intento de conexión TCP (vía `/dev/tcp` o `TcpClient`).
     - Se guarda una línea CSV indicando si el puerto está `Abierto` o `Cerrado`.

4. Consolidación de Resultados
   - Cada host genera:
     - Un archivo `.csv` con los resultados de red.
     - Un archivo `.log` con un resumen detallado.
   - Todo se guarda localmente en la carpeta `Salidas_Playbooks/`.

🔒 SSH Y SEGURIDAD
-------------------
- Las conexiones SSH a hosts Linux se hacen utilizando claves (SSH key-based authentication).
- Las credenciales de Windows (si aplica) están protegidas mediante Ansible Vault (`vault_windows.yml`).

🧪 EJEMPLO DE RESULTADO CSV
----------------------------
hostname,ip_local,mask,gateway,tipo,ip_destino,puerto,estado
srv-app01,192.168.10.5,255.255.255.0,192.168.10.1,ping,8.8.8.8,N/A,Exitoso
srv-app01,192.168.10.5,255.255.255.0,192.168.10.1,puerto,8.8.8.8,443,Abierto
srv-app01,192.168.10.5,255.255.255.0,192.168.10.1,puerto,8.8.8.8,22,Cerrado

📤 SALIDAS GENERADAS
---------------------
- Salidas_Playbooks/reporte_red_linux_<timestamp>.csv
- Salidas_Playbooks/reporte_red_windows_<timestamp>.csv
- Salidas_Playbooks/reporte_red_linux_<timestamp>.log
- Salidas_Playbooks/reporte_red_windows_<timestamp>.log

📁 FORMATO DE LOS ARCHIVOS DE ENTRADA
-------------------------------------
archivo_ips.txt:
8.8.8.8
192.168.1.1
10.10.0.5

archivo_puertos.txt:
22
443
8080

📦 REQUISITOS
--------------
- Ansible 2.9 o superior.
- SSH sin contraseña configurado para hosts Linux.
- Acceso WinRM o credenciales cifradas vía vault para hosts Windows.
- Rutas `playbook_dir` y carpeta `Salidas_Playbooks` creadas previamente.

🛠️ PERSONALIZACIÓN
-------------------
- Se puede adaptar para escanear rangos IP.
- Puede integrarse con Zabbix, Excel, o sistemas de inventario.

📍 AUTOR: John Castaño (Infraestructura Linux )
📆 Última actualización: Julio 2025
