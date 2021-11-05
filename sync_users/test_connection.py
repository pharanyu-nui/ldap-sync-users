import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

MEMO_WEB_PROD = os.getenv('MEMO_WEB_PROD')
MEMO_WEB_DEV = os.getenv('MEMO_WEB_DEV')
MEMO_AUTH_USER = os.getenv('MEMO_AUTH_USER')
MEMO_AUTH_PASS = os.getenv('MEMO_AUTH_PASS')


if __name__ == '__main__':
    web_servers = list(filter(lambda x: x != '', [MEMO_WEB_DEV, MEMO_WEB_PROD]))

    for web_server in web_servers:
        res = requests.post(
            f'{web_server}/api/sync-ldap-test-api/', 
            auth=HTTPBasicAuth(MEMO_AUTH_USER, MEMO_AUTH_PASS),
            data={
                'hello': 'world'
            }
        )

        if (res.status_code == 200):
            print(f'Can connect {web_server}')
        else:
            print(f'Fail connect {web_server} with status code {res.status_code}')
