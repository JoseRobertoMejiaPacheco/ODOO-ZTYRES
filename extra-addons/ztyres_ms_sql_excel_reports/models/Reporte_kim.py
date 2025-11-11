import pandas as pd
import math
from datetime import datetime, date

status_clientes = [
('LUIS FERNANDO CALLEJA VILLALOBOS', 'Regular'),
('HECTOR MANUEL GONZALEZ PIÑA', 'Regular'),
('TIRECLICK.COM', 'Regular'),
('AUTO LLANTAS ANDRADE', 'Regular'),
('MARTIN GONZALEZ ZAMUDIO', 'Regular'),
('COMERCIALIZADORA MUNVER', 'pago inmediato'),
('BODEGA GENERAL DE LLANTAS', 'Regular'),
('LAURA VIRGINIA AYALA VELAZQUEZ', 'Regular'),
('REFACCIONES ORIGINALES DEL BAJIO', 'Regular'),
('JOSE MARIA VAZQUEZ HERNANDEZ', 'Regular'),
('MANUEL ALEJANDRO SAUCEDO ROJAS', 'pago inmediato'),
('EURO RINES', 'Regular'),
('KARTISIMO BAJIO', 'Regular'),
('KARTISIMO', 'Regular'),
('MARRUFO ORTEGA', 'Regular'),
('MR TIRES', 'pago inmediato'),
('COMERCIALIZADORA REMV', 'Regular'),
('MONICA LEON DIAZ', 'Regular'),
('MIRIAM MARIANA VILLALOBOS ORTEGA', 'Regular'),
('LUIS HERRERA ESPINOZA', 'Regular'),
('TECNICENTRO DE LAGOS', 'Regular'),
('JUAN FILIBERTO LEON MEZA', 'Regular'),
('MERCANEUMATICOS', 'pago inmediato'),
('LAURA ANGELICA HERNANDEZ SANCHEZ', 'Regular'),
('LUIS HERRERA ELIZALDE', 'Regular'),
('OMAR ALEXANDRO GOVEA MARTINEZ', 'pago inmediato'),
('IDEAL LLANTA', 'Moroso'),
('ROY DE JESUS HERRERA ESPINOZA', 'Regular'),
('MIGUEL IGNACIO ZEPEDA QUIROZ', 'Regular'),
('ANA KAREN GARCIA GOMEZ', 'pago inmediato'),
('MULTILLANTAS NUEVA ITALIA', 'Regular'),
('LLANTERA SEN', 'Regular'),
('MARIA ESTELA ZAMUDIO TISNADO', 'Regular'),
('AARON OSVALDO PALOMINO LERMA', 'Regular'),
('JOSE ALEJANDRO GONTES GARCIA', 'Moroso'),
('FRANCISCO JAVIER ARREGUI VALENCIA', 'Regular'),
('RINES Y LLANTAS LOS ANGELES', 'Regular'),
('SALVADOR SANTOYO CORTES', 'Regular'),
('JOSE MAURICIO NORIEGA PADILLA', 'pago inmediato'),
('COMERCIALIZADORA DE VEHICULOS Y REFACCIONES DE OCCIDENTE', 'Regular'),
('IRMA LOPEZ ROCHA', 'pago inmediato'),
('COMERCIALIZADORA DE LLANTAS, REFACCIONES Y ACCESORIOS CAR', 'pago inmediato'),
('ALDAHIR ANTONIO LOPEZ SERAFIN', 'Moroso'),
('GRUPO ROAD INNOVATION', 'Regular'),
('MTRBN', 'Regular'),
('MANUEL GONZALEZ GONZALEZ', 'Regular'),
('SERGIO BARRETO MONTIEL', 'pago inmediato'),
('GONTEZ MULTILLANTAS', 'Moroso'),
('ALFREDO ORTIZ ALVARADO', 'Regular'),
('LLANTAS ROJAVE DE ZACATECAS', 'Regular'),
('DANIELA ADRIANA JIMENEZ BENITEZ', 'Regular'),
('WORLDWIDE TIRE EXPORT', 'Regular'),
('MARIA DOLORES MARTIN NAVARRO', 'Regular'),
('LLANTAS Y RINES ARREOLA', 'Regular'),
('MULTISERVICIOS CIR', 'Regular'),
('KARINA LOPEZ MIRANDA', 'Regular'),
('LAURA PATRICIA MONSERRAT HERNANDEZ RAYAS', 'Regular'),
('MAURICIO ALVA MARTINEZ', 'Moroso'),
('ROCIO LIZBETH MORENO MILAN', 'Moroso'),
('MAURICIO ALEJANDRO LOPEZ DE LA CRUZ', 'pago inmediato'),
('FRESNILLANTAS TORNEL', 'Regular'),
('JOEL MEJIA CHAVEZ', 'Regular'),
('SUPREME TIRES MX', 'Regular'),
('MARIA EUGENIA GOVEA VILLANUEVA', 'Regular'),
('JULIO OCTAVIO ZEPEDA OCEGUEDA', 'Regular'),
('JORGE DE JESUS PIÑA', 'Regular'),
('JANETH BERENICE RODRIGUEZ SAINZ', 'Regular'),
('ELIZABETH DE JESUS CALDERON', 'Regular'),
('VICTOR AIME SOULE HERNANDEZ', 'pago inmediato'),
('MARINA RENTERIA SAAVEDRA', 'Regular'),
('MANTENIMIENTO SERVICIOS Y PRODUCTOS AVILA', 'Regular'),
('SUMINISTRADORA DE LLANTAS LA SALTILLENSE', 'Regular'),
('DIEGO RAMOS ARTEAGA', 'Regular'),
('GLORIA DIAZ LUGO', 'Regular'),
('ORBELI MONTAÑO FIGUEROA', 'Regular'),
('PIÑA PALOMINO', 'Regular'),
('LLANTAS Y MONTAJES DEL HUMAYA', 'Regular'),
('ALAN MIMICH GONZALEZ CIFUENTES', 'pago inmediato'),
('SOFIA GONZALEZ RUIZ', 'Moroso'),
('JOSE LUIS ALBA CHAVEZ', 'Regular'),
('LEXUS TIRE CENTER', 'Moroso'),
('MARTA ELENA AYALA TAHUADO', 'Regular'),
('HERPECA', 'Regular'),
('AVRIL MERITT PEREZ HERNANDEZ', 'Regular'),
('ROBERTO GONTES LEON', 'Moroso'),
('OLGA VILLALOBOS VALDIVIA', 'Regular'),
('ANA MARIA CASTILLO RAMOS', 'Regular'),
('BRENDA MARIANA RODRIGUEZ SAINZ', 'Regular'),
('LUIS FERNANDO MENDOZA NILA', 'pago inmediato'),
('JOSE MANUEL MEJIA CEDEÑO', 'Regular'),
('JULIO CESAR RAMOS ARTEAGA', 'Regular'),
('DANIEL BAUTISTA REYES', 'Regular'),
('TEREZA GARCIA MERCADO', 'Moroso'),
('GRUPO SANART DEL PACIFICO', 'pago inmediato'),
('JUANA YASMIN PANTOJA LOPEZ', 'Regular'),
('JOSE JAVIER LEON LOPEZ', 'pago inmediato'),
('JAIRO URIEL RODRIGUEZ LOPEZ', 'Regular'),
('ADAN MUÑOZ MUÑOZ', 'pago inmediato'),
('ANA GUADALUPE RODRIGUEZ BUCIO', 'pago inmediato'),
('MARTHA CLARA ORTIZ GUTIERREZ', 'Regular'),
('LUCIA ZAMORA ROSADO', 'pago inmediato'),
('SERVAL LLANTAS Y SERVICIOS DE CALVILLO', 'pago inmediato'),
('RAMONA LIDIA APODACA HIGUERA', 'pago inmediato'),
('HORACIO CASTRO ANGULO', 'Regular'),
('TIRE TEK CENTER', 'pago inmediato'),
('MARIA DE JESUS PARRA ARIAS', 'Regular'),
('COMERCIALIZADORA RA', 'Regular'),
('NEUMATICOS IMPERIO', 'pago inmediato'),
('ALBERTO ISAAC SALAS NAVA', 'pago inmediato'),
('LLANTAS Y SERVICIOS SALAZAR', 'Regular'),
('JUAN MANUEL LEON LLAMAS', 'pago inmediato'),
('IMELDA SOFIA CERNA CISNEROS', 'Regular'),
('RINES Y LLANTAS AVILA', 'Regular'),
('JOSE DONACIANO ARROYO PARAMO', 'Regular'),
('LUIS FERNANDO HOROWICH MEDINA', 'Regular'),
('ADAN MUÑOZ PLASCENCIA', 'pago inmediato'),
('ANGEL ARTURO UNGSON VALDEZ', 'pago inmediato'),
('SUPER SPORT RINES Y LLANTAS', 'pago inmediato'),
('MARIA DEL CARMEN NORIEGA ZAMOREZ', 'pago inmediato'),
('VICTOR ALFONSO CARDENAS SANCHEZ', 'Regular'),
('ALEJANDRA ZUÑIGA LEON', 'pago inmediato'),
('ABRAHAM ALMIRUDIS SILVA', 'pago inmediato'),
('GASOLLANTAS', 'Regular'),
('DELFINO NUÑEZ MANDUJANO', 'Regular'),
('ELIZABETH PEREZ LOPEZ', 'Regular'),
('SALVADOR SANDOVAL VERDUZCO', 'pago inmediato'),
('MARISOL GONZALEZ MENDOZA', 'Moroso'),
('OSCAR JESUS ESPINOS GOMEZ', 'pago inmediato'),
('DISTRIBUCION Y LOGISTICA MAC', 'Regular'),
('MIGUEL ANGEL RAMIREZ JIMENEZ', 'pago inmediato'),
('LIZANDRO DAMIAN LUNA HERNANDEZ', 'pago inmediato'),
('MARIA DE LOURDES HERNANDEZ PEREZ', 'Regular'),
('MULTISERVICIOS AYON', 'pago inmediato'),
('VENTUS SPORT', 'Regular'),
('MARIO ALBERTO DIAZ VAZQUEZ', 'pago inmediato'),
('ANA KAREN GALLEGOS ARANDA', 'pago inmediato'),
('COMERCIALIZADORA ARCEVI', 'pago inmediato'),
('ACEROS Y MATERIALES DEL NORESTE', 'Regular'),
('LLANTAS ROYAL DE SINALOA', 'Moroso'),
('LLANTAS Y SERVICIOS SANMAR', 'Regular'),
('DISTRIBUIDORA DE LLANTAS GUZMAN', 'Regular'),
('FRANCISCO JAVIER LUGO MEJIA', 'Regular'),
('JOSE LUIS ALBA PALOMINO', 'Regular'),
('KAREN PALOMA ZARAHI PORRAS LOZA', 'pago inmediato'),
('GRUPO DILLAR', 'pago inmediato'),
('LLANTERA COSTERA DEL PACIFICO', 'Regular'),
('NEUMARKET DE MEXICO', 'pago inmediato'),
('OSCAR ADRIAN HIGUERA MARTINEZ', 'Moroso'),
('PÚBLICO EN GENERAL', 'pago inmediato'),
('LLANTISERVICIOS EL MONTE', 'pago inmediato'),
('JUAN CARLOS TOVAR HERREJON', 'Regular'),
('EDUARDO GARCIA BLANCO', 'pago inmediato'),
('JORGE MANUEL CALIXTO LOPEZ', 'Regular'),
('EDUARDO GAVITO HEREDIA', 'pago inmediato'),
('LLANTAS REALCO', 'pago inmediato'),
('MARIA DEL SOCORRO HUANOSTO GUILLEN', 'Regular'),
('JAIME AGUILERA CRISTOBAL', 'pago inmediato'),
('COMERCIAL LLANTERA DE LAGOS', 'pago inmediato'),
('LEON AUTOMOTRIZ', 'pago inmediato'),
('RUBEN AYALA QUINTERO', 'Moroso'),
('LUIS FABIAN AYALA MARTINEZ', 'Regular'),
('MARIA PAULA RODRIGUEZ MORALES', 'pago inmediato'),
('VICTOR HUGO VARGAS ZARAGOZA', 'Moroso'),
('NEUMATICOS Y RINES INDUSTRIALES', 'Moroso'),
('ROCIO HERMOSILLO MUÑOZ', 'pago inmediato'),
('JUAN JAIME MENDOZA ROMERO', 'Regular'),
('VENTA A EMPLEADOS', 'Regular'),
('LLANTAS Y SERVICIOS ABASTOS', 'Regular'),
('REFACCIONARIA LEONESA', 'pago inmediato'),
('GERARDO GARCIA BALVER', 'pago inmediato'),
('FRANCISCO JAVIER ZAMBRANO REYNOSO', 'pago inmediato'),
('DIANA LAURA HURTADO BARRON', 'Regular'),
('DUYERA TIRE', 'Regular'),
('RINES Y LLANTAS DE GDL', 'Moroso'),
('RAMIRO ROSALES BORREGO', 'Regular'),
('LUIS HERNANDEZ SANCHEZ', 'pago inmediato'),
('GENERAL TIRE DE LA COSTA', 'Regular'),
('ZURECO DE CHIAPAS', 'Regular'),
('JOSE CRUZ RODRIGUEZ RODRIGUEZ', 'Regular'),
('JOSE DE JESUS GONZALEZ OROZCO', 'pago inmediato'),
('INES PATRICIA SANTIAGO CALDERON', 'Regular'),
('ADOLFO MARQUEZ MOJICA', 'pago inmediato'),
('NEACCSA', 'pago inmediato'),
('DAVID RIVERA HERNANDEZ', 'pago inmediato'),
('FELIX PABLO DIAZ AVILA', 'Regular'),
('COMERCIALIZADORA PEGUZA', 'Moroso'),
('JUAN FRANCISCO MARTINEZ RIVERA', 'pago inmediato'),
('ANDRES IVAN GONZALEZ CUEVAS', 'pago inmediato'),
('AR MARKETING', 'pago inmediato'),
('NICOLAS BALTAZAR PALACIOS', 'pago inmediato'),
('PELAYO SERVICIO AUTOMOTRIZ', 'pago inmediato'),
('JMC LLANTAS DE ALTAMIRA', 'pago inmediato'),
('RAUL YEPEZ SANDOVAL', 'pago inmediato'),
('DISTRIBUIDORA ESPECIALIZADA VIPLA', 'pago inmediato'),
('MARIA DE LOURDES ABREGO GUZMAN', 'Regular'),
('MARTHA ALICIA LOPEZ MALLARES', 'pago inmediato'),
('JUAN CARLOS DIAZ RIZO', 'pago inmediato'),
('CARLOS IVAN LOZA ANGEL', 'pago inmediato'),
('JOSE LUIS GUTIERREZ REYES', 'Regular'),
('CIPRIANO ONTIVEROS CAMPOS', 'Moroso'),
('JUAN CARLOS ALCOCER CHALICO', 'Regular'),
('LLANTERA DE CULIACAN', 'Regular'),
('LUZ ESTELA GARNICA CONTRERAS', 'pago inmediato'),
('MARIA EUGENIA PLASCENCIA GARCIA', 'pago inmediato'),
('EMMANUEL CARBAJAL ZEPEDA', 'Moroso'),
('JULIAN ALBERTO SAMBRANO', 'pago inmediato'),
('JORGE ALBERTO PEREA LOPEZ', 'pago inmediato'),
('MOISEIS GARCIA MEJIA', 'pago inmediato'),
('LUIS FRANCISCO ROSAS VERGARA', 'pago inmediato'),
('CESAR ALEJANDRO GUTIERREZ REYES', 'pago inmediato'),
('JOSE MANUEL GONZALEZ MERCADO', 'pago inmediato'),
('ALDO CECILIO JIMENEZ PUENTE', 'pago inmediato'),
('LUIS GERARDO HURTADO BARRON', 'pago inmediato'),
('PAULA PATRICIA ESPINOZA BARRAGAN', 'pago inmediato'),
('TERESA DE JESUS BELTRAN PACHUCA', 'pago inmediato'),
('JOSE ANTONIO ABONCE VILLAGOMEZ', 'Moroso'),
('HUGO LAGARDA PALMA', 'pago inmediato'),
('ACACIA ROCIO ENRIQUEZ RAMOS', 'pago inmediato'),
('CHRISTIAN IVAN MARTINEZ VALDOVINO', 'pago inmediato'),
('NEUMAYR SLU', 'pago inmediato'),
('JUAN EMILIO SILVA ZIMBRON', 'Regular'),
('LLANTAS CENTER XL', 'pago inmediato'),
('ESPERANZA ROSAS GUERRERO', 'pago inmediato'),
('SUELAS WYNY', 'pago inmediato'),
('ARCHIBALDO FERNANDO ARANDA MUÑIZ', 'pago inmediato'),
('PEDRO NAZARENO GONZALEZ SILVA', 'pago inmediato'),
('COMERCIALIZADORA AZUL RAFAGA', 'Regular'),
('DIEGO GUZMAN GARCIA', 'pago inmediato'),
('JUANA ERIKA GALVAN MARTINEZ', 'pago inmediato'),
('VRAMA PRODUCTOS PARA LA INDUSTRIA', 'pago inmediato'),
('INTERNATIONAL TIRE CO. LTD', 'pago inmediato'),
('FRANCISCO EMMANUEL PEREZ CASTRO', 'Moroso'),
('AGROCOMERCIALIZADORA DEL CAMPO UNIDAD SUTACI', 'Regular'),
('COMERCIALIZADORA SSC', 'pago inmediato'),
('JOSE FRANCISCO ALVA MARTINEZ', 'pago inmediato'),
('COMERCIALIZADORA TOPIK', 'Regular'),
('COMERZ OVER CROSS', 'Regular'),
('FRANCISCO JAVIER LOZANO ZAZUETA', 'pago inmediato'),
('NOVOCART', 'pago inmediato'),
('ESTEFANIA SERRANO REYNOSO', 'pago inmediato'),
('JAIME DEL RIO MENDOZA', 'Moroso'),
('KENNY SARAHI DE LILI GALDAMES BELLO', 'pago inmediato'),
('LLANTERA GUZMAN', 'pago inmediato'),
('GONZALO ZAPATERO OÑATE', 'pago inmediato'),
('KEVIN YERAY GARCIA MERCADO', 'Moroso'),
('MARGARITA HERNANDEZ GUTIERREZ', 'pago inmediato'),
('BETSY JEANINE OSORIO NIQUET', 'pago inmediato'),
('SUPER LLANTAS MORALES', 'pago inmediato'),
('CARLOS ALBERTO AVENDAÑO SOLIS', 'pago inmediato'),
('CAR MOTION', 'Regular'),
('ELVIRA JUAREZ ANDRADE', 'pago inmediato'),
('KARLA FABIOLA ALMANZA HURTADO', 'pago inmediato'),
('LLANTERA LOMELI', 'Moroso'),
('TIRE DIRECT', 'Regular'),
('FRANCISCO VAZQUEZ RODRIGUEZ', 'pago inmediato'),
('GENERAL HAESA', 'pago inmediato'),
('OFERLLANTAS', 'Regular'),
('RODOLFO SIFUENTES PALACIOS', 'Regular'),
('SUPER LLANTAS DEL PACIFICO', 'pago inmediato'),
('OMAR ALEJANDRO ZARAGOZA ARELLANO', 'pago inmediato'),
('GUZMAN TIRE IMPORTER', 'pago inmediato'),
('DAVID ERNESTO GUZMAN LOPEZ', 'pago inmediato'),
('JUAN ANTONIO HERNANDEZ ALVAREZ', 'pago inmediato'),
('TIRE EXPRESS', 'Regular'),
('BBVA SEGUROS MEXICO, S.A. DE C.V., GRUPO FINANCIER', 'pago inmediato'),
('EUROLLANTAS DE SAN LUIS', 'Regular'),
('LUIS ERNESTO PEREZ PEÑA', 'pago inmediato'),
('CARLOS ARTURO VENECIA NAVARRO', 'pago inmediato'),
('CRISTIAN STENNER PANIAGUA', 'pago inmediato'),
('GUILLERMINA MORENO CAFUENTES', 'pago inmediato'),
('INTER-SPRINT BANDEN BV', 'pago inmediato'),
('LLANTAS Y SERVICIOS CORTES DE URUAPAN', 'pago inmediato'),
('LLANTAS Y ACCESORIOS', 'Regular'),
('ACME INTERNATIONAL LLC', 'pago inmediato'),
('JUAN MANUEL CORONA AISPURO', 'pago inmediato'),
('DARIANA JANETH OROZCO VAZQUEZ', 'pago inmediato'),
('JOSE DE JESUS VALLIN DIAZ', 'pago inmediato'),
('LLANTIRED', 'pago inmediato'),
('JOSE DE JESUS GUZMAN PALOMARES', 'pago inmediato'),
('LLANTERA PAVA', 'pago inmediato'),
('ROYAAL BANDEN', 'pago inmediato'),
('CONZUELO GOMEZ COLLAZO', 'pago inmediato'),
('COMERCIALIZADORA LOYGA', 'pago inmediato'),
('FATIMA MARIANA MARES MORENO', 'pago inmediato'),
('KATANA RACING INC DBA WHOLESALE TIRE  DISTRIBUTORS', 'pago inmediato'),
('MARIA GUADALUPE ROCIO HERNANDEZ VELASQUEZ', 'pago inmediato'),
('DIMAS FERNANDEZ ARIADNA', 'pago inmediato'),
('JOSE LUIS ARRIAGA LOPEZ', 'pago inmediato'),
('JOSE RENE VALENZUELA CASTRO', 'pago inmediato'),
('JUANA SUSANA GARCIA SETURINO', 'pago inmediato'),
('LAZOS EN TRANSPORTE Y SERVICIOS LOGISTICOS SA DE CV', 'pago inmediato'),
('LLAVANTE', 'pago inmediato'),
('DANIELA ORTIZ DE MONTELLANO DE LILI GALDAMES', 'pago inmediato'),
('JOAN ANTONIO SANCHEZ SANCHEZ', 'pago inmediato'),
('VERONICA IVETTE VILLEDA NOYOLA', 'pago inmediato'),
('CENTRAL LLANTERA HACSA', 'pago inmediato'),
('JORGE HUMBERTO CORTES HARO', 'pago inmediato'),
('JOSE PINEDA GARCIA', 'Regular'),
('JOSE RODOLFO CASSIANO SIGALA', 'pago inmediato'),
('MARCO CESAR AVILA VAZQUEZ', 'pago inmediato'),
('SAUL EDUARDO RODRIGUEZ PRIETO', 'pago inmediato'),
('DERIVADOS ALIMENTICIOS DEL BAJIO', 'pago inmediato'),
('FEDERAL EXPRESS HOLDINGS (MEXICO) Y COMPAÑIA', 'pago inmediato'),
('HECTOR ENRIQUE ZUARTH ROJAS', 'pago inmediato'),
('JORGE ALBERTO LOPEZ FRANCO', 'pago inmediato'),
('KUMHO TIRE DE MEXICO', 'Regular'),
('BODEGA  URUAPAN', 'Regular'),
('TANJUIJEN MARX SONG', 'Regular'),
('ALWIN INDUSTRIAL CO.,LIMITED', 'pago inmediato'),
('BRIDGESTONE DE MEXICO SA DE CV', 'Regular'),
('ITALIA VENECIA NAVARRO', 'pago inmediato'),
('DANANG RUBBER JOINT STOCK COMPANY', 'pago inmediato'),
('EURO TRADE CONSULTING SRLS', 'pago inmediato'),
('DAVIDE COCCO', 'pago inmediato'),
('CONSUELO VALADEZ HERNANDEZ', 'Regular'),
('JOSE EULOGIO BONILLA GOMEZ', 'Regular'),
('VICTOR ALBERTO PITONEZ PAEZ', 'Regular'),
('KIA SENDERO', 'pago inmediato'),
('LIZBETH GUADALUPE RODRIGUEZ LOPEZ', 'pago inmediato'),
('FRANCISCO JAVIER VALENZUELA', 'Regular'),
('LLANTAS Y COMPLEMENTOS DEL NORTE', 'pago inmediato'),
('LORENA LANDIN CRUZ', 'pago inmediato'),
('LUIS ANTONIO BELLO CHAVEZ', 'pago inmediato'),
('MARGARITA GUERRERO LOPEZ', 'pago inmediato'),
('LLANTERA DE OCCIDENTE', 'Regular'),
('MONTSERRAT SANCHEZ RAMIREZ', 'pago inmediato'),
('LIZETH ESTEFANIA GUTIERREZ LOZA', 'pago inmediato'),
('LUIS ANGEL ESQUEDA SOTO', 'pago inmediato'),
('ROSAURA RIVERA MURO', 'pago inmediato'),
('ROY FELIPE ESTRADA ESTRADA', 'pago inmediato'),
('TERESITA OVIEDO MACEDO', 'pago inmediato'),
('TRANSPORTES CASTORES DE BAJA CALIFORNIA', 'pago inmediato')
]

search_domain = [
    ('move_type', 'in', ['out_invoice']),
    ('state', 'in', ['posted'])
]

datos = []

records = self.env['account.move'].search(search_domain)

# Extrae nombres de los registros relacionados
for record in records:
    vals = {
        'factura': record.name,
        'Cliente': record.partner_id.name,
        'Términos de pago del cliente': record.partner_id.property_payment_term_id.name,
        'Vendedor': record.invoice_user_id.name or '',
        'fecha factura': record.invoice_date,
        'Fecha límite': record.invoice_date_due,
        'TotalFac': record.amount_total,
        'divisa': record.currency_id.name
    }
    clientes_dict = {t[0]: t[1] for t in status_clientes}
    if record.partner_id.name in clientes_dict:
        vals.update({'Status': clientes_dict[record.partner_id.name]})
    else:
        vals.update({'Status': ''})
    datos.append(vals)

df = pd.DataFrame(datos)

# Consulta consolidada para "Pagos" y "Notas de Crédito"
query = """
    SELECT 
        am2."name" AS factura,
        rpu."name" AS cobrador,
        SUM(apr.debit_amount_currency) AS monto,
        DATE(apr.max_date) AS fecha,
        am.date AS fecha_aplicación,
        am.currency_id AS divisa,
        CASE 
            WHEN am.move_type = 'entry' THEN 'Pagos'
            WHEN am.move_type = 'out_refund' THEN 'NC'
        END AS tipo
    FROM account_partial_reconcile apr
    JOIN account_move_line aml ON aml.id = apr.credit_move_id
    JOIN account_move am ON am.id = aml.move_id
    JOIN account_move_line aml2 ON aml2.id = apr.debit_move_id
    JOIN account_move am2 ON am2.id = aml2.move_id
    JOIN res_users ru ON apr.create_uid = ru.id 
    JOIN res_partner rpu ON ru.partner_id = rpu.id
    WHERE am.move_type IN ('entry', 'out_refund')
    AND apr.credit_move_id IN (
            SELECT aml.id 
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id 
            JOIN account_account aa ON aa.id = aml.account_id 
            WHERE aa.account_type = 'asset_receivable' 
        )
    GROUP BY am2."name", rpu."name", apr.max_date, am.currency_id, am.date, am.move_type
"""
# Ejecutar la consulta y crear el DataFrame
self.env.cr.execute(query)
result = self.env.cr.dictfetchall()
df2 = pd.DataFrame(result)

df2 = df2.drop(columns=['fecha'])

df_pivoted = df2.pivot_table(index=['factura', 'cobrador', 'fecha_aplicación'], 
                                    columns='tipo', 
                                    values='monto', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()

merged_df = pd.merge(df, df_pivoted, on='factura', how='left')
merged_df10 = pd.merge(df[['factura', 'Cliente', 'Status', 'Términos de pago del cliente', 'fecha factura', 'Fecha límite']], df_pivoted, on='factura', how='left')

merged_df_copy = merged_df.copy()
#####################################################################################################################################################
query2 = """
    SELECT rp."name" AS cliente, 
           am."name" AS factura, 
           am.amount_total AS total, 
           am.invoice_date AS fecha_factura,
           am.invoice_date_due AS fecha_limite
    FROM account_move am 
    JOIN res_partner rp ON am.partner_id = rp.id 
    WHERE am.amount_residual <> 0
    AND am.move_type IN ('out_invoice', 'out_refund')
    AND state IN ('posted')
"""

self.env.cr.execute(query2)
result2 = self.env.cr.dictfetchall()
df3 = pd.DataFrame(result2)

query3 = """
    SELECT 
        am2."name" AS factura,
        rpu."name" AS cobrador,
        SUM(apr.debit_amount_currency) AS monto,
        apr.max_date AS fecha_aplicación,
        DATE(am.date) AS fecha,
        am.currency_id AS divisa
    FROM account_partial_reconcile apr
    JOIN account_move_line aml ON aml.id = apr.credit_move_id
    JOIN account_move am ON am.id = aml.move_id
    JOIN account_move_line aml2 ON aml2.id = apr.debit_move_id
    JOIN account_move am2 ON am2.id = aml2.move_id
    JOIN res_users ru ON apr.create_uid = ru.id 
    JOIN res_partner rpu ON ru.partner_id = rpu.id
    WHERE am.move_type IN ('entry', 'out_refund')
    AND apr.credit_move_id IN (
            SELECT aml.id 
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id 
            JOIN account_account aa ON aa.id = aml.account_id 
            WHERE aa.account_type = 'asset_receivable' 
        )
    AND am2.amount_residual != 0
    AND apr.max_date <= '2025-07-31'
    GROUP BY am2."name", rpu."name", apr.max_date, am.currency_id, am.date, am.move_type
"""
# Ejecutar la consulta y crear el DataFrame
self.env.cr.execute(query3)
result3 = self.env.cr.dictfetchall()
df4 = pd.DataFrame(result3)

merged_df2 = pd.merge(df3, df4, on='factura', how='left')
merged_df2['monto'] = merged_df2['monto'].fillna(0)

#REEMPLAZAR FECHA DE ACUERDO A LO SOLICITADO "pd.to_datetime('2023-11-27')" Y apr.max_date EN LA CONULTA SQL (TIENEN QUE SER IGUALES)
merged_df2['dias de atraso'] = (pd.to_datetime('2025-07-31') - pd.to_datetime(merged_df2['fecha_limite'])).dt.days
merged_df2['restante'] = merged_df2['total'] - merged_df2['monto']

merged_df2_copy = merged_df2.copy()

merged_df2.loc[(merged_df2['dias de atraso'] > 120), 'no c q poner :V'] = 'Antiguos'
merged_df2.loc[(merged_df2['dias de atraso'] >= 91) & (merged_df2['dias de atraso'] <= 120), 'no c q poner :V'] = '91 - 120'
merged_df2.loc[(merged_df2['dias de atraso'] >= 61) & (merged_df2['dias de atraso'] < 91), 'no c q poner :V'] = '61 - 90'
merged_df2.loc[(merged_df2['dias de atraso'] >= 31) & (merged_df2['dias de atraso'] < 61), 'no c q poner :V'] = '31 - 60'
merged_df2.loc[(merged_df2['dias de atraso'] >= 1) & (merged_df2['dias de atraso'] < 31), 'no c q poner :V'] = '1 - 30'
merged_df2.loc[(merged_df2['dias de atraso'] < 1), 'no c q poner :V'] = 'En fecha'

df_pivoted2 = merged_df2.pivot_table(index=['factura'], 
                                    columns='no c q poner :V', 
                                    values='restante', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()

merged_df3 = pd.merge(merged_df, df_pivoted2, on='factura', how='left')
#####################################################################################################################################################
#                                    REVISAR CALCULO DE DIAS DE ATRASO Y FECHA LIMITE
merged_df_copy['dias de atraso'] = (pd.to_datetime('2025-07-31') - pd.to_datetime(merged_df_copy['Fecha límite'])).dt.days
merged_df_copy = merged_df_copy[(merged_df_copy['dias de atraso'] > 0)]

merged_df_copy['fecha_aplicación'] = pd.to_datetime(merged_df_copy['fecha_aplicación'])

hoy = pd.Timestamp.today()

# Agrega la nueva columna: fecha si es del mes actual, NaT si no lo es
merged_df_copy['fecha_mes_actual'] = merged_df_copy['fecha_aplicación'].where(
    (merged_df_copy['fecha_aplicación'].dt.year == hoy.year) &
    (merged_df_copy['fecha_aplicación'].dt.month == hoy.month)
)

merged_df_copy['primer_dia_mes'] = merged_df_copy['fecha_mes_actual'].apply(lambda x: x.replace(day=1))

merged_df_copy['semana_inicio'] = (merged_df_copy['primer_dia_mes'].dt.weekday + 1) % 7

merged_df_copy['dias_desde_inicio'] = (merged_df_copy['fecha_aplicación'] - merged_df_copy['primer_dia_mes']).dt.days

semanas = (merged_df_copy['dias_desde_inicio'] + merged_df_copy['semana_inicio']) // 7 + 1

# Asigna la columna, pero deja en blanco si el número es 0 (es decir, si semana = 1 original antes de sumar)
merged_df_copy['semana_num'] = [f"SEMANA {n}" if n >= 1 and p > 0 else "Anteriores" for n, p in zip(semanas, merged_df_copy['Pagos'])]

merged_df_copy['Pagos2'] = merged_df_copy['Pagos']

df_pivoted3 = merged_df_copy.pivot_table(index=['factura', 'Cliente', 'Status', 'Vendedor', 'fecha factura', 'Fecha límite', 'TotalFac', 'divisa', 'cobrador', 'fecha_aplicación', 'dias de atraso', 'NC', 'Pagos'], 
                                    columns='semana_num', 
                                    values='Pagos2', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()

df_pivoted3 = df_pivoted3.drop(columns='Anteriores', errors='ignore')

df_pivoted3['Monto Restante'] = (df_pivoted3['TotalFac'] - (df_pivoted3.groupby('factura')['NC'].transform('sum')) - (df_pivoted3.groupby('factura')['Pagos'].transform('sum'))).fillna(0).round(2)
df_pivoted3 = df_pivoted3[(df_pivoted3['Monto Restante'] > 0)]
df_pivoted3['fecha_aplicación'] = df_pivoted3['fecha_aplicación'].dt.date
#####################################################################################################################################################
merged_df10['fecha_aplicación'] = pd.to_datetime(merged_df10['fecha_aplicación'])
merged_df10 = merged_df10[(merged_df10['fecha_aplicación'] >= '2025-07-01') & (merged_df10['fecha_aplicación'] <= '2025-07-31')]
merged_df10['día'] = merged_df10['fecha_aplicación'].dt.day

merged_df10 = merged_df10.pivot_table(index=['factura', 'Cliente', 'Status', 'Términos de pago del cliente', 'cobrador', 'fecha factura', 'Fecha límite'], 
                                    columns='día', 
                                    values='Pagos', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()
#####################################################################################################################################################
df['Fecha límite'] = pd.to_datetime(df['Fecha límite'])
df = df[(df['Fecha límite'] >= '2025-08-01') & (df['Fecha límite'] <= '2025-08-31')]
df['Fecha límite'] = df['Fecha límite'].dt.date
df = df.pivot_table(index=['factura', 'Cliente', 'Status', 'Términos de pago del cliente', 'Vendedor', 'fecha factura', 'divisa'], 
                                    columns='Fecha límite', 
                                    values='TotalFac', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()
#####################################################################################################################################################
merged_df3.to_excel('/mnt/extra-addons/Reporte Kim (general).xlsx', index=False)
df_pivoted3.to_excel('/mnt/extra-addons/Reporte Morosos.xlsx', index=False)
merged_df10.to_excel('/mnt/extra-addons/Reporte cobranza mes actual.xlsx', index=False)
df.to_excel('/mnt/extra-addons/Reporte agosto actual.xlsx', index=False)