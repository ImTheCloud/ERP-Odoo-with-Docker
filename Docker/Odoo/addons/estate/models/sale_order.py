from odoo import fields, models
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))

            if total_amount >= 500 and not order.env.user.has_group('base.group_system'):
                # If price_unit is above 500 and the user is not an admin, show a warning message
                order.message_post(body="Sale order not confirmed: Amount above the group limit.", subtype_xmlid="mail.mt_comment")
                return {'warning': {'title': 'Warning', 'message': 'Sale order not confirmed: Amount above the group limit.'}}

            res = super(SaleOrder, order).action_confirm()

            for line in order.order_line.filtered(lambda l: l.training_date):
                start_datetime = datetime.combine(line.training_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=1, seconds=-1)

                event_vals = {
                    'name': f"{line.product_id.display_name} - {line.name}",
                    'start': start_datetime,
                    'stop': end_datetime,
                    'allday': True,
                    'rrule': "FREQ=WEEKLY",
                    'partner_ids': [(4, line.employee.user_id.partner_id.id)],
                    'description': line.name,
                }
                order.env['calendar.event'].create(event_vals)

        return res

    
    def action_request_approval(self):
        res = False  

        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))

            if total_amount < 500:
                # No approval required for amounts less than 500€
                res = super(SaleOrder, order).action_confirm()
            elif 500 <= total_amount <= 1000:
                # Approval required from managers with job title 'Manager1' or 'Manager2'
                employee = order.env['hr.employee'].search([('user_id', '=', order.env.user.id)], limit=1)
                if employee and employee.job_title in ['Manager1', 'Manager2']:
                    res = super(SaleOrder, order).action_confirm()
                else:
                    # Create activity to notify about approval requirement
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        note="Quotation approval requested. Please confirm.",
                        user_id=order.user_id.id
                    )
                    order.message_post(body="Request for approval sent to the managers.", subtype_xmlid="mail.mt_comment")
            elif 1000 <= total_amount <= 5000:
                # Approval required from managers with job title 'Manager2'
                employee = order.env['hr.employee'].search([('user_id', '=', order.env.user.id)], limit=1)
                if employee and employee.job_title == 'Manager2':
                    res = super(SaleOrder, order).action_confirm()
                else:
                    # Create activity to notify about approval requirement
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        note="Quotation approval requested. Please confirm.",
                        user_id=order.user_id.id
                    )
                    order.message_post(body="Request for approval sent to the manager2.", subtype_xmlid="mail.mt_comment")
            else:
                # Amount greater than 5000, approval required from an administrator
                employee = order.env['hr.employee'].search([('user_id', '=', order.env.user.id)], limit=1)
                if employee and employee.job_title == 'Administrator':
                    res = super(SaleOrder, order).action_confirm()
                    # Create activity to notify about approval requirement
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        note="Quotation approval requested. Please confirm.",
                        user_id=order.user_id.id
                    )
                    order.message_post(body="Request for approval sent to the Administrators.", subtype_xmlid="mail.mt_comment")
        return res

    
class EstateProperty(models.Model):
    _inherit = 'sale.order.line'

    # Ajout de champs personnalisés pour gérer les propriétés immobilières
    training_date = fields.Date(string="Training Date")  # Date de formation associée à la ligne de commande
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")  # Employé associé à la ligne de commande