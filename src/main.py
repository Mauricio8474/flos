import io
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import openpyxl
import uvicorn
from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

from src.infrastructure.auth import (
    crear_token,
    hash_password,
    obtener_usuario_actual,
    requerir_rol,
    verificar_password,
)

from src.domain.models import ComponenteFormula, Formula
from src.domain.services import CalculadorMRP
from src.infrastructure.adapters.excel_reader import ExcelFormulasAdapter, ExcelInventarioAdapter
from src.infrastructure.adapters.repositories import (
    PostgresRepositorioAuditoria,
    PostgresRepositorioFormula,
    PostgresRepositorioInventario,
    PostgresRepositorioUsuario,
    init_db,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("flos")

app = FastAPI(title="Flos MES", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard/")


@app.get("/dashboard/{rest:path}")
def dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class ComponenteInput(BaseModel):
    sku: str
    porcentaje: float


class FormulaInput(BaseModel):
    id: str
    nombre: str
    componentes: list[ComponenteInput]


class LoginInput(BaseModel):
    username: str
    password: str


class UsuarioInput(BaseModel):
    username: str
    password: str
    rol: str
    nombre: str


class OrdenBatch(BaseModel):
    id_formula: str
    cantidad: float


# ---------------------------------------------------------------------------
# Startup — repos + seed admin
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://flos_admin:flos_secure_password@localhost:5432/flos_core")
    sf = init_db(db_url)
    app.state.sf = sf
    app.state.repo_formula = PostgresRepositorioFormula(sf)
    app.state.repo_inventario = PostgresRepositorioInventario(sf)
    app.state.repo_auditoria = PostgresRepositorioAuditoria(sf)
    app.state.repo_usuarios = PostgresRepositorioUsuario(sf)

    repo_usu = app.state.repo_usuarios
    if not repo_usu.existe_admin():
        repo_usu.guardar("admin", hash_password("123456789"), "admin", "Administrador")
        logger.info("Usuario admin creado con contraseña por defecto")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _repo_formula():
    return app.state.repo_formula


def _repo_inventario():
    return app.state.repo_inventario


def _repo_auditoria():
    return app.state.repo_auditoria


def _repo_usuarios():
    return app.state.repo_usuarios


def _auditar(entidad: str, entidad_id: str, accion: str, detalle: str, usuario: str) -> None:
    _repo_auditoria().registrar(entidad, entidad_id, accion, detalle, usuario)


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
@app.post("/auth/login")
def login(body: LoginInput) -> dict:
    user = _repo_usuarios().obtener(body.username)
    if not user or not user.get("activo"):
        return {"error": "Usuario o contraseña incorrectos"}
    if not verificar_password(body.password, user["password_hash"]):
        return {"error": "Usuario o contraseña incorrectos"}
    token = crear_token(user["username"], user["rol"], user["nombre"])
    return {"access_token": token, "token_type": "bearer", "rol": user["rol"], "nombre": user["nombre"]}


@app.get("/auth/me")
def auth_me(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    return {"username": usuario["sub"], "rol": usuario["rol"], "nombre": usuario["nombre"]}


# ---------------------------------------------------------------------------
# Usuarios (solo admin)
# ---------------------------------------------------------------------------
@app.get("/usuarios", dependencies=[Depends(requerir_rol("admin"))])
def listar_usuarios() -> list[dict]:
    return _repo_usuarios().listar()


@app.post("/usuarios", dependencies=[Depends(requerir_rol("admin"))])
def crear_usuario(body: UsuarioInput) -> dict:
    if body.rol not in ("admin", "ingenieria", "almacen", "produccion", "consultor"):
        return {"error": f"Rol invalido: {body.rol}"}
    existe = _repo_usuarios().obtener(body.username)
    if existe:
        return {"error": f"Usuario '{body.username}' ya existe"}
    _repo_usuarios().guardar(body.username, hash_password(body.password), body.rol, body.nombre)
    return {"mensaje": f"Usuario '{body.username}' creado", "rol": body.rol}


@app.put("/usuarios/{username}", dependencies=[Depends(requerir_rol("admin"))])
def actualizar_usuario(username: str, body: UsuarioInput) -> dict:
    existe = _repo_usuarios().obtener(username)
    if not existe:
        return {"error": f"Usuario '{username}' no encontrado"}
    _repo_usuarios().guardar(username, hash_password(body.password), body.rol, body.nombre)
    return {"mensaje": f"Usuario '{username}' actualizado"}


@app.delete("/usuarios/{username}", dependencies=[Depends(requerir_rol("admin"))])
def eliminar_usuario(username: str) -> dict:
    repo = _repo_usuarios()
    user = repo.obtener(username)
    if not user:
        return {"error": f"Usuario '{username}' no encontrado"}
    repo.guardar(username, user["password_hash"], user["rol"], user["nombre"], activo=False)
    return {"mensaje": f"Usuario '{username}' desactivado"}


# ---------------------------------------------------------------------------
# Fórmulas
# ---------------------------------------------------------------------------
@app.get("/produccion/formulas", dependencies=[Depends(obtener_usuario_actual)])
def listar_formulas() -> list[dict]:
    todas = _repo_formula().listar()
    return [{"id": ref, "nombre": f.nombre, "componentes": [{"sku": c.sku, "porcentaje": c.porcentaje} for c in f.componentes]} for ref, f in sorted(todas.items())]


@app.get("/produccion/formulas/excel", dependencies=[Depends(obtener_usuario_actual)])
def descargar_formulas_excel() -> StreamingResponse:
    todas = _repo_formula().listar()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "formulas"
    ws.append(["REFERENCIA PRODUCTO TERMINADO", "MP", "MP POR REF", "fórmula en Kg"])
    for ref, f in sorted(todas.items()):
        for c in f.componentes:
            ws.append([ref, f.nombre, c.sku, c.porcentaje])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=formulas.xlsx"},
    )


@app.get("/produccion/formulas/{id_formula}", dependencies=[Depends(obtener_usuario_actual)])
def obtener_formula(id_formula: str) -> dict:
    f = _repo_formula().obtener(id_formula)
    if not f:
        return {"error": f"Formula '{id_formula}' no encontrada"}
    return {"id": id_formula, "nombre": f.nombre, "componentes": [{"sku": c.sku, "porcentaje": c.porcentaje} for c in f.componentes]}


@app.post("/produccion/formulas", dependencies=[Depends(requerir_rol("admin", "ingenieria"))])
def crear_formula(body: FormulaInput, usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    repo = _repo_formula()
    if repo.obtener(body.id):
        return {"error": f"La formula '{body.id}' ya existe"}
    repo.guardar(body.id, Formula(nombre=body.nombre, componentes=tuple(ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje) for c in body.componentes)))
    _auditar("formula", body.id, "CREAR", f"{len(body.componentes)} componentes", usuario["sub"])
    return {"mensaje": f"Formula '{body.id}' creada", "componentes": len(body.componentes)}


@app.put("/produccion/formulas/{id_formula}", dependencies=[Depends(requerir_rol("admin", "ingenieria"))])
def actualizar_formula(id_formula: str, body: FormulaInput, usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    repo = _repo_formula()
    if not repo.obtener(id_formula):
        return {"error": f"Formula '{id_formula}' no encontrada"}
    repo.guardar(id_formula, Formula(nombre=body.nombre, componentes=tuple(ComponenteFormula(sku=c.sku, porcentaje=c.porcentaje) for c in body.componentes)))
    _auditar("formula", id_formula, "ACTUALIZAR", f"{len(body.componentes)} componentes", usuario["sub"])
    return {"mensaje": f"Formula '{id_formula}' actualizada", "componentes": len(body.componentes)}


@app.delete("/produccion/formulas/{id_formula}", dependencies=[Depends(requerir_rol("admin", "ingenieria"))])
def eliminar_formula(id_formula: str, usuario: dict = Depends(obtener_usuario_actual)) -> dict:
    if _repo_formula().eliminar(id_formula):
        _auditar("formula", id_formula, "ELIMINAR", "", usuario["sub"])
        return {"mensaje": f"Formula '{id_formula}' eliminada"}
    return {"error": f"Formula '{id_formula}' no encontrada"}


@app.post("/produccion/cargar-formulas", dependencies=[Depends(requerir_rol("admin", "ingenieria"))])
def cargar_formulas(
    archivo: UploadFile = File(...),
    columna_id: int | None = Form(None),
    columna_mp: int | None = Form(None),
    columna_sku: int | None = Form(None),
    columna_kg: int | None = Form(None),
    usuario: dict = Depends(obtener_usuario_actual),
) -> dict:
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(archivo.file.read())
        tmp_path = tmp.name

    mapeo = {}
    if columna_id is not None:
        mapeo["ID"] = columna_id
    if columna_mp is not None:
        mapeo["MP"] = columna_mp
    if columna_sku is not None:
        mapeo["SKU"] = columna_sku
    if columna_kg is not None:
        mapeo["KG"] = columna_kg

    adapter = ExcelFormulasAdapter(mapeo=mapeo)
    formulas = adapter.leer_formulas(tmp_path)
    repo = _repo_formula()
    for ref, formula in formulas.items():
        repo.guardar(ref, formula)
    os.unlink(tmp_path)
    _auditar("formula", "MASIVO", "CARGAR", f"{len(formulas)} formulas desde Excel", usuario["sub"])
    return {"mensaje": f"{len(formulas)} formulas cargadas"}


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------
@app.post("/produccion/cargar-inventario", dependencies=[Depends(requerir_rol("admin", "ingenieria", "almacen"))])
def cargar_inventario(
    archivo: UploadFile = File(...),
    fila_encabezados: int = Form(1),
    columna_sku: str | None = Form(None),
    columna_nombre: str | None = Form(None),
    columna_cantidad: str | None = Form(None),
    columna_costo: str | None = Form(None),
    usuario: dict = Depends(obtener_usuario_actual),
) -> dict:
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(archivo.file.read())
        tmp_path = tmp.name

    mapeo = {}
    if columna_sku:
        mapeo["SKU"] = columna_sku
    if columna_nombre:
        mapeo["Nombre"] = columna_nombre
    if columna_cantidad:
        mapeo["Cantidad_KG"] = columna_cantidad
    if columna_costo:
        mapeo["CostoUnitario"] = columna_costo

    adapter = ExcelInventarioAdapter(fila_encabezados=fila_encabezados, mapeo=mapeo)
    inventario = adapter.leer_inventario(tmp_path)
    _repo_inventario().guardar_muchos(inventario)
    _auditar("inventario", "MASIVO", "CARGAR", f"{len(inventario)} SKUs desde Excel", usuario["sub"])
    return {"mensaje": f"Inventario actualizado: {len(inventario)} SKUs"}


@app.get("/produccion/inventario", dependencies=[Depends(obtener_usuario_actual)])
def obtener_inventario() -> list[dict]:
    items = _repo_inventario().obtener_todos()
    return [
        {
            "sku": i.sku,
            "nombre": i.nombre,
            "cantidad_kg": i.cantidad_kg,
            "costo_unitario": i.costo_unitario,
        }
        for i in items
    ]


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------
@app.get("/produccion/auditoria", dependencies=[Depends(requerir_rol("admin"))])
def listar_auditoria(limite: int = 100) -> list[dict]:
    return _repo_auditoria().listar(limite)


def _inventario_a_dict(items: list) -> dict[str, float]:
    return {i.sku: i.cantidad_kg for i in items}


# ---------------------------------------------------------------------------
# Explosión
# ---------------------------------------------------------------------------
@app.post("/produccion/calcular-explosion", dependencies=[Depends(requerir_rol("admin", "ingenieria", "produccion"))])
def calcular_explosion(id_formula: str = Form(...), cantidad_a_producir_kg: float = Form(...)) -> list[dict]:
    formula = _repo_formula().obtener(id_formula)
    if not formula:
        return [{"error": f"Formula '{id_formula}' no encontrada"}]
    inventario_dict = _inventario_a_dict(_repo_inventario().obtener_todos())
    return [{"sku": r.sku, "requerido_kg": r.requerido_kg, "disponible_kg": r.disponible_kg, "faltante_kg": r.faltante_kg, "cubierto": r.cubierto} for r in CalculadorMRP.calcular_explosion(formula, cantidad_a_producir_kg, inventario_dict)]


@app.post("/produccion/calcular-explosion/batch", dependencies=[Depends(requerir_rol("admin", "ingenieria", "produccion"))])
def calcular_explosion_batch(ordenes: list[OrdenBatch]) -> list[dict]:
    inventario = _inventario_a_dict(_repo_inventario().obtener_todos())
    repo = _repo_formula()
    resultados = []
    for orden in ordenes:
        formula = repo.obtener(orden.id_formula)
        if not formula:
            resultados.append({"orden": orden.id_formula, "error": "Formula no encontrada"})
            continue
        for r in CalculadorMRP.calcular_explosion(formula, orden.cantidad, inventario):
            resultados.append({"orden": orden.id_formula, "sku": r.sku, "requerido_kg": r.requerido_kg, "disponible_kg": r.disponible_kg, "faltante_kg": r.faltante_kg, "cubierto": r.cubierto})
    return resultados


def _generar_excel_resultados(resultados, id_formula) -> StreamingResponse:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Explosion"
    ws.append(["SKU", "Requerido_KG", "Disponible_KG", "Faltante_KG", "Cubierto"])
    for r in resultados:
        ws.append([r.sku, r.requerido_kg, r.disponible_kg, r.faltante_kg, r.cubierto])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=explosion_{id_formula}.xlsx"})


def _generar_pdf_resultados(resultados, id_formula, cantidad) -> StreamingResponse:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    estilos = getSampleStyleSheet()
    elementos = [
        Paragraph(f"Explosion de Materiales: {id_formula}", estilos["Title"]),
        Paragraph(f"Cantidad a producir: {cantidad} kg", estilos["Normal"]),
        Paragraph("<br/>", estilos["Normal"]),
    ]
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
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=explosion_{id_formula}.pdf"})


@app.post("/produccion/calcular-explosion/excel", dependencies=[Depends(requerir_rol("admin", "ingenieria", "almacen", "produccion"))])
def calcular_explosion_excel(id_formula: str = Form(...), cantidad_a_producir_kg: float = Form(...)) -> StreamingResponse:
    formula = _repo_formula().obtener(id_formula)
    if not formula:
        return StreamingResponse(iter([b"Formula no encontrada"]), media_type="text/plain", status_code=404)
    inventario_dict = _inventario_a_dict(_repo_inventario().obtener_todos())
    resultados = CalculadorMRP.calcular_explosion(formula, cantidad_a_producir_kg, inventario_dict)
    return _generar_excel_resultados(resultados, id_formula)


@app.post("/produccion/calcular-explosion/pdf", dependencies=[Depends(requerir_rol("admin", "ingenieria", "almacen", "produccion"))])
def calcular_explosion_pdf(id_formula: str = Form(...), cantidad_a_producir_kg: float = Form(...)) -> StreamingResponse:
    formula = _repo_formula().obtener(id_formula)
    if not formula:
        return StreamingResponse(iter([b"Formula no encontrada"]), media_type="text/plain", status_code=404)
    inventario_dict = _inventario_a_dict(_repo_inventario().obtener_todos())
    resultados = CalculadorMRP.calcular_explosion(formula, cantidad_a_producir_kg, inventario_dict)
    return _generar_pdf_resultados(resultados, id_formula, cantidad_a_producir_kg)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("src.main:app", reload=True)
