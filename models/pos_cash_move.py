from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosCashMove(models.Model):
    _name = "pos.cash.move"
    _description = "Historial de Entradas y Salidas de Caja"
    _order = "create_date desc"

    name = fields.Char(
        string="Nro. Ticket", required=True, readonly=True, copy=False, default="/"
    )
    session_id = fields.Many2one(
        "pos.session", string="Sesión POS", required=True, readonly=True
    )

    session_state = fields.Selection(
        related="session_id.state",
        string="Estado de Sesión",
        readonly=True,
    )
    config_id = fields.Many2one(
        "pos.config",
        string="Punto de Venta",
        related="session_id.config_id",
        store=True,
    )
    user_id = fields.Many2one(
        "res.users", string="Cajero", default=lambda self: self.env.user, readonly=True
    )

    move_type = fields.Selection(
        [("in", "Entrada de Dinero"), ("out", "Salida de Dinero")],
        string="Tipo de Movimiento",
        required=True,
        readonly=True,
    )

    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Método de Pago",
        readonly=True,
    )

    affects_cash = fields.Boolean(
        string="Afecta Caja Física",
        compute="_compute_affects_cash",
        store=True,
    )

    payment_method_type = fields.Selection(
        [("cash", "Efectivo"), ("yape", "Yape"), ("transfer", "Transferencia")],
        string="Medio de Pago",
        required=True,
        default="cash",
        readonly=True,
    )

    is_digital = fields.Boolean(
        string="Es Registro Digital", compute="_compute_is_digital", store=True
    )

    amount = fields.Float(string="Monto", required=True, readonly=True)
    reason = fields.Text(string="Motivo / Concepto", required=True, readonly=True)

    state = fields.Selection(
        [
            ("done", "Realizado"),
            ("cancel", "Anulado"),
            ("reversed", "Revertido"),
        ],
        string="Estado",
        default="done",
        readonly=True,
    )

    correction_type = fields.Selection(
        [
            ("normal", "Movimiento Normal"),
            ("reversal", "Reversión"),
            ("adjustment", "Ajuste Histórico"),
        ],
        string="Tipo de Registro",
        default="normal",
        required=True,
        readonly=True,
    )

    affects_balance = fields.Boolean(
        string="Afecta Saldo",
        default=True,
        readonly=True,
    )

    original_move_id = fields.Many2one(
        "pos.cash.move",
        string="Movimiento Original",
        readonly=True,
        copy=False,
    )

    reversal_move_id = fields.Many2one(
        "pos.cash.move",
        string="Movimiento de Reversión",
        readonly=True,
        copy=False,
    )

    correction_reason = fields.Text(
        string="Motivo de Corrección",
        readonly=True,
    )

    correction_user_id = fields.Many2one(
        "res.users",
        string="Corregido Por",
        readonly=True,
    )

    correction_date = fields.Datetime(
        string="Fecha de Corrección",
        readonly=True,
    )

    cancel_reason = fields.Text(string="Motivo de Anulación")
    cancel_user_id = fields.Many2one("res.users", string="Anulado Por", readonly=True)

    @api.depends("payment_method_type")
    def _compute_is_digital(self):
        for rec in self:
            rec.is_digital = rec.payment_method_type in ["yape", "transfer"]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                prefix = "ING" if vals.get("move_type") == "in" else "SAL"
                sequence = (
                    self.env["ir.sequence"].next_by_code("pos.cash.move.sequence")
                    or "000001"
                )
                vals["name"] = f"{prefix}-{sequence}"
        return super().create(vals_list)

    @api.depends("payment_method_id")
    def _compute_affects_cash(self):
        for rec in self:
            rec.affects_cash = bool(
                rec.payment_method_id and rec.payment_method_id.is_cash_count
            )

    def action_print_ticket(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_url",
            "url": f"/pos_cash_flow/ticket/{self.id}",
            "target": "new",
        }

    def action_cancel_move_in_place(self):
        """Anula el movimiento directamente desde la misma vista extornando en caja"""
        for rec in self:
            if rec.state == "cancel":
                raise UserError(_("Este movimiento ya se encuentra anulado."))

            if not rec.cancel_reason or not rec.cancel_reason.strip():
                raise UserError(
                    _(
                        "Debe escribir el motivo de la anulación en el campo correspondiente antes de confirmar."
                    )
                )

            # Solo afectamos la caja física si el método realmente es efectivo
            if rec.affects_cash:
                reversal_amount = rec.amount
                reversal_reason = f"ANULACIÓN [{rec.name}]: {rec.cancel_reason}"
                reversal_type = "in" if rec.move_type == "out" else "out"

                extras = {
                    "translatedType": "ENTRADA" if reversal_type == "in" else "SALIDA",
                }

                rec.session_id.try_cash_in_out(
                    reversal_type,
                    reversal_amount,
                    reversal_reason,
                    False,
                    extras,
                )

            # Marcar registro como anulado
            rec.write(
                {
                    "state": "cancel",
                    "cancel_user_id": self.env.user.id,
                }
            )

        return True

    def action_create_historical_reversal(self):
        """
        Genera una reversión administrativa de un movimiento cuya sesión
        ya está cerrada.

        IMPORTANTE:
        - No modifica la sesión original.
        - No modifica la caja actual.
        - No ejecuta try_cash_in_out().
        - Solo deja trazabilidad de la corrección.
        """
        self.ensure_one()

        # 1. Solo se usa cuando la sesión original está cerrada
        if self.session_id.state != "closed":
            raise UserError(
                _(
                    "La sesión todavía está abierta. "
                    "Utilice la opción de anulación normal."
                )
            )

        # 2. No permitir corregir algo que ya fue anulado
        if self.state == "cancel":
            raise UserError(
                _("No se puede corregir un movimiento que ya está anulado.")
            )

        # 3. No permitir revertir dos veces
        if self.state == "reversed" or self.reversal_move_id:
            raise UserError(_("Este movimiento ya tiene una reversión registrada."))

        # 4. Debe existir un motivo
        if not self.correction_reason or not self.correction_reason.strip():
            raise UserError(_("Debe ingresar el motivo de la corrección."))

        # 5. Crear movimiento administrativo inverso
        reversal_type = "out" if self.move_type == "in" else "in"

        reversal = self.create(
            {
                "session_id": self.session_id.id,
                "move_type": reversal_type,
                "payment_method_id": (
                    self.payment_method_id.id if self.payment_method_id else False
                ),
                # Temporal mientras mantenemos compatibilidad
                # con el campo antiguo.
                "payment_method_type": self.payment_method_type,
                "amount": self.amount,
                "reason": "REVERSIÓN HISTÓRICA DE %s: %s"
                % (
                    self.name,
                    self.correction_reason,
                ),
                "correction_type": "reversal",
                # MUY IMPORTANTE:
                # esta reversión NO mueve dinero de ninguna caja.
                "affects_balance": False,
                "original_move_id": self.id,
                "correction_reason": self.correction_reason,
                "correction_user_id": self.env.user.id,
                "correction_date": fields.Datetime.now(),
            }
        )

        # 6. Marcar el movimiento original
        self.write(
            {
                "state": "reversed",
                "reversal_move_id": reversal.id,
                "correction_user_id": self.env.user.id,
                "correction_date": fields.Datetime.now(),
            }
        )

        return True

    @api.model
    def create_from_pos(
        self,
        session_id,
        move_type,
        payment_method_id,
        amount,
        reason,
    ):
        session = self.env["pos.session"].browse(session_id)

        if not session.exists():
            raise UserError(_("La sesión POS no existe."))

        if session.state == "closed":
            raise UserError(
                _("No se puede registrar un movimiento porque la sesión está cerrada.")
            )

        payment_method = self.env["pos.payment.method"].browse(payment_method_id)

        if not payment_method.exists():
            raise UserError(_("El método de pago no existe."))

        move = self.create(
            {
                "session_id": session.id,
                "move_type": move_type,
                "payment_method_id": payment_method.id,
                "amount": amount,
                "reason": reason,
                "affects_balance": True,
            }
        )

        return {
            "id": move.id,
            "name": move.name,
        }
