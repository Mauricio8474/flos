from abc import ABC, abstractmethod

from src.domain.models import ComponenteFormula, Formula, ItemInventario


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
    def listar(self) -> dict[str, Formula]:
        ...

    @abstractmethod
    def eliminar(self, id_formula: str) -> bool:
        ...


class RepositorioInventario(ABC):
    @abstractmethod
    def guardar_muchos(self, items: list[ItemInventario]) -> None:
        ...

    @abstractmethod
    def obtener_todos(self) -> list[ItemInventario]:
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
    def listar(self, limite: int = 100) -> list[dict]:
        ...
