# -*- coding: utf-8 -*-

{
    # =========================
    # Module Information
    # =========================
    "name": "SFS Payroll Extend",
    "version": "18.0.1.0.0",
    "category": "Human Resources/Approvals",
    "summary": "This module customizes the payslip report name to include employee name, month and year.",
    "description": """
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
        'account'
    ],

    # =========================
    # Data Files (Security, Views, Wizards, Data)
    # =========================
    "data": [
        'data/data.xml'
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
    "application": False,
}
