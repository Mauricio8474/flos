from src.domain.models import ComponenteFormula, Formula, ItemInventario, ResultadoExplosion


class MaterialNoEncontradoError(KeyError):
    def __init__(self, sku: str) -> None:
        super().__init__(f"Material con SKU '{sku}' no encontrado en el inventario")
        self.sku = sku


class CalculadorMRP:
    @staticmethod
    def calcular_explosion(
        formula: Formula,
        cantidad_a_producir_kg: float,
        inventario_actual: dict[str, ItemInventario],
    ) -> list[ResultadoExplosion]:
        if cantidad_a_producir_kg <= 0:
            raise ValueError("cantidad_a_producir_kg debe ser mayor a 0")

        resultados: list[ResultadoExplosion] = []

        for comp in formula.componentes:
            item = inventario_actual.get(comp.sku)
            requerido = (comp.porcentaje / 100.0) * cantidad_a_producir_kg
            disponible = item.cantidad_kg if item else 0.0
            nombre = item.nombre if item else "(No encontrado en inventario)"
            faltante = max(0.0, requerido - disponible)
            nota = "" if item else f"Material con SKU '{comp.sku}' no registrado en inventario"

            resultados.append(
                ResultadoExplosion(
                    sku=comp.sku,
                    nombre=nombre,
                    requerido_kg=round(requerido, 3),
                    disponible_kg=round(disponible, 3),
                    faltante_kg=round(faltante, 3),
                    cubierto=faltante <= 0.0,
                    nota=nota,
                )
            )

        return resultados
