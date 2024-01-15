from odoo import models

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def activity_done(self, activity_ids):
        # Cette fonction est appelée lorsque vous marquez une activité comme terminée

        # Appel de la méthode action_confirm de sale order pour chaque vente liée à l'activité
        sale_orders = self.env['sale.order'].search([('activity_ids', 'in', activity_ids)])
        for order in sale_orders:
            order.action_confirm()

        # Appel de la fonction d'origine
        return super(MailActivity, self).activity_done(activity_ids)
