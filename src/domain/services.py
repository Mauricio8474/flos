from src.domain.models import AlertaStock, ComponenteFormula, Formula, ItemInventario, ResultadoExplosion, SugerenciaCompra


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


class GeneradorAlertasStock:
    @staticmethod
    def generar(inventario: list[ItemInventario]) -> list[AlertaStock]:
        alertas: list[AlertaStock] = []
        for item in inventario:
            if item.stock_minimo > 0 and item.cantidad_kg < item.stock_minimo:
                alertas.append(AlertaStock(
                    sku=item.sku,
                    nombre=item.nombre,
                    cantidad_kg=item.cantidad_kg,
                    stock_minimo=item.stock_minimo,
                    faltante=round(item.stock_minimo - item.cantidad_kg, 3),
                ))
        return sorted(alertas, key=lambda a: a.faltante, reverse=True)


class GeneradorSugerenciasCompra:
    @staticmethod
    def desde_faltantes_ordenes(ordenes_con_faltantes: list[dict], inventario: dict[str, ItemInventario]) -> list[SugerenciaCompra]:
        sugerencias: dict[str, SugerenciaCompra] = {}
        for orden in ordenes_con_faltantes:
            for detalle in orden.get("detalles", []):
                if not detalle.get("cubierto") and detalle.get("faltante_kg", 0) > 0:
                    sku = detalle["sku"]
                    if sku not in sugerencias:
                        sugerencias[sku] = SugerenciaCompra(
                            sku=sku,
                            nombre=detalle.get("nombre", ""),
                            cantidad_requerida=0.0,
                            origen="orden_faltante",
                            id_orden=orden["id"],
                        )
                    existing = sugerencias[sku]
                    sugerencias[sku] = SugerenciaCompra(
                        sku=existing.sku,
                        nombre=existing.nombre,
                        cantidad_requerida=round(existing.cantidad_requerida + detalle["faltante_kg"], 3),
                        origen=existing.origen,
                        id_orden=existing.id_orden,
                    )
        return sorted(sugerencias.values(), key=lambda s: s.cantidad_requerida, reverse=True)

    @staticmethod
    def desde_stock_minimo(inventario: list[ItemInventario]) -> list[SugerenciaCompra]:
        return [
            SugerenciaCompra(
                sku=item.sku,
                nombre=item.nombre,
                cantidad_requerida=round(item.stock_minimo - item.cantidad_kg, 3),
                origen="stock_minimo",
            )
            for item in inventario
            if item.stock_minimo > 0 and item.cantidad_kg < item.stock_minimo
        ]
