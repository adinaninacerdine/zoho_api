# zoho_api/__manifest__.py
{
    "name": "Zoho API Integration",
    "version": "18.0.1.0.0",
    "depends": ["base", "project"],
    "data": [
        "security/ir.model.access.csv",
        "views/zoho_menu.xml",
        "views/project_views.xml",
        "data/ir_config_parameter.xml",
    ],
    "installable": True,
}