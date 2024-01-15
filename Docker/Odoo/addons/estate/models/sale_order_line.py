from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Ajout de champs personnalisés pour gérer les propriétés immobilières
    training_date = fields.Date(string="Training Date")  # Date de formation associée à la ligne de commande
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")  # Employé associé à la ligne de commande

