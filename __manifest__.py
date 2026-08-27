{
    "name": "POS Cash Flow - Control de Caja",
    "version": "19.0.1.0.0",
    "summary": "Control de ingresos, salidas, medios de pago (Efectivo/Yape/Transferencia) y vouchers térmicos",
    "category": "Point of Sale",
    "author": "Detalles Textiles S.A.C.",
    "depends": ["base", "point_of_sale", "account"],
    "data": [
        "data/sequence_data.xml",
        "views/pos_cash_move_views.xml",
        "report/pos_cash_move_ticket.xml",
        "security/ir.model.access.csv",
        "views/pos_config_views.xml",
        "wizard/cancel_move_wizard_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_cash_flow/static/src/xml/cash_popup.xml",
            "pos_cash_flow/static/src/js/cash_popup.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
