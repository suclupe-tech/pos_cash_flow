/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { _t } from "@web/core/l10n/translation";

patch(CashMovePopup.prototype, {
    setup() {
        super.setup();

        const methods = this.pos.models["pos.payment.method"].getAll();

        this.state.payment_method_id = methods.length
            ? methods[0].id
            : false;
    },

    get paymentMethods() {
        return this.pos.models["pos.payment.method"].getAll();
    },

    _prepareTryCashInOutPayload(type, amount, reason, partnerId, extras) {
        // Incluimos el método de pago seleccionado en los datos enviados al backend
        extras.payment_method_id = this.state.payment_method_id;
        return super._prepareTryCashInOutPayload(type, amount, reason, partnerId, extras);
    },

    async confirm() {
        // Mapeo de nombres para la impresión del ticket
        const paymentMethods = this.pos.models["pos.payment.method"].getAll();

        const paymentMethod = paymentMethods.find(
            (method) => method.id === parseInt(this.state.payment_method_id)
        );

        if (!paymentMethod) {
            throw new Error("No se encontró el método de pago seleccionado.");
        }

        const paymentMethodLabel = paymentMethod.name;

        const amount = parseFloat(this.state.amount);
        const formattedAmount = this.env.utils.formatCurrency(amount);
        if (!amount) {
            this.notification.add(_t("Movimiento ignorado por monto 0."));
            return this.props.close();
        }

        const type = this.state.type;
        const translatedType = type === "in" ? "ENTRADA" : "SALIDA";
        const extras = {
            formattedAmount,
            translatedType,
            payment_method_id: paymentMethod.id,
            payment_method_name: paymentMethod.name,
        };
        const reason = `${this.state.reason.trim()} [Pago: ${paymentMethodLabel}]`;

        const cashMove = await this.pos.data.call(
            "pos.cash.move",
            "create_from_pos",
            [
                this.pos.session.id,
                type,
                paymentMethod.id,
                amount,
                this.state.reason.trim(),
            ],
            {}
        );

        // Abrir el ticket real generado en backend
        const ticketUrl = `/pos_cash_flow/ticket/${cashMove.id}`;
        window.open(ticketUrl, "_blank");

        this.props.close();
        this.notification.add(
            _t("Movimiento registrado con éxito (%s via %s).", formattedAmount, paymentMethodLabel),
            3000
        );
    }
});