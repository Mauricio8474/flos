from tempfile import NamedTemporaryFile

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

from src.domain.models import ComponenteFormula, Formula
from src.domain.services import CalculadorMRP
from src.infrastructure.adapters.excel_reader import ExcelFormulasAdapter, ExcelInventarioAdapter

app = FastAPI(title="Flos MES", version="0.1.0")

RUTA_FORMULAS = "formulas.xlsx"

formulas_adapter = ExcelFormulasAdapter()
_formulas_cache: dict[str, Formula] | None = None


class ComponenteInput(BaseModel):
    sku: str
    porcentaje: float


class FormulaInput(BaseModel):
    id: str
    nombre: str
    componentes: list[ComponenteInput]


def _obtener_formulas() -> dict[str, Formula]:
    global _formulas_cache
    if _formulas_cache is None:
        _formulas_cache = formulas_adapter.leer_formulas(RUTA_FORMULAS)
    return _formulas_cache


@app.get("/produccion/formulas")
def listar_formulas() -> list[dict]:
    todas = _obtener_formulas()
    return [
        {
            "id": ref,
            "nombre": f.nombre,
            "componentes": [
                {"sku": c.sku, "porcentaje": c.porcentaje} for c in f.componentes
            ],
        }
        for ref, f in sorted(todas.items())
    ]


@app.get("/produccion/formulas/{id_formula}")
def obtener_formula(id_formula: str) -> dict:
    todas = _obtener_formulas()
    if id_formula not in todas:
        return {"error": f"Formula '{id_formula}' no encontrada"}
    f = todas[id_formula]
    return {
        "id": id_formula,
        "nombre": f.nombre,
        "componentes": [
            {"sku": c.sku, "porcentaje": c.porcentaje} for c in f.componentes
        ],
    }


@app.post("/produccion/formulas")
def crear_formula(body: FormulaInput) -> dict:
    todas = _obtener_formulas()
    if body.id in todas:
        return {"error": f"La formula '{body.id}' ya existe"}
    todas[body.id] = Formula(
        nombre=body.nombre,
        componentes=tuple(
            ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje)
            for c in body.componentes
        ),
    )
    return {"mensaje": f"Formula '{body.id}' creada", "componentes": len(body.componentes)}


@app.put("/produccion/formulas/{id_formula}")
def actualizar_formula(id_formula: str, body: FormulaInput) -> dict:
    todas = _obtener_formulas()
    if id_formula not in todas:
        return {"error": f"Formula '{id_formula}' no encontrada"}
    todas[id_formula] = Formula(
        nombre=body.nombre,
        componentes=tuple(
            ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje)
            for c in body.componentes
        ),
    )
    return {"mensaje": f"Formula '{id_formula}' actualizada", "componentes": len(body.componentes)}


@app.delete("/produccion/formulas/{id_formula}")
def eliminar_formula(id_formula: str) -> dict:
    todas = _obtener_formulas()
    if id_formula not in todas:
        return {"error": f"Formula '{id_formula}' no encontrada"}
    del todas[id_formula]
    return {"mensaje": f"Formula '{id_formula}' eliminada"}


@app.post("/produccion/calcular-explosion")
def calcular_explosion(
    archivo: UploadFile = File(...),
    id_formula: str = Form(...),
    cantidad_a_producir_kg: float = Form(...),
) -> list[dict]:
    todas = _obtener_formulas()

    if id_formula not in todas:
        disponibles = sorted(todas.keys())[:5]
        return [{
            "error": f"Formula '{id_formula}' no encontrada",
            "sugerencia": f"Usa GET /produccion/formulas para ver las disponibles. Ej: {disponibles}",
        }]

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
