"""Module for IQ option appinit http resource."""

from iqoptionapi.http.resource import Resource


class Appinit(Resource):
    """Class for IQ option login resource."""
    # pylint: disable=too-few-public-methods

    url = "appinit"

    def _get(self, data=None, headers=None):
        """Send get request for IQ Option API appinit http resource.

        :returns: The instance of :class:`requests.Response`.
        """
        return self.send_http_request("GET", data=data, headers=headers)

    def __call__(self):
        """Method to get IQ Option API appinit http request.

        :returns: The instance of :class:`requests.Response`.
        """
        return self._get()
        
    def get_app_init(self):
        """Method to get application initialization data.
        
        :returns: The instance of :class:`requests.Response`.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://iqoption.com/",
            "Origin": "https://iqoption.com"
        }
        return self._get(headers=headers)