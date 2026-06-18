from abc import ABC, abstractmethod

from src.domain.models import ComponenteFormula, Formula


class PuertoInventario(ABC):
    @abstractmethod
    def leer_inventario(self, ruta: str) -> dict[str, float]:
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
    def obtener(self, id_formula: str) -> Formula | None:
        ...

    @abstractmethod
    def listar(self) -> dict[str, Formula]:
        ...

    @abstractmethod
    def eliminar(self, id_formula: str) -> bool:
        ...


class RepositorioInventario(ABC):
    @abstractmethod
    def guardar_muchos(self, items: dict[str, float]) -> None:
        ...

    @abstractmethod
    def obtener_todos(self) -> dict[str, float]:
        ...
