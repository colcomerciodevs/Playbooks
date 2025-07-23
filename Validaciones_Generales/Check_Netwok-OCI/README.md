README - Análisis de Red con Ansible
=====================================

Descripción:
------------
Este playbook de Ansible realiza un análisis básico de red desde hosts Linux y Windows.
Verifica conectividad (ping) y puertos TCP hacia una lista de IPs especificadas, y genera reportes.

Funciones principales:
----------------------
1. Lee una lista de IPs objetivo desde archivo (archivo_ips.txt)
2. Lee una lista de puertos TCP desde archivo (archivo_puertos.txt)
3. Obtiene información local del host (hostname, IP, netmask, gateway)
4. Ejecuta pruebas de ping a cada IP
5. Ejecuta pruebas de conexión TCP a cada IP:PUERTO
6. Genera dos archivos de salida por ejecución:
   - reporte_red_<timestamp>.csv → resultado plano en formato CSV
   - reporte_red_<timestamp>.log → log legible por host

Tecnologías utilizadas:
------------------------
- Ansible con módulos:
    - shell / win_shell (para ping y verificación TCP directa)
    - lineinfile / blockinfile (para generar archivos locales)
- Linux:
    - Uso de /dev/tcp para testear puertos (sin necesidad de nc)
- Windows:
    - PowerShell TcpClient para testear puertos

Formato de salida CSV:
-----------------------
HOSTNAME,IP_LOCAL,MASCARA,GATEWAY,ACCION,IP_DESTINO,PUERTO,ESTADO

Ejemplo:
--------
ansiblepruLB,10.181.6.38,255.255.240.0,10.181.0.1,ping,8.8.8.8,N/A,Exitoso
ansiblepruLB,10.181.6.38,255.255.240.0,10.181.0.1,puerto,8.8.8.8,53,Abierto

Estructura esperada del proyecto:
----------------------------------
Check_Netwok-OCI/
├── archivo_ips.txt                → Lista de IPs objetivo
├── archivo_puertos.txt           → Lista de puertos objetivo
├── check_network-oci.yml         → Playbook principal
├── Tasks/
│   ├── ping_task.yml             → Lógica por sistema para ping
│   └── puerto_task.yml           → Lógica por sistema para puertos
└── Salidas_Playbooks/
    └── reporte_red_<timestamp>.csv
    └── reporte_red_<timestamp>.log

Requisitos:
-----------
- Ansible 2.9 o superior
- Conectividad válida SSH (Linux) o WinRM (Windows)
- Linux con Bash y /dev/tcp habilitado
- Windows con PowerShell disponible

Limitaciones:
-------------
- Solo se validan puertos TCP, no UDP
- No se distingue entre "filtrado" y "cerrado" si hay firewalls
- Ping solo verifica conectividad básica, no latencia avanzada

Recomendado para:
------------------
- Diagnóstico básico de red en entornos mixtos Linux/Windows
- Verificación de conectividad desde nodos sin herramientas externas
- Generación de reportes para validación de red y troubleshooting

