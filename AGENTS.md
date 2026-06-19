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
└── src/
    ├── __init__.py
    ├── main.py                       # FastAPI - Composición de dependencias
    ├── application/
    │   ├── __init__.py
    │   └── use_cases.py              # Casos de uso (CalcularExplosion, CargarInventario)
    ├── domain/
    │   ├── __init__.py
    │   ├── models.py                 # Entidades puras de negocio
    │   └── services.py               # Motor de explosión (lógica de dominio)
    └── infrastructure/
        ├── __init__.py
        └── adapters/
            ├── __init__.py
            ├── excel_reader.py       # Lector de Excel (OpenPyXL / Pandas)
            └── repositories.py       # PostgreSQL + SQLAlchemy
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

## Testing
- No hay suite de pruebas definida aún.

## Linting / Typecheck
- No hay configuración de linter o typechecker.
