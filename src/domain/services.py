from src.domain.models import ComponenteFormula, Formula, ResultadoExplosion


class MaterialNoEncontradoError(KeyError):
    def __init__(self, sku: str) -> None:
        super().__init__(f"Material con SKU '{sku}' no encontrado en el inventario")
        self.sku = sku


class CalculadorMRP:
    @staticmethod
    def calcular_explosion(
        formula: Formula,
        cantidad_a_producir_kg: float,
        inventario_actual: dict[str, float],
    ) -> list[ResultadoExplosion]:
        if cantidad_a_producir_kg <= 0:
            raise ValueError("cantidad_a_producir_kg debe ser mayor a 0")

        resultados: list[ResultadoExplosion] = []

        for comp in formula.componentes:
            if comp.sku not in inventario_actual:
                raise MaterialNoEncontradoError(comp.sku)

            requerido = (comp.porcentaje / 100.0) * cantidad_a_producir_kg
            disponible = inventario_actual[comp.sku]
            faltante = max(0.0, requerido - disponible)

            resultados.append(
                ResultadoExplosion(
                    sku=comp.sku,
                    requerido_kg=round(requerido, 3),
                    disponible_kg=round(disponible, 3),
                    faltante_kg=round(faltante, 3),
                    cubierto=faltante <= 0.0,
                )
            )

        return resultados
