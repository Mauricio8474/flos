from abc import ABC, abstractmethod

from src.domain.models import Formula


class PuertoInventario(ABC):
    @abstractmethod
    def leer_inventario(self, ruta: str) -> dict[str, float]:
        ...


class PuertoFormulas(ABC):
    @abstractmethod
    def leer_formulas(self, ruta: str) -> dict[str, Formula]:
        ...
