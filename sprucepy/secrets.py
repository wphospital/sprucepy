import requests
import os
from .constants import api_url


def get_secret_by_key(
    key,
    api_url : str = api_url,
    api_token : str = ''
):
    """Retrieve a secret from the key vault

    Args:
        key
            str: the key for the secret to retreive
        api_url
            str : the root url for the Spruce API
        api_token
            str : auth token for the Spruce API

    Returns:
        str
            the secret value
    """

    auth_token = os.getenv('SPRUCE_API_TOKEN', api_token)

    headers = {
        'Authorization': f'Token {auth_token}'
    }

    res = requests.get(
        api_url + "secrets/" + str(key),
        headers=headers
    )

    if res.status_code == 200:
        return res.json()['value']
    else:
        if res.status_code == 404:
            raise IndexError(key)
        elif res.status_code == 401:
            raise PermissionError(res.json()['detail'])
        else:
            raise Exception(res.text)
