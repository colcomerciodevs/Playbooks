## Ejecutar para cargar variables donde se guarda contraseña de llave privada para conexion servers OCI
source start_oci_ssh_agent_temp.sh

# 🔐 Auditoría de Usuarios Linux – Reporte Excel con Detalle de Permisos y Estado

Este playbook de Ansible, junto con el script Python `Generar_Excel_Users_CON_METODO.py`, genera un reporte completo en Excel de los usuarios reales en servidores Linux, incluyendo:

- UID, grupos, shell asignado
- Permisos sudo y comandos permitidos
- Validación de si el usuario está activo o no
- Método exacto de bloqueo (si aplica)

---

## 📌 ¿Qué hace este playbook?

1. Filtra usuarios reales: considera usuarios con `UID >= 1000` y excluye cuentas de sistema como `nobody`, `sshd`, `zabbix`, etc.

2. Recolecta información detallada para cada usuario:
   - `id usuario` → UID, GID, grupos secundarios
   - `sudo -lU usuario` → permisos sudo
   - `getent passwd` → shell configurado
   - `passwd -S` → estado de la cuenta (LK, NP, etc.)

3. Consolida todos los datos por host en un archivo JSON estructurado.

4. Ejecuta un script Python local que lee el JSON y genera un archivo Excel (`usuarios_permisos.xlsx`) con columnas como:

   | Host | Usuario | UID | Shell | Grupos | Tiene Sudo | Usuario Activo | Método de Bloqueo |
   |------|---------|-----|--------|--------|------------|----------------|--------------------|

---

## ⚙️ Validaciones implementadas

El script evalúa el estado del usuario en el siguiente orden:

### ✅ Activo (sin restricciones)
- Shell válido (ej. `/bin/bash`)
- UID >= 1000
- Contraseña habilitada

### 🟡 Activo solo con llave privada SSH
- Shell válido y UID ≥ 1000
- Pero `passwd -S` indica bloqueo (`LK`, `!!`, `*`, `NP`)

→ Se muestra como: `SÍ (solo llave privada SSH)`

### 🔴 Inactivo
- Shell inválido (`/sbin/nologin`, `/bin/false`, `shutdown`)
- UID < 1000
- O ambos

→ Se indica el primer método detectado como: `Shell`, `UID < 1000`, etc.

---

## 📥 Salida generada

El Excel se guarda en:

Salidas_Playbooks/usuarios_permisos.xlsx

Puedes filtrar fácilmente por ambiente, host, usuarios con sudo o inactivos.

---

## 🧑‍💻 Requisitos

- Ansible en la máquina de control
- Clave SSH válida hacia los servidores
- Python 3 + xlsxwriter en la máquina donde se ejecuta el script

---

## 🚀 Ejecución

Desde el directorio del playbook, ejecuta:

ansible-playbook view_user_permissions.yml

---

## 📁 Estructura esperada

view_user_permissions.yml  
Generar_Excel_Users_CON_METODO.py  
Salidas_Playbooks/  
└── usuarios_permisos.json  
└── usuarios_permisos.xlsx  

---

## ✍️ Autor

Automatizado por Ansible y Python  
Adaptado para ambientes Linux corporativos con auditorías de seguridad.
