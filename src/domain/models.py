from dataclasses import dataclass


@dataclass(frozen=True)
class ComponenteFormula:
    sku: str
    porcentaje: float


@dataclass(frozen=True)
class Formula:
    nombre: str
    componentes: tuple[ComponenteFormula, ...]


@dataclass(frozen=True)
class ItemInventario:
    sku: str
    nombre: str
    cantidad_kg: float
    costo_unitario: float
    stock_minimo: float = 0.0


@dataclass(frozen=True)
class AlertaStock:
    sku: str
    nombre: str
    cantidad_kg: float
    stock_minimo: float
    faltante: float


@dataclass(frozen=True)
class SugerenciaCompra:
    sku: str
    nombre: str
    cantidad_requerida: float
    origen: str  # "stock_minimo" | "orden_faltante"
    id_orden: str = ""


@dataclass(frozen=True)
class ResultadoExplosion:
    sku: str
    nombre: str
    requerido_kg: float
    disponible_kg: float
    faltante_kg: float
    cubierto: bool
    nota: str = ""


ESTADOS_ORDEN = frozenset({"pendiente", "en_produccion", "completada"})

TRANSICIONES_ORDEN: dict[str, str] = {
    "pendiente": "en_produccion",
    "en_produccion": "completada",
}


def validar_transicion_orden(estado_actual: str, nuevo_estado: str) -> str | None:
    esperado = TRANSICIONES_ORDEN.get(estado_actual)
    if esperado is None:
        return f"Estado '{estado_actual}' no permite transiciones"
    if nuevo_estado != esperado:
        return f"No se puede pasar de '{estado_actual}' a '{nuevo_estado}'. Solo se permite '{estado_actual}' → '{esperado}'"
    return None
