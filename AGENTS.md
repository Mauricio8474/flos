# AGENTS.md — Flos MES

## Proyecto
- **Nombre:** Flos
- **Propósito:** Sistema MES (Manufacturing Execution System) para producción de esencias.
- **Arquitectura:** Hexagonal (DDD — Domain-Driven Design)

## Stack
- **Backend:** Python 3.12+, FastAPI
- **Base de datos:** PostgreSQL 15 (vía SQLAlchemy)
- **Lectura de datos fuente:** OpenPyXL / Pandas (archivos `.xlsx`)
- **Infraestructura:** Docker Compose (PostgreSQL + app)
- **Archivos data actuales:**
  - `ERP Metarom.xlsx` — Módulo ERP
  - `formulas.xlsx` — Lógica de cálculos
  - `inventario.xlsx` — Control de inventario

## Estructura del proyecto

```
flos/
├── AGENTS.md
├── docker-compose.yml
├── ERP Metarom.xlsx
├── formulas.xlsx
├── inventario.xlsx
├── ejemplo_batch.xlsx
├── test_excel_batch.py
└── src/
    ├── __init__.py
    ├── main.py                       # FastAPI — Composition root
    ├── application/
    │   ├── __init__.py
    │   └── use_cases.py              # Ports + casos de uso
    ├── domain/
    │   ├── __init__.py
    │   ├── models.py                 # Entidades puras de negocio
    │   └── services.py               # Lógica de dominio (MRP, alertas, sugerencias)
    └── infrastructure/
        ├── __init__.py
        ├── auth.py                   # JWT + autenticación
        └── adapters/
            ├── __init__.py
            ├── excel_reader.py       # Lector de Excel (OpenPyXL / Pandas)
            └── repositories.py       # PostgreSQL + SQLAlchemy + migraciones
```

## URLs
- **Frontend (Dashboard):** `http://localhost:8001/dashboard/`
- **API base:** `http://localhost:8001/`
- **Documentación OpenAPI:** `http://localhost:8001/docs`

## Convenciones generales
- **Idioma:** Español para nombres de archivos y documentación; código y commits en inglés.
- **Commits:** Prefijo conventional commit en inglés (`feat:`, `fix:`, `refactor:`, `docs:`).
- **Documentación:** Archivos `.md` en español.

## AI Agent Instructions
- No modificar archivos `.xlsx` directamente sin verificar antes el contenido.
- La capa `domain/` debe ser pura: sin dependencias externas (no importar FastAPI, SQLAlchemy, Pandas, etc.).
- Los adapters en `infrastructure/` implementan puertos definidos en `domain/` o `application/`.
- `main.py` es el composition root: aquí se instancian y conectan todas las dependencias.

## Progress

### Done
- **Proyecto base:** Scaffold hexagonal con domain/application/infrastructure
- **Modelos:** Formula, ComponenteFormula, ItemInventario, ResultadoExplosion, ControlCalidad, LoteProduccion, AlertaStock, SugerenciaCompra
- **Servicios:** CalculadorMRP (explosión con notas para SKUs faltantes), GeneradorAlertasStock, GeneradorSugerenciasCompra
- **Excel:** Adaptadores configurables para inventario (simple + SIIGO) y fórmulas
- **Persistencia:** PostgresRepositorioFormula, Inventario, Auditoria, Usuario, Ordenes, ControlCalidad, Lotes
- **Auth:** JWT con bcrypt/passlib, 5 roles (admin/ingenieria/almacen/produccion/consultor), seed automático de admin
- **CRUD:** Fórmulas (individual + Excel), inventario (individual + Excel SIIGO), usuarios (admin)
- **Explosión MRP:** Simple, batch JSON, batch Excel — auto-guarda órdenes, descarga Excel/PDF
- **Dashboard SPA:** FastAPI static files con tabs, buscadores, estadísticas
- **Órdenes:** Auto-guardado en explosión, CRUD, estadísticas
- **Sprint 1 — Refactor:** CalcularExplosion/CalcularExplosionBatch como use cases, RepositorioOrdenes port, paginación
- **Sprint 2 — Estados:** Máquina de estados (pendiente → en_produccion → completada), consumo de inventario al completar, UI con badges/botones
- **Sprint 3 — Alertas:** stock_minimo por SKU, alertas de stock bajo, sugerencias de compra desde órdenes faltantes + stock mínimo, input inline en UI
- **Sprint 4 — Calidad y trazabilidad:** Control de calidad por orden (tipo, resultado, observaciones), lotes con código único, trazabilidad lote → orden → materiales, UI integrada

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- Domain layer puro sin dependencias externas
- JWT con 8h de expiración
- Adaptador de inventario configurable (fila y columnas) para formatos simple/SIIGO
- SKUs faltantes en explosión: disponible=0 con nota aclaratoria (no error)
- Auto-guardado de órdenes en toda explosión
- Dashboard SPA servido por FastAPI
- Máquina de estados orden: solo pendiente → en_produccion → completada
- Consumo de inventario al completar orden
- stock_minimo default 0.0 (sin alerta hasta configurar)
- Control de calidad: tipo libre, resultado pendiente/aprobado/rechazado
- Lotes: código único definido por usuario

## Testing
- **Framework:** pytest + httpx
- **Tests unitarios:** 40 tests en `tests/` (modelos de dominio, servicios, Excel adapter)
- **Ejecución:** `pytest tests/ -v`

## CI/CD
- **GitHub Actions:** `.github/workflows/ci.yml`
- **Triggers:** push a develop/main/test, PR a main
- **Pasos:** lint (ruff) → test (pytest con PostgreSQL) → build Docker
- **Artefactos:** reporte JUnit de tests

## Critical Context
- Puerto: 8001 (mapeado externamente)
- Admin password por defecto: 123456789
- Docker: flos_production_db, flos_backend_app
- Branch strategy: main (stable), develop (working), test (pre-release)
- Git remote: https://github.com/Mauricio8474/flos.git
