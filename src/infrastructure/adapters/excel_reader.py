from pathlib import Path

import openpyxl

from src.application.use_cases import PuertoFormulas, PuertoInventario
from src.domain.models import ComponenteFormula, Formula


class ExcelInventarioAdapter(PuertoInventario):
    COLUMNAS_REQUERIDAS = ("SKU", "Nombre", "Cantidad_KG")

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

        encabezados = [str(c).strip() if c is not None else "" for c in filas[0]]
        for col in self.COLUMNAS_REQUERIDAS:
            if col not in encabezados:
                raise ValueError(
                    f"Columna requerida '{col}' no encontrada. "
                    f"Columnas encontradas: {encabezados}"
                )

        idx_sku = encabezados.index("SKU")
        idx_cant = encabezados.index("Cantidad_KG")
        inventario: dict[str, float] = {}

        for fila in filas[1:]:
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
