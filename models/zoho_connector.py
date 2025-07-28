# zoho_api/models/zoho_connector.py
import requests
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ZohoConnector(models.Model):
    _name = 'zoho.connector'
    _description = 'Zoho API Connector'
    
    name = fields.Char(default='Zoho Connector')
    workspace_id = fields.Char(string='WorkDrive Workspace ID')
    
    @api.model
    def get_access_token(self):
        """Obtient un token d'accès à partir du refresh token"""
        ICP = self.env['ir.config_parameter'].sudo()
        
        refresh_token = ICP.get_param('zoho.refresh_token')
        if not refresh_token:
            raise UserError(_("Pas de refresh token. Veuillez vous authentifier d'abord."))
        
        token_url = f"https://accounts.zoho.{ICP.get_param('zoho.domain', 'com')}/oauth/v2/token"
        
        data = {
            'refresh_token': refresh_token,
            'client_id': ICP.get_param('zoho.client_id'),
            'client_secret': ICP.get_param('zoho.client_secret'),
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            _logger.error(f"Erreur token: {e}")
            raise UserError(_("Impossible d'obtenir le token: %s") % str(e))
    
    @api.model
    def get_workspaces(self):
        """Récupère les workspaces WorkDrive"""
        token = self.get_access_token()
        domain = self.env['ir.config_parameter'].sudo().get_param('zoho.domain', 'com')
        
        # URL correcte selon la région
        if domain == 'eu':
            base_url = 'https://www.zohoapis.eu'
        elif domain == 'in':
            base_url = 'https://www.zohoapis.in'
        else:
            base_url = 'https://www.zohoapis.com'
        
        headers = {'Authorization': f'Zoho-oauthtoken {token}'}
        
        try:
            url = f"{base_url}/workdrive/api/v1/ws"
            _logger.info(f"Calling WorkDrive API: {url}")
            _logger.info(f"Headers: {headers}")
            
            response = requests.get(url, headers=headers)
            
            _logger.info(f"Response status: {response.status_code}")
            _logger.info(f"Response body: {response.text}")
            
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            _logger.error(f"Erreur workspaces: {e}")
            _logger.error(f"Response content: {getattr(response, 'text', 'No response')}")
            raise UserError(_("Erreur récupération workspaces: %s") % str(e))
    
    def create_folder(self, name, parent_id=None):
        """Crée un dossier dans WorkDrive"""
        token = self.get_access_token()
        domain = self.env['ir.config_parameter'].sudo().get_param('zoho.domain', 'com')
        
        # URL correcte selon la région
        if domain == 'eu':
            base_url = 'https://www.zohoapis.eu'
        elif domain == 'in':
            base_url = 'https://www.zohoapis.in'
        else:
            base_url = 'https://www.zohoapis.com'
        
        # Récupérer workspace_id si pas défini
        if not self.workspace_id:
            workspaces = self.get_workspaces()
            if workspaces:
                self.workspace_id = workspaces[0]['id']
            else:
                raise UserError(_("Aucun workspace trouvé"))
        
        url = f"{base_url}/workdrive/api/v1/ws/{self.workspace_id}/files"
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "data": {
                "type": "folder",
                "attributes": {
                    "name": name
                }
            }
        }
        
        if parent_id:
            data["data"]["attributes"]["parent_id"] = parent_id
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result.get('data', {}).get('id')
        except Exception as e:
            _logger.error(f"Erreur création dossier: {e}")
            raise UserError(_("Erreur création dossier: %s") % str(e))
    
    def send_cliq_message(self, channel_name, message):
        """Envoie un message dans Cliq"""
        token = self.get_access_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('zoho.cliq_base_url')
        
        url = f"{base_url}/api/v2/channelsbyname/{channel_name}/message"
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
        
        data = {"text": message}
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            _logger.error(f"Erreur Cliq: {e}")
            # Ne pas faire échouer si Cliq n'est pas configuré
            _logger.warning("Message Cliq non envoyé: %s", str(e))
            return False