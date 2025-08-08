
# 📄 README - Recolección de Permisos de Usuarios Solaris

Este proyecto consta de un **playbook de Ansible** y un **script Python** que trabajan juntos para recolectar información sobre usuarios locales en servidores **Solaris 11**, verificar sus pertenencias a grupos y privilegios sudo, y exportar esta información en un archivo **Excel (.xlsx)** de forma estructurada para propósitos de auditoría o cumplimiento.

---

## 🧰 Archivos Principales

### 1. `view_user_permissions-SOLARIS.yml`
Playbook de Ansible que ejecuta tareas remotas en servidores Solaris:

- **Recolecta usuarios reales** (UID >= 100 y < 65534) desde `/etc/passwd`, excluyendo cuentas del sistema.
- Por cada usuario identificado:
  - Ejecuta el comando `id` para obtener UID y grupos.
  - Revisa `/etc/sudoers` y `/etc/sudoers.d/` para determinar si tiene permisos `sudo`.
- Agrupa esta información por host y la guarda en un archivo JSON llamado:
  ```
  Salidas_Playbooks/usuarios_permisos_solaris.json
  ```

### 2. `Generar_Excel_Users_Solaris.py`
Script Python que procesa el archivo JSON generado por el playbook y crea un Excel con toda la información.

#### El Excel incluye las siguientes columnas:
- `Host`: nombre del servidor.
- `IP`: dirección IP del host.
- `Ambiente`: valor del inventario (dev, qa, prod, etc.).
- `Grupo(s) Inventario`: grupos de Ansible a los que pertenece el host.
- `Usuario`: nombre del usuario.
- `UID`: ID de usuario.
- `Grupos`: grupos Unix a los que pertenece.
- `Tiene Sudo`: indica si tiene permisos sudo (`SÍ`, `NO`, `Desconocido`).
- `Comandos Permitidos`: comandos específicos permitidos por sudoers.
- `Usuario Activo`: evaluación de si el usuario está activo o no.

---

## 🧠 ¿Cómo se determina si un usuario está activo?

El script Python evalúa lo siguiente:

1. Si el usuario pertenece a grupos como `nologin`, `false`, `shutdown`, se considera **inactivo**.
2. Si el UID es mayor o igual a `65000` (normalmente usado por usuarios del sistema), también se considera **inactivo**.
3. En los demás casos, se considera **activo**.

---

## ▶️ Ejecución

1. Ejecuta el playbook de Ansible:
```bash
ansible-playbook view_user_permissions-SOLARIS.yml
```

2. Esto generará el archivo `usuarios_permisos_solaris.json` dentro de `Salidas_Playbooks/`.

3. El playbook ejecutará automáticamente el script Python que generará el archivo Excel:
```
Salidas_Playbooks/usuarios_permisos_solaris.xlsx
```

---

## 📁 Requisitos

- Python 3.x
- Paquete `xlsxwriter` para Python:
```bash
pip3 install xlsxwriter
```

- Ansible instalado en el controlador
- Acceso `become` habilitado para los servidores Solaris

---

## 📌 Observaciones

- Este script está orientado a entornos Solaris 11.
- Se recomienda revisar manualmente usuarios con UID alto o nombres atípicos si la lógica no cubre todos los casos de tu entorno.

---
