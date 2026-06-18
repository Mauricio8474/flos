import io
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import openpyxl
import uvicorn
from fastapi import Depends, FastAPI, File, Form, Security, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

from src.infrastructure.auth import verificar_api_key

from src.domain.models import ComponenteFormula, Formula
from src.domain.services import CalculadorMRP
from src.infrastructure.adapters.excel_reader import ExcelFormulasAdapter, ExcelInventarioAdapter
from src.infrastructure.adapters.repositories import (
    PostgresRepositorioAuditoria,
    PostgresRepositorioFormula,
    PostgresRepositorioInventario,
    init_db,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("flos")

app = FastAPI(title="Flos MES", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard/")


@app.get("/dashboard/{rest:path}")
def dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))


class ComponenteInput(BaseModel):
    sku: str
    porcentaje: float


class FormulaInput(BaseModel):
    id: str
    nombre: str
    componentes: list[ComponenteInput]


@app.on_event("startup")
def startup():
    import os

    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://flos_admin:flos_secure_password@localhost:5432/flos_core")
    sf = init_db(db_url)
    app.state.sf = sf
    app.state.repo_formula = PostgresRepositorioFormula(sf)
    app.state.repo_inventario = PostgresRepositorioInventario(sf)
    app.state.repo_auditoria = PostgresRepositorioAuditoria(sf)


def _repo_formula() -> PostgresRepositorioFormula:
    return app.state.repo_formula


def _repo_inventario() -> PostgresRepositorioInventario:
    return app.state.repo_inventario


def _repo_auditoria() -> PostgresRepositorioAuditoria:
    return app.state.repo_auditoria


def _auditar(entidad: str, entidad_id: str, accion: str, detalle: str, api_key: str) -> None:
    _repo_auditoria().registrar(entidad, entidad_id, accion, detalle, api_key)


@app.get("/produccion/formulas", dependencies=[Depends(verificar_api_key)])
def listar_formulas() -> list[dict]:
    todas = _repo_formula().listar()
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


@app.get("/produccion/formulas/{id_formula}", dependencies=[Depends(verificar_api_key)])
def obtener_formula(id_formula: str) -> dict:
    f = _repo_formula().obtener(id_formula)
    if not f:
        return {"error": f"Formula '{id_formula}' no encontrada"}
    return {
        "id": id_formula,
        "nombre": f.nombre,
        "componentes": [
            {"sku": c.sku, "porcentaje": c.porcentaje} for c in f.componentes
        ],
    }


@app.post("/produccion/formulas")
def crear_formula(body: FormulaInput, api_key: str = Security(verificar_api_key)) -> dict:
    repo = _repo_formula()
    if repo.obtener(body.id):
        return {"error": f"La formula '{body.id}' ya existe"}
    repo.guardar(
        body.id,
        Formula(
            nombre=body.nombre,
            componentes=tuple(
                ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje) for c in body.componentes
            ),
        ),
    )
    _auditar("formula", body.id, "CREAR", f"{len(body.componentes)} componentes", api_key)
    return {"mensaje": f"Formula '{body.id}' creada", "componentes": len(body.componentes)}


@app.put("/produccion/formulas/{id_formula}")
def actualizar_formula(id_formula: str, body: FormulaInput, api_key: str = Security(verificar_api_key)) -> dict:
    repo = _repo_formula()
    if not repo.obtener(id_formula):
        return {"error": f"Formula '{id_formula}' no encontrada"}
    repo.guardar(
        id_formula,
        Formula(
            nombre=body.nombre,
            componentes=tuple(
                ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje) for c in body.componentes
            ),
        ),
    )
    _auditar("formula", id_formula, "ACTUALIZAR", f"{len(body.componentes)} componentes", api_key)
    return {"mensaje": f"Formula '{id_formula}' actualizada", "componentes": len(body.componentes)}


@app.delete("/produccion/formulas/{id_formula}")
def eliminar_formula(id_formula: str, api_key: str = Security(verificar_api_key)) -> dict:
    if _repo_formula().eliminar(id_formula):
        _auditar("formula", id_formula, "ELIMINAR", "", api_key)
        return {"mensaje": f"Formula '{id_formula}' eliminada"}
    return {"error": f"Formula '{id_formula}' no encontrada"}


@app.post("/produccion/cargar-formulas")
def cargar_formulas(api_key: str = Security(verificar_api_key)) -> dict:
    adapter = ExcelFormulasAdapter()
    formulas = adapter.leer_formulas("formulas.xlsx")
    repo = _repo_formula()
    for ref, formula in formulas.items():
        repo.guardar(ref, formula)
    _auditar("formula", "MASIVO", "CARGAR", f"{len(formulas)} formulas desde Excel", api_key)
    return {"mensaje": f"{len(formulas)} formulas cargadas desde formulas.xlsx"}


@app.post("/produccion/cargar-inventario")
def cargar_inventario(archivo: UploadFile = File(...), api_key: str = Security(verificar_api_key)) -> dict:
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(archivo.file.read())
        tmp_path = tmp.name

    adapter = ExcelInventarioAdapter()
    inventario = adapter.leer_inventario(tmp_path)
    _repo_inventario().guardar_muchos(inventario)
    _auditar("inventario", "MASIVO", "CARGAR", f"{len(inventario)} SKUs desde Excel", api_key)
    return {"mensaje": f"Inventario actualizado: {len(inventario)} SKUs"}


@app.get("/produccion/inventario", dependencies=[Depends(verificar_api_key)])
def obtener_inventario() -> dict[str, float]:
    return _repo_inventario().obtener_todos()


@app.get("/produccion/auditoria", dependencies=[Depends(verificar_api_key)])
def listar_auditoria(limite: int = 100) -> list[dict]:
    return _repo_auditoria().listar(limite)


@app.post("/produccion/calcular-explosion", dependencies=[Depends(verificar_api_key)])
def calcular_explosion(
    id_formula: str = Form(...),
    cantidad_a_producir_kg: float = Form(...),
) -> list[dict]:
    formula = _repo_formula().obtener(id_formula)
    if not formula:
        ids = sorted(_repo_formula().listar().keys())[:5]
        return [{
            "error": f"Formula '{id_formula}' no encontrada",
            "sugerencia": f"Usa GET /produccion/formulas. Ej: {ids}",
        }]

    inventario = _repo_inventario().obtener_todos()
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


@app.post("/produccion/calcular-explosion/excel", dependencies=[Depends(verificar_api_key)])
def calcular_explosion_excel(
    id_formula: str = Form(...),
    cantidad_a_producir_kg: float = Form(...),
) -> StreamingResponse:
    formula = _repo_formula().obtener(id_formula)
    if not formula:
        return StreamingResponse(
            iter([b"Formula no encontrada"]),
            media_type="text/plain",
            status_code=404,
        )

    inventario = _repo_inventario().obtener_todos()
    resultados = CalculadorMRP.calcular_explosion(formula, cantidad_a_producir_kg, inventario)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Explosion"
    ws.append(["SKU", "Requerido_KG", "Disponible_KG", "Faltante_KG", "Cubierto"])
    for r in resultados:
        ws.append([r.sku, r.requerido_kg, r.disponible_kg, r.faltante_kg, r.cubierto])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=explosion_{id_formula}.xlsx"},
    )


class OrdenBatch(BaseModel):
    id_formula: str
    cantidad: float


@app.post("/produccion/calcular-explosion/batch", dependencies=[Depends(verificar_api_key)])
def calcular_explosion_batch(ordenes: list[OrdenBatch]) -> list[dict]:
    inventario = _repo_inventario().obtener_todos()
    repo = _repo_formula()
    resultados_totales: list[dict] = []

    for orden in ordenes:
        formula = repo.obtener(orden.id_formula)
        if not formula:
            resultados_totales.append({
                "orden": orden.id_formula,
                "error": f"Formula '{orden.id_formula}' no encontrada",
            })
            continue
        try:
            resultados = CalculadorMRP.calcular_explosion(formula, orden.cantidad, inventario)
            for r in resultados:
                resultados_totales.append({
                    "orden": orden.id_formula,
                    "sku": r.sku,
                    "requerido_kg": r.requerido_kg,
                    "disponible_kg": r.disponible_kg,
                    "faltante_kg": r.faltante_kg,
                    "cubierto": r.cubierto,
                })
        except Exception as e:
            resultados_totales.append({
                "orden": orden.id_formula,
                "error": str(e),
            })

    return resultados_totales


@app.post("/produccion/calcular-explosion/pdf", dependencies=[Depends(verificar_api_key)])
def calcular_explosion_pdf(
    id_formula: str = Form(...),
    cantidad_a_producir_kg: float = Form(...),
) -> StreamingResponse:
    formula = _repo_formula().obtener(id_formula)
    if not formula:
        return StreamingResponse(iter([b"Formula no encontrada"]), media_type="text/plain", status_code=404)

    inventario = _repo_inventario().obtener_todos()
    resultados = CalculadorMRP.calcular_explosion(formula, cantidad_a_producir_kg, inventario)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    estilos = getSampleStyleSheet()

    elementos = []
    elementos.append(Paragraph(f"Explosion de Materiales: {id_formula}", estilos["Title"]))
    elementos.append(Paragraph(f"Cantidad a producir: {cantidad_a_producir_kg} kg", estilos["Normal"]))
    elementos.append(Paragraph("<br/>", estilos["Normal"]))

    data = [["SKU", "Requerido (kg)", "Disponible (kg)", "Faltante (kg)", "Cubierto"]]
    for r in resultados:
        data.append([r.sku, str(r.requerido_kg), str(r.disponible_kg), str(r.faltante_kg), "Si" if r.cubierto else "No"])

    tabla = Table(data)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#DCE6F1")]),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=explosion_{id_formula}.pdf"},
    )


if __name__ == "__main__":
    uvicorn.run("src.main:app", reload=True)
