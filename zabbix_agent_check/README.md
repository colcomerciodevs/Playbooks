Playbook: Instalación/Auditoría de Zabbix Agent 2 desde repositorio HTTP local

📌 Objetivo
Automatiza la verificación, desinstalación controlada e instalación de Zabbix Agent 2 (versión exacta) usando un repositorio HTTP local sin firmas, evitando dependencias de Internet/repocentros externos y generando un reporte JSON + Excel con el resultado por host.

🧩 Qué hace (resumen)
* Detecta versiones instaladas de zabbix-agent (v1) y zabbix-agent2 (v2).
* Decide si reinstalar v2 (si no existe o si la versión ≠ deseada).
* Desinstala sin consultar repos:
   RHEL/CentOS/Oracle: dnf/yum --disablerepo="*" --noplugins
   SLES: zypper --no-gpg-checks
   Fallback: rpm -e (último recurso si falla el gestor).
* Crea repos temporales hacia el repo HTTP local:
   RHEL/CentOS/Oracle: yum_repository sin GPG.
   SLES: escribe /etc/zypp/repos.d/zabbix-local.repo con gpgcheck=0 y repo_gpgcheck=0.
* Instala Zabbix Agent 2 con versión exacta solo desde el repo local:
   RHEL/CentOS/Oracle: yum con enablerepo=zabbix-local y disablerepo=*.
   SLES: zypper install -r zabbix-local zabbix-agent2=VERSION (sin firmas).
* Configura /etc/zabbix/zabbix_agent2.conf (template Ansible).
* Habilita e inicia el servicio zabbix-agent2.
* Limpia repos temporales.
* Reporta por host: JSON y Excel en Salidas_Playbooks/.

✅ Compatibilidad

Familia RedHat: RHEL / CentOS / Oracle Linux (7/8/9)
SUSE: SLES 12/15

La selección de ruta del repo se hace con facts:
.../el7/, .../el8/, .../el9/
.../sles12/, .../sles15/

📦 Requisitos del repositorio local
Servido por HTTP accesible para los hosts, ej.:
http://10.181.8.209:8080/repos/localrepo/zabbix2/

Cada subcarpeta debe contener metadata válida:
el7/      repodata/repomd.xml
el8/      repodata/repomd.xml
el9/      repodata/repomd.xml
sles12/   repodata/repomd.xml
sles15/   repodata/repomd.xml


Si no hay firmas, el playbook desactiva GPG check para ese repo temporal.


🔧 Variables clave

En el playbook:
zabbix_desired_version: "7.0.18"  # versión exacta a instalar
repo_base_url: "http://10.181.8.209:8080/repos/localrepo/zabbix2"

🗂️ Estructura sugerida del proyecto
zabbix_agent_check/
├── ansible.cfg
├── inventario.ini
├── zabbix_agent_checkV2.yml
├── files/
│   └── zabbix_agent2.conf.template
├── scripts/
│   └── generar_excel_zabbix.py
└── Salidas_Playbooks/
    ├── zabbix_auditoria.json
    └── zabbix_auditoria.xlsx

🧪 Inventario (ejemplo)

inventario.ini
[PRUEBA]
appidman ansible_host=10.10.10.11
ibm_audit ansible_host=10.10.10.12
appdespadock_prd ansible_host=10.10.10.13
soabogdis01 ansible_host=10.10.10.14
crm04_k8s ansible_host=10.10.10.15
ethical_hacking ansible_host=10.10.10.16
pos_historicos2 ansible_host=10.10.10.17
mford-new ansible_host=10.10.10.18

▶️ Ejecución
Desde la raíz del proyecto:
ansible-playbook -i inventario.ini zabbix_agent_checkV2.yml

🔄 Lógica e idempotencia (cómo lo hace)

Detección:
rpm -q zabbix-agent ⇒ captura versión v1 (si existe).
rpm -q --qf '%{VERSION}\n' zabbix-agent2 ⇒ captura versión v2.

Decisión reinstall_required:
true si v2 no está o si su versión ≠ zabbix_desired_version.

Desinstalación controlada:
Intenta con dnf/yum/zypper sin tocar repos ni plugins.
Si falla (o no aplica), fallback rpm -e.

Repo temporal:
RedHat-family: yum_repository con gpgcheck: no.
SLES: .repo con gpgcheck=0 y repo_gpgcheck=0 + zypper refresh.

Instalación forzada:
RedHat-family: yum name="zabbix-agent2-<vers>*" + enablerepo=zabbix-local + disablerepo=* + disable_gpg_check: yes.
SLES: zypper --no-gpg-checks install -r zabbix-local zabbix-agent2=<vers>.

Configuración + servicio:
Template a /etc/zabbix/zabbix_agent2.conf + handler de reinicio.
systemd para enabled + started.

Limpieza:
Borra el repo temporal (yum_repository state=absent o borrar .repo en SLES).

Reporte:
Junta resultados en resultados_zabbix (por host).
Exporta JSON (Salidas_Playbooks/zabbix_auditoria.json).
Ejecuta script Python que genera Excel.