📘 Proyecto Ansible: Creación de Usuarios por Zonas

Este proyecto permite crear usuarios en servidores Linux de manera organizada, diferenciando por zonas (ej. zona_norte, zona_centro, etc.).
Cada zona tiene su propio archivo de variables (vars/usuarios_zona_xxx.yml) que contiene la lista de usuarios a crear.

📂 Estructura de Carpetas
crear_usuarios/
├── crear_usuarios.yml           # Playbook principal
├── README.md                    # Documentación
└── vars/
    ├── usuarios_zona_norte.yml  # Usuarios zona norte
    ├── usuarios_zona_centro.yml # Usuarios zona centro
    ├── usuarios_zona_sur.yml    # (plantilla)
    └── usuarios_zona_occ.yml    # (plantilla)

⚙️ Funcionamiento del Playbook

Selecciona la zona al ejecutar el playbook con -e "zona=...".
Ejemplo:
ansible-playbook crear_usuarios_por_zonas.yml -e "zona=zona_norte"
ansible-playbook crear_usuarios_por_zonas.yml -e "zona=zona_centro"



El playbook:

Valida que exista el archivo vars/usuarios_{{ zona }}.yml.
Incluye la lista de usuarios definida en el archivo de la zona.
Crea el grupo base soporte (si no existe).
Crea cada usuario con su:
Nombre de usuario.
Descripción (comment).
Carpeta home (/home/usuario).
Grupo primario soporte.
Shell /bin/bash.
Contraseña inicial (hash sha512).
Fuerza el cambio de contraseña en el primer inicio de sesión (chage -d 0).