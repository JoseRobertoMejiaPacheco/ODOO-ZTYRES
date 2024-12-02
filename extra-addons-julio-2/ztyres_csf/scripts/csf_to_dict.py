import requests
from bs4 import BeautifulSoup

# Disable warnings for urllib3
requests.packages.urllib3.disable_warnings()
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'

CSF_LABELS = [
    "RFC:",
    "CURP:",
    "Denominación o Razón Social:",
    "Nombre:",
    "Apellido Paterno:",
    "Apellido Materno:",
    "Tipo de vialidad:",
    "Nombre de la vialidad:",
    "Número exterior:",
    "Número interior:",
    "Colonia:",
    "Régimen:",
    "Nombre:,Apellido Paterno:",
    "Apellido Materno:,",
    "Entidad Federativa:",
    "Municipio o delegación:",
    "CP:",
    "Denominación o Razón Social:"
]

def format_address(values):
    """Formats an address based on a provided dictionary."""
    road_type = values.get('Tipo de vialidad:', '')
    road_name = values.get('Nombre de la vialidad:', '')
    external_number = values.get('Número exterior:', '')
    internal_number = values.get('Número interior:', '')
    neighborhood = values.get('Colonia:', '')
    address = "{} {} NO. {}".format(road_type, road_name, external_number)
    if internal_number:
        address += " Int. " + internal_number
    if neighborhood:
        address += " COLONIA " + neighborhood
    return address

def get_soup(html):
    return BeautifulSoup(html, 'html.parser')

def get_csf_data(key, soup):
    # Buscar la etiqueta que contiene el valor
    label = soup.find('span', text=key)
    if label:
        value = label.find_next('td', role='gridcell').text.strip()
        return {key: value}
    else:
        return {}

def get_csf_html(url):
    page = requests.get(url, verify=False)
    return page.content.decode("utf-8")

def get_rfc_from_url(url):
    return {'RFC:': url.split('_')[1]}

def get_csf_dict(url, labels=CSF_LABELS):
    html = get_csf_html(url)
    soup = get_soup(html)
    vals = {}
    vals.update(get_rfc_from_url(url))
    for label in labels:
        vals.update(get_csf_data(label, soup))
    return vals

def get_partner_data(vals):
    name = vals.get('Denominación o Razón Social:') or '%s %s %s' % (
    vals.get('Nombre:') or "", vals.get('Apellido Paterno:') or "", vals.get('Apellido Materno:') or "")
    data = {
        'name': name,
        'street': format_address(vals),
        'state_id': vals.get('Entidad Federativa:'),
        'city_id': vals.get('Municipio o delegación:'),
        'zip': vals.get('CP:'),
        'country_id': 156,
        'vat': vals.get('RFC:'),
        'l10n_mx_edi_curp': vals.get('CURP:'),
        'l10n_mx_edi_fiscal_regime': vals.get('Régimen:')
    }
    return data

def get_odoo_vals(url_csf):
    vals = get_csf_dict(url_csf)
    return get_partner_data(vals)