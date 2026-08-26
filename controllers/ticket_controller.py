from markupsafe import escape

from odoo import http, fields
from odoo.http import request


class PosCashMoveTicketController(http.Controller):

    @http.route(
        "/pos_cash_flow/ticket/<int:move_id>",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def print_cash_move_ticket(self, move_id, **kwargs):

        move = request.env["pos.cash.move"].browse(move_id).exists()

        if not move:
            return request.not_found()

        # ---------------------------------------------------------
        # Fecha y hora ORIGINAL del movimiento
        # convertida a la zona horaria del usuario
        # ---------------------------------------------------------
        fecha = fields.Datetime.context_timestamp(
            move,
            move.create_date,
        )

        fecha_texto = fecha.strftime("%d/%m/%Y")
        hora_texto = fecha.strftime("%H:%M")

        # ---------------------------------------------------------
        # Tipo de movimiento
        # ---------------------------------------------------------
        tipo_texto = (
            "INGRESO DE DINERO" if move.move_type == "in" else "SALIDA DE DINERO"
        )

        caja = move.config_id.name or ""
        vendedor = move.user_id.name or ""
        medio = move.payment_method_id.name or ""
        motivo = move.reason or ""

        # ---------------------------------------------------------
        # Ticket HTML
        # ---------------------------------------------------------
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>

            <meta charset="UTF-8"/>

            <title>{escape(move.name)}</title>

            <style>

                @page {{
                    size: 80mm auto;
                    margin: 4mm;
                }}

                html,
                body {{
                    width: 72mm;
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                    font-size: 11px;
                    color: #000;
                    background: #fff;
                }}

                .ticket {{
                    width: 72mm;
                    box-sizing: border-box;
                }}

                .center {{
                    text-align: center;
                }}

                .title {{
                    font-size: 14px;
                    font-weight: bold;
                }}

                .type {{
                    font-size: 11px;
                    margin-top: 2px;
                }}

                .number {{
                    font-size: 13px;
                    font-weight: bold;
                    margin-top: 4px;
                }}

                .separator {{
                    border-top: 1px dashed #000;
                    margin: 7px 0;
                }}

                .row {{
                    margin-bottom: 4px;
                    line-height: 1.25;
                }}

                .reason-title {{
                    font-weight: bold;
                    margin-bottom: 3px;
                }}

                .reason {{
                    text-transform: uppercase;
                    line-height: 1.25;
                }}

                .signatures {{
                    display: flex;
                    justify-content: space-between;
                    gap: 10px;
                    margin-top: 28px;
                }}

                .signature {{
                    width: 48%;
                    text-align: center;
                    font-size: 9px;
                }}

                .signature-line {{
                    border-top: 1px solid #000;
                    padding-top: 4px;
                }}

                @media print {{

                    html,
                    body {{
                        width: 72mm;
                        margin: 0;
                        padding: 0;
                    }}

                    .ticket {{
                        width: 72mm;
                    }}
                }}

            </style>

        </head>

        <body>

            <div class="ticket">

                <!-- ENCABEZADO -->
                <div class="center title">
                    COMPROBANTE DE CAJA
                </div>

                <div class="center type">
                    {escape(tipo_texto)}
                </div>

                <div class="center number">
                    {escape(move.name)}
                </div>

                <div class="separator"></div>

                <!-- DATOS -->
                <div class="row">
                    <strong>Fecha:</strong>
                    {escape(fecha_texto)}
                </div>

                <div class="row">
                    <strong>Hora:</strong>
                    {escape(hora_texto)}
                </div>

                <div class="row">
                    <strong>Caja:</strong>
                    {escape(caja)}
                </div>

                <div class="row">
                    <strong>Vendedor:</strong>
                    {escape(vendedor)}
                </div>

                <div class="row">
                    <strong>Medio:</strong>
                    {escape(medio)}
                </div>

                <div class="row">
                    <strong>Monto:</strong>
                    S/ {move.amount:.2f}
                </div>

                <div class="separator"></div>

                <!-- MOTIVO -->
                <div class="reason-title">
                    Motivo:
                </div>

                <div class="reason">
                    {escape(motivo)}
                </div>

                <!-- FIRMAS -->
                <div class="signatures">

                    <div class="signature">
                        <div class="signature-line">
                            Firma del Vendedor
                        </div>
                    </div>

                    <div class="signature">
                        <div class="signature-line">
                            Firma del Receptor
                        </div>
                    </div>

                </div>

            </div>

            <script>
                window.addEventListener("load", function () {{
                    setTimeout(function () {{
                        window.print();
                    }}, 300);
                }});

                window.addEventListener("afterprint", function () {{
                    window.close();
                }});
            </script>

        </body>
        </html>
        """

        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Cache-Control", "no-store"),
            ],
        )
