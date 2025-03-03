# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests

class ZtyresExata(models.Model):
    _name = 'ztyres_exata.facturacion'
    _description = 'ztyres exata facturacion'
    
    state = fields.Selection(string="Estado de Envio", selection=[('done', 'Correcto'), ('error', 'Erróneo')])
    fecha = fields.Date(string='Fecha')
    creado_por = fields.Char(string="Creado por")
    respuesta = fields.Char(string='Respuesta')
    line_ids = fields.One2many('ztyres_exata.facturacion.line', 'id_facturacion', string="Líneas de Facturación")
    jenkins_message = fields.Char(string='Estado Jenkins')
                
    # Campo computado para mostrar el encabezado personalizado
    display_name = fields.Char(compute="_compute_display_name", store=True)
    
    def execute_jenkinks_task(self):
        JENKINS_URL = f"http://ztyres.com:8080/job/EXATA%20UPLOAD%20GOODYEAR/buildWithParameters?{'DATE'}={self.fecha}"
        USER = "ztyres"
        API_TOKEN = "11d6d297c855d483b667039c9854f8194f"
        response = requests.post(JENKINS_URL, auth=(USER, API_TOKEN))
        if response.status_code == 201:
            self.jenkins_message = "Tarea ejecutada correctamente."
            print("Tarea ejecutada correctamente.")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            self.jenkins_message = response.text
        self.unlink()

    @api.depends('state', 'fecha')
    def _compute_display_name(self):
        for record in self:
            if record.state == 'done':
                record.display_name = f"Correcto | {record.fecha}"
            else:
                record.display_name = f"Erróneo | {record.fecha}"
        