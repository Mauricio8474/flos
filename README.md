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

# Iniciar base de datos con Docker
docker compose up -d flos-db

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
uvicorn src.main:app --reload
```

La API estará disponible en `http://localhost:8000/docs`

## Estructura del proyecto

```
flos/
├── src/
│   ├── domain/          # Entidades y lógica de negocio (capa pura)
│   ├── application/     # Casos de uso (orquestación)
│   ├── infrastructure/  # Adaptadores (Excel, PostgreSQL)
│   └── main.py          # Composition root (FastAPI)
├── docs/                # Documentación
├── docker-compose.yml
├── ERP Metarom.xlsx     # Datos fuente ERP
├── formulas.xlsx        # Lógica de fórmulas
└── inventario.xlsx      # Control de inventario
```

## Licencia

Propietaria — Uso interno.
