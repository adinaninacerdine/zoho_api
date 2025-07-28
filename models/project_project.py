# zoho_api/models/project_project.py
from odoo import api, fields, models, _

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    zoho_folder_id = fields.Char(string='ID Dossier WorkDrive')
    zoho_cliq_channel = fields.Char(string='Canal Cliq')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Crée automatiquement un dossier WorkDrive à la création du projet"""
        projects = super().create(vals_list)
        
        connector = self.env['zoho.connector'].search([], limit=1)
        if not connector:
            connector = self.env['zoho.connector'].create({})
        
        for project in projects:
            try:
                # Créer dossier WorkDrive
                folder_id = connector.create_folder(project.name)
                project.zoho_folder_id = folder_id
                
                # Envoyer notification Cliq si canal configuré
                if project.zoho_cliq_channel:
                    message = f"📁 Nouveau projet créé : {project.name}"
                    connector.send_cliq_message(project.zoho_cliq_channel, message)
                    
            except Exception as e:
                # Log mais ne pas bloquer la création
                project.message_post(
                    body=f"⚠️ Erreur Zoho: {str(e)}",
                    message_type='notification'
                )
        
        return projects
    
    def write(self, vals):
        """Notifie les changements dans Cliq"""
        res = super().write(vals)
        
        if 'name' in vals and self.zoho_cliq_channel:
            connector = self.env['zoho.connector'].search([], limit=1)
            if connector:
                message = f"📝 Projet modifié : {self.name}"
                connector.send_cliq_message(self.zoho_cliq_channel, message)
        
        return res