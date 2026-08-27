from odoo import fields, models, _
from odoo.exceptions import UserError


class PosCashMoveCancelWizard(models.TransientModel):
    _name = "pos.cash.move.cancel.wizard"
    _description = "Anular Movimiento de Caja"

    move_id = fields.Many2one(
        "pos.cash.move",
        string="Movimiento",
        required=True,
        readonly=True,
    )

    reason = fields.Text(
        string="Motivo de Anulación",
        required=True,
    )

    def action_confirm_cancel(self):
        self.ensure_one()

        move = self.move_id

        if move.state == "cancel":
            raise UserError(
                _("Este movimiento ya se encuentra anulado.")
            )

        if move.session_id.state == "closed":
            raise UserError(
                _(
                    "No se puede realizar una anulación normal porque "
                    "la sesión POS ya está cerrada. Utilice la reversión histórica."
                )
            )

        reason = (self.reason or "").strip()

        if not reason:
            raise UserError(
                _("Debe ingresar el motivo de la anulación.")
            )

        move.write({
            "cancel_reason": reason,
        })

        move.action_cancel_move_in_place()

        return {
            "type": "ir.actions.act_window_close",
        }