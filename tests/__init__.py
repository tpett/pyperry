import pyperry
import tests.helpers.http_test_server as http_server

def run_http_server():
    try:
        http_server.spawn()
    except http_server.ServerAlreadyRunning:
        pass
