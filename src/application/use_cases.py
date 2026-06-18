from abc import ABC, abstractmethod


class PuertoInventario(ABC):
    @abstractmethod
    def leer_inventario(self, ruta: str) -> dict[str, float]:
        ...
