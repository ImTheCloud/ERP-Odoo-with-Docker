from odoo import models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_done(self):
        res = super(MailActivity, self).action_done()

        for activity in self:
            activity.message_post(body="test", subtype_xmlid="mail.mt_comment")

            sale_order = activity.sale_order_id
            if sale_order:
                sale_order.action_confirm()

        return res