# Arquitectura Hexagonal — Flos MES

## Principios

Flos MES sigue una **Arquitectura Hexagonal** (Puertos y Adaptadores) combinada con **Domain-Driven Design** (DDD). El objetivo es aislar la lógica de negocio de los detalles técnicos (base de datos, frameworks, archivos Excel).

## Capas

```
┌─────────────────────────────────────────────┐
│               main.py (FastAPI)              │  ← Composition Root
│  ┌───────────────────────────────────────┐   │
│  │         APPLICATION (use_cases)        │   │  ← Casos de uso
│  └──────────┬────────────────────────────┘   │
│             │ puertos (interfaces)            │
│  ┌──────────▼────────────────────────────┐   │
│  │           DOMAIN                       │   │  ← Capa pura
│  │  ┌──────────┐  ┌──────────────────┐   │   │
│  │  │  models   │  │   services       │   │   │
│  │  └──────────┘  └──────────────────┘   │   │
│  └──────────┬────────────────────────────┘   │
│             │                                │
│  ┌──────────▼────────────────────────────┐   │
│  │      INFRASTRUCTURE (adapters)         │   │  ← Implementaciones
│  │  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │ excel_reader │  │ repositories │   │   │
│  │  └──────────────┘  └──────────────┘   │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### Dominio (`src/domain/`)

**Capa pura:** sin importar FastAPI, SQLAlchemy, Pandas ni ninguna librería externa.

- `models.py` — Entidades de negocio (Producto, Formula, Ingrediente, Lote, Inventario).
- `services.py` — Lógica del motor de explosión de materiales (cálculo de necesidades brutas/netas).

### Aplicación (`src/application/`)

Orquesta los casos de uso del sistema:

- `CalcularExplosion` — Dispara el cálculo de explosión de materiales para una orden de producción.
- `CargarInventario` — Importa y actualiza el inventario desde archivos Excel.

Depende de puertos (interfaces) definidos en dominio, no de implementaciones concretas.

### Infraestructura (`src/infrastructure/adapters/`)

Implementa los puertos definidos en capas superiores:

- `excel_reader.py` — Lee archivos `.xlsx` usando OpenPyXL o Pandas.
- `repositories.py` — Persistencia en PostgreSQL usando SQLAlchemy.

### Composition Root (`src/main.py`)

Único lugar donde se instancian todas las dependencias y se conectan las capas. Configura FastAPI, inyecta dependencias y expone los endpoints REST.

## Flujo de datos

1. El cliente HTTP llama a un endpoint en `main.py`
2. El endpoint invoca un caso de uso en `application/use_cases.py`
3. El caso de uso orquesta la lógica de dominio (`domain/`) y los adapters (`infrastructure/`)
4. Los adapters leen/escriben en Excel o PostgreSQL según corresponda
5. El resultado retorna al cliente vía FastAPI

## Reglas

- `domain/` **nunca** importa de `infrastructure/` o `application/`
- `application/` importa de `domain/` y define puertos
- `infrastructure/` importa de `domain/` y `application/` (implementa puertos)
- `main.py` importa de todas las capas (es el punto de ensamblaje)
