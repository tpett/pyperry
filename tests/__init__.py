import os

import pyperry
import tests.helpers.http_test_server as http_server

test_dir = os.path.abspath(os.path.dirname(__file__))
test_fixtures_dir = os.path.join(test_dir, 'fixtures')
test_sys_path_dir = os.path.join(test_fixtures_dir, 'path')

def run_http_server():
    try:
        http_server.spawn()
    except http_server.ServerAlreadyRunning:
        pass
