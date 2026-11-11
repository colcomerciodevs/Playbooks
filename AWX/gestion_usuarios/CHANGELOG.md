# Registro de cambios

## 1.0 — 2026-11-11

Primera versión estable de gestion_usuarios: gestión de usuarios Linux (sin LDAP) desde AWX,
con encuestas, aprobación previa y auditoría de verificación. La descripción completa está en
`docs/Arquitectura_Gestion_Usuarios.pdf`.

### Qué incluye

| Plantilla AWX | Qué hace | Workflow con aprobación |
|---|---|---|
| 0 - Relación de confianza | Crea o completa las cuentas de automatización `iacolcoauto` y `ansible_test` (llaves, sudo, acceso SSH). Se conecta con usuario y contraseña. | No |
| 1a - Crear con contraseña | Alta de usuarios con contraseña inicial. | Sí |
| 1b - Crear con llave | Alta de usuarios con llave SSH del almacén (se reutiliza o se crea, con su `.ppk`). | Sí |
| 2a - Cambiar contraseña | Asigna una contraseña nueva. | Sí |
| 2b - Forzar cambio de contraseña | Obliga a cambiarla en el próximo ingreso; admite catálogo o todas las cuentas UID ≥ 1000. | Sí |
| 3 - Auditoría | Reporte HTML y CSV de cuentas, contraseñas, llaves, último acceso y sudo. Solo lectura. | No (es el último nodo de todos los workflows) |
| 4 - Bloquear o eliminar | Bloquea, reactiva o elimina cuentas, con respaldo del home. | Sí |

### Cambios respecto a la versión anterior

- **Validación antes de tocar servidores.** Cada playbook valida la encuesta y verifica los servidores (solo lectura) antes de cambiar nada. Si algo falla, se detienen todos los servidores.
- **Cuentas críticas protegidas** (`root`, `tux`, `adminso`, `ansible_test`, `iacolcoauto`, entre otras): no se crean, bloquean ni eliminan. Cambiar su contraseña exige escribir CONFIRMAR y no se permite con objetivo `all` ni comodines. Una cuenta con UID 0 también cuenta como crítica.
- **Llaves en un almacén persistente** (`/data/work/gestion_usuarios/keys`, grupo de instancias `Container_Group_Corbeta`). Cada usuario tiene su llave privada, `.pub` y `.ppk` (PuTTY v3, generado sin `puttygen`).
- **Plantillas separadas** (1a/1b y 2a/2b) para que cada encuesta muestre solo los campos que aplican. Los valores que distinguen cada plantilla van fijos en sus variables.
- **Acceso SSH al crear usuarios:** agrega al grupo `ssh_access` si existe, y a la línea `AllowUsers` de `sshd_config` si existe (validado con `sshd -t`).
- **Forzar cambio en bloque** (2b), con exclusión automática de cuentas críticas, cuentas de servicio (`cuentas_servicio` en `vars/comunes.yml`), shells no interactivos y cuentas sin contraseña.
- **Auditoría:** avisa de contraseñas por vencer (cuentas de solo llave), separa el sudo real del sudo con clave de root (SUSE) y muestra a quién se le forzaría el cambio en bloque.
- **Grupos privilegiados prohibidos** al crear (`wheel`, `sudo`, `root`, `docker`…), y protección de cuentas de servicio (UID < 1000).
- **Sin secretos en los registros:** las lecturas de `/etc/shadow` y las contraseñas usan `no_log`.
- **Catálogos renombrados:** `admins_linux`, `cuentas_de_servicio`, `soporte_zona_norte`, `soporte_zona_centro`.
- **Inventario** separado en `normalizados` (entran con `ansible_test`) y `pendientes_normalizar` (aún con `tux` o `adminso`).

### Eliminado

- Publicación de llaves en Git y servidor custodio de llaves.
- Envío del reporte de auditoría por correo y copia a otro servidor.
- Llaves públicas pegadas en la encuesta.
- Pregunta "Detalle en la salida del job" de la auditoría.
- Catálogos `usuarios_generales` y de automatización (reemplazado por la plantilla 0).
- `awx/configurar_awx.yml` (AWX se configura directamente; ya no reflejaba la configuración real).
- Manual PDF anterior y su generador.

### Pendiente para 1.1

- **Pruebas reales** de cada plantilla en un servidor de prueba. Esta versión se validó de forma estática y con pruebas locales, sin ejecutarse contra servidores.
- **Plantilla 0:** confirmar que el entorno `Corbeta AWX-EE` incluye `sshpass` (necesario para conectarse con contraseña).
- **Permisos en AWX:** que solo `admin` apruebe, que los operadores tengan Execute en los workflows y no en las plantillas 1a, 1b, 2a, 2b y 4, y retirar a `srvinnops` los permisos temporales.
- **Normalizar** los servidores de `pendientes_normalizar` para que entren con `ansible_test`.
- `AllowUsers` definido en `/etc/ssh/sshd_config.d/` no se detecta; solo se edita el archivo principal.
- El campo `llave_publica` de los catálogos sigue disponible y usa una llave fuera del almacén.
- Revisar la lista `cuentas_servicio` con la auditoría de cada grupo de servidores.
