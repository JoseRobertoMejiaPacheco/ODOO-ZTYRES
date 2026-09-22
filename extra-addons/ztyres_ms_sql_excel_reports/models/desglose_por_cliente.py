from odoo import api, fields, models
import os
from collections import defaultdict
from datetime import date
import pandas as pd

FECHA_DESDE = os.getenv("REPORTE_DESDE", "2026-05-01")
FECHA_HASTA = os.getenv("REPORTE_HASTA", "2026-12-31")
NUEVOS_DESDE = os.getenv("CLIENTES_NUEVOS_DESDE", FECHA_DESDE)

FILTRO_PRODUCTO = os.getenv("FILTRO_PRODUCTO", "").strip()

CLIENTES_EXCLUIDOS = (
    (11829, "305 TIRES LLC", "JUANA PATRICIA REYES GOMES"),
    (7468, "ACME INTERNATIONAL LLC", "JUANA PATRICIA REYES GOMES"),
    (11250, "ALWIN INDUSTRIAL CO.,LIMITED", "JUANA PATRICIA REYES GOMES"),
    (11763, "BODEGA AVANTE DE OCCIDENTE, Dirección de entrega", "JUANA PATRICIA REYES GOMES"),
    (7009, "CAR MOTION", "JUANA PATRICIA REYES GOMES"),
    (11297, "COMERCIALIZADORA TOPIK", "JUANA PATRICIA REYES GOMES"),
    (11299, "COMERZ OVER CROSS", "JUANA PATRICIA REYES GOMES"),
    (11633, "DANANG RUBBER JOINT STOCK COMPANY", "JUANA PATRICIA REYES GOMES"),
    (8370, "ECONOLLANTAS SERVICIOS Y ACCESORIOS", "JUANA PATRICIA REYES GOMES"),
    (11078, "EURO TRADE CONSULTING SRLS", "JUANA PATRICIA REYES GOMES"),
    (11079, "EURO TRADE CONSULTING SRLS, DAVIDE COCCO", "JUANA PATRICIA REYES GOMES"),
    (11815, "GABRIELA SANDRA CRUZ ORTEGA", "JUANA PATRICIA REYES GOMES"),
    (4824, "GENERAL HAESA", "JUANA PATRICIA REYES GOMES"),
    (11603, "HECTOR ENRIQUE ZUARTH ROJAS", "JUANA PATRICIA REYES GOMES"),
    (11092, "INTER-SPRINT BANDEN BV", "JUANA PATRICIA REYES GOMES"),
    (7107, "INTERNATIONAL TIRE CO. LTD", "JUANA PATRICIA REYES GOMES"),
    (11903, "International Tires 1 LLC", "JUANA PATRICIA REYES GOMES"),
    (11639, "KATANA RACING INC DBA WHOLESALE TIRE DISTRIBUTORS", "JUANA PATRICIA REYES GOMES"),
    (7366, "KUMHO TIRE DE MEXICO", "JUANA PATRICIA REYES GOMES"),
    (8838, "LLANTAS CAVAZOS", "RICARDO DE COSS"),
    (11810, "LLANTAS CAVAZOS (copia)", "RICARDO DE COSS"),
    (11196, "LLAVANTE", "JUANA PATRICIA REYES GOMES"),
    (11794, "MACSTER VENTURES INC", "JUANA PATRICIA REYES GOMES"),
    (7256, "MARIA GUADALUPE ROCIO HERNANDEZ VELASQUEZ", "JUANA PATRICIA REYES GOMES"),
    (7401, "NEUMAYR SLU", "JUANA PATRICIA REYES GOMES"),
    (11896, "PUBLICO EN GENERAL", "JUANA PATRICIA REYES GOMES"),
    (11309, "ROYAAL BANDEN", "JUANA PATRICIA REYES GOMES"),
    (11311, "ROYAAL BANDEN, SUC. WHEEL WORLD", "JUANA PATRICIA REYES GOMES"),
    (8644, "TIRE DIRECT", "JUANA PATRICIA REYES GOMES"),
    (8261, "VENTUS SPORT", "JUANA PATRICIA REYES GOMES"),
    (7091, "WORLDWIDE TIRE EXPORT", "JUANA PATRICIA REYES GOMES"),
    (7029, "ZURECO DE CHIAPAS", "JUANA PATRICIA REYES GOMES"),
)

IDS_CLIENTES_EXCLUIDOS = [registro[0] for registro in CLIENTES_EXCLUIDOS]

RANGOS = (
    (1, 99, "1-99"),
    (100, 199, "100-199"),
    (200, 399, "200-399"),
    (400, 699, "400-699"),
    (700, None, "700+"),
)

TIPOS_CLIENTE = {
    "1-99": "E",
    "100-199": "D",
    "200-399": "C",
    "400-699": "B",
    "700+": "A",
}

NOMBRES_MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

class desgloseporcliente(models.TransientModel):

    _name = 'desglose_por_cliente'

    def validar_fecha(self, valor, nombre):
        try:
            return date.fromisoformat(valor)
        except ValueError as exc:
            raise ValueError("%s debe tener formato AAAA-MM-DD" % nombre) from exc

    def meses_inclusivos(self, desde, hasta):
        actual = desde.replace(day=1)
        final = hasta.replace(day=1)
        resultado = []

        while actual <= final:
            resultado.append(actual)
            actual = date(
                actual.year + (1 if actual.month == 12 else 0),
                1 if actual.month == 12 else actual.month + 1,
                1,
            )

        return resultado

    def obtener_rango(self, cantidad):
        for minimo, maximo, etiqueta in RANGOS:
            if cantidad >= minimo and (maximo is None or cantidad <= maximo):
                return etiqueta

        return None

    def get_report(self):
        desde = self.validar_fecha(FECHA_DESDE, "REPORTE_DESDE")
        hasta = self.validar_fecha(FECHA_HASTA, "REPORTE_HASTA")
        nuevos_desde = self.validar_fecha(
            NUEVOS_DESDE,
            "CLIENTES_NUEVOS_DESDE"
        )

        if desde > hasta:
            raise ValueError(
                "REPORTE_DESDE no puede ser posterior a REPORTE_HASTA"
            )

        if nuevos_desde > hasta:
            raise ValueError(
                "CLIENTES_NUEVOS_DESDE no puede ser posterior a REPORTE_HASTA"
            )

        meses = self.meses_inclusivos(desde, hasta)
        claves_meses = [mes.strftime("%Y-%m") for mes in meses]

        dominio_lineas = [
            ("move_id.move_type", "in", ("out_invoice", "out_refund")),
            ("move_id.state", "=", "posted"),
            ("move_id.invoice_date", ">=", FECHA_DESDE),
            ("move_id.invoice_date", "<=", FECHA_HASTA),
            ("display_type", "=", "product"),
            ("product_id", "!=", False),
            ("product_id.detailed_type", "=", "product"),
            ("company_id", "in", self.env.companies.ids),
            ("move_id.partner_id", "not in", IDS_CLIENTES_EXCLUIDOS),
            ("move_id.commercial_partner_id", "not in", IDS_CLIENTES_EXCLUIDOS),
        ]

        if FILTRO_PRODUCTO:
            dominio_lineas += [
                "|",
                ("product_id.display_name", "ilike", FILTRO_PRODUCTO),
                ("product_id.categ_id.name", "ilike", FILTRO_PRODUCTO),
            ]

        lineas = self.env["account.move.line"].search(
            dominio_lineas,
            order="date, id",
        )

        cantidades = defaultdict(float)
        clientes_periodo = set()
        documentos = set()

        for linea in lineas:
            movimiento = linea.move_id
            cliente = movimiento.commercial_partner_id

            if not cliente:
                continue

            signo = -1.0 if movimiento.move_type == "out_refund" else 1.0
            mes = movimiento.invoice_date.strftime("%Y-%m")
            cantidades[(cliente.id, mes)] += linea.quantity * signo
            clientes_periodo.add(cliente.id)
            documentos.add(movimiento.id)

        primera_venta_por_cliente = {}

        if clientes_periodo:

            facturas_historicas = self.env["account.move"].search([
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", "<=", FECHA_HASTA),
                ("commercial_partner_id", "in", list(clientes_periodo)),
                ("company_id", "in", self.env.companies.ids),
                ("partner_id", "not in", IDS_CLIENTES_EXCLUIDOS),
                ("commercial_partner_id", "not in", IDS_CLIENTES_EXCLUIDOS),
            ], order="invoice_date, id")

            for factura in facturas_historicas:

                cliente_id = factura.commercial_partner_id.id

                if cliente_id not in primera_venta_por_cliente:
                    primera_venta_por_cliente[cliente_id] = factura.invoice_date

        clientes_regulares_ids = {
            cliente_id
            for cliente_id, primera_venta in primera_venta_por_cliente.items()
            if primera_venta < nuevos_desde
        }

        clientes = self.env["res.partner"].browse(
            sorted(clientes_periodo)
        )

        nombre_por_cliente = {
            cliente.id: cliente.display_name
            for cliente in clientes
        }

        creacion_por_cliente = {
            cliente.id: cliente.create_date
            for cliente in clientes
        }

        # Clientes que tienen al menos un mes dentro de algún bracket válido.
        clientes_con_volumen = [
            cliente_id
            for cliente_id in clientes_periodo
            if any(
                self.obtener_rango(cantidades[(cliente_id, mes)])
                for mes in claves_meses
            )
        ]

        clientes_con_volumen.sort(
            key=lambda cliente_id: (
                cliente_id not in clientes_regulares_ids,
                (nombre_por_cliente.get(cliente_id) or "").lower(),
            )
        )

        # ============================================================
        # DATAFRAME ÚNICO
        # Formato normalizado para tabla dinámica
        # ============================================================
        datos = []
        for cliente_id in clientes_con_volumen:
            es_regular = cliente_id in clientes_regulares_ids
            primera_venta = primera_venta_por_cliente.get(cliente_id)
            fecha_creacion = creacion_por_cliente.get(cliente_id)

            for mes in claves_meses:
                cantidad = cantidades[(cliente_id, mes)]
                bracket = self.obtener_rango(cantidad)
                # Si no pertenece a ningún bracket, no se incluye.
                if not bracket:
                    continue

                fecha_mes = date.fromisoformat(mes + "-01")

                datos.append({
                    "cliente_id": cliente_id,
                    "cliente": nombre_por_cliente.get(
                        cliente_id,
                        str(cliente_id)
                    ),
                    "creacion_cliente": fecha_creacion,
                    "primera_venta": primera_venta,
                    "clasificacion": "Regular" if es_regular else "Nuevo",
                    "mes": mes,
                    "mes_nombre": NOMBRES_MESES[fecha_mes.month],
                    "volumen_neto": cantidad,
                    "bracket": bracket,
                    "tipo_cliente": TIPOS_CLIENTE[bracket],
                })

        df_desglose_cliente = pd.DataFrame(
            datos,
            columns=[
                "cliente_id",
                "cliente",
                "creacion_cliente",
                "primera_venta",
                "clasificacion",
                "mes",
                "mes_nombre",
                "volumen_neto",
                "bracket",
                "tipo_cliente",
            ],
        )

        if not df_desglose_cliente.empty:
            df_desglose_cliente["creacion_cliente"] = pd.to_datetime(df_desglose_cliente["creacion_cliente"])
            df_desglose_cliente["primera_venta"] = pd.to_datetime(df_desglose_cliente["primera_venta"])
            df_desglose_cliente["mes"] = pd.to_datetime(df_desglose_cliente["mes"] + "-01")
        # ============================================================
        # INSERTAR EL ÚNICO DATAFRAME
        # ============================================================
        reports_core = self.env["ztyres_ms_sql_excel_core"].sudo()
        reports_core.action_insert_dataframe(df_desglose_cliente, "desglose_por_cliente")

        return 