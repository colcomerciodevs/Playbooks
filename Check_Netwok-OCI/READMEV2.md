=======================================================================
📡 VALIDACIÓN DE CONECTIVIDAD DE RED (PING Y PUERTOS) EN LINUX Y WINDOWS
=======================================================================

Este proyecto automatiza la validación de conectividad de red desde múltiples
servidores (tanto Linux como Windows) hacia un conjunto de IPs y puertos 
especificados por el usuario. Utiliza Ansible para desplegar scripts que
ejecutan pruebas de "ping" y conexión TCP a puertos definidos, y genera reportes 
estructurados por host.

-----------------------------------------------------------------------
📁 ESTRUCTURA DEL PROYECTO
-----------------------------------------------------------------------

Check_Netwok-OCI/
├── archivo_ips.txt              → Lista de IPs destino (una por línea)
├── archivo_puertos.txt          → Lista de puertos TCP (uno por línea)
├── vault_windows.yml            → Vault con ansible_password para WinRM
├── scripts/
│   ├── valida_red.sh            → Script Bash (para Linux)
│   └── valida_red.ps1           → Script PowerShell (para Windows)
├── Salidas_Playbooks/           → CSVs individuales por host y reportes globales
└── playbook_validacion_red.yml  → Playbook principal de ejecución

-----------------------------------------------------------------------
⚙️ REQUISITOS
-----------------------------------------------------------------------

• Ansible >= 2.9
• Conectividad:
   - Linux: Acceso SSH mediante clave (key-based authentication)
   - Windows: WinRM configurado + vault con contraseña
• Scripts remotos:
   - Linux: Bash, ping, timeout, /dev/tcp, ip, awk
   - Windows: PowerShell con `System.Net.Sockets.TcpClient`

-----------------------------------------------------------------------
🔍 ¿QUÉ HACE CADA SCRIPT?
-----------------------------------------------------------------------

▶️ **valida_red.sh (Linux):**
   - Ejecuta `ping -c1 -W1 <IP>` para verificar conectividad ICMP
   - Usa `/dev/tcp/IP/PORT` con `timeout` para probar puertos TCP
   - Calcula IP local, máscara y gateway
   - Guarda resultados en `~/salida_valida_red.csv`

▶️ **valida_red.ps1 (Windows):**
   - Usa `Test-Connection` para validar ping
   - Usa `System.Net.Sockets.TcpClient` con timeout de 1 segundo
   - Registra resultado por cada IP y puerto
   - Guarda resultados en `C:\temp\salida_valida_red.csv`

-----------------------------------------------------------------------
📋 FLUJO DE EJECUCIÓN (playbook)
-----------------------------------------------------------------------

1. 🧼 Normaliza y valida archivos de entrada:
   - Elimina líneas vacías o caracteres `\r`
   - Asegura salto de línea final

2. 📁 Copia scripts y archivos de entrada a cada host:
   - Linux: Copia a `~/`
   - Windows: Copia a `C:\temp\`

3. ▶️ Ejecuta el script de validación remoto según el sistema operativo

4. 📥 Trae de vuelta los archivos CSV generados con el módulo `fetch`

5. 🧹 Limpia líneas vacías de los archivos traídos

6. 🔧 Combina todos los resultados por sistema operativo en:
   - `reporte_red_linux_<timestamp>.csv`
   - `reporte_red_windows_<timestamp>.csv`

7. 🔄 Ordena los archivos por nombre de host

-----------------------------------------------------------------------
📥 ENTRADA: archivo_ips.txt y archivo_puertos.txt
-----------------------------------------------------------------------

- archivo_ips.txt:
  8.8.8.8
  8.8.4.4
  1.1.1.1

- archivo_puertos.txt:
  53
  443
  22

-----------------------------------------------------------------------
📤 SALIDA: Formato del archivo CSV generado
-----------------------------------------------------------------------

HOSTNAME,IP_LOCAL,MASCARA,GATEWAY,TIPO,DESTINO,PUERTO,ESTADO

Ejemplo:
linuxhost01,192.168.1.10,255.255.255.0,192.168.1.1,ping,8.8.8.8,N/A,Exitoso  
linuxhost01,192.168.1.10,255.255.255.0,192.168.1.1,puerto,8.8.8.8,53,Abierto  
winhost02,10.10.10.5,24,10.10.10.1,ping,1.1.1.1,N/A,Fallido  
winhost02,10.10.10.5,24,10.10.10.1,puerto,1.1.1.1,443,Cerrado  

-----------------------------------------------------------------------
🛠️ PERSONALIZACIÓN
-----------------------------------------------------------------------

• Puedes editar los archivos `archivo_ips.txt` y `archivo_puertos.txt` para 
  ajustar los destinos.
• La salida por host se encuentra en:
   - Linux: Salidas_Playbooks/tmp_linux_<hostname>.csv
   - Windows: Salidas_Playbooks/tmp_windows_<hostname>.csv
• Los reportes consolidados están en:
   - Salidas_Playbooks/reporte_red_linux_<timestamp>.csv
   - Salidas_Playbooks/reporte_red_windows_<timestamp>.csv

-----------------------------------------------------------------------
🧪 CÓMO EJECUTAR EL PLAYBOOK
-----------------------------------------------------------------------

ansible-playbook check_network-oci.yml --vault-password-file /ansible/Vault/.vault_pass_windows.txt

• Asegúrate que los hosts tengan claves configuradas para SSH (Linux)
• Para Windows, el vault `vault_windows.yml` debe estar descifrado o accesible

-----------------------------------------------------------------------
📌 NOTAS ADICIONALES
-----------------------------------------------------------------------

• Este proyecto NO requiere instalar software adicional en los servidores.
• Los scripts trabajan en paralelo por cada host (modo default Ansible).
• Si tu entorno bloquea `/tmp` con noexec, ya se ajustó para usar `$HOME`.



📍 AUTOR: John Castaño (Infraestructura Linux )
📆 Última actualización: Julio 2025
