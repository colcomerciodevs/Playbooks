# Proyecto Ansible - Creación de Usuarios con Llave SSH

## Descripción

Este proyecto permite crear usuarios de sistema operativo de forma automatizada mediante Ansible, configurando acceso por llave SSH y aplicando permisos básicos de seguridad sobre el directorio home, `.ssh` y `authorized_keys`.

El proyecto está diseñado para ser reutilizable. No está ligado a un usuario específico como `seti_monitor`; cualquier usuario futuro puede ser agregado modificando únicamente el archivo de variables correspondiente.

El caso inicial contempla la creación del usuario `seti_monitor`, requerido para tareas de observabilidad y monitoreo, con acceso de solo lectura a nivel de sistema operativo y sin privilegios administrativos.

---

## Alcance funcional

Este proyecto realiza las siguientes acciones:

- Crea grupos de sistema operativo.
- Crea usuarios en servidores Linux.
- Crea usuarios en servidores Solaris 11.
- Genera llaves SSH automáticamente en el nodo Ansible o AWX.
- Instala la llave pública en el archivo `authorized_keys` del usuario.
- Bloquea el acceso por contraseña.
- Aplica permisos seguros sobre:
  - Directorio home.
  - Directorio `.ssh`.
  - Archivo `authorized_keys`.
- Permite ejecutar sobre grupos específicos del inventario, por ejemplo:
  - Oracle.
  - MySQL.
  - Linux.
  - Solaris 11.

---

## Consideraciones de seguridad

Por defecto, el usuario creado queda con las siguientes características:

```text
Acceso por SSH: Sí
Acceso por contraseña: No
Sudo: No
Privilegios administrativos: No
Uso esperado: Consulta de métricas y monitoreo