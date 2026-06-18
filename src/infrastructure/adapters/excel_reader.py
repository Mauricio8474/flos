from pathlib import Path

import openpyxl

from src.application.use_cases import PuertoInventario


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
