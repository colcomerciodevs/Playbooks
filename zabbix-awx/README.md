# Reporte de Capacidad Zabbix — Proyecto AWX

Proyecto de automatización que extrae métricas de capacidad de infraestructura
desde la **API de Zabbix** y genera un **reporte en Excel** con los datos por
máquina y un resumen ejecutivo. Está diseñado para ejecutarse desde **AWX**
mediante un Job Template con encuesta y programación.

La arquitectura es híbrida: **Ansible orquesta** (entrada del usuario,
expansión de grupos, encadenado de etapas, publicación de resultados) y
**Python procesa** (llamadas a la API, cálculo de métricas, generación del
Excel), porque cada herramienta hace lo que mejor sabe hacer.

---

## ¿Qué hace, en una frase?

A partir de unos grupos/IPs y un rango de fechas, consulta Zabbix por el uso de
CPU, RAM, número de vCPU y memoria total de cada máquina, calcula promedios y
detecta umbrales configurados, y entrega todo en un Excel con dos hojas.

---

## Métricas que recolecta

Por cada máquina consultada, el reporte obtiene:

| Métrica | Descripción |
|--------|-------------|
| **Number of CPUs/Cores** | Cantidad de vCPU/núcleos asignados |
| **Total memory** | Memoria RAM total (convertida a GB) |
| **CPU utilization** | % de uso de CPU (promedio del periodo) |
| **Memory utilization** | % de uso de RAM (promedio del periodo) |
| **Umbrales (triggers)** | Umbrales de alerta configurados en Zabbix para CPU/RAM |

---

## El flujo, etapa por etapa

El proyecto reproduce y reorganiza la lógica de un script Python original,
repartida ahora entre Ansible y dos scripts de Python.

### Etapa 0 — Entrada (Ansible)
La **encuesta de AWX** recoge qué máquinas reportar y el rango de fechas.
Soporta **dos formatos de encuesta** de forma transparente:

- **Texto libre**: un solo campo `entrada_usuario` donde se escribe, por
  ejemplo, `JD,PPS,10.0.0.99` (grupos e IPs mezclados).
- **Multiselect**: un selector de grupos `grupos_seleccionados` más un campo
  de texto opcional `objetivos_extra` para IPs sueltas.

El rol detecta automáticamente cuál se usó y unifica ambas en una sola entrada;
no hay que tocar código para cambiar de una a otra.

### Etapa 1 — Expansión de objetivos (Ansible)
Convierte la entrada en una lista plana de máquinas:
- Los **grupos** (JD, PPS, GP) se expanden a sus IPs según `grupos_app`.
- Las **IPs/nombres sueltos** se añaden tal cual.
- Se **eliminan duplicados preservando el orden** de aparición.

Esto reemplaza el bloque `objetivos_ordenados` del script original.

### Etapa 2 — Extracción desde Zabbix (Python: `extraer_zabbix.py`)
Para cada máquina:
1. **Resuelve el host** en Zabbix: primero busca por IP; si no aparece, por nombre.
2. **Busca los items** de las métricas requeridas (búsqueda flexible por nombre).
3. **Decide la fuente de datos automáticamente**:
   - Si el rango es **mayor a 3 días** usa `trend.get` (tendencias, más eficiente).
   - Si es **igual o menor** usa `history.get` (historial detallado).
4. **Lee los umbrales** (`trigger.get`) para las métricas de utilización y
   extrae la condición numérica con una expresión regular.

El resultado crudo se guarda en **dos archivos**:
- `Reporte_Zabbix_<fecha>.json` — JSON puro.
- `Reporte_Zabbix_<fecha>.json.gz` — el mismo JSON comprimido en **gzip**.

Esta etapa **no genera Excel**; solo extrae y serializa datos.

### Etapa 3 — Procesamiento y Excel (Python: `procesar_reporte.py`)
Lee el **JSON comprimido**, y a partir de los datos crudos:
- Calcula **promedio y máximo** de cada serie de valores.
- Convierte la memoria de **bytes a GB**.
- Formatea los **umbrales** detectados en texto legible.
- Genera el **Excel** con dos hojas:
  - **`Metricas_Infraestructura`**: una fila por máquina (nombre, IP, servicio,
    memoria, % RAM, vCPU, % CPU, umbrales).
  - **`Summary`**: totales y promedios globales (máquinas procesadas, total de
    vCPU, promedio de uso CPU/RAM, tráfico de red consumido por la consulta).

### Etapa 4 — Publicación de resultados (Ansible)
Las rutas de los archivos generados se publican como **artefactos del job**
(`set_stats`), de modo que sean visibles en AWX y puedan encadenarse en un
**Workflow Template** para un paso posterior de entrega.

---

## Estructura del proyecto

```
zabbix-awx/
├── ansible.cfg                      # Configuración de Ansible
├── playbook.yml                     # Punto de entrada (corre en localhost)
├── requirements.txt                 # Dependencias Python (van en el EE)
├── execution-environment.yml        # Definición del EE (ansible-builder)
├── collections/requirements.yml     # Colecciones Ansible
├── awx/
│   ├── survey.json                  # Encuesta: texto libre
│   ├── survey_multiselect.json      # Encuesta: multiselect + IPs extra
│   └── custom_credential_type.yml   # Tipo de credencial (inyecta URL/token)
└── roles/zabbix_report/
    ├── defaults/main.yml            # grupos_app, fechas, rutas (CONFIGURAR)
    ├── tasks/main.yml               # Orquestación de las etapas
    └── files/
        ├── extraer_zabbix.py        # Extracción API + gzip (Etapa 2)
        └── procesar_reporte.py      # Procesamiento + Excel (Etapa 3)
```

---

## Reparto Ansible / Python

| Responsabilidad | Dónde | Por qué |
|-----------------|-------|---------|
| Entrada del usuario | AWX Survey | Reemplaza el `input()` interactivo |
| Expandir grupos + dedup en orden | Ansible (Jinja2) | Lógica simple de listas |
| Validar credenciales, carpetas, encadenado | Ansible | Orquestación |
| API Zabbix, host, trend/history, triggers, gzip | Python | Lógica condicional dinámica |
| Promedios, regex de umbrales, bytes→GB, Excel | Python | Cálculo y generación de archivos |
| Publicar rutas de salida | Ansible (`set_stats`) | Artefactos del job |

---

## Configuración

### Grupos de aplicación y fechas
Edita `roles/zabbix_report/defaults/main.yml`:

```yaml
grupos_app:
  JD:  ["10.0.0.11", "10.0.0.12"]
  PPS: ["10.0.0.21", "10.0.0.22"]
  GP:  ["10.0.0.31"]

fecha_inicio: "2026-04-01 00:00:00"
fecha_fin:    "2026-04-30 23:59:59"
```

> Sustituye las IPs de ejemplo por las reales de tu entorno. También puedes
> sobrescribir `grupos_app` desde las *extra_vars* del Job Template.

### Credenciales
En AWX, una **Custom Credential** (tipo definido en
`awx/custom_credential_type.yml`) inyecta como variables de entorno:

- `ZABBIX_URL` — ej. `https://zabbix.empresa.com/api_jsonrpc.php`
- `ZABBIX_TOKEN` — token de API de Zabbix

El playbook verifica que ambas existan antes de ejecutar.

---

## Salida

Cada ejecución produce tres archivos con marca de tiempo:

| Archivo | Contenido |
|---------|-----------|
| `Reporte_Zabbix_<fecha>.json` | Datos crudos (JSON puro) |
| `Reporte_Zabbix_<fecha>.json.gz` | Datos crudos comprimidos (gzip) |
| `Reporte_Zabbix_<fecha>.xlsx` | Reporte final (hojas *Metricas* + *Summary*) |

> **Nota sobre AWX:** el sistema de archivos de un job es **efímero** —
> al terminar, los archivos se eliminan. Sus rutas quedan publicadas como
> artefactos, pero para **conservar o entregar** el Excel hay que añadir un
> paso posterior (correo, copia a un recurso compartido, S3, etc.),
> normalmente encadenado en un Workflow Template.

---

## Ejecución local de prueba (fuera de AWX)

```bash
pip install -r requirements.txt
export ZABBIX_URL="https://tu-zabbix/api_jsonrpc.php"
export ZABBIX_TOKEN="tu_token"
ansible-playbook -i 'localhost,' playbook.yml -e 'entrada_usuario=JD,PPS,10.0.0.99'
```

Los scripts Python también pueden ejecutarse por separado:

```bash
# Solo procesamiento, sobre un JSON ya extraído:
python3 roles/zabbix_report/files/procesar_reporte.py \
  --input Reporte_Zabbix_xxx.json.gz \
  --output Reporte_Zabbix_xxx.xlsx
```

---

## Requisitos

- **Ansible** (núcleo) y colecciones de `collections/requirements.yml`.
- **Python 3** con: `requests`, `urllib3`, `pandas`, `openpyxl`, `python-dotenv`.
- En AWX, estas dependencias Python deben ir en un **Execution Environment**
  construido con `ansible-builder` (no se instalan en tiempo de ejecución).
- Acceso de red desde el ejecutor hacia la API de Zabbix.

---

## Documentación relacionada

- **`DESPLIEGUE_AWX.md`** — guía paso a paso para integrar el proyecto en AWX
  (proyecto, Execution Environment, credencial, Job Template, encuesta y schedule).
