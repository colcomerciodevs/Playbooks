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
- **Cuentas críticas protegidas** (`root`, `tux`, `adminso`, `ansible_test`, `iacolcoauto`, entre otras): no se crean, bloquean ni eliminan. Cambiar su contraseña exige escribir CONFIRMAR y no se permite con objetivo `all` ni comodines; su caducidad no se modifica (se ignoran «sin caducidad» y «forzar cambio»). Una cuenta con UID 0 también cuenta como crítica.
- **Llaves en un almacén persistente** (`/data/work/gestion_usuarios/keys`, grupo de instancias `Container_Group_Corbeta`). Cada usuario tiene su llave privada, `.pub` y `.ppk` (PuTTY v3, generado sin `puttygen`).
- **Plantillas separadas** (1a/1b y 2a/2b) para que cada encuesta muestre solo los campos que aplican. Los valores que distinguen cada plantilla van fijos en sus variables.
- **Acceso SSH al crear usuarios:** agrega al grupo `ssh_access` si existe, y a la línea `AllowUsers` de `sshd_config` si existe (validado con `sshd -t`).
- **Forzar cambio en bloque** (2b), con exclusión automática de cuentas críticas, cuentas de servicio (`cuentas_servicio` en `vars/comunes.yml`), shells no interactivos, cuentas expiradas y cuentas sin contraseña.
- **Verificación del cambio en los workflows:** la auditoría del último nodo revisa solo las cuentas que modificó el paso anterior (también en operaciones en bloque) y genera `verificacion_cambio_<fecha>.html/.csv` con la operación, el ticket y las cuentas no encontradas. La plantilla 3 sola sigue siendo la auditoría general.
- **Informe de auditoría en un solo Excel (.xlsx):** reemplaza al HTML y al CSV. Hojas Resumen, Usuarios, Hallazgos, Sudo, Detalle, Servidores y, en un workflow, No encontradas; con filtros y encabezado fijo. Lo genera el módulo `generar_excel` (solo biblioteca estándar de Python).
- **Excel más fácil de leer:** el Resumen explica cada cifra («Qué significa»), divide el sudo total en sin contraseña / con la propia / con la de root (antes «sudo completo» no incluía los de clave de root y no cuadraba con Detalle) y muestra los motivos por los que no se forzaría el cambio. Nueva hoja **Tipos de hallazgo** (qué significa, qué hacer, casos, servidores y cuentas). Severidades en color, «SÍ» con tilde, hostname e IP al final y columnas fijas en Detalle, Usuarios, Servidores y Sudo. Las explicaciones están en `roles/usuarios_auditoria/vars/main.yml`.
- **Hoja «Plan forzar cambio contraseña»:** prepara el cambio masivo (2b, UID ≥ 1000). Por usuario, una fila con los servidores donde SÍ se forzaría y una por cada motivo de NO, con justificación, indicios de cuenta de servicio, aplicación o automatización (nombre genérico, terminado en número, descripción de servicio, uso de llave SSH; configurables en `roles/usuarios_auditoria/vars/main.yml`) y recomendación (REVISAR, CONFIRMAR, APLICAR, EXCLUIDA, CORREGIR). La 2b omite sola las cuentas expiradas.
- **Hoja Usuarios:** una fila por usuario sumando todos los servidores, con títulos descriptivos: en cuántos existe y puede entrar, último acceso, hallazgo más grave, sudo y estado de la contraseña. La decisión del cambio forzado está solo en la hoja del plan; Detalle deja de repetir los comandos sudo (están en la hoja Sudo).
- **Informe del cambio en Excel (opciones 0, 1a, 1b, 2a, 2b y 4, solas o en su workflow):** cada cambio deja `<operación>_<fecha>.xlsx` en `/data/work/gestion_usuarios/reportes/` (ruta en la salida del job y en el artefacto `informe_cambio`). Hojas Resumen (lo pedido, ticket, quién lo lanzó, job, cifras y qué sigue), Por usuario (dónde se aplicó, dónde no y por qué), Detalle (resultado, motivo, verificación y estado de la cuenta ANTES y DESPUÉS) y Servidores (OK, falló durante el cambio con el error, o sin respuesta). No guarda contraseñas ni hashes. Si un servidor falla a mitad del cambio, se registra el error y el estado real de sus cuentas, el informe se genera igual y el job termina fallido. La auditoría (3) conserva su propio informe. Piezas comunes en `roles/usuarios_comun` (`informe_estado.yml`, `informe_fallo.yml`, `informe.yml`, `templates/informe_cambio.json.j2`); el módulo `generar_excel` pasa a `library/` para que lo usen todos los playbooks. La carpeta de reportes se crea al validar el objetivo, antes de tocar servidores.
- **2b en bloque omite las cuentas con un cambio forzado ya pendiente** (último cambio = 0): forzarlo otra vez no cambiaba nada e inflaba el informe. La auditoría usa la misma regla («Cambio forzado ya pendiente» en la hoja Plan y el Resumen). Con lista explícita se sigue aplicando.
- **Consola de la 2b:** «Omitidas en …» mostraba «key = value»; ahora muestra cada cuenta con su motivo.
- **Estado de la contraseña claro:** distingue activa, bloqueada, solo llave, sin inicio de sesión, sin contraseña ni llave y vacía, e indica si está vencida, con cambio pendiente o con la cuenta expirada.
- **Ayuda de "Servidores o grupo del inventario"** (12 encuestas): ejemplos en formato `[valor] efecto`; deja claro que varios grupos se separan con coma (`GEOPOS,PPU`).
- **Informes de auditoría:** muestran el hostname real (lo devuelve el servidor) y la IP (`ansible_host`) de cada servidor en el HTML, el CSV (columnas Hostname e IP) y la salida del job. A root y a las cuentas con UID 0 ya no se les marcan hallazgos de sudo ni de grupos privilegiados.
- **Manual de uso** (`docs/Manual_de_Uso.pdf`, fuente `docs/fuente/generar_manual.py`): guía para operadores con qué workflow lanzar, cómo llenar la encuesta, qué se detiene y qué se omite con cuentas críticas, de sistema y de aplicación, ejemplos y cómo leer el informe. Toma las cuentas protegidas, los perfiles y los IDs del proyecto.
- **Perfiles de cuenta (1a y 1b):** las preguntas "Nivel de sudo", "Comandos sudo permitidos" y "sudo sin contraseña" se reemplazan por "Perfil de la cuenta": `perfil_estandar` (sin sudo), `perfil_admin_linux` (sudo completo), `perfil_auditor_linux` (solo consulta) y `perfil_soporte_geopos` (status/start/stop/restart de los servicios Geopos). Se definen en `vars/perfiles.yml`; los catálogos usan el campo `perfil` (los campos `sudo*` ya no se aceptan). Cada programa se busca en el servidor y se omite si no existe. Con contraseña, sudo pide la del propio usuario (`Defaults:<usuario> !targetpw`, también en SUSE); con llave, NOPASSWD. La auditoría ya no marca "clave de root" cuando el usuario tiene `!targetpw`.
- **Servidores con S.O. obsoleto (Python 2.6):** todas las plantillas USUARIOS usan el EE `Corbeta AWX-EE-Legacy` (Ansible 2.9.27). Los servidores del grupo `legacy_ssh` (parte de `normalizados`) conectan con `ansible_test` y la llave RSA de la credencial `SSH RSA Legacy` (tipo `SSH Key - Legacy RSA`, variable `legacy_ssh_key_file`), con ssh-rsa habilitado en `group_vars/legacy_ssh.yml`. Nueva plantilla `USUARIOS | Test - Conexión legacy SSH` (ID 65, `test_conexion.yml`) para probar la conexión, porque los comandos ad hoc solo aceptan credenciales Machine. Verificado con Ansible 2.9.27: sintaxis, auditoría completa y de verificación, y generación de llaves y .ppk.
- **Servidores con Python 3.4 (SLES 12):** `MONGO-PRD-N1/N2/N3` usan `ansible_python_interpreter=/usr/bin/python2.7` en el inventario, porque ansible-core no soporta Python 3.4.
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
- **Plantilla 0:** confirmar que el entorno `Corbeta AWX-EE-Legacy` incluye `sshpass` (necesario para conectarse con contraseña) y probarla en un servidor legacy.
- **Servidores legacy:** probar en uno de ellos las plantillas que modifican (1a, 1b, 2a, 2b, 4); hasta ahora solo se probó la conexión (job 9798).
- **Permisos en AWX:** que solo `admin` apruebe, que los operadores tengan Execute en los workflows y no en las plantillas 1a, 1b, 2a, 2b y 4, y retirar a `srvinnops` los permisos temporales.
- **Normalizar** los servidores de `pendientes_normalizar` para que entren con `ansible_test`.
- `AllowUsers` definido en `/etc/ssh/sshd_config.d/` no se detecta; solo se edita el archivo principal.
- El campo `llave_publica` de los catálogos sigue disponible y usa una llave fuera del almacén.
- Revisar la lista `cuentas_servicio` con la auditoría de cada grupo de servidores.
