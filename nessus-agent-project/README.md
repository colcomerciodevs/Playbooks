# nessus-agent-project
Despliegue **offline** del Tenable Nessus Agent para Linux (RHEL/OL 7/8/9, SLES 12/15, Debian/Ubuntu, Fedora).
- Usa **instaladores locales** en `installers/`
- Copia e instala **sin Internet** en cada host
- (Opcional) Vincula al Manager si hay reachability
- Genera **Excel** con resultados

## Uso rápido
1) Copia 1 instalador por subcarpeta en `installers/` (según distro/versión).
2) Ajusta variables (host/port/key/grupo) en `ansible/roles/nessus_agent_offline/vars/main.yml` o pásalas por `-e`.
3) Ejecuta el playbook de raíz:
   ```bash
   ansible-playbook deploy_nessus_offline.yml -l linux      -e nessus_try_link=true      -e nessus_manager_host=10.181.8.192 -e nessus_manager_port=8834      -e nessus_agent_key='***' -e nessus_agent_groups='corbeta'
   ```
4) Revisa el Excel en `Salidas_Playbooks/nessus/nessus_agent_reporte.xlsx`.
