from pathlib import Path

import openpyxl

from src.application.use_cases import PuertoFormulas, PuertoInventario
from src.domain.models import ComponenteFormula, Formula


class ExcelInventarioAdapter(PuertoInventario):
    COLUMNAS_REQUERIDAS = ("SKU", "Nombre", "Cantidad_KG")

    def __init__(
        self,
        fila_encabezados: int = 1,
        mapeo: dict[str, str] | None = None,
    ) -> None:
        self._fila_encabezados = fila_encabezados
        self._mapeo = mapeo or {}

    def leer_inventario(self, ruta: str) -> dict[str, float]:
        archivo = Path(ruta)

        if not archivo.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
        if archivo.suffix not in (".xlsx", ".xls"):
            raise ValueError(f"Formato no soportado: {archivo.suffix}")

        libro = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
        hoja = libro.active

        filas = list(hoja.iter_rows(values_only=True))
        if not filas:
            raise ValueError("El archivo Excel no contiene datos")

        idx_header = self._fila_encabezados - 1
        if idx_header >= len(filas):
            raise ValueError(
                f"Fila de encabezados {self._fila_encabezados} no existe "
                f"(el archivo tiene {len(filas)} filas)"
            )

        encabezados = [str(c).strip() if c is not None else "" for c in filas[idx_header]]

        if self._mapeo:
            col_sku = self._mapeo.get("SKU", "SKU")
            col_cant = self._mapeo.get("Cantidad_KG", "Cantidad_KG")
        else:
            col_sku = "SKU"
            col_cant = "Cantidad_KG"

        if col_sku not in encabezados:
            raise ValueError(
                f"Columna SKU ('{col_sku}') no encontrada. "
                f"Columnas: {encabezados}"
            )
        if col_cant not in encabezados:
            raise ValueError(
                f"Columna de cantidad ('{col_cant}') no encontrada. "
                f"Columnas: {encabezados}"
            )

        idx_sku = encabezados.index(col_sku)
        idx_cant = encabezados.index(col_cant)
        inventario: dict[str, float] = {}

        for fila in filas[idx_header + 1:]:
            sku = str(fila[idx_sku]).strip() if fila[idx_sku] is not None else ""
            if not sku:
                continue

            try:
                cantidad = float(fila[idx_cant]) if fila[idx_cant] is not None else 0.0
            except (ValueError, TypeError):
                cantidad = 0.0

            inventario[sku] = round(inventario.get(sku, 0.0) + cantidad, 3)

        return inventario


class ExcelFormulasAdapter(PuertoFormulas):
    HOJA = "formulas"
    COL_ID = 1  # B
    COL_SKU = 3  # D
    COL_KG = 11  # L

    def leer_formulas(self, ruta: str) -> dict[str, Formula]:
        archivo = Path(ruta)

        if not archivo.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

        libro = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
        hoja = libro[self.HOJA]

        filas = list(hoja.iter_rows(values_only=True))
        if not filas:
            raise ValueError("El archivo Excel no contiene datos")

        encabezados = [str(c).strip() if c is not None else "" for c in filas[0]]
        if len(encabezados) <= self.COL_KG:
            raise ValueError(
                f"Estructura de columnas inesperada. "
                f"Se esperaban al menos {self.COL_KG + 1} columnas, se encontraron {len(encabezados)}"
            )

        agrupadas: dict[str, list[ComponenteFormula]] = {}

        for fila in filas[1:]:
            ref = str(fila[self.COL_ID]).strip() if fila[self.COL_ID] is not None else ""
            sku = str(fila[self.COL_SKU]).strip() if fila[self.COL_SKU] is not None else ""
            kg = fila[self.COL_KG]

            if not ref or not sku:
                continue

            try:
                porcentaje = float(kg) if kg is not None else 0.0
            except (ValueError, TypeError):
                porcentaje = 0.0

            if ref not in agrupadas:
                agrupadas[ref] = []
            agrupadas[ref].append(ComponenteFormula(sku=sku, porcentaje=porcentaje))

        return {
            ref: Formula(nombre=ref, componentes=tuple(comps))
            for ref, comps in agrupadas.items()
        }
