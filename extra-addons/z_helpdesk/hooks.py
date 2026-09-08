from odoo import SUPERUSER_ID, api


KANBAN_EXTENSION_NAME = "z.helpdesk.ticket.kanban.priority.text"


def ensure_kanban_priority_view(env):
    View = env["ir.ui.view"]

    View.search([("name", "=", KANBAN_EXTENSION_NAME)]).unlink()

    candidates = View.search(
        [
            ("model", "=", "helpdesk.ticket"),
            ("type", "=", "kanban"),
            ("mode", "=", "primary"),
            ("active", "=", True),
        ],
        order="priority, id",
    )
    base_view = next(
        (
            view
            for view in candidates
            if "kanban-box" in (view.arch_db or "")
        ),
        candidates[:1],
    )
    if not base_view:
        return

    View.create(
        {
            "name": KANBAN_EXTENSION_NAME,
            "model": "helpdesk.ticket",
            "type": "kanban",
            "mode": "extension",
            "inherit_id": base_view.id,
            "priority": 90,
            "arch_db": """
                <data>
                    <xpath expr="//kanban/templates" position="before">
                        <field name="priority_level"/>
                    </xpath>
                    <xpath expr="//t[@t-name='kanban-box']/*[1]" position="inside">
                        <div class="z_helpdesk_kanban_priority mt-1">
                            <strong>Prioridad: </strong>
                            <field name="priority_level"/>
                        </div>
                    </xpath>
                </data>
            """,
        }
    )


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.ui.view"].search([("name", "=", KANBAN_EXTENSION_NAME)]).unlink()
