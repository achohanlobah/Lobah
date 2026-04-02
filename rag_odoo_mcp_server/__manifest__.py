# -*- coding: utf-8 -*-
{
    'name': "Claude Integration | Odoo mcp server | claude Ai connect | Trained AI assistant",

    'summary': "This module will connect and train Claude to interact with your odoo instance. Use it for generating dashboards, create or read any records and much more......",

    'description': """
        Exposes an MCP (Model Context Protocol) server as part of the Odoo HTTP server.
        Claude or other LLM can query and manage your Odoo data using natural language.
        Installing the module is enough — no separate process needed.
        
        Usage Examples
        ---------------------------------------------
        Data retrieval:
          • "Show me all customers from Spain"
          • "Find products with stock below 10 units"
          • "List today's sales orders over $1000"
          • "Search for unpaid invoices from last month"
        Data management:
          • "Create a new customer contact for Acme Corporation"
          • "Add a new product called 'Premium Widget' with price $99.99"
          • "Update the phone number for customer John Doe"
          • "Change the status of order SO/2024/001 to confirmed"
          • "Delete the test contact we created earlier"
            """,

    'author': "RAG Solutions",
    'price': 30.00,
    'currency': 'EUR',
    'website': "https://rag-solutions.cloud/",
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'category': 'Uncategorized',

    # any module necessary for this one to work correctly (web provides ir.http for multi-db URL dispatch)
    'depends': ['base', 'web'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/generate_api_key_wizard_views.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'images': [
            'static/description/banner.gif'
    ],
}

