from odoo import models
from datetime import datetime, timedelta

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = False

        # Check total amount for the order and user permissions
        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))
                            
            if total_amount < 500:
                 res = super(SaleOrder, order).action_confirm()
            elif 500 <= total_amount <= 1000:
                # Get the current user's job title
                current_user_job_title = order.env.user.employee_id.job_title

                # Check if the current user's job title is in the allowed titles
                if current_user_job_title in ['Manager1', 'Manager2','Administrator']:
                    res = super(SaleOrder, order).action_confirm()
                else:
                    order.message_post(body="Sale order not confirmed: Amount above the group limit.", subtype_xmlid="mail.mt_comment")
                return {'warning': {'title': 'Warning', 'message': 'Sale order not confirmed: Amount above the group limit.'}}
                    
            elif 1000 <= total_amount <= 5000:
                current_user_job_title = order.env.user.employee_id.job_title

                # Check if the current user's job title is 'Manager2' or 'Administrator'
                if current_user_job_title in ['Manager2', 'Administrator']:
                    res = super(SaleOrder, order).action_confirm()
                else:
                    order.message_post(body="Sale order not confirmed: Amount above the group limit.", subtype_xmlid="mail.mt_comment")
                return {'warning': {'title': 'Warning', 'message': 'Sale order not confirmed: Amount above the group limit.'}}
                
            elif total_amount > 5000:
                current_user_job_title = order.env.user.employee_id.job_title

                # Check if the current user's job title is 'Administrator'
                if current_user_job_title in ['Administrator']:
                    res = super(SaleOrder, order).action_confirm()
                else:
                    order.message_post(body="Sale order not confirmed: Amount above the group limit.", subtype_xmlid="mail.mt_comment")
                return {'warning': {'title': 'Warning', 'message': 'Sale order not confirmed: Amount above the group limit.'}}



            # Create calendar events for order lines with training dates
            for line in order.order_line.filtered(lambda l: l.training_date):
                start_datetime = datetime.combine(line.training_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(days=1, seconds=-1)

                user_id = line.employee.user_id.id if line.employee.user_id else False

                # Create a calendar event for the training date
                event_vals = {
                    'name': f"{line.product_id.display_name} - {line.name}",
                    'start': start_datetime,
                    'stop': end_datetime,
                    'allday': True,
                    'rrule': "FREQ=WEEKLY",
                    'partner_ids': [(4, line.employee.user_id.partner_id.id)],
                    'description': line.name,
                    'user_id': user_id,  # Assign activity to the user who should approve
                }
                order.env['calendar.event'].create(event_vals)
        return res

    def action_request_approval(self):
        res = False

        # Check total amount for the order and initiate approval process
        for order in self:
            total_amount = sum(order.order_line.mapped('price_unit'))

            if total_amount < 500:
                # No approval required for amounts less than 500€
                res = super(SaleOrder, order).action_confirm()
            elif 500 <= total_amount <= 1000:
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
