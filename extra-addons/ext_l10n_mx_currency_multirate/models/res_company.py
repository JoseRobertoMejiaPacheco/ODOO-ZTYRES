from odoo import api, fields, models,_
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    def _generate_currency_rates(self, parsed_data):
        """ Generate the currency rate entries for each of the companies, using the
        result of a parsing function, given as parameter, to get the rates data.

        This function ensures the currency rates of each company are computed,
        based on parsed_data, so that the currency of this company receives rate=1.
        This is done so because a lot of users find it convenient to have the
        exchange rate of their main currency equal to one in Odoo.
        """
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        for company in self:
            rate_info = parsed_data.get(company.currency_id.name, None)

            if not rate_info:
                msg = _("Your main currency (%s) is not supported by this exchange rate provider. Please choose another one.", company.currency_id.name)
                if self._context.get('suppress_errors'):
                    _logger.warning(msg)
                    continue
                else:
                    raise UserError(msg)

            base_currency_rate = rate_info[0]

            for currency, (rate, date_rate) in parsed_data.items():
                rate_value = rate / base_currency_rate

                currency_object = Currency.search([('name', '=', currency),('type','not in',['custom'])])
                if currency_object:  # if rate provider base currency is not active, it will be present in parsed_data
                    already_existing_rate = CurrencyRate.search([('currency_id', '=', currency_object.id), ('name', '=', date_rate), ('company_id', '=', company.id)])
                    if already_existing_rate:
                        already_existing_rate.rate = rate_value
                    else:
                        CurrencyRate.create({'currency_id': currency_object.id, 'rate': rate_value, 'name': date_rate, 'company_id': company.id})

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    def update_currency_rates_manually(self):
        self.ensure_one()
        if not (self.company_id.update_currency_rates()):
            raise UserError(_('El servicio web puede estar inactivo temporalmente, inténtelo más tarde. O revise que exista solo un registro personalizado por producto.'))
