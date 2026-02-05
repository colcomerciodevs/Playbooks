# ELASTIC AGENT – PLAYBOOK OPERATIVO (REENROLL / RESTART / REPORT)

# DESCRIPCIÓN GENERAL
Este playbook permite administrar el Elastic Agent en servidores Linux mediante ejecución selectiva de acciones:

Re-Enroll del agente contra Fleet
Reinicio y validación del servicio
Generación de reporte consolidado JSON + Excel

# El playbook es modular y permite ejecutar acciones específicas sin afectar otras.

####  ARQUITECTURA ####

# Estructura del proyecto:
playbooks/
elastic_agent_action.yml
roles/
elastic_agent_siem/
tasks/
enroll.yml
record_min.yml
service.yml
report.yml
defaults/main.yml

##### ESCENARIOS SOPORTADOS #####

# ESCENARIO 1 – SOLO RE-ENROLL
Ejecuta:
enroll.yml
record_min.yml
report.yml

Uso típico:
Re registrar agente en Fleet
Cambio de token
Cambio Fleet URL
No valida estado del servicio systemd.

# ESCENARIO 2 – SOLO RESTART

Ejecuta:
service.yml
report.yml

Uso típico:
Validar estado servicio
Reinicio controlado
Auditoría versión y status

# ESCENARIO 3 – RE-ENROLL + RESTART

Ejecuta:
enroll.yml
record_min.yml
service.yml
report.yml

Uso típico:
Re-enroll + validación servicio
Despliegues masivos
Recuperación agentes

##### SALIDA DEL REPORTE ####

Se generan los archivos:

Salidas_Playbooks/
elastic_agent_report.json
elastic_agent_report.xlsx

# Columnas del Excel:
Inventario
Hostname
IP
Versión Elastic Agent
Re-Enroll Ejecutado
Re-Enroll OK
Mensaje Re-Enroll
Restart OK
Estado Servicio
OK Global
Extracto Status

#### VARIABLES PRINCIPALES ####

CORE
elastic_agent_service_name

REPORT
elastic_agent_report_dir
elastic_agent_report_json
elastic_agent_report_xlsx

RE-ENROLL
elastic_fleet_url
elastic_enrollment_token
elastic_insecure

CONTROL DE ACCIÓN
elastic_action

Valores válidos:
restart
reenroll
reenroll_restart



#### EJECUCIÓN EN ANSIBLE CORE #####

SOLO RESTART
ansible-playbook elastic_agent_action.yml -i inventory.ini -e "elastic_action=restart"

SOLO RE-ENROLL
ansible-playbook elastic_agent_action.yml -i inventory.ini -e "elastic_action=reenroll"

RE-ENROLL + RESTART
ansible-playbook elastic_agent_action.yml -i inventory.ini -e "elastic_action=reenroll_restart"



#### FLUJO INTERNO #####

Si elastic_action = reenroll
ejecuta enroll.yml
ejecuta record_min.yml
ejecuta report.yml

Si elastic_action = restart
ejecuta service.yml
ejecuta report.yml

Si elastic_action = reenroll_restart
ejecuta enroll.yml
ejecuta record_min.yml
ejecuta service.yml
ejecuta report.yml



### NOTAS OPERATIVAS ###

record_min.yml asegura que exista información para el reporte aunque no se valide el servicio.

service.yml construye el registro completo con estado real del servicio.

report.yml consolida la información de todos los hosts y genera JSON y Excel.

### USO TÍPICO EN PRODUCCIÓN ###

Validar servicio masivamente
elastic_action=restart

Re enroll agentes comprometidos
elastic_action=reenroll

Re enroll y validar funcionamiento
elastic_action=reenroll_restart

### TROUBLESHOOTING ###

Servicio no existe
Validar instalación previa del Elastic Agent.

Token inválido
Regenerar token desde Fleet en Kibana.

Excel no se genera
Instalar dependencia Python openpyxl.
pip3 install openpyxl


### VERSIÓN ###
v1.0 Elastic Agent Unified Operational Playbook