from tempfile import NamedTemporaryFile

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile

from src.domain.services import CalculadorMRP
from src.infrastructure.adapters.excel_reader import ExcelFormulasAdapter, ExcelInventarioAdapter

app = FastAPI(title="Flos MES", version="0.1.0")

RUTA_FORMULAS = "formulas.xlsx"

formulas_adapter = ExcelFormulasAdapter()


@app.post("/produccion/calcular-explosion")
def calcular_explosion(
    archivo: UploadFile = File(...),
    id_formula: str = Form(...),
    cantidad_a_producir_kg: float = Form(...),
) -> list[dict]:
    todas = formulas_adapter.leer_formulas(RUTA_FORMULAS)

    if id_formula not in todas:
        return [{"error": f"Fórmula '{id_formula}' no encontrada"}]

    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(archivo.file.read())
        tmp_path = tmp.name

    inventario_adapter = ExcelInventarioAdapter()
    inventario = inventario_adapter.leer_inventario(tmp_path)

    formula = todas[id_formula]
    resultados = CalculadorMRP.calcular_explosion(formula, cantidad_a_producir_kg, inventario)

    return [
        {
            "sku": r.sku,
            "requerido_kg": r.requerido_kg,
            "disponible_kg": r.disponible_kg,
            "faltante_kg": r.faltante_kg,
            "cubierto": r.cubierto,
        }
        for r in resultados
    ]


if __name__ == "__main__":
    uvicorn.run("src.main:app", reload=True)
