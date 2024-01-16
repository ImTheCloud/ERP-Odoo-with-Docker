from odoo import models
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    MESSAGE_ORDER = 'Sale order not confirmed: Amount above the group limit.'

    def action_confirm(self):
        res = False
        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))
            current_user_job_title = order.env.user.employee_id.job_title
            
            if current_user_job_title == 'Employee' and total_amount < 500:
                res = super(SaleOrder, order).action_confirm()
            elif  total_amount < 500:
                res = self._confirm_order(order, current_user_job_title, 250, ['EmployeeLimited'])
            elif 500 <= total_amount <= 1000:
                res = self._confirm_order(order, current_user_job_title, None, ['Manager1', 'Manager2', 'Administrator'])
            elif 1000 <= total_amount <= 5000:
                res = self._confirm_order(order, current_user_job_title, None, ['Manager2', 'Administrator'])
            elif total_amount > 5000:
                res = self._confirm_order(order, current_user_job_title, None, ['Administrator'])

            self._create_calendar_events(order)
        return res

    def _confirm_order(self, order, user_job_title, min_amount, allowed_titles):
        total_amount = sum(order.order_line.mapped('price_unit'))
        
        if min_amount is not None and total_amount >= min_amount:
            return order.message_post(body=self.MESSAGE_ORDER, subtype_xmlid="mail.mt_comment")
        elif user_job_title not in allowed_titles:
            return order.message_post(body=self.MESSAGE_ORDER, subtype_xmlid="mail.mt_comment")
        else:
            return super(SaleOrder, order).action_confirm()


    def _create_calendar_events(self, order):
        for line in order.order_line.filtered(lambda l: l.training_date):
            start_datetime = datetime.combine(line.training_date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1, seconds=-1)

            user_id = line.employee.user_id.id if line.employee.user_id else False

            event_vals = {
                'name': f"{line.product_id.display_name} - {line.name}",
                'start': start_datetime,
                'stop': end_datetime,
                'allday': True,
                'rrule': "FREQ=WEEKLY",
                'partner_ids': [(4, line.employee.user_id.partner_id.id)],
                'description': line.name,
                'user_id': user_id,
            }
            order.env['calendar.event'].create(event_vals)

    def action_request_approval(self):
        res = False

        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))

            if 500 <= total_amount <= 1000:
                self._request_approval_for_managers(order, ['Manager1', 'Manager2'])
            elif 1000 <= total_amount <= 5000:
                self._request_approval_for_managers(order, ['Manager2'])
            else:
                self._request_approval_for_administrator(order)

        return res

    def _request_approval_for_managers(self, order, manager_titles):
        order.message_post(body="Request for approval sent to the managers.", subtype_xmlid="mail.mt_comment")
        managers = order.env['hr.employee'].search([('job_title', 'in', manager_titles)])

        if managers:
            for manager in managers:
                self._create_activity_for_manager(order, f"Quotation {order.name} needs to be confirmed by {manager.job_title}.", manager.user_id.id)

    def _request_approval_for_administrator(self, order):
        order.message_post(body="Request for approval sent to the Administrators.", subtype_xmlid="mail.mt_comment")
        admin = order.env['hr.employee'].search([('job_title', '=', 'Administrator')])

        if admin:
            self._create_activity_for_manager(order, f"Quotation {order.name} needs to be confirmed by an administrator.", admin[0].user_id.id)

    def _create_activity_for_manager(self, order, note, user_id):
        activity_vals = {
            'activity_type_id': order.env.ref('mail.mail_activity_data_todo').id,
            'note': note,
            'user_id': user_id,
        }
        order.activity_schedule('mail.mail_activity_data_todo', **activity_vals)
