from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
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
    id_formula = Column(String, nullable=False)
    sku = Column(String, nullable=False)
    porcentaje = Column(Float, nullable=False)


class InventarioORM(Base):
    __tablename__ = "inventario"

    sku = Column(String, primary_key=True)
    nombre = Column(String, default="")
    cantidad_kg = Column(Float, nullable=False, default=0.0)
    costo_unitario = Column(Float, default=0.0)


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
            formulas_orm = session.query(FormulaORM).all()
            resultado: dict[str, Formula] = {}
            for f in formulas_orm:
                componentes = (
                    session.query(ComponenteORM)
                    .filter_by(id_formula=f.id_formula)
                    .order_by(ComponenteORM.id)
                    .all()
                )
                resultado[f.id_formula] = Formula(
                    nombre=f.nombre,
                    componentes=tuple(
                        ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje) for c in componentes
                    ),
                )
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


def init_db(database_url: str) -> sessionmaker:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    # Migrate existing tables adding new columns if missing
    with engine.connect() as conn:
        from sqlalchemy import inspect, text
        inspector = inspect(conn)
        columns = {c["name"] for c in inspector.get_columns("inventario")}
        if "nombre" not in columns:
            conn.execute(text("ALTER TABLE inventario ADD COLUMN nombre VARCHAR DEFAULT ''"))
        if "costo_unitario" not in columns:
            conn.execute(text("ALTER TABLE inventario ADD COLUMN costo_unitario FLOAT DEFAULT 0.0"))
        conn.commit()

    return sessionmaker(bind=engine)
