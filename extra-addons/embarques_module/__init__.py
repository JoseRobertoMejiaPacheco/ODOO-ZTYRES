from . import models

from odoo import api, SUPERUSER_ID


def pre_init_hook(cr):
    """Evita que instalar el módulo recalcule los campos logísticos para
    TODAS las facturas ya existentes en ``account.move``.

    ``embarque_discount_percentage``, ``embarque_discount_summary`` y
    ``embarque_discount_amount`` son campos calculados con ``store=True``
    sobre ``account.move``. Cuando Odoo agrega la columna de un campo así,
    ejecuta el compute para cada registro que ya existe en la tabla antes
    de terminar la instalación; en una base con muchas facturas eso es lo
    que hace que instalar tarde tanto.

    Ninguna factura anterior a este módulo puede estar ligada a un
    embarque (la relación es nueva), así que el valor "recalculado" para
    esas facturas siempre sería 0 / vacío: no hay nada real que calcular.
    Creamos aquí las columnas por SQL con ese mismo valor por defecto. Al
    llegar a ``_auto_init`` Odoo ve que la columna ya existe y NO dispara
    el recálculo masivo. Las facturas nuevas se siguen calculando de
    forma normal, como cualquier otro campo calculado.
    """
    cr.execute("SELECT to_regclass('account_move')")
    if not cr.fetchone()[0]:
        # 'account' todavía no ha creado la tabla (no debería pasar, es
        # dependencia del módulo, pero por seguridad no hacemos nada).
        return

    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'account_move'
    """)
    existing = {row[0] for row in cr.fetchall()}

    nuevas_columnas = {
        'embarque_discount_percentage': 'double precision DEFAULT 0.0',
        'embarque_discount_summary': 'varchar',
        'embarque_discount_amount': 'numeric DEFAULT 0.0',
    }
    statements = [
        'ADD COLUMN %s %s' % (column, definition)
        for column, definition in nuevas_columnas.items()
        if column not in existing
    ]
    if statements:
        cr.execute('ALTER TABLE account_move %s' % ', '.join(statements))


def post_init_configure(cr, registry):
    """Configura paquetería y garantiza la carga inicial logística."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    # El XML no puede construir de forma segura el recordset de la compañía
    # actual para llamar a write(). Se configura aquí, una vez creados todos
    # los datos del módulo, y se respeta cualquier valor previamente definido.
    producto = env.ref('embarques_module.product_paqueteria')
    companies = env['res.company'].search([
        ('paqueteria_product_id', '=', False),
    ])
    companies.write({'paqueteria_product_id': producto.id})
    env['embarques.destino']._load_logistico_seed()
