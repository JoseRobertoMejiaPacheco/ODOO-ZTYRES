{
    "name": "Z Helpdesk",
    "version": "16.0.1.5.7",
    "category": "Services/Helpdesk",
    "summary": "Solicitante interno, prioridad 1-10 y evidencias",
    "author": "ZTYRES",
    "license": "LGPL-3",
    "depends": ["helpdesk", "mail"],
    "data": [
        "security/helpdesk_security.xml",
        "security/ir.model.access.csv",
        "data/security_setup.xml",
        "data/helpdesk_stages.xml",
        "views/helpdesk_ticket_views.xml",
        "views/requester_menu_views.xml",
        "data/tree_view_setup.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "z_helpdesk/static/src/js/priority_ten_field.js",
            "z_helpdesk/static/src/xml/priority_ten_field.xml",
            "z_helpdesk/static/src/scss/priority_ten_field.scss",
        ],
    },
    "installable": True,
    "application": False,
}
