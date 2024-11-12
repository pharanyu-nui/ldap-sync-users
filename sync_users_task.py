import os
import json
import logging
import pysftp
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL
from utils import (
    truncate_utf8_chars, generate_timestamp_filename, clear_dir, create_dir_if_not_exist,
)

load_dotenv()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

SFTP_PROD_IP = os.getenv('SFTP_PROD_IP')
SFTP_DEV_IP = os.getenv('SFTP_DEV_IP')
SFTP_PROD_PORT = int(os.getenv('SFTP_PROD_PORT'))
SFTP_DEV_PORT = int(os.getenv('SFTP_DEV_PORT'))
SFTP_USER = os.getenv('SFTP_USER')
SFTP_PASSWORD = os.getenv('SFTP_PASSWORD')
SFTP_PROD_TARGET_DIR_PATH = './upload'
SFTP_DEV_TARGET_DIR_PATH = './files'

LDAP_HOST = os.getenv('LDAP_HOST')
LDAP_PORT = int(os.getenv('LDAP_PORT'))
LDAP_USER = os.getenv('LDAP_USER')
LDAP_PASSWORD = os.getenv('LDAP_PASSWORD')
LDAP_BASE = os.getenv('LDAP_BASE')

SEARCH_FILTER=os.getenv('LDAP_SEARCH_FILTER')
SEARCH_ATTRIBUTES = ['distinguishedName', 'sAMAccountName', 'givenName', 'sn', 'mail', 'department']
SEARCH_PAGE_SIZE = 1000

BACKUP_DIR_PATH = os.path.join(ROOT_DIR, 'backup')
LOG_DIR_PATH = os.path.join(ROOT_DIR, 'logs')


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
    print(f'==> connect LDAP server "{LDAP_HOST}:{LDAP_PORT}"')

    conn.extend.standard.paged_search(
        LDAP_BASE, 
        SEARCH_FILTER, 
        attributes=SEARCH_ATTRIBUTES, 
        paged_size=SEARCH_PAGE_SIZE,
        generator=False,
    )
    print('==> query users from LDAP')

    execute_data_fn(conn.entries)

    conn.unbind()


def write_json_file(entry_generator) -> str:
    create_dir_if_not_exist(BACKUP_DIR_PATH)
    clear_dir(BACKUP_DIR_PATH)

    filename = generate_timestamp_filename()
    file_path = os.path.join(BACKUP_DIR_PATH, filename)

    with open(file_path, 'w') as outfile:
        print('[', file=outfile)

        for entry in entry_generator:
            user_data_dict = json.loads(entry.entry_to_json())
            json.dump(user_data_dict, outfile, indent=4)
            print(',', file=outfile)

    truncate_utf8_chars(file_path, 1)
    with open(file_path, 'a') as outfile:
        print('\n]', file=outfile)

    print(f'==> write users data to "{file_path}"')
    return file_path


def send_file_to_sftp_server(file_path: str, ip_address: str, port: int, target_path: str):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    connection_config = {
        'host': ip_address,
        'port': port,
        'username': SFTP_USER,
        'password': SFTP_PASSWORD,
        'cnopts': cnopts,
    }

    with pysftp.Connection(**connection_config) as sftp:
        print(f'==> connect SFTP server "{ip_address}:{port}"')
        if not sftp.exists(target_path):
            raise Exception(f'"{target_path}" doesn\'t exists on SFTP server.')

        filename = os.path.basename(file_path)
        local_file_path = file_path
        remote_file_path = os.path.join(target_path, filename)
        sftp.put(local_file_path, remote_file_path)
        print(f'==> copy file "{local_file_path}" to SFTP server')


def process_user_data(entry_generator):
    filename = write_json_file(entry_generator)
    send_file_to_sftp_server(
        file_path=filename,
        ip_address=SFTP_PROD_IP,
        port=SFTP_PROD_PORT,
        target_path=SFTP_PROD_TARGET_DIR_PATH
    )
    send_file_to_sftp_server(
        file_path=filename,
        ip_address=SFTP_DEV_IP,
        port=SFTP_DEV_PORT,
        target_path=SFTP_DEV_TARGET_DIR_PATH
    )


def write_error_log(err):
    create_dir_if_not_exist(LOG_DIR_PATH)
    log_filename = generate_timestamp_filename(type='log')
    log_path = os.path.join(LOG_DIR_PATH, log_filename)
    logging.basicConfig(
        filename=log_path, 
        level=logging.DEBUG, 
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    logger=logging.getLogger(__name__)
    logger.exception(err)
    print(f'==> [ERROR] write error log to "{log_path}"')


if __name__ == '__main__':
    try:
        query_user_data(
            lambda entry_generator: process_user_data(entry_generator)
        )
    except Exception as err:
        write_error_log(err)
