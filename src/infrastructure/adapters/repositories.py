from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker

from src.application.use_cases import RepositorioAuditoria, RepositorioFormula, RepositorioInventario, RepositorioUsuario
from src.domain.models import ItemInventario
from src.domain.models import ComponenteFormula, Formula

Base = declarative_base()


class FormulaORM(Base):
    __tablename__ = "formulas"

    id_formula = Column(String, primary_key=True)
    nombre = Column(String, nullable=False)


class ComponenteORM(Base):
    __tablename__ = "componentes_formula"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_formula = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=False)
    porcentaje = Column(Float, nullable=False)


class InventarioORM(Base):
    __tablename__ = "inventario"

    sku = Column(String, primary_key=True)
    nombre = Column(String, default="")
    cantidad_kg = Column(Float, nullable=False, default=0.0)
    costo_unitario = Column(Float, default=0.0)


class OrdenProduccionORM(Base):
    __tablename__ = "ordenes_produccion"

    id = Column(String, primary_key=True)
    id_formula = Column(String, nullable=False)
    nombre_formula = Column(String, nullable=False)
    cantidad_kg = Column(Float, nullable=False)
    usuario = Column(String, default="")
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DetalleOrdenORM(Base):
    __tablename__ = "detalle_orden"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_orden = Column(String, nullable=False, index=True)
    sku = Column(String, nullable=False)
    nombre = Column(String, default="")
    requerido_kg = Column(Float, nullable=False)
    disponible_kg = Column(Float, nullable=False)
    faltante_kg = Column(Float, nullable=False)
    cubierto = Column(Integer, default=0)
    nota = Column(String, default="")


class PostgresRepositorioFormula(RepositorioFormula):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar(self, id_formula: str, formula: Formula) -> None:
        with self._sf() as session:
            session.merge(FormulaORM(id_formula=id_formula, nombre=formula.nombre))
            session.query(ComponenteORM).filter_by(id_formula=id_formula).delete()
            for c in formula.componentes:
                session.add(ComponenteORM(id_formula=id_formula, sku=c.sku, porcentaje=c.porcentaje))
            session.commit()

    def guardar_muchos(self, formulas: dict[str, Formula]) -> None:
        with self._sf() as session:
            for id_formula, formula in formulas.items():
                session.merge(FormulaORM(id_formula=id_formula, nombre=formula.nombre))
                session.query(ComponenteORM).filter_by(id_formula=id_formula).delete()
                for c in formula.componentes:
                    session.add(ComponenteORM(id_formula=id_formula, sku=c.sku, porcentaje=c.porcentaje))
            session.commit()

    def obtener(self, id_formula: str) -> Formula | None:
        with self._sf() as session:
            f = session.query(FormulaORM).filter_by(id_formula=id_formula).first()
            if not f:
                return None
            componentes = (
                session.query(ComponenteORM)
                .filter_by(id_formula=id_formula)
                .order_by(ComponenteORM.id)
                .all()
            )
            return Formula(
                nombre=f.nombre,
                componentes=tuple(
                    ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje) for c in componentes
                ),
            )

    def listar(self) -> dict[str, Formula]:
        with self._sf() as session:
            formulas_orm = {f.id_formula: f for f in session.query(FormulaORM).all()}
            if not formulas_orm:
                return {}
            componentes = (
                session.query(ComponenteORM)
                .order_by(ComponenteORM.id_formula, ComponenteORM.id)
                .all()
            )
            resultado: dict[str, Formula] = {}
            for id_formula, f in formulas_orm.items():
                comps = tuple(
                    ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje)
                    for c in componentes
                    if c.id_formula == id_formula
                )
                resultado[id_formula] = Formula(nombre=f.nombre, componentes=comps)
            return resultado

    def eliminar(self, id_formula: str) -> bool:
        with self._sf() as session:
            f = session.query(FormulaORM).filter_by(id_formula=id_formula).first()
            if not f:
                return False
            session.query(ComponenteORM).filter_by(id_formula=id_formula).delete()
            session.delete(f)
            session.commit()
            return True


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    activo = Column(Integer, default=1)
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PostgresRepositorioUsuario(RepositorioUsuario):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar(self, username: str, password_hash: str, rol: str, nombre: str, activo: bool = True) -> None:
        with self._sf() as session:
            session.merge(
                UsuarioORM(
                    username=username, password_hash=password_hash,
                    rol=rol, nombre=nombre, activo=1 if activo else 0,
                )
            )
            session.commit()

    def obtener(self, username: str) -> dict | None:
        with self._sf() as session:
            u = session.query(UsuarioORM).filter_by(username=username).first()
            if not u:
                return None
            return {"id": u.id, "username": u.username, "password_hash": u.password_hash, "rol": u.rol, "nombre": u.nombre, "activo": u.activo}

    def listar(self) -> list[dict]:
        with self._sf() as session:
            return [
                {"id": u.id, "username": u.username, "rol": u.rol, "nombre": u.nombre, "activo": bool(u.activo), "creado_en": u.creado_en.isoformat() if u.creado_en else None}
                for u in session.query(UsuarioORM).order_by(UsuarioORM.id).all()
            ]

    def existe_admin(self) -> bool:
        with self._sf() as session:
            return session.query(UsuarioORM).filter_by(rol="admin").first() is not None


class AuditoriaORM(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entidad = Column(String, nullable=False)
    entidad_id = Column(String, nullable=False)
    accion = Column(String, nullable=False)
    detalle = Column(Text, default="")
    usuario = Column(String, default="")
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PostgresRepositorioAuditoria(RepositorioAuditoria):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def registrar(self, entidad: str, entidad_id: str, accion: str, detalle: str, usuario: str) -> None:
        with self._sf() as session:
            session.add(
                AuditoriaORM(
                    entidad=entidad, entidad_id=entidad_id,
                    accion=accion, detalle=detalle, usuario=usuario,
                )
            )
            session.commit()

    def listar(self, limite: int = 100) -> list[dict]:
        with self._sf() as session:
            rows = (
                session.query(AuditoriaORM)
                .order_by(AuditoriaORM.id.desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "entidad": r.entidad,
                    "entidad_id": r.entidad_id,
                    "accion": r.accion,
                    "detalle": r.detalle,
                    "usuario": r.usuario,
                    "creado_en": r.creado_en.isoformat() if r.creado_en else None,
                }
                for r in rows
            ]


class PostgresRepositorioInventario(RepositorioInventario):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar_muchos(self, items: list[ItemInventario]) -> None:
        with self._sf() as session:
            for item in items:
                session.merge(
                    InventarioORM(
                        sku=item.sku,
                        nombre=item.nombre,
                        cantidad_kg=item.cantidad_kg,
                        costo_unitario=item.costo_unitario,
                    )
                )
            session.commit()

    def obtener_todos(self) -> list[ItemInventario]:
        with self._sf() as session:
            rows = session.query(InventarioORM).order_by(InventarioORM.sku).all()
            return [
                ItemInventario(sku=r.sku, nombre=r.nombre, cantidad_kg=r.cantidad_kg, costo_unitario=r.costo_unitario)
                for r in rows
            ]


class PostgresRepositorioOrdenes:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar(
        self,
        id_orden: str,
        id_formula: str,
        nombre_formula: str,
        cantidad_kg: float,
        usuario: str,
        detalles: list[dict],
    ) -> None:
        with self._sf() as session:
            session.add(
                OrdenProduccionORM(
                    id=id_orden,
                    id_formula=id_formula,
                    nombre_formula=nombre_formula,
                    cantidad_kg=cantidad_kg,
                    usuario=usuario,
                )
            )
            for d in detalles:
                session.add(
                    DetalleOrdenORM(
                        id_orden=id_orden,
                        sku=d["sku"],
                        nombre=d["nombre"],
                        requerido_kg=d["requerido_kg"],
                        disponible_kg=d["disponible_kg"],
                        faltante_kg=d["faltante_kg"],
                        cubierto=1 if d["cubierto"] else 0,
                        nota=d.get("nota", ""),
                    )
                )
            session.commit()

    def listar(self, limite: int = 100) -> list[dict]:
        with self._sf() as session:
            rows = (
                session.query(OrdenProduccionORM)
                .order_by(OrdenProduccionORM.creado_en.desc())
                .limit(limite)
                .all()
            )
            ids = [r.id for r in rows]
            if ids:
                from sqlalchemy import text
                counts = {
                    row[0]: row[1]
                    for row in session.execute(
                        text("SELECT id_orden, COUNT(*) FROM detalle_orden WHERE id_orden = ANY(:ids) GROUP BY id_orden"),
                        {"ids": ids},
                    ).fetchall()
                }
            else:
                counts = {}
            return [
                {
                    "id": r.id,
                    "id_formula": r.id_formula,
                    "nombre_formula": r.nombre_formula,
                    "cantidad_kg": r.cantidad_kg,
                    "usuario": r.usuario,
                    "creado_en": r.creado_en.isoformat() if r.creado_en else None,
                    "cantidad_componentes": counts.get(r.id, 0),
                    "detalles": [],
                }
                for r in rows
            ]

    def obtener(self, id_orden: str) -> dict | None:
        with self._sf() as session:
            r = session.query(OrdenProduccionORM).filter_by(id=id_orden).first()
            if not r:
                return None
            detalles = (
                session.query(DetalleOrdenORM)
                .filter_by(id_orden=id_orden)
                .order_by(DetalleOrdenORM.id)
                .all()
            )
            return {
                "id": r.id,
                "id_formula": r.id_formula,
                "nombre_formula": r.nombre_formula,
                "cantidad_kg": r.cantidad_kg,
                "usuario": r.usuario,
                "creado_en": r.creado_en.isoformat() if r.creado_en else None,
                "detalles": [
                    {
                        "sku": d.sku,
                        "nombre": d.nombre,
                        "requerido_kg": d.requerido_kg,
                        "disponible_kg": d.disponible_kg,
                        "faltante_kg": d.faltante_kg,
                        "cubierto": bool(d.cubierto),
                        "nota": d.nota,
                    }
                    for d in detalles
                ],
            }

    def eliminar(self, id_orden: str) -> bool:
        with self._sf() as session:
            r = session.query(OrdenProduccionORM).filter_by(id=id_orden).first()
            if not r:
                return False
            session.query(DetalleOrdenORM).filter_by(id_orden=id_orden).delete()
            session.delete(r)
            session.commit()
            return True

    def estadisticas(self) -> dict:
        with self._sf() as session:
            total = session.query(OrdenProduccionORM).count()

            # Ordenes por día (últimos 7)
            from sqlalchemy import text
            rows = session.execute(
                text("""
                    SELECT DATE(creado_en) as fecha, COUNT(*) as total
                    FROM ordenes_produccion
                    WHERE creado_en >= CURRENT_DATE - INTERVAL '7 days'
                    GROUP BY DATE(creado_en)
                    ORDER BY fecha
                """)
            ).fetchall()
            ordenes_por_dia = [{"fecha": str(r[0]), "total": r[1]} for r in rows]

            # Productos más demandados (por cantidad de veces producidos)
            rows = session.execute(
                text("""
                    SELECT id_formula, nombre_formula, COUNT(*) as veces, SUM(cantidad_kg) as total_kg
                    FROM ordenes_produccion
                    GROUP BY id_formula, nombre_formula
                    ORDER BY veces DESC
                    LIMIT 10
                """)
            ).fetchall()
            productos_top = [
                {"id_formula": r[0], "nombre": r[1], "veces_producido": r[2], "total_kg": float(r[3])}
                for r in rows
            ]

            # Materiales más requeridos
            rows = session.execute(
                text("""
                    SELECT d.sku, d.nombre, SUM(d.requerido_kg) as total_requerido
                    FROM detalle_orden d
                    JOIN ordenes_produccion o ON o.id = d.id_orden
                    GROUP BY d.sku, d.nombre
                    ORDER BY total_requerido DESC
                    LIMIT 10
                """)
            ).fetchall()
            materiales_top = [
                {"sku": r[0], "nombre": r[1], "total_requerido_kg": float(r[2])}
                for r in rows
            ]

            return {
                "total_ordenes": total,
                "ordenes_por_dia": ordenes_por_dia,
                "productos_mas_demandados": productos_top,
                "materiales_mas_requeridos": materiales_top,
            }


def init_db(database_url: str) -> sessionmaker:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    # Migrate existing tables adding new columns / indexes if missing
    with engine.connect() as conn:
        from sqlalchemy import inspect, text
        inspector = inspect(conn)
        columns = {c["name"] for c in inspector.get_columns("inventario")}
        if "nombre" not in columns:
            conn.execute(text("ALTER TABLE inventario ADD COLUMN nombre VARCHAR DEFAULT ''"))
        if "costo_unitario" not in columns:
            conn.execute(text("ALTER TABLE inventario ADD COLUMN costo_unitario FLOAT DEFAULT 0.0"))

        indexes = {ix["name"] for ix in inspector.get_indexes("componentes_formula")}
        if "ix_componentes_formula_id_formula" not in indexes:
            conn.execute(text("CREATE INDEX ix_componentes_formula_id_formula ON componentes_formula (id_formula)"))

        conn.commit()

    return sessionmaker(bind=engine)
