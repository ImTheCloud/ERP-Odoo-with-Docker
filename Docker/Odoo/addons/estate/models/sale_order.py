from odoo import fields, models
from datetime import datetime, timedelta


class EstateProperty(models.Model):
    _inherit = 'sale.order.line'
    training_date = fields.Date(string="Training Date")
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    
    
    def _request_approval(self, approver):
        message = f"Request for approval sent to {approver.name}."
        log_note_group = self.env['mail.channel'].search([('name', '=', 'Log Note')], limit=1)
        if not log_note_group:
            log_note_group = self.env['mail.channel'].create({'name': 'Log Note'})
        log_note_group.message_post(body=message, subtype='mail.mt_comment', content_subtype='plaintext')

        activity = self.env['mail.activity'].create({
            'res_id': self.id,
            'res_model': self._name,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'user_id': approver.user_id.id,
            'date_deadline': fields.Datetime.now() + timedelta(days=7),
            'note': f"Quotation {self.id} needs to be confirmed by {approver.name}.",
        })
        self.confirm_quotation(self)

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

    def confirm_quotation(self):
        if self.state == 'draft':
            self.write({'state': 'confirmed'})

            current_user = self.env.user

            activity = self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model', '=', self._name),
                ('user_id', '=', current_user.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ('state', '!=', 'done')
            ])

            if activity:
                activity.action_feedback(feedback="Quotation confirmed by the approver.")
            else:
                self.env['mail.channel'].search([('name', '=', 'Log Note')]).message_post(
                    body=f"{current_user.name} confirmed the quotation {self.id}.",
                    subtype='mail.mt_comment',
                    content_subtype='plaintext'
                )













    # Method to check if the employee limit condition is met
    def _check_employee_limit(self):
        if self.employee.name == "Employee Limited" and sum(self.mapped('price_unit')) > 250:
            message = "Sale Order not confirmed: Amount above the partner limit."
            self._post_in_log_note_group(message)
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
