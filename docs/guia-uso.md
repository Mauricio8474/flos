# Guía de uso — Flos MES

## Configuración del entorno

### Variables de entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL | — (definido en `.env`) |
| `JWT_SECRET` | Clave secreta para firmar tokens JWT | `flos-secret-key-change-in-production` |
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

## Dashboard Web

La interfaz para el personal está en `http://localhost:8000/dashboard/`.

### Login

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `123456789` | Administrador (control total) |

El usuario `admin` se crea automáticamente al iniciar la app si no existe.

### Roles y permisos

| Sección | admin | ingenieria | almacen | produccion | consultor |
|---|---|---|---|---|---|
| Dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fórmulas (ver) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Fórmulas (crear/editar/eliminar) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cargar fórmulas desde Excel | ✅ | ✅ | ❌ | ❌ | ❌ |
| Inventario (ver) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Inventario (cargar Excel) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Explosión (calcular) | ✅ | ✅ | ❌ | ✅ | ❌ |
| Descargar Excel/PDF | ✅ | ✅ | ✅ | ✅ | ❌ |
| Auditoría | ✅ | ❌ | ❌ | ❌ | ❌ |
| Usuarios (CRUD) | ✅ | ❌ | ❌ | ❌ | ❌ |

## API REST

Todas las llamadas a la API requieren autenticación JWT.

### Autenticación

```bash
# Obtener token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "123456789"}'

# Respuesta:
# {"access_token": "...", "token_type": "bearer", "rol": "admin", "nombre": "Administrador"}
```

Usar el token en cada petición:

```bash
curl http://localhost:8000/produccion/formulas \
  -H "Authorization: Bearer <token>"
```

### Usuarios (solo admin)

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/usuarios` | Listar usuarios |
| `POST` | `/usuarios` | Crear usuario |
| `PUT` | `/usuarios/{username}` | Actualizar usuario |
| `DELETE` | `/usuarios/{username}` | Desactivar usuario |

```json
// POST /usuarios
{
  "username": "jperez",
  "password": "mi-clave",
  "rol": "ingenieria",
  "nombre": "Juan Pérez"
}
```

### Fórmulas

| Método | Endpoint | Permiso |
|---|---|---|
| `GET` | `/produccion/formulas` | Todos autenticados |
| `GET` | `/produccion/formulas/{id}` | Todos autenticados |
| `POST` | `/produccion/formulas` | admin, ingenieria |
| `PUT` | `/produccion/formulas/{id}` | admin, ingenieria |
| `DELETE` | `/produccion/formulas/{id}` | admin, ingenieria |
| `POST` | `/produccion/cargar-formulas` | admin, ingenieria |

```json
// POST /produccion/formulas
{
  "id": "F-001",
  "nombre": "Mi Formula",
  "componentes": [{"sku": "MP001", "porcentaje": 60}]
}
```

### Inventario

| Método | Endpoint | Permiso |
|---|---|---|
| `POST` | `/produccion/cargar-inventario` | admin, ingenieria, almacen |
| `GET` | `/produccion/inventario` | Todos autenticados |

### Explosión de materiales

| Método | Endpoint | Permiso |
|---|---|---|
| `POST` | `/produccion/calcular-explosion` | admin, ingenieria, produccion |
| `POST` | `/produccion/calcular-explosion/batch` | admin, ingenieria, produccion |
| `POST` | `/produccion/calcular-explosion/excel` | admin, ingenieria, almacen, produccion |
| `POST` | `/produccion/calcular-explosion/pdf` | admin, ingenieria, almacen, produccion |

```bash
# Explosión simple
curl -X POST http://localhost:8000/produccion/calcular-explosion \
  -H "Authorization: Bearer <token>" \
  -d "id_formula=AMC2705&cantidad_a_producir_kg=100"

# Explosión batch
curl -X POST http://localhost:8000/produccion/calcular-explosion/batch \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[{"id_formula": "AMC2705", "cantidad": 100}, {"id_formula": "AM2494", "cantidad": 50}]'

# Descargar Excel
curl -X POST http://localhost:8000/produccion/calcular-explosion/excel \
  -H "Authorization: Bearer <token>" \
  -d "id_formula=AMC2705&cantidad_a_producir_kg=100" \
  -o explosion.xlsx

# Descargar PDF
curl -X POST http://localhost:8000/produccion/calcular-explosion/pdf \
  -H "Authorization: Bearer <token>" \
  -d "id_formula=AMC2705&cantidad_a_producir_kg=100" \
  -o explosion.pdf
```

### Auditoría (solo admin)

| Método | Endpoint |
|---|---|
| `GET` | `/produccion/auditoria?limite=100` |

## Flujo de trabajo

```bash
# 1. Obtener token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456789"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Cargar fórmulas desde Excel a la BD
curl -X POST http://localhost:8000/produccion/cargar-formulas \
  -H "Authorization: Bearer $TOKEN"

# 3. Cargar inventario desde Excel a la BD
curl -X POST http://localhost:8000/produccion/cargar-inventario \
  -H "Authorization: Bearer $TOKEN" \
  -F "archivo=@inventario.xlsx"

# 4. Consultar fórmulas disponibles
curl http://localhost:8000/produccion/formulas \
  -H "Authorization: Bearer $TOKEN"

# 5. Ejecutar explosión
curl -X POST http://localhost:8000/produccion/calcular-explosion \
  -H "Authorization: Bearer $TOKEN" \
  -d "id_formula=AMC2705&cantidad_a_producir_kg=100"

# 6. Ver auditoría (solo admin)
curl http://localhost:8000/produccion/auditoria \
  -H "Authorization: Bearer $TOKEN"
```

## Desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en modo desarrollo
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```
