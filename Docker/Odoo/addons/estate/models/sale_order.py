import logging
from odoo import fields, models, api
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class EstateProperty(models.Model):
    _inherit = 'sale.order.line'

    # Add new fields to the sale order line
    training_date = fields.Date(string="Training Date")
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")

    # Method to post a message in the 'Log Note' group
    @api.model
    def _post_in_log_note_group(self, message):
        # Find or create the 'Log Note' group
        log_note_group = self.env['mail.channel'].search([('name', '=', 'Log Note')], limit=1)
        if not log_note_group:
            log_note_group = self.env['mail.channel'].create({'name': 'Log Note'})

        # Post the message in the 'Log Note' group
        log_note_group.message_post(body=message)

    # Method to request approval for a quotation
    def _request_approval(self, approver):
        # Message to notify the approver
        message = "Quotation '%s' needs your approval." % self.order_id.name

        # Add buttons to the message
        buttons = [
            {'name': 'Confirm', 'action': 'confirm_approval'},
            {'name': 'Refuse', 'action': 'refuse_approval'}
        ]

        # Post the message in the 'Log Note' group with buttons
        log_note_group = self.env['mail.channel'].search([('name', '=', 'Log Note')], limit=1)
        if not log_note_group:
            log_note_group = self.env['mail.channel'].create({'name': 'Log Note'})

        log_note_group.message_post(body=message, subtype='mail.mt_comment', content_subtype='plaintext', buttons=buttons)


    # Button to request approval based on the total amount of the quotation
    def button_request_approval(self):
        total_amount = sum(self.mapped('price_unit'))

        if total_amount < 500:
            self.order_id.action_confirm()
        elif 500 <= total_amount < 1000:
            approver = self.env['hr.employee'].search([('job_id', 'in', ['manager_level_1', 'manager_level_2'])], limit=1)
            self._request_approval(approver)
        elif 1000 <= total_amount < 5000:
            approver = self.env['hr.employee'].search([('job_id', '=', 'manager_level_2')], limit=1)
            self._request_approval(approver)
        else:
            administrator = self.env['hr.employee'].search([('job_id', '=', 'administrator')], limit=1)
            self._request_approval(administrator)

    # Button to confirm and approve the sale order line
    def button_confirm_and_approve(self):
        self.action_confirm()
        message = "Sale Order confirmed: Amount ok for the partner limit."
        self._post_in_log_note_group(message)

    # Button to refuse the sale order line
    def button_refuse(self):
        self.action_refuse()
        message = "Sale Order not confirmed: Amount above the partner limit."
        self._post_in_log_note_group(message)

    # Overridden action_confirm method
    def action_confirm(self):
        if not self._check_employee_limit():
            return

        _logger.info("Start of action_confirm method for SaleOrder")
        self._create_training_calendar_event()
        res = super(EstateProperty, self).action_confirm()
        _logger.info("End of action_confirm method for SaleOrder")
        return res

    # Method to check if the employee limit condition is met
    def _check_employee_limit(self):
        if self.employee.name == "Employee Limited" and sum(self.mapped('price_unit')) > 350:
            message = "Sale Order not confirmed: Amount above the partner limit."
            self._post_in_log_note_group(message)
            _logger.warning(message)
            return False
        return True

    # Method to create calendar events based on training date and employee
    def _create_training_calendar_event(self):
        for order_line in self:
            if order_line.training_date and order_line.product_template_id:
                start_datetime = datetime.combine(order_line.training_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(hours=2)
                self.env['calendar.event'].create({
                    'name': 'Training: %s' % order_line.product_template_id.name,
                    'start_datetime': start_datetime,
                    'stop_datetime': end_datetime,
                    'partner_ids': [(6, 0, [order_line.order_id.partner_id.id])],
                    'description': 'Training for product: %s' % order_line.product_template_id.name,
                    'location': order_line.order_id.partner_id.property_product_pricelist.city or '',
                    'alarm_ids': [(0, 0, {'name': 'Remind', 'alarm_id': self.env.ref('calendar.alarm_reminder').id, 'duration': 60})],
                })
