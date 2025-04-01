"""Module for IQ Option http login resource."""

from iqoptionapi.http.resource import Resource
import time
import json
import uuid
import random
import logging


class Login(Resource):
    """Class for IQ option login resource."""
    # pylint: disable=too-few-public-methods

    url = ""

    def _post(self, data=None, headers=None):
        """Send get request for IQ Option API login http resource.

        :returns: The instance of :class:`requests.Response`.
        """
        login_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Origin": "https://iqoption.com",
            "Referer": "https://iqoption.com/pt/login",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Platform": "9",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Ch-Ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"114\", \"Google Chrome\";v=\"114\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        
        if headers:
            login_headers.update(headers)
            
        # Visitar página de login primeiro para obter cookies necessários
        try:
            self.api.session.get("https://iqoption.com/pt/login")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Falha ao visitar página de login: {e}")
            
        return self.api.send_http_request_v2(
            method="POST", 
            url="https://auth.iqoption.com/api/v2/login", 
            data=data, 
            headers=login_headers
        )

    def __call__(self, username, password):
        """Method to get IQ Option API login http request.

        :param str username: The username of a IQ Option server.
        :param str password: The password of a IQ Option server.

        :returns: The instance of :class:`requests.Response`.
        """
        # Gerar um identificador único para a sessão para evitar detecção de bots
        device_id = str(uuid.uuid4())
        session_id = ''.join(random.choice('0123456789abcdef') for i in range(32))
        
        # Timestamp atual em milissegundos
        timestamp = int(time.time() * 1000)
        
        data = {
            "identifier": username,
            "password": password,
            "remember": True,
            "device": "web",
            "device_id": device_id,
            "session_id": session_id, 
            "device_name": "Chrome",
            "device_type": "desktop",
            "device_model": "Windows",
            "browser_name": "Chrome",
            "browser_version": "114.0.0.0",
            "os_name": "Windows",
            "os_version": "10",
            "language": "pt-BR",
            "region": "br",
            "tz": "America/Sao_Paulo",
            "tz_offset": -180,
            "attempt_only": False,
            "timestamp": timestamp,
            "captcha": {
                "type": "None",
                "v": "v3"
            }
        }

        logger = logging.getLogger(__name__)
        logger.info(f"Tentando login para {username}")
        
        return self._post(data=data)
