# Auditoría curl / libcurl — Validación Solicitud Ciber

## Contexto

- El área de Ciberseguridad identificó múltiples vulnerabilidades asociadas a curl / libcurl.
- Estas vulnerabilidades pueden impactar servicios que utilicen esta biblioteca para:

- HTTP / HTTPS  
- LDAP / LDAPS  
- SSH / SCP / SFTP  
- Integraciones con APIs  
- Automatizaciones con tokens OAuth  

---

## Vulnerabilidades Reportadas

### CVEs identificadas

- CVE-2025-13034  
- CVE-2025-14017  
- CVE-2025-14524  
- CVE-2025-14819  
- CVE-2025-15079  
- CVE-2025-15224  

---

## Rango de Versiones Vulnerables

curl 7.17.0 hasta 8.17.0 (inclusive)


---

## Sistemas Cubiertos

- CentOS 7  
- RedHat Enterprise Linux 7  
- RedHat Enterprise Linux 8  
- Oracle Linux 8  
- Oracle Linux 9  
- SLES 15 SP4  
- SLES 15 SP5  

---

## Objetivo del Playbook

- Identificar si curl / libcurl está instalado  
- Obtener versión instalada  
- Detectar backend criptográfico:
  - OpenSSL  
  - GnuTLS  
  - NSS  
- Detectar soporte de protocolos:
  - LDAP / LDAPS  
  - SFTP  
  - SCP  
- Detectar indicios de librerías:
  - libssh  
  - libssh2  
- Validar contra rango vulnerable informado por Ciber  
- Generar evidencia técnica en JSON y Excel  

---

## Evidencias Generadas

### JSON Técnico

Salidas_Playbooks/curl_audit.json


- Contiene información técnica detallada por servidor.

---

### Excel Ejecutivo (Respuesta para Ciber)

Salidas_Playbooks/curl_audit_report.xlsx


- Incluye:
  - Datos del servidor  
  - Versiones detectadas  
  - Backend detectado  
  - Indicios de protocolos soportados  
  - Evaluación contra rango vulnerable  

### Columna Clave

VERSION AFECTADA


- SI → Rojo  
- NO → Verde  

---

## Relación con Solicitud de Ciber

### 1. curl / libcurl instalado

- Validación:
  - Detección binario curl
  - Validación paquete instalado
- Resultado en Excel:
  - Curl Instalado
  - Ciber Q1

---

### 2. Aplicaciones con libcurl embebido

- Limitación técnica:
  - No se puede confirmar solo desde sistema operativo.
- Resultado en Excel:
  - REQUIERE VALIDACION APP

---

### 3. Uso backend libssh o GnuTLS

- Validación:
  - salida curl -V
- Resultado en Excel:
  - Usa GnuTLS
  - Usa libssh / libssh2
  - Ciber Q3

---

### 4. Uso tokens OAuth mediante curl

- Limitación técnica:
  - Depende de aplicación / scripts
- Resultado en Excel:
  - REQUIERE VALIDACION APP

---

### 5. Integraciones LDAP o SFTP automatizadas

- Validación como indicio:
  - Protocolos soportados por curl
- Resultado en Excel:
  - Soporta LDAP
  - Soporta SFTP
  - Ciber Q5

---

## Estructura del Proyecto

playbook/
├ curl_audit.yml
├ curl_audit_to_excel.py
├ inventario.ini
└ Salidas_Playbooks/
├ curl_audit.json
└ curl_audit_report.xlsx


---

## Requisitos

### En servidores auditados

- Acceso SSH
- Permisos sudo (si aplica)

---

### En nodo controlador / AWX

- Python 3
- Librería openpyxl

Instalación:

pip3 install openpyxl


---

## Ejecución

ansible-playbook -i inventario.ini curl_audit.yml


---

## Interpretación del Resultado

### VERSION AFECTADA = SI

- Versión dentro del rango vulnerable
- Requiere actualización o mitigación

---

### VERSION AFECTADA = NO

- Versión fuera del rango vulnerable
- No vulnerable según CVEs reportadas

---

## Consideraciones de Seguridad

- El análisis es a nivel sistema operativo.
- Validaciones de aplicaciones requieren revisión adicional.

---

## Uso del Resultado

- Respuesta formal a Ciberseguridad  
- Evidencia para auditoría  
- Gestión de vulnerabilidades  
- Planes de remediación  