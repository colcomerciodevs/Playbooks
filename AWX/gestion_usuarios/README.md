# gestion_usuarios

Gestión de usuarios Linux con Ansible y AWX: crear usuarios con un perfil de permisos, cambiar contraseñas, auditar cuentas y permisos sudo, y bloquear, reactivar o eliminar cuentas.

**Documentación:**
- [docs/Manual_de_Uso.pdf](docs/Manual_de_Uso.pdf): para quien lanza los workflows. Qué lanzar, cómo llenar la encuesta, qué pasa con las cuentas críticas y cómo leer el resultado.
- [docs/Arquitectura_Gestion_Usuarios.pdf](docs/Arquitectura_Gestion_Usuarios.pdf): detalle técnico. Cada encuesta, los comandos que ejecuta, los IDs de AWX y los servidores con S.O. obsoleto (Python 2.6).

Para regenerar los PDF después de cambiar encuestas, perfiles (`vars/perfiles.yml`) o cuentas protegidas (`vars/comunes.yml`):

```
python3 awx/generar_encuestas.py
python3 -B docs/fuente/generar_arquitectura.py
python3 -B docs/fuente/generar_manual.py
```

Los servidores con S.O. obsoleto se prueban con la plantilla `USUARIOS | Test - Conexión legacy SSH` (`test_conexion.yml`).
