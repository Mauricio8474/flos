from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from src.application.use_cases import RepositorioFormula, RepositorioInventario
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
    cantidad_kg = Column(Float, nullable=False, default=0.0)


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


class PostgresRepositorioInventario(RepositorioInventario):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar_muchos(self, items: dict[str, float]) -> None:
        with self._sf() as session:
            for sku, cantidad in items.items():
                session.merge(InventarioORM(sku=sku, cantidad_kg=cantidad))
            session.commit()

    def obtener_todos(self) -> dict[str, float]:
        with self._sf() as session:
            return {
                row.sku: row.cantidad_kg
                for row in session.query(InventarioORM).all()
            }


def init_db(database_url: str) -> sessionmaker:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
