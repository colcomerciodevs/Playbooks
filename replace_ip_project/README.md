## 📂 Estructura General del Proyecto

project_root/
│
├ site.yml
├ ansible.cfg
│
├ inventories/
│ └ inventory.ini
│
├ roles/
│ └ replace_ip_host/
│ ├ defaults/
│ │ └ main.yml
│ │
│ ├ tasks/
│ │ ├ main.yml
│ │ ├ build_regex.yml
│ │ ├ find_files.yml
│ │ ├ process_files.yml
│ │ ├ one_file.yml
│ │ ├ summary.yml
│ │ └ report.yml
│
├ scripts/
│ └ genera_reporte_replace_ip.py
│
└ Salidas_Playbooks/


---

## 🧠 Arquitectura y Flujo General

site.yml
↓
Rol replace_ip_host
↓
build_regex.yml
↓
find_files.yml
↓
process_files.yml
↓
one_file.yml (por archivo)
↓
summary.yml
↓
report.yml
↓
JSON + HTML


---

## ⚙️ Variables Principales (defaults/main.yml)

### scan_root
Ruta donde se buscarán scripts.

Ejemplos:

/home
/app
/data/scripts


---

### old_ip
IP exacta a buscar y reemplazar.

Ejemplo:

10.181.0.77


---

### new_host
Hostname destino.

Ejemplo:

batch01


---

### file_patterns
Tipos de archivos a escanear.

Ejemplo:

*.sh
*.bash


---

### old_ip_regex
Regex opcional.

Si queda vacío → el rol construye regex exacto usando límites `\b` para evitar reemplazos parciales.

---

### capture_after_host_lines
Define si se guarda evidencia del hostname después del cambio.

No afecta el estado OK si está desactivado.

---

## 🔍 Lógica de Validación

El estado final depende principalmente de:

### 🟢 OK
La IP ya no existe después del replace.

### 🔴 FAIL
La IP sigue existiendo después del replace.

### ⚪ SKIPPED
El archivo nunca tuvo la IP.

---

## 🧪 Flujo de Validación por Archivo

### BEFORE
Busca la IP dentro del archivo usando:

grep -nE


Captura número de línea + contenido.

---

### MATCH FLAG
Determina si el archivo contiene la IP.  
Evita warnings de ansible-lint.

---

### REPLACE
Ejecuta reemplazo IP → Hostname usando módulo replace.  
Solo si existe coincidencia.

---

### AFTER VALIDATION IP
Verifica que la IP ya no exista.

Si desaparece → candidato a OK.

---

### AFTER VALIDATION HOSTNAME
Validación opcional.  
Solo evidencia visual.

---

### RESULT REGISTRATION
Construye objeto resultado con:

- Archivo  
- Before lines  
- After IP lines  
- After Host lines  
- Estado  
- Changed  

---

## 📊 Summary por Host

Incluye:

- Total archivos escaneados  
- Total archivos con IP  
- Total OK  
- Total FAIL  
- Total SKIPPED  
- Detalle por archivo  

---

## 📑 Generación de Reportes

El rol ejecuta automáticamente:

### JSON Consolidado

Salidas_Playbooks/replace_ip_report.json


---

### Reporte HTML Visual

Salidas_Playbooks/replace_ip_report.html


Incluye:

- Totales globales  
- Resultados por host  
- Resultados por archivo  
- Evidencia BEFORE / AFTER  

---

## 🐍 Script Python Reporte HTML

Archivo:

scripts/genera_reporte_replace_ip.py


Funciones:

- Leer JSON consolidado  
- Calcular totales globales  
- Renderizar HTML visual  
- Manejar valores numéricos de forma segura  

---

## ▶️ Ejecución del Proyecto

Modo simple:

ansible-playbook site.yml


---

Modo pasando variables manualmente:

ansible-playbook site.yml -e "scan_root=/home/carvajal old_ip=10.181.0.77 new_host=batch01"


---

## 🔁 Comportamiento Recursivo

La búsqueda de scripts es recursiva.

Configurado con:

recurse: true


Incluye subcarpetas automáticamente.

Ejemplo:

/home/scripts
/home/scripts/old
/home/scripts/tmp
/home/scripts/test/sub


---

## 📌 Notas Importantes

El estado OK depende principalmente de que la IP desaparezca del archivo.

El hostname se usa solo como evidencia visual.

El replace es exacto y evita coincidencias parciales.

---

## 👨‍💻 Autor

Infraestructura Linux