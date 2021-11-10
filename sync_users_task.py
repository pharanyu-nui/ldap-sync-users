from logging import log
import os
import json
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL
from utils import truncate_utf8_chars, generate_timestamp_filename

load_dotenv()

SFTP_PROD_IP=os.getenv('SFTP_PROD_IP')
SFTP_DEV_IP=os.getenv('SFTP_DEV_IP')
SFTP_PORT=int(os.getenv('SFTP_PORT'))
SFTP_USER=os.getenv('SFTP_USER')
SFTP_PASSWORD=os.getenv('SFTP_PASSWORD')

LDAP_HOST=os.getenv('LDAP_HOST')
LDAP_PORT=int(os.getenv('LDAP_PORT'))
LDAP_USER=os.getenv('LDAP_USER')
LDAP_PASSWORD=os.getenv('LDAP_PASSWORD')
LDAP_BASE=os.getenv('LDAP_BASE')

SEARCH_FILTER=os.getenv('LDAP_SEARCH_FILTER')
SEARCH_ATTRIBUTES = ['givenName', 'sn', 'mail', 'telephoneNumber']
# SEARCH_ATTRIBUTES = ['distinguishedName', 'sAMAccountName', 'givenName', 'sn', 'mail', 'department']
SEARCH_PAGE_SIZE = 1000


def query_user_data(execute_data_fn):
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

    execute_data_fn(entry_generator)

    conn.unbind()


def write_json_file(entry_generator) -> str:
    filename = generate_timestamp_filename()
    with open(filename, 'w') as outfile:
        print('[', file=outfile)

        for entry in entry_generator:
            user_data = dict(entry['attributes'])
            json.dump(user_data, outfile, indent=4)
            print(',', file=outfile)

    truncate_utf8_chars(filename, 1)
    with open(filename, 'a') as outfile:
        print('\n]', file=outfile)

    return filename


def send_file_to_sftp_server(filename: str):
    print('send file to sftp server')


def process_user_data(entry_generator):
    filename = write_json_file(entry_generator)
    send_file_to_sftp_server(filename)


if __name__ == '__main__':
    query_user_data(
        lambda entry_generator: process_user_data(entry_generator)
    )
