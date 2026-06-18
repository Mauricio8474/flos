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
class ResultadoExplosion:
    sku: str
    requerido_kg: float
    disponible_kg: float
    faltante_kg: float
    cubierto: bool
