from abc import ABC, abstractmethod
import uuid

from src.domain.models import (
    AlertaStock, ComponenteFormula, Formula, ItemInventario,
    ResultadoExplosion, SugerenciaCompra, ESTADOS_ORDEN, validar_transicion_orden,
)
from src.domain.services import CalculadorMRP, GeneradorAlertasStock, GeneradorSugerenciasCompra


class PuertoInventario(ABC):
    @abstractmethod
    def leer_inventario(self, ruta: str) -> list[ItemInventario]:
        ...


class PuertoFormulas(ABC):
    @abstractmethod
    def leer_formulas(self, ruta: str) -> dict[str, Formula]:
        ...


class RepositorioFormula(ABC):
    @abstractmethod
    def guardar(self, id_formula: str, formula: Formula) -> None:
        ...

    @abstractmethod
    def guardar_muchos(self, formulas: dict[str, Formula]) -> None:
        ...

    @abstractmethod
    def obtener(self, id_formula: str) -> Formula | None:
        ...

    @abstractmethod
    def listar(self, page: int = 0, page_size: int = 0) -> tuple[dict[str, Formula], int]:
        ...

    @abstractmethod
    def eliminar(self, id_formula: str) -> bool:
        ...


class RepositorioInventario(ABC):
    @abstractmethod
    def guardar_muchos(self, items: list[ItemInventario]) -> None:
        ...

    @abstractmethod
    def obtener_todos(self, page: int = 0, page_size: int = 0) -> tuple[list[ItemInventario], int]:
        ...

    @abstractmethod
    def obtener(self, sku: str) -> ItemInventario | None:
        ...

    @abstractmethod
    def actualizar_stock_minimo(self, sku: str, stock_minimo: float) -> bool:
        ...

    @abstractmethod
    def obtener_ordenes_con_faltantes(self) -> list[dict]:
        ...


class RepositorioUsuario(ABC):
    @abstractmethod
    def guardar(self, username: str, password_hash: str, rol: str, nombre: str, activo: bool = True) -> None:
        ...

    @abstractmethod
    def obtener(self, username: str) -> dict | None:
        ...

    @abstractmethod
    def listar(self) -> list[dict]:
        ...

    @abstractmethod
    def existe_admin(self) -> bool:
        ...


class RepositorioAuditoria(ABC):
    @abstractmethod
    def registrar(self, entidad: str, entidad_id: str, accion: str, detalle: str, usuario: str) -> None:
        ...

    @abstractmethod
    def listar(self, page: int = 0, page_size: int = 0) -> tuple[list[dict], int]:
        ...


class RepositorioOrdenes(ABC):
    @abstractmethod
    def guardar(self, id_orden: str, id_formula: str, nombre_formula: str, cantidad_kg: float, usuario: str, detalles: list[dict]) -> None:
        ...

    @abstractmethod
    def listar(self, page: int = 0, page_size: int = 0) -> tuple[list[dict], int]:
        ...

    @abstractmethod
    def obtener(self, id_orden: str) -> dict | None:
        ...

    @abstractmethod
    def eliminar(self, id_orden: str) -> bool:
        ...

    @abstractmethod
    def estadisticas(self) -> dict:
        ...

    @abstractmethod
    def actualizar_estado(self, id_orden: str, nuevo_estado: str) -> bool:
        ...

    @abstractmethod
    def consumir_inventario_orden(self, id_orden: str) -> None:
        ...


def _detalles_from_resultados(resultados: list[ResultadoExplosion]) -> list[dict]:
    return [
        {
            "sku": r.sku,
            "nombre": r.nombre,
            "requerido_kg": r.requerido_kg,
            "disponible_kg": r.disponible_kg,
            "faltante_kg": r.faltante_kg,
            "cubierto": r.cubierto,
            "nota": r.nota,
        }
        for r in resultados
    ]


class CalcularExplosion:
    def __init__(
        self,
        repo_formula: RepositorioFormula,
        repo_inventario: RepositorioInventario,
        repo_ordenes: RepositorioOrdenes,
    ) -> None:
        self._repo_formula = repo_formula
        self._repo_inventario = repo_inventario
        self._repo_ordenes = repo_ordenes

    def ejecutar(
        self,
        id_formula: str,
        cantidad_kg: float,
        usuario: str,
    ) -> tuple[list[dict], str | None]:
        formula = self._repo_formula.obtener(id_formula)
        if not formula:
            return [], f"Formula '{id_formula}' no encontrada"

        inventario = {i.sku: i for i in self._repo_inventario.obtener_todos()[0]}
        resultados = CalculadorMRP.calcular_explosion(formula, cantidad_kg, inventario)

        orden_id = str(uuid.uuid4())
        self._repo_ordenes.guardar(
            id_orden=orden_id,
            id_formula=id_formula,
            nombre_formula=formula.nombre,
            cantidad_kg=cantidad_kg,
            usuario=usuario,
            detalles=_detalles_from_resultados(resultados),
        )

        return [
            {
                "sku": r.sku,
                "nombre": r.nombre,
                "requerido_kg": r.requerido_kg,
                "disponible_kg": r.disponible_kg,
                "faltante_kg": r.faltante_kg,
                "cubierto": r.cubierto,
                "nota": r.nota,
                "orden_id": orden_id,
            }
            for r in resultados
        ], None


class CalcularExplosionBatch:
    def __init__(
        self,
        repo_formula: RepositorioFormula,
        repo_inventario: RepositorioInventario,
        repo_ordenes: RepositorioOrdenes,
    ) -> None:
        self._repo_formula = repo_formula
        self._repo_inventario = repo_inventario
        self._repo_ordenes = repo_ordenes

    def ejecutar(
        self,
        ordenes: list[dict],
        usuario: str,
    ) -> list[dict]:
        inventario = {i.sku: i for i in self._repo_inventario.obtener_todos()[0]}
        resultados = []

        for orden in ordenes:
            id_formula = orden["id_formula"]
            cantidad = orden["cantidad"]
            formula = self._repo_formula.obtener(id_formula)
            if not formula:
                resultados.append({"orden": id_formula, "error": "Formula no encontrada"})
                continue

            res = CalculadorMRP.calcular_explosion(formula, cantidad, inventario)
            orden_id = str(uuid.uuid4())
            self._repo_ordenes.guardar(
                id_orden=orden_id,
                id_formula=id_formula,
                nombre_formula=formula.nombre,
                cantidad_kg=cantidad,
                usuario=usuario,
                detalles=_detalles_from_resultados(res),
            )

            for r in res:
                resultados.append(
                    {
                        "orden": id_formula,
                        "orden_id": orden_id,
                        "sku": r.sku,
                        "nombre": r.nombre,
                        "requerido_kg": r.requerido_kg,
                        "disponible_kg": r.disponible_kg,
                        "faltante_kg": r.faltante_kg,
                        "cubierto": r.cubierto,
                        "nota": r.nota,
                    }
                )

        return resultados


class CambiarEstadoOrden:
    def __init__(self, repo_ordenes: RepositorioOrdenes) -> None:
        self._repo_ordenes = repo_ordenes

    def ejecutar(self, id_orden: str, nuevo_estado: str) -> dict:
        orden = self._repo_ordenes.obtener(id_orden)
        if not orden:
            return {"error": f"Orden '{id_orden}' no encontrada"}

        error = validar_transicion_orden(orden["estado"], nuevo_estado)
        if error:
            return {"error": error}

        if nuevo_estado == "completada":
            self._repo_ordenes.consumir_inventario_orden(id_orden)

        self._repo_ordenes.actualizar_estado(id_orden, nuevo_estado)
        return {"mensaje": f"Orden '{id_orden[:8]}…' ahora está en '{nuevo_estado}'", "estado": nuevo_estado}


class GenerarAlertasStock:
    def __init__(self, repo_inventario: RepositorioInventario) -> None:
        self._repo_inventario = repo_inventario

    def ejecutar(self) -> list[dict]:
        inventario, _ = self._repo_inventario.obtener_todos()
        alertas = GeneradorAlertasStock.generar(inventario)
        return [
            {"sku": a.sku, "nombre": a.nombre, "cantidad_kg": a.cantidad_kg, "stock_minimo": a.stock_minimo, "faltante": a.faltante}
            for a in alertas
        ]


class GenerarSugerenciasCompra:
    def __init__(self, repo_inventario: RepositorioInventario, repo_ordenes: RepositorioOrdenes) -> None:
        self._repo_inventario = repo_inventario
        self._repo_ordenes = repo_ordenes

    def ejecutar(self) -> dict:
        inventario, _ = self._repo_inventario.obtener_todos()
        inv_dict = {i.sku: i for i in inventario}
        ordenes_faltantes = self._repo_inventario.obtener_ordenes_con_faltantes()
        desde_ordenes = GeneradorSugerenciasCompra.desde_faltantes_ordenes(ordenes_faltantes, inv_dict)
        desde_minimo = GeneradorSugerenciasCompra.desde_stock_minimo(inventario)
        todas = desde_ordenes + desde_minimo
        return [
            {"sku": s.sku, "nombre": s.nombre, "cantidad_requerida": s.cantidad_requerida, "origen": s.origen, "id_orden": s.id_orden}
            for s in todas
        ]
