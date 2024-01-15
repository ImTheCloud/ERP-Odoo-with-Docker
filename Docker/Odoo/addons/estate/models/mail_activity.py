from odoo import models

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def activity_done(self, activity_ids):
        # This function is called when you mark an activity as done

        # Call the action_confirm method of sale order for each sale linked to the activity
        sale_orders = self.env['sale.order'].search([('activity_ids', 'in', activity_ids)])
        for order in sale_orders:
            order.action_confirm()

        # Call the original function
        return super(MailActivity, self).activity_done(activity_ids)
