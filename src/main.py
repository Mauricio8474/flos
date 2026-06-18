from tempfile import NamedTemporaryFile

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile

from src.domain.models import ComponenteFormula, Formula
from src.domain.services import CalculadorMRP
from src.infrastructure.adapters.excel_reader import ExcelInventarioAdapter

app = FastAPI(title="Flos MES", version="0.1.0")

FORMULAS_MOCK: dict[str, Formula] = {
    "F-001": Formula(
        nombre="Esencias Tropicales",
        componentes=(
            ComponenteFormula(sku="ACEITE-BASE", porcentaje=60.0),
            ComponenteFormula(sku="AROMA-MANGO", porcentaje=25.0),
            ComponenteFormula(sku="COLORANTE-ROJO", porcentaje=15.0),
        ),
    ),
    "F-002": Formula(
        nombre="Brisa Marina",
        componentes=(
            ComponenteFormula(sku="ACEITE-BASE", porcentaje=50.0),
            ComponenteFormula(sku="AROMA-BRISAMAR", porcentaje=30.0),
            ComponenteFormula(sku="ESTABILIZANTE", porcentaje=20.0),
        ),
    ),
}


@app.post("/produccion/calcular-explosion")
def calcular_explosion(
    archivo: UploadFile = File(...),
    id_formula: str = Form(...),
    cantidad_a_producir_kg: float = Form(...),
) -> list[dict]:
    if id_formula not in FORMULAS_MOCK:
        return [{"error": f"Fórmula '{id_formula}' no encontrada"}]

    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(archivo.file.read())
        tmp_path = tmp.name

    adapter = ExcelInventarioAdapter()
    inventario = adapter.leer_inventario(tmp_path)

    formula = FORMULAS_MOCK[id_formula]
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
