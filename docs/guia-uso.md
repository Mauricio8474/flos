# Guía de uso — Flos MES

## Configuración del entorno

### Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL | — (definido en `.env`) |
| `EXCEL_DIR` | Directorio de archivos .xlsx | `.` (raíz del proyecto) |

Copiar `.env.example` a `.env` y ajustar las credenciales antes de ejecutar.

### Docker Compose

```bash
# Iniciar solo la base de datos
docker compose up -d flos-db

# Iniciar todo (app + db)
docker compose up --build

# Detener servicios
docker compose down
```

## Archivos de datos

Los archivos Excel deben ubicarse en la raíz del proyecto:

| Archivo | Propósito |
|---|---|
| `ERP Metarom.xlsx` | Catálogo de productos, órdenes de producción, datos maestros |
| `formulas.xlsx` | Fórmulas y recetas para la explosión de materiales |
| `inventario.xlsx` | Stock actual de materias primas y materiales |

## Endpoints de la API

### `POST /produccion/cargar-formulas`

Carga todas las fórmulas desde `formulas.xlsx` a la base de datos.

### `POST /produccion/cargar-inventario`

Carga un archivo Excel de inventario a la base de datos.

- **archivo:** Excel con columnas `SKU`, `Nombre`, `Cantidad_KG`

### `GET /produccion/inventario`

Consulta el inventario actual en la base de datos.

### `GET /produccion/formulas`

Lista todas las fórmulas disponibles en la base de datos.

### `POST /produccion/formulas`

Crea una nueva fórmula en la base de datos.

```json
{
  "id": "F-001",
  "nombre": "Mi Formula",
  "componentes": [{"sku": "MP001", "porcentaje": 60}]
}
```

### `PUT /produccion/formulas/{id}`

Actualiza una fórmula existente.

### `DELETE /produccion/formulas/{id}`

Elimina una fórmula.

### `POST /produccion/calcular-explosion`

Ejecuta el cálculo de explosión de materiales. **No necesita archivo Excel** — el inventario debe estar precargado en la base de datos.

| Parámetro | Tipo | Descripción |
|---|---|---|
| `id_formula` | string | ID de la fórmula en BD |
| `cantidad_a_producir_kg` | float | Cantidad a producir |

### `POST /produccion/calcular-explosion/batch`

Ejecuta múltiples explosiones en una sola llamada.

```json
[
  {"id_formula": "AMC2705", "cantidad": 100},
  {"id_formula": "AM2494", "cantidad": 50}
]
```

### `POST /produccion/calcular-explosion/excel`

Descarga el resultado como archivo `.xlsx`.

### `POST /produccion/calcular-explosion/pdf`

Descarga el resultado como archivo `.pdf`.

### `GET /produccion/auditoria`

Consulta el historial de cambios en fórmulas e inventario.

## Flujo de trabajo

```bash
# 1. Cargar fórmulas desde Excel a la BD
curl -X POST http://localhost:8000/produccion/cargar-formulas \
  -H "X-API-Key: flos-dev-key-2026"

# 2. Cargar inventario desde Excel a la BD
curl -X POST http://localhost:8000/produccion/cargar-inventario \
  -H "X-API-Key: flos-dev-key-2026" \
  -F "archivo=@inventario.xlsx"

# 3. Consultar fórmulas disponibles
curl http://localhost:8000/produccion/formulas \
  -H "X-API-Key: flos-dev-key-2026"

# 4. Ejecutar explosión
curl -X POST http://localhost:8000/produccion/calcular-explosion \
  -H "X-API-Key: flos-dev-key-2026" \
  -d "id_formula=AMC2705&cantidad_a_producir_kg=100"
```

## Desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en modo desarrollo
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
