from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    @api.model
    def setup_z_helpdesk_security(self):
        """Reaplica las reglas aunque una versión anterior quedara como noupdate."""
        requester_group = self.env.ref("z_helpdesk.group_ticket_requester")
        helpdesk_user = self.env.ref("helpdesk.group_helpdesk_user")
        helpdesk_manager = self.env.ref("helpdesk.group_helpdesk_manager")
        all_access_group = self.env.ref("z_helpdesk.group_ticket_all_access")
        full_access_groups = [
            helpdesk_user.id,
            helpdesk_manager.id,
            all_access_group.id,
        ]

        own_ticket_rule = self.env.ref(
            "z_helpdesk.helpdesk_ticket_rule_own_unassigned"
        )
        own_ticket_rule.sudo().write({
            "active": True,
            "groups": [(6, 0, [requester_group.id])],
            "domain_force": "['|', ('requester_user_id', '=', user.id), ('create_uid', '=', user.id)]",
        })

        all_ticket_rule = self.env.ref(
            "z_helpdesk.helpdesk_ticket_rule_helpdesk_all"
        )
        all_ticket_rule.sudo().write({
            "active": True,
            "groups": [(6, 0, full_access_groups)],
            "domain_force": "[(1, '=', 1)]",
        })

        own_sla_rule = self.env.ref(
            "z_helpdesk.helpdesk_sla_status_rule_own_ticket"
        )
        own_sla_rule.sudo().write({
            "active": True,
            "groups": [(6, 0, [requester_group.id])],
            "domain_force": "['|', ('ticket_id.requester_user_id', '=', user.id), ('ticket_id.create_uid', '=', user.id)]",
        })

        all_sla_rule = self.env.ref(
            "z_helpdesk.helpdesk_sla_status_rule_helpdesk_all"
        )
        all_sla_rule.sudo().write({
            "active": True,
            "groups": [(6, 0, full_access_groups)],
            "domain_force": "[(1, '=', 1)]",
        })
        self.env["ir.rule"].clear_caches()
        # Hace visible inmediatamente cualquier grupo nuevo en el formulario
        # de usuarios después de actualizar el módulo.
        self.env["res.groups"].sudo()._update_user_groups_view()
        return True

    requester_user_id = fields.Many2one(
        "res.users",
        string="Solicitante interno",
        default=lambda self: self.env.user if self.env.user._is_internal() else False,
        tracking=True,
        index=True,
        help="Usuario interno que solicitó el servicio.",
    )
    requester_locked = fields.Boolean(
        compute="_compute_requester_locked",
        help="Control técnico para bloquear el solicitante a usuarios no administradores.",
    )
    requester_only_mode = fields.Boolean(
        compute="_compute_requester_only_mode",
        help="Oculta los campos de atención cuando el usuario no pertenece a un equipo.",
    )
    team_id = fields.Many2one(required=False)
    allowed_assignee_ids = fields.Many2many(
        "res.users",
        compute="_compute_allowed_assignee_ids",
        string="Responsables permitidos",
    )
    priority_level = fields.Selection(
        selection=[
            ("1", "1 - Informativa"),
            ("2", "2 - Muy baja"),
            ("3", "3 - Baja"),
            ("4", "4 - Limitada"),
            ("5", "5 - Media"),
            ("6", "6 - Relevante"),
            ("7", "7 - Alta"),
            ("8", "8 - Muy alta"),
            ("9", "9 - Crítica"),
            ("10", "10 - Emergencia"),
        ],
        string="Prioridad (1-10)",
        required=True,
        default="5",
        tracking=True,
        index=True,
    )
    evidence_html = fields.Html(
        string="Capturas y evidencias",
        sanitize=True,
        help="Pegue capturas de pantalla directamente en este espacio.",
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "helpdesk_ticket_evidence_attachment_rel",
        "ticket_id",
        "attachment_id",
        string="Archivos adjuntos",
        help="Seleccione o arrastre archivos relacionados con el ticket.",
    )

    @api.depends_context("uid", "z_requester_mode")
    def _compute_requester_locked(self):
        locked = self._is_requester_restricted_mode()
        for ticket in self:
            ticket.requester_locked = locked

    @api.depends_context("uid", "z_requester_mode")
    def _compute_requester_only_mode(self):
        requester_only = self._is_requester_restricted_mode()
        for ticket in self:
            ticket.requester_only_mode = requester_only

    @api.model
    def _is_requester_restricted_mode(self):
        """Limit only My Tickets or users without a Helpdesk agent role."""
        if self.env.context.get("z_requester_mode"):
            return True
        user = self.env.user
        is_requester = user.has_group("z_helpdesk.group_ticket_requester")
        is_helpdesk_agent = user.has_group(
            "helpdesk.group_helpdesk_user"
        ) or user.has_group("helpdesk.group_helpdesk_manager")
        return is_requester and not is_helpdesk_agent

    @api.depends("team_id", "team_id.member_ids")
    def _compute_allowed_assignee_ids(self):
        for ticket in self:
            ticket.allowed_assignee_ids = ticket.team_id.member_ids

    @api.model
    def _native_priority_from_level(self, level):
        level = int(level or 5)
        if level <= 2:
            return "0"
        if level <= 5:
            return "1"
        if level <= 8:
            return "2"
        return "3"

    @api.model
    def _internal_requester_values(self):
        user = self.env.user
        partner = user.partner_id
        return {
            "requester_user_id": user.id,
            "partner_id": partner.id,
            "partner_email": partner.email or user.email or False,
        }

    @api.model_create_multi
    def create(self, vals_list):
        is_internal = self.env.user._is_internal()
        is_manager = self.env.user.has_group("helpdesk.group_helpdesk_manager")
        is_requester = self._is_requester_restricted_mode()
        requester_values = self._internal_requester_values() if is_internal else {}

        for vals in vals_list:
            if is_internal and not is_manager:
                vals.update(requester_values)
            elif is_internal:
                for field_name, value in requester_values.items():
                    vals.setdefault(field_name, value)
            if is_requester:
                # El solicitante registra el ticket sin decidir quién lo atenderá.
                vals["team_id"] = False
                vals["user_id"] = False
                vals["ticket_type_id"] = False
                vals["tag_ids"] = [(5, 0, 0)]
            vals["priority"] = self._native_priority_from_level(
                vals.get("priority_level", "5")
            )

        tickets = super().create(vals_list)
        tickets._link_evidence_attachments()
        return tickets

    def write(self, vals):
        protected = {"requester_user_id", "partner_id", "partner_email"}
        is_requester = self._is_requester_restricted_mode()
        is_manager = self.env.user.has_group("helpdesk.group_helpdesk_manager")
        if protected.intersection(vals) and (is_requester or not is_manager):
            raise UserError(
                _("Solo un administrador de Servicio de asistencia puede cambiar el solicitante o su correo.")
            )

        assignment_fields = {"team_id", "user_id"}
        if assignment_fields.intersection(vals):
            if is_requester:
                raise UserError(
                    _("Un administrador de Servicio de asistencia debe asignar el equipo y el responsable.")
                )

        if is_requester and {"ticket_type_id", "tag_ids", "partner_phone"}.intersection(vals):
            raise UserError(
                _("El solicitante no puede cambiar el tipo, las etiquetas ni el teléfono del ticket.")
            )

        if "priority_level" in vals:
            vals["priority"] = self._native_priority_from_level(vals["priority_level"])

        result = super().write(vals)
        if "evidence_attachment_ids" in vals:
            self._link_evidence_attachments()
        return result

    @api.onchange("requester_user_id")
    def _onchange_requester_user_id(self):
        if self.requester_user_id:
            partner = self.requester_user_id.partner_id
            self.partner_id = partner
            self.partner_email = partner.email or self.requester_user_id.email

    @api.onchange("priority_level")
    def _onchange_priority_level(self):
        self.priority = self._native_priority_from_level(self.priority_level)

    def _link_evidence_attachments(self):
        for ticket in self:
            ticket.evidence_attachment_ids.sudo().write({
                "res_model": ticket._name,
                "res_id": ticket.id,
            })

    @api.model
    def setup_z_helpdesk_tree_view(self):
        """Replace native priority stars with the 1-10 text in the ticket list."""
        View = self.env["ir.ui.view"].sudo()
        extension_name = "z.helpdesk.ticket.tree.priority.text"
        View.search([("name", "=", extension_name)]).unlink()

        candidates = View.search(
            [
                ("model", "=", "helpdesk.ticket"),
                ("type", "=", "tree"),
                ("mode", "=", "primary"),
                ("active", "=", True),
            ],
            order="priority, id",
        )
        base_view = next(
            (
                view
                for view in candidates
                if 'name="priority"' in (view.arch_db or "")
                and 'widget="priority"' in (view.arch_db or "")
            ),
            False,
        )
        if not base_view:
            return False

        View.create(
            {
                "name": extension_name,
                "model": "helpdesk.ticket",
                "type": "tree",
                "mode": "extension",
                "inherit_id": base_view.id,
                "priority": 90,
                "arch_db": """
                    <data>
                        <xpath expr="//field[@name='priority'][@widget='priority']" position="replace">
                            <field name="priority_level" string="Prioridad" optional="show"/>
                        </xpath>
                    </data>
                """,
            }
        )
        return True
