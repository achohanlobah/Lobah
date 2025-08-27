# -*- coding: utf-8 -*-

{
    # =========================
    # Module Information
    # =========================
    "name": "Approval Attachment Zip",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Approvals",
    "summary": "Approval Attachment Zip",
    "description": """
        Approval Attachment Zip.
    """,
    "license": "LGPL-3",

    # =========================
    # Author & Maintainer
    # =========================
    "author": "SereneFox Solutions",
    "website": "https://www.serenefoxsolutions.com",
    "maintainer": "SereneFox Solutions",
    "support": "serenefoxsolution@gmail.com",

    # =========================
    # Dependencies
    # =========================
    "depends": [
        'approvals',
    ],

    # =========================
    # Data Files (Security, Views, Wizards, Data)
    # =========================
    "data": [
        'security/ir.model.access.csv',
        'data/server_action.xml',
        'views/approval_request.xml',
        'report/approval_request_template.xml',
    ],

    # =========================
    # Web Assets (CSS, JS, etc.)
    # =========================
    "assets": {},

    # =========================
    # Technical Settings
    # =========================
    "installable": True,
    "auto_install": False,
    "application": True,
}
