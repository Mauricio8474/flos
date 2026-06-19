# Flos MES

Sistema MES (Manufacturing Execution System) para la producción de esencias, construido bajo Arquitectura Hexagonal con DDD.

## Stack

- **Backend:** Python 3.12+, FastAPI
- **Base de datos:** PostgreSQL 15 (SQLAlchemy)
- **Lectura de datos:** OpenPyXL / Pandas (archivos `.xlsx`)
- **Infraestructura:** Docker Compose

## Requisitos

- Python 3.12+
- Docker Desktop (opcional, para base de datos)
- PostgreSQL 15 (si se ejecuta sin Docker)

## Inicio rápido

```bash
# Clonar el repositorio
git clone <repo-url>
cd flos

# Copiar variables de entorno
cp .env.example .env  # o crear .env con DATABASE_URL y JWT_SECRET

# Iniciar todo con Docker
docker compose up -d --build

# O bien, solo la base de datos y ejecutar la app localmente
docker compose up -d flos-db
pip install -r requirements.txt
uvicorn src.main:app --reload
```

- **Frontend:** http://localhost:8001/dashboard/
- **API:** http://localhost:8001/
- **Documentación OpenAPI:** http://localhost:8001/docs

## Funcionalidades

- **Fórmulas** — CRUD completo, carga masiva desde Excel (configurable por columnas)
- **Inventario** — Carga desde Excel (formato simple o SIIGO), consulta con paginación, stock mínimo configurable
- **Explosión de materiales** — Cálculo MRP con detección de faltantes; soporta batch JSON y Excel
- **Órdenes de producción** — Auto-guardado en explosión, máquina de estados (pendiente → en_producción → completada), consumo de inventario al completar
- **Alertas de stock** — Materiales por debajo del stock mínimo configurado
- **Sugerencias de compra** — Combina faltantes de órdenes activas + stock mínimo
- **Control de calidad** — Controles por tipo (viscosidad, densidad, ph…) vinculados a órdenes
- **Lotes y trazabilidad** — Lotes con código único, trazabilidad lote → orden → materiales
- **Dashboard** — Estadísticas: órdenes por día, productos más demandados, materiales más requeridos
- **Autenticación JWT** — 5 roles (admin, ingenieria, almacen, produccion, consultor)
- **Auditoría** — Trazabilidad de cambios en fórmulas, inventario, órdenes, controles y lotes
- **Reportes** — Descarga de resultados de explosión en Excel y PDF

## Estructura del proyecto

```
flos/
├── src/
│   ├── domain/          # Entidades y lógica de negocio (capa pura)
│   ├── application/     # Puertos (interfaces) y casos de uso
│   ├── infrastructure/  # Adaptadores (Excel, PostgreSQL) y auth
│   └── main.py          # Composition root (FastAPI)
├── docker-compose.yml
├── AGENTS.md            # Documentación técnica del proyecto
├── ERP Metarom.xlsx     # Datos fuente ERP
├── formulas.xlsx        # Lógica de fórmulas
├── inventario.xlsx      # Control de inventario
└── ejemplo_batch.xlsx   # Ejemplo de carga batch
```

## Licencia

Propietaria — Uso interno.
