# Guía de uso — Flos MES

## Configuración del entorno

### Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL | `postgresql+psycopg://flos_admin:flos_secure_password@localhost:5432/flos_core` |
| `EXCEL_DIR` | Directorio de archivos .xlsx | `.` (raíz del proyecto) |

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

### `POST /api/explosion`

Ejecuta el cálculo de explosión de materiales para una orden.

```json
{
  "orden_id": "ORD-001",
  "producto_codigo": "ES-001",
  "cantidad": 100
}
```

### `POST /api/inventario/cargar`

Carga los datos del archivo `inventario.xlsx` a la base de datos.

```json
{
  "archivo": "inventario.xlsx"
}
```

### `GET /api/inventario`

Consulta el inventario actual.

### `GET /api/productos`

Lista los productos disponibles.

## Desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en modo desarrollo
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
