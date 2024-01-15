from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Additional custom fields for managing real estate properties
    training_date = fields.Date(string="Training Date")  # Date of training associated with the order line
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")  # Employee associated with the order line
