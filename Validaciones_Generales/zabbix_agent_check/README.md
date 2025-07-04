INSTRUCCIONES - PLAYBOOK ZABBIX AGENT 2 (7.0.10 LTS) DESDE REPOSITORIO LOCAL HTTP

Este playbook instala o actualiza el Zabbix Agent 2 versión 7.0.10 LTS desde un repositorio HTTP local 
en servidores Linux compatibles, elimina agentes anteriores, configura el archivo de agente 
y genera un reporte en formato Excel.

--------------------------------------------------------------------------------
SISTEMAS OPERATIVOS SOPORTADOS:
--------------------------------------------------------------------------------
- Red Hat Enterprise Linux 7, 8, 9
- CentOS 7, 8
- Oracle Linux 7, 8, 9
- SUSE Linux Enterprise Server 15

--------------------------------------------------------------------------------
REQUISITOS:
--------------------------------------------------------------------------------
1. Repositorio local HTTP funcional (ya configurado con `createrepo`) y accesible, ejemplo:
   http://10.181.8.209:8080/repos/localrepo/zabbix2/

2. Estructura del repositorio en el servidor:
   ├── el7/
   ├── el8/
   ├── el9/
   └── sles15/

   Cada carpeta debe contener el `.rpm` correspondiente a su OS y arquitectura + metadatos.

3. En el controlador Ansible:
   - Instalar dependencias para generar el Excel:
     pip3 install pandas openpyxl

   - Estructura del proyecto:

     zabbix_agent_check/
     ├── playbook.yml
     ├── files/
     │   └── zabbix_agentd.conf.template
     ├── scripts/
     │   └── generar_excel_zabbix.py
     ├── Salidas_Playbooks/
     └── INSTRUCCIONES.txt

--------------------------------------------------------------------------------
¿QUÉ HACE EL PLAYBOOK?
--------------------------------------------------------------------------------
1. Verifica si el agente Zabbix v1 está instalado (zabbix-agent).
2. Verifica si el agente Zabbix v2 está instalado (zabbix-agent2).
3. Si hay que reemplazar v1 o actualizar v2, desinstala el anterior.
4. Agrega temporalmente el repositorio HTTP correspondiente según OS detectado.
5. Instala zabbix-agent2 desde el repositorio local.
6. Configura /etc/zabbix/zabbix_agentd.conf usando plantilla.
7. Habilita e inicia el servicio zabbix-agent2.
8. Elimina el repositorio del sistema después de la instalación.
9. Genera reporte en JSON y lo convierte a Excel con:

   - IP del servidor
   - Versión de Zabbix Agent 1
   - Versión de Zabbix Agent 2
   - Nueva versión instalada (si aplica)
   - Estado final del servicio

--------------------------------------------------------------------------------
¿CÓMO EJECUTARLO?
--------------------------------------------------------------------------------
Desde el directorio raíz del proyecto:

ansible-playbook playbook.yml -i inventario

El Excel se genera en la carpeta:
  Salidas_Playbooks/Reporte_Zabbix_<fecha>.xlsx

--------------------------------------------------------------------------------
NOTAS ADICIONALES:
--------------------------------------------------------------------------------
- El repositorio se agrega como `zabbix-local` y luego se elimina para no dejarlo persistente.
- El archivo de configuración zabbix_agentd.conf se define en `files/zabbix_agentd.conf.template`.
- Puedes modificarlo según tus parámetros de red, hostname, etc.
