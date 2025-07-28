from odoo import http
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)


class ZohoAuth(http.Controller):
    
    @http.route('/zoho/auth/start', type='http', auth='user', methods=['GET'])
    def auth_start(self, **kwargs):
        """Démarre l'authentification OAuth"""
        ICP = request.env['ir.config_parameter'].sudo()
        
        client_id = ICP.get_param('zoho.client_id')
        if not client_id:
            return """
            <html>
                <body style="font-family: Arial; padding: 50px;">
                    <h2>❌ Erreur de configuration</h2>
                    <p>Le paramètre <code>zoho.client_id</code> n'est pas configuré.</p>
                    <p>Allez dans <b>Paramètres > Paramètres Système</b> et ajoutez:</p>
                    <ul>
                        <li>zoho.client_id</li>
                        <li>zoho.client_secret</li>
                    </ul>
                    <a href="/web">Retour à Odoo</a>
                </body>
            </html>
            """
        
        base_url = ICP.get_param('web.base.url')
        redirect_uri = f"{base_url}/zoho/auth/callback"
        
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
        
        _logger.info("Redirecting to Zoho OAuth: %s", auth_url)
        
        return request.redirect(auth_url)
    
    @http.route(['/zoho/auth/callback', '/auth/zoho/callback'], type='http', auth='public', methods=['GET', 'POST'])
    def auth_callback(self, **kw):
        """Callback OAuth"""
        code = kw.get('code')
        error = kw.get('error')
        
        if error:
            return f"""
            <html>
                <body style="font-family: Arial; padding: 50px;">
                    <h2>❌ Erreur Zoho</h2>
                    <p>{error}: {kw.get('error_description', '')}</p>
                    <a href="/web">Retour à Odoo</a>
                </body>
            </html>
            """
        
        if not code:
            return """
            <html>
                <body style="font-family: Arial; padding: 50px;">
                    <h2>❌ Erreur</h2>
                    <p>Pas de code d'autorisation reçu</p>
                    <a href="/web">Retour à Odoo</a>
                </body>
            </html>
            """
        
        ICP = request.env['ir.config_parameter'].sudo()
        
        # Échanger le code contre un token
        token_url = f"https://accounts.zoho.{ICP.get_param('zoho.domain', 'com')}/oauth/v2/token"
        
        data = {
            'code': code,
            'client_id': ICP.get_param('zoho.client_id'),
            'client_secret': ICP.get_param('zoho.client_secret'),
            'redirect_uri': f"{ICP.get_param('web.base.url')}/zoho/auth/callback",
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(token_url, data=data)
            _logger.info("Token response: %s - %s", response.status_code, response.text)
            
            response.raise_for_status()
            
            tokens = response.json()
            refresh_token = tokens.get('refresh_token')
            
            if refresh_token:
                ICP.set_param('zoho.refresh_token', refresh_token)
                return """
                <html>
                    <body style="font-family: Arial; padding: 50px; text-align: center;">
                        <h2>✅ Authentification réussie!</h2>
                        <p>Le refresh token a été sauvegardé.</p>
                        <p>Vous pouvez maintenant utiliser l'intégration Zoho.</p>
                        <br>
                        <a href="/web" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px;">
                            Retourner à Odoo
                        </a>
                    </body>
                </html>
                """
            else:
                return f"""
                <html>
                    <body style="font-family: Arial; padding: 50px;">
                        <h2>❌ Erreur</h2>
                        <p>Pas de refresh token dans la réponse</p>
                        <pre>{tokens}</pre>
                        <a href="/web">Retour à Odoo</a>
                    </body>
                </html>
                """
                
        except Exception as e:
            _logger.error(f"Erreur callback: {e}")
            return f"""
            <html>
                <body style="font-family: Arial; padding: 50px;">
                    <h2>❌ Erreur</h2>
                    <p>{str(e)}</p>
                    <a href="/web">Retour à Odoo</a>
                </body>
            </html>
            """