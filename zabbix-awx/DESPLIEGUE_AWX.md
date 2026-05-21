# Reporte de capacidad Zabbix — Proyecto para AWX

Extrae métricas de capacidad (vCPU, RAM, % uso promedio, umbrales) desde la
API de Zabbix y genera un Excel con hoja de datos + hoja Summary.
Ansible orquesta; Python hace la extracción de la API y el Excel.

Diseñado para subir a **AWX** como Proyecto + Job Template con **encuesta**
(survey) y **programación** (schedule).

## Estructura

```
zabbix-awx/
├── ansible.cfg
├── playbook.yml                     # entrypoint (sin vars_prompt; usa survey)
├── requirements.txt                 # deps Python (van en el Execution Environment)
├── execution-environment.yml        # para construir el EE con ansible-builder
├── collections/requirements.yml     # colecciones (AWX las instala al sincronizar)
├── awx/
│   ├── survey.json                  # encuesta: texto libre (grupos/IPs)
│   ├── survey_multiselect.json      # encuesta: multiselect de grupos + IPs extra
│   └── custom_credential_type.yml   # tipo de credencial -> inyecta ZABBIX_URL/TOKEN
└── roles/zabbix_report/
    ├── defaults/main.yml            # grupos_app, fechas (editar IPs reales aquí)
    ├── tasks/main.yml               # orquestación + set_stats (artefactos)
    └── files/
        ├── extraer_zabbix.py        # API Zabbix + trend/history + JSON + gzip
        └── procesar_reporte.py      # JSON gzip -> Excel (datos + Summary)
```

## Qué quedó en Ansible y qué en Python

| Etapa | Dónde |
|-------|-------|
| Entrada del usuario | **AWX Survey** (no `vars_prompt`) |
| Expandir grupos JD/PPS/GP + dedup en orden | Ansible (Jinja2) |
| Validar credenciales, carpetas, copiar scripts | Ansible |
| API Zabbix, resolver host, trend/history, triggers, gzip | Python `extraer_zabbix.py` |
| Promedios/máximos, regex de umbrales, bytes→GB, Excel | Python `procesar_reporte.py` |
| Publicar rutas de salida | Ansible `set_stats` (artefactos del job) |

---

## Despliegue en AWX (paso a paso)

### 1. Subir el proyecto
Sube esta carpeta a un repositorio Git y en AWX:
**Resources > Projects > Add** → SCM type Git → apunta al repo.
Al sincronizar, AWX instalará las colecciones de `collections/requirements.yml`.

### 2. Construir el Execution Environment (deps Python)
pandas/openpyxl/requests deben vivir en el EE. En una máquina con
`ansible-builder`:

```bash
cd zabbix-awx
ansible-builder build -t zabbix-report-ee:latest
# sube la imagen a tu registry, ej:
# docker tag zabbix-report-ee:latest registry.local/zabbix-report-ee:latest
# docker push registry.local/zabbix-report-ee:latest
```

En AWX: **Administration > Execution Environments > Add** → registra la imagen.

### 3. Crear el tipo de credencial y la credencial
- **Administration > Credential Types > Add**: copia INPUT e INJECTOR desde
  `awx/custom_credential_type.yml`.
- **Resources > Credentials > Add**: crea una credencial de ese tipo con tu
  URL y token de Zabbix.

### 4. Crear el Job Template
**Resources > Templates > Add > Job Template**:
- Inventory: Demo Inventory (o cualquiera; el playbook corre en localhost).
- Project: el del paso 1. Playbook: `playbook.yml`.
- Execution Environment: el del paso 2.
- Credentials: añade la credencial Zabbix del paso 3.
- Marca **Prompt on launch** si quieres.

### 5. Añadir la encuesta (survey)
En el Job Template → pestaña **Survey** → activa y añade los campos.
Puedes importar/replicar `awx/survey.json` (texto libre) o
`awx/survey_multiselect.json` (grupos por multiselect). El rol soporta
**ambos formatos** automáticamente.

### 6. Programar (schedule)
En el Job Template → pestaña **Schedules > Add**: define frecuencia
(ej. mensual el día 1 a las 07:00). Las respuestas por defecto de la encuesta
se usan en las ejecuciones programadas.

---

## Configuración de datos

Edita `roles/zabbix_report/defaults/main.yml` con tus **IPs reales** por grupo
(`grupos_app`). También puedes sobreescribir `grupos_app` desde las
**extra_vars** del Job Template sin tocar el código.

## Salida y entrega del Excel

El job deja en `dir_salida`: `Reporte_Zabbix_<fecha>.json`, `.json.gz` y `.xlsx`,
y publica sus rutas vía `set_stats` (visibles en los artefactos del job).

> En AWX el filesystem del job es **efímero**. Para conservar/entregar el Excel,
> encadena en un **Workflow Template** un segundo paso que lo entregue, por ej.:
> enviarlo por correo, subirlo a un share/S3, o copiarlo a un volumen
> persistente. Las rutas quedan disponibles como artefactos (`reporte_excel`).

## Prueba local (fuera de AWX)

```bash
pip install -r requirements.txt
export ZABBIX_URL="https://tu-zabbix/api_jsonrpc.php"
export ZABBIX_TOKEN="tu_token"
ansible-playbook -i 'localhost,' playbook.yml -e 'entrada_usuario=JD,PPS,10.0.0.99'
```
