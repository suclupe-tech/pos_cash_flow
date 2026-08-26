/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { CashMoveReceipt } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_receipt/cash_move_receipt";
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

        // 1. Registro del movimiento en la sesión POS
        if (paymentMethod.is_cash_count) {
            await this.pos.data.call(
                "pos.session",
                "try_cash_in_out",
                this._prepareTryCashInOutPayload(
                    type,
                    amount,
                    reason,
                    this.partnerId,
                    extras
                ),
                {},
                true
            );
        }

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

        // 2. Creación del objeto temporal de orden para mandar a imprimir
        const order = this.pos.models["pos.order"].create({
            session_id: this.pos.session,
            company_id: this.pos.company,
            config_id: this.pos.config,
            user_id: this.pos.user,
            ticket_code: "",
            tracking_number: "",
            sequence_number: 0,
            pos_reference: "",
        });

        // 3. Emisión e Impresión del ticket
        await this.printer.print(CashMoveReceipt, {
            reason: reason,
            translatedType: translatedType,
            order: order,
            formattedAmount: formattedAmount,
            date: new Date().toLocaleString(),
        });

        this.pos.models["pos.order"].delete(order);

        this.props.close();
        this.notification.add(
            _t("Movimiento registrado con éxito (%s via %s).", formattedAmount, paymentMethodLabel),
            3000
        );
    }
});