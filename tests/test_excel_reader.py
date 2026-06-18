import pytest

from src.infrastructure.adapters.excel_reader import ExcelInventarioAdapter


class TestExcelInventarioAdapter:
    def test_archivo_inexistente(self):
        adapter = ExcelInventarioAdapter()
        with pytest.raises(FileNotFoundError):
            adapter.leer_inventario("no_existe.xlsx")

    def test_extension_invalida(self, tmp_path):
        csv_path = tmp_path / "datos.csv"
        csv_path.write_text("a,b,c")
        adapter = ExcelInventarioAdapter()
        with pytest.raises(ValueError, match="Formato no soportado"):
            adapter.leer_inventario(str(csv_path))

    def test_excel_vacio(self, tmp_path):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.save(tmp_path / "vacio.xlsx")

        adapter = ExcelInventarioAdapter()
        with pytest.raises(ValueError, match="no contiene datos"):
            adapter.leer_inventario(str(tmp_path / "vacio.xlsx"))

    def test_faltan_columnas(self, tmp_path):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "Nombre"])
        wb.save(tmp_path / "sin_cantidad.xlsx")

        adapter = ExcelInventarioAdapter()
        with pytest.raises(ValueError, match="Columna requerida"):
            adapter.leer_inventario(str(tmp_path / "sin_cantidad.xlsx"))

    def test_lectura_correcta(self, tmp_path):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "Nombre", "Cantidad_KG"])
        ws.append(["MP001", "Material 1", 100.0])
        ws.append(["MP002", "Material 2", 50.5])
        wb.save(tmp_path / "inventario.xlsx")

        adapter = ExcelInventarioAdapter()
        resultado = adapter.leer_inventario(str(tmp_path / "inventario.xlsx"))

        assert resultado == {"MP001": 100.0, "MP002": 50.5}

    def test_sku_duplicado_se_acumula(self, tmp_path):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "Nombre", "Cantidad_KG"])
        ws.append(["MP001", "Material 1", 50.0])
        ws.append(["MP001", "Material 1 extra", 30.0])
        wb.save(tmp_path / "duplicados.xlsx")

        adapter = ExcelInventarioAdapter()
        resultado = adapter.leer_inventario(str(tmp_path / "duplicados.xlsx"))
        assert resultado["MP001"] == 80.0

    def test_cantidad_invalida_se_trata_como_cero(self, tmp_path):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "Nombre", "Cantidad_KG"])
        ws.append(["MP001", "Material 1", "invalido"])
        wb.save(tmp_path / "invalido.xlsx")

        adapter = ExcelInventarioAdapter()
        resultado = adapter.leer_inventario(str(tmp_path / "invalido.xlsx"))
        assert resultado["MP001"] == 0.0

    def test_celda_vacia_en_cantidad(self, tmp_path):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "Nombre", "Cantidad_KG"])
        ws.append(["MP001", "Material 1", None])
        wb.save(tmp_path / "vacio_cantidad.xlsx")

        adapter = ExcelInventarioAdapter()
        resultado = adapter.leer_inventario(str(tmp_path / "vacio_cantidad.xlsx"))
        assert resultado["MP001"] == 0.0
