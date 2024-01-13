import logging
from odoo import fields, models
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class EstateProperty(models.Model):
    _inherit = 'sale.order.line'    
    training_date = fields.Date(string="Training Date")
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")


# btn Request approval
    def _request_approval(self, approver):
        # Update the sale order line to indicate that approval is pending
        # self.write({'state': 'pending_approval'})

        # Log a message indicating the need for approval
        _logger.info("Quotation '%s' needs to be confirmed by %s" % (self.order_id.name, approver))

        # Add a note in the document's discussion
        # self.message_post(body="Quotation needs approval from %s"% (self.order_id.name, approver))


    def button_request_approval(self):
        # Calculate the total amount of the quotation
        total_amount = sum(self.mapped('price_unit'))

        # Define the approval levels
        if total_amount < 500:
            # No approval required
            self.order_id.action_confirm()
        elif 500 <= total_amount < 1000:
            # Approval required from manager level 1 or 2
            approver = self.env['hr.employee'].search([('job_id', 'in', ['manager_level_1', 'manager_level_2'])], limit=1)
            self._request_approval(approver)
        elif 1000 <= total_amount < 5000:
            # Approval required from manager level 2
            approver = self.env['hr.employee'].search([('job_id', '=', 'manager_level_2')], limit=1)
            self._request_approval(approver)
        else:
            # Approval required from administrator
            administrator = self.env['hr.employee'].search([('job_id', '=', 'administrator')], limit=1)
            self._request_approval(administrator)

        # Log a message to indicate that approval has been requested
        _logger.info("Request for approval sent to the appropriate approver")

 
# btn confirm
    def action_confirm(self):
        # Check if the employee limit condition is met
        if not self._check_employee_limit():
            return

        _logger.info("Début de la méthode action_confirm pour SaleOrder")

        # Create calendar events based on training date and employee for each order line
        self._create_training_calendar_event()

        # Call the original action_confirm method to continue the order confirmation process
        res = super(EstateProperty, self).action_confirm()

        _logger.info("Fin de la méthode action_confirm pour SaleOrder")
        return res
    
    def _check_employee_limit(self):
        """Check if the employee is 'Employee Limited' and if the amount exceeds 350."""
        if self.employee.name == "Employee Limited" and sum(self.mapped('price_unit')) > 350:
            message = "Sale Order not confirmed: Amount above the partner limit."
            self.order_id.message_post(body=message)
            _logger.warning(message)
            return False
        return True

    def _create_training_calendar_event(self):
        for order_line in self:
            # Vérifiez si la ligne de commande a une date de formation et un produit associé
            if order_line.training_date and order_line.product_template_id:
                # Calculer la date et l'heure de début et de fin de l'événement
                start_datetime = datetime.combine(order_line.training_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(hours=2)  # Vous devrez ajuster cela en fonction de la durée de votre événement

                # Créer l'événement dans le calendrier
                self.env['calendar.event'].create({
                    'name': 'Training: %s' % order_line.product_template_id.name,
                    'start_datetime': start_datetime,
                    'stop_datetime': end_datetime,
                    'partner_ids': [(6, 0, [order_line.order_id.partner_id.id])],  # Associer l'événement au partenaire de la commande
                    'description': 'Training for product: %s' % order_line.product_template_id.name,
                    'location': order_line.order_id.partner_id.property_product_pricelist.city or '',  # Ajoutez la ville du partenaire comme lieu de l'événement
                    'alarm_ids': [(0, 0, {'name': 'Remind', 'alarm_id': self.env.ref('calendar.alarm_reminder').id, 'duration': 60})],  # Ajouter une alarme de rappel 60 minutes avant
                })