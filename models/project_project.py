# zoho_api/models/project_project.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    zoho_folder_id = fields.Char(string='ID Dossier WorkDrive')
    zoho_cliq_channel = fields.Char(string='Canal Cliq')
    zoho_user_folders = fields.Text(string='Dossiers utilisateurs (JSON)', default='{}')
    
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
    
    def action_create_zoho_folder(self):
        """Crée le dossier WorkDrive pour ce projet (pour projets existants)"""
        if self.zoho_folder_id:
            raise UserError(_("Ce projet a déjà un dossier WorkDrive"))
        
        connector = self.env['zoho.connector'].search([], limit=1)
        if not connector:
            connector = self.env['zoho.connector'].create({})
        
        try:
            folder_id = connector.create_folder(self.name)
            self.zoho_folder_id = folder_id
            
            self.message_post(
                body=f"✅ Dossier WorkDrive créé avec succès",
                message_type='notification'
            )
            
            # Notifier dans Cliq si configuré
            if self.zoho_cliq_channel:
                message = f"📁 Dossier WorkDrive créé pour le projet : {self.name}"
                connector.send_cliq_message(self.zoho_cliq_channel, message)
                
        except Exception as e:
            raise UserError(_("Erreur lors de la création du dossier: %s") % str(e))
    
    def get_user_folder_id(self, user_id=None):
        """Obtient ou crée le dossier utilisateur dans le projet"""
        if not self.zoho_folder_id:
            raise UserError(_("Pas de dossier principal. Créez d'abord le dossier du projet."))
        
        if not user_id:
            user_id = self.env.user.id
        
        import json
        user_folders = json.loads(self.zoho_user_folders or '{}')
        user_key = str(user_id)
        
        # Si le dossier utilisateur existe déjà
        if user_key in user_folders:
            return user_folders[user_key]
        
        # Créer le dossier utilisateur
        connector = self.env['zoho.connector'].search([], limit=1)
        if not connector:
            raise UserError(_("Connecteur Zoho non trouvé"))
        
        user = self.env['res.users'].browse(user_id)
        folder_name = f"{user.name}"
        
        try:
            user_folder_id = connector.create_folder(
                name=folder_name,
                parent_id=self.zoho_folder_id
            )
            
            # Sauvegarder dans le JSON
            user_folders[user_key] = user_folder_id
            self.zoho_user_folders = json.dumps(user_folders)
            
            return user_folder_id
            
        except Exception as e:
            raise UserError(_("Erreur création dossier utilisateur: %s") % str(e))
    
    def action_get_my_folder_link(self):
        """Obtient le lien vers le dossier de l'utilisateur connecté"""
        try:
            user_folder_id = self.get_user_folder_id()
            
            # Construire l'URL WorkDrive (à adapter selon votre région Zoho)
            base_url = self.env['ir.config_parameter'].sudo().get_param('zoho.workdrive_base_url')
            workdrive_url = base_url.replace('www.zohoapis.com', 'workdrive.zoho.com')
            folder_url = f"{workdrive_url}/folder/{user_folder_id}"
            
            return {
                'type': 'ir.actions.act_url',
                'url': folder_url,
                'target': 'new',
            }
            
        except Exception as e:
            raise UserError(_("Erreur: %s") % str(e))