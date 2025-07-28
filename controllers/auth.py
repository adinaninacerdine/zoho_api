from odoo import http
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)


class ZohoAuth(http.Controller):
    
    @http.route('/auth/zoho', type='http', auth='user')
    def auth_start(self):
        """Démarre l'authentification OAuth"""
        ICP = request.env['ir.config_parameter'].sudo()
        
        client_id = ICP.get_param('zoho.client_id')
        if not client_id:
            return "Erreur: zoho.client_id non configuré"
        
        base_url = ICP.get_param('web.base.url')
        redirect_uri = f"{base_url}/auth/zoho/callback"
        
        # Scopes corrects selon la doc
        scope = 'WorkDrive.files.CREATE,WorkDrive.files.READ,ZohoCliq.Webhooks.CREATE'
        
        auth_url = (
            f"https://accounts.zoho.{ICP.get_param('zoho.domain', 'com')}/oauth/v2/auth"
            f"?response_type=code"
            f"&client_id={client_id}"
            f"&scope={scope}"
            f"&redirect_uri={redirect_uri}"
            f"&access_type=offline"
        )
        
        return request.redirect(auth_url)
    
    @http.route('/auth/zoho/callback', type='http', auth='public')
    def auth_callback(self, **kw):
        """Callback OAuth"""
        code = kw.get('code')
        if not code:
            return "Erreur: pas de code d'autorisation"
        
        ICP = request.env['ir.config_parameter'].sudo()
        
        # Échanger le code contre un token
        token_url = f"https://accounts.zoho.{ICP.get_param('zoho.domain', 'com')}/oauth/v2/token"
        
        data = {
            'code': code,
            'client_id': ICP.get_param('zoho.client_id'),
            'client_secret': ICP.get_param('zoho.client_secret'),
            'redirect_uri': f"{ICP.get_param('web.base.url')}/auth/zoho/callback",
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            refresh_token = tokens.get('refresh_token')
            
            if refresh_token:
                ICP.set_param('zoho.refresh_token', refresh_token)
                return "✅ Authentification réussie! Vous pouvez fermer cette fenêtre."
            else:
                return f"Erreur: pas de refresh token dans la réponse"
                
        except Exception as e:
            _logger.error(f"Erreur callback: {e}")
            return f"Erreur: {str(e)}"