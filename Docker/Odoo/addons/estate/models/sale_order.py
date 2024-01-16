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

        # Check total amount for the order and initiate approval process
        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))


            if 500 <= total_amount <= 1000:
                # Approval required from managers with job title 'Manager1' or 'Manager2'
                order.message_post(body="Request for approval sent to the managers.", subtype_xmlid="mail.mt_comment")
                managers = order.env['hr.employee'].search([('job_title', 'in', ['Manager1', 'Manager2'])])
                if managers:
                    # Create activity to notify about approval requirement for both managers
                    activity_vals_manager1 = {
                        'activity_type_id': order.env.ref('mail.mail_activity_data_todo').id,
                        'note': f"Quotation {order.name} needs to be confirmed by Manager1.",
                        'user_id': managers[0].user_id.id,
                    }
                    activity_vals_manager2 = {
                        'activity_type_id': order.env.ref('mail.mail_activity_data_todo').id,
                        'note': f"Quotation {order.name} needs to be confirmed by Manager2.",
                        'user_id': managers[1].user_id.id, 
                    }
                    order.activity_schedule('mail.mail_activity_data_todo', **activity_vals_manager1)
                    order.activity_schedule('mail.mail_activity_data_todo', **activity_vals_manager2)
            elif 1000 <= total_amount <= 5000:
                # Approval required from managers with job title 'Manager2'
                manager2 = order.env['hr.employee'].search([('job_title', '=', 'Manager2')])
                if manager2:
                    order.message_post(body="Request for approval sent to the managers.", subtype_xmlid="mail.mt_comment")
                    # Create activity to notify about approval requirement for Manager2
                    activity_vals = {
                        'activity_type_id': order.env.ref('mail.mail_activity_data_todo').id,
                        'note': f"Quotation {order.name} needs to be confirm by a manager.",
                        'user_id': manager2[0].user_id.id,  # Assign activity to the first Manager2
                    }
                    order.activity_schedule('mail.mail_activity_data_todo', **activity_vals)
            else:
                order.message_post(body="Request for approval sent to the Administrators.", subtype_xmlid="mail.mt_comment")
                # Amount greater than 5000, approval required from an administrator
                admin = order.env['hr.employee'].search([('job_title', '=', 'Administrator')])
                if admin:
                    # Create activity to notify about approval requirement for the Administrator
                    activity_vals = {
                        'activity_type_id': order.env.ref('mail.mail_activity_data_todo').id,
                        'note': f"Quotation {order.name} needs to be confirmed by an administrator.",
                        'user_id': admin[0].user_id.id,  # Assign activity to the administrator
                    }
                    order.activity_schedule('mail.mail_activity_data_todo', **activity_vals)
        return res
