from odoo import fields, models
from datetime import datetime, timedelta

class EstateProperty(models.Model):
    _inherit = 'sale.order.line'

    # Ajout de champs personnalisés pour gérer les propriétés immobilières
    training_date = fields.Date(string="Training Date")  # Date de formation associée à la ligne de commande
    employee = fields.Many2one(comodel_name="hr.employee", string="Employee", ondelete="set null")  # Employé associé à la ligne de commande
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')  # État de la commande (brouillon, confirmé, annulé)

    # Méthode pour demander l'approbation d'une commande
    def _request_approval(self, approver):
        message = f"Demande d'approbation envoyée à {approver.name}."
        log_note_group = self.env['mail.channel'].search([('name', '=', 'Log Note')], limit=1)
        if not log_note_group:
            log_note_group = self.env['mail.channel'].create({'name': 'Log Note'})
        log_note_group.message_post(body=message, subtype='mail.mt_comment', content_subtype='plaintext')

        # Création d'une activité pour l'approbation
        activity = self.env['mail.activity'].create({
            'res_id': self.id,
            'res_model': self._name,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'user_id': approver.user_id.id,
            'date_deadline': fields.Datetime.now() + timedelta(days=7),
            'note': f"Devis {self.id} doit être confirmé par {approver.name}.",
        })
        self.confirm_quotation  # Appel à la méthode de confirmation

    # Méthode déclenchée par le bouton de demande d'approbation
    def button_request_approval(self):
        total_amount = sum(self.mapped('price_unit'))

        if total_amount < 500:
            self.order_id.action_confirm()  # Confirmer automatiquement la commande si le montant est inférieur à 500
        elif 500 <= total_amount < 1000:
            approver = self.env['hr.employee'].search([('job_id', 'in', ['manager_level_1', 'manager_level_2'])], limit=1)
            self._request_approval(approver)
        elif 1000 <= total_amount < 5000:
            approver = self.env['hr.employee'].search([('job_id', '=', 'manager_level_2')], limit=1)
            self._request_approval(approver)
        else:
            administrator = self.env['hr.employee'].search([('job_id', '=', 'administrator')], limit=1)
            self._request_approval(administrator)

    # Méthode pour confirmer un devis
    def confirm_quotation(self):
        if self.state == 'draft':
            self.write({'state': 'confirmed'})

            current_user = self.env.user

            # Recherche d'une activité existante liée à la confirmation
            activity = self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('res_model', '=', self._name),
                ('user_id', '=', current_user.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ('state', '!=', 'done')
            ])

            if activity:
                activity.action_feedback(feedback="Devis confirmé par l'approbateur.")
            else:
                # Création d'un message dans le canal de journalisation si aucune activité n'est trouvée
                self.env['mail.channel'].search([('name', '=', 'Log Note')]).message_post(
                    body=f"{current_user.name} a confirmé le devis {self.id}.",
                    subtype='mail.mt_comment',
                    content_subtype='plaintext'
                )

    # Méthode pour vérifier si le montant de la commande dépasse la limite de l'employé limité
    def _check_employee_limit(self):
        if self.employee.name == "Employee Limited" and sum(self.mapped('price_unit')) > 250:
            message = "Commande non confirmée : Montant au-dessus de la limite du partenaire."
            log_note_group = self.env['mail.channel'].search([('name', '=', 'Log Note')], limit=1)
            if not log_note_group:
                log_note_group = self.env['mail.channel'].create({'name': 'Log Note'})
                log_note_group.message_post(body=message, subtype='mail.mt_comment', content_subtype='plaintext')
                return False
        return True

    # Méthode pour confirmer une commande avec gestion de la date de formation
    def action_confirm(self):
        self._check_employee_limit()  # Vérification de la limite d'employé
        for order_line in self:
            if order_line.training_date and order_line.product_template_id:
                # Création d'un événement de calendrier pour la formation
                start_datetime = datetime.combine(order_line.training_date, datetime.min.time())
                end_datetime = start_datetime + timedelta(hours=2)
                self.env['calendar.event'].create({
                    'name': 'Formation : %s' % order_line.product_template_id.name,
                    'start_datetime': start_datetime,
                    'stop_datetime': end_datetime,
                    'partner_ids': [(6, 0, [order_line.order_id.partner_id.id])],
                    'description': 'Formation pour le produit : %s' % order_line.product_template_id.name,
                    'location': order_line.order_id.partner_id.property_product_pricelist.city or '',
                    'alarm_ids': [(0, 0, {'name': 'Rappel', 'alarm_id': self.env.ref('calendar.alarm_reminder').id, 'duration': 60})],
                })
