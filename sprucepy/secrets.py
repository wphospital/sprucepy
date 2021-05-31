import requests
import os
from .constants import api_url


def get_secret_by_key(key):
    """Retrieve a secret from the key vault

    Args:
        key (str): the key for the secret to retreive
    """
    res = requests.get(api_url + "secrets/" + str(key))
    if res.status_code == 200:
        return res.json()['value']
    else:
        raise IndexError(key)
