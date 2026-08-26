from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def get_closing_control_data(self):
        data = super().get_closing_control_data()

        self.ensure_one()

        for payment_data in data.get("non_cash_payment_methods", []):
            payment_method_id = payment_data.get("id")

            cash_moves = self.env["pos.cash.move"].search(
                [
                    ("session_id", "=", self.id),
                    ("payment_method_id", "=", payment_method_id),
                    ("state", "=", "done"),
                    ("affects_balance", "=", True),
                ]
            )

            total_entries = sum(
                cash_moves.filtered(lambda move: move.move_type == "in").mapped(
                    "amount"
                )
            )

            total_outputs = sum(
                cash_moves.filtered(lambda move: move.move_type == "out").mapped(
                    "amount"
                )
            )

            payment_data["amount"] += total_entries - total_outputs

        return data
