import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL

load_dotenv()

MEMO_WEB_PROD = os.getenv('MEMO_WEB_PROD')
MEMO_WEB_DEV = os.getenv('MEMO_WEB_DEV')
MEMO_AUTH_USER = os.getenv('MEMO_AUTH_USER')
MEMO_AUTH_PASS = os.getenv('MEMO_AUTH_PASS')

LDAP_HOST=os.getenv('LDAP_HOST')
LDAP_PORT=int(os.getenv('LDAP_PORT'))
LDAP_USER=os.getenv('LDAP_USER')
LDAP_PASSWORD=os.getenv('LDAP_PASSWORD')
LDAP_BASE=os.getenv('LDAP_BASE')

SEARCH_FILTER=os.getenv('LDAP_SEARCH_FILTER')
SEARCH_ATTRIBUTES = ['distinguishedName', 'sAMAccountName', 'givenName', 'sn', 'mail', 'department']
SEARCH_PAGE_SIZE = 500


def format_entry_attribute(attr):
    if type(attr) == int:
        return str(attr)

    elif type(attr) == list:
        if len(attr) == 0:
            return None
        else:
            return '|'.join(attr) 

    return attr


def format_entry(entry) -> dict:
    formated = {}
    for field in SEARCH_ATTRIBUTES:
        formated[field] = format_entry_attribute(entry[field])
    return formated


def query_user_data(query_callback_fn):
    server = Server(LDAP_HOST, LDAP_PORT, get_info=ALL)
    conn = Connection(
        server, 
        LDAP_USER, 
        LDAP_PASSWORD, 
        auto_bind=False,
        raise_exceptions=False,
    )
    conn.open()
    conn.bind()
    entry_generator = conn.extend.standard.paged_search(
        LDAP_BASE, 
        SEARCH_FILTER, 
        attributes=SEARCH_ATTRIBUTES, 
        paged_size=SEARCH_PAGE_SIZE,
        generator=True,
    )

    users = []
    count_size = 0
    for entry in entry_generator:
        formated_user = format_entry(entry['attributes'])
        users.append(formated_user)
        count_size += 1
        if count_size == SEARCH_PAGE_SIZE:
            query_callback_fn(users)
            users = []
            count_size = 0

    # last page
    if len(users) > 0:
        query_callback_fn(users)

    conn.unbind()


def send_user_data(web_server, data):
    headers = {'Content-type': 'application/json'}
    res = requests.post(
        f'{web_server}/api/sync-ldap-user-data/', 
        auth=HTTPBasicAuth(MEMO_AUTH_USER, MEMO_AUTH_PASS),
        headers=headers,
        json=data,
    )
    print(f'send data to {web_server}, response code {res.status_code}')


if __name__ == '__main__':
    web_servers = list(filter(lambda x: x != '', [MEMO_WEB_DEV, MEMO_WEB_PROD]))

    for web_server in web_servers:
        query_user_data(
            lambda users: send_user_data(web_server, users)
        )
