# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import json
#curl -X POST -H "Content-Type: application/json" -d '{}' http://192.168.1.126:8001/reporte_direccion
class ZtyresMsSqlExcelReports(http.Controller):
#http://your_odoo_domain_or_ip/reportes_ztyreshome?db=your_database_name

    @http.route('/test', auth='public', methods=['GET'], website=True)
    def insert_dataframe_2(self):
        request.env['ztyres_ms_sql_excel_reports'].sudo().generate_report()
        data = {"message": "Dataframe inserted successfully"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_direccion', auth='public', methods=['GET'], website=True)
    def insert_dataframe_2(self):
        request.env['ztyres_ms_sql_excel_reports'].sudo().generate_report()
        data = {"message": "Dataframe inserted successfully"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    
    @http.route('/reporte_antiguedad', auth='public', methods=['GET'], website=True)
    def insert_dataframe_4(self):
        request.env['ztyres_ms_sql_excel_reports_antiguedad'].sudo().reporte_antiguedadsaldos()
        data = {"message": "Dataframe inserted successfully"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/reporte_ultimoDeposito', auth='public', methods=['GET'], website=True)
    def insert_dataframe_6(self):
        request.env['ztyres_ms_sql_excel_reports_ultimo_deposito'].sudo().genereta_ultimo_deposito()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/reporte_reserva_ventas', auth='public', methods=['GET'], website=True)
    def reporte_reserva_ventas(self):
        request.env['ztyres_reporte_reserva_ventas'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/comision_kumho', auth='public', methods=['GET'], website=True)
    def comision_kumho(self):
        res = request.env['reporte.comisiones'].sudo().get_df_promo_kumho()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Promocion Kumho</title>
            <style>
                /* Aquí puedes añadir estilos CSS si lo deseas */
            </style>
        </head>
        <body>
            <h1>Un paquete por factura</h1>
            {res}
        </body>
        </html>
        """

        return Response(html_content, content_type='text/html; charset=utf-8', status=200)

    @http.route('/reporte_inv_prom', auth='public', methods=['GET'], website=True)
    def inventariosmaspromos(self):
        request.env['inventariosmaspromos'].sudo().get_all_products()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    
    @http.route('/reporte_costo_ventas', auth='public', methods=['GET'], website=True)
    def reporte_costo_ventas(self):
        request.env['ztyres_reporte_costo_ventas'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)

    @http.route('/reporte_avance_asesor', auth='public', methods=['GET'], website=True)
    def ztyres_reporte_avance_asesor(self):
        request.env['ztyres_reporte_avance_asesor'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_cobranza', auth='public', methods=['GET'], website=True)
    def insert_dataframe_7(self):
        request.env['reporte_cobranza_en_tiempo'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_ultimo_costo', auth='public', methods=['GET'], website=True)
    def reporte_ultimo_costo(self):
        request.env['ztyres_reporte_ultimo_costo'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/potencial_compra', auth='public', methods=['GET'], website=True)
    def reporte_potencial_compra(self):
        request.env['reporte_potencial_compra'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/usuarios', auth='public', methods=['GET'], website=True)
    def ztyres_reporte_usuarios(self):
        request.env['ztyres_reporte_usuarios'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/pedidos_diarios', auth='public', methods=['GET'], website=True)
    def ztyres_pedidos_diarios(self):
        request.env['ztyres_pedidos_diarios'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/ventas_trimestre', auth='public', methods=['GET'], website=True)
    def reporte_ventas_trimestre(self):
        request.env['reporte_ventas_trimestre'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/codigos_no_comprados', auth='public', methods=['GET'], website=True)
    def reporte_codigos_no_comprados(self):
        request.env['reporte_codigos_no_comprados'].sudo().get_all_products()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_pedidos_facturados', auth='public', methods=['GET'], website=True)
    def ztyres_reporte_pedidos_facturados(self):
        request.env['ztyres_reporte_pedidos_facturados'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_pagos', auth='public', methods=['GET'], website=True)
    def ztyres_reporte_pagos(self):
        request.env['ztyres_reporte_pagos'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
        
    @http.route('/reporte_ventas_diarias', auth='public', methods=['GET'], website=True)
    def ztyres_reporte_ventas_diarias(self):
        request.env['ztyres_reporte_ventas_diarias'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_porcentaje_ventas', auth='public', methods=['GET'], website=True)
    def reporte_porcentaje_ventas(self):
        request.env['reporte_porcentaje_ventas'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_forecast', auth='public', methods=['GET'], website=True)
    def reporte_forecast(self):
        request.env['reporte_forecast'].sudo().get_report()
        data = {"message": "Informacion Actualizada"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_comparativo', auth='public', methods=['GET'], website=True)
    def ztyres_reporte_comparativo(self):
        request.env['ztyres_reporte_comparativo'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_goodyear', auth='public', methods=['GET'], website=True)
    def reporte_goodyear(self):
        request.env['reporte_goodyear'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/ventas_por_marca', auth='public', methods=['GET'], website=True)
    def ventas_por_marca(self):
        request.env['ventas_por_marca'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/ventas_por_llantas', auth='public', methods=['GET'], website=True)
    def reporte_ventas25(self):
        request.env['reporte_ventas25'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/plan_comercial', auth='public', methods=['GET'], website=True)
    def reporte_plan_comercial(self):
        request.env['reporte_plan_comercial'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reporte_ventas_direccion', auth='public', methods=['GET'], website=True)
    def reporte_ventas_direccion(self):
        request.env['reporte_ventas_direccion'].sudo().get_report()
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/reportes_cxc/<string:mes>/<int:anio>', auth='public', methods=['GET'], website=True)
    def reportes_cxc(self, mes, anio):
        request.env['reportes_cobranza'].sudo().get_report(mes, anio)
        data = {"Mensaje": "Reporte actualizado correctamente"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)
    
    @http.route('/ventas/<string:vendedor_id>', auth='user', methods=['GET'], website=True)
    def ventas_por_vendedor_individual(self, vendedor_id):
        vendedor_id = int(vendedor_id)   
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['ventas_por_vendedor_individual'].sudo()
        lista = report_data.get_report(vendedor_id)
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="ventas_por_vendedor.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    # @http.route('/reporte_ventas', auth='user', methods=['GET'], website=True)
    # def reporte_ventas(self):
    #     # Llamar a la función get_report para obtener los datos del reporte
    #     report_data = request.env['reporte_ventas'].sudo()
    #     lista = report_data.get_report()
    #     # Generar el archivo Excel
    #     report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
    #     excel_file = report_generator.generate_excel_report(lista)
        
    #     # Preparar la respuesta para descargar el archivo
    #     return Response(
    #         excel_file,
    #         headers={
    #             'Content-Disposition': 'attachment; filename="ventas_por_vendedor.xlsx"',
    #             'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    #         }
    #     )
    
    @http.route('/antiguedad_de_saldos/<string:fecha>', auth='user', methods=['GET'], website=True)
    def antiguedad_de_saldos(self, fecha):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['antiguedad_de_saldos'].sudo()
        lista = report_data.get_report(fecha)
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="antiguedad_de_saldos.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    @http.route('/ventas_acumuladas/<string:mes>/<int:anio>', auth='user', methods=['GET'], website=True)
    def ventas_acumuladas(self, mes, anio):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['ventas_acumuladas'].sudo()
        lista = report_data.get_report(mes, anio)
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="ventas_acumuladas.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    @http.route('/reporte_promos', auth='user', methods=['GET'], website=True)
    def reporte_promos_bridgestone(self):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['reporte_promos_bridgestone'].sudo()
        lista = report_data.get_all_products()
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="reporte_promos.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    @http.route('/ventas_bridgestone', auth='user', methods=['GET'], website=True)
    def ventas_bridgestone(self):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['ventas_6_meses'].sudo()
        lista = report_data.get_report()
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="ventas_bridgestone.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    @http.route('/facturas/<string:mes>/<int:anio>', auth='user', methods=['GET'], website=True)
    def facturas_y_notasdecredito(self, mes, anio):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['facturas_y_notasdecredito'].sudo()
        lista = report_data.get_report(mes, anio)
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="facturas.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    @http.route('/reporte_ventas', auth='user', methods=['GET'], website=True)
    def ventas_del_mes(self):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['ventas_del_mes'].sudo()
        output = report_data.get_report()
        # Preparar la respuesta para descargar el archivo
        excel_file = output.read()
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="ventas_del_mes.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    # @http.route('/reportes_cxc/<string:mes>/<int:anio>', auth='user', methods=['GET'], website=True)
    # def reportes_cxc(self, mes, anio):
    #     # Llamar a la función get_report para obtener los datos del reporte
    #     report_data = request.env['reportes_cobranza'].sudo()
    #     lista = report_data.get_report(mes, anio)
    #     # Generar el archivo Excel
    #     report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
    #     excel_file = report_generator.generate_excel_report(lista)
        
    #     # Preparar la respuesta para descargar el archivo
    #     return Response(
    #         excel_file,
    #         headers={
    #             'Content-Disposition': 'attachment; filename="reportes_cxc.xlsx"',
    #             'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    #         }
    #     )
        
    @http.route('/comportamiento', auth='user', methods=['GET'], website=True)
    def comportamiento_clientes(self):
        # Llamar a la función get_report para obtener los datos del reporte
        report_data = request.env['comportamiento_clientes'].sudo()
        lista = report_data.get_report()
        # Generar el archivo Excel
        report_generator  = request.env['excel_ventas_por_vendedor'].sudo()
        excel_file = report_generator.generate_excel_report(lista)
        
        # Preparar la respuesta para descargar el archivo
        return Response(
            excel_file,
            headers={
                'Content-Disposition': 'attachment; filename="comportamiento.xlsx"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
        
    @http.route('/resumen_ventas/<int:vendedor_id>', auth='public', methods=['GET'], website=True)
    def reporte_direccion_ventas(self, vendedor_id):
        request.env['reports_ventas'].sudo().generate_report(vendedor_id=vendedor_id)
        data = {"message": "Dataframe inserted successfully"}
        return Response(json.dumps(data), content_type='application/json;charset=utf-8', status=200)