from odoo import fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    cash_flow_series = fields.Char(
        string="Serie Movimientos de Caja",
        copy=False,
    )

    cash_flow_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Secuencia Movimientos de Caja",
        readonly=True,
        copy=False,
    )

    def _get_cash_flow_sequence(self):
        self.ensure_one()

        if not self.cash_flow_series:
            raise UserError(
                _(
                    "Debe configurar la Serie de Movimientos de Caja "
                    "en el Punto de Venta %s."
                )
                % self.display_name
            )

        if not self.cash_flow_sequence_id:
            sequence = self.env["ir.sequence"].sudo().create(
                {
                    "name": "Movimientos Caja - %s" % self.display_name,
                    "code": "pos.cash.flow.%s" % self.id,
                    "padding": 6,
                    "number_next": 1,
                    "company_id": self.company_id.id,
                }
            )

            self.sudo().write(
                {
                    "cash_flow_sequence_id": sequence.id,
                }
            )

        return self.cash_flow_sequence_id