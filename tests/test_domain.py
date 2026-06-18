import pytest

from src.domain.models import ComponenteFormula, Formula, ResultadoExplosion
from src.domain.services import CalculadorMRP, MaterialNoEncontradoError


class TestComponenteFormula:
    def test_creacion(self):
        c = ComponenteFormula(sku="MP001", porcentaje=25.0)
        assert c.sku == "MP001"
        assert c.porcentaje == 25.0

    def test_inmutabilidad(self):
        c = ComponenteFormula(sku="MP001", porcentaje=25.0)
        with pytest.raises(AttributeError):
            c.sku = "MP002"  # type: ignore


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


class TestCalculadorMRP:
    def test_explosion_cubierta(self):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=50.0),),
        )
        inventario = {"MP001": 100.0}
        resultados = CalculadorMRP.calcular_explosion(formula, 100, inventario)

        assert len(resultados) == 1
        r = resultados[0]
        assert r.sku == "MP001"
        assert r.requerido_kg == 50.0
        assert r.disponible_kg == 100.0
        assert r.faltante_kg == 0.0
        assert r.cubierto is True

    def test_explosion_con_faltante(self):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=80.0),),
        )
        inventario = {"MP001": 50.0}
        resultados = CalculadorMRP.calcular_explosion(formula, 100, inventario)

        assert len(resultados) == 1
        r = resultados[0]
        assert r.requerido_kg == 80.0
        assert r.disponible_kg == 50.0
        assert r.faltante_kg == 30.0
        assert r.cubierto is False

    def test_explosion_exacta(self):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=100.0),),
        )
        inventario = {"MP001": 100.0}
        resultados = CalculadorMRP.calcular_explosion(formula, 100, inventario)
        assert resultados[0].faltante_kg == 0.0
        assert resultados[0].cubierto is True

    def test_material_no_en_inventario(self):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=50.0),),
        )
        with pytest.raises(MaterialNoEncontradoError) as exc:
            CalculadorMRP.calcular_explosion(formula, 100, {})
        assert "MP001" in str(exc.value)

    def test_cantidad_cero_o_negativa(self):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="MP001", porcentaje=50.0),),
        )
        with pytest.raises(ValueError, match="mayor a 0"):
            CalculadorMRP.calcular_explosion(formula, 0, {"MP001": 100})
        with pytest.raises(ValueError, match="mayor a 0"):
            CalculadorMRP.calcular_explosion(formula, -10, {"MP001": 100})

    def test_multiples_componentes(self):
        formula = Formula(
            nombre="Multi",
            componentes=(
                ComponenteFormula(sku="A", porcentaje=30.0),
                ComponenteFormula(sku="B", porcentaje=50.0),
                ComponenteFormula(sku="C", porcentaje=20.0),
            ),
        )
        inventario = {"A": 100, "B": 100, "C": 100}
        resultados = CalculadorMRP.calcular_explosion(formula, 200, inventario)
        assert len(resultados) == 3
        assert resultados[0].requerido_kg == 60.0
        assert resultados[1].requerido_kg == 100.0
        assert resultados[2].requerido_kg == 40.0

    def test_redondeo(self):
        formula = Formula(
            nombre="Test",
            componentes=(ComponenteFormula(sku="X", porcentaje=33.3333),),
        )
        inventario = {"X": 10.0}
        r = CalculadorMRP.calcular_explosion(formula, 100, inventario)[0]
        assert r.requerido_kg == 33.333

    def test_resultado_dataclass(self):
        r = ResultadoExplosion(sku="X", requerido_kg=10.0, disponible_kg=5.0, faltante_kg=5.0, cubierto=False)
        assert r.sku == "X"
        assert r.cubierto is False
