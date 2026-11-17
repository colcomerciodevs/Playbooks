# gestion_usuarios

Gestión de usuarios Linux con Ansible y AWX: crear usuarios, cambiar contraseñas, auditar cuentas y permisos sudo, y bloquear, reactivar o eliminar cuentas.

**La documentación está en [docs/Arquitectura_Gestion_Usuarios.pdf](docs/Arquitectura_Gestion_Usuarios.pdf).**

Para regenerarla después de cambiar las encuestas: `python3 -B docs/fuente/generar_arquitectura.py`

Servidores con S.O. obsoleto (Python 2.6): ver la última sección del PDF. Se prueban con la plantilla `USUARIOS | Test - Conexión legacy SSH` (`test_conexion.yml`).
