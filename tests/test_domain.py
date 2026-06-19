import pytest
from src.domain.models import (
    AlertaStock, ComponenteFormula, ControlCalidad, Formula,
    ItemInventario, LoteProduccion, ResultadoExplosion, SugerenciaCompra,
    ESTADOS_ORDEN, TRANSICIONES_ORDEN, validar_transicion_orden,
)
from src.domain.services import CalculadorMRP, GeneradorAlertasStock, GeneradorSugerenciasCompra


@pytest.fixture
def inventario():
    return {
        "MP001": ItemInventario(sku="MP001", nombre="Material A", cantidad_kg=100.0, costo_unitario=10.0),
        "MP002": ItemInventario(sku="MP002", nombre="Material B", cantidad_kg=50.0, costo_unitario=5.0),
        "MP003": ItemInventario(sku="MP003", nombre="Material C", cantidad_kg=0.0, costo_unitario=8.0),
    }


class TestComponenteFormula:
    def test_creacion(self):
        c = ComponenteFormula(sku="MP001", porcentaje=25.0)
        assert c.sku == "MP001"
        assert c.porcentaje == 25.0

    def test_inmutabilidad(self):
        c = ComponenteFormula(sku="MP001", porcentaje=25.0)
        with pytest.raises(AttributeError):
            c.sku = "MP002"

    def test_equality(self):
        a = ComponenteFormula(sku="X", porcentaje=10.0)
        b = ComponenteFormula(sku="X", porcentaje=10.0)
        assert a == b


class TestFormula:
    def test_creacion_con_componentes(self):
        f = Formula(
            nombre="Test",
            componentes=(
                ComponenteFormula(sku="A", porcentaje=60.0),
                ComponenteFormula(sku="B", porcentaje=40.0),
            ),
        )
        assert f.nombre == "Test"
        assert len(f.componentes) == 2


class TestItemInventario:
    def test_creacion(self):
        item = ItemInventario(sku="X", nombre="Test", cantidad_kg=50.0, costo_unitario=25.0)
        assert item.sku == "X"
        assert item.cantidad_kg == 50.0

    def test_stock_minimo_default(self):
        item = ItemInventario(sku="X", nombre="Test", cantidad_kg=10.0, costo_unitario=1.0)
        assert item.stock_minimo == 0.0


class TestCalculadorMRP:
    def test_explosion_cubierta(self, inventario):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=50.0),),
        )
        resultados = CalculadorMRP.calcular_explosion(formula, 100, inventario)
        assert len(resultados) == 1
        r = resultados[0]
        assert r.sku == "MP001"
        assert r.requerido_kg == 50.0
        assert r.disponible_kg == 100.0
        assert r.faltante_kg == 0.0
        assert r.cubierto is True
        assert r.nombre == "Material A"

    def test_explosion_con_faltante(self, inventario):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=200.0),),
        )
        resultados = CalculadorMRP.calcular_explosion(formula, 100, inventario)
        r = resultados[0]
        assert r.requerido_kg == 200.0
        assert r.faltante_kg == 100.0
        assert r.cubierto is False

    def test_material_sin_inventario(self, inventario):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="SKU_INEXISTENTE", porcentaje=50.0),),
        )
        resultados = CalculadorMRP.calcular_explosion(formula, 100, inventario)
        r = resultados[0]
        assert r.disponible_kg == 0.0
        assert r.faltante_kg == 50.0
        assert r.cubierto is False
        assert "no registrado" in r.nota.lower()

    def test_cantidad_cero_o_negativa(self, inventario):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=50.0),),
        )
        with pytest.raises(ValueError, match="mayor a 0"):
            CalculadorMRP.calcular_explosion(formula, 0, inventario)
        with pytest.raises(ValueError, match="mayor a 0"):
            CalculadorMRP.calcular_explosion(formula, -10, inventario)

    def test_multiples_componentes(self, inventario):
        formula = Formula(
            nombre="Multi",
            componentes=(
                ComponenteFormula(sku="MP001", porcentaje=30.0),
                ComponenteFormula(sku="MP002", porcentaje=50.0),
                ComponenteFormula(sku="MP003", porcentaje=20.0),
            ),
        )
        resultados = CalculadorMRP.calcular_explosion(formula, 200, inventario)
        assert len(resultados) == 3
        assert resultados[0].requerido_kg == 60.0
        assert resultados[1].requerido_kg == 100.0
        assert resultados[2].requerido_kg == 40.0

    def test_redondeo(self, inventario):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=33.3333),),
        )
        r = CalculadorMRP.calcular_explosion(formula, 100, inventario)[0]
        assert r.requerido_kg == 33.333

    def test_resultado_dataclass(self):
        r = ResultadoExplosion(sku="X", nombre="", requerido_kg=10.0, disponible_kg=5.0, faltante_kg=5.0, cubierto=False)
        assert r.sku == "X"
        assert r.cubierto is False


class TestEstadoOrden:
    def test_estados_validos(self):
        assert "pendiente" in ESTADOS_ORDEN
        assert "en_produccion" in ESTADOS_ORDEN
        assert "completada" in ESTADOS_ORDEN

    def test_transiciones_validas(self):
        assert TRANSICIONES_ORDEN["pendiente"] == "en_produccion"
        assert TRANSICIONES_ORDEN["en_produccion"] == "completada"

    def test_validar_transicion_ok(self):
        assert validar_transicion_orden("pendiente", "en_produccion") is None
        assert validar_transicion_orden("en_produccion", "completada") is None

    def test_validar_transicion_invalida(self):
        err = validar_transicion_orden("pendiente", "completada")
        assert err is not None
        assert "pendiente" in err

    def test_validar_transicion_desde_completada(self):
        err = validar_transicion_orden("completada", "pendiente")
        assert err is not None
        assert "no permite" in err.lower()


class TestGeneradorAlertasStock:
    def test_sin_alertas(self):
        inv = [ItemInventario(sku="X", nombre="X", cantidad_kg=100.0, costo_unitario=1.0, stock_minimo=0.0)]
        assert GeneradorAlertasStock.generar(inv) == []

    def test_alerta_generada(self):
        inv = [ItemInventario(sku="X", nombre="X", cantidad_kg=10.0, costo_unitario=1.0, stock_minimo=50.0)]
        alertas = GeneradorAlertasStock.generar(inv)
        assert len(alertas) == 1
        a = alertas[0]
        assert a.sku == "X"
        assert a.faltante == 40.0

    def test_alerta_solo_cuando_menor(self):
        inv = [ItemInventario(sku="X", nombre="X", cantidad_kg=60.0, costo_unitario=1.0, stock_minimo=50.0)]
        assert GeneradorAlertasStock.generar(inv) == []

    def test_orden_descendente_por_faltante(self):
        inv = [
            ItemInventario(sku="A", nombre="A", cantidad_kg=5.0, costo_unitario=1.0, stock_minimo=100.0),
            ItemInventario(sku="B", nombre="B", cantidad_kg=50.0, costo_unitario=1.0, stock_minimo=60.0),
        ]
        alertas = GeneradorAlertasStock.generar(inv)
        assert len(alertas) == 2
        assert alertas[0].sku == "A"
        assert alertas[0].faltante >= alertas[1].faltante


class TestGeneradorSugerenciasCompra:
    def test_desde_stock_minimo(self):
        inventario_list = [ItemInventario(sku="X", nombre="X", cantidad_kg=10.0, costo_unitario=1.0, stock_minimo=50.0)]
        sugerencias = GeneradorSugerenciasCompra.desde_stock_minimo(inventario_list)
        assert len(sugerencias) == 1
        assert sugerencias[0].origen == "stock_minimo"
        assert sugerencias[0].cantidad_requerida == 40.0

    def test_sin_ordenes_faltantes(self):
        sugerencias = GeneradorSugerenciasCompra.desde_faltantes_ordenes([], {})
        assert sugerencias == []


class TestControlCalidad:
    def test_creacion(self):
        c = ControlCalidad(id="1", id_orden="ORD-001", tipo="viscosidad")
        assert c.tipo == "viscosidad"
        assert c.resultado == "pendiente"
        assert c.observaciones == ""

    def test_resultado_aprobado(self):
        c = ControlCalidad(id="2", id_orden="ORD-001", tipo="ph", resultado="aprobado", observaciones="OK")
        assert c.resultado == "aprobado"
        assert c.observaciones == "OK"


class TestLoteProduccion:
    def test_creacion(self):
        l = LoteProduccion(id="1", id_orden="ORD-001", id_formula="F001", nombre_formula="Test", codigo_lote="L-001", cantidad_producida=100.0)
        assert l.codigo_lote == "L-001"
        assert l.estado == "activo"

    def test_estados(self):
        l = LoteProduccion(id="2", id_orden="ORD-001", id_formula="F001", nombre_formula="Test", codigo_lote="L-002", cantidad_producida=50.0, estado="liberado")
        assert l.estado == "liberado"
