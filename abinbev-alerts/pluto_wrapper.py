import time
import logging

import requests


class LoginFailedException(BaseException):
    pass


class PlutoClient:
    def __init__(self, email, password, subdomain):
        self.base_url = f"https://{subdomain}.plutoshift.com"
        self.email = email
        self.password = password
        self.headers = {}
        self.logger = logging.getLogger()
        self.acquire_token()

    def acquire_token(self):
        wait_time = 5
        while not len(self.headers):
            try:
                self._acquire_token_single()
                break
            except LoginFailedException as lfe:
                time.sleep(wait_time)
                if wait_time < 300:
                    wait_time *= 2
                self.logger.warning(f"Login failed, trying again in {wait_time} seconds ({lfe}")

    def _acquire_token_single(self):
        r = requests.post(f"{self.base_url}/api/token/", {'email': self.email, 'password': self.password})
        if r.status_code != 200:
            raise LoginFailedException(r.status_code)
        self.headers = {"Authorization": f"Token {r.json()['token']}"}

    def post(self, *args, **kwargs):
        r = requests.get(f"{self.base_url}{args[0]}", *args[1:], headers=self.headers, **kwargs)
        if r.status_code == 401 or r.status_code == 400:
            # Token may have expired, lets try reacquiring!
            logging.warning("Initial connection refused, reacquiring token")
            self.acquire_token()
            r = requests.post(f"{self.base_url}{args[0]}", *args[1:], headers=self.headers, **kwargs)
        return r

    def get(self, *args, **kwargs):
        r = requests.get(f"{self.base_url}{args[0]}", *args[1:], headers=self.headers, **kwargs)
        if r.status_code == 401 or r.status_code == 400:
            # Token may have expired, lets try reacquiring!
            logging.warning("Initial connection refused, reacquiring token")
            self.acquire_token()
            r = requests.get(f"{self.base_url}{args[0]}", *args[1:], headers=self.headers, **kwargs)
        return r
