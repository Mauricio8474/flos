from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, func, or_
from sqlalchemy.orm import declarative_base, sessionmaker

from src.application.use_cases import (
    RepositorioAuditoria, RepositorioControlCalidad, RepositorioFormula,
    RepositorioInventario, RepositorioLotes, RepositorioOrdenes, RepositorioUsuario,
)
from src.domain.models import ItemInventario
from src.domain.models import ComponenteFormula, ControlCalidad, Formula, LoteProduccion

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
    stock_minimo = Column(Float, default=0.0)


class OrdenProduccionORM(Base):
    __tablename__ = "ordenes_produccion"

    id = Column(String, primary_key=True)
    id_formula = Column(String, nullable=False)
    nombre_formula = Column(String, nullable=False)
    cantidad_kg = Column(Float, nullable=False)
    estado = Column(String, nullable=False, default="pendiente")
    usuario = Column(String, default="")
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ControlCalidadORM(Base):
    __tablename__ = "control_calidad"

    id = Column(String, primary_key=True)
    id_orden = Column(String, nullable=False, index=True)
    tipo = Column(String, nullable=False)
    resultado = Column(String, nullable=False, default="pendiente")
    observaciones = Column(String, default="")
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LoteProduccionORM(Base):
    __tablename__ = "lotes_produccion"

    id = Column(String, primary_key=True)
    id_orden = Column(String, nullable=False, index=True)
    id_formula = Column(String, nullable=False)
    nombre_formula = Column(String, nullable=False)
    codigo_lote = Column(String, unique=True, nullable=False)
    cantidad_producida = Column(Float, nullable=False)
    estado = Column(String, nullable=False, default="activo")
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

    def listar(self, page: int = 0, page_size: int = 0, q: str = "") -> tuple[dict[str, Formula], int]:
        with self._sf() as session:
            query = session.query(FormulaORM)
            if q:
                like = f"%{q}%"
                query = query.filter(or_(FormulaORM.id_formula.ilike(like), FormulaORM.nombre.ilike(like)))
            total = query.count()

            if page > 0 and page_size > 0:
                formulas_orm = {f.id_formula: f for f in query.order_by(FormulaORM.id_formula).offset((page - 1) * page_size).limit(page_size).all()}
            else:
                formulas_orm = {f.id_formula: f for f in query.all()}

            if not formulas_orm:
                return {}, total
            ids = list(formulas_orm.keys())
            componentes = (
                session.query(ComponenteORM)
                .filter(ComponenteORM.id_formula.in_(ids))
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
            return resultado, total

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

    def listar(self, q: str = "") -> list[dict]:
        with self._sf() as session:
            query = session.query(UsuarioORM).order_by(UsuarioORM.id)
            if q:
                like = f"%{q}%"
                query = query.filter(or_(
                    UsuarioORM.username.ilike(like),
                    UsuarioORM.nombre.ilike(like),
                    UsuarioORM.rol.ilike(like),
                ))
            return [
                {"id": u.id, "username": u.username, "rol": u.rol, "nombre": u.nombre, "activo": bool(u.activo), "creado_en": u.creado_en.isoformat() if u.creado_en else None}
                for u in query.all()
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

    def listar(self, page: int = 0, page_size: int = 0, q: str = "") -> tuple[list[dict], int]:
        with self._sf() as session:
            query = session.query(AuditoriaORM).order_by(AuditoriaORM.id.desc())
            if q:
                like = f"%{q}%"
                query = query.filter(or_(
                    AuditoriaORM.entidad.ilike(like),
                    AuditoriaORM.entidad_id.ilike(like),
                    AuditoriaORM.accion.ilike(like),
                    AuditoriaORM.detalle.ilike(like),
                    AuditoriaORM.usuario.ilike(like),
                ))
            total = query.count()
            if page > 0 and page_size > 0:
                rows = query.offset((page - 1) * page_size).limit(page_size).all()
            else:
                rows = query.all()
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
            ], total


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
                        stock_minimo=item.stock_minimo,
                    )
                )
            session.commit()

    def obtener_todos(self, page: int = 0, page_size: int = 0, q: str = "") -> tuple[list[ItemInventario], int]:
        with self._sf() as session:
            query = session.query(InventarioORM).order_by(InventarioORM.sku)
            if q:
                like = f"%{q}%"
                query = query.filter(or_(InventarioORM.sku.ilike(like), InventarioORM.nombre.ilike(like)))
            total = query.count()
            if page > 0 and page_size > 0:
                rows = query.offset((page - 1) * page_size).limit(page_size).all()
            else:
                rows = query.all()
            return [
                ItemInventario(sku=r.sku, nombre=r.nombre, cantidad_kg=r.cantidad_kg, costo_unitario=r.costo_unitario, stock_minimo=r.stock_minimo or 0.0)
                for r in rows
            ], total

    def obtener(self, sku: str) -> ItemInventario | None:
        with self._sf() as session:
            r = session.query(InventarioORM).filter_by(sku=sku).first()
            if not r:
                return None
            return ItemInventario(sku=r.sku, nombre=r.nombre, cantidad_kg=r.cantidad_kg, costo_unitario=r.costo_unitario, stock_minimo=r.stock_minimo or 0.0)

    def actualizar_stock_minimo(self, sku: str, stock_minimo: float) -> bool:
        with self._sf() as session:
            r = session.query(InventarioORM).filter_by(sku=sku).first()
            if not r:
                return False
            r.stock_minimo = stock_minimo
            session.commit()
            return True

    def obtener_ordenes_con_faltantes(self) -> list[dict]:
        with self._sf() as session:
            from sqlalchemy import text
            rows = session.execute(
                text("""
                    SELECT o.id, o.id_formula, o.nombre_formula, o.cantidad_kg
                    FROM ordenes_produccion o
                    WHERE o.estado IN ('pendiente', 'en_produccion')
                    ORDER BY o.creado_en DESC
                """)
            ).fetchall()
            ids = [r[0] for r in rows]
            if not ids:
                return []
            detalles_rows = session.execute(
                text("""
                    SELECT d.id_orden, d.sku, d.nombre, d.requerido_kg, d.disponible_kg, d.faltante_kg, d.cubierto, d.nota
                    FROM detalle_orden d
                    WHERE d.id_orden = ANY(:ids) AND d.cubierto = 0 AND d.faltante_kg > 0
                    ORDER BY d.id_orden, d.id
                """),
                {"ids": ids},
            ).fetchall()
            detalles_por_orden: dict[str, list[dict]] = {}
            for row in detalles_rows:
                oid = row[0]
                if oid not in detalles_por_orden:
                    detalles_por_orden[oid] = []
                detalles_por_orden[oid].append({
                    "sku": row[1], "nombre": row[2], "requerido_kg": float(row[3]),
                    "disponible_kg": float(row[4]), "faltante_kg": float(row[5]),
                    "cubierto": bool(row[6]), "nota": row[7],
                })
            return [
                {"id": r[0], "id_formula": r[1], "nombre_formula": r[2], "cantidad_kg": float(r[3]), "detalles": detalles_por_orden.get(r[0], [])}
                for r in rows
            ]


class PostgresRepositorioOrdenes(RepositorioOrdenes):
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
                    estado="pendiente",
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

    def listar(self, page: int = 0, page_size: int = 0, q: str = "") -> tuple[list[dict], int]:
        with self._sf() as session:
            query = session.query(OrdenProduccionORM).order_by(OrdenProduccionORM.creado_en.desc())
            if q:
                like = f"%{q}%"
                query = query.filter(or_(
                    OrdenProduccionORM.id.ilike(like),
                    OrdenProduccionORM.id_formula.ilike(like),
                    OrdenProduccionORM.nombre_formula.ilike(like),
                    OrdenProduccionORM.usuario.ilike(like),
                ))
            total = query.count()
            if page > 0 and page_size > 0:
                rows = query.offset((page - 1) * page_size).limit(page_size).all()
            else:
                rows = query.all()
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
                    "estado": r.estado,
                    "usuario": r.usuario,
                    "creado_en": r.creado_en.isoformat() if r.creado_en else None,
                    "cantidad_componentes": counts.get(r.id, 0),
                    "detalles": [],
                }
                for r in rows
            ], total

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
                "estado": r.estado,
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

    def actualizar_estado(self, id_orden: str, nuevo_estado: str) -> bool:
        with self._sf() as session:
            r = session.query(OrdenProduccionORM).filter_by(id=id_orden).first()
            if not r:
                return False
            r.estado = nuevo_estado
            session.commit()
            return True

    def consumir_inventario_orden(self, id_orden: str) -> None:
        with self._sf() as session:
            detalles = session.query(DetalleOrdenORM).filter_by(id_orden=id_orden).all()
            for d in detalles:
                inv = session.query(InventarioORM).filter_by(sku=d.sku).first()
                if inv:
                    nuevo = max(0.0, inv.cantidad_kg - d.requerido_kg)
                    inv.cantidad_kg = nuevo
            session.commit()

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


class PostgresRepositorioControlCalidad(RepositorioControlCalidad):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar(self, control: ControlCalidad) -> None:
        with self._sf() as session:
            session.add(ControlCalidadORM(
                id=control.id, id_orden=control.id_orden, tipo=control.tipo,
                resultado=control.resultado, observaciones=control.observaciones,
            ))
            session.commit()

    def listar_por_orden(self, id_orden: str) -> list[dict]:
        with self._sf() as session:
            rows = session.query(ControlCalidadORM).filter_by(id_orden=id_orden).order_by(ControlCalidadORM.creado_en.desc()).all()
            return [
                {"id": r.id, "id_orden": r.id_orden, "tipo": r.tipo, "resultado": r.resultado,
                 "observaciones": r.observaciones, "creado_en": r.creado_en.isoformat() if r.creado_en else None}
                for r in rows
            ]

    def actualizar_resultado(self, id_control: str, resultado: str, observaciones: str) -> bool:
        with self._sf() as session:
            r = session.query(ControlCalidadORM).filter_by(id=id_control).first()
            if not r:
                return False
            r.resultado = resultado
            if observaciones:
                r.observaciones = observaciones
            session.commit()
            return True


class PostgresRepositorioLotes(RepositorioLotes):
    def __init__(self, session_factory: sessionmaker) -> None:
        self._sf = session_factory

    def guardar(self, lote: LoteProduccion) -> None:
        with self._sf() as session:
            session.add(LoteProduccionORM(
                id=lote.id, id_orden=lote.id_orden, id_formula=lote.id_formula,
                nombre_formula=lote.nombre_formula, codigo_lote=lote.codigo_lote,
                cantidad_producida=lote.cantidad_producida, estado=lote.estado,
            ))
            session.commit()

    def listar(self, page: int = 0, page_size: int = 0, q: str = "") -> tuple[list[dict], int]:
        with self._sf() as session:
            query = session.query(LoteProduccionORM).order_by(LoteProduccionORM.creado_en.desc())
            if q:
                like = f"%{q}%"
                query = query.filter(or_(
                    LoteProduccionORM.codigo_lote.ilike(like),
                    LoteProduccionORM.nombre_formula.ilike(like),
                    LoteProduccionORM.id_orden.ilike(like),
                ))
            total = query.count()
            if page > 0 and page_size > 0:
                rows = query.offset((page - 1) * page_size).limit(page_size).all()
            else:
                rows = query.all()
            return [
                {"id": r.id, "id_orden": r.id_orden, "id_formula": r.id_formula,
                 "nombre_formula": r.nombre_formula, "codigo_lote": r.codigo_lote,
                 "cantidad_producida": r.cantidad_producida, "estado": r.estado,
                 "creado_en": r.creado_en.isoformat() if r.creado_en else None}
                for r in rows
            ], total

    def obtener(self, id_lote: str) -> dict | None:
        with self._sf() as session:
            r = session.query(LoteProduccionORM).filter_by(id=id_lote).first()
            if not r:
                return None
            return {"id": r.id, "id_orden": r.id_orden, "id_formula": r.id_formula,
                    "nombre_formula": r.nombre_formula, "codigo_lote": r.codigo_lote,
                    "cantidad_producida": r.cantidad_producida, "estado": r.estado,
                    "creado_en": r.creado_en.isoformat() if r.creado_en else None}

    def obtener_por_orden(self, id_orden: str) -> list[dict]:
        with self._sf() as session:
            rows = session.query(LoteProduccionORM).filter_by(id_orden=id_orden).order_by(LoteProduccionORM.creado_en.desc()).all()
            return [
                {"id": r.id, "id_orden": r.id_orden, "id_formula": r.id_formula,
                 "nombre_formula": r.nombre_formula, "codigo_lote": r.codigo_lote,
                 "cantidad_producida": r.cantidad_producida, "estado": r.estado,
                 "creado_en": r.creado_en.isoformat() if r.creado_en else None}
                for r in rows
            ]

    def actualizar_estado(self, id_lote: str, estado: str) -> bool:
        with self._sf() as session:
            r = session.query(LoteProduccionORM).filter_by(id=id_lote).first()
            if not r:
                return False
            r.estado = estado
            session.commit()
            return True


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
        if "stock_minimo" not in columns:
            conn.execute(text("ALTER TABLE inventario ADD COLUMN stock_minimo FLOAT DEFAULT 0.0"))

        indexes = {ix["name"] for ix in inspector.get_indexes("componentes_formula")}
        if "ix_componentes_formula_id_formula" not in indexes:
            conn.execute(text("CREATE INDEX ix_componentes_formula_id_formula ON componentes_formula (id_formula)"))

        if "ordenes_produccion" in [t for t in inspector.get_table_names()]:
            ord_cols = {c["name"] for c in inspector.get_columns("ordenes_produccion")}
            if "estado" not in ord_cols:
                conn.execute(text("ALTER TABLE ordenes_produccion ADD COLUMN estado VARCHAR NOT NULL DEFAULT 'pendiente'"))

        # Create control_calidad table if not exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS control_calidad (
                id VARCHAR PRIMARY KEY,
                id_orden VARCHAR NOT NULL,
                tipo VARCHAR NOT NULL,
                resultado VARCHAR NOT NULL DEFAULT 'pendiente',
                observaciones VARCHAR DEFAULT '',
                creado_en TIMESTAMP DEFAULT NOW()
            )
        """))
        # Create lotes_produccion table if not exists
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS lotes_produccion (
                id VARCHAR PRIMARY KEY,
                id_orden VARCHAR NOT NULL,
                id_formula VARCHAR NOT NULL,
                nombre_formula VARCHAR NOT NULL,
                codigo_lote VARCHAR UNIQUE NOT NULL,
                cantidad_producida FLOAT NOT NULL,
                estado VARCHAR NOT NULL DEFAULT 'activo',
                creado_en TIMESTAMP DEFAULT NOW()
            )
        """))
        # Add indexes if missing
        existing_tables = [t for t in inspector.get_table_names()]
        if "control_calidad" in existing_tables:
            cc_ix = {ix["name"] for ix in inspector.get_indexes("control_calidad")}
            if "ix_control_calidad_id_orden" not in cc_ix:
                conn.execute(text("CREATE INDEX ix_control_calidad_id_orden ON control_calidad (id_orden)"))
        if "lotes_produccion" in existing_tables:
            lp_ix = {ix["name"] for ix in inspector.get_indexes("lotes_produccion")}
            if "ix_lotes_produccion_id_orden" not in lp_ix:
                conn.execute(text("CREATE INDEX ix_lotes_produccion_id_orden ON lotes_produccion (id_orden)"))

        conn.commit()

    return sessionmaker(bind=engine)
